
"""
Основной код Telegram бота
"""

import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота (установите в Secrets)
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start"""
    await update.message.reply_text('Привет! Я готов помочь вам.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка текстовых сообщений"""
    user_message = update.message.text
    logger.info(f"Получено сообщение: {user_message}")
    
    # Здесь будет логика обработки сообщений через GPT
    response = f"Вы написали: {user_message}"
    await update.message.reply_text(response)

def main() -> None:
    """Главная функция запуска бота"""
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
