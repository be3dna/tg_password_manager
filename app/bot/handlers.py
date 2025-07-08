import logging
import string
from random import Random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton, ReplyKeyboardMarkup, \
    KeyboardButton
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, \
    filters

from app.config import SERVICES_PER_PAGE
from app.db.account import AccountDB
from app.db.user import UserDB
from app.dto.account import Account
from app.dto.user import User
from app.security.password_generator import generate
from app.security.security_utils import encrypt, decrypt, get_hash

DEFAULT_GENERATION_SIZE = 16
DEFAULT_GENERATION_ALPHABET = string.ascii_letters + string.digits + string.punctuation

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

random = Random()
stickers = {
    "CHOOSE": [
        'CAACAgIAAxkBAAIECmhtJSy_oEXipnv9q6dvFR4PKkTOAAJ1AAOOiR49hHbdG_lTH_M2BA',
        'CAACAgIAAxkBAAID9WhtHVmV7VwOjhhIhYIUv_yXuvFcAALYAAOrV8QLErq7V-AW7ik2BA'
    ],
    "APPROVED": [
        "CAACAgIAAxkBAAIERWhtKi0dpM2pm5yEZdHbYFx8VZeXAAK5JgACuOERSNjm4ZIjUtqYNgQ",
        "CAACAgIAAxkBAAIESWhtKqwYrdE4Zdo4MWPTF5vH98KaAAKbTgACHAmJSPXVOEFqJBLxNgQ",
        "CAACAgEAAxkBAAIETWhtK0lc8Oby3Ot8gUQEnvRgAk_gAAICAAN_cEYcBcxk2DciK8g2BA"
    ],
    "DENIED": [
        "CAACAgIAAxkBAAIER2htKk1CTCFqiGX0kWUyTi3Ksfy7AAI4JAACutcQSJqfkfiyfw9gNgQ",
        "CAACAgIAAxkBAAIES2htKsG_HkqMr5DOxyaiaWwhGQ40AAKbRwACu0tYSNiEJY1aPU7WNgQ",
        "CAACAgEAAxkBAAIET2htK0tL4PDuIiUVdvXhQOIQXgABwgACAwADf3BGHENZiEtY50bNNgQ"
    ],
    "SUCCESS": [
        "CAACAgIAAxkBAAIESWhtKqwYrdE4Zdo4MWPTF5vH98KaAAKbTgACHAmJSPXVOEFqJBLxNgQ"
    ]
}

ACCOUNT_LIST_BUTTON_MESSAGE = "📋 список аккаунтов"
ADD_ACCOUNT_BUTTON_MESSAGE = "📥 добавить аккаунт"
DELETE_ACCOUNT_BUTTON_MESSAGE = "❌ удалить аккаунт"
SETTINGS_BUTTON_MESSAGE = "🛠 настройки"
BACK_BUTTON_MESSAGE = "↪ назад"
HOME_BUTTON_MESSAGE = "🏠 на главную"
GENERATE_BUTTON_MESSAGE = "⚙ сгенерировать пароль"
EXIT_BUTTON_MESSAGE = "👋 Выйти"
LOGIN_BUTTON_MESSAGE = "🔑 Войти"

# Словарь для хранения паролей
(UNAUTHED_STATE, LOGIN_STATE, SIGN_UP_STATE, PASSWORD_VERIFICATION_STATE, CMD_STATE,
 INPUT_SERVICE_STATE, INPUT_LOGIN_STATE, INPUT_PASSWORD_STATE,
 CHOOSE_STATE, CHOOSE_DELETING_STATE, CONFIRM_DELETE_STATE,
 GENERATE_PASSWORD_SIZE_STATE, GENERATE_PASSWORD_ALPHABET_STATE,
 GENERATE_PASSWORD_MANUAL_ALPHABET_STATE, DEAD_END) = range(15)

