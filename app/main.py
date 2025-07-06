
from telegram.ext import ApplicationBuilder

from app.config import TELEGRAM_TOKEN
from bot.handlers import conversation_handler


def main() -> None:
    application = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .build()
    )
    application.add_handler(conversation_handler)


    application.run_polling()

if __name__ == '__main__':
    main()
