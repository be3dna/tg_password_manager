import logging
import string

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton, ReplyKeyboardMarkup, \
    KeyboardButton
from telegram.ext import ContextTypes

from app.db.repository import Account, Repository, InMemoryRepository, User
from app.security.password_generator import generate
from app.security.security_utils import encrypt, decrypt, get_hash

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Словарь для хранения паролей
services_per_page = 5
repository: Repository = InMemoryRepository()
_MAIN_MENU_MARKUP = ReplyKeyboardMarkup.from_row([
    KeyboardButton("📋 список аккаунтов"),
    KeyboardButton("📥 добавить аккаунт"),
    KeyboardButton("⚙ новый пароль"),
    KeyboardButton("👋 Выйти")
], resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Привет! Используй /add для добавления пароля и /list для просмотра. {update.effective_user.id}')
    context.user_data["secret"] = "pass"
    await update.message.reply_text(
        f'Привет! Используй /add для добавления пароля и /list для просмотра. {update.effective_user.id}',
        reply_markup=_MAIN_MENU_MARKUP)

async def add_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_markup = ReplyKeyboardMarkup.from_row([
        KeyboardButton("🏠 на главную")
    ], resize_keyboard=True, one_time_keyboard=True)

    if (context.args is None) or (len(context.args) < 2):
        await update.message.reply_text('Используйте: /add <сервис> <login> <пароль>', reply_markup=reply_markup)
        return

    user_id = update.effective_user.id
    service = context.args[0]
    login = context.args[1]
    password = context.args[2]

    password, password_salt = encrypt(password.encode(), context.user_data["secret"].encode())

    await repository.save_account(Account(user_id, service, login, password, password_salt))
    await update.message.reply_text(f'Пароль для {service} добавлен!', reply_markup=_MAIN_MENU_MARKUP)

async def list_passwords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = await repository.get_accounts(update.effective_user.id)
    if not services:
        await update.message.reply_text('Нет сохраненных паролей.')
        return

    # Пагинация
    page = int(context.args[0]) if context.args and context.args[0].isdigit() else 0
    start = page * services_per_page
    end = start + services_per_page
    keyboard = []

    for service in services[start:end]:
        keyboard.append([InlineKeyboardButton(service, callback_data=service)])

    # Добавляем кнопки навигации
    if start > 0:
        keyboard.append([InlineKeyboardButton('Назад', callback_data=f'page_{page - 1}')])
    if end < len(services):
        keyboard.append([InlineKeyboardButton('Вперед', callback_data=f'page_{page + 1}')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите сервис:', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data.startswith('page_'):
        page = int(query.data.split('_')[1])
        await list_passwords(query, context)

    else:
        service = query.data
        await send_password(query, service, context)


async def generate_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    alphabet = string.ascii_letters + string.digits + string.punctuation

    password = generate(16, alphabet)

    copy_kb = InlineKeyboardMarkup([[InlineKeyboardButton('Копировать password', copy_text=CopyTextButton(password))]])
    await update.message.reply_text('Пароль сгенерирован!', reply_markup=copy_kb)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    commands = {
        "📋 список аккаунтов": list_passwords,
        "📥 добавить аккаунт": add_password,
        "↪ назад": None,
        "🏠 на главную": start,
        "⚙ новый пароль": generate_password,
        "👋 Выйти": logout
    }

    command = commands.get(update.message.text)
    if command:
        await command(update, context)
    else:
        await context.message.reply_text("Неизвестная команда")


async def send_password(update: Update, service: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    account = await repository.get_account(update.from_user.id, service)
    login = account.get_login()
    password = decrypt(account.get_password(), context.user_data["secret"].encode(), account.get_password_salt())
    copy_kb = InlineKeyboardMarkup([[InlineKeyboardButton('Копировать login', copy_text=CopyTextButton(login))],
                                    [InlineKeyboardButton('Копировать password',
                                                          copy_text=CopyTextButton(password.decode()))]])
    await update.message.reply_text(f'Ваш пароль от сервиса {service}.', reply_markup=copy_kb)