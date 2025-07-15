from telegram import Update
from telegram.ext import ContextTypes, CallbackContext, ConversationHandler
from database import Session, User, Lesson, Song, Assignment, CompletedLesson, CompletedSong
from keyboards import profile_keyboard, song_selection_keyboard, admin_review_keyboard
from config import Config
import random

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

        await update.message.reply_text(
            f"Привет, {user.full_name}! Добро пожаловать в Антимузыкалку!",
            reply_markup=profile_keyboard(db_user)
        )

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
            profile_text += f"Текущий урок: {lesson.title}\n"

        if db_user.current_song_id:
            song = session.get(Song, db_user.current_song_id)
            profile_text += f"Текущий разбор: {song.title}\n"

        await update.message.reply_text(
            profile_text,
            reply_markup=profile_keyboard(db_user)
        )

    return ConversationHandler.END


async def start_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    query = update.callback_query
    await query.answer()

    with Session() as session:
        db_user = session.query(User).filter_by(id=user.id).first()

        if db_user.current_lesson_id or db_user.current_song_id:
            await query.edit_message_text("⚠️ Сначала завершите текущее задание!")
            return

        # Логика выбора следующего урока
        next_lesson = session.query(Lesson).filter(
            Lesson.course == db_user.current_course,
            Lesson.id.not_in([cl.lesson_id for cl in db_user.completed_lessons])
        ).order_by(Lesson.order_index).first()

        if not next_lesson:
            await query.edit_message_text("🎉 Вы завершили текущий курс!")
            return

        db_user.current_lesson_id = next_lesson.id
        session.commit()

        await query.edit_message_text(
            f"✅ Начат урок: {next_lesson.title}\n\n"
            "После выполнения нажмите 'Проверить задание' в профиле.",
            reply_markup=profile_keyboard(db_user)
        )

    return ConversationHandler.END


async def start_song_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎸 Выберите номер разбора из списка:",
        reply_markup=song_selection_keyboard()
    )
    return SELECTING_SONG


async def select_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("Выбор разбора отменен")
        return ConversationHandler.END

    song_id = int(query.data.split("_")[1])
    user = update.effective_user

    with Session() as session:
        db_user = session.query(User).filter_by(id=user.id).first()

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

        if not db_user.current_lesson_id and not db_user.current_song_id:
            await query.edit_message_text("❌ У вас нет активных заданий!")
            return

        # Создание задания на проверку
        assignment = Assignment(
            user_id=user.id,
            type="lesson" if db_user.current_lesson_id else "song",
            item_id=db_user.current_lesson_id or db_user.current_song_id
        )
        session.add(assignment)
        session.commit()

        # Оповещение админа
        item_type = "урок" if assignment.type == "lesson" else "разбор"
        item_name = session.get(Lesson if assignment.type == "lesson" else Song, assignment.item_id).title

        await context.bot.send_message(
            chat_id=Config.ADMIN_ID,
            text=f"📬 Новое задание на проверку!\n"
                 f"Пользователь: @{db_user.username}\n"
                 f"Тип: {item_type}\n"
                 f"Задание: {item_name}\n"
                 f"ID задания: {assignment.id}",
            reply_markup=admin_review_keyboard(assignment.id)
        )

        await query.edit_message_text(
            "✅ Задание отправлено на проверку!\n"
            "Админ проверит его в ближайшее время."
        )

    return ConversationHandler.END


async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    assignment_id = int(query.data.split("_")[1])
    reward = 0  # Инициализируем переменную

    with Session() as session:
        assignment = session.get(Assignment, assignment_id)
        if not assignment or assignment.status != "pending":
            await query.edit_message_text("❌ Задание уже обработано!")
            return

        db_user = session.query(User).filter_by(id=assignment.user_id).first()
        config = Config()

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
            reward = config.FINAL_LESSON_REWARD if lesson and "выпускн" in lesson.title.lower() else config.LESSON_REWARD
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
        db_user.update_rank(config)

        # Обновление прогресса курса
        total_lessons = session.query(Lesson).filter_by(course=db_user.current_course).count()
        completed_lessons = session.query(CompletedLesson).filter_by(user_id=db_user.id).count()
        db_user.progress = (completed_lessons / total_lessons) * 100 if total_lessons > 0 else 0

        assignment.status = "approved"
        session.commit()

        # Оповещение пользователя
        await context.bot.send_message(
            chat_id=db_user.id,
            text=f"🎉 Ваше задание принято! +{reward} репутации\n"
                 f"Текущая репутация: {db_user.reputation} ({db_user.rank})"
        )

        await query.edit_message_text(f"✅ Задание одобрено! Пользователь получил +{reward} репутации.")


async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    assignment_id = int(query.data.split("_")[1])

    with Session() as session:
        assignment = session.get(Assignment, assignment_id)
        if not assignment or assignment.status != "pending":
            await query.edit_message_text("✔️ Задание уже обработано!")
            return

        db_user = session.query(User).filter_by(id=assignment.user_id).first()

        assignment.status = "rejected"
        session.commit()

        # Оповещение пользователя
        await context.bot.send_message(
            chat_id=db_user.id,
            text="🚫 Ваше задание отклонено. Попробуйте снова!"
        )

        await query.edit_message_text("❌ Задание отклонено.")
