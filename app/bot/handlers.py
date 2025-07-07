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

DEFAULT_GENERATION_SIZE = 16
DEFAULT_GENERATION_ALPHABET = string.ascii_letters + string.digits + string.punctuation

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

ACCOUNT_LIST_BUTTON_MESSAGE = "📋 список аккаунтов"
ADD_ACCOUNT_BUTTON_MESSAGE = "📥 добавить аккаунт"
DELETE_ACCOUNT_BUTTON_MESSAGE = "❌ удалить аккаунт"
BACK_BUTTON_MESSAGE = "↪ назад"
HOME_BUTTON_MESSAGE = "🏠 на главную"
GENERATE_BUTTON_MESSAGE = "⚙ сгенерировать пароль"
EXIT_BUTTON_MESSAGE = "👋 Выйти"
LOGIN_BUTTON_MESSAGE = "🔑 Войти"

# Словарь для хранения паролей
(UNAUTHED_STATE, LOGIN_STATE, PASSWORD_VERIFICATION_STATE, CMD_STATE,
 INPUT_SERVICE_STATE, INPUT_LOGIN_STATE, INPUT_PASSWORD_STATE,
 CHOOSE_STATE, CHOOSE_DELETING_STATE, CONFIRM_DELETE_STATE,
 GENERATE_PASSWORD_SIZE_STATE, GENERATE_PASSWORD_ALPHABET_STATE, GENERATE_PASSWORD) = range(13)

_START_MENU_MARKUP = ReplyKeyboardMarkup.from_row([
    KeyboardButton(LOGIN_BUTTON_MESSAGE),
    KeyboardButton(GENERATE_BUTTON_MESSAGE)
])
_MAIN_MENU_MARKUP = ReplyKeyboardMarkup.from_row([
    KeyboardButton(ACCOUNT_LIST_BUTTON_MESSAGE),
    KeyboardButton(ADD_ACCOUNT_BUTTON_MESSAGE),
    KeyboardButton(GENERATE_BUTTON_MESSAGE),
    KeyboardButton(EXIT_BUTTON_MESSAGE)
], resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("handled: start")
    if await auth_check(update, context):
        return CMD_STATE

    await update.message.reply_text(
        "Добро пожаловать! Введите:" +
        "\n\t /login - для входа" +
        "\n\t /generate - для начала диалога генерации пароля" +
        "\n\t /generate <size> - для генерации пароля указанной длинны", reply_markup=_START_MENU_MARKUP)
    return UNAUTHED_STATE


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("handled: login")
    await update.message.reply_text("Введите мастер пароль:")
    return PASSWORD_VERIFICATION_STATE


async def verify_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("handled: verify_password")

    if update.message.text is not None:
        #todo context.user_data['secret'] = update.message.text
        context.user_data['secret'] = "master"

    if not await auth_check(update, context):
        return await start(update, context)

    await update.message.reply_text("Login success!")
    return await main_menu(update, context)


async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("handled: logout")
    del (context.user_data['secret'])
    logging.info(f"Logout state: {context.user_data.get('secret')}")
    await update.message.reply_text("Logout success!")
    return await start(update, context)


async def auth_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    logging.info("handled: auth_check")
    if context.user_data.get('secret') is None:
        return False
    # todo pass verification
    return True


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("handled: main_menu")
    if not await auth_check(update, context):
        logging.info("auth_check is false")
        return UNAUTHED_STATE
    await update.message.reply_text(
        'Привет! Используй /add для добавления пароля, /list для просмотра, а /del - для удаления!',
        reply_markup=_MAIN_MENU_MARKUP)
    return CMD_STATE


# add
async def new_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await auth_check(update, context):
        return UNAUTHED_STATE
    reply_markup = ReplyKeyboardMarkup.from_row([
        KeyboardButton(HOME_BUTTON_MESSAGE)
    ], resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text('Введи название сервиса', reply_markup=reply_markup)
    return INPUT_SERVICE_STATE

async def add_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    service_name = update.message.text
    user_id = update.effective_user.id

    account = await AccountDB.get_account(user_id=user_id, service=service_name)
    if account is not None:
        await update.message.reply_text(f'Пароль для сервиса {service_name} уже добавлен')
        return CMD_STATE

    context.user_data['service'] = service_name

    generate_password_kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text='Сгенерировать', callback_data='generate_password')]]
    )
    await update.message.reply_text(f'Введи логин для сервиса {service_name}', reply_markup=generate_password_kb)
    return INPUT_LOGIN_STATE

async def add_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    service_login = update.message.text
    context.user_data['login'] = service_login
    generate_password_kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text='Сгенерировать', callback_data='generate_password')]]
    )
    await update.message.reply_text(f'Введи пароль для сервиса {context.user_data["service"]}',
                                    reply_markup=generate_password_kb)
    return INPUT_PASSWORD_STATE

async def add_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    service = context.user_data['service']
    login = context.user_data['login']
    password = update.message.text
    password, salt = encrypt(password.encode(), context.user_data['secret'].encode())
    account = Account(user_id, service, login, password, salt)

    await AccountDB.save_account(account)
    await update.message.reply_text(f'Пароль для сервиса {service} был успешно сохранен')
    return CMD_STATE

async def add_generated_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    service = context.user_data['service']
    login = context.user_data['login']
    password = generate(DEFAULT_GENERATION_SIZE, DEFAULT_GENERATION_ALPHABET)
    encrypted_password, salt = encrypt(password.encode(), context.user_data['secret'].encode())
    account = Account(user_id, service, login, encrypted_password, salt)

    copy_password_kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text='Скопировать', copy_text=password)]]
    )

    await AccountDB.save_account(account)
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(f'Пароль для сервиса {service} был успешно сгенерирован',
                                                   reply_markup=copy_password_kb)
    return CMD_STATE


