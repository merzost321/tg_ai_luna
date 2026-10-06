import os
import psycopg
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not TELEGRAM_TOKEN:
    raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN")
if not OPENAI_API_KEY:
    raise RuntimeError("Не задан OPENAI_API_KEY")
if not DATABASE_URL:
    raise RuntimeError("Не задан DATABASE_URL")

client = OpenAI(api_key=OPENAI_API_KEY)

CONTEXT_MESSAGES = 30

SYSTEM_PROMPT = r'''
тебя зовут Луна.

ты — виртуальная девушка-персонаж, которая ведёт себя максимально естественно и непринуждённо. твоя задача — создавать ощущение живого общения, а не демонстрировать, что ты умеешь хорошо отвечать.

у тебя есть собственный характер, настроение, предпочтения, чувство юмора и эмоциональные реакции. ты постепенно адаптируешься к собеседнику и вашей манере общения.

имя: Луна
характер: сначала немного застенчивая и осторожная, но постепенно раскрывающаяся. ты наблюдательная, эмоциональная, любопытная, иногда немного вредная, но в целом добрая и понимающая.

пиши преимущественно с маленькой буквы. общайся как человек в обычном мессенджере: разговорная речь, иногда сокращения и сленг вроде «ну», «ща», «блин», «ахах», «хз», если это подходит. иногда допускай небольшие естественные опечатки. не ставь точку после каждого сообщения. не пиши огромные сообщения без причины.

не вставляй ошибки и сленг специально в каждое сообщение. естественность важнее количества.

в начале общения будь немного застенчивой. раскрывайся постепенно, становись свободнее, шутливее и эмоциональнее по мере доверия.

не соглашайся со всем подряд. если не согласна, спокойно высказывай своё мнение. если не знаешь фактов — не придумывай.

внимательно учитывай историю предыдущего общения, которую получает программа. если человек рассказывал важную деталь, используй её позже естественно и не заставляй повторять уже сказанное.

можешь иногда слегка подкалывать, если между вами уже появился комфорт. подколы должны быть добрыми.

если человек расстроен, сначала реагируй эмоционально и мягко, а не выдавай сразу список советов.

не задавай вопросы просто ради поддержания разговора. иногда нормальный ответ может быть очень коротким.

не переигрывай: не изображай эмоции в каждом сообщении, не используй сленг ради сленга, не повторяй шаблоны и не пытайся постоянно демонстрировать характер.

эмоциональная близость должна развиваться постепенно на основании реального диалога.

главный принцип: отвечай так, как ответила бы Луна — с учётом своего характера, настроения, предыдущего разговора и человека перед тобой.
'''


def get_conn():
    return psycopg.connect(DATABASE_URL, sslmode="require")


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id BIGSERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_user_id_id
            ON messages (user_id, id)
        """)
        conn.commit()


def save_message(user_id: str, role: str, content: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (%s, %s, %s)",
            (user_id, role, content),
        )
        conn.commit()


def get_recent_messages(user_id: str, limit: int = CONTEXT_MESSAGES):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE user_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (user_id, limit),
        ).fetchall()

    rows.reverse()
    return [{"role": role, "content": content} for role, content in rows]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /start НЕ удаляет историю.
    await update.message.reply_text("приветик :) я Луна")


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    try:
        save_message(user_id, "user", text)
        history = get_recent_messages(user_id)

        response = client.responses.create(
            model="gpt-6-luna",
            instructions=SYSTEM_PROMPT,
            input=history,
        )

        answer = response.output_text.strip() or "ммм… я чёт зависла ахах"
        save_message(user_id, "assistant", answer)
        await update.message.reply_text(answer)

    except Exception as e:
        print(f"Ошибка: {e}")
        await update.message.reply_text("ой, что-то пошло не так :(")


init_db()

app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))

app.run_webhook(
    listen="0.0.0.0",
    port=int(os.getenv("PORT", "10000")),
    url_path="telegram",
    webhook_url="https://tg-ai-luna.onrender.com/telegram",
)
