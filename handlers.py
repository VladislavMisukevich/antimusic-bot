from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import Session, User, Lesson, Song, Assignment, CompletedLesson, CompletedSong
from keyboards import profile_keyboard, song_selection_keyboard, admin_review_keyboard
from config import Config
import logging

# Настройка логгера
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
SELECTING_SONG = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    with Session() as session:
        db_user = session.query(User).filter_by(id=user.id).first()

        if not db_user:
            db_user = User(
                id=user.id,
                username=user.username,
                full_name=user.full_name
            )
            session.add(db_user)
            session.commit()
            logger.info(f"New user created: {user.id}")

        await update.message.reply_text(
            f"Привет, {user.full_name}! Добро пожаловать в Антимузыкалку!",
            reply_markup=profile_keyboard(db_user)
        )
        logger.info(f"Start command by user: {user.id}")

    return ConversationHandler.END

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    with Session() as session:
        db_user = session.query(User).filter_by(id=user.id).first()

        if not db_user:
            await start(update, context)
            return

        # Формируем текст профиля
        profile_text = (
            f"{db_user.full_name} | Звание: {db_user.rank} (✨{db_user.reputation})\n"
            f"---\n"
            f"Курс: {db_user.current_course} | Прогресс: {db_user.progress:.1f}%\n"
        )

        if db_user.current_lesson_id:
            lesson = session.get(Lesson, db_user.current_lesson_id)
            profile_text += f"Текущий урок: {lesson.title}\n" if lesson else "Текущий урок: Неизвестный урок\n"

        if db_user.current_song_id:
            song = session.get(Song, db_user.current_song_id)
            profile_text += f"Текущий разбор: {song.title}\n" if song else "Текущий разбор: Неизвестный разбор\n"

        await update.message.reply_text(
            profile_text,
            reply_markup=profile_keyboard(db_user)
        )
        logger.info(f"Profile viewed by user: {user.id}")

    return ConversationHandler.END

async def start_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    query = update.callback_query
    await query.answer()

    with Session() as session:
        db_user = session.query(User).filter_by(id=user.id).first()

        if not db_user:
            await query.edit_message_text("❌ Пользователь не найден!")
            return ConversationHandler.END

        if db_user.current_lesson_id or db_user.current_song_id:
            await query.edit_message_text("⚠️ Сначала завершите текущее задание!")
            return ConversationHandler.END

        # Логика выбора следующего урока
        next_lesson = session.query(Lesson).filter(
            Lesson.course == db_user.current_course,
            Lesson.id.not_in([cl.lesson_id for cl in db_user.completed_lessons])
        ).order_by(Lesson.order_index).first()

        if not next_lesson:
            await query.edit_message_text("🎉 Вы завершили текущий курс!")
            return ConversationHandler.END

        db_user.current_lesson_id = next_lesson.id
        session.commit()
        logger.info(f"Lesson started: user={user.id}, lesson={next_lesson.id}")

        await query.edit_message_text(
            f"✅ Начат урок: {next_lesson.title}\n\n"
            "После выполнения нажмите 'Проверить задание' в профиле.",
            reply_markup=profile_keyboard(db_user)
        )

    return ConversationHandler.END

async def start_song_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(
            "🎸 Выберите номер разбора из списка:",
            reply_markup=song_selection_keyboard()
        )
        logger.info(f"Song selection started by user: {query.from_user.id}")
        return SELECTING_SONG
    except Exception as e:
        logger.error(f"Error in start_song_selection: {str(e)}")
        return ConversationHandler.END

async def select_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("Выбор разбора отменен")
        return ConversationHandler.END

    try:
        song_id = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ Ошибка при выборе разбора!")
        return SELECTING_SONG

    user = update.effective_user

    with Session() as session:
        db_user = session.query(User).filter_by(id=user.id).first()

        if not db_user:
            await query.edit_message_text("❌ Пользователь не найден!")
            return ConversationHandler.END

        # Проверка на существование песни
        song = session.get(Song, song_id)
        if not song:
            await query.edit_message_text("❌ Такого разбора не существует!")
            return SELECTING_SONG

        # Проверка на повторное прохождение
        if any(cs.song_id == song_id for cs in db_user.completed_songs):
            await query.edit_message_text("⚠️ Вы уже прошли этот разбор!")
            return SELECTING_SONG

        # Проверка на активное задание
        if db_user.current_lesson_id or db_user.current_song_id:
            await query.edit_message_text("⚠️ Сначала завершите текущее задание!")
            return SELECTING_SONG

        db_user.current_song_id = song_id
        session.commit()
        logger.info(f"Song started: user={user.id}, song={song_id}")

        await query.edit_message_text(
            f"✅ Начат разбор: {song.title}\n\n"
            "После выполнения нажмите 'Проверить задание' в профиле.",
            reply_markup=profile_keyboard(db_user)
        )

    return ConversationHandler.END

