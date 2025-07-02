from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

from bot.handlers import add_password, button, list_passwords, start


def main() -> None:
    application = ApplicationBuilder().token("7112004063:AAEZ3hTzJ82iG7zBAmFo6VWQibA9-kdp7ig").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_password))
    application.add_handler(CommandHandler("list", list_passwords))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
