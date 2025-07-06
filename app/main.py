from telegram.ext import ApplicationBuilder, CommandHandler

from bot.handlers import get_password_handler, start, new_password_handler

def main() -> None:
    application = (
        ApplicationBuilder()
        .token("ТОКЕН ХИАР")
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(new_password_handler)
    application.add_handler(get_password_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
