
"""
Основной код Telegram бота
"""

import asyncio
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from .services.gpt import initialize_gpt_service, get_gpt_response

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получение токенов из секретов
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start"""
    await update.message.reply_text('Привет! Я готов помочь вам.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка текстовых сообщений"""
    user_message = update.message.text
    logger.info(f"Получено сообщение: {user_message}")
    
    try:
        # Получение ответа от GPT
        response = await get_gpt_response(user_message)
        if response:
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("Извините, произошла ошибка при обработке вашего сообщения.")
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await update.message.reply_text("Извините, произошла ошибка при обработке вашего сообщения.")

def main() -> None:
    """Главная функция запуска бота"""
    # Проверка наличия необходимых токенов
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не найден в секретах!")
        return
    
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY не найден в секретах!")
        return
    
    # Инициализация GPT сервиса
    initialize_gpt_service(OPENAI_API_KEY)
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск бота
    logger.info("Запуск бота...")
    application.run_polling()

if __name__ == '__main__':
    main()
