import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from app.config import SERVICES_PER_PAGE
from app.db.password import PasswordDB
from app.utils import generate_password

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


CMD_STATE, SERVICE_STATE, PASSWORD_STATE, CHOOSE_STATE, CHOOSE_DELETING_STATE, CONFIRM_DELETE_STATE = range(6)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(f'Привет! Используй /add для добавления пароля, /list для просмотра, а /del - для удаления!')
    return CMD_STATE


async def new_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Введи название сервиса')
    return SERVICE_STATE


async def add_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    service_name = update.message.text
    user_id = update.effective_user.id
    
    password = await PasswordDB.get_password(user_id=user_id, service=service_name)
    if password is not None:
        await update.message.reply_text(f'Пароль для сервиса {service_name} уже добавлен')
        return CMD_STATE
    
    context.user_data['service'] = service_name
    generate_password_kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text='Сгенерировать', callback_data='generate_password')]]
    )
    await update.message.reply_text(f'Введи пароль для сервиса {service_name}', reply_markup=generate_password_kb)
    return PASSWORD_STATE


async def add_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    service = context.user_data['service']
    password = update.message.text
    user_id = update.effective_user.id
    await PasswordDB.add_password(service=service, password=password, user_id=user_id)
    await update.message.reply_text(f'Пароль для сервиса {service} был успешно сохранен')
    return CMD_STATE


async def add_generated_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    service = context.user_data['service']
    user_id = update.effective_user.id
    password = generate_password()
    await PasswordDB.add_password(service=service, password=password, user_id=user_id)
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(f'Пароль для сервиса {service} был успешно сгенерирован')
    return CMD_STATE


async def list_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    user_id = update.effective_user.id
    
    if update.callback_query is None:
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


async def send_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del(context.user_data['page'])
    user_id = update.effective_user.id
    service = update.callback_query.data.split('_', 1)[1]
    password = await PasswordDB.get_password(user_id=user_id, service=service)
    copy_kb = InlineKeyboardMarkup([[InlineKeyboardButton('Копировать', copy_text=CopyTextButton(password))]])
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(f'Ваш пароль от сервиса {service}.', reply_markup=copy_kb)
    return CMD_STATE


async def delete_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id

    if update.callback_query is None:
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
    await PasswordDB.delete_password(user_id=user_id, service=service)
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(f'Парооль для сервиса {service} был удален')
    return CMD_STATE


async def cancel_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(f'Удаление было отменено')
    return CMD_STATE


conversation_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        CMD_STATE: [
            CommandHandler('add', new_password),
            CommandHandler('list', list_services),
            CommandHandler('del', delete_service)
        ],
        SERVICE_STATE: [MessageHandler(filters.TEXT, add_service)],
        PASSWORD_STATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_password),
            CallbackQueryHandler(pattern='^generate_password$', callback=add_generated_password)
        ],
        CHOOSE_STATE: [
            CallbackQueryHandler(pattern='^previous_page$|^next_page$',callback=list_services),
            CallbackQueryHandler(pattern='^service_.+$', callback=send_password)
        ],
        CHOOSE_DELETING_STATE: [
            CallbackQueryHandler(pattern='^previous_page$|^next_page$',callback=delete_service),
            CallbackQueryHandler(pattern='^del_service_.+$', callback=delete_password)
        ],
        CONFIRM_DELETE_STATE: [
            CallbackQueryHandler(pattern='^confirm_delete$', callback=confirm_delete),
            CallbackQueryHandler(pattern='^cancel_delete$', callback=cancel_delete)
        ]
    },
    fallbacks=[]

)