async def submit_assignment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    with Session() as session:
        db_user = session.query(User).filter_by(id=user.id).first()

        if not db_user:
            await query.edit_message_text("❌ Пользователь не найден!")
            return ConversationHandler.END

        if not db_user.current_lesson_id and not db_user.current_song_id:
            await query.edit_message_text("❌ У вас нет активных заданий!")
            return ConversationHandler.END

        # Создание задания на проверку
        assignment = Assignment(
            user_id=user.id,
            type="lesson" if db_user.current_lesson_id else "song",
            item_id=db_user.current_lesson_id or db_user.current_song_id
        )
        session.add(assignment)
        session.commit()
        logger.info(f"Assignment submitted: id={assignment.id}, user={user.id}")

        # Оповещение админа
        try:
            item_type = "урок" if assignment.type == "lesson" else "разбор"
            if assignment.type == "lesson":
                item = session.get(Lesson, assignment.item_id)
            else:
                item = session.get(Song, assignment.item_id)
                
            item_name = item.title if item else "Неизвестное задание"

            await context.bot.send_message(
                chat_id=Config.ADMIN_ID,
                text=f"📬 Новое задание на проверку!\n"
                     f"Пользователь: @{db_user.username or 'без username'}\n"
                     f"Тип: {item_type}\n"
                     f"Задание: {item_name}\n"
                     f"ID задания: {assignment.id}",
                reply_markup=admin_review_keyboard(assignment.id)
            )
        except Exception as e:
            logger.error(f"Error notifying admin: {str(e)}")
            await query.edit_message_text("❌ Ошибка при отправке задания администратору!")
            return

        await query.edit_message_text(
            "✅ Задание отправлено на проверку!\n"
            "Админ проверит его в ближайшее время."
        )

    return ConversationHandler.END

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    reward = 0  # Инициализация по умолчанию

    try:
        assignment_id = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ Неверный ID задания!")
        return

    with Session() as session:
        assignment = session.get(Assignment, assignment_id)
        if not assignment:
            await query.edit_message_text("❌ Задание не найдено!")
            return

        if assignment.status != "pending":
            await query.edit_message_text("❌ Задание уже обработано!")
            return

        db_user = session.query(User).filter_by(id=assignment.user_id).first()
        if not db_user:
            await query.edit_message_text("❌ Пользователь задания не найден!")
            return

        config = Config()

        try:
            if assignment.type == "lesson":
                # Добавляем урок в завершенные
                session.add(CompletedLesson(
                    user_id=db_user.id,
                    lesson_id=assignment.item_id
                ))

                # Сброс текущего урока
                db_user.current_lesson_id = None

                # Начисление репутации
                lesson = session.get(Lesson, assignment.item_id)
                if lesson:
                    if "выпускн" in lesson.title.lower():
                        reward = config.FINAL_LESSON_REWARD
                    else:
                        reward = config.LESSON_REWARD
                else:
                    reward = config.LESSON_REWARD
                    logger.warning(f"Lesson not found for assignment: {assignment_id}")
                
                db_user.reputation += reward

            else:  # type == "song"
                # Добавляем песню в завершенные
                session.add(CompletedSong(
                    user_id=db_user.id,
                    song_id=assignment.item_id
                ))

                # Сброс текущего разбора
                db_user.current_song_id = None

                # Начисление репутации
                reward = config.SONG_REWARD
                db_user.reputation += reward

            # Обновление звания
            rank_changed = db_user.update_rank(config)

            # Обновление прогресса курса
            total_lessons = session.query(Lesson).filter_by(course=db_user.current_course).count()
            completed_lessons = session.query(CompletedLesson).filter_by(user_id=db_user.id).count()
            db_user.progress = (completed_lessons / total_lessons) * 100 if total_lessons > 0 else 0

            assignment.status = "approved"
            session.commit()
            logger.info(f"Assignment approved: id={assignment_id}, reward={reward}")

            # Оповещение пользователя
            try:
                await context.bot.send_message(
                    chat_id=db_user.id,
                    text=f"🎉 Ваше задание принято! +{reward} репутации\n"
                         f"Текущая репутация: {db_user.reputation} ({db_user.rank})"
                )
            except Exception as e:
                logger.error(f"Error notifying user: {str(e)}")
                await query.edit_message_text(
                    f"✅ Задание одобрено, но не удалось уведомить пользователя!\n"
                    f"Начислено: +{reward} репутации"
                )
            else:
                await query.edit_message_text(f"✅ Задание одобрено! Пользователь получил +{reward} репутации.")

        except Exception as e:
            session.rollback()
            logger.error(f"Error approving assignment: {str(e)}")
            await query.edit_message_text("❌ Ошибка при обработке задания!")

async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        assignment_id = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ Неверный ID задания!")
        return

    with Session() as session:
        assignment = session.get(Assignment, assignment_id)
        if not assignment:
            await query.edit_message_text("❌ Задание не найдено!")
            return

        if assignment.status != "pending":
            await query.edit_message_text("❌ Задание уже обработано!")
            return

        db_user = session.query(User).filter_by(id=assignment.user_id).first()
        if not db_user:
            await query.edit_message_text("❌ Пользователь задания не найден!")
            return

        assignment.status = "rejected"
        session.commit()
        logger.info(f"Assignment rejected: id={assignment_id}")

        # Оповещение пользователя
        try:
            await context.bot.send_message(
                chat_id=db_user.id,
                text="🚫 Ваше задание отклонено. Попробуйте снова!"
            )
        except Exception as e:
            logger.error(f"Error notifying user: {str(e)}")
            await query.edit_message_text("❌ Задание отклонено, но не удалось уведомить пользователя!")
        else:
            await query.edit_message_text("✅ Задание отклонено. Пользователь уведомлен.")
