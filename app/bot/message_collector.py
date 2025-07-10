from telegram import Update
from telegram.ext import ContextTypes


def message_collected(f, sensitive=False):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        attr_name = 'message_id_archive'
        if sensitive:
            attr_name = 'sensitive_message_id_archive'

        if update and update.message:
            message_archive = context.user_data.get(attr_name, [])
            message_archive.append([update.effective_chat.id, update.message.message_id])
            context.user_data[attr_name] = message_archive

        res = await f(update, context, *args, **kwargs)

        return res

    return wrapper
