from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Float
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.exc import IntegrityError
from config import Config
import logging
import sys
if sys.version_info >= (3, 13):
    print("FATAL ERROR: Python 3.13 is not supported")
    print("Please use Python 3.11")
    sys.exit(1)

# Настройка логгера
logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

Base = declarative_base()
engine = create_engine(f'sqlite:///{Config.DB_NAME}')
Session = sessionmaker(bind=engine)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String)
    full_name = Column(String)
    reputation = Column(Integer, default=0)
    rank = Column(String, default='Новичок')
    current_course = Column(Integer, default=1)
    progress = Column(Float, default=0.0)
    current_lesson_id = Column(Integer, ForeignKey('lessons.id'))
    current_song_id = Column(Integer, ForeignKey('songs.id'))
    is_graduated = Column(Boolean, default=False)

    completed_lessons = relationship("CompletedLesson", back_populates="user")
    completed_songs = relationship("CompletedSong", back_populates="user")

    def update_rank(self, config):
        for threshold, rank in sorted(config.RANKS.items(), reverse=True):
            if self.reputation >= threshold:
                if self.rank != rank:
                    self.rank = rank
                    return True  # Звание изменилось
                return False  # Звание не изменилось
        return False


class Lesson(Base):
    __tablename__ = 'lessons'

    id = Column(Integer, primary_key=True)
    course = Column(Integer)
    module = Column(String)
    title = Column(String)
    order_index = Column(Integer)
    is_bonus = Column(Boolean, default=False)
    is_final = Column(Boolean, default=False)

    users = relationship("CompletedLesson", back_populates="lesson")


class Song(Base):
    __tablename__ = 'songs'

    id = Column(Integer, primary_key=True)
    title = Column(String)

    users = relationship("CompletedSong", back_populates="song")


class CompletedLesson(Base):
    __tablename__ = 'completed_lessons'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    lesson_id = Column(Integer, ForeignKey('lessons.id'), primary_key=True)

    user = relationship("User", back_populates="completed_lessons")
    lesson = relationship("Lesson", back_populates="users")


class CompletedSong(Base):
    __tablename__ = 'completed_songs'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    song_id = Column(Integer, ForeignKey('songs.id'), primary_key=True)

    user = relationship("User", back_populates="completed_songs")
    song = relationship("Song", back_populates="users")


class Assignment(Base):
    __tablename__ = 'assignments'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    type = Column(String)  # 'lesson' или 'song'
    item_id = Column(Integer)
    status = Column(String, default='pending')  # pending/approved/rejected/revision_requested


