from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import Config


def profile_keyboard(user):
    buttons = []

    if not user.current_lesson_id and not user.current_song_id:
        buttons.append([
            InlineKeyboardButton("Начать урок", callback_data="start_lesson"),
            InlineKeyboardButton("Начать разбор", callback_data="start_song")
        ])
    elif user.current_lesson_id or user.current_song_id:
        buttons.append([InlineKeyboardButton("Проверить задание", callback_data="submit_assignment")])

    return InlineKeyboardMarkup(buttons)


def song_selection_keyboard():
    buttons = []
    row = []

    for i in range(1, 18):
        row.append(InlineKeyboardButton(str(i), callback_data=f"song_{i}"))
        if len(row) == 3:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("Отмена", callback_data="cancel")])

    return InlineKeyboardMarkup(buttons)


def admin_review_keyboard(assignment_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"approve_{assignment_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{assignment_id}")
        ]
    ])