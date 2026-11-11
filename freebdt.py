import os
import threading
import telebot
from flask import Flask
from pymongo import MongoClient

# --- কনফিগারেশন (আপনার তথ্যগুলো এখানে বসাবেন) ---
TOKEN = "9059189356:AAGJ5YGLVw_cvvK8OQlkyX6hDYHtZBpMGPA"
ADMIN_ID = 7833766898  # আপনার টেলিগ্রাম আইডি (সংখ্যায়)
MONGO_URI = "MONGO_URI = "mongodb://tasr1kva1954_db_user:MB9qXeRSuraCf8pj@ac-jx50sx1-shard-00-00.xzv6fcr.mongodb.net:27017,ac-jx50sx1-shard-00-01.xzv6fcr.mongodb.net:27017,ac-jx50sx1-shard-00-02.xzv6fcr.mongodb.net:27017/?ssl=true&replicaSet=atlas-hsxnjk-shard-0&authSource=admin"
"

# --- ডাটাবেজ কানেকশন ---
client = MongoClient(MONGO_URI)
db = client["free_income_bdt"]
users_col = db["users"]
settings_col = db["settings"]
channels_col = db["channels"]

# ডিফল্ট সেটিংস ইনিশিয়ালাইজ
if not settings_col.find_one({"_id": "config"}):
  settings_col.insert_one({
      "_id": "config",
      "signup_bonus": 50,
      "refer_bonus": 10,
      "min_withdraw": 500,
      "maintenance": False,
  })

bot = telebot.TeleBot(TOKEN)

# --- Flask Server (Render ওয়েব সার্ভিসের পোর্ট রিকোয়ারমেন্ট পূরণের জন্য) ---
app = Flask(__name__)


@app.route("/")
def home():
  return "Telegram Bot is running live & secure!"


# --- মেইন মেনু কিবোর্ড ---
def get_main_keyboard(user_id):
  markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add(
      telebot.types.KeyboardButton("💰 আমার ব্যালেন্স"),
      telebot.types.KeyboardButton("👥 ইনভাইট ও রেফার"),
  )
  markup.add(
      telebot.types.KeyboardButton("🎁 ডেইলি বোনাস"),
      telebot.types.KeyboardButton("💳 টাকা তুলুন"),
  )
  markup.add(
      telebot.types.KeyboardButton("🏆 লিডারবোর্ড"),
      telebot.types.KeyboardButton("ℹ️ হেল্প ও রুলস"),
  )
  if user_id == ADMIN_ID:
    markup.add(telebot.types.KeyboardButton("👑 এডমিন প্যানেল"))
  return markup


# --- /start কমান্ড হ্যান্ডলার ---
@bot.message_handler(commands=["start"])
def cmd_start(message):
  user_id = message.from_user.id
  username = message.from_user.username or "No Username"
  config = settings_col.find_one({"_id": "config"})

  if config.get("maintenance") and user_id != ADMIN_ID:
    bot.send_message(
        user_id, "🛠️ সিস্টেম আপডেট চলছে। দয়া করে কিছু সময় পর চেষ্টা করুন।"
    )
    return

  # রেফারেল হ্যান্ডলিং
  args = message.text.split()
  referrer_id = None
  if len(args) > 1 and args[1].startswith("ref_"):
    try:
      referrer_id = int(args[1].replace("ref_", ""))
    except ValueError:
      pass

  user = users_col.find_one({"telegram_id": user_id})
  if not user:
    signup_bonus = config.get("signup_bonus", 50)
    users_col.insert_one({
        "telegram_id": user_id,
        "username": username,
        "balance": signup_bonus,
        "referrals": 0,
    })

    if referrer_id and referrer_id != user_id:
      ref_bonus = config.get("refer_bonus", 10)
      users_col.update_one(
          {"telegram_id": referrer_id},
          {"$inc": {"balance": ref_bonus, "referrals": 1}},
      )
      try:
        bot.send_message(
            referrer_id,
            f"🔥 নতুন রেফার যুক্ত হয়েছে! আপনার অ্যাকাউন্টে ৳{ref_bonus} যোগ"
            " করা হয়েছে।",
        )
      except Exception:
        pass

  bot.send_message(
      user_id,
      "🎉 স্বাগতম! আপনার মূল মেনু ওপেন হয়েছে। নিچ থেকে অপশন সিলেক্ট করুন:",
      reply_markup=get_main_keyboard(user_id),
  )


