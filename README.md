## Документация по запуску бота

### Требования
- Python 3.8 или выше
- PostgreSQL

### 1. Создание базы данных
Подключитесь к PostgreSQL и создайте базу данных:
```sql
CREATE DATABASE enBot;
```

### 2. Настройка конфигурации
Создайте файл `.env` в корне проекта по шаблону из `.env.example`:
```
BOT_TOKEN=<YOUR BOT TOKEN>

DB_HOST=localhost
DB_PORT=5432
BD_NAME=enBot
DB_USER=postgres
DB_PASSWORD=<YOUR PASSWORD>
```

### 3. Установка зависимостей
Выполните в терминале:
```bash
pip install -r requirements.txt
```
### 4. Инициализации БД:
```bash
psql -U postgres -d enBot -f CREATE.sql
psql -U postgres -d enBot -f INSERT.sql
```

### 5. Запуск бота
```bash
python main.py
```

### 6. Начало работы с ботом в Telegram:
Найдите своего бота и отправьте сообщение:
```
/start
```
