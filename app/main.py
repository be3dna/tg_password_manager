from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from bot.handlers import get_password_handler, start, new_password_handler, handle_message


def main() -> None:
    application = (
        ApplicationBuilder()
        .token("YOUR_TOKEN_HERE")
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(new_password_handler)
    application.add_handler(get_password_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
