import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton
from telegram.ext import ContextTypes

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Словарь для хранения паролей
passwords = {'github': '1234'}
services_per_page = 5


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Используй /add для добавления пароля и /list для просмотра.')

async def add_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text('Используйте: /add <сервис> <пароль>')
        return
    service = context.args[0]
    password = context.args[1]
    passwords[service] = password
    await update.message.reply_text(f'Пароль для {service} добавлен!')

async def list_passwords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = list(passwords.keys())
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
        await send_password(query, service)


async def send_password(update: Update, service: str) -> None:
    password = passwords[service]
    copy_kb = InlineKeyboardMarkup([[InlineKeyboardButton('Копировать', copy_text=CopyTextButton(password))]])
    await update.message.reply_text(f'Ваш пароль от сервиса {service}.', reply_markup=copy_kb)