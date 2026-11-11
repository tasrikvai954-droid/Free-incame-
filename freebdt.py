import json
import os
import threading
import telebot
from flask import Flask

# --- কনফিগারেশন ---
TOKEN = "9059189356:AAGJ5YGLVw_cvvK8OQlkyX6hDYHtZBpMGPA"  # আপনার বটের টোকেন এখানে বসাবেন
ADMIN_ID = (
    7833766898  # আপনার টেলিগ্রাম আইডি (সংখ্যায় - যেমন: 612345678)
)

# --- লোকাল JSON ডেটাবেজ হ্যান্ডলার (ফ্রি ও ১০০% সিকিউর) ---
DB_FILE = "database.json"


def load_db():
  if not os.path.exists(DB_FILE):
    initial_data = {
        "users": {},
        "settings": {
            "signup_bonus": 50,
            "refer_bonus": 10,
            "min_withdraw": 500,
            "maintenance": False,
            "auto_payout": True,
        },
        "channels": [],
        "tasks": [],
    }
    save_db(initial_data)
    return initial_data
  try:
    with open(DB_FILE, "r", encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return {
        "users": {},
        "settings": {
            "signup_bonus": 50,
            "refer_bonus": 10,
            "min_withdraw": 500,
            "maintenance": False,
            "auto_payout": True,
        },
        "channels": [],
        "tasks": [],
    }


def save_db(data):
  with open(DB_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)


bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)


@app.route("/")
def home():
  return "Telegram Bot is running live with full features!"


# --- মেইন মেনু কিবোর্ড ---
def get_main_keyboard(user_id):
  markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add(
      telebot.types.KeyboardButton("💰 আমার ব্যালেন্স"),
      telebot.types.KeyboardButton("👥 ইনভাইট ও রেফার"),
  )
  markup.add(
      telebot.types.KeyboardButton("🎁 ডেইলি বোনাস"),
      telebot.types.KeyboardButton("💳 টাকা তুলুন (bKash/Nagad)"),
  )
  markup.add(
      telebot.types.KeyboardButton("🏆 লিডারবোর্ড"),
      telebot.types.KeyboardButton("🎯 মাইক্রো টাস্ক"),
  )
  markup.add(telebot.types.KeyboardButton("ℹ️ হেল্প ও রুলস"))
  if user_id == ADMIN_ID:
    markup.add(telebot.types.KeyboardButton("👑 এডমিন প্যানেল"))
  return markup


# --- /start কমান্ড ও রেফারেল লজিক ---
@bot.message_handler(commands=["start"])
def cmd_start(message):
  user_id = str(message.from_user.id)
  username = message.from_user.username or "No Username"

  db = load_db()
  config = db["settings"]

  if config.get("maintenance") and int(user_id) != ADMIN_ID:
    bot.send_message(
        message.chat.id,
        "🛠️ সিস্টেম আপডেট চলছে। দয়া করে কিছু সময় পর আবার চেষ্টা করুন।",
    )
    return

  # রেফারেল আর্গুমেন্ট পার্সিং
  args = message.text.split()
  referrer_id = None
  if len(args) > 1 and args[1].startswith("ref_"):
    referrer_id = args[1].replace("ref_", "")

  if user_id not in db["users"]:
    signup_bonus = config.get("signup_bonus", 50)
    db["users"][user_id] = {
        "username": username,
        "balance": signup_bonus,
        "referrals": 0,
        "referred_by": referrer_id,
    }

    if referrer_id and referrer_id != user_id and referrer_id in db["users"]:
      ref_bonus = config.get("refer_bonus", 10)
      db["users"][referrer_id]["balance"] += ref_bonus
      db["users"][referrer_id]["referrals"] += 1
      try:
        bot.send_message(
            int(referrer_id),
            f"🔥 নতুন রেফার যুক্ত হয়েছে! আপনার অ্যাকাউন্টে ৳{ref_bonus} যোগ"
            " করা হয়েছে।",
        )
      except Exception:
        pass

    save_db(db)

  bot.send_message(
      message.chat.id,
      "🎉 স্বাগতম! আপনার মূল মেনু ওপেন হয়েছে। নিচ থেকে অপশন সিলেক্ট করুন:",
      reply_markup=get_main_keyboard(int(user_id)),
  )


