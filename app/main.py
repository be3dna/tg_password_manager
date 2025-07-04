
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler,filters

from bot.handlers import add_password, button, list_passwords, start, handle_message


def main() -> None:
    application = (
        ApplicationBuilder()
        .token("TOKEN")
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_password))
    application.add_handler(CommandHandler("list", list_passwords))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
