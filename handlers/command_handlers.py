from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from models import Player, Lobby, GameState, GameMode, user_states, lobbies, user_to_lobby
from utils.helpers import generate_lobby_id, validate_name, get_random_scenario, validate_scenario



ENTER_FULL_NAME, WAITING_FOR_LOBBY_OR_CREATE, IN_LOBBY = range(3)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    
    
    if user_id in user_to_lobby and user_to_lobby[user_id] in lobbies:
        lobby_id = user_to_lobby[user_id]
        await update.message.reply_text(
            f"Вы уже состоите в лобби. Используйте /lobby для просмотра информации о лобби."
        )
        return IN_LOBBY
    
    
    await update.message.reply_text(
        "Добро пожаловать в игру 'Против ИИ'!\n\n"
        "Вам предстоит испытать свои навыки выживания в различных сценариях, "
        "соревнуясь с другими игроками и нейросетью.\n\n"
        "Для начала, пожалуйста, введите своё имя и фамилию:"
    )
    
    
    user_states[user_id] = {}
    
    return ENTER_FULL_NAME


async def enter_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик ввода полного имени"""
    user_id = update.effective_user.id
    full_name = update.message.text.strip()
    
    
    if user_id in user_states and 'join_lobby_id' in user_states[user_id]:
        
        is_valid, error_message = validate_name(full_name)
        if not is_valid:
            await update.message.reply_text(f"Ошибка: {error_message}. Пожалуйста, введите полное имя еще раз:")
            return ENTER_FULL_NAME
        
        
        name_parts = full_name.split(maxsplit=1)
        user_states[user_id]['first_name'] = name_parts[0]
        user_states[user_id]['last_name'] = name_parts[1] if len(name_parts) > 1 else ""
        
        
        lobby_id = user_states[user_id]['join_lobby_id']
        
        
        if lobby_id not in lobbies:
            await update.message.reply_text("Лобби с таким ID не найдено. Создаём новое лобби.")
            return await create_new_lobby(update, context, user_id)
        
        
        lobby = lobbies[lobby_id]
        
        
        if len(lobby.players) >= 10:  
            await update.message.reply_text("К сожалению, лобби уже заполнено. Создаём новое лобби.")
            return await create_new_lobby(update, context, user_id)
        
        if lobby.game_state != GameState.WAITING_FOR_PLAYERS:
            await update.message.reply_text("К сожалению, в этом лобби уже началась игра. Создаём новое лобби.")
            return await create_new_lobby(update, context, user_id)
        
        
        player = Player(
            user_id=user_id,
            first_name=user_states[user_id]['first_name'],
            last_name=user_states[user_id]['last_name'],
            username=update.effective_user.username
        )
        
        lobby.add_player(player)
        user_to_lobby[user_id] = lobby_id
        
        
        user_states[user_id].pop('join_lobby_id', None)
        
        await update.message.reply_text(
            f"Вы присоединились к лобби ID: {lobby_id}"
        )
        
        
        await broadcast_lobby_update(context, lobby)
        
        return IN_LOBBY
    
    
    is_valid, error_message = validate_name(full_name)
    if not is_valid:
        await update.message.reply_text(f"Ошибка: {error_message}. Пожалуйста, введите полное имя еще раз:")
        return ENTER_FULL_NAME
    
    
    name_parts = full_name.split(maxsplit=1)
    user_states[user_id]['first_name'] = name_parts[0]
    user_states[user_id]['last_name'] = name_parts[1] if len(name_parts) > 1 else ""
    
    
    await update.message.reply_text(
        f"Отлично, {user_states[user_id]['first_name']} {user_states[user_id]['last_name']}!\n\n"
        f"Теперь вы можете:\n"
        f"1. Ввести ID существующего лобби, чтобы присоединиться к нему\n"
        f"2. Или просто нажмите кнопку ниже, чтобы создать новое лобби"
    )
    
    
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
    
    
    
    lobby_id = text
    
    
    if lobby_id not in lobbies:
        await update.message.reply_text(
            "Лобби с таким ID не найдено. Проверьте ID и попробуйте снова, "
            "или создайте новое лобби кнопкой ниже."
        )
        
        
        keyboard = [
            [InlineKeyboardButton("Создать новое лобби", callback_data="create_new_lobby")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=reply_markup
        )
        
        return WAITING_FOR_LOBBY_OR_CREATE
    
    
    lobby = lobbies[lobby_id]
    
    
    if len(lobby.players) >= 10:  
        await update.message.reply_text(
            "К сожалению, лобби уже заполнено. Создайте новое лобби."
        )
        return WAITING_FOR_LOBBY_OR_CREATE
    
    if lobby.game_state != GameState.WAITING_FOR_PLAYERS:
        await update.message.reply_text(
            "К сожалению, в этом лобби уже началась игра. Создайте новое лобби."
        )
        return WAITING_FOR_LOBBY_OR_CREATE
    
    
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
    
    player = Player(
        user_id=user_id,
        first_name=user_states[user_id]['first_name'],
        last_name=user_states[user_id]['last_name'],
        username=update.effective_user.username if not is_callback else update.callback_query.from_user.username
    )
    
    
    lobby_id = generate_lobby_id()
    lobby = Lobby(id=lobby_id)
    lobby.add_player(player)
    
    
    lobbies[lobby_id] = lobby
    user_to_lobby[user_id] = lobby_id
    
    
    message_text = (
        f"Отлично, {player.first_name} {player.last_name}!\n\n"
        f"Лобби создано. Вы назначены капитаном.\n"
        f"ID лобби: `{lobby_id}`\n\n"
    )
    
    
    keyboard = [
        [
            InlineKeyboardButton("Каждый сам за себя", callback_data="mode_every_man"),
            InlineKeyboardButton("Братство (кооператив)", callback_data="mode_brotherhood")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    
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
    
    
    if lobby_id not in lobbies:
        await update.message.reply_text("Лобби с таким ID не найдено. Проверьте ID и попробуйте снова.")
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    
    
    if user_id in user_to_lobby:
        existing_lobby_id = user_to_lobby[user_id]
        
        
        if existing_lobby_id == lobby_id:
            await update.message.reply_text("Вы уже состоите в этом лобби.")
            return IN_LOBBY
        
        
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
    
    
    if user_id not in user_states or 'first_name' not in user_states[user_id]:
        user_states[user_id] = {}
        await update.message.reply_text(
            "Для присоединения к лобби, сначала введите свое полное имя (имя и фамилию):"
        )
        
        user_states[user_id]['join_lobby_id'] = lobby_id
        return ENTER_FULL_NAME
    
    
    lobby = lobbies[lobby_id]
    
    
    player = Player(
        user_id=user_id,
        first_name=user_states[user_id]['first_name'],
        last_name=user_states[user_id]['last_name'],
        username=update.effective_user.username
    )
    
    
    if len(lobby.players) >= 10:  
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
    
    
    await broadcast_lobby_update(context, lobby)
    
    return IN_LOBBY


async def lobby_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /lobby"""
    user_id = update.effective_user.id
    
    
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await update.message.reply_text(
            "Вы не состоите ни в одном лобби. Используйте /start для создания нового."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    
    await send_lobby_info(update, context, lobby)
    
    return IN_LOBBY


async def leave_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /leave"""
    user_id = update.effective_user.id
    
    
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await update.message.reply_text(
            "Вы не состоите ни в одном лобби."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    
    lobby.remove_player(user_id)
    del user_to_lobby[user_id]
    
    await update.message.reply_text(
        "Вы покинули лобби."
    )
    
    
    if not lobby.players:
        del lobbies[lobby_id]
        return ConversationHandler.END
    
    
    await broadcast_lobby_update(context, lobby)
    
    return ConversationHandler.END


async def start_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /startgame"""
    user_id = update.effective_user.id
    
    
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await update.message.reply_text(
            "Вы не состоите ни в одном лобби. Используйте /start для создания нового."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    
    if not lobby.players[user_id].is_captain:
        await update.message.reply_text(
            "Только капитан может начать игру."
        )
        return IN_LOBBY
    
    
    if len(lobby.players) < 1:  
        await update.message.reply_text(
            "Для начала игры необходимо минимум 2 игрока."
        )
        return IN_LOBBY
    
    
    lobby.game_state = GameState.WAITING_FOR_SCENARIO
    
    
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
    
    
    await broadcast_lobby_update(context, lobby)
    
    return IN_LOBBY


async def send_lobby_info(update: Update, context: ContextTypes.DEFAULT_TYPE, lobby: Lobby):
    """Отправляет информацию о лобби"""
    
    players_info = []
    for player in lobby.players.values():
        captain_mark = "👑 " if player.is_captain else ""
        players_info.append(f"{captain_mark}{player.first_name} {player.last_name}")
    
    players_list = "\n".join(players_info)
    
    
    keyboard = []
    
    
    if lobby.game_state == GameState.WAITING_FOR_PLAYERS:
        keyboard.append([
            InlineKeyboardButton("Пригласить игроков", switch_inline_query=f"{lobby.id}")
        ])
    
    
    user_id = update.effective_user.id
    if user_id in lobby.players and lobby.players[user_id].is_captain and lobby.game_state == GameState.WAITING_FOR_PLAYERS:
        keyboard.append([
            InlineKeyboardButton("Начать игру", callback_data="start_game")
        ])
    
    
    keyboard.append([
        InlineKeyboardButton("Покинуть лобби", callback_data="leave_lobby")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    
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
    
    
    if lobby.scenario and lobby.game_state in [GameState.WAITING_FOR_ACTIONS, GameState.PROCESSING_RESULTS]:
        message += f"\n\nСценарий:\n{lobby.scenario}"
    
    
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
    
    
    lobby.message_id = sent_message.message_id
    lobby.chat_id = sent_message.chat_id


async def broadcast_lobby_update(context: ContextTypes.DEFAULT_TYPE, lobby: Lobby):
    """Обновляет информацию о лобби для всех игроков"""
    
    players_info = []
    for player in lobby.players.values():
        captain_mark = "👑 " if player.is_captain else ""
        players_info.append(f"{captain_mark}{player.first_name} {player.last_name}")
    
    players_list = "\n".join(players_info)
    
    
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
    
    
    if lobby.scenario and lobby.game_state in [GameState.WAITING_FOR_ACTIONS, GameState.PROCESSING_RESULTS]:
        message += f"\n\nСценарий:\n{lobby.scenario}"
    
    
    if lobby.game_state == GameState.WAITING_FOR_ACTIONS:
        submitted = [f"{p.first_name} {p.last_name}" for p in lobby.get_players_with_actions().values()]
        waiting = [f"{p.first_name} {p.last_name}" for p in lobby.get_players_without_actions().values()]
        
        message += f"\n\nОтправили действия ({len(submitted)}/{len(lobby.players)}):\n"
        message += "\n".join(submitted) if submitted else "Никто пока не отправил"
        
        message += f"\n\nОжидаем действия от:\n"
        message += "\n".join(waiting) if waiting else "Все отправили свои действия"
    
    
    for user_id in lobby.players:
        
        keyboard = []
        
        
        if lobby.game_state == GameState.WAITING_FOR_PLAYERS:
            keyboard.append([
                InlineKeyboardButton("Пригласить игроков", switch_inline_query=f"join_{lobby.id}")
            ])
        
        
        if user_id in lobby.players and lobby.players[user_id].is_captain and lobby.game_state == GameState.WAITING_FOR_PLAYERS:
            keyboard.append([
                InlineKeyboardButton("Начать игру", callback_data="start_game")
            ])
        
        
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
    
    
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await query.edit_message_text(
            "Вы не состоите ни в одном лобби."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    
    lobby.remove_player(user_id)
    del user_to_lobby[user_id]
    
    await query.edit_message_text(
        "Вы покинули лобби."
    )
    
    
    if not lobby.players:
        del lobbies[lobby_id]
        return ConversationHandler.END
    
    
    await broadcast_lobby_update(context, lobby)
    
    return ConversationHandler.END


async def start_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик кнопки 'Начать игру'"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await query.edit_message_text(
            "Вы не состоите ни в одном лобби. Используйте /start для создания нового."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    
    if not lobby.players[user_id].is_captain:
        await query.message.reply_text(
            "Только капитан может начать игру."
        )
        return IN_LOBBY
    
    
    if len(lobby.players) < 1:  
        await query.message.reply_text(
            "Для начала игры необходимо минимум 2 игрока."
        )
        return IN_LOBBY
    
    
    lobby.game_state = GameState.WAITING_FOR_SCENARIO
    
    
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
    
    
    await broadcast_lobby_update(context, lobby)
    
    return IN_LOBBY


async def enter_scenario_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик кнопки 'Ввести свой сценарий'"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await query.edit_message_text(
            "Вы не состоите ни в одном лобби. Используйте /start для создания нового."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    
    if not lobby.players[user_id].is_captain:
        await query.message.reply_text(
            "Только капитан может выбирать сценарий."
        )
        return IN_LOBBY
    
    
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
    
    
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await query.edit_message_text(
            "Вы не состоите ни в одном лобби. Используйте /start для создания нового."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    
    if not lobby.players[user_id].is_captain:
        await query.message.reply_text(
            "Только капитан может выбирать сценарий."
        )
        return IN_LOBBY
    
    
    scenario = get_random_scenario()
    
    
    lobby.scenario = scenario
    lobby.game_state = GameState.WAITING_FOR_ACTIONS
    
    
    lobby.reset_actions()
    
    await query.message.reply_text(
        f"Выбран случайный сценарий!\n\n{scenario}\n\nИгроки могут теперь отправлять свои действия."
    )
    
    
    await broadcast_lobby_update(context, lobby)
    
    
    for player_id in lobby.players:
        if player_id != user_id:  
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
    
    
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    
    if user_id in user_states and user_states.get(user_id, {}).get('awaiting_scenario', False):
        
        is_valid, error_message = validate_scenario(message_text)
        if not is_valid:
            await update.message.reply_text(f"Ошибка: {error_message}. Попробуйте еще раз:")
            return IN_LOBBY
        
        
        lobby.scenario = message_text
        lobby.game_state = GameState.WAITING_FOR_ACTIONS
        
        
        user_states[user_id]['awaiting_scenario'] = False
        
        
        lobby.reset_actions()
        
        await update.message.reply_text(
            f"Сценарий принят!\n\n{message_text}\n\nИгроки могут теперь отправлять свои действия."
        )
        
        
        await broadcast_lobby_update(context, lobby)
        
        
        for player_id in lobby.players:
            if player_id != user_id:  
                try:
                    await context.bot.send_message(
                        chat_id=player_id,
                        text=f"Новый сценарий от капитана:\n\n{message_text}\n\nОпишите ваши действия:"
                    )
                except Exception as e:
                    print(f"Ошибка при отправке сценария игроку {player_id}: {e}")
        
        return IN_LOBBY
    
    
    if lobby.game_state == GameState.WAITING_FOR_ACTIONS and lobby.players[user_id].action is None:
        from utils.helpers import validate_action
        
        
        is_valid, error_message = validate_action(message_text)
        if not is_valid:
            await update.message.reply_text(f"Ошибка: {error_message}. Попробуйте еще раз:")
            return IN_LOBBY
        
        
        lobby.players[user_id].action = message_text
        
        await update.message.reply_text(
            f"Ваше действие принято:\n\n{message_text}\n\nОжидаем действия от других игроков."
        )
        
        
        await broadcast_lobby_update(context, lobby)
        
        
        if lobby.all_players_submitted_actions():
            
            lobby.game_state = GameState.PROCESSING_RESULTS
            
            
            await broadcast_lobby_update(context, lobby)
            
            
            await process_game_results(context, lobby)
        
        return IN_LOBBY
    
    
    return IN_LOBBY


async def process_game_results(context: ContextTypes.DEFAULT_TYPE, lobby: Lobby):
    """Обрабатывает результаты игры"""
    from services.ai.gemini_service import GeminiService
    import logging
    import re
    
    logger = logging.getLogger(__name__)
    
    
    for player_id in lobby.players:
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text="Обработка результатов... Пожалуйста, подождите."
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения игроку {player_id}: {e}")
    
    try:
        
        gemini_service = GeminiService()
        logger.info(f"Gemini сервис создан. API ключ установлен: {bool(gemini_service.model)}")
        
        
        logger.info(f"Сценарий: {lobby.scenario}")
        
        
        for player_id, player in lobby.players.items():
            logger.info(f"Игрок {player.first_name} {player.last_name}, действие: {player.action}")
            if player.action is None:
                logger.error(f"У игрока {player.first_name} {player.last_name} нет действия")
                raise ValueError(f"У игрока {player.first_name} {player.last_name} нет действия")
        
        
        logger.info("Отправляем запрос к Gemini API...")
        try:
            narrative = await gemini_service.evaluate_survival(lobby.scenario, lobby.players, lobby.game_mode)
            logger.info(f"Получен ответ от Gemini API. Длина нарратива: {len(narrative)},")
        except Exception as api_error:
            logger.error(f"Ошибка Gemini API: {api_error}")
            raise api_error
        
        
        def escape_markdown(text): 
            escape_chars = r'_*[]()~`>#+-=|{}.!'
            return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
        
        
        for player_id in lobby.players:
            try:
                
                await context.bot.send_message(
                    chat_id=player_id,
                    text=f"{narrative}"
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке результатов игроку {player_id}: {e}")
        
        
        lobby.game_state = GameState.WAITING_FOR_SCENARIO
        
        
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
        
        
        await broadcast_lobby_update(context, lobby)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке результатов: {str(e)}", exc_info=True)
        
        
        lobby.game_state = GameState.WAITING_FOR_SCENARIO
        
        
        for player_id in lobby.players:
            try:
                await context.bot.send_message(
                    chat_id=player_id,
                    text=f"Произошла ошибка при обработке результатов. Пожалуйста, попробуйте еще раз.\n{str(e)}"
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения об ошибке игроку {player_id}: {e}")
        
        
        await broadcast_lobby_update(context, lobby)


async def handle_game_mode_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик выбора режима игры"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await query.edit_message_text(
            "Вы не состоите ни в одном лобби. Используйте /start для создания нового."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    
    if not lobby.players[user_id].is_captain:
        await query.message.reply_text(
            "Только капитан может выбирать режим игры."
        )
        return IN_LOBBY
    
    
    if query.data == "mode_every_man":
        lobby.game_mode = GameMode.EVERY_MAN_FOR_HIMSELF
        mode_name = "Каждый сам за себя"
    elif query.data == "mode_brotherhood":
        lobby.game_mode = GameMode.BROTHERHOOD
        mode_name = "Братство (кооператив)"
    else:
        
        lobby.game_mode = GameMode.EVERY_MAN_FOR_HIMSELF
        mode_name = "Каждый сам за себя"
    
    
    await query.edit_message_text(
        f"Отлично, {lobby.players[user_id].first_name} {lobby.players[user_id].last_name}!\n\n"
        f"Лобби создано. Вы назначены капитаном.\n"
        f"ID лобби: `{lobby_id}`\n\n"
        f"Выбран режим игры: {mode_name}"
    )
    
    
    await broadcast_lobby_update(context, lobby)
    
    return IN_LOBBY


async def game_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик выбора режима игры"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    
    if user_id not in user_to_lobby or user_to_lobby[user_id] not in lobbies:
        await query.edit_message_text(
            "Вы не состоите ни в одном лобби. Используйте /start для создания нового."
        )
        return ConversationHandler.END
    
    lobby_id = user_to_lobby[user_id]
    lobby = lobbies[lobby_id]
    
    
    if not lobby.players[user_id].is_captain:
        await query.message.reply_text(
            "Только капитан может выбирать режим игры."
        )
        return IN_LOBBY
    
    
    if query.data == "mode_every_man":
        lobby.game_mode = GameMode.EVERY_MAN_FOR_HIMSELF
        mode_name = "Каждый сам за себя"
    elif query.data == "mode_brotherhood":
        lobby.game_mode = GameMode.BROTHERHOOD
        mode_name = "Братство (кооператив)"
    else:
        
        lobby.game_mode = GameMode.EVERY_MAN_FOR_HIMSELF
        mode_name = "Каждый сам за себя"
    
    
    await query.edit_message_text(
        f"Отлично, {lobby.players[user_id].first_name} {lobby.players[user_id].last_name}!\n\n"
        f"Лобби создано. Вы назначены капитаном.\n"
        f"ID лобби: `{lobby_id}`\n\n"
        f"Выбран режим игры: {mode_name}",
        parse_mode='Markdown'
    )
    
    
    await broadcast_lobby_update(context, lobby)
    
    return IN_LOBBY