# list
async def list_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    if not await auth_check(update, context):
        return UNAUTHED_STATE
    user_id = update.effective_user.id

    if update.callback_query is None:
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
        return CMD_STATE

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


# generate

async def generation_dialog_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите желаемую длину пароля:")
    return GENERATE_PASSWORD_SIZE_STATE

async def set_generator_password_size(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # todo save size
    await update.message.reply_text(
        "выберите символы, участвующие в генерации:")  # todo добавить кнопку подтверждения и кнопки чекбоксов
    return GENERATE_PASSWORD_ALPHABET_STATE

async def set_generator_password_alphabet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # todo save alphabet
    return await generate_password(update, context)


async def generate_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    alphabet = context.user_data.get("generator_password_alphabet")
    size = context.user_data.get("generator_password_size")
    if alphabet is None:
        alphabet = string.ascii_letters + string.digits + string.punctuation
    if size is None:
        size = 16

    password = generate(size, alphabet)

    copy_kb = InlineKeyboardMarkup([[InlineKeyboardButton('Копировать password', copy_text=CopyTextButton(password))]])
    await update.message.reply_text('Пароль сгенерирован!', reply_markup=copy_kb)
    return PASSWORD_VERIFICATION_STATE

async def send_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    del (context.user_data['page'])
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
    return CMD_STATE


# delete
async def delete_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id

    if update.callback_query is None:
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
        return CMD_STATE

    # Пагинация
    start = page * SERVICES_PER_PAGE
    end = start + SERVICES_PER_PAGE
    keyboard = []

    for service in services[start:end]:
        keyboard.append([InlineKeyboardButton(service, callback_data=f'del_service_{service}')])

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

    return CHOOSE_DELETING_STATE

async def delete_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    service = update.callback_query.data.split('_', 2)[2]
    context.user_data['service_to_delete'] = service
    delete_kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton('Удалить', callback_data='confirm_delete')],
            [InlineKeyboardButton('Отменить', callback_data='cancel_delete')]
        ]
    )
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(f'Удалить запись для сервиса {service}?', reply_markup=delete_kb)
    return CONFIRM_DELETE_STATE


async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    service = context.user_data['service_to_delete']
    await AccountDB.delete_account(user_id=user_id, service=service)
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(f'Пароль для сервиса {service} был удален')
    return CMD_STATE


async def cancel_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text('Удаление было отменено')
    return CMD_STATE


##
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    commands = {
        ACCOUNT_LIST_BUTTON_MESSAGE: list_services,
        ADD_ACCOUNT_BUTTON_MESSAGE: new_password,
        BACK_BUTTON_MESSAGE: None,
        HOME_BUTTON_MESSAGE: start,
        GENERATE_BUTTON_MESSAGE: generate_password,
        EXIT_BUTTON_MESSAGE: None
    }

    command = commands.get(update.message.text)
    if command:
        await command(update, context)
    else:
        await update.message.reply_text("Неизвестная команда")



conversation_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        UNAUTHED_STATE: [
            CommandHandler('login', login),
            MessageHandler(filters.TEXT & filters.Text([LOGIN_BUTTON_MESSAGE]), login),

            CommandHandler('generate', generation_dialog_start),
            MessageHandler(filters.TEXT & filters.Text([GENERATE_BUTTON_MESSAGE]), generation_dialog_start),
        ],
        PASSWORD_VERIFICATION_STATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, verify_password)
        ],
        CMD_STATE: [
            CommandHandler('add', new_password),
            MessageHandler(filters.TEXT & filters.Text([ADD_ACCOUNT_BUTTON_MESSAGE]), new_password),

            CommandHandler('list', list_services),
            MessageHandler(filters.TEXT & filters.Text([ACCOUNT_LIST_BUTTON_MESSAGE]), new_password),

            CommandHandler('del', delete_service),
            MessageHandler(filters.TEXT & filters.Text([DELETE_ACCOUNT_BUTTON_MESSAGE]), new_password),

            CommandHandler('generate', generate_password),
            MessageHandler(filters.TEXT & filters.Text([GENERATE_BUTTON_MESSAGE]), generate_password),

            CommandHandler('logout', logout),
            MessageHandler(filters.TEXT & filters.Text([EXIT_BUTTON_MESSAGE]), logout)
        ],
        INPUT_SERVICE_STATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_service)
        ],
        INPUT_LOGIN_STATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_login)
        ],
        INPUT_PASSWORD_STATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_password),
            CallbackQueryHandler(pattern='^generate_password$', callback=add_generated_password)
        ],
        CHOOSE_STATE: [
            CallbackQueryHandler(pattern='^previous_page$|^next_page$', callback=list_services),
            CallbackQueryHandler(pattern='^service_.+$', callback=send_password)
        ],
        CHOOSE_DELETING_STATE: [
            CallbackQueryHandler(pattern='^previous_page$|^next_page$', callback=delete_service),
            CallbackQueryHandler(pattern='^del_service_.+$', callback=delete_password)
        ],
        CONFIRM_DELETE_STATE: [
            CallbackQueryHandler(pattern='^confirm_delete$', callback=confirm_delete),
            CallbackQueryHandler(pattern='^cancel_delete$', callback=cancel_delete)
        ],
        GENERATE_PASSWORD_SIZE_STATE: [
            MessageHandler(filters.TEXT & filters.Regex(r"^\d+$"), set_generator_password_size)
        ],
        GENERATE_PASSWORD_ALPHABET_STATE: [
            MessageHandler(filters.TEXT, set_generator_password_alphabet)
        ],
        GENERATE_PASSWORD: [

        ]
    },
    fallbacks=[]
)