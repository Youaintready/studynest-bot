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

async def show_subject_buttons(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    selected = context.user_data["subjects"]
    buttons = [
        [InlineKeyboardButton(f"{'✅' if s in selected else ''} {s}", callback_data=s)]
        for s in SUBJECTS
    ]
    buttons.append([InlineKeyboardButton("✅ Done", callback_data="done")])

    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text("📚 Select your subjects:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update_or_query.message.reply_text("📚 Select your subjects:", reply_markup=InlineKeyboardMarkup(buttons))
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

async def show_next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = users.find_one({"telegram_id": user_id})
    if not user:
        await update.effective_message.reply_text("❌ No profile found. Use /start to register.")
        return ConversationHandler.END

    candidates = list(users.find({
        "telegram_id": {"$ne": user_id},
        "grade": user["grade"],
        "subjects": {"$in": user["subjects"]},
        "telegram_id": {"$nin": user.get("likes", []) + user.get("matched", [])}
    }))
    shuffle(candidates)

    if not candidates:
        await update.effective_message.reply_text("🚫 No more matches right now. Tap Refresh Matches later!")
        return BROWSING

    match = candidates[0]
    context.user_data["current_match"] = match["telegram_id"]

    profile_text = f"👤 {match['name']}\n🎓 {match['grade']}\n📚 Subjects: {', '.join(match['subjects'])}"
    buttons = [
        [InlineKeyboardButton("❤️ Like", callback_data="like"), InlineKeyboardButton("❌ Skip", callback_data="skip")]
    ]
    await update.effective_message.reply_text(profile_text, reply_markup=InlineKeyboardMarkup(buttons))
    return BROWSING

async def handle_match_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    user_id = update.effective_user.id
    user = users.find_one({"telegram_id": user_id})
    match_id = context.user_data.get("current_match")
    match_user = users.find_one({"telegram_id": match_id})

    if action == "like":
        users.update_one({"telegram_id": user_id}, {"$push": {"likes": match_id}})
        if user_id in match_user.get("likes", []):
            users.update_one({"telegram_id": user_id}, {"$push": {"matched": match_id}})
            users.update_one({"telegram_id": match_id}, {"$push": {"matched": user_id}})
            await query.edit_message_text("🎉 It’s a Match! 🎊 You can now message each other.")
            if match_user.get("username"):
                await query.message.reply_text(f"🔗 Username: @{match_user['username']}")
        else:
            await query.edit_message_text("👍 Like sent! Looking for more...")
    else:
        await query.edit_message_text("⏭️ Skipped! Searching more...")

    return await show_next_profile(update, context)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = users.find_one({"telegram_id": update.effective_user.id})
    if not user:
        await update.message.reply_text("❌ No profile yet. Use /start to register.")
        return
    profile = f"👤 Name: {user['name']}\n🎓 Grade: {user['grade']}\n📚 Subjects: {', '.join(user['subjects'])}"
    await update.message.reply_text(profile)

# Application setup
app = Application.builder().token(BOT_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ASK_GRADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_location)],
        ASK_LOCATION: [MessageHandler(filters.LOCATION, ask_subjects)],
        ASK_SUBJECTS: [CallbackQueryHandler(handle_subject_selection)],
        BROWSING: [CallbackQueryHandler(handle_match_action)]
    },
    fallbacks=[]
)

app.add_handler(conv_handler)
app.add_handler(CommandHandler("profile", show_profile))

if __name__ == '__main__':
    print("🤖 StudyNest is running...")
    app.run_polling()

