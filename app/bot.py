import re
import json
import asyncio
import logging
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (Application, CommandHandler, MessageHandler,
                          CallbackQueryHandler, ContextTypes, filters)
from app.services.gpt import initialize_gpt_service, get_gpt_response

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@YOUR_CHANNEL")

# Загрузка системных промптов
BASE_PROMPT_PATH = "app/prompts/base_ru.txt"
EVAL_PROMPT_PATH = "app/prompts/evaluate_ru.txt"


def load_prompt(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error(f"Промпт {path} не найден!")
        return ""


async def check_subscription(user_id, context):
    try:
        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Ошибка при проверке подписки: {e}")
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/start вызван пользователем {update.effective_user.id}")

    user_id = update.effective_user.id
    if not await check_subscription(user_id, context):
        buttons = [[InlineKeyboardButton("✅ Подписаться", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
                   [InlineKeyboardButton("🔄 Проверить подписку", callback_data="check_sub")]]
        markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text("Сначала подпишитесь на канал, чтобы пользоваться ботом:", reply_markup=markup)
    else:
        await update.message.reply_text("Привет! Напиши, какую задачу ты хочешь решить с помощью ИИ.")


async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await check_subscription(user_id, context):
        await update.callback_query.message.reply_text("Отлично! Теперь напиши, что должен делать твой промпт.")
    else:
        await update.callback_query.answer("Вы еще не подписались", show_alert=True)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    task = update.message.text.strip()

    base_prompt = load_prompt(BASE_PROMPT_PATH)
    logger.info(f"Загружен системный промпт длиной {len(base_prompt)} символов")

    if not base_prompt:
        await update.message.reply_text("⚠️ Ошибка: системный промпт не загружен.")
        return

    result = await get_gpt_response(task, base_prompt)
    context.user_data['generated_prompt'] = result

    buttons = [[InlineKeyboardButton("🔍 Оценить по 15 критериям", callback_data="evaluate")],
               [InlineKeyboardButton("💎 Сделать идеальным", callback_data="improve")]]
    markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(f"<b>Вот твой промпт:</b>\n<code>{result}</code>\n\nМожешь скопировать его или улучшить:",
                                    reply_markup=markup, parse_mode="HTML")


async def evaluate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = context.user_data.get('generated_prompt')
    if not prompt:
        await update.callback_query.answer("Сначала отправьте задачу", show_alert=True)
        return

    eval_prompt = load_prompt(EVAL_PROMPT_PATH).replace("{PROMPT}", prompt)

    raw_result = await get_gpt_response(
        eval_prompt,
        system_prompt="""Ты — эксперт по оценке промптов. Твоя задача — проанализировать промпт по 15 критериям и выдать только один JSON-объект. 

📌 Правила:
- Пиши строго на русском языке.
- Ответ — только в валидном JSON.
- JSON должен начинаться с { и заканчиваться на }.
- Должны быть все 15 критериев, каждый с полями: "Score", "Strength", "Improvement", "Justification".
- Обязательно включи ключ "Total Score" в конце.
- Никаких пояснений вне JSON.
- Не используй ```json или другие обрамления.
- Каждое значение (Strength, Improvement, Justification) - не длиннее 25 слов.

Если JSON не влезает — сокращай тексты, но не обрывай JSON и не пропускай критерии."""
    )
    logger.warning(f"RAW GPT OUTPUT:\n{raw_result}")

    # Убираем возможные обёртки ```json ... ```
    cleaned = raw_result.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").removesuffix("```").strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").removesuffix("