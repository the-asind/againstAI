import unittest
from models import Player, Lobby, GameState, GameMode


class TestModels(unittest.TestCase):
    """Тесты для моделей данных"""

    def test_player_creation(self):
        """Тест создания игрока"""
        player = Player(user_id=123, first_name="Иван", last_name="Иванов")
        
        self.assertEqual(player.user_id, 123)
        self.assertEqual(player.first_name, "Иван")
        self.assertEqual(player.last_name, "Иванов")
        self.assertFalse(player.is_captain)
        self.assertIsNone(player.action)
        self.assertTrue(player.is_alive)

    def test_lobby_creation(self):
        """Тест создания лобби"""
        lobby = Lobby(id="test_id")
        
        self.assertEqual(lobby.id, "test_id")
        self.assertEqual(lobby.game_mode, GameMode.EVERY_MAN_FOR_HIMSELF)
        self.assertEqual(lobby.game_state, GameState.WAITING_FOR_PLAYERS)
        self.assertIsNone(lobby.scenario)
        self.assertIsNone(lobby.captain_id)
        
    def test_add_player_to_lobby(self):
        """Тест добавления игрока в лобби"""
        lobby = Lobby(id="test_id")
        player1 = Player(user_id=123, first_name="Иван", last_name="Иванов")
        player2 = Player(user_id=456, first_name="Петр", last_name="Петров")
        
        # Первый игрок должен стать капитаном
        self.assertTrue(lobby.add_player(player1))
        self.assertEqual(len(lobby.players), 1)
        self.assertTrue(lobby.players[123].is_captain)
        self.assertEqual(lobby.captain_id, 123)
        
        # Второй игрок не должен быть капитаном
        self.assertTrue(lobby.add_player(player2))
        self.assertEqual(len(lobby.players), 2)
        self.assertFalse(lobby.players[456].is_captain)
        
        # Попытка добавить игрока повторно должна вернуть False
        self.assertFalse(lobby.add_player(player1))
        
    def test_remove_player_from_lobby(self):
        """Тест удаления игрока из лобби"""
        lobby = Lobby(id="test_id")
        player1 = Player(user_id=123, first_name="Иван", last_name="Иванов")
        player2 = Player(user_id=456, first_name="Петр", last_name="Петров")
        
        lobby.add_player(player1)
        lobby.add_player(player2)
        
        # Удаление игрока, который не является капитаном
        self.assertTrue(lobby.remove_player(456))
        self.assertEqual(len(lobby.players), 1)
        
        # Удаление несуществующего игрока должно вернуть False
        self.assertFalse(lobby.remove_player(789))
        
        # Удаление капитана из лобби с несколькими игроками
        lobby.add_player(player2)
        self.assertTrue(lobby.remove_player(123))
        self.assertEqual(len(lobby.players), 1)
        # Новый капитан должен быть назначен
        self.assertTrue(lobby.players[456].is_captain)
        self.assertEqual(lobby.captain_id, 456)
        
        # Удаление последнего игрока из лобби
        self.assertTrue(lobby.remove_player(456))
        self.assertEqual(len(lobby.players), 0)
        
    def test_get_captain(self):
        """Тест получения капитана лобби"""
        lobby = Lobby(id="test_id")
        player = Player(user_id=123, first_name="Иван", last_name="Иванов")
        
        # Первый игрок должен стать капитаном
        lobby.add_player(player)
        captain = lobby.get_captain()
        self.assertIsNotNone(captain)
        self.assertEqual(captain.user_id, 123)
        
        # Удаление капитана из лобби
        lobby.remove_player(123)
        self.assertIsNone(lobby.get_captain())
        
    def test_players_actions(self):
        """Тест действий игроков"""
        lobby = Lobby(id="test_id")
        player1 = Player(user_id=123, first_name="Иван", last_name="Иванов")
        player2 = Player(user_id=456, first_name="Петр", last_name="Петров")
        
        lobby.add_player(player1)
        lobby.add_player(player2)
        
        # Изначально у игроков нет действий
        self.assertFalse(lobby.all_players_submitted_actions())
        self.assertEqual(len(lobby.get_players_with_actions()), 0)
        self.assertEqual(len(lobby.get_players_without_actions()), 2)
        
        # Установка действия для одного игрока
        lobby.players[123].action = "Бежать"
        self.assertFalse(lobby.all_players_submitted_actions())
        self.assertEqual(len(lobby.get_players_with_actions()), 1)
        self.assertEqual(len(lobby.get_players_without_actions()), 1)
        
        # Установка действия для второго игрока
        lobby.players[456].action = "Прятаться"
        self.assertTrue(lobby.all_players_submitted_actions())
        self.assertEqual(len(lobby.get_players_with_actions()), 2)
        self.assertEqual(len(lobby.get_players_without_actions()), 0)
        
        # Сброс действий
        lobby.reset_actions()
        self.assertFalse(lobby.all_players_submitted_actions())
        self.assertEqual(len(lobby.get_players_with_actions()), 0)
        self.assertEqual(len(lobby.get_players_without_actions()), 2)
        self.assertTrue(lobby.players[123].is_alive)
        self.assertTrue(lobby.players[456].is_alive)


if __name__ == '__main__':
    unittest.main()