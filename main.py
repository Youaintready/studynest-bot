import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["studynest"]
users = db["users"]

# States
NAME, LEVEL, SUBJECTS, TIME, LOCATION, BIO = range(6)

education_levels = ["High School", "Undergrad", "Graduate", "Other"]
study_times = ["Morning", "Afternoon", "Evening", "Flexible"]

def keyboard(options):
    return ReplyKeyboardMarkup([[opt] for opt in options], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐣 Welcome to StudyNest!\nYour cozy place to find study buddies.\n\nWhat’s your name?"
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("🎓 What’s your education level?", reply_markup=keyboard(education_levels))
    return LEVEL

async def get_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["level"] = update.message.text
    await update.message.reply_text("📚 What subjects are you interested in?\n(Separate with commas)", reply_markup=None)
    return SUBJECTS

async def get_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["subjects"] = [s.strip() for s in update.message.text.split(",")]
    await update.message.reply_text("🕒 When do you prefer to study?", reply_markup=keyboard(study_times))
    return TIME

async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["time"] = update.message.text
    await update.message.reply_text("🌍 Where are you located? (Or type 'skip')", reply_markup=None)
    return LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = update.message.text
    context.user_data["location"] = None if loc.lower() == "skip" else loc
    await update.message.reply_text("🧑‍💬 Write a short fun bio about yourself:")
    return BIO

async def get_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["bio"] = update.message.text
    context.user_data["telegram_id"] = update.message.from_user.id

    users.update_one(
        {"telegram_id": context.user_data["telegram_id"]},
        {"$set": context.user_data},
        upsert=True
    )

    await update.message.reply_text("✅ You’re all set! Welcome to StudyNest! 🎉")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Registration cancelled. Use /start to try again.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_level)],
            SUBJECTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_subjects)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_time)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_location)],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bio)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()

