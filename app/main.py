from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

from bot.handlers import button, list_passwords, start, new_password_handler

def main() -> None:
    application = (
        ApplicationBuilder()
        .token("7112004063:AAEZ3hTzJ82iG7zBAmFo6VWQibA9-kdp7ig")
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(new_password_handler)
    application.add_handler(CommandHandler("list", list_passwords))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
