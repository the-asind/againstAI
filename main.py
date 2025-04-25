import logging
from telegram.ext import Application

from config import BOT_TOKEN
from handlers.setup import setup_handlers

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция запуска бота"""
    
    if not BOT_TOKEN:
        logger.error("Токен бота не найден. Убедитесь, что он указан в переменных окружения или в .env файле.")
        return
    application = Application.builder().token(BOT_TOKEN).build()
    setup_handlers(application)
    logger.info("Запуск бота")
    application.run_polling(close_loop=False)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем.")
    except Exception as e:
        logger.error(f"Произошла ошибка: {e}")
    finally:
        logger.info("Бот остановлен.")