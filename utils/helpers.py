import random
import re
import string
import uuid
import os
from typing import List, Optional

from config import (
    SCENARIOS_FILE, VALID_NAME_PATTERN, VALID_SCENARIO_PATTERN,
    VALID_ACTION_PATTERN, MAX_NAME_LENGTH, MAX_SCENARIO_LENGTH,
    MAX_ACTION_LENGTH
)


def generate_lobby_id() -> str:
    """Генерирует уникальный ID для лобби"""
    return str(uuid.uuid4())[:8]


def generate_invite_code() -> str:
    """Генерирует 6-символьный код приглашения"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def get_random_scenario() -> str:
    """Возвращает случайный сценарий из файла"""
    try:
        with open(SCENARIOS_FILE, 'r', encoding='utf-8') as file:
            scenarios = file.read().splitlines()
        
        # Фильтруем пустые строки
        scenarios = [s for s in scenarios if s.strip()]
        
        if not scenarios:
            return "Вы оказались в опасной ситуации. Что вы будете делать?"
        
        return random.choice(scenarios)
    except Exception as e:
        print(f"Ошибка при чтении файла сценариев: {e}")
        return "Вы оказались в опасной ситуации. Что вы будете делать?"


def validate_name(name: str) -> tuple[bool, Optional[str]]:
    """
    Проверяет валидность имени или фамилии
    
    Args:
        name: Имя или фамилия для проверки
        
    Returns:
        tuple[bool, Optional[str]]: (Валидно ли имя, сообщение об ошибке)
    """
    if not name:
        return False, "Имя не может быть пустым"
    
    if len(name) > MAX_NAME_LENGTH:
        return False, f"Имя не может быть длиннее {MAX_NAME_LENGTH} символов"
    
    if not re.match(VALID_NAME_PATTERN, name):
        return False, "Имя может содержать только буквы, пробелы и дефисы"
    
    return True, None


def validate_scenario(scenario: str) -> tuple[bool, Optional[str]]:
    """
    Проверяет валидность сценария
    
    Args:
        scenario: Сценарий для проверки
        
    Returns:
        tuple[bool, Optional[str]]: (Валиден ли сценарий, сообщение об ошибке)
    """
    if not scenario:
        return False, "Сценарий не может быть пустым"
    
    if len(scenario) > MAX_SCENARIO_LENGTH:
        return False, f"Сценарий не может быть длиннее {MAX_SCENARIO_LENGTH} символов"
    
    if not re.match(VALID_SCENARIO_PATTERN, scenario):
        return False, "Сценарий содержит недопустимые символы"
    
    return True, None


def validate_action(action: str) -> tuple[bool, Optional[str]]:
    """
    Проверяет валидность действия игрока
    
    Args:
        action: Действие для проверки
        
    Returns:
        tuple[bool, Optional[str]]: (Валидно ли действие, сообщение об ошибке)
    """
    if not action:
        return False, "Действие не может быть пустым"
    
    if len(action) > MAX_ACTION_LENGTH:
        return False, f"Действие не может быть длиннее {MAX_ACTION_LENGTH} символов"
    
    if not re.match(VALID_ACTION_PATTERN, action):
        return False, "Действие содержит недопустимые символы"
    
    return True, None