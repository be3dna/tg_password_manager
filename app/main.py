from telegram.ext import ApplicationBuilder, CommandHandler, filters, MessageHandler

from app.config import TELEGRAM_TOKEN
from bot.handlers import conversation_handler, get_sticker_id, toggle_stickers, is_authorized


def main() -> None:
    application = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .build()
    )
    application.add_handler(CommandHandler("toggle_stickers", toggle_stickers))
    application.add_handler(MessageHandler(filters.Sticker.ALL, get_sticker_id))
    application.add_handler(CommandHandler("home", is_authorized))
    application.add_handler(conversation_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
