import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

AI_SERVICE_TYPE = os.getenv("AI_SERVICE_TYPE", "gemini")

MIN_PLAYERS = 1
MAX_PLAYERS = 10
MAX_NAME_LENGTH = 30
MAX_SCENARIO_LENGTH = 500
MAX_ACTION_LENGTH = 500

VALID_NAME_PATTERN = r'^[а-яА-ЯёЁa-zA-Z\s\-]+$'  
VALID_SCENARIO_PATTERN = r'^[а-яА-ЯёЁa-zA-Z0-9\s\.\,\-\!\?\_\(\)\:\;\"\']+$'
VALID_ACTION_PATTERN = r'^[а-яА-ЯёЁa-zA-Z0-9\s\.\,\-\!\?\_\(\)\:\;\"\']+$'

SCENARIOS_FILE = os.path.join('data', 'scenarios.txt')