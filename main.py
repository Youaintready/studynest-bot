import os
from dotenv import load_dotenv
from telegram import (
    Update, 
    KeyboardButton, 
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ConversationHandler, 
    ContextTypes
)
from pymongo import MongoClient

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# Setup MongoDB
client = MongoClient(MONGO_URI)
db = client["studynest"]
users_collection = db["users"]

# Define states
ASK_GRADE, ASK_NAME, ASK_LOCATION, FINISHED = range(4)

VALID_GRADES = ["Grade 10", "Grade 11", "Grade 12", "University Freshman"]

# Start conversation
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎓 Welcome to StudyNest! Let's build your profile.\n\n"
        "👉 First, choose your grade level:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(g)] for g in VALID_GRADES],
            resize_keyboard=True
        )
    )
    return ASK_GRADE

# Handle grade selection
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    grade = update.message.text
    if grade not in VALID_GRADES:
        await update.message.reply_text("❗ Please choose a valid grade.")
        return ASK_GRADE

    context.user_data["grade"] = grade
    await update.message.reply_text(
        "🌟 Great! Now, what's your full name?",
        reply_markup=ReplyKeyboardRemove()
    )
    return ASK_NAME

# Ask for location
async def ask_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()

    location_button = KeyboardButton("📍 Share Location", request_location=True)
    await update.message.reply_text(
        "📍 Please share your location to help us find study groups near you!",
        reply_markup=ReplyKeyboardMarkup([[location_button]], resize_keyboard=True)
    )
    return ASK_LOCATION

# Save user
async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.location:
        location = update.message.location
        user_data = {
            "telegram_id": update.effective_user.id,
            "name": context.user_data["name"],
            "grade": context.user_data["grade"],
            "location": {"lat": location.latitude, "lon": location.longitude}
        }
        users_collection.update_one(
            {"telegram_id": user_data["telegram_id"]},
            {"$set": user_data},
            upsert=True
        )
        await update.message.reply_text(
            f"🎉 Profile created successfully, {user_data['name']}!\n\n"
            "📚 You'll now be matched with amazing study groups!",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text("❗ Please share your location using the button.")
        return ASK_LOCATION

# Cancel handler
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Setup cancelled. You can start again anytime by sending /start.")
    return ConversationHandler.END

# Main bot setup
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_GRADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_location)],
            ASK_LOCATION: [MessageHandler(filters.LOCATION, save_user)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    print("🤖 StudyNest bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

