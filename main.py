from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler
from database import init_db
from handlers import *
from config import Config
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_check():
    server = HTTPServer(('0.0.0.0', 8080), HealthCheckHandler)
    server.serve_forever()

def main():
    health_thread = threading.Thread(target=run_health_check, daemon=True)
    health_thread.start()
    # Инициализация базы данных
    init_db()

    # Создание приложения
    application = Application.builder().token(Config.BOT_TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))

    # Обработчики callback-запросов
    application.add_handler(CallbackQueryHandler(start_lesson, pattern="^start_lesson$"))
    application.add_handler(CallbackQueryHandler(submit_assignment, pattern="^submit_assignment$"))
    application.add_handler(CallbackQueryHandler(admin_approve, pattern="^approve_"))
    application.add_handler(CallbackQueryHandler(admin_reject, pattern="^reject_"))

    # ConversationHandler для выбора песен
    song_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_song_selection, pattern="^start_song$")],
        states={
            SELECTING_SONG: [CallbackQueryHandler(select_song, pattern="^song_")]
        },
        fallbacks=[CallbackQueryHandler(select_song, pattern="^cancel$")]
    )
    application.add_handler(song_conv_handler)

    # Запуск бота
    application.run_polling()


if __name__ == "__main__":
    # Запускаем health-check сервер в отдельном потоке
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer


    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is healthy")


    def run_health_server():
        server = HTTPServer(('0.0.0.0', 10000), HealthHandler)
        server.serve_forever()


    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    # Запускаем бота
    main()
