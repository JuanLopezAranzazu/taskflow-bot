import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram.types import Update
from fastapi import FastAPI, HTTPException, Request

from app.bot.bot import bot, dp
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

polling_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global polling_task
    if settings.BOT_MODE == "webhook":
        webhook_url = settings.WEBHOOK_BASE_URL.rstrip("/") + settings.WEBHOOK_PATH
        await bot.set_webhook(webhook_url, secret_token=settings.WEBHOOK_SECRET)
        logger.info("Webhook configurado en %s", webhook_url)
    else:
        await bot.delete_webhook(drop_pending_updates=True)
        polling_task = asyncio.create_task(dp.start_polling(bot))
        logger.info("Bot en modo polling")

    yield

    if polling_task:
        polling_task.cancel()
    await bot.session.close()


app = FastAPI(title="Project Tracker Bot API", lifespan=lifespan)


# ---------------- Webhook endpoint ----------------

@app.post(settings.WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    if settings.BOT_MODE != "webhook":
        raise HTTPException(status_code=404, detail="Webhook desactivado (BOT_MODE=polling)")
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Token secreto inválido")
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}


# ---------------- API REST ----------------

@app.get("/health")
async def health():
    return {"status": "ok"}
