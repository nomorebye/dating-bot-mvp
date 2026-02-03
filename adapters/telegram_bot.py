import asyncio
import os
import random

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from core.engine import generate_proactive, get_memory_store, handle_user_message


async def send_bubbles(app, chat_id: str, bubbles: list[str]) -> None:
    for bubble in bubbles:
        await app.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(random.uniform(0.4, 1.2))
        await app.bot.send_message(chat_id=chat_id, text=bubble)


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    user_id = str(update.effective_chat.id)
    bubbles = handle_user_message(user_id, update.message.text)
    await send_bubbles(context.application, update.effective_chat.id, bubbles)


async def proactive_job(app) -> None:
    store = get_memory_store()
    for user_id in store.list_user_ids():
        bubbles = generate_proactive(user_id)
        if bubbles:
            await send_bubbles(app, user_id, bubbles)


def main() -> None:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(lambda: asyncio.create_task(proactive_job(app)), "interval", minutes=1)
    scheduler.start()

    app.run_polling()


if __name__ == "__main__":
    main()
