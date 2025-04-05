from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from models import Player, Lobby, GameState, GameMode, user_states, lobbies, user_to_lobby
from utils.helpers import generate_lobby_id, validate_name, get_random_scenario, validate_scenario


# Состояния разговора
ENTER_FULL_NAME, WAITING_FOR_LOBBY_OR_CREATE, IN_LOBBY = range(3)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    
    # Если пользователь уже в лобби, сразу перенаправляем его туда
    if user_id in user_to_lobby and user_to_lobby[user_id] in lobbies:
        lobby_id = user_to_lobby[user_id]
        await update.message.reply_text(
            f"Вы уже состоите в лобби. Используйте /lobby для просмотра информации о лобби."
        )
        return IN_LOBBY
    
    # Начинаем процесс регистрации
    await update.message.reply_text(
        "Добро пожаловать в игру 'Против ИИ'!\n\n"
        "Вам предстоит испытать свои навыки выживания в различных сценариях, "
        "соревнуясь с другими игроками и нейросетью.\n\n"
        "Для начала, пожалуйста, введите своё имя и фамилию:"
    )
    
    # Сбрасываем состояние пользователя
    user_states[user_id] = {}
    
    return ENTER_FULL_NAME


async def enter_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик ввода полного имени"""
    user_id = update.effective_user.id
    full_name = update.message.text.strip()
    
    # Проверяем, если пользователь хотел присоединиться к конкретному лобби
    if user_id in user_states and 'join_lobby_id' in user_states[user_id]:
        # Валидация полного имени
        is_valid, error_message = validate_name(full_name)
        if not is_valid:
            await update.message.reply_text(f"Ошибка: {error_message}. Пожалуйста, введите полное имя еще раз:")
            return ENTER_FULL_NAME
        
        # Разбиваем полное имя на имя и фамилию
        name_parts = full_name.split(maxsplit=1)
        user_states[user_id]['first_name'] = name_parts[0]
        user_states[user_id]['last_name'] = name_parts[1] if len(name_parts) > 1 else ""
        
        # Получаем ID лобби для присоединения
        lobby_id = user_states[user_id]['join_lobby_id']
        
        # Проверяем существование лобби
        if lobby_id not in lobbies:
            await update.message.reply_text("Лобби с таким ID не найдено. Создаём новое лобби.")
            return await create_new_lobby(update, context, user_id)
        
        # Если лобби существует, присоединяем игрока
        lobby = lobbies[lobby_id]
        
        # Проверяем, можно ли добавить еще игрока
        if len(lobby.players) >= 10:  # MAX_PLAYERS
            await update.message.reply_text("К сожалению, лобби уже заполнено. Создаём новое лобби.")
            return await create_new_lobby(update, context, user_id)
        
        if lobby.game_state != GameState.WAITING_FOR_PLAYERS:
            await update.message.reply_text("К сожалению, в этом лобби уже началась игра. Создаём новое лобби.")
            return await create_new_lobby(update, context, user_id)
        
        # Добавляем игрока в лобби
        player = Player(
            user_id=user_id,
            first_name=user_states[user_id]['first_name'],
            last_name=user_states[user_id]['last_name'],
            username=update.effective_user.username
        )
        
        lobby.add_player(player)
        user_to_lobby[user_id] = lobby_id
        
        # Удаляем временный ID лобби из состояния пользователя
        user_states[user_id].pop('join_lobby_id', None)
        
        await update.message.reply_text(
            f"Вы присоединились к лобби ID: {lobby_id}"
        )
        
        # Обновляем информацию о лобби для всех игроков
        await broadcast_lobby_update(context, lobby)
        
        return IN_LOBBY
    
    # Валидация полного имени
    is_valid, error_message = validate_name(full_name)
    if not is_valid:
        await update.message.reply_text(f"Ошибка: {error_message}. Пожалуйста, введите полное имя еще раз:")
        return ENTER_FULL_NAME
    
    # Сохраняем имя и фамилию
    name_parts = full_name.split(maxsplit=1)
    user_states[user_id]['first_name'] = name_parts[0]
    user_states[user_id]['last_name'] = name_parts[1] if len(name_parts) > 1 else ""
    
    # Отправляем сообщение о том, что можно ввести ID лобби
    await update.message.reply_text(
        f"Отлично, {user_states[user_id]['first_name']} {user_states[user_id]['last_name']}!\n\n"
        f"Теперь вы можете:\n"
        f"1. Ввести ID существующего лобби, чтобы присоединиться к нему\n"
        f"2. Или просто нажмите кнопку ниже, чтобы создать новое лобби"
    )
    
    # Добавляем кнопку для создания лобби
    keyboard = [
        [InlineKeyboardButton("Создать новое лобби", callback_data="create_new_lobby")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=reply_markup
    )
    
    return WAITING_FOR_LOBBY_OR_CREATE


async def wait_for_lobby_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик ввода ID лобби после регистрации"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Проверяем, является ли текст ID лобби - убираем проверку формата,
    # так как лобби может иметь разные форматы ID
    lobby_id = text
    
    # Проверяем существование лобби
    if lobby_id not in lobbies:
        await update.message.reply_text(
            "Лобби с таким ID не найдено. Проверьте ID и попробуйте снова, "
            "или создайте новое лобби кнопкой ниже."
        )
        
        # Добавляем кнопку для создания лобби
        keyboard = [
            [InlineKeyboardButton("Создать новое лобби", callback_data="create_new_lobby")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=reply_markup
        )
        
        return WAITING_FOR_LOBBY_OR_CREATE
    
    # Если лобби существует, присоединяем игрока
    lobby = lobbies[lobby_id]
    
    # Проверяем, можно ли добавить еще игрока
    if len(lobby.players) >= 10:  # MAX_PLAYERS
        await update.message.reply_text(
            "К сожалению, лобби уже заполнено. Создайте новое лобби."
        )
        return WAITING_FOR_LOBBY_OR_CREATE
    
    if lobby.game_state != GameState.WAITING_FOR_PLAYERS:
        await update.message.reply_text(
            "К сожалению, в этом лобби уже началась игра. Создайте новое лобби."
        )
        return WAITING_FOR_LOBBY_OR_CREATE
    
    # Добавляем игрока в лобби
    player = Player(
        user_id=user_id,
        first_name=user_states[user_id]['first_name'],
        last_name=user_states[user_id]['last_name'],
        username=update.effective_user.username
    )
    
    lobby.add_player(player)
    user_to_lobby[user_id] = lobby_id
    
    await update.message.reply_text(
        f"Вы присоединились к лобби ID: {lobby_id}"
    )
    
    # Обновляем информацию о лобби для всех игроков
    await broadcast_lobby_update(context, lobby)
    
    return IN_LOBBY


async def create_new_lobby_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик кнопки 'Создать новое лобби'"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    return await create_new_lobby(update, context, user_id, is_callback=True)


async def create_new_lobby(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, is_callback: bool = False) -> int:
    """Создает новое лобби для пользователя"""
    # Создаем игрока
    player = Player(
        user_id=user_id,
        first_name=user_states[user_id]['first_name'],
        last_name=user_states[user_id]['last_name'],
        username=update.effective_user.username if not is_callback else update.callback_query.from_user.username
    )
    
    # Создаем новое лобби
    lobby_id = generate_lobby_id()
    lobby = Lobby(id=lobby_id)
    lobby.add_player(player)
    
    # Сохраняем лобби
    lobbies[lobby_id] = lobby
    user_to_lobby[user_id] = lobby_id
    
    # Отправляем информацию о лобби и запрос на выбор режима игры
    message_text = (
        f"Отлично, {player.first_name} {player.last_name}!\n\n"
        f"Лобби создано. Вы назначены капитаном.\n"
        f"ID лобби: `{lobby_id}`\n\n"
    )
    
    # Создаем клавиатуру для выбора режима игры
    keyboard = [
        [
            InlineKeyboardButton("Каждый сам за себя", callback_data="mode_every_man"),
            InlineKeyboardButton("Братство (кооператив)", callback_data="mode_brotherhood")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем основное сообщение
    if is_callback:
        sent_message = await update.callback_query.message.reply_text(
            message_text + "Выберите режим игры:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        sent_message = await update.message.reply_text(
            message_text + "Выберите режим игры:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    return IN_LOBBY


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /join"""
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "Для присоединения к лобби используйте команду /join с ID лобби.\n"
            "Например: /join abc123"
        )
        return ConversationHandler.END
    
    lobby_id = context.args[0]
    
    # Проверяем существование лобби
    if lobby_id not in lobbies:
        await update.message.reply_text("Лобби с таким ID не найдено. Проверьте ID и попробуйте снова.")
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    
    # Если пользователь уже в каком-то лобби
    if user_id in user_to_lobby:
        existing_lobby_id = user_to_lobby[user_id]
        
        # Если это то же самое лобби
        if existing_lobby_id == lobby_id:
            await update.message.reply_text("Вы уже состоите в этом лобби.")
            return IN_LOBBY
        
        # Если другое лобби, спрашиваем, хочет ли покинуть его
        keyboard = [
            [
                InlineKeyboardButton("Да, покинуть", callback_data=f"leave_join_{existing_lobby_id}_{lobby_id}"),
                InlineKeyboardButton("Нет, остаться", callback_data="stay_in_lobby")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Вы уже состоите в другом лобби. Хотите покинуть его и присоединиться к новому?",
            reply_markup=reply_markup
        )
        return IN_LOBBY
    
    # Если пользователь еще не вводил имя и фамилию
    if user_id not in user_states or 'first_name' not in user_states[user_id]:
        user_states[user_id] = {}
        await update.message.reply_text(
            "Для присоединения к лобби, сначала введите свое полное имя (имя и фамилию):"
        )
        # Сохраняем ID лобби, к которому игрок хочет присоединиться
        user_states[user_id]['join_lobby_id'] = lobby_id
        return ENTER_FULL_NAME
    
    # Если имя и фамилия уже есть, добавляем игрока в лобби
    lobby = lobbies[lobby_id]
    
    # Добавляем игрока в лобби
    player = Player(
        user_id=user_id,
        first_name=user_states[user_id]['first_name'],
        last_name=user_states[user_id]['last_name'],
        username=update.effective_user.username
    )
    
    # Проверяем, можно ли добавить еще игрока
    if len(lobby.players) >= 10:  # MAX_PLAYERS
        await update.message.reply_text("К сожалению, лобби уже заполнено.")
        return ConversationHandler.END
    
    if lobby.game_state != GameState.WAITING_FOR_PLAYERS:
        await update.message.reply_text("К сожалению, в этом лобби уже началась игра.")
        return ConversationHandler.END
    
    lobby.add_player(player)
    user_to_lobby[user_id] = lobby_id
    
    await update.message.reply_text(
        f"Вы присоединились к лобби ID: {lobby_id}"
    )
    
    # Обновляем информацию о лобби для всех игроков
    await broadcast_lobby_update(context, lobby)
    
    return IN_LOBBY


async def lobby_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /lobby"""
    user_id = update.effective_user.id
    
    # Проверяем, состоит ли пользователь в лобби
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await update.message.reply_text(
            "Вы не состоите ни в одном лобби. Используйте /start для создания нового."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    # Отправляем информацию о лобби
    await send_lobby_info(update, context, lobby)
    
    return IN_LOBBY


async def leave_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /leave"""
    user_id = update.effective_user.id
    
    # Проверяем, состоит ли пользователь в лобби
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await update.message.reply_text(
            "Вы не состоите ни в одном лобби."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    # Удаляем игрока из лобби
    lobby.remove_player(user_id)
    del user_to_lobby[user_id]
    
    await update.message.reply_text(
        "Вы покинули лобби."
    )
    
    # Если в лобби не осталось игроков, удаляем его
    if not lobby.players:
        del lobbies[lobby_id]
        return ConversationHandler.END
    
    # Обновляем информацию о лобби для оставшихся игроков
    await broadcast_lobby_update(context, lobby)
    
    return ConversationHandler.END


async def start_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /startgame"""
    user_id = update.effective_user.id
    
    # Проверяем, состоит ли пользователь в лобби
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await update.message.reply_text(
            "Вы не состоите ни в одном лобби. Используйте /start для создания нового."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    # Проверяем, является ли пользователь капитаном
    if not lobby.players[user_id].is_captain:
        await update.message.reply_text(
            "Только капитан может начать игру."
        )
        return IN_LOBBY
    
    # Проверяем минимальное количество игроков
    if len(lobby.players) < 1:  # MIN_PLAYERS
        await update.message.reply_text(
            "Для начала игры необходимо минимум 2 игрока."
        )
        return IN_LOBBY
    
    # Изменяем состояние игры
    lobby.game_state = GameState.WAITING_FOR_SCENARIO
    
    # Отправляем сообщение капитану с вариантами
    keyboard = [
        [
            InlineKeyboardButton("Ввести свой сценарий", callback_data="enter_scenario"),
            InlineKeyboardButton("Случайный сценарий", callback_data="random_scenario")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Игра начинается! Выберите сценарий:",
        reply_markup=reply_markup
    )
    
    # Обновляем информацию о лобби для всех игроков
    await broadcast_lobby_update(context, lobby)
    
    return IN_LOBBY


async def send_lobby_info(update: Update, context: ContextTypes.DEFAULT_TYPE, lobby: Lobby):
    """Отправляет информацию о лобби"""
    # Формируем список игроков
    players_info = []
    for player in lobby.players.values():
        captain_mark = "👑 " if player.is_captain else ""
        players_info.append(f"{captain_mark}{player.first_name} {player.last_name}")
    
    players_list = "\n".join(players_info)
    
    # Кнопки в зависимости от состояния игры и роли пользователя
    keyboard = []
    
    # Кнопка для приглашения игроков (только в состоянии ожидания)
    if lobby.game_state == GameState.WAITING_FOR_PLAYERS:
        keyboard.append([
            InlineKeyboardButton("Пригласить игроков", switch_inline_query=f"{lobby.id}")
        ])
    
    # Кнопка для начала игры (только для капитана и в состоянии ожидания)
    user_id = update.effective_user.id
    if user_id in lobby.players and lobby.players[user_id].is_captain and lobby.game_state == GameState.WAITING_FOR_PLAYERS:
        keyboard.append([
            InlineKeyboardButton("Начать игру", callback_data="start_game")
        ])
    
    # Кнопка для выхода из лобби
    keyboard.append([
        InlineKeyboardButton("Покинуть лобби", callback_data="leave_lobby")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Формируем сообщение в зависимости от состояния игры
    if lobby.game_state == GameState.WAITING_FOR_PLAYERS:
        status_text = "Ожидание игроков"
    elif lobby.game_state == GameState.WAITING_FOR_SCENARIO:
        status_text = "Ожидание выбора сценария капитаном"
    elif lobby.game_state == GameState.WAITING_FOR_ACTIONS:
        status_text = "Ожидание действий игроков"
    elif lobby.game_state == GameState.PROCESSING_RESULTS:
        status_text = "Обработка результатов"
    else:
        status_text = "Игра окончена"
    
    message = (
        f"🎮 ЛОББИ ID: `{lobby.id}`\n\n"
        f"Статус: {status_text}\n"
        f"Режим: {lobby.game_mode.value}\n\n"
        f"Игроки ({len(lobby.players)}):\n{players_list}"
    )
    
    # Если есть сценарий, добавляем его
    if lobby.scenario and lobby.game_state in [GameState.WAITING_FOR_ACTIONS, GameState.PROCESSING_RESULTS]:
        message += f"\n\nСценарий:\n{lobby.scenario}"
    
    # Если игра в процессе ожидания действий, добавляем информацию о сдавших действия
    if lobby.game_state == GameState.WAITING_FOR_ACTIONS:
        submitted = [f"{p.first_name} {p.last_name}" for p in lobby.get_players_with_actions().values()]
        waiting = [f"{p.first_name} {p.last_name}" for p in lobby.get_players_without_actions().values()]
        
        message += f"\n\nОтправили действия ({len(submitted)}/{len(lobby.players)}):\n"
        message += "\n".join(submitted) if submitted else "Никто пока не отправил"
        
        message += f"\n\nОжидаем действия от:\n"
        message += "\n".join(waiting) if waiting else "Все отправили свои действия"
    
    sent_message = await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    # Сохраняем ID сообщения и чата для обновления
    lobby.message_id = sent_message.message_id
    lobby.chat_id = sent_message.chat_id


async def broadcast_lobby_update(context: ContextTypes.DEFAULT_TYPE, lobby: Lobby):
    """Обновляет информацию о лобби для всех игроков"""
    # Формируем список игроков
    players_info = []
    for player in lobby.players.values():
        captain_mark = "👑 " if player.is_captain else ""
        players_info.append(f"{captain_mark}{player.first_name} {player.last_name}")
    
    players_list = "\n".join(players_info)
    
    # Формируем сообщение в зависимости от состояния игры
    if lobby.game_state == GameState.WAITING_FOR_PLAYERS:
        status_text = "Ожидание игроков"
    elif lobby.game_state == GameState.WAITING_FOR_SCENARIO:
        status_text = "Ожидание выбора сценария капитаном"
    elif lobby.game_state == GameState.WAITING_FOR_ACTIONS:
        status_text = "Ожидание действий игроков"
    elif lobby.game_state == GameState.PROCESSING_RESULTS:
        status_text = "Обработка результатов"
    else:
        status_text = "Игра окончена"
    
    message = (
        f"🎮 ЛОББИ ID: `{lobby.id}`\n\n"
        f"Статус: {status_text}\n"
        f"Режим: {lobby.game_mode.value}\n\n"
        f"Игроки ({len(lobby.players)}):\n{players_list}"
    )
    
    # Если есть сценарий, добавляем его
    if lobby.scenario and lobby.game_state in [GameState.WAITING_FOR_ACTIONS, GameState.PROCESSING_RESULTS]:
        message += f"\n\nСценарий:\n{lobby.scenario}"
    
    # Если игра в процессе ожидания действий, добавляем информацию о сдавших действия
    if lobby.game_state == GameState.WAITING_FOR_ACTIONS:
        submitted = [f"{p.first_name} {p.last_name}" for p in lobby.get_players_with_actions().values()]
        waiting = [f"{p.first_name} {p.last_name}" for p in lobby.get_players_without_actions().values()]
        
        message += f"\n\nОтправили действия ({len(submitted)}/{len(lobby.players)}):\n"
        message += "\n".join(submitted) if submitted else "Никто пока не отправил"
        
        message += f"\n\nОжидаем действия от:\n"
        message += "\n".join(waiting) if waiting else "Все отправили свои действия"
    
    # Отправляем обновление каждому игроку
    for user_id in lobby.players:
        # Кнопки в зависимости от состояния игры и роли пользователя
        keyboard = []
        
        # Кнопка для приглашения игроков (только в состоянии ожидания)
        if lobby.game_state == GameState.WAITING_FOR_PLAYERS:
            keyboard.append([
                InlineKeyboardButton("Пригласить игроков", switch_inline_query=f"join_{lobby.id}")
            ])
        
        # Кнопка для начала игры (только для капитана и в состоянии ожидания)
        if user_id in lobby.players and lobby.players[user_id].is_captain and lobby.game_state == GameState.WAITING_FOR_PLAYERS:
            keyboard.append([
                InlineKeyboardButton("Начать игру", callback_data="start_game")
            ])
        
        # Кнопка для выхода из лобби
        keyboard.append([
            InlineKeyboardButton("Покинуть лобби", callback_data="leave_lobby")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"Ошибка при отправке обновления игроку {user_id}: {e}")


async def leave_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик кнопки 'Покинуть лобби'"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Проверяем, состоит ли пользователь в лобби
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await query.edit_message_text(
            "Вы не состоите ни в одном лобби."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    # Удаляем игрока из лобби
    lobby.remove_player(user_id)
    del user_to_lobby[user_id]
    
    await query.edit_message_text(
        "Вы покинули лобби."
    )
    
    # Если в лобби не осталось игроков, удаляем его
    if not lobby.players:
        del lobbies[lobby_id]
        return ConversationHandler.END
    
    # Обновляем информацию о лобби для оставшихся игроков
    await broadcast_lobby_update(context, lobby)
    
    return ConversationHandler.END


async def start_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик кнопки 'Начать игру'"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Проверяем, состоит ли пользователь в лобби
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await query.edit_message_text(
            "Вы не состоите ни в одном лобби. Используйте /start для создания нового."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    # Проверяем, является ли пользователь капитаном
    if not lobby.players[user_id].is_captain:
        await query.message.reply_text(
            "Только капитан может начать игру."
        )
        return IN_LOBBY
    
    # Проверяем минимальное количество игроков
    if len(lobby.players) < 1:  # MIN_PLAYERS
        await query.message.reply_text(
            "Для начала игры необходимо минимум 2 игрока."
        )
        return IN_LOBBY
    
    # Изменяем состояние игры
    lobby.game_state = GameState.WAITING_FOR_SCENARIO
    
    # Отправляем сообщение капитану с вариантами
    keyboard = [
        [
            InlineKeyboardButton("Ввести свой сценарий", callback_data="enter_scenario"),
            InlineKeyboardButton("Случайный сценарий", callback_data="random_scenario")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(
        "Игра начинается! Выберите сценарий:",
        reply_markup=reply_markup
    )
    
    # Обновляем информацию о лобби для всех игроков
    await broadcast_lobby_update(context, lobby)
    
    return IN_LOBBY


async def enter_scenario_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик кнопки 'Ввести свой сценарий'"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Проверяем, состоит ли пользователь в лобби
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await query.edit_message_text(
            "Вы не состоите ни в одном лобби. Используйте /start для создания нового."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    # Проверяем, является ли пользователь капитаном
    if not lobby.players[user_id].is_captain:
        await query.message.reply_text(
            "Только капитан может выбирать сценарий."
        )
        return IN_LOBBY
    
    # Устанавливаем ожидание ввода сценария
    user_states[user_id]['awaiting_scenario'] = True
    
    await query.message.reply_text(
        "Введите ваш сценарий для игры (до 500 символов):"
    )
    
    return IN_LOBBY


async def random_scenario_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик кнопки 'Случайный сценарий'"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Проверяем, состоит ли пользователь в лобби
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await query.edit_message_text(
            "Вы не состоите ни в одном лобби. Используйте /start для создания нового."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    # Проверяем, является ли пользователь капитаном
    if not lobby.players[user_id].is_captain:
        await query.message.reply_text(
            "Только капитан может выбирать сценарий."
        )
        return IN_LOBBY
    
    # Получаем случайный сценарий
    scenario = get_random_scenario()
    
    # Устанавливаем сценарий и переходим к сбору действий
    lobby.scenario = scenario
    lobby.game_state = GameState.WAITING_FOR_ACTIONS
    
    # Сбрасываем действия игроков (на случай, если это новый раунд)
    lobby.reset_actions()
    
    await query.message.reply_text(
        f"Выбран случайный сценарий!\n\n{scenario}\n\nИгроки могут теперь отправлять свои действия."
    )
    
    # Обновляем информацию о лобби для всех игроков
    await broadcast_lobby_update(context, lobby)
    
    # Отправляем всем игрокам запрос на действия
    for player_id in lobby.players:
        if player_id != user_id:  # Капитану уже отправили сообщение выше
            try:
                await context.bot.send_message(
                    chat_id=player_id,
                    text=f"Новый сценарий от капитана:\n\n{scenario}\n\nОпишите ваши действия:"
                )
            except Exception as e:
                print(f"Ошибка при отправке сценария игроку {player_id}: {e}")
    
    return IN_LOBBY


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик текстовых сообщений в лобби"""
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    # Если пользователь не в лобби, игнорируем сообщение
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    # Проверяем, ожидает ли капитан ввода сценария
    if user_id in user_states and user_states.get(user_id, {}).get('awaiting_scenario', False):
        # Проверяем валидность сценария
        is_valid, error_message = validate_scenario(message_text)
        if not is_valid:
            await update.message.reply_text(f"Ошибка: {error_message}. Попробуйте еще раз:")
            return IN_LOBBY
        
        # Устанавливаем сценарий и переходим к сбору действий
        lobby.scenario = message_text
        lobby.game_state = GameState.WAITING_FOR_ACTIONS
        
        # Сбрасываем флаг ожидания сценария
        user_states[user_id]['awaiting_scenario'] = False
        
        # Сбрасываем действия игроков (на случай, если это новый раунд)
        lobby.reset_actions()
        
        await update.message.reply_text(
            f"Сценарий принят!\n\n{message_text}\n\nИгроки могут теперь отправлять свои действия."
        )
        
        # Обновляем информацию о лобби для всех игроков
        await broadcast_lobby_update(context, lobby)
        
        # Отправляем всем игрокам запрос на действия
        for player_id in lobby.players:
            if player_id != user_id:  # Капитану уже отправили сообщение выше
                try:
                    await context.bot.send_message(
                        chat_id=player_id,
                        text=f"Новый сценарий от капитана:\n\n{message_text}\n\nОпишите ваши действия:"
                    )
                except Exception as e:
                    print(f"Ошибка при отправке сценария игроку {player_id}: {e}")
        
        return IN_LOBBY
    
    # Если игра в состоянии ожидания действий, и у игрока еще нет действия
    if lobby.game_state == GameState.WAITING_FOR_ACTIONS and lobby.players[user_id].action is None:
        from utils.helpers import validate_action
        
        # Проверяем валидность действия
        is_valid, error_message = validate_action(message_text)
        if not is_valid:
            await update.message.reply_text(f"Ошибка: {error_message}. Попробуйте еще раз:")
            return IN_LOBBY
        
        # Устанавливаем действие игрока
        lobby.players[user_id].action = message_text
        
        await update.message.reply_text(
            f"Ваше действие принято:\n\n{message_text}\n\nОжидаем действия от других игроков."
        )
        
        # Обновляем информацию о лобби для всех игроков
        await broadcast_lobby_update(context, lobby)
        
        # Если все игроки отправили действия, запускаем обработку результатов
        if lobby.all_players_submitted_actions():
            # Изменяем состояние игры
            lobby.game_state = GameState.PROCESSING_RESULTS
            
            # Обновляем информацию о лобби для всех игроков
            await broadcast_lobby_update(context, lobby)
            
            # Запускаем обработку результатов
            await process_game_results(context, lobby)
        
        return IN_LOBBY
    
    # Если ничего из вышеперечисленного не подходит, просто игнорируем сообщение
    return IN_LOBBY


async def process_game_results(context: ContextTypes.DEFAULT_TYPE, lobby: Lobby):
    """Обрабатывает результаты игры"""
    from services.ai.gemini_service import GeminiService
    import logging
    import re
    
    logger = logging.getLogger(__name__)
    
    # Отправляем сообщение о начале обработки результатов
    for player_id in lobby.players:
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text="Обработка результатов... Пожалуйста, подождите."
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения игроку {player_id}: {e}")
    
    try:
        # Создаем экземпляр сервиса Gemini
        gemini_service = GeminiService()
        logger.info(f"Gemini сервис создан. API ключ установлен: {bool(gemini_service.model)}")
        
        # Логируем информацию о сценарии и игроках для отладки
        logger.info(f"Сценарий: {lobby.scenario}")
        
        # Проверяем, что у всех игроков есть действия
        for player_id, player in lobby.players.items():
            logger.info(f"Игрок {player.first_name} {player.last_name}, действие: {player.action}")
            if player.action is None:
                logger.error(f"У игрока {player.first_name} {player.last_name} нет действия")
                raise ValueError(f"У игрока {player.first_name} {player.last_name} нет действия")
        
        # Получаем результаты от Gemini API
        logger.info("Отправляем запрос к Gemini API...")
        try:
            narrative = await gemini_service.evaluate_survival(lobby.scenario, lobby.players, lobby.game_mode)
            logger.info(f"Получен ответ от Gemini API. Длина нарратива: {len(narrative)},")
        except Exception as api_error:
            logger.error(f"Ошибка Gemini API: {api_error}")
            raise api_error
        
        # Функция для экранирования символов Markdown
        def escape_markdown(text):
            # Экранирование специальных символов Markdown
            escape_chars = r'_*[]()~`>#+-=|{}.!'
            return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
        
        # Отправляем результаты всем игрокам
        for player_id in lobby.players:
            try:
                # Отправляем без parse_mode, чтобы избежать проблем с форматированием
                await context.bot.send_message(
                    chat_id=player_id,
                    text=f"{narrative}"
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке результатов игроку {player_id}: {e}")
        
        # Переводим игру обратно в режим ожидания выбора сценария для нового раунда
        lobby.game_state = GameState.WAITING_FOR_SCENARIO
        
        # Отправляем капитану запрос на новый сценарий
        captain = lobby.get_captain()
        if captain:
            keyboard = [
                [
                    InlineKeyboardButton("Ввести свой сценарий", callback_data="enter_scenario"),
                    InlineKeyboardButton("Случайный сценарий", callback_data="random_scenario")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await context.bot.send_message(
                    chat_id=captain.user_id,
                    text="Раунд завершен! Выберите сценарий для нового раунда:",
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке запроса на новый сценарий капитану {captain.user_id}: {e}")
        
        # Обновляем информацию о лобби для всех игроков
        await broadcast_lobby_update(context, lobby)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке результатов: {str(e)}", exc_info=True)
        
        # В случае ошибки, переводим игру обратно в режим ожидания выбора сценария
        lobby.game_state = GameState.WAITING_FOR_SCENARIO
        
        # Отправляем сообщение об ошибке всем игрокам
        for player_id in lobby.players:
            try:
                await context.bot.send_message(
                    chat_id=player_id,
                    text=f"Произошла ошибка при обработке результатов. Пожалуйста, попробуйте еще раз.\n{str(e)}"
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения об ошибке игроку {player_id}: {e}")
        
        # Обновляем информацию о лобби для всех игроков
        await broadcast_lobby_update(context, lobby)


async def handle_game_mode_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик выбора режима игры"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Проверяем, состоит ли пользователь в лобби
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await query.edit_message_text(
            "Вы не состоите ни в одном лобби. Используйте /start для создания нового."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    # Проверяем, является ли пользователь капитаном
    if not lobby.players[user_id].is_captain:
        await query.message.reply_text(
            "Только капитан может выбирать режим игры."
        )
        return IN_LOBBY
    
    # Устанавливаем режим игры в зависимости от нажатой кнопки
    if query.data == "mode_every_man":
        lobby.game_mode = GameMode.EVERY_MAN_FOR_HIMSELF
        mode_name = "Каждый сам за себя"
    elif query.data == "mode_brotherhood":
        lobby.game_mode = GameMode.BROTHERHOOD
        mode_name = "Братство (кооператив)"
    else:
        # Неизвестный режим, используем режим по умолчанию
        lobby.game_mode = GameMode.EVERY_MAN_FOR_HIMSELF
        mode_name = "Каждый сам за себя"
    
    # Сообщаем о выборе режима
    await query.edit_message_text(
        f"Отлично, {lobby.players[user_id].first_name} {lobby.players[user_id].last_name}!\n\n"
        f"Лобби создано. Вы назначены капитаном.\n"
        f"ID лобби: `{lobby_id}`\n\n"
        f"Выбран режим игры: {mode_name}"
    )
    
    # Обновляем информацию о лобби для всех игроков
    await broadcast_lobby_update(context, lobby)
    
    return IN_LOBBY


async def game_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик выбора режима игры"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Проверяем, состоит ли пользователь в лобби
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await query.edit_message_text(
            "Вы не состоите ни в одном лобби. Используйте /start для создания нового."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    # Проверяем, является ли пользователь капитаном
    if not lobby.players[user_id].is_captain:
        await query.message.reply_text(
            "Только капитан может выбирать режим игры."
        )
        return IN_LOBBY
    
    # Устанавливаем режим игры в зависимости от выбора
    if query.data == "mode_every_man":
        lobby.game_mode = GameMode.EVERY_MAN_FOR_HIMSELF
        mode_name = "Каждый сам за себя"
    elif query.data == "mode_brotherhood":
        lobby.game_mode = GameMode.BROTHERHOOD
        mode_name = "Братство (кооператив)"
    else:
        # Неизвестный режим, используем режим по умолчанию
        lobby.game_mode = GameMode.EVERY_MAN_FOR_HIMSELF
        mode_name = "Каждый сам за себя"
    
    # Сообщаем о выборе режима
    await query.edit_message_text(
        f"Отлично, {lobby.players[user_id].first_name} {lobby.players[user_id].last_name}!\n\n"
        f"Лобби создано. Вы назначены капитаном.\n"
        f"ID лобби: `{lobby_id}`\n\n"
        f"Выбран режим игры: {mode_name}",
        parse_mode='Markdown'
    )
    
    # Обновляем информацию о лобби для всех игроков
    await broadcast_lobby_update(context, lobby)
    
    return IN_LOBBY