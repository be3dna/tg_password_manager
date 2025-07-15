# Telegram Password Manager 🔐

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot%20API-6.7+-lightgrey)](https://core.telegram.org/bots/api)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

Бот для безопасного хранения паролей в Telegram с end-to-end шифрованием. Доступ к данным только по мастер-паролю.

**🔥 Фичи:**

- 🔒 **Шифрование паролей** (AES-256/GCM).
- 🛡️ **Авторизация по мастер-паролю** (хэш via PBKDF2).
- 🎲 **Генератор паролей** (настройка длины, символов).
- ⏳ **Автовыход при бездействии** (таймаут сессии).
- 🧹 **Автоочистка истории сообщений** (удаление следов).
- 📦 **Локальное хранилище** (PostgreSQL + шифрование).

⚠️ **Важно**: Мастер-пароль не хранится на сервере. Если вы его забудете, данные не восстановить!

---

## 🛠 Технологии

- **Python 3.10+**
- `python-telegram-bot` (v20+)
- `SQLAlchemy` + `PostgreSQL`
- `cryptography` (AES, PBKDF2)
- `python-dotenv` (конфиги)
- `Docker`

---

## 🚀 Запуск

### Способ 1: локальный запуск

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/be3dna/tg_password_manager.git
   cd tg_password_manager
    ```
2. Установите зависимости:
    ```bash
    pip install -r requirements.txt
    ```
3. Настройте .env:
    ```ini
    TELEGRAM_TOKEN=YOUR TOKEN
    DATABASE_URL=driver://login:password@host/db
    
    POSTGRES_HOST=YOUR HOST NAME
    POSTGRES_USER=YOUR USER NAME
    POSTGRES_PASSWORD=YOUR PASSWORD
    POSTGRES_DB=YOUR DB NAME
    ```
4. Запустите бота:
    ```bash
    python src/main.py
   ```

### Способ 2: Docker-compose

1. настроить .env (пример выше)
2. запуск контейнеров
```shell
docker-compose up --build
```