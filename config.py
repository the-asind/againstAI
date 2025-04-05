import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройки бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Тип AI сервиса (gemini, openai, и т.д.)
AI_SERVICE_TYPE = os.getenv("AI_SERVICE_TYPE", "gemini")

# Настройки игры
MIN_PLAYERS = 1
MAX_PLAYERS = 10
MAX_NAME_LENGTH = 30
MAX_SCENARIO_LENGTH = 500
MAX_ACTION_LENGTH = 500

# Ограничения для валидации
VALID_NAME_PATTERN = r'^[а-яА-ЯёЁa-zA-Z\s\-]+$'  # Разрешены только буквы, пробелы и дефисы
VALID_SCENARIO_PATTERN = r'^[а-яА-ЯёЁa-zA-Z0-9\s\.\,\-\!\?\_\(\)\:\;\"\']+$'
VALID_ACTION_PATTERN = r'^[а-яА-ЯёЁa-zA-Z0-9\s\.\,\-\!\?\_\(\)\:\;\"\']+$'

# Пути к данным
SCENARIOS_FILE = os.path.join('data', 'scenarios.txt')