_START_MENU_MARKUP = ReplyKeyboardMarkup.from_row([
    KeyboardButton(LOGIN_BUTTON_MESSAGE),
    KeyboardButton(GENERATE_BUTTON_MESSAGE)
], resize_keyboard=True, one_time_keyboard=True)
_MAIN_MENU_MARKUP = ReplyKeyboardMarkup([
    [KeyboardButton(ACCOUNT_LIST_BUTTON_MESSAGE), KeyboardButton(GENERATE_BUTTON_MESSAGE)],
    [KeyboardButton(ADD_ACCOUNT_BUTTON_MESSAGE), KeyboardButton(DELETE_ACCOUNT_BUTTON_MESSAGE)],
    [KeyboardButton(SETTINGS_BUTTON_MESSAGE), KeyboardButton(EXIT_BUTTON_MESSAGE)]
], resize_keyboard=True, one_time_keyboard=True)

_HOME_AND_BACK_BUTTONS_MARKUP = ReplyKeyboardMarkup.from_row([
    KeyboardButton(BACK_BUTTON_MESSAGE),
    KeyboardButton(HOME_BUTTON_MESSAGE)
], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("handled: start")
    if await auth_check(update, context):
        return CMD_STATE
        return await main_menu(update, context)

    await update.message.reply_text(
        "Добро пожаловать! Введите:" +
        "\n\t /login - для входа" +
        "\n\t /generate - для начала диалога генерации пароля" +
        "\n\t /generate <size> - для генерации пароля указанной длинны", reply_markup=_START_MENU_MARKUP)
    return UNAUTHED_STATE


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("handled: login")
    user_id = update.effective_user.id
    user = await UserDB.get_user(user_id=user_id)

    if user is None:
        return await sign_up(update, context)

    await update.message.reply_text("Введите мастер пароль:")
    return PASSWORD_VERIFICATION_STATE


async def sign_up(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Данного аккаунта нет в базе денных.\n Необходимо придумать мастер пароль (не менее 8 символов):")
    return SIGN_UP_STATE


async def set_user_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = update.message.text
    if len(data) < 8 or data.__contains__(' '):
        await update.message.reply_text("Пароль не может содержать менее 8 символов, пробелы итд.")
        return await sign_up(update, context)

    _hash, salt = get_hash(data.encode())
    user = User(update.effective_user.id, _hash, salt)
    await UserDB.add_user(user=user)
    await show_stickers_of_placeholder(context, update.message, "SUCCESS", placeholder="Пароль успешно сохранен!")
    return await login(update, context)

async def verify_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("handled: verify_password")

    if update.message.text is not None:
        context.user_data['secret'] = update.message.text

    return await is_authorized(update, context)


async def is_authorized(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("handled: is_authorized")

    if not await auth_check(update, context):
        return await start(update, context)

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

    password = context.user_data['secret']
    user_id = update.effective_user.id
    user = await UserDB.get_user(user_id)

    _hash, _ = get_hash(password.encode(), user.get_password_hash_salt())

    return user.get_password_hash() == _hash


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("handled: main_menu")
    if not await auth_check(update, context):
        logging.info("auth_check is false")
        return UNAUTHED_STATE
    await update.message.reply_text(
        'Привет! Используй /add для добавления пароля, /list для просмотра, а /del - для удаления!',
        reply_markup=_MAIN_MENU_MARKUP)
    return CMD_STATE


async def toggle_stickers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('is_stickers_active') is None:
        context.user_data['is_stickers_active'] = True
    else:
        context.user_data['is_stickers_active'] = not context.user_data['is_stickers_active']


async def show_stickers_of_placeholder(context, message, stickers_type, reply_markup=None,
                                       placeholder="^----------------------------------^"):
    if context.user_data.get('is_stickers_active') is not None and context.user_data['is_stickers_active']:
        choose_stickers = stickers.get(stickers_type)
        await message.reply_sticker(random.choice(choose_stickers), reply_markup=reply_markup)
    else:
        await message.reply_text(placeholder, reply_markup=reply_markup)


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

    await update.message.reply_text(f'Введи логин для сервиса {service_name}')
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

    await show_stickers_of_placeholder(context, update.callback_query.message, "SUCCESS", _HOME_AND_BACK_BUTTONS_MARKUP,
                                       "🎉🎉🎉")
    return DEAD_END

async def add_generated_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    service = context.user_data['service']
    login = context.user_data['login']
    password = generate(DEFAULT_GENERATION_SIZE, DEFAULT_GENERATION_ALPHABET)
    encrypted_password, salt = encrypt(password.encode(), context.user_data['secret'].encode())
    account = Account(user_id, service, login, encrypted_password, salt)

    copy_password_kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text='Скопировать', copy_text=CopyTextButton(password))]]
    )

    await AccountDB.save_account(account)
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(f'Пароль для сервиса {service} был успешно сгенерирован',
                                                   reply_markup=copy_password_kb)
    return CMD_STATE

    await show_stickers_of_placeholder(context, update.callback_query.message, "SUCCESS", _HOME_AND_BACK_BUTTONS_MARKUP,
                                       "🎉🎉🎉")

    return DEAD_END


