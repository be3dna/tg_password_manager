from telegram.ext import ApplicationBuilder

from bot.handlers import conversation_handler

def main() -> None:
    application = (
        ApplicationBuilder()
        .token("ТОКЕН ХИАР")
        .build()
    )
    application.add_handler(conversation_handler)


    application.run_polling()

if __name__ == '__main__':
    main()