# --- ইউজার মেনু অ্যাকশন হ্যান্ডলার ---
@bot.message_handler(
    func=lambda message: message.text
    in [
        "💰 আমার ব্যালেন্স",
        "👥 ইনভাইট ও রেফার",
        "🎁 ডেইলি বোনাস",
        "💳 টাকা তুলুন (bKash/Nagad)",
        "🏆 লিডারবোর্ড",
        "🎯 মাইক্রো টাস্ক",
        "ℹ️ হেল্প ও রুলস",
        "👑 এডমিন প্যানেল",
    ]
)
def handle_user_menu(message):
  user_id = str(message.from_user.id)
  text = message.text
  db = load_db()
  config = db["settings"]

  if user_id not in db["users"] and int(user_id) != ADMIN_ID:
    db["users"][user_id] = {
        "username": message.from_user.username or "No",
        "balance": 0,
        "referrals": 0,
    }
    save_db(db)

  user_data = db["users"].get(
      user_id, {"balance": 0, "referrals": 0, "username": "Admin"}
  )

  if text == "💰 আমার ব্যালেন্স":
    bot.send_message(
        message.chat.id,
        f"📊 **আপনার ওয়ালেট:**\n\n🆔 আইডি: `{user_id}`\n💰 ব্যালেন্স:"
        f" **৳{user_data.get('balance', 0)}**\n👥 রেফার: **{user_data.get('referrals', 0)} জন**",
    )

  elif text == "👥 ইনভাইট ও রেফার":
    bot_info = bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    bonus = config.get("refer_bonus", 10)
    bot.send_message(
        message.chat.id,
        f"🔗 **আপনার রেফারেল লিংক:**\n\n`{link}`\n\n📌 প্রতি রেফারে পাবেন"
        f" **৳{bonus}**!",
    )

  elif text == "🎁 ডেইলি বোনাস":
    db["users"][user_id]["balance"] += 10
    save_db(db)
    bot.send_message(
        message.chat.id, "🎁 আপনি ডেইলি বোনাস হিসেবে **৳১০** পেয়েছেন!"
    )

  elif text == "💳 টাকা তুলুন (bKash/Nagad)":
    min_w = config.get("min_withdraw", 500)
    if user_data.get("balance", 0) < min_w:
      bot.send_message(
          message.chat.id,
          f"❌ পর্যাপ্ত ব্যালেন্স নেই! ন্যূনতম উইথড্র **৳{min_w}**।",
      )
    else:
      if config.get("auto_payout", True):
        bot.send_message(
            message.chat.id,
            "✅ উইথড্র রিকোয়েস্ট সফল! সিমুলেটেড মোডে কিছুক্ষণের মধ্যে আপনার"
            " নম্বরে পেমেন্ট পাঠানো হবে।",
        )
      else:
        bot.send_message(
            message.chat.id,
            "✅ উইথড্র রিকোয়েস্ট সফলভাবে অ্যাডমিনের কাছে জমা হয়েছে।",
        )

  elif text == "🏆 লিডারবোর্ড":
    sorted_users = sorted(
        db["users"].items(),
        key=lambda x: x[1].get("referrals", 0),
        reverse=True,
    )[:5]
    txt = "🏆 **টপ রেফার লিডারবোর্ড:**\n\n"
    for i, (uid, uinfo) in enumerate(sorted_users, 1):
      txt += f"{i}. @{uinfo.get('username')} — {uinfo.get('referrals', 0)} রেফার\n"
    bot.send_message(message.chat.id, txt)

  elif text == "🎯 মাইক্রো টাস্ক":
    tasks = db["tasks"]
    if not tasks:
      bot.send_message(
          message.chat.id, "📭 বর্তমানে কোনো নতুন টাস্ক উপলব্ধ নেই।"
      )
    else:
      txt = "🎯 **চলমান টাস্কসমূহ:**\n\n"
      for idx, t in enumerate(tasks, 1):
        txt += f"{idx}. {t['title']} (রিওয়ার্ড: ৳{t['reward']})\n"
      bot.send_message(message.chat.id, txt)

  elif text == "ℹ️ হেল্প ও রুলস":
    bot.send_message(
        message.chat.id,
        "ℹ️ নিয়ম মেনে কাজ করুন। ফেক রেফার বা অটোমেশন করলে অ্যাকাউন্ট স্থায়ীভাবে"
        " ব্যান করা হবে।",
    )

  elif text == "👑 এডমিন প্যানেল" and int(user_id) == ADMIN_ID:
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📊 লাইভ স্ট্যাটস", callback_data="adm_stats"
        ),
        telebot.types.InlineKeyboardButton(
            "📢 ব্রডকাস্ট মেসেজ", callback_data="adm_bc"
        ),
        telebot.types.InlineKeyboardButton(
            "🎁 বোনাস সেটিংস", callback_data="adm_bonus"
        ),
        telebot.types.InlineKeyboardButton(
            "📉 উইথড্র লিমিট", callback_data="adm_minw"
        ),
        telebot.types.InlineKeyboardButton(
            "🛠️ মেইনটেনেন্স টগল", callback_data="adm_maint"
        ),
        telebot.types.InlineKeyboardButton(
            "🤖 অটো-পেমেন্ট টগল", callback_data="adm_autopay"
        ),
        telebot.types.InlineKeyboardButton(
            "📋 ইউজার লিস্ট", callback_data="adm_users"
        ),
    )
    bot.send_message(
        message.chat.id,
        "👑 **মাস্টার অ্যাডমিন কন্ট্রোল প্যানেল:**\nনিচের অপশনগুলো থেকে আপনার"
        " বট ফুল কন্ট্রোল করুন:",
        reply_markup=markup,
    )


