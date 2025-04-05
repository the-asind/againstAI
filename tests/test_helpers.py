import unittest
import os
import re
from unittest.mock import patch, mock_open
from utils.helpers import (
    generate_lobby_id,
    generate_invite_code,
    get_random_scenario,
    validate_name,
    validate_scenario,
    validate_action
)


class TestHelpers(unittest.TestCase):
    """Тесты для вспомогательных функций"""

    def test_generate_lobby_id(self):
        """Тест генерации ID лобби"""
        lobby_id = generate_lobby_id()
        
        # ID должен быть строкой
        self.assertIsInstance(lobby_id, str)
        # ID должен иметь правильную длину (8 символов)
        self.assertEqual(len(lobby_id), 8)
        
        # Генерируем еще один ID для проверки уникальности
        another_id = generate_lobby_id()
        self.assertNotEqual(lobby_id, another_id)

    def test_generate_invite_code(self):
        """Тест генерации кода приглашения"""
        invite_code = generate_invite_code()
        
        # Код должен быть строкой
        self.assertIsInstance(invite_code, str)
        # Код должен иметь правильную длину (6 символов)
        self.assertEqual(len(invite_code), 6)
        # Код должен содержать только буквы верхнего регистра и цифры
        self.assertTrue(all(c.isdigit() or c.isupper() for c in invite_code))
        
        # Генерируем еще один код для проверки уникальности
        another_code = generate_invite_code()
        self.assertNotEqual(invite_code, another_code)

    @patch('builtins.open', new_callable=mock_open, read_data="Сценарий 1\nСценарий 2\nСценарий 3")
    def test_get_random_scenario(self, mock_file):
        """Тест получения случайного сценария"""
        # Патчим константу SCENARIOS_FILE чтобы функция использовала её
        with patch('utils.helpers.SCENARIOS_FILE', 'mocked_path'):
            scenario = get_random_scenario()
            
            # Проверяем, что сценарий - одна из строк из "файла"
            self.assertIn(scenario, ["Сценарий 1", "Сценарий 2", "Сценарий 3"])
            
            # Проверяем, что файл был открыт правильно
            mock_file.assert_called_once_with('mocked_path', 'r', encoding='utf-8')

    def test_validate_name(self):
        """Тест валидации имени/фамилии"""
        # Валидные имена
        self.assertEqual(validate_name("Иван"), (True, None))
        self.assertEqual(validate_name("John"), (True, None))
        self.assertEqual(validate_name("Иван-Петр"), (True, None))
        
        # Невалидные имена
        self.assertEqual(validate_name(""), (False, "Имя не может быть пустым"))
        self.assertEqual(validate_name("Иван123"), (False, "Имя может содержать только буквы, пробелы и дефисы"))
        
        # Тест с длинным именем
        long_name = "А" * 31  # 31 символ, максимум по умолчанию 30
        self.assertEqual(validate_name(long_name), (False, "Имя не может быть длиннее 30 символов"))

    def test_validate_scenario(self):
        """Тест валидации сценария"""
        # Валидные сценарии
        self.assertEqual(validate_scenario("Тестовый сценарий"), (True, None))
        self.assertEqual(validate_scenario("Test scenario with numbers 123"), (True, None))
        self.assertEqual(validate_scenario("Сценарий с пунктуацией: запятые, точки, тире - и прочее!"), (True, None))
        
        # Невалидные сценарии
        self.assertEqual(validate_scenario(""), (False, "Сценарий не может быть пустым"))
        
        # Тест с длинным сценарием
        long_scenario = "А" * 501  # 501 символ, максимум по умолчанию 500
        self.assertEqual(validate_scenario(long_scenario), (False, "Сценарий не может быть длиннее 500 символов"))

    def test_validate_action(self):
        """Тест валидации действия"""
        # Валидные действия
        self.assertEqual(validate_action("Бежать из здания"), (True, None))
        self.assertEqual(validate_action("Run and hide! Quickly."), (True, None))
        self.assertEqual(validate_action("Действие с цифрами: 123, и знаками пунктуации."), (True, None))
        
        # Невалидные действия
        self.assertEqual(validate_action(""), (False, "Действие не может быть пустым"))
        
        # Тест с длинным действием
        long_action = "А" * 501  # 501 символ, максимум по умолчанию 500
        self.assertEqual(validate_action(long_action), (False, "Действие не может быть длиннее 500 символов"))


if __name__ == '__main__':
    unittest.main()