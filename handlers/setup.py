from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)

from handlers.command_handlers import (
    start_command,
    enter_full_name,
    wait_for_lobby_id,
    create_new_lobby_callback,
    join_command,
    lobby_command,
    leave_command,
    start_game_command,
    leave_callback,
    start_game_callback,
    enter_scenario_callback,
    random_scenario_callback,
    game_mode_callback,
    message_handler,
    ENTER_FULL_NAME,
    WAITING_FOR_LOBBY_OR_CREATE,
    IN_LOBBY
)


def setup_handlers(application: Application):
    """Настраивает обработчики команд и сообщений"""
    
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            CommandHandler("join", join_command),
        ],
        states={
            ENTER_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_full_name)],
            WAITING_FOR_LOBBY_OR_CREATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, wait_for_lobby_id),
                CallbackQueryHandler(create_new_lobby_callback, pattern="^create_new_lobby$"),
            ],
            IN_LOBBY: [
                CommandHandler("lobby", lobby_command),
                CommandHandler("leave", leave_command),
                CommandHandler("startgame", start_game_command),
                MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler),
                CallbackQueryHandler(leave_callback, pattern="^leave_lobby$"),
                CallbackQueryHandler(start_game_callback, pattern="^start_game$"),
                CallbackQueryHandler(enter_scenario_callback, pattern="^enter_scenario$"),
                CallbackQueryHandler(random_scenario_callback, pattern="^random_scenario$"),
                CallbackQueryHandler(game_mode_callback, pattern="^mode_(every_man|brotherhood)$"),
            ],
        },
        fallbacks=[CommandHandler("start", start_command)],
        per_chat=True,  
        per_message=False  
    )
    
    
    application.add_handler(conv_handler)
    
    
    application.add_handler(CommandHandler("lobby", lobby_command))
    application.add_handler(CommandHandler("leave", leave_command))
    
    return application