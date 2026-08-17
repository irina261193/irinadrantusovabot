import hashlib
import os

from dotenv import load_dotenv
from supabase import Client, create_client
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

ADMIN_ID = 8580647796
TEACHER_USERNAME = "Sadako_93"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")
if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL не найден в переменных окружения")
if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY не найден в переменных окружения")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_slots():
    response = (
        supabase.table("slots")
        .select("id, slot_text, is_available")
        .eq("is_available", True)
        .order("id")
        .execute()
    )
    return response.data or []


def get_slot(slot_id: int):
    response = (
        supabase.table("slots")
        .select("id, slot_text, is_available")
        .eq("id", slot_id)
        .eq("is_available", True)
        .limit(1)
        .execute()
    )
    data = response.data or []
    return data[0] if data else None


def add_slot(slot_text: str):
    return (
        supabase.table("slots")
        .insert({"slot_text": slot_text, "is_available": True})
        .execute()
    )


def delete_slot(slot_id: int):
    return (
        supabase.table("slots")
        .delete()
        .eq("id", slot_id)
        .execute()
    )


def main_menu():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💬 Отзывы", callback_data="reviews"),
                InlineKeyboardButton("📅 Свободные окна", callback_data="slots"),
            ],
            [InlineKeyboardButton("✏️ Записаться на урок", callback_data="book")],
        ]
    )


def admin_menu():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Добавить окно", callback_data="admin_add_slot")],
            [InlineKeyboardButton("➖ Удалить окно", callback_data="admin_delete_slot")],
            [InlineKeyboardButton("📅 Посмотреть окна", callback_data="admin_view_slots")],
        ]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            reply_markup=main_menu(),
        )


