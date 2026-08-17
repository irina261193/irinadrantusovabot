import os
import json

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Telegram ID Ирины
ADMIN_ID = 8580647796

# Файл со свободными окнами
SLOTS_FILE = "data/slots.json"


# ==========================================
# ГЛАВНОЕ МЕНЮ
# ==========================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    keyboard = [
        [
            InlineKeyboardButton(
                "💬 Отзывы",
                callback_data="reviews",
            ),
            InlineKeyboardButton(
                "📅 Свободные окна",
                callback_data="slots",
            ),
        ],
        [
            InlineKeyboardButton(
                "✏️ Записаться на урок",
                callback_data="book",
            )
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    with open("images/hello.png", "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption=(
                "Приветики! 💗\n\n"
                "Это персональный ассистент Ирины Дрантусовой.\n\n"
                "Ирина Дрантусова — репетитор по английскому языку, "
                "который помогает сделать английский понятным, "
                "живым и комфортным. 🇬🇧✨\n\n"
                "Здесь можно посмотреть отзывы, узнать свободные "
                "окошки и записаться на урок."
            ),
            reply_markup=reply_markup,
        )


# ==========================================
# ОБРАБОТКА КНОПОК
# ==========================================

async def button_handler (
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    ):
    query = update.callback_query
    await query.answer()

    # ОТЗЫВЫ
    if query.data == "reviews":
        await query.message.reply_text(
            "💗 Вот что говорят мои ученики:"
        )

        for i in range(1, 4):
            with open(
                f"images/reviews/review{i}.png",
                "rb",
            ) as photo:
                await query.message.reply_photo(
                    photo=photo
                )

    # СВОБОДНЫЕ ОКНА
    elif query.data == "slots":
        with open(
            SLOTS_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            slots = json.load(file)

        if not slots:
            await query.message.reply_text(
                "😔 Сейчас свободных окошек нет.\n\n"
                "Но расписание обновляется — загляните чуть позже 💗"
            )
            return

        slots_text = "\n".join(
            f"• {slot}" for slot in slots
        )

        await query.message.reply_text(
            "📅 Свободные окошки:\n\n"
            f"{slots_text}\n\n"
            "Если нашли подходящее время — "
            "нажмите «Записаться на урок» 💗"
        )

    # ЗАПИСАТЬСЯ НА УРОК
    elif query.data == "book":
        with open(
            SLOTS_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            slots = json.load(file)

        if not slots:
            await query.message.reply_text(
                "😔 Сейчас свободных окошек нет.\n\n"
                "Можно написать Ирине напрямую: @Sadako_93"
            )
            return

        keyboard = []

        for index, slot in enumerate(slots):
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📅 {slot}",
                        callback_data=f"book_slot_{index}",
                    )
                ]
            )

        await query.message.reply_text(
            "✏️ Выберите удобное время:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    # ПОЛЬЗОВАТЕЛЬ ВЫБРАЛ ОКНО
    elif query.data.startswith("book_slot_"):
        index = int(
            query.data.replace("book_slot_", "")
        )

        with open(
            SLOTS_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            slots = json.load(file)

        if index >= len(slots):
            await query.message.reply_text(
                "⚠️ Это окно уже недоступно."
            )
            return

        slot = slots[index]
        user = query.from_user

        username = (
            f"@{user.username}"
            if user.username
            else "username не указан"
        )

        request_keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Подтвердить",
                    callback_data=f"confirm_booking_{index}_{user.id}",
                ),
                InlineKeyboardButton(
                    "❌ Отклонить",
                    callback_data=f"reject_booking_{user.id}",
                ),
            ]
        ]

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "🔔 Новая заявка на урок!\n\n"
                f"👤 Имя: {user.full_name}\n"
                f"📱 Telegram: {username}\n"
                f"🆔 ID: {user.id}\n"
                f"📅 Время: {slot}\n\n"
                "Подтвердить запись?"
            ),
            reply_markup=InlineKeyboardMarkup(
                request_keyboard
            ),
        )

        await query.message.reply_text(
            "💗 Заявка отправлена Ирине!\n\n"
            f"Вы выбрали:\n📅 {slot}\n\n"
            "Ирина подтвердит запись отдельно.\n\n"
            "Связаться напрямую:\n"
            "👉 @Sadako_93"
        )

    # АДМИН: ПОДТВЕРДИТЬ ЗАПИСЬ
    elif query.data.startswith("confirm_booking_"):
        if query.from_user.id != ADMIN_ID:
            await query.message.reply_text(
                "⛔ Доступ запрещён."
            )
            return

        parts = query.data.split("_")
        index = int(parts[2])
        user_id = int(parts[3])

        with open(
            SLOTS_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            slots = json.load(file)

        if index >= len(slots):
            await query.message.reply_text(
                "⚠️ Это окно уже было удалено."
            )
            return

        confirmed_slot = slots.pop(index)

        with open(
            SLOTS_FILE,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                slots,
                file,
                ensure_ascii=False,
                indent=2,
            )

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "✅ Ирина подтвердила вашу запись!\n\n"
                f"📅 {confirmed_slot}\n\n"
                "До встречи на уроке 💗\n"
                "Связаться с Ириной: @Sadako_93"
            ),
        )

        await query.message.reply_text(
            "✅ Запись подтверждена.\n\n"
            f"📅 {confirmed_slot}\n\n"
            "Окно удалено из свободных."
        )

    # АДМИН: ОТКЛОНИТЬ ЗАПИСЬ
    elif query.data.startswith("reject_booking_"):
        if query.from_user.id != ADMIN_ID:
            await query.message.reply_text(
                "⛔ Доступ запрещён."
            )
            return

        user_id = int(
            query.data.replace(
                "reject_booking_",
                ""
            )
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "К сожалению, Ирина пока не смогла "
                "подтвердить это время 💗\n\n"
                "Посмотрите другие свободные окна "
                "или напишите напрямую: @Sadako_93"
            ),
        )

        await query.message.reply_text(
            "❌ Заявка отклонена."
        )

    # АДМИН: ДОБАВИТЬ ОКНО
    elif query.data == "admin_add_slot":
        if query.from_user.id != ADMIN_ID:
            await query.message.reply_text(
                "⛔ Доступ запрещён."
            )
            return

        context.user_data["waiting_for_slot"] = True

        await query.message.reply_text(
            "➕ Добавление свободного окна\n\n"
            "Напишите дату и время одной строкой.\n\n"
            "Например:\n"
            "20 августа - 14:00"
        )

    # АДМИН: ПОСМОТРЕТЬ ОКНА
    elif query.data == "admin_view_slots":
        if query.from_user.id != ADMIN_ID:
            await query.message.reply_text(
                "⛔ Доступ запрещён."
            )
            return

        with open(
            SLOTS_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            slots = json.load(file)

        if not slots:
            await query.message.reply_text(
                "📅 Свободных окон сейчас нет."
            )
            return

        slots_text = "\n".join(
            f"• {slot}" for slot in slots
        )

        await query.message.reply_text(
            "📅 Ваши свободные окна:\n\n"
            f"{slots_text}"
        )

    # АДМИН: ВЫБРАТЬ ОКНО ДЛЯ УДАЛЕНИЯ
    elif query.data == "admin_delete_slot":
        if query.from_user.id != ADMIN_ID:
            await query.message.reply_text(
                "⛔ Доступ запрещён."
            )
            return

        with open(
            SLOTS_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            slots = json.load(file)

        if not slots:
            await query.message.reply_text(
                "📅 Удалять нечего — свободных окон нет."
            )
            return

        keyboard = []

        for index, slot in enumerate(slots):
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"❌ {slot}",
                        callback_data=f"delete_slot_{index}",
                    )
                ]
            )

        await query.message.reply_text(
            "Выберите окно, которое хотите удалить:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

    # АДМИН: УДАЛИТЬ ОКНО
    elif query.data.startswith("delete_slot_"):
        if query.from_user.id != ADMIN_ID:
            await query.message.reply_text(
                "⛔ Доступ запрещён."
            )
            return

        index = int(
            query.data.replace(
                "delete_slot_",
                ""
            )
        )

        with open(
            SLOTS_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            slots = json.load(file)

        if index >= len(slots):
            await query.message.reply_text(
                "⚠️ Это окно уже не существует."
            )
            return

        deleted_slot = slots.pop(index)

        with open(
            SLOTS_FILE,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                slots,
                file,
                ensure_ascii=False,
                indent=2,
            )

        await query.message.reply_text(
            "✅ Окно удалено:\n\n"
            f"📅 {deleted_slot}"
        )

async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    # Обычный пользователь не может
    # добавлять свободные окна
    if user.id != ADMIN_ID:
        return

    # Проверяем, ждёт ли бот новое окно
    if context.user_data.get("waiting_for_slot"):

        slot = update.message.text.strip()

        # Читаем существующие окна
        with open(
            SLOTS_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            slots = json.load(file)

        # Добавляем новое
        slots.append(slot)

        # Сохраняем
        with open(
            SLOTS_FILE,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                slots,
                file,
                ensure_ascii=False,
                indent=2,
            )

        context.user_data["waiting_for_slot"] = False

        await update.message.reply_text(
            "✅ Свободное окно добавлено!\n\n"
            f"📅 {slot}"
        )


# ==========================================
# МОЙ TELEGRAM ID
# ==========================================

async def my_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    await update.message.reply_text(
        f"Ваш Telegram ID: {user.id}\n"
        f"Username: @{user.username}"
    )


# ==========================================
# АДМИН-ПАНЕЛЬ
# ==========================================

async def admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    if user.id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ Доступ запрещён."
        )
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ Добавить окно",
                callback_data="admin_add_slot",
            )
        ],
        [
            InlineKeyboardButton(
                "➖ Удалить окно",
                callback_data="admin_delete_slot",
            )
        ],
        [
            InlineKeyboardButton(
                "📅 Посмотреть окна",
                callback_data="admin_view_slots",
            )
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚙️ Управление расписанием",
        reply_markup=reply_markup,
    )


# ==========================================
# ЗАПУСК
# ==========================================

def main():

    if not BOT_TOKEN:
        raise ValueError(
            "BOT_TOKEN не найден в файле .env"
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        CommandHandler(
            "myid",
            my_id,
        )
    )

    app.add_handler(
        CommandHandler(
            "admin",
            admin,
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text,
        )
    )

    print("Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()