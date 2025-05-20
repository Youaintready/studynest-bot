import os
from dotenv import load_dotenv
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup,
    ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ConversationHandler, ContextTypes, CallbackQueryHandler
)
from pymongo import MongoClient
from random import shuffle

# Load .env
load_dotenv()
BOT_TOKEN = os.getenv("8155679286:AAGn0SCC7DkO6Jmw0pTBilwtCLQ0xdROoxg")
MONGO_URI = os.getenv("mongodb+srv://studynestuser:sHcjjtbZdUqFJkE9@studynestcluster.6cnx0t3.mongodb.net/?retryWrites=true&w=majority&appName=StudyNestCluster")

# MongoDB setup
client = MongoClient(MONGO_URI)
db = client["studynest"]
users = db["users"]

# States
ASK_GRADE, ASK_NAME, ASK_LOCATION, ASK_SUBJECTS, BROWSING, EDIT_PROFILE = range(6)
VALID_GRADES = ["Grade 10", "Grade 11", "Grade 12", "University Freshman"]
SUBJECTS = [
    "Biology", "Chemistry", "Physics", "Mathematics", "ICT",
    "History", "Geography", "Civics", "Economics", "English", "Amharic"
]

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Welcome to StudyNest — where smart minds meet & match!\n\n"
        "👉 Select your grade level:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(g)] for g in VALID_GRADES], resize_keyboard=True
        )
    )
    return ASK_GRADE

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    grade = update.message.text
    if grade not in VALID_GRADES:
        await update.message.reply_text("⚠️ Pick from the available grade options.")
        return ASK_GRADE

    context.user_data["grade"] = grade
    await update.message.reply_text("😊 Nice! What’s your full name?")
    return ASK_NAME

async def ask_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    button = KeyboardButton("📍 Share My Location", request_location=True)
    await update.message.reply_text(
        "📌 Share your location to find nearby study buddies:",
        reply_markup=ReplyKeyboardMarkup([[button]], resize_keyboard=True)
    )
    return ASK_LOCATION

async def ask_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.location:
        await update.message.reply_text("⚠️ Please use the location button.")
        return ASK_LOCATION

    context.user_data["location"] = {
        "lat": update.message.location.latitude,
        "lon": update.message.location.longitude
    }
    context.user_data["subjects"] = []
    return await show_subject_buttons(update, context)

async def show_subject_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected = context.user_data["subjects"]
    buttons = [
        [InlineKeyboardButton(f"{'✅' if s in selected else ''} {s}", callback_data=s)]
        for s in SUBJECTS
    ]
    buttons.append([InlineKeyboardButton("✅ Done", callback_data="done")])
    await update.message.reply_text("📚 Select your subjects:", reply_markup=InlineKeyboardMarkup(buttons))
    return ASK_SUBJECTS

async def handle_subject_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject = query.data

    if subject == "done":
        user = {
            "telegram_id": update.effective_user.id,
            "username": update.effective_user.username,
            "name": context.user_data["name"],
            "grade": context.user_data["grade"],
            "location": context.user_data["location"],
            "subjects": context.user_data["subjects"],
            "likes": [],
            "liked_by": [],
            "matched": []
        }
        users.update_one({"telegram_id": user["telegram_id"]}, {"$set": user}, upsert=True)
        await query.edit_message_text("🎉 You’re all set! Finding matches...")
        return await show_next_profile(update, context)

    subjects = context.user_data["subjects"]
    if subject in subjects:
        subjects.remove(subject)
    else:
        subjects.append(subject)
    context.user_data["subjects"] = subjects
    return await show_subject_buttons(query, context)

# Matching logic remains similar to earlier version (not shown here for space)

# Add handlers for My Profile, Edit Profile, Refresh Matches, etc.
# Continue from here in the next part of the implementation...
