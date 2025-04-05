from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class GameMode(Enum):
    """Game modes"""
    EVERY_MAN_FOR_HIMSELF = "Каждый сам за себя"
    BROTHERHOOD = "Братство (кооператив)"


class GameState(Enum):
    """Состояние игры"""
    WAITING_FOR_PLAYERS = "Ожидание игроков"
    WAITING_FOR_SCENARIO = "Ожидание сценария"
    WAITING_FOR_ACTIONS = "Ожидание действий"
    PROCESSING_RESULTS = "Обработка результатов"
    GAME_OVER = "Игра окончена"


@dataclass
class Player:
    """Модель игрока"""
    user_id: int
    first_name: str
    last_name: str
    username: Optional[str] = None
    is_captain: bool = False
    action: Optional[str] = None
    is_alive: bool = True


@dataclass
class Lobby:
    """Модель лобби"""
    id: str
    players: Dict[int, Player] = field(default_factory=dict)
    game_mode: GameMode = GameMode.EVERY_MAN_FOR_HIMSELF
    game_state: GameState = GameState.WAITING_FOR_PLAYERS
    scenario: Optional[str] = None
    captain_id: Optional[int] = None
    message_id: Optional[int] = None
    chat_id: Optional[int] = None

    def add_player(self, player: Player) -> bool:
        """Добавить игрока в лобби"""
        if player.user_id in self.players:
            return False
        
        # Если это первый игрок, делаем его капитаном
        if not self.players:
            player.is_captain = True
            self.captain_id = player.user_id
            
        self.players[player.user_id] = player
        return True
    
    def remove_player(self, user_id: int) -> bool:
        """Удалить игрока из лобби"""
        if user_id not in self.players:
            return False
        
        is_captain = self.players[user_id].is_captain
        del self.players[user_id]
        
        # Если удалили капитана и есть другие игроки, назначаем нового
        if is_captain and self.players:
            new_captain_id = next(iter(self.players))
            self.players[new_captain_id].is_captain = True
            self.captain_id = new_captain_id
            
        return True
    
    def get_captain(self) -> Optional[Player]:
        """Получить капитана лобби"""
        if self.captain_id and self.captain_id in self.players:
            return self.players[self.captain_id]
        return None
    
    def all_players_submitted_actions(self) -> bool:
        """Проверить, все ли игроки отправили свои действия"""
        return all(player.action is not None for player in self.players.values())
    
    def reset_actions(self):
        """Сбросить действия игроков для новой игры"""
        for player in self.players.values():
            player.action = None
            player.is_alive = True
    
    def get_players_with_actions(self) -> Dict[int, Player]:
        """Получить игроков, которые отправили действия"""
        return {uid: player for uid, player in self.players.items() if player.action is not None}
    
    def get_players_without_actions(self) -> Dict[int, Player]:
        """Получить игроков, которые еще не отправили действия"""
        return {uid: player for uid, player in self.players.items() if player.action is None}


# Хранилище лобби (в памяти)
lobbies: Dict[str, Lobby] = {}
# Отображение пользователь -> лобби
user_to_lobby: Dict[int, str] = {}
# Состояние пользователей (ожидание имени, фамилии и т.д.)
user_states: Dict[int, Dict[str, any]] = {}