def init_db():
    try:
        Base.metadata.create_all(engine)
        logger.info("Таблицы базы данных созданы")

        session = Session()

        # Проверяем, есть ли уже уроки в базе
        if session.query(Lesson).count() == 0:
            logger.info("Добавляем уроки в базу данных...")

            # Курс 1: Основы фингерстайла (20 уроков)
            course1_lessons = [
                (1, "Вводный модуль", "Урок 1. Введение. Что такое финегрстайл?", 0),
                (1, "Вводный модуль", "Урок 2. Постановка правой руки", 1),
                (1, "Вводный модуль", "Урок 3. Постановка левой руки", 2),
                (1, "Модуль 1", "Урок 4. Как читать ТАБы правильно", 3),
                (1, "Модуль 1", "Урок 5. Длительности нот и метроном", 4),
                (1, "Модуль 1", "Урок 6. Большой палец и бас", 5),
                (1, "Модуль 2", "Урок 7. Двухголосие", 6),
                (1, "Модуль 2", "Урок 8. Четверть с точкой", 7),
                (1, "Модуль 2", "Урок 9. Мелодия+аккорд", 8),
                (1, "Модуль 2", "Урок 10. Соединяем мелодию, бас и аккомпанемент. Синкопа", 9),
                (1, "Модуль 2", "Урок 11. Синкопа внутри такта", 10),
                (1, "Модуль 2", "Урок 12. Трехголосие, знаки повтора в табах", 11),
                (1, "Модуль 3", "Урок 13. Шестнадцатые", 12),
                (1, "Модуль 3", "Урок 14. Пунктир", 13),
                (1, "Модуль 3", "Урок 15. Триоли", 14),
                (1, "Модуль 4", "Урок 16. Техника левой руки. Hammer on/Pull off", 15),
                (1, "Модуль 4", "Урок 17. Натуральные флажолеты", 16),
                (1, "Модуль 4", "Урок 18. Искусственные флажолеты", 17),
                (1, "Модуль 4", "Урок 19. Украшаем игру: Форшлаг/Слайд/Арпеджиато", 18),
                (1, "Модуль 4", "Урок 20. Выпускная композиция", 19, True)
            ]

            # Курс 2: Перкуссия и сложные биты (17 уроков)
            course2_lessons = [
                (2, "Модуль 1", "Урок 1. Что такое перкуссия?", 0),
                (2, "Модуль 1", "Урок 2. Щелчок по всем струнам", 1),
                (2, "Модуль 1", "Урок 3. Бас + Snare", 2),
                (2, "Модуль 1", "Урок 4. Мелодия + Snare", 3),
                (2, "Модуль 1", "Урок 5. 'Выброс' по нескольким струнам", 4),
                (2, "Модуль 1", "Урок 6. 'Выброс' по одной струне. Глушение струн левой рукой при игре 'выброса'.", 5),
                (2, "Модуль 1", "Урок 7. Изучение композиций на 'выброс'", 6),
                (2, "Модуль 2", "Урок 8. Бас-бочка (Kick)", 7),
                (2, "Модуль 2", "Урок 9. Бас + Kick", 8),
                (2, "Модуль 2", "Урок 10. Double Kick", 9),
                (2, "Модуль 2", "Урок 11. Мелодия + Kick", 10),
                (2, "Модуль 2", "Урок 12. Аккорд + Kick", 11),
                (2, "Модуль 2", "Урок 13. Соединение (Kick + Snare)", 12),
                (2, "Модуль 3", "Урок 14. Ломаная бочка/Смещенная бочка.", 13),
                (2, "Модуль 3", "Урок 15. Сложные биты. Написание битов.", 14),
                (2, "Модуль 3", "Урок 16. Pre-Chorus 'Numb'", 15),
                (2, "Модуль 3", "Урок 17. Выпускная композиция 'Numb': Intro, Verse, Pre-Chorus, Chorus", 16, True)
            ]

            # Курс 3: Продвинутые техники (18 уроков)
            course3_lessons = [
                (3, "Модуль 1", "Урок 1. Snare ладонью", 0),
                (3, "Модуль 1", "Урок 2. Snare ладонью. Практика", 1),
                (3, "Модуль 1", "Урок 3. Slap-Snare и Snare по деке", 2),
                (3, "Модуль 1", "Урок 4. 3 вида Hi-Hats 8-ми длительностями", 3),
                (3, "Модуль 1", "Урок 5. 2 вида Hi-Hats 16-ми длительностями.", 4),
                (3, "Модуль 2", "Урок 6. Slap большим пальцем по нескольким струнам", 5),
                (3, "Модуль 2", "Урок 7. Slap + бочка.", 6),
                (3, "Модуль 2", "Урок 8. Slap по одной струне.", 7),
                (3, "Модуль 2", "Урок 9. Перкуссионные флажолеты (slap флажолеты)", 8),
                (3, "Модуль 3", "Урок 10. Palm mute + Фанковый бас", 9),
                (3, "Модуль 3", "Урок 11. Перкуссия по корпусу", 10),
                (3, "Модуль 3", "Урок 12. Расгеадо", 11),
                (3, "Модуль 3", "Урок 13. Независимость рук", 12),
                (3, "Модуль 3", "Урок 14. Тэпинг двумя руками", 13, True),
                (3, "Бонусный модуль", "Урок 15. Rasgeado по струнам", 14, False, True),
                (3, "Бонусный модуль", "Урок 16. Сбивка Marcin", 15, False, True),
                (3, "Бонусный модуль", "Урок 17. Разбор полной аранжировки Marcin 'Kashmir'", 16, False, True),
                (3, "Бонусный модуль", "Урок 18. Разбор полной аранжировки Jinsan Kim 'Crow'", 17, False, True)
            ]

            # Добавляем уроки курса 1
            for lesson in course1_lessons:
                is_final = len(lesson) > 4 and lesson[4]
                session.add(Lesson(
                    course=lesson[0],
                    module=lesson[1],
                    title=lesson[2],
                    order_index=lesson[3],
                    is_final=is_final
                ))

            # Добавляем уроки курса 2
            for lesson in course2_lessons:
                is_final = len(lesson) > 4 and lesson[4]
                session.add(Lesson(
                    course=lesson[0],
                    module=lesson[1],
                    title=lesson[2],
                    order_index=lesson[3],
                    is_final=is_final
                ))

            # Добавляем уроки курса 3
            for lesson in course3_lessons:
                is_final = len(lesson) > 4 and lesson[4]
                is_bonus = len(lesson) > 5 and lesson[5]
                session.add(Lesson(
                    course=lesson[0],
                    module=lesson[1],
                    title=lesson[2],
                    order_index=lesson[3],
                    is_final=is_final,
                    is_bonus=is_bonus
                ))

            logger.info(f"Добавлено {len(course1_lessons) + len(course2_lessons) + len(course3_lessons)} уроков")

        # Проверяем песни
        if session.query(Song).count() == 0:
            logger.info("Добавляем песни в базу данных...")
            songs = [
                (1, "Billie Jean"),
                (2, "Седьмой лепесток"),
                (3, "Another love"),
                (4, "Crow"),
                (5, "One of us"),
                (6, "Game of thrones"),
                (7, "Stay"),
                (8, "Get Lucky"),
                (9, "Zombie"),
                (10, "Kashmir"),
                (11, "Beggin"),
                (12, "We don't talk anymore"),
                (13, "Перемен"),
                (14, "Take me to church"),
                (15, "Numb"),
                (16, "The Weeknd"),
                (17, "Feel good")
            ]

            for song_id, title in songs:
                session.add(Song(id=song_id, title=title))

            logger.info(f"Добавлено {len(songs)} песен")

        # Проверяем наличие админ-пользователя
        admin_id = Config.ADMIN_ID
        if not session.query(User).get(admin_id):
            logger.info("Создаем администратора...")
            admin = User(
                id=admin_id,
                username="admin",
                full_name="Администратор",
                reputation=1000,
                rank="Гуру фингерстайла",
                is_graduated=True
            )
            session.add(admin)
            logger.info(f"Администратор с ID {admin_id} создан")

        session.commit()
        logger.info("База данных успешно инициализирована")

    except IntegrityError as e:
        session.rollback()
        logger.error(f"Ошибка целостности данных: {str(e)}")
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при инициализации БД: {str(e)}")
    finally:
        session.close()


def get_session():
    return Session()


# Для тестирования: если файл запущен напрямую, инициализируем БД
if __name__ == "__main__":
    init_db()
