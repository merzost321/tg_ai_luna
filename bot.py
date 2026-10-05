import os

from openai import OpenAI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

async def check_webhook(application):
    info = await application.bot.get_webhook_info()
    print("=== WEBHOOK INFO ===")
    print(f"url: {info.url}")
    print(f"pending: {info.pending_update_count}")
    print(f"last_error: {info.last_error_message}")
    print("====================")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "приветик 🙂 теперь я умею общаться с AI"
    )


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    try:
        response = client.responses.create(
            model="gpt-5.6-mini",
            input=text,
        )

        answer = response.output_text

        await update.message.reply_text(answer)

    except Exception as e:
        print(f"Ошибка OpenAI: {e}")
        await update.message.reply_text(
            "ой, что-то пошло не так с AI :("
        )


app = (
    Application.builder()
    .token(TELEGRAM_TOKEN)
    .post_init(check_webhook)
    .build()
)

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))

print("бот запущен...")

app.run_webhook(
    listen="0.0.0.0",
    port=int(os.getenv("PORT", "10000")),
    url_path="telegram",
    webhook_url="https://tg-ai-luna.onrender.com/telegram",
)