# list
async def list_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    if not await auth_check(update, context):
        return UNAUTHED_STATE
        return await start(update, context)

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

        return await main_menu(update, context)

    # Пагинация
    start_indx = page * SERVICES_PER_PAGE
    end_indx = start_indx + SERVICES_PER_PAGE
    keyboard = []

    for service in services[start_indx:end_indx]:
        keyboard.append([InlineKeyboardButton(service, callback_data=f'service_{service}')])

    # Добавляем кнопки навигации
    if start_indx > 0:
        keyboard.append([InlineKeyboardButton('Назад', callback_data='previous_page')])
    if end_indx < len(services):
        keyboard.append([InlineKeyboardButton('Вперед', callback_data='next_page')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message is not None:
        message = update.message
    else:
        await update.callback_query.answer()
        message = update.callback_query.message
    await message.reply_text('Выберите сервис:', reply_markup=reply_markup)

    await show_stickers_of_placeholder(context, message, "CHOOSE", _HOME_AND_BACK_BUTTONS_MARKUP)

    return CHOOSE_STATE


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
    return DEAD_END


# generate

async def generation_dialog_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await ask_password_size(update, context)

async def ask_password_size(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите желаемую длину пароля:", reply_markup=_GENERATION_BUTTONS_MARKUP)
    await update.message.reply_text("Введите желаемую длину пароля:", reply_markup=_HOME_AND_BACK_BUTTONS_MARKUP)
    return GENERATE_PASSWORD_SIZE_STATE

async def set_generator_password_size(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    size = int(update.message.text)
    if not size:
        return await ask_password_size(update, context)

    context.user_data['generator_password_size'] = size

    return await ask_password_alphabet(update, context)

def get_or_default(context: ContextTypes.DEFAULT_TYPE, name: str, default=True):
    if context.user_data.get(name) is None:
        context.user_data[name] = default
        return default

    return context.user_data[name]

async def ask_password_alphabet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    alphabet_high = get_or_default(context, 'generator_password_alphabet_high')
    alphabet_low = get_or_default(context, 'generator_password_alphabet_low')
    alphabet_numb = get_or_default(context, 'generator_password_alphabet_numb')
    alphabet_spec = get_or_default(context, 'generator_password_alphabet_spec')

    if update.callback_query is not None:
        query = update.callback_query.data.split("_")[1]
        if query == "high":
            alphabet_high = not alphabet_high
            context.user_data['generator_password_alphabet_high'] = alphabet_high
        elif query == "low":
            alphabet_low = not alphabet_low
            context.user_data['generator_password_alphabet_low'] = alphabet_low
        elif query == "numb":
            alphabet_numb = not alphabet_numb
            context.user_data['generator_password_alphabet_numb'] = alphabet_numb
        elif query == "spec":
            alphabet_spec = not alphabet_spec
            context.user_data['generator_password_alphabet_spec'] = alphabet_spec

    high_message = ("✅" if alphabet_high else "❌") + " high letters"
    low_message = ("✅" if alphabet_low else "❌") + " low letters"
    numb_message = ("✅" if alphabet_numb else "❌") + " numbers letters"
    spec_message = ("✅" if alphabet_spec else "❌") + " special symbols"

    alphabet_checkboxes_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(high_message, callback_data="toggle_high")],
        [InlineKeyboardButton(low_message, callback_data="toggle_low")],
        [InlineKeyboardButton(numb_message, callback_data="toggle_numb")],
        [InlineKeyboardButton(spec_message, callback_data="toggle_spec")],
        [
            InlineKeyboardButton("Ввести в ручную", callback_data="manual_mode"),
            InlineKeyboardButton("Подтвердить", callback_data="alphabet_approve")
        ]
    ])
    if update.message is not None:
        message = update.message
    else:
        await update.callback_query.answer()
        message = update.callback_query.message
    await message.reply_text(
        "Выберите символы, участвующие в генерации:",
        reply_markup=alphabet_checkboxes_markup)

    return GENERATE_PASSWORD_ALPHABET_STATE

async def set_generator_password_alphabet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    alphabet_high = context.user_data['generator_password_alphabet_high']
    alphabet_low = context.user_data['generator_password_alphabet_low']
    alphabet_numb = context.user_data['generator_password_alphabet_numb']
    alphabet_spec = context.user_data['generator_password_alphabet_spec']

    alphabet = ''
    if alphabet_high: alphabet += string.ascii_uppercase
    if alphabet_low: alphabet += string.ascii_lowercase
    if alphabet_numb: alphabet += string.digits
    if alphabet_spec: alphabet += string.punctuation

    context.user_data['generator_password_alphabet'] = alphabet
    return await generate_password(update, context)

async def ask_password_alphabet_manual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите строку символов, которые будут использоваться при создании пароля:")
    return GENERATE_PASSWORD_MANUAL_ALPHABET_STATE

async def set_generator_password_alphabet_manual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    alphabet = update.message.text

    if alphabet is None or len(alphabet) < 1:
        return await ask_password_alphabet_manual(update, context)

    context.user_data['generator_password_alphabet'] = alphabet
    return await generate_password(update, context)

async def generate_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    alphabet = context.user_data.get("generator_password_alphabet")
    size = context.user_data.get("generator_password_size")
    if alphabet is None:
        alphabet = string.ascii_letters + string.digits + string.punctuation
    if size is None:
        size = 16

    password = generate(size, alphabet)

    if update.message is not None:
        message = update.message
    else:
        await update.callback_query.answer()
        message = update.callback_query.message

    copy_kb = InlineKeyboardMarkup([[InlineKeyboardButton('Копировать password', copy_text=CopyTextButton(password))]])
    await message.reply_text('Пароль сгенерирован!', reply_markup=copy_kb)

    return GENERATE_PASSWORD

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
    return DEAD_END


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
        return await main_menu(update, context)

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

    await show_stickers_of_placeholder(context, message, "CHOOSE", _HOME_AND_BACK_BUTTONS_MARKUP)

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
    await update.callback_query.message.reply_text(f'Пароль для сервиса {service} был удален',
                                                   reply_markup=_HOME_AND_BACK_BUTTONS_MARKUP)
    return DEAD_END

async def cancel_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text('Удаление было отменено', reply_markup=_HOME_AND_BACK_BUTTONS_MARKUP)
    return DEAD_END


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


async def get_sticker_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    file_id = update.message.sticker.file_id
    message = f"Sticker's file id: {file_id}"
    logging.info(message)

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
        SIGN_UP_STATE: [
            CommandHandler('home', is_authorized),
            MessageHandler(filters.TEXT & filters.Text([HOME_BUTTON_MESSAGE]), is_authorized),
            MessageHandler(filters.TEXT & filters.Text([BACK_BUTTON_MESSAGE]), is_authorized),

            MessageHandler(filters.TEXT & ~filters.COMMAND, set_user_password)

        ],
        CMD_STATE: [
            CommandHandler('add', new_password),
            MessageHandler(filters.TEXT & filters.Text([ADD_ACCOUNT_BUTTON_MESSAGE]), new_password),

            CommandHandler('list', list_services),
            MessageHandler(filters.TEXT & filters.Text([ACCOUNT_LIST_BUTTON_MESSAGE]), list_services),

            CommandHandler('del', delete_service),
            MessageHandler(filters.TEXT & filters.Text([DELETE_ACCOUNT_BUTTON_MESSAGE]), delete_service),

            CommandHandler('generate', generation_dialog_start),
            MessageHandler(filters.TEXT & filters.Text([GENERATE_BUTTON_MESSAGE]), generation_dialog_start),

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
            CommandHandler('home', is_authorized),
            MessageHandler(filters.TEXT & filters.Text([HOME_BUTTON_MESSAGE]), is_authorized),
            MessageHandler(filters.TEXT & filters.Text([BACK_BUTTON_MESSAGE]), is_authorized),

            CallbackQueryHandler(pattern='^previous_page$|^next_page$', callback=list_services),
            CallbackQueryHandler(pattern='^service_.+$', callback=send_password)
        ],
        CHOOSE_DELETING_STATE: [
            CommandHandler('home', is_authorized),
            MessageHandler(filters.TEXT & filters.Text([HOME_BUTTON_MESSAGE]), is_authorized),
            MessageHandler(filters.TEXT & filters.Text([BACK_BUTTON_MESSAGE]), is_authorized),

            CallbackQueryHandler(pattern='^previous_page$|^next_page$', callback=delete_service),
            CallbackQueryHandler(pattern='^del_service_.+$', callback=delete_password)
        ],
        CONFIRM_DELETE_STATE: [
            CommandHandler('home', is_authorized),
            MessageHandler(filters.TEXT & filters.Text([HOME_BUTTON_MESSAGE]), is_authorized),
            MessageHandler(filters.TEXT & filters.Text([BACK_BUTTON_MESSAGE]), delete_service),

            CallbackQueryHandler(pattern='^confirm_delete$', callback=confirm_delete),
            CallbackQueryHandler(pattern='^cancel_delete$', callback=cancel_delete)
        ],
        GENERATE_PASSWORD_SIZE_STATE: [
            CommandHandler('home', is_authorized),
            MessageHandler(filters.TEXT & filters.Text([HOME_BUTTON_MESSAGE]), is_authorized),
            MessageHandler(filters.TEXT & filters.Text([BACK_BUTTON_MESSAGE]), is_authorized),

            MessageHandler(filters.TEXT & filters.Regex(r"^\d+$"), set_generator_password_size),
            MessageHandler(filters.ALL, ask_password_size)
        ],
        GENERATE_PASSWORD_ALPHABET_STATE: [
            CommandHandler('home', is_authorized),
            MessageHandler(filters.TEXT & filters.Text([HOME_BUTTON_MESSAGE]), is_authorized),
            MessageHandler(filters.TEXT & filters.Text([BACK_BUTTON_MESSAGE]), ask_password_size),

            CallbackQueryHandler(pattern='^alphabet_approve$', callback=set_generator_password_alphabet),
            CallbackQueryHandler(pattern='^manual_mode$', callback=ask_password_alphabet_manual),
            CallbackQueryHandler(pattern='^toggle_.+$', callback=ask_password_alphabet)
        ],
        GENERATE_PASSWORD_MANUAL_ALPHABET_STATE: [
            CommandHandler('home', is_authorized),
            MessageHandler(filters.TEXT & filters.Text([HOME_BUTTON_MESSAGE]), is_authorized),
            MessageHandler(filters.TEXT & filters.Text([BACK_BUTTON_MESSAGE]), ask_password_alphabet),

            MessageHandler(filters.TEXT, set_generator_password_alphabet_manual)
        ],
        DEAD_END: [
            CommandHandler('home', is_authorized),
            MessageHandler(filters.TEXT & filters.Text([HOME_BUTTON_MESSAGE]), is_authorized)
        ]
    },
    fallbacks=[],
    conversation_timeout=5
)