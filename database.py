import psycopg2
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT

def get_connection():
    conn = psycopg2.connect(
        host = DB_HOST,
        database = DB_NAME,
        user = DB_USER,
        password = DB_PASSWORD,
        port = DB_PORT
    )
    return conn

def get_or_create_user(telegram_id, username):
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                            SELECT user_id FROM users WHERE tg_id = %s;
                            """, (telegram_id,)
                            )
                row = cur.fetchone()
            
                if row: return row[0]
                
                cur.execute("""
                            INSERT INTO users (tg_id, username) VALUE  (%s, %s) RETURNING user_id
                            """, (telegram_id, username))

                return cur.fetchone()[0]
    finally:
        conn.close()

def get_words_for_user(user_id):
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                            SELECT w.word_id, w.en, w.ru FROM words w 
                            JOIN users_to_words uw ON w.word_id = uw.word_id
                            WHERE uw.user_id=%s AND uw.is_deleted = FALSE;""", (user_id,))
                return cur.fetchall()
    finally:
        conn.close()

def add_word(user_id, word_en, word_ru):
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                            SELECT id FROM users_to_words 
                            WHERE user_id=%s AND word_id = (SELECT word_id FROM words WHERE en = %s)
                            AND is_deleted = FALSE;""", (user_id, word_en))
                if cur.fetchone():
                    return 'already_exists'
                
                cur.execute("""
                            INSERT INTO words (en, ru) VALUES (%s, %s) RETURNING word_id;
                            """, (word_en, word_ru))
                word_id = cur.fetchone()[0]
                cur.execute("""
                            INSERT INTO users_to_words (user_id, word_id) VALUES (%s, %s) RETURNING word_id;
                            """, (user_id, word_id))
                return 'success'
    finally:
        conn.close()

def delete_word(user_id, word_id):
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                            UPDATE users_to_words SET is_deleted = TRUE
                            WHERE user_id = %s AND word_id = %s;""", (user_id, word_id))
    finally:
        conn.close()