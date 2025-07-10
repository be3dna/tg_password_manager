from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes


def collector(sensitive: bool = False):
    def message_collected(f):

        @wraps(f)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            attr_name = 'message_id_archive'
            if sensitive:
                attr_name = 'sensitive_message_id_archive'

            if update and update.message:
                message_archive = context.user_data.get(attr_name, [])
                message_archive.append([update.effective_chat.id, update.message.message_id])
                context.user_data[attr_name] = message_archive

            return await f(update, context, *args, **kwargs)

        return wrapper

    return message_collected