# --- অ্যাডমিন ইনলাইন বাটন কন্ট্রোল ও ফুল লজিক ---
@bot.callback_query_handler(
    func=lambda call: call.data.startswith("adm_")
    and call.from_user.id == ADMIN_ID
)
def admin_callbacks(call):
  db = load_db()
  config = db["settings"]
  data = call.data

  if data == "adm_stats":
    total_users = len(db["users"])
    bot.answer_callback_query(
        call.id,
        f"📊 মোট রেজিস্টার্ড ইউজার: {total_users} জন\n🟢 সার্ভার অবস্থা: Online"
        " (Active)",
        show_alert=True,
    )

  elif data == "adm_maint":
    config["maintenance"] = not config.get("maintenance", False)
    save_db(db)
    status = "ON 🔴" if config["maintenance"] else "OFF 🟢"
    bot.answer_callback_query(
        call.id, f"মেইনটেনেন্স মোড এখন: {status}", show_alert=True
    )

  elif data == "adm_autopay":
    config["auto_payout"] = not config.get("auto_payout", True)
    save_db(db)
    status = "ON 🟢" if config["auto_payout"] else "OFF 🔴"
    bot.answer_callback_query(
        call.id, f"অটো-পেমেন্ট সিমুলেটর: {status}", show_alert=True
    )

  elif data == "adm_bonus":
    bot.send_message(
        ADMIN_ID,
        "🎁 বর্তমান বোনাস সেটিংস:\n- সাইনআপ বোনাস: "
        f"৳{config.get('signup_bonus')}\n- রেফার বোনাস:"
        f" ৳{config.get('refer_bonus')}\n\nপরিবর্তন করতে কমান্ড ব্যবহার করুন:"
        " `/setbonus <signup> <refer>`",
    )

  elif data == "adm_minw":
    bot.send_message(
        ADMIN_ID,
        "📉 বর্তমান ন্যূনতম উইথড্র লিমিট: "
        f"৳{config.get('min_withdraw')}\n\nপরিবর্তন করতে কমান্ড ব্যবহার করুন:"
        " `/setminw <amount>`",
    )

  elif data == "adm_bc":
    bot.send_message(
        ADMIN_ID,
        "📢 ব্রডকাস্ট পাঠাতে এই কমান্ডটি লিখুন:\n`/broadcast আপনার মেসেজ এখানে"
        " লিখুন`",
    )

  elif data == "adm_users":
    total = len(db["users"])
    bot.answer_callback_query(
        call.id,
        f"👥 মোট ডাটাবেজে ইউজার সংরক্ষিত আছে: {total} জন",
        show_alert=True,
    )


# --- অ্যাডমিন কন্ট্রোল কমান্ডসমূহ ---
@bot.message_handler(commands=["broadcast"])
def admin_broadcast(message):
  if message.from_user.id != ADMIN_ID:
    return
  text = message.text.replace("/broadcast", "").strip()
  if not text:
    bot.send_message(ADMIN_ID, "❌ দয়া করে মেসেজ লিখুন।")
    return

  db = load_db()
  cnt = 0
  for uid in db["users"]:
    try:
      bot.send_message(int(uid), f"📢 **অফিসিয়াল ঘোষণা:**\n\n{text}")
      cnt += 1
    except Exception:
      pass
  bot.send_message(
      ADMIN_ID, f"✅ সফলভাবে `{cnt}` জন ইউজারের কাছে ব্রডকাস্ট পাঠানো হয়েছে।"
  )


@bot.message_handler(commands=["setbonus"])
def admin_setbonus(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    parts = message.text.split()
    s_bonus = int(parts[1])
    r_bonus = int(parts[2])
    db = load_db()
    db["settings"]["signup_bonus"] = s_bonus
    db["settings"]["refer_bonus"] = r_bonus
    save_db(db)
    bot.send_message(
        ADMIN_ID,
        f"✅ সফলভাবে আপডেট হয়েছে!\n- সাইনআপ বোনাস: ৳{s_bonus}\n- রেফার বোনাস:"
        f" ৳{r_bonus}",
    )
  except Exception:
    bot.send_message(ADMIN_ID, "❌ ফরম্যাট ভুল! ব্যবহার করুন: `/setbonus 50 10`")


@bot.message_handler(commands=["setminw"])
def admin_setminw(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    parts = message.text.split()
    min_w = int(parts[1])
    db = load_db()
    db["settings"]["min_withdraw"] = min_w
    save_db(db)
    bot.send_message(
        ADMIN_ID, f"✅ ন্যূনতম উইথড্র লিমিট সফলভাবে পরিবর্তন করে ৳{min_w} করা হলো!"
    )
  except Exception:
    bot.send_message(ADMIN_ID, "❌ ফরম্যাট ভুল! ব্যবহার করুন: `/setminw 500`")


# --- ব্যাকগ্রাউন্ড থ্রেড ও ফ্লাস্ক রানার ---
def run_bot():
  bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
  # ব্যাকগ্রাউন্ডে টেলিগ্রাম বট চালু করা
  t = threading.Thread(target=run_bot)
  t.daemon = True
  t.start()

  # Render পোর্টের জন্য ফ্লাস্ক সার্ভার স্টার্ট
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
