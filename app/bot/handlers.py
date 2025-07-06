import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from app.config import SERVICES_PER_PAGE
from app.db.password import PasswordDB

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Словарь для хранения паролей
passwords = {'github': '1234', 'b': '1234', 'c': '1234', 'd': '1234', 'e': '1234', 'f': '1234'}

SERVICE_STATE, PASSWORD_STATE, CHOOSE_STATE = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Привет! Используй /add для добавления пароля и /list для просмотра. {update.effective_user.id}')


async def new_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Введи название сервиса')
    return SERVICE_STATE


async def add_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    service_name = update.message.text
    context.user_data['service'] = service_name
    await update.message.reply_text(f'Введи пароль для сервиса {service_name}')
    return PASSWORD_STATE


async def add_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    service = context.user_data['service']
    password = update.message.text
    user_id = update.effective_user.id
    await PasswordDB.add_password(service=service, password=password, user_id=user_id)
    await update.message.reply_text(f'Пароль для сервиса {service} был успешно сохранен')
    return ConversationHandler.END


async def list_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    page = context.user_data.get('page')
    user_id = update.effective_user.id
    
    if page is None:
        context.user_data['page'] = 0
        services = await PasswordDB.get_user_services(user_id=user_id)
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


async def send_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    service = update.callback_query.data.split('_', 1)[1]
    password = await PasswordDB.get_password(user_id=user_id, service=service)
    copy_kb = InlineKeyboardMarkup([[InlineKeyboardButton('Копировать', copy_text=CopyTextButton(password))]])
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(f'Ваш пароль от сервиса {service}.', reply_markup=copy_kb)
    return ConversationHandler.END


new_password_handler = ConversationHandler(
    entry_points=[CommandHandler('add', new_password)],
    states={
        SERVICE_STATE: [MessageHandler(filters.TEXT, add_service)],
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