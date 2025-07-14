import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_ID = int(os.getenv('ADMIN_ID'))
    DB_NAME = os.getenv('DB_NAME')

    # Система званий
    RANKS = {
        0: "Новичок",
        50: "Ученик",
        150: "Гитарный адепт",
        300: "Мастер аккордов",
        500: "Мастер перкуссии",
        750: "Битмейкер",
        1000: "Легенда антимузыкалки",
        1500: "Гуру фингерстайла"
    }

    # Награды
    LESSON_REWARD = 10
    SONG_REWARD = 20
    FINAL_LESSON_REWARD = 30
    COURSE_COMPLETE_REWARD = 50