async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = f"@{user.username}" if user.username else "не указан"
    await update.message.reply_text(
        f"Ваш Telegram ID: {user.id}\nUsername: {username}"
    )


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Доступ запрещён.")
        return
    await update.message.reply_text(
        "⚙️ Управление расписанием",
        reply_markup=admin_menu(),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "reviews":
        await query.message.reply_text("💗 Вот что говорят мои ученики:")
        for i in range(1, 4):
            with open(f"images/reviews/review{i}.png", "rb") as photo:
                await query.message.reply_photo(photo=photo)

    elif query.data == "slots":
        slots = get_slots()
        if not slots:
            await query.message.reply_text(
                "😔 Сейчас свободных окошек нет.\n\n"
                "Но расписание обновляется — загляните чуть позже 💗"
            )
            return
        slots_text = "\n".join(f"• {slot['slot_text']}" for slot in slots)
        await query.message.reply_text(
            "📅 Свободные окошки:\n\n"
            f"{slots_text}\n\n"
            "Если нашли подходящее время — нажмите «Записаться на урок» 💗"
        )

    elif query.data == "book":
        slots = get_slots()
        if not slots:
            await query.message.reply_text(
                "😔 Сейчас свободных окошек нет.\n\n"
                f"Можно написать Ирине напрямую: @{TEACHER_USERNAME}"
            )
            return
        keyboard = [
            [
                InlineKeyboardButton(
                    f"📅 {slot['slot_text']}",
                    callback_data=f"book_slot_{slot['id']}",
                )
            ]
            for slot in slots
        ]
        await query.message.reply_text(
            "✏️ Выберите удобное время:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data.startswith("book_slot_"):
        slot_id = int(query.data.replace("book_slot_", ""))
        slot = get_slot(slot_id)
        if not slot:
            await query.message.reply_text(
                "⚠️ Это окно уже недоступно. Посмотрите актуальные свободные окна."
            )
            return

        user = query.from_user
        username = f"@{user.username}" if user.username else "username не указан"
        request_keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Подтвердить",
                        callback_data=f"confirm_booking_{slot_id}_{user.id}",
                    ),
                    InlineKeyboardButton(
                        "❌ Отклонить",
                        callback_data=f"reject_booking_{user.id}",
                    ),
                ]
            ]
        )
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "🔔 Новая заявка на урок!\n\n"
                f"👤 Имя: {user.full_name}\n"
                f"📱 Telegram: {username}\n"
                f"🆔 ID: {user.id}\n"
                f"📅 Время: {slot['slot_text']}\n\n"
                "Подтвердить запись?"
            ),
            reply_markup=request_keyboard,
        )
        await query.message.reply_text(
            "💗 Заявка отправлена Ирине!\n\n"
            f"Вы выбрали:\n📅 {slot['slot_text']}\n\n"
            "Ирина подтвердит запись отдельно.\n\n"
            f"Связаться напрямую:\n👉 https://t.me/{TEACHER_USERNAME}"
        )

    elif query.data.startswith("confirm_booking_"):
        if query.from_user.id != ADMIN_ID:
            await query.message.reply_text("⛔ Доступ запрещён.")
            return
        parts = query.data.split("_")
        slot_id = int(parts[2])
        user_id = int(parts[3])
        slot = get_slot(slot_id)
        if not slot:
            await query.message.reply_text(
                "⚠️ Это окно уже было удалено или стало недоступно."
            )
            return
        delete_slot(slot_id)
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "✅ Ирина подтвердила вашу запись!\n\n"
                f"📅 {slot['slot_text']}\n\n"
                "До встречи на уроке 💗\n\n"
                f"Связаться с Ириной:\nhttps://t.me/{TEACHER_USERNAME}"
            ),
        )
        await query.message.reply_text(
            "✅ Запись подтверждена.\n\n"
            f"📅 {slot['slot_text']}\n\n"
            "Окно удалено из свободных."
        )

    elif query.data.startswith("reject_booking_"):
        if query.from_user.id != ADMIN_ID:
            await query.message.reply_text("⛔ Доступ запрещён.")
            return
        user_id = int(query.data.replace("reject_booking_", ""))
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "К сожалению, Ирина пока не смогла подтвердить это время 💗\n\n"
                "Посмотрите другие свободные окна или напишите Ирине напрямую:\n"
                f"https://t.me/{TEACHER_USERNAME}"
            ),
        )
        await query.message.reply_text(
            "❌ Заявка отклонена.\nОкно осталось в списке свободных."
        )

    elif query.data == "admin_add_slot":
        if query.from_user.id != ADMIN_ID:
            await query.message.reply_text("⛔ Доступ запрещён.")
            return
        context.user_data["waiting_for_slot"] = True
        await query.message.reply_text(
            "➕ Добавление свободного окна\n\n"
            "Напишите дату и время одной строкой.\n\n"
            "Например:\n20 августа - 14:00"
        )

    elif query.data == "admin_view_slots":
        if query.from_user.id != ADMIN_ID:
            await query.message.reply_text("⛔ Доступ запрещён.")
            return
        slots = get_slots()
        if not slots:
            await query.message.reply_text("📅 Свободных окон сейчас нет.")
            return
        slots_text = "\n".join(f"• {slot['slot_text']}" for slot in slots)
        await query.message.reply_text(
            "📅 Ваши свободные окна:\n\n" + slots_text
        )

    elif query.data == "admin_delete_slot":
        if query.from_user.id != ADMIN_ID:
            await query.message.reply_text("⛔ Доступ запрещён.")
            return
        slots = get_slots()
        if not slots:
            await query.message.reply_text("📅 Удалять нечего — свободных окон нет.")
            return
        keyboard = [
            [
                InlineKeyboardButton(
                    f"❌ {slot['slot_text']}",
                    callback_data=f"delete_slot_{slot['id']}",
                )
            ]
            for slot in slots
        ]
        await query.message.reply_text(
            "Выберите окно, которое хотите удалить:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data.startswith("delete_slot_"):
        if query.from_user.id != ADMIN_ID:
            await query.message.reply_text("⛔ Доступ запрещён.")
            return
        slot_id = int(query.data.replace("delete_slot_", ""))
        slot = get_slot(slot_id)
        if not slot:
            await query.message.reply_text("⚠️ Это окно уже не существует.")
            return
        delete_slot(slot_id)
        await query.message.reply_text(
            "✅ Окно удалено:\n\n" f"📅 {slot['slot_text']}"
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    if context.user_data.get("waiting_for_slot"):
        slot_text = update.message.text.strip()
        if not slot_text:
            await update.message.reply_text("⚠️ Напишите дату и время.")
            return
        add_slot(slot_text)
        context.user_data["waiting_for_slot"] = False
        await update.message.reply_text(
            "✅ Свободное окно добавлено!\n\n" f"📅 {slot_text}",
            reply_markup=admin_menu(),
        )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", my_id))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text,
        )
    )

    render_url = os.getenv("RENDER_EXTERNAL_URL")
    port = int(os.getenv("PORT", "10000"))

    if render_url:
        webhook_hash = hashlib.sha256(BOT_TOKEN.encode("utf-8")).hexdigest()[:32]
        webhook_path = f"telegram/{webhook_hash}"
        webhook_url = f"{render_url.rstrip('/')}/{webhook_path}"

        print(f"Bot is running on Render: {render_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=webhook_path,
            webhook_url=webhook_url,
            drop_pending_updates=False,
        )
    else:
        print("Bot is running locally...")
        app.run_polling()


if __name__ == "__main__":
    main()
