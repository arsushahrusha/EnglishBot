import random

import telebot
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from config import BOT_TOKEN
import database

print('Start telegram bot...')

telebot.apihelper.proxy = {
    'https': 'socks5://64.227.76.27:1080'
}

state_storage = StateMemoryStorage()
token_bot = BOT_TOKEN
bot = TeleBot(token_bot, state_storage=state_storage)

known_users = []
userStep = {}
buttons = []


def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word_en = State()
    translate_word_ru = State()
    delete_word = State()

def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        known_users.append(uid)
        userStep[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0

def get_or_create_user_words(message):
    telegram_id = message.from_user.id
    username = message.from_user.username
    user_id = database.get_or_create_user(telegram_id, username)
    return user_id
    
def create_cards(message):
    user_id = get_or_create_user_words(message)
    cid = message.chat.id

    words = database.get_random_words(user_id, cnt=4)

    if not words:
        bot.send_message(cid, "Слов для изучения нет, добавьте с помощью кнопки 'Добавить слово'")
        return

    # if cid not in known_users:
    #     known_users.append(cid)
    #     userStep[cid] = 0
    #     bot.send_message(cid, "Hello, stranger, let study English...")
    # markup = types.ReplyKeyboardMarkup(row_width=2)

    global buttons
    buttons = []

    target_word_id, target_word_en, target_word_ru = words[0]  # брать из БД
    translate = target_word_ru
    target_word_btn = types.KeyboardButton(target_word_en)
    buttons.append(target_word_btn)

    others = [w[1] for w in words[1:]]  # брать из БД
    other_words_btns = [types.KeyboardButton(word) for word in others]
    buttons.extend(other_words_btns)

    random.shuffle(buttons)

    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])

    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(cid, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, cid)
    with bot.retrieve_data(message.from_user.id, cid) as data:
        data['target_word'] = target_word_en
        data['translate_word'] = translate
        data['other_words'] = others
        data['target_word_id'] = target_word_id
        data['user_id'] = user_id



@bot.message_handler(commands=['start'])
def start_registration(message):
    telegram_id = message.from_user.id
    username = message.from_user.username
    database.get_or_create_user(telegram_id, username)

    bot.send_message(message.chat.id, """Привет 👋
  Давай попрактикуемся в английском языке. Тренировки можешь проходить в удобном для себя темпе. 

  У тебя есть возможность использовать тренажёр, как конструктор, и собирать свою собственную базу для обучения. Для этого воспрользуйся инструментами:
  - добавить слово ➕,
  - удалить слово 🔙.

  Ну что, начнём ⬇️""")
    
    create_cards(message)

@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


# @bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
# def delete_word(message):
#     with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
#         print(data['target_word'])  # удалить из БД
#         user_id = data['user_id']
#         word_id = data['target_word_id']
#         target_word_en = data['target_word']

#     database.delete_word(user_id, word_id)
#     bot.send_message(message.chat.id, f'Слово "{target_word_en}" удалено')
#     create_cards(message)

@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def show_words_to_delete(message):
    user_id = get_or_create_user_words(message)
    words = database.get_all_user_words(user_id)

    if not words:
        bot.send_message(message.chat.id, "У вас нет слов для удаления!")
        return

    markup = types.ReplyKeyboardMarkup(row_width=1)
    for word_id, en, ru in words:
        btn = types.KeyboardButton(f"{en} — {ru}")
        markup.add(btn)

    bot.send_message(message.chat.id, "Выберите слово для удаления:", reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.delete_word, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['words_list'] = words


@bot.message_handler(state=MyStates.delete_word)
def process_delete_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        user_id = data['user_id']
        words_list = data['words_list']

    word_id = None
    for wid, en, ru in words_list:
        if message.text == f"{en} — {ru}":
            word_id = wid
            break

    if word_id is None:
        bot.send_message(message.chat.id, "Слово не найдено, попробуйте ещё раз")
        return

    database.delete_word(user_id, word_id)
    bot.send_message(message.chat.id, f"Слово '{message.text}' удалено!")
    bot.delete_state(message.from_user.id, message.chat.id)
    create_cards(message)

@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    bot.send_message(cid, "Введи, какое слово ты хочешь добавить на английском:")
    bot.set_state(message.from_user.id, MyStates.translate_word_en, cid)

@bot.message_handler(state=MyStates.translate_word_en)
def process_word_en(message):
    cid = message.chat.id
    with bot.retrieve_data(message.from_user.id, cid) as data:
        data['new_word_en'] = message.text

    bot.send_message(cid, f"Введи перевод на русском для слова {message.text}:")
    bot.set_state(message.from_user.id, MyStates.translate_word_ru, cid)

@bot.message_handler(state=MyStates.translate_word_ru)
def process_word_ru(message):
    cid = message.chat.id
    with bot.retrieve_data(message.from_user.id, cid) as data:
        word_en = data['new_word_en']
        user_id = data['user_id']
    
    word_ru = message.text
    res = database.add_word(user_id, word_en, word_ru)

    if res == 'already_exists':
        bot.send_message(cid, f"Слово {word_en} уже есть в словаре и переводится: {word_ru}")
    else:
        words_count = database.get_all_words_count(user_id)
        bot.send_message(cid, f"""Слово '{word_en}' добавлено в словарь!\n
                         Всего слов: {words_count}""")

    bot.delete_state(message.from_user.id, cid)
    create_cards(message)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            next_btn = types.KeyboardButton(Command.NEXT)
            add_word_btn = types.KeyboardButton(Command.ADD_WORD)
            delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
            buttons.extend([next_btn, add_word_btn, delete_word_btn])
            hint = show_hint(*hint_text)
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}")
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)