# --- টেক্সট মেসেজ ও মেনু হ্যান্ডলার ---
@bot.message_handler(
    func=lambda message: message.text
    in [
        "💰 আমার ব্যালেন্স",
        "👥 ইনভাইট ও রেফার",
        "🎁 ডেইলি বোনাস",
        "💳 টাকা তুলুন",
        "🏆 লিডারবোর্ড",
        "ℹ️ হেল্প ও রুলস",
        "👑 এডমিন প্যানেল",
    ]
)
def handle_menu(message):
  user_id = message.from_user.id
  text = message.text
  user = users_col.find_one({"telegram_id": user_id})
  config = settings_col.find_one({"_id": "config"})

  if text == "💰 আমার ব্যালেন্স":
    bot.send_message(
        user_id,
        f"📊 **আপনার ওয়ালেট:**\n\n🆔 আইডি: `{user_id}`\n💰 ব্যালেন্স:"
        f" **৳{user.get('balance', 0)}**\n👥 রেফার: **{user.get('referrals', 0)}"
        " জন**",
    )

  elif text == "👥 ইনভাইট ও রেফার":
    bot_info = bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    bonus = config.get("refer_bonus", 10)
    bot.send_message(
        user_id,
        f"🔗 **আপনার রেফারেল লিংক:**\n\n`{link}`\n\n📌 প্রতি রেফারে পাবেন"
        f" **৳{bonus}**!",
    )

  elif text == "🎁 ডেইলি বোনাস":
    users_col.update_one({"telegram_id": user_id}, {"$inc": {"balance": 10}})
    bot.send_message(user_id, "🎁 আপনি ডেইলি বোনাস হিসেবে **৳১০** পেয়েছেন!")

  elif text == "💳 টাকা তুলুন":
    min_w = config.get("min_withdraw", 500)
    if user.get("balance", 0) < min_w:
      bot.send_message(
          user_id, f"❌ পর্যাপ্ত ব্যালেন্স নেই! ন্যূনতম উইথড্র **৳{min_w}**।"
      )
    else:
      bot.send_message(
          user_id,
          "✅ উইথড্র রিকোয়েস্ট সফল! ২৪ ঘণ্টার মধ্যে পেমেন্ট পৌঁছে যাবে।",
      )

  elif text == "🏆 লিডারবোর্ড":
    tops = list(users_col.find().sort("referrals", -1).limit(5))
    txt = "🏆 **টপ লিডারবোর্ড:**\n\n"
    for i, u in enumerate(tops, 1):
      txt += f"{i}. @{u.get('username')} — {u.get('referrals', 0)} রেফার\n"
    bot.send_message(user_id, txt)

  elif text == "ℹ️ হেল্প ও রুলস":
    bot.send_message(
        user_id,
        "ℹ️ নিয়ম মেনে কাজ করুন। ফেক রেফার বা স্প্যামিং করলে আইডি ব্যান করা হবে।",
    )

  elif text == "👑 এডমিন প্যানেল" and user_id == ADMIN_ID:
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📊 লাইভ স্ট্যাটস", callback_data="adm_stats"
        )
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📢 ব্রডকাস্ট", callback_data="adm_bc"
        )
    )
    bot.send_message(
        user_id, "👑 **মাস্টার অ্যাডমিন প্যানেল:**", reply_markup=markup
    )


# --- অ্যাডমিন ইনলাইন বাটন হ্যান্ডলার ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
  if call.from_user.id != ADMIN_ID:
    return

  if call.data == "adm_stats":
    total = users_col.count_documents({})
    bot.answer_callback_query(
        call.id, f"মোট রেজিস্টার্ড ইউজার: {total}", show_alert=True
    )
  elif call.data == "adm_bc":
    bot.send_message(
        ADMIN_ID,
        "ব্রডকাস্ট পাঠানোর জন্য /broadcast <message> কমান্ডটি ব্যবহার করুন।",
    )


# --- ব্রডকাস্ট কমান্ড ---
@bot.message_handler(commands=["broadcast"])
def broadcast_msg(message):
  if message.from_user.id != ADMIN_ID:
    return
  text = message.text.replace("/broadcast", "").strip()
  if not text:
    bot.send_message(
        ADMIN_ID, "❌ দয়া করে মেসেজ লিখুন। যেমন: /broadcast আপনার অফার"
    )
    return

  users = list(users_col.find({}, {"telegram_id": 1}))
  cnt = 0
  for u in users:
    try:
      bot.send_message(u["telegram_id"], f"📢 **অফিসিয়াল ঘোষণা:**\n\n{text}")
      cnt += 1
    except Exception:
      pass
  bot.send_message(
      ADMIN_ID, f"✅ সফলভাবে `{cnt}` জন ইউজারের কাছে ব্রডকাস্ট পাঠানো হয়েছে।"
  )


# --- ব্যাকগ্রাউন্ডে বট এবং ফ্লাস্ক একসাথে চালানোর মেকানিজম ---
def run_bot():
  bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
  # ব্যাকগ্রাউন্ড থ্রেডে টেলিগ্রাম বট রান করা
  t = threading.Thread(target=run_bot)
  t.daemon = True
  t.start()

  # Render এর জন্য ডাইনামিক পোর্ট বাইন্ডিং
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
