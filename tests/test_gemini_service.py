import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio
from services.ai.gemini_service import GeminiService
from models import Player, GameMode


class TestGeminiService(unittest.TestCase):
    """Тесты для сервиса интеграции с Gemini API"""

    def setUp(self):
        """Подготовка к тестам"""
        self.service = GeminiService()
        
        # Создаем тестовых игроков
        self.players = {
            123: Player(user_id=123, first_name="Иван", last_name="Иванов", action="Бежать из здания"),
            456: Player(user_id=456, first_name="Петр", last_name="Петров", action="Прятаться под столом")
        }
        self.scenario = "Вы оказались в горящем здании. Огонь быстро распространяется по помещениям."
        self.game_mode = GameMode.EVERY_MAN_FOR_HIMSELF  # Используем правильное значение перечисления

    @patch('google.generativeai.GenerativeModel.generate_content_async')
    def test_build_prompt(self, mock_generate):
        """Тест создания промпта для Gemini API"""
        # Проверяем, что промпт содержит все необходимые данные
        prompt = self.service._build_competitive_prompt(self.scenario, self.players)
        
        # Проверяем, что промпт содержит сценарий
        self.assertIn(self.scenario, prompt)
        
        # Проверяем, что промпт содержит информацию о всех игроках
        for player in self.players.values():
            self.assertIn(player.first_name, prompt)
            self.assertIn(player.last_name, prompt)
            self.assertIn(player.action, prompt)
        
        # Проверяем, что промпт содержит инструкции для Gemini (на английском)
        self.assertIn("INSTRUCTIONS", prompt)
        # Проверка на наличие раздела для выживших в промпте
        self.assertIn("list the names", prompt.lower())

    def test_parse_response(self):
        """Тест парсинга ответа от Gemini API"""
        # Тестовый ответ от API с указанием выживших
        test_response = (
            "В горящем здании разворачивается драма выживания.\n\n"
            "Иван Иванов быстро принимает решение бежать из здания. "
            "Он находит путь через задымленный коридор и выбирается наружу.\n\n"
            "Петр Петров решает спрятаться под столом. К сожалению, огонь быстро охватывает комнату, "
            "и дым становится слишком густым. Петр теряет сознание от отравления угарным газом.\n\n"
            "ВЫЖИВШИЕ: Иван Иванов"
        )
        
        # Парсим ответ, передавая режим игры
        narrative, survivors = self.service._parse_response(test_response, self.players, self.game_mode)
        
        # Проверяем, что текст истории правильно отделен
        self.assertIn("В горящем здании разворачивается драма выживания", narrative)
        
        # Проверяем, что список выживших правильно определен
        self.assertEqual(len(survivors), 1)
        self.assertIn(123, survivors)  # ID Ивана
        self.assertNotIn(456, survivors)  # ID Петра

    @patch('google.generativeai.GenerativeModel.generate_content_async')
    def test_evaluate_survival(self, mock_generate_async):
        """Тест оценки выживания с использованием мока для API"""
        # Создаем мок для ответа от API
        mock_response = MagicMock()
        # Используем формат, который возвращает обновленная версия сервиса
        mock_response.text = (
            "In the scenario \"Вы оказались в горящем здании\", players acted differently.\n\n"
            "Иван Иванов быстро принимает решение бежать из здания. "
            "Он находит путь через задымленный коридор и выбирается наружу.\n\n"
            "Players demonstrated ingenuity and resourcefulness.\n\n"
            "ВЫЖИВШИЕ: Иван Иванов"
        )
        
        # Правильно настраиваем асинхронный мок
        mock_generate_async.return_value = mock_response
        
        # Запускаем тест асинхронно
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            narrative, survivors = loop.run_until_complete(
                self.service.evaluate_survival(self.scenario, self.players, self.game_mode)
            )
            
            # Проверяем результаты с учетом нового формата ответа
            self.assertIn("In the scenario", narrative)
        finally:
            loop.close()


if __name__ == '__main__':
    unittest.main()