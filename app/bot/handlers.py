import logging
import string

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton, ReplyKeyboardMarkup, \
    KeyboardButton
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, \
    filters

from app.config import SERVICES_PER_PAGE
from app.db.account import AccountDB
from app.dto.account import Account
from app.security.password_generator import generate
from app.security.security_utils import encrypt, decrypt

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

ACCOUNT_LIST_BUTTON_MESSAGE = "📋 список аккаунтов"
ADD_ACCOUNT_BUTTON_MESSAGE = "📥 добавить аккаунт"
BACK_BUTTON_MESSAGE = "↪ назад"
HOME_BUTTON_MESSAGE = "🏠 на главную"
NEW_PASSWORD_BUTTON_MESSAGE = "⚙ новый пароль"
EXIT_BUTTON_MESSAGE = "👋 Выйти"

# Словарь для хранения паролей
SERVICE_STATE, LOGIN_STATE, PASSWORD_STATE, CHOOSE_STATE, GENERATE_PASSWORD_SIZE, GENERATE_PASSWORD_ALPHABET = range(6)

_MAIN_MENU_MARKUP = ReplyKeyboardMarkup.from_row([
    KeyboardButton(ACCOUNT_LIST_BUTTON_MESSAGE),
    KeyboardButton(ADD_ACCOUNT_BUTTON_MESSAGE),
    KeyboardButton(NEW_PASSWORD_BUTTON_MESSAGE),
    KeyboardButton(EXIT_BUTTON_MESSAGE)
], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await auth_check(update, context)
    await update.message.reply_text(f'Привет! Используй /add для добавления пароля и /list для просмотра. {update.effective_user.id}')
    context.user_data["secret"] = "pass"
    await update.message.reply_text(
        f'Привет! Используй /add для добавления пароля и /list для просмотра. {update.effective_user.id}',
        reply_markup=_MAIN_MENU_MARKUP)

async def new_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await auth_check(update, context)
    reply_markup = ReplyKeyboardMarkup.from_row([
        KeyboardButton(HOME_BUTTON_MESSAGE)
    ], resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text('Введи название сервиса', reply_markup=reply_markup)
    return SERVICE_STATE

async def add_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    service_name = update.message.text
    context.user_data['service'] = service_name
    await update.message.reply_text(f'Введи логин для сервиса {service_name}')
    return LOGIN_STATE

async def add_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    service_login = update.message.text
    context.user_data['login'] = service_login
    await update.message.reply_text(f'Введи пароль для сервиса {context.user_data["service"]}')
    return PASSWORD_STATE

async def add_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    service = context.user_data['service']
    login = context.user_data['login']
    password = update.message.text
    password, salt = encrypt(password.encode(), context.user_data['secret'].encode())
    account = Account(user_id, service, login, password, salt)
    await AccountDB.save_account(account)
    await update.message.reply_text(f'Пароль для сервиса {service} был успешно сохранен')
    return ConversationHandler.END

async def list_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await auth_check(update, context)
    page = context.user_data.get('page')
    user_id = update.effective_user.id

    if page is None:
        context.user_data['page'] = 0
        services = await AccountDB.get_accounts(user_id=user_id)
        context.user_data['services'] = services[::]
    else:
        services = context.user_data['services']
        if update.callback_query.data == 'next_page':
            context.user_data['page'] += 1
        else:
            context.user_data['page'] -= 1

    page = context.user_data['page']

    if not services:
        await update.message.reply_text('Нет сохраненных паролей.')
        return ConversationHandler.END

    # Пагинация
    start = page * SERVICES_PER_PAGE
    end = start + SERVICES_PER_PAGE
    keyboard = []

    for service in services[start:end]:
        keyboard.append([InlineKeyboardButton(service, callback_data=f'service_{service}')])

    # Добавляем кнопки навигации
    if start > 0:
        keyboard.append([InlineKeyboardButton('Назад', callback_data='previous_page')])
    if end < len(services):
        keyboard.append([InlineKeyboardButton('Вперед', callback_data='next_page')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message is not None:
        message = update.message
    else:
        await update.callback_query.answer()
        message = update.callback_query.message
    await message.reply_text('Выберите сервис:', reply_markup=reply_markup)

    return CHOOSE_STATE


async def set_generator_password_size(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    return GENERATE_PASSWORD_ALPHABET


async def set_generator_password_alphabet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    return ConversationHandler.END

async def generate_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    alphabet = context.user_data.get("generator_password_alphabet")
    size = context.user_data.get("generator_password_size")
    if alphabet is None:
        alphabet = string.ascii_letters + string.digits + string.punctuation
    if size is None:
        size = 16

    password = generate(size, alphabet)

    copy_kb = InlineKeyboardMarkup([[InlineKeyboardButton('Копировать password', copy_text=CopyTextButton(password))]])
    await update.message.reply_text('Пароль сгенерирован!', reply_markup=copy_kb)

async def send_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    service = update.callback_query.data.split('_', 1)[1]
    account = await AccountDB.get_account(user_id=user_id, service=service)
    login = account.get_login()
    password = account.get_password()
    password = decrypt(password, context.user_data["secret"].encode(), account.get_password_salt())
    copy_kb = InlineKeyboardMarkup([[InlineKeyboardButton('Копировать login', copy_text=CopyTextButton(login))],
                                    [InlineKeyboardButton('Копировать password',
                                                          copy_text=CopyTextButton(password.decode()))]])
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(f'Ваш пароль от сервиса {service}.', reply_markup=copy_kb)
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    commands = {
        ACCOUNT_LIST_BUTTON_MESSAGE: list_services,
        ADD_ACCOUNT_BUTTON_MESSAGE: new_password,
        BACK_BUTTON_MESSAGE: None,
        HOME_BUTTON_MESSAGE: start,
        NEW_PASSWORD_BUTTON_MESSAGE: generate_password,
        EXIT_BUTTON_MESSAGE: None
    }

    command = commands.get(update.message.text)
    if command:
        await command(update, context)
    else:
        await update.message.reply_text("Неизвестная команда")


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['secret'] = "master"
    await update.message.reply_text("Login success!")


async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['secret'] = None
    await update.message.reply_text("Logout success!")


async def auth_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    while context.user_data.get('secret') is None:
        await login(update, context)

    # todo pass verification


new_password_handler = ConversationHandler(
    entry_points=[CommandHandler('add', new_password)],
    states={
        SERVICE_STATE: [MessageHandler(filters.TEXT, add_service)],
        LOGIN_STATE: [MessageHandler(filters.TEXT, add_login)],
        PASSWORD_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_password)]
    },
    fallbacks=[]
)

get_password_handler = ConversationHandler(
    entry_points=[CommandHandler('list', list_services)],
    states={
        CHOOSE_STATE: [
            CallbackQueryHandler(pattern='^previous_page$|^next_page$',callback=list_services),
            CallbackQueryHandler(pattern='^service_.+$', callback=send_password)
        ],
    },
    fallbacks=[]
)

generate_password_handler = ConversationHandler(
    entry_points=[CommandHandler('generate', generate_password)],
    states={
        GENERATE_PASSWORD_SIZE: [MessageHandler(filters.TEXT & filters.Regex(r"^\d+$"), set_generator_password_size)],
        GENERATE_PASSWORD_ALPHABET: [MessageHandler(filters.TEXT, set_generator_password_alphabet)]
    },
    fallbacks=[]
)
