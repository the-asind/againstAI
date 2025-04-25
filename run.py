import os
import sys
import unittest
import logging
import subprocess
import time


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def run_tests():
    """Запуск всех тестов"""
    logger.info("Запуск тестов...")
    
    
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir)
    
    
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_bot(timeout=5):
    """Запуск бота в отдельном процессе для проверки"""
    logger.info(f"Запуск бота в отдельном процессе на {timeout} секунд для проверки...")
    
    
    process = subprocess.Popen([sys.executable, 'main.py'])
    
    
    logger.info(f"Ожидание {timeout} секунд...")
    time.sleep(timeout)
    
    
    logger.info("Завершение процесса бота...")
    if process.poll() is None:
        process.terminate()
        process.wait(timeout=2)
        logger.info("Бот успешно запущен и остановлен!")
        return True
    else:
        logger.error("Бот завершился преждевременно!")
        return False

def main():
    """Основная функция для тестирования и запуска бота"""
    
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('
                    continue
                key, value = line.split('=', 1)
                os.environ[key] = value
    
    
    if 'BOT_TOKEN' not in os.environ:
        logger.error("Переменная окружения BOT_TOKEN не установлена.")
        return False
    
    if 'GEMINI_API_KEY' not in os.environ and os.path.exists('services/gemini_service.py'):
        logger.error("Переменная окружения GEMINI_API_KEY не установлена.")
        return False
    
    
    tests_success = run_tests()
    
    if not tests_success:
        logger.error("Тесты не пройдены. Исправьте ошибки перед запуском бота.")
        return False
    
    
    bot_success = run_bot()
    
    return bot_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)