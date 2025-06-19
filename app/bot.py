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


import re  # в начале файла, если ещё не добавлено

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import json
import logging

logger = logging.getLogger(__name__)

async def evaluate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = context.user_data.get('generated_prompt')
    if not prompt:
        await update.callback_query.answer("Сначала отправьте задачу", show_alert=True)
        return

    eval_prompt = load_prompt(EVAL_PROMPT_PATH).replace("{PROMPT}", prompt)

    raw_result = await get_gpt_response (
        eval_prompt,
    system_prompt = """Ты — эксперт по оценке промптов. Твоя задача — проанализировать промпт по 15 критериям и выдать только один JSON-объект. 

    📌 Правила:
    - Пиши строго на русском языке.
    - Ответ — только в валидном JSON.
    - JSON должен начинаться с { и заканчиваться на }.
    - Должны быть все 15 критериев, каждый с полями: "Score", "Strength", "Improvement", "Justification".
    - Обязательно включи ключ "Total Score" в конце.
    - Никаких пояснений вне JSON.
    - Не используй ```json или другие обрамления.
    - Каждое значение (Strength, Improvement, Justification) — не длиннее 25 слов.

    Если JSON не влезает — сокращай тексты, но не обрывай JSON и не пропускай критерии."""
    )
    logger.warning(f"RAW GPT OUTPUT:\n{raw_result}")

    # Убираем возможные обёртки ```json ... ```
    cleaned = raw_result.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").removesuffix("```").strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").removesuffix("```").strip()

    # Обрезаем по последней закрывающей скобке
    last_brace = cleaned.rfind("}")
    if last_brace != -1:
        cleaned = cleaned[:last_brace + 1]

    try:
        # Пробуем парсить JSON, по одному символу отрезая в случае ошибки
        while cleaned:
            try:
                parsed = json.loads(cleaned)
                break
            except json.JSONDecodeError:
                cleaned = cleaned[:-1]
        else:
            raise ValueError("Не удалось распарсить JSON даже после обрезки.")

        # Извлекаем, если есть ключ 'Evaluation'
        if "Evaluation" in parsed:
            parsed = parsed["Evaluation"]

        # Формируем текст
        text_parts = []
        for key, val in parsed.items():
            if isinstance(val, dict):
                name = key
                score = val.get("Score") or val.get("score", "—")
                strength = (val.get("Strength") or val.get("strength", "")).replace("<br>", "\n")
                improvement = (val.get("Improvement") or val.get("improvement", "")).replace("<br>", "\n")

                block = (
                    f"<b>{name}</b>\n"
                    f"⭐️ Оценка: <b>{score}/5</b>\n"
                    f"✅ Сильная сторона: {strength}\n"
                    f"🛠 Можно улучшить: {improvement}"
                )
                text_parts.append(block)
        total_score = parsed.get("Total Score") or parsed.get("total_score")
        if total_score:
            text_parts.append(f"\n<b>Общая оценка промпта:</b> <b>{total_score}/75</b>")

        final_text = "<b>Оценка промпта по критериям:</b>\n\n" + "\n\n".join(text_parts)

        # Кнопка "Сделать промпт идеальным"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Сделать промпт идеальным", callback_data="refine_prompt")]
        ])

        await update.callback_query.message.reply_text(
            final_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Ошибка разбора JSON: {e}\nОтвет GPT:\n{raw_result}")
        await update.callback_query.message.reply_text("Ошибка при разборе оценки. Попробуй ещё раз.")

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
    import logging
    import os

    from .services.gpt import initialize_gpt_service, get_gpt_response
    from .bot_helpers import start, check_sub_callback, handle_message, evaluate_callback  # если они в отдельных файлах

    # Настройка логирования
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    # Переменные окружения
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Коллбэк улучшения промпта

async def improve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        prompt = context.user_data.get('generated_prompt')
        if not prompt:
            await update.callback_query.answer("Сначала отправьте задачу", show_alert=True)
            return

        improve_prompt = f"""
    Ты Senior Prompt Engineer. Улучши следующий промпт по всем 15 критериям оценки качества. 
    Верни только улучшенный промпт — без пояснений и без форматирования. Промпт ниже:

    {prompt}
    """

        result = await get_gpt_response(improve_prompt, system_prompt="Ты Senior Prompt Engineer.")
        await update.callback_query.message.reply_text(
            f"<b>Идеальный промпт:</b>\n<code>{result}</code>",
            parse_mode="HTML"
        )

    # Главная функция запуска бота
def main():
        if not BOT_TOKEN or not OPENAI_API_KEY:
            logger.error("Нет BOT_TOKEN или OPENAI_API_KEY в переменных окружения!")
            return

        initialize_gpt_service(OPENAI_API_KEY)

        app = Application.builder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="check_sub"))
        app.add_handler(CallbackQueryHandler(evaluate_callback, pattern="evaluate"))
        app.add_handler(CallbackQueryHandler(improve_callback, pattern="improve"))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("Бот запущен!")
        app.run_polling()

if __name__ == '__main__':
        main()
