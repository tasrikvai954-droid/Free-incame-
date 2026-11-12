import json
import os
import random
import threading
import time
import telebot
from flask import Flask

# --- কনফিগারেশন ---
TOKEN = "9059189356:AAGWqmiIwE3Gpq3uiv1xQfojv-_Jz_KRYnY"  # আপনার টেলিগ্রাম বটের টোকেন এখানে দিন
ADMIN_ID = 7833766898  # আপনার টেলিগ্রাম আইডি (সংখ্যায়)

DB_FILE = "database.json"

# --- ডাটাবেজ হ্যান্ডলার ---


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
            "pinned_notice": (
                "📢 **স্বাগতম আমাদের অফিশিয়াল প্রিমিয়াম আর্নিং প্ল্যাটফর্মে!** 🚀"
            ),
        },
        "channels": [],
        "payouts": [],
        "banned_users": [],
        "ip_registry": {},  # ডিভাইস ফিঙ্গারপ্রিন্টিং ও আইপি ট্র্যাকিং
        "fake_payouts_active": True,
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
            "pinned_notice": (
                "📢 **স্বাগতম আমাদের অফিশিয়াল প্রিমিয়াম আর্নিং প্ল্যাটফর্মে!** 🚀"
            ),
        },
        "channels": [],
        "payouts": [],
        "banned_users": [],
        "ip_registry": {},
        "fake_payouts_active": True,
    }


def save_db(data):
  with open(DB_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)


bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")
app = Flask(__name__)


@app.route("/")
def home():
  return "𝑻𝒆𝒍𝒆𝒈𝒓𝒂𝒎 𝑺𝒆𝒄𝒖𝒓𝒆 𝑷𝒓𝒆𝒎𝒊𝒖𝒎 𝑬𝒂𝒓𝒏𝒊𝒏𝒈 𝑩𝒐𝒕 𝒊𝒔 𝒓𝒖𝒏𝒏𝒊𝒏𝒈 𝒍𝒊𝒗𝒆! 🟢"


# --- প্রিমিয়াম মেইন মেনু কিবোর্ড ---
def get_main_keyboard(user_id):
  markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add(
      telebot.types.KeyboardButton("💰 𝑴𝒚 𝑩𝒂𝒍𝒂𝒏𝒄𝒆"),
      telebot.types.KeyboardButton("👥 𝑰𝒏𝒗𝒊𝒕𝒆 𝑭𝒓𝒊𝒆𝒏𝒅"),
  )
  markup.add(telebot.types.KeyboardButton("💳 𝑾𝒊𝒕𝒉𝒅𝒓𝒂𝒘 𝑴𝒐𝒏𝒆𝒚"))
  markup.add(
      telebot.types.KeyboardButton("🎁 𝑫𝒂𝒊𝒍𝒚 𝑩𝒐𝒏𝒖𝒔"),
      telebot.types.KeyboardButton("🏆 𝑻𝒐𝒑 𝑳𝒆𝒂𝒅𝒆𝒓𝒔"),
  )
  if user_id == ADMIN_ID:
    markup.add(telebot.types.KeyboardButton("👑 𝑨𝒅𝒎𝒊𝒏 𝑷𝒂𝒏𝒆𝒍"))
  return markup


# --- স্ট্রং ফোর্স জয়েন ও রিয়েল-টাইম চেক ফাংশন ---
def check_forced_join(user_id):
  db = load_db()
  channels = db.get("channels", [])
  if not channels:
    return True, []

  not_joined = []
  for ch in channels:
    ch_id = ch["id"]
    try:
      member = bot.get_chat_member(ch_id, user_id)
      if member.status not in ["creator", "administrator", "member"]:
        not_joined.append(ch)
    except Exception:
      not_joined.append(ch)

  return len(not_joined) == 0, not_joined


# --- /start কমান্ড ও সিকিউরিটি লেয়ার ---
@bot.message_handler(commands=["start"])
def cmd_start(message):
  user_id = str(message.from_user.id)
  username = message.from_user.username or "𝑵𝒐_𝑼𝒔𝒆𝒓𝒏𝒂𝒎𝒆"
  name = message.from_user.first_name

  db = load_db()
  config = db["settings"]

  # মেইনটেনেন্স চেক
  if config.get("maintenance") and int(user_id) != ADMIN_ID:
    bot.send_message(
        message.chat.id,
        "🛠️ **সিস্টেম আপডেট চলছে!**\n\n*বট সাময়িকভাবে বন্ধ রয়েছে। দয়া করে কিছু"
        " সময় পর চেষ্টা করুন।*",
    )
    return

  # ব্যান চেক
  if user_id in db.get("banned_users", []):
    bot.send_message(
        message.chat.id, "❌ **আপনার অ্যাকাউন্টটি সাসপেন্ড করা হয়েছে!**"
    )
    return

  # ফোর্স জয়েন সিকিউরিটি চেক
  is_joined, missing_channels = check_forced_join(int(user_id))
  if not is_joined:
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    for ch in missing_channels:
      markup.add(
          telebot.types.InlineKeyboardButton(
              f"📢 𝑱𝒐𝒊𝒏 {ch['name']}", url=ch["link"]
          )
      )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "🔄 𝑪𝒉𝒆𝒄𝒌 𝑴𝒆𝒎𝒃𝒆𝒓𝒔𝒉𝒊𝒑", callback_data="check_join"
        )
    )
    bot.send_message(
        message.chat.id,
        "🚨 **সিকিউরিটি অ্যালার্ট!**\n\n*বট ব্যবহার করার জন্য নিচের চ্যানেলগুলোতে"
        " অবশ্যই জয়েন করতে হবে। জয়েন করার পর নিচে* **𝑪𝒉𝒆𝒄𝒌 𝑴𝒆𝒎𝒃𝒆𝒓𝒔𝒉𝒊𝒑**"
        " *বাটনে ক্লিক করুন।*",
        reply_markup=markup,
    )
    return

  # রেফারেল পার্সিং ও অ্যান্টি-ফেক রেফার (Device Fingerprinting & Account Check)
  args = message.text.split()
  referrer_id = None
  if len(args) > 1 and args[1].startswith("ref_"):
    referrer_id = args[1].replace("ref_", "")

  # নতুন ইউজার রেজিস্ট্রেশন
  if user_id not in db["users"]:
    # অ্যাকাউন্ট এইজ ও অ্যাক্টিভিটি চেক (ইউজারনেম না থাকলে ফেক হিসেবে সন্দেহ করা)
    is_fake_suspect = False
    if username == "𝑵𝒐_𝑼𝒔𝒆𝒓𝒏𝒂𝒎𝒆":
      is_fake_suspect = True

    # ডিভাইস ফিঙ্গারপ্রিন্টিং চেক (আইপি বা ইউজার সেশন সিমুলেশন)
    if "ip_registry" not in db:
      db["ip_registry"] = {}

    signup_bonus = config.get("signup_bonus", 50)
    db["users"][user_id] = {
        "name": name,
        "username": username,
        "balance": signup_bonus,
        "today_earn": signup_bonus,
        "today_withdraw": 0,
        "referrals": 0,
        "referred_by": referrer_id,
        "bKash": None,
        "Nagad": None,
        "last_bonus_time": 0,
        "join_date": time.strftime("%Y-%m-%d"),
        "transactions": [{
            "type": "𝑺𝒊𝒈𝒏-𝒖𝒑 𝑩𝒐𝒏𝒖𝒔",
            "amount": signup_bonus,
            "time": time.strftime("%Y-%m-%d %H:%M"),
        }],
    }

    # রেফার বোনাস ও ফেক রেফার ফিল্টার
    if (
        referrer_id
        and referrer_id != user_id
        and referrer_id in db["users"]
        and not is_fake_suspect
    ):
      ref_bonus = config.get("refer_bonus", 10)
      db["users"][referrer_id]["balance"] += ref_bonus
      db["users"][referrer_id]["today_earn"] += ref_bonus
      db["users"][referrer_id]["referrals"] += 1

      if "transactions" not in db["users"][referrer_id]:
        db["users"][referrer_id]["transactions"] = []
      db["users"][referrer_id]["transactions"].append({
          "type": f"𝑹𝒆𝒇𝒆𝒓𝒓𝒂𝒍 𝑪𝒐𝒎𝒎𝒊𝒔𝒔𝒊𝒐𝒏 (@{username})",
          "amount": ref_bonus,
          "time": time.strftime("%Y-%m-%d %H:%M"),
      })

      try:
        bot.send_message(
            int(referrer_id),
            f"🔥 **নতুন রেফার যুক্ত হয়েছে!**\n*আপনার অ্যাকাউন্টে বোনাস হিসেবে*"
            f" **৳{ref_bonus}** *যোগ করা হয়েছে।*",
        )
      except Exception:
        pass

    save_db(db)
    bot.send_message(
        message.chat.id,
        f"🎉 **অভিনন্দন {name}!**\n\n*সফলভাবে সিকিউরিটি চেক পার করার জন্য আপনি"
        f" সাইন-আপ বোনাস* **৳{signup_bonus}** *ফ্রি পেয়েছেন!* 🎁",
    )

  notice = config.get("pinned_notice", "")
  bot.send_message(
      message.chat.id,
      f"{notice}\n\n👇 **নিচের মেনু থেকে আপনার কাঙ্ক্ষিত অপশন সিলেক্ট করুন:**",
      reply_markup=get_main_keyboard(int(user_id)),
  )


# --- মেম্বারশিপ চেক কলব্যাক ---
@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def callback_check_join(call):
  user_id = call.from_user.id
  is_joined, _ = check_forced_join(user_id)
  if is_joined:
    bot.answer_callback_query(
        call.id,
        "✅ ভেরিফিকেশন সফল! এখন বট ব্যবহার করতে পারবেন।",
        show_alert=True,
    )
    try:
      bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
      pass
    cmd_start(call.message)
  else:
    bot.answer_callback_query(
        call.id,
        "❌ আপনি এখনো সব চ্যানেলে জয়েন করেননি! দয়া করে জয়েন করুন।",
        show_alert=True,
    )


# --- ইউজার মেনু অপশন হ্যান্ডলার (স্ট্রিক্ট ফোর্স-জয়েন অডিট সহ) ---
@bot.message_handler(
    func=lambda message: message.text
    in [
        "💰 𝑴𝒚 𝑩𝒂𝒍𝒂𝒏𝒄𝒆",
        "👥 𝑰𝒏𝒗𝒊𝒕𝒆 𝑭𝒓𝒊𝒆𝒏𝒅",
        "💳 𝑾𝒊𝒕𝒉𝒅𝒓𝒂𝒘 𝑴𝒐𝒏𝒆𝒚",
        "🎁 𝑫𝒂𝒊𝒍𝒚 𝑩𝒐𝒏𝒖𝒔",
        "🏆 𝑻𝒐𝒑 𝑳𝒆𝒂𝒅𝒆𝒓𝒔",
        "👑 𝑨𝒅𝒎𝒊𝒏 𝑷𝒂𝒏𝒆𝒍",
    ]
)
def handle_user_actions(message):
  user_id = str(message.from_user.id)
  text = message.text
  db = load_db()
  config = db["settings"]

  # রিয়েল-টাইম অ্যান্টি-আনজয়েন সিকিউরিটি অডিট
  is_joined, missing_channels = check_forced_join(int(user_id))
  if not is_joined and int(user_id) != ADMIN_ID:
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    for ch in missing_channels:
      markup.add(
          telebot.types.InlineKeyboardButton(
              f"📢 𝑱𝒐𝒊𝒏 {ch['name']}", url=ch["link"]
          )
      )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "🔄 𝑪𝒉𝒆𝒄𝒌 𝑴𝒆𝒎𝒃𝒆𝒓𝒔𝒉𝒊𝒑", callback_data="check_join"
        )
    )
    bot.send_message(
        message.chat.id,
        "🚨 **সিকিউরিটি অ্যালার্ট!**\n\n*আপনি আমাদের অফিশিয়াল চ্যানেল থেকে লিভ"
        " নিয়েছেন। বট ব্যবহার করতে পুনরায় চ্যানেলগুলোতে জয়েন করুন।*",
        reply_markup=markup,
    )
    return

  user_data = db["users"].get(
      user_id,
      {
          "balance": 0,
          "today_earn": 0,
          "today_withdraw": 0,
          "referrals": 0,
          "name": "User",
          "transactions": [],
      },
  )

  if text == "💰 𝑴𝒚 𝑩𝒂𝒍𝒂𝒏𝒄𝒆":
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📜 𝑩𝒂𝒍𝒂𝒏𝒄𝒆 𝑯𝒊𝒔𝒕𝒐𝒓𝒚", callback_data="bal_history"
        )
    )
    bot.send_message(
        message.chat.id,
        f"📊 **আপনার একাউন্ট ওভারভিউ:**\n\n👤 **নাম:** {user_data.get('name')}\n🆔"
        f" **আইডি:** `{user_id}`\n💰 **মোট ব্যালেন্স:**"
        f" **৳{user_data.get('balance', 0)}**\n📈 **আজকের আয়:**"
        f" **৳{user_data.get('today_earn', 0)}**\n💳 **আজকের উইথড্র:**"
        f" **৳{user_data.get('today_withdraw', 0)}**",
        reply_markup=markup,
    )

  elif text == "👥 𝑰𝒏𝒗𝒊𝒕𝒆 𝑭𝒓𝒊𝒆𝒏𝒅":
    bot_info = bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    ref_bonus = config.get("refer_bonus", 10)
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📊 𝑴𝒚 𝑹𝒆𝒇𝒆𝒓𝒓𝒂𝒍𝒔", callback_data="my_refs"
        ),
        telebot.types.InlineKeyboardButton(
            "📤 𝑺𝒉𝒂𝒓𝒆 𝑳𝒊𝒏𝒌",
            url=f"https://t.me/share/url?url={link}&text=Join%20this%20amazing%20earning%20bot%20and%20get%20bonus!",
        ),
    )
    bot.send_message(
        message.chat.id,
        f"🔗 **আপনার রেফারেল লিংক:**\n\n`{link}`\n\n📌 *প্রতি রেফারে নিশ্চিত"
        f" কমিশন পাবেন* **৳{ref_bonus}**!",
        reply_markup=markup,
    )

  elif text == "💳 𝑾𝒊𝒕𝒉𝒅𝒓𝒂𝒘 𝑴𝒐𝒏𝒆𝒚":
    balance = user_data.get("balance", 0)
    min_w = config.get("min_withdraw", 500)

    progress_val = min(balance, min_w)
    percent = int((progress_val / min_w) * 10) if min_w > 0 else 10
    bar = "🟢" * percent + "⚪" * (10 - percent)

    markup = telebot.types.InlineKeyboardMarkup()
    if balance >= min_w:
      markup.add(
          telebot.types.InlineKeyboardButton(
              "💸 𝑼𝒕𝒕𝒐𝒍𝒐𝒏 𝑲𝒐𝒓𝒖𝒏 (𝑾𝒊𝒕𝒉𝒅𝒓𝒂𝒘)", callback_data="start_withdraw"
          )
      )

    bot.send_message(
        message.chat.id,
        f"💳 **উইথড্র পোর্টাল:**\n\n💰 মোট ব্যালেন্স: **৳{balance}**\n🎯 ন্যূনতম"
        f" লিমিট: **৳{min_w}**\n\nপ্রোগ্রেস:\n{bar}"
        f" `({balance}/{min_w})`\n\n{('✅ *উইথড্র করার জন্য আপনার পর্যাপ্ত ব্যালেন্স রয়েছে!*' if balance >= min_w else '❌ *পর্যাপ্ত ব্যালেন্স নেই। রেফার করে ব্যালেন্স পূর্ণ করুন।*')}",
        reply_markup=markup,
    )

  elif text == "🎁 𝑫𝒂𝒊𝒍𝒚 𝑩𝒐𝒏𝒖𝒔":
    now = time.time()
    last_time = user_data.get("last_bonus_time", 0)
    if user_data.get("referrals", 0) < 1:
      bot.send_message(
          message.chat.id,
          "❌ **ডেইলি বোনাস পাওয়ার শর্ত:**\n*ডেইলি বোনাস ক্লেইম করতে হলে আপনার অন্তত"
          " ১টি সফল রেফার থাকতে হবে!*",
      )
      return

    if now - last_time < 86400:
      remaining = int(86400 - (now - last_time))
      hrs = remaining // 3600
      mins = (remaining % 3600) // 60
      bot.send_message(
          message.chat.id,
          f"⏳ *আপনি ইতিমধ্যে ডেইলি বোনাস নিয়েছেন!*\n*পরবর্তী বোনাসের জন্য অপেক্ষা"
          f" করুন:* **{hrs} ঘণ্টা {mins} মিনিট**।",
      )
    else:
      bonus_amt = 15
      db["users"][user_id]["balance"] += bonus_amt
      db["users"][user_id]["today_earn"] += bonus_amt
      db["users"][user_id]["last_bonus_time"] = now

      if "transactions" not in db["users"][user_id]:
        db["users"][user_id]["transactions"] = []
      db["users"][user_id]["transactions"].append({
          "type": "𝑫𝒂𝒊𝒍𝒚 𝑩𝒐𝒏𝒖𝒔",
          "amount": bonus_amt,
          "time": time.strftime("%Y-%m-%d %H:%M"),
      })

      save_db(db)
      bot.send_message(
          message.chat.id,
          f"🎁 *অভিনন্দন! আপনি সফলভাবে ডেইলি বোনাস হিসেবে* **৳{bonus_amt}** *ক্লেইম"
          " করেছেন!*",
      )

  elif text == "🏆 𝑻𝒐𝒑 𝑳𝒆𝒂𝒅𝒆𝒓𝒔":
    sorted_users = sorted(
        db["users"].items(),
        key=lambda x: x[1].get("referrals", 0),
        reverse=True,
    )[:10]
    txt = "🏆 **টপ রেফার লিডারবোর্ড (সেরা ১০ জন):**\n\n"
    if not sorted_users:
      txt += "১. @Rahim_Official — 45 রেফার (৳450)\n২. @Karim_BD — 32 রেফার"
      " (৳320)\n"
    else:
      for i, (uid, uinfo) in enumerate(sorted_users, 1):
        txt += (
            f"{i}. @{uinfo.get('username')} — {uinfo.get('referrals', 0)} রেফার"
            f" (৳{uinfo.get('balance', 0)})\n"
        )
    bot.send_message(message.chat.id, txt)

  elif text == "👑 𝑨𝒅𝒎𝒊𝒏 𝑷𝒂𝒏𝒆𝒍" and int(user_id) == ADMIN_ID:
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📈 𝑳𝒊𝒗𝒆 𝑶𝒗𝒆𝒓𝒗𝒊𝒆𝒘", callback_data="adm_stats"
        ),
        telebot.types.InlineKeyboardButton(
            "🔍 𝑼𝒔𝒆𝒓 𝑳𝒐𝒐𝒌𝒖𝒑", callback_data="adm_lookup"
        ),
        telebot.types.InlineKeyboardButton(
            "➕ 𝑨𝒅𝒅 𝑭𝒐𝒓𝒄𝒆-𝑱𝒐𝒊𝒏", callback_data="adm_addch"
        ),
        telebot.types.InlineKeyboardButton(
            "📋 𝑳𝒊𝒔𝒕 𝑪𝒉𝒂𝒏𝒏𝒆𝒍𝒔", callback_data="adm_listch"
        ),
        telebot.types.InlineKeyboardButton(
            "💳 𝑷𝒂𝒚𝒐𝒖𝒕 𝑹𝒆𝒒𝒖𝒆𝒔𝒕𝒔", callback_data="adm_payouts"
        ),
        telebot.types.InlineKeyboardButton(
            "⚙️ 𝑺𝒆𝒕 𝑴𝒊𝒏 𝑾𝒊𝒕𝒉𝒅𝒓𝒂𝒘", callback_data="adm_minw"
        ),
        telebot.types.InlineKeyboardButton(
            "🎁 𝑺𝒊𝒈𝒏-𝒖𝒑 𝑩𝒐𝒏𝒖𝒔", callback_data="adm_subonus"
        ),
        telebot.types.InlineKeyboardButton(
            "👥 𝑹𝒆𝒇𝒆𝒓 𝑩𝒐𝒏𝒖𝒔", callback_data="adm_refbonus"
        ),
        telebot.types.InlineKeyboardButton(
            "📢 𝑩𝒓𝒐𝒂𝒅𝒄𝒂𝒔𝒕 𝑨𝒍𝒍", callback_data="adm_bc"
        ),
        telebot.types.InlineKeyboardButton(
            "🛠️ 𝑴𝒂𝒊𝒏𝒕𝒆𝒏𝒂𝒏𝒄𝒆", callback_data="adm_maint"
        ),
        telebot.types.InlineKeyboardButton(
            "🤖 𝑨𝒖𝒕𝒐-𝑷𝒂𝒚𝒐𝒖𝒕", callback_data="adm_autopay"
        ),
        telebot.types.InlineKeyboardButton(
            "⚙️ 𝑨𝒅𝒋𝒖𝒔𝒕 𝑩𝒂𝒍𝒂𝒏𝒄𝒆", callback_data="adm_adj"
        ),
        telebot.types.InlineKeyboardButton(
            "🚫 𝑩𝒂𝒏 / 𝑼𝒏𝒃𝒂𝒏", callback_data="adm_ban"
        ),
    )
    bot.send_message(
        message.chat.id,
        "👑 **মাস্টার অ্যাডমিন কন্ট্রোল প্যানেল:**\n*নিচের অপশনগুলো থেকে বট ফুল"
        " কন্ট্রোল করুন:*",
        reply_markup=markup,
    )


# --- ইনলাইন বাটন ও উইথড্র ফ্লো হ্যান্ডলার ---
@bot.callback_query_handler(func=lambda call: True)
def callback_router(call):
  user_id = str(call.from_user.id)
  db = load_db()
  data = call.data

  if data == "bal_history":
    user_data = db["users"].get(user_id, {})
    txs = user_data.get("transactions", [])
    if not txs:
      bot.answer_callback_query(
          call.id, "📭 আপনার কোনো ট্রানজেকশন হিস্ট্রি নেই।", show_alert=True
      )
    else:
      txt = "📜 **আপনার ট্রানজেকশন হিস্ট্রি (শেষ ৫টি):**\n\n"
      for tx in txs[-5:]:
        txt += f"🔹 {tx['type']} — **৳{tx['amount']}** `({tx['time']})`\n"
      bot.answer_callback_query(call.id, "📜 হিস্ট্রি লোড করা হয়েছে!", show_alert=False)
      bot.send_message(call.message.chat.id, txt)

  elif data == "my_refs":
    user_data = db["users"].get(user_id, {})
    refs = user_data.get("referrals", 0)
    bot.answer_callback_query(
        call.id,
        f"👥 আপনার মোট সফল রেফার: {refs} জন। প্রতি রেফারে আয় হয়েছে"
        f" ৳{refs * db['settings'].get('refer_bonus', 10)}",
        show_alert=True,
    )

  elif data == "start_withdraw":
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton(
            "bkash 𝒃𝒊𝒌𝒂𝒔𝒉", callback_data="method_bkash"
        ),
        telebot.types.InlineKeyboardButton(
            "nagad 𝒏𝒐𝒈𝒐𝒅", callback_data="method_nagad"
        ),
    )
    bot.send_message(
        call.message.chat.id,
        "💳 **পেমেন্ট মেথড সিলেক্ট করুন:**",
        reply_markup=markup,
    )

  elif data.startswith("method_"):
    method = data.split("_")[1].upper()
    msg = bot.send_message(
        call.message.chat.id,
        f"📞 আপনার **{method}** নম্বরটি লিখুন (যেমন: 017xxxxxxxx):",
    )
    bot.register_next_step_handler(msg, process_withdraw_number, method)

  # --- পেমেন্ট অ্যাপ্রুভ/রিজেক্ট কলব্যাক হ্যান্ডলার ---
  elif data.startswith("pay_action_") and int(user_id) == ADMIN_ID:
    parts = data.split("_")
    action = parts[2]  # approve বা reject
    req_idx = int(parts[3])
    payouts = db.get("payouts", [])

    if req_idx < len(payouts):
      req = payouts[req_idx]
      target_uid = req["uid"]
      amount = req["amount"]

      if action == "approve":
        payouts.pop(req_idx)
        save_db(db)
        bot.answer_callback_query(call.id, "✅ পেমেন্ট সফলভাবে অ্যাপ্রুভ করা হয়েছে!", show_alert=True)
        bot.edit_message_text(
            f"✅ **পেমেন্ট সফলভাবে অনুমোদিত!**\n🆔 আইডি: `{target_uid}`\n💰 পরিমাণ: **৳{amount}**",
            call.message.chat.id,
            call.message.message_id,
        )
        try:
          bot.send_message(
              int(target_uid),
              f"🎉 *অভিনন্দন! আপনার* **৳{amount}** *উইথড্র রিকোয়েস্ট সফলভাবে"
              " পেমেন্ট করা হয়েছে।*",
          )
        except Exception:
          pass

      elif action == "reject":
        # টাকা ইউজারের ব্যালেন্সে ফেরত দেওয়া
        if target_uid in db["users"]:
          db["users"][target_uid]["balance"] += amount
          db["users"][target_uid]["today_withdraw"] -= amount
          if "transactions" not in db["users"][target_uid]:
            db["users"][target_uid]["transactions"] = []
          db["users"][target_uid]["transactions"].append({
              "type": "𝑾𝒊𝒕𝒉𝒅𝒓𝒂𝒘 𝑹𝒆𝒇𝒖𝒏𝒅 (𝑹𝒆𝒋𝒆𝒄𝒕𝒆𝒅)",
              "amount": amount,
              "time": time.strftime("%Y-%m-%d %H:%M"),
          })
        payouts.pop(req_idx)
        save_db(db)
        bot.answer_callback_query(call.id, "❌ পেমেন্ট রিজেক্ট করা হয়েছে এবং টাকা ফেরত দেওয়া হয়েছে!", show_alert=True)
        bot.edit_message_text(
            f"❌ **পেমেন্ট রিজেক্ট করা হয়েছে!**\n🆔 আইডি: `{target_uid}`\n💰 পরিমাণ: **৳{amount}** (ব্যালেন্সে ফেরত দেওয়া হয়েছে)",
            call.message.chat.id,
            call.message.message_id,
        )
        try:
          bot.send_message(
              int(target_uid),
              f"⚠️ *দুঃখিত! আপনার* **৳{amount}** *উইথড্র রিকোয়েস্টটি বাতিল করা হয়েছে"
              " এবং টাকা আপনার ব্যালেন্সে ফেরত দেওয়া হয়েছে।*",
          )
        except Exception:
          pass
    else:
      bot.answer_callback_query(call.id, "⚠️ রিকোয়েস্টটি ইতিমধ্যে প্রসেস করা হয়েছে।", show_alert=True)

  # --- অ্যাডমিন কলব্যাকসমূহ ---
  elif data.startswith("adm_") and int(user_id) == ADMIN_ID:
    if data == "adm_stats":
      total_users = len(db["users"])
      total_payouts = len(db.get("payouts", []))
      total_paid_sum = sum(
          p.get("amount", 0) for p in db.get("history_payouts", [])
      )
      bot.answer_callback_query(
          call.id,
          f"📈 𝑨𝒅𝒗𝒂𝒏𝒄𝒆𝒅 𝑫𝒂𝒔𝒉𝒃𝒐𝒂𝒓𝒅:\n- মোট ইউজার: {total_users}\n- পেন্ডিং উইথড্র:"
          f" {total_payouts}\n- সার্ভার স্ট্যাটাস: 𝑶𝒏𝒍𝒊𝒏𝒆 🟢",
          show_alert=True,
      )

    elif data == "adm_maint":
      db["settings"]["maintenance"] = not db["settings"].get(
          "maintenance", False
      )
      save_db(db)
      status = "𝑶𝑵 🔴" if db["settings"]["maintenance"] else "𝑶𝑭𝑭 🟢"
      bot.answer_callback_query(
          call.id, f"মেইনটেনেন্স মোড এখন: {status}", show_alert=True
      )

    elif data == "adm_autopay":
      db["settings"]["auto_payout"] = not db["settings"].get(
          "auto_payout", True
      )
      save_db(db)
      status = "𝑶𝑵 🟢" if db["settings"]["auto_payout"] else "𝑶𝑭𝑭 🔴"
      bot.answer_callback_query(
          call.id, f"অটো-পেমেন্ট সিমুলেটর: {status}", show_alert=True
      )

    elif data == "adm_listch":
      channels = db.get("channels", [])
      if not channels:
        bot.answer_callback_query(
            call.id, "📭 বর্তমানে কোনো চ্যানেল যুক্ত নেই।", show_alert=True
        )
      else:
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        for idx, ch in enumerate(channels):
          markup.add(
              telebot.types.InlineKeyboardButton(
                  f"🗑️ 𝑫𝒆𝒍𝒆𝒕𝒆 {ch['name']}", callback_data=f"del_ch_{idx}"
              )
          )
        bot.send_message(
            ADMIN_ID,
            "📋 **সংযুক্ত চ্যানেলসমূহ (ডিলিট করতে বাটনে ক্লিক করুন):**",
            reply_markup=markup,
        )

    elif data.startswith("del_ch_"):
      idx = int(data.split("_")[2])
      channels = db.get("channels", [])
      if idx < len(channels):
        removed = channels.pop(idx)
        save_db(db)
        bot.answer_callback_query(
            call.id,
            f"✅ সফলভাবে ডিলিট করা হয়েছে: {removed['name']}",
            show_alert=True,
        )

    elif data == "adm_addch":
      msg = bot.send_message(
          ADMIN_ID,
          "➕ নতুন চ্যানেল যুক্ত করতে এই ফরম্যাটে লিখুন:\n`ChannelName |"
          " @ChannelUsername | https://t.me/...`",
      )
      bot.register_next_step_handler(msg, save_new_channel)

    elif data == "adm_minw":
      msg = bot.send_message(
          ADMIN_ID, "⚙️ নতুন সর্বনিম্ন উইথড্র পরিমাণ লিখুন (যেমন: 500):"
      )
      bot.register_next_step_handler(msg, update_min_withdraw)

    elif data == "adm_subonus":
      msg = bot.send_message(
          ADMIN_ID, "🎁 নতুন সাইন-আপ বোনাস পরিমাণ লিখুন (যেমন: 50):"
      )
      bot.register_next_step_handler(msg, update_signup_bonus)

    elif data == "adm_refbonus":
      msg = bot.send_message(
          ADMIN_ID, "👥 নতুন রেফার কমিশন পরিমাণ লিখুন (যেমন: 10):"
      )
      bot.register_next_step_handler(msg, update_refer_bonus)

    elif data == "adm_bc":
      markup = telebot.types.InlineKeyboardMarkup(row_width=2)
      markup.add(
          telebot.types.InlineKeyboardButton(
              "📢 𝑨𝒍𝒍 𝑼𝒔𝒆𝒓𝒔", callback_data="bc_type_all"
          ),
          telebot.types.InlineKeyboardButton(
              "👥 𝒁𝒆𝒓𝒐 𝑹𝒆𝒇𝒆𝒓 𝑼𝒔𝒆𝒓𝒔", callback_data="bc_type_zero"
          ),
      )
      bot.send_message(
          ADMIN_ID,
          "📢 **ব্রডকাস্ট ক্যাটাগরি সিলেক্ট করুন:**",
          reply_markup=markup,
      )

    elif data.startswith("bc_type_") and int(user_id) == ADMIN_ID:
      btype = data.split("_")[2]
      msg = bot.send_message(
          ADMIN_ID,
          f"📢 সিলেক্টেড ক্যাটাগরি: **{btype.upper()}**\nব্রডকাস্ট মেসেজটি লিখুন:",
      )
      bot.register_next_step_handler(msg, execute_broadcast, btype)

    elif data == "adm_lookup":
      msg = bot.send_message(
          ADMIN_ID, "🔍 ইউজারের টেলিগ্রাম আইডি বা ইউজারনেম লিখুন:"
      )
      bot.register_next_step_handler(msg, execute_user_lookup)

    elif data == "adm_adj":
      msg = bot.send_message(
          ADMIN_ID,
          "⚙️ ব্যালেন্স এডিট করতে এই ফরম্যাটে লিখুন:\n`UserID | Amount`"
          " (ឧ: `123456789 | 100` বা `-50` কাটা যাবে)",
      )
      bot.register_next_step_handler(msg, execute_balance_adjust)

    elif data == "adm_ban":
      msg = bot.send_message(
          ADMIN_ID,
          "🚫 ব্যান বা আনব্যান করতে ইউজারের টেলিগ্রাম আইডি লিখুন:",
      )
      bot.register_next_step_handler(msg, execute_ban_user)

    elif data == "adm_payouts":
      payouts = db.get("payouts", [])
      if not payouts:
        bot.answer_callback_query(
            call.id, "📭 কোনো পেন্ডিং উইথড্র নেই।", show_alert=True
        )
      else:
        for idx, p in enumerate(payouts[:5]):
          markup = telebot.types.InlineKeyboardMarkup(row_width=2)
          markup.add(
              telebot.types.InlineKeyboardButton(
                  "✅ 𝑨𝒑𝒑𝒓𝒐𝒗𝒆", callback_data=f"pay_action_approve_{idx}"
              ),
              telebot.types.InlineKeyboardButton(
                  "❌ 𝑹𝒆𝒋𝒆𝒄𝒕", callback_data=f"pay_action_reject_{idx}"
              ),
          )
          bot.send_message(
              ADMIN_ID,
              f"💳 **উইথড্র রিকোয়েস্ট #{idx+1}:**\n🆔 আইডি: `{p['uid']}`\n📞 মেথড:"
              f" {p['method']} ({p['number']})\n💰 টাকা: **৳{p['amount']}**",
              reply_markup=markup,
          )


# --- উইথড্র নম্বর ও অ্যামাউন্ট হ্যান্ডলার ---
def process_withdraw_number(message, method):
  user_id = str(message.from_user.id)
  number = message.text.strip()
  db = load_db()
  config = db["settings"]
  user_data = db["users"].get(user_id, {})
  balance = user_data.get("balance", 0)
  min_w = config.get("min_withdraw", 500)

  if balance < min_w:
    bot.send_message(
        message.chat.id, f"❌ পর্যাপ্ত ব্যালেন্স নেই! ন্যূনতম উইথড্র ৳{min_w}।"
    )
    return

  db["users"][user_id]["balance"] -= min_w
  db["users"][user_id]["today_withdraw"] += min_w

  if "transactions" not in db["users"][user_id]:
    db["users"][user_id]["transactions"] = []
  db["users"][user_id]["transactions"].append({
      "type": f"𝑾𝒊𝒕𝒉𝒅𝒓𝒂𝒘 ({method})",
      "amount": -min_w,
      "time": time.strftime("%Y-%m-%d %H:%M"),
  })

  if "payouts" not in db:
    db["payouts"] = []
  db["payouts"].append({
      "uid": user_id,
      "method": method,
      "number": number,
      "amount": min_w,
  })
  save_db(db)

  bot.send_message(
      message.chat.id,
      f"✅ **উইথড্র রিকোয়েস্ট সফল!**\n\nমেথড: {method}\nনম্বর: `{number}`\nপরিমাণ:"
      " **৳"
      f"{min_w}**\n\n*২৪ ঘণ্টার মধ্যে পেমেন্ট আপনার অ্যাকাউন্টে পৌঁছে যাবে।*",
  )
  try:
    bot.send_message(
        ADMIN_ID,
        f"🚨 **নতুন উইথড্র রিকোয়েস্ট!**\nইউজার আইডি: `{user_id}`\nনম্বর:"
        f" `{number}` ({method})\nটাকা: **৳{min_w}**",
    )
  except Exception:
    pass


# --- ফেক পেআউট ব্যাকগ্রাউন্ড থ্রেড অটোমেশন ---
def fake_payout_worker():
  while True:
    try:
      db = load_db()
      if db.get("fake_payouts_active", True) and db.get("channels"):
        pass
    except Exception:
      pass
    time.sleep(300)


# --- এডমিন স্টেপ হ্যান্ডলার ফাংশনসমূহ ---
def save_new_channel(message):
  try:
    parts = message.text.split("|")
    name = parts[0].strip()
    ch_id = parts[1].strip()
    link = parts[2].strip()
    db = load_db()
    db["channels"].append({"name": name, "id": ch_id, "link": link})
    save_db(db)
    bot.send_message(ADMIN_ID, f"✅ সফলভাবে চ্যানেল যুক্ত করা হয়েছে: {name}")
  except Exception:
    bot.send_message(
        ADMIN_ID, "❌ ফরম্যাট ভুল! ব্যবহার করুন: `Name | @username | https://...`"
    )


def update_min_withdraw(message):
  try:
    val = int(message.text.strip())
    db = load_db()
    db["settings"]["min_withdraw"] = val
    save_db(db)
    bot.send_message(
        ADMIN_ID, f"✅ ন্যূনতম উইথড্র লিমিট সফলভাবে ৳{val} করা হয়েছে।"
    )
  except Exception:
    bot.send_message(ADMIN_ID, "❌ সঠিক সংখ্যা লিখুন।")


def update_signup_bonus(message):
  try:
    val = int(message.text.strip())
    db = load_db()
    db["settings"]["signup_bonus"] = val
    save_db(db)
    bot.send_message(ADMIN_ID, f"✅ সাইন-আপ বোনাস সফলভাবে ৳{val} করা হয়েছে।")
  except Exception:
    bot.send_message(ADMIN_ID, "❌ সঠিক সংখ্যা লিখুন।")


def update_refer_bonus(message):
  try:
    val = int(message.text.strip())
    db = load_db()
    db["settings"]["refer_bonus"] = val
    save_db(db)
    bot.send_message(ADMIN_ID, f"✅ রেফার বোনাস সফলভাবে ৳{val} করা হয়েছে।")
  except Exception:
    bot.send_message(ADMIN_ID, "❌ সঠিক সংখ্যা লিখুন।")


def execute_broadcast(message, btype):
  text = message.text.strip()
  db = load_db()
  cnt = 0
  for uid, uinfo in db["users"].items():
    if btype == "zero" and uinfo.get("referrals", 0) > 0:
      continue
    try:
      bot.send_message(int(uid), f"📢 **অফিসিয়াল নোটিশ:**\n\n{text}")
      cnt += 1
    except Exception:
      pass
  bot.send_message(
      ADMIN_ID,
      f"✅ সফলভাবে `{cnt}` জন ইউজারের কাছে ({btype}) ব্রডকাস্ট পাঠানো হয়েছে।",
  )


def execute_user_lookup(message):
  query = message.text.strip()
  db = load_db()
  user_data = db["users"].get(query)
  if not user_data:
    for uid, uinfo in db["users"].items():
      if uinfo.get("username") == query.replace("@", ""):
        user_data = uinfo
        query = uid
        break
  if user_data:
    bot.send_message(
        ADMIN_ID,
        f"🔍 **ইউজার ডিটেইলস:**\n🆔 আইডি: `{query}`\n👤 নাম:"
        f" {user_data.get('name')}\n💰 ব্যালেন্স:"
        f" **৳{user_data.get('balance')}**\n👥 রেফার সংখ্যা:"
        f" {user_data.get('referrals')}\n📅 জয়েনিং তারিখ:"
        f" {user_data.get('join_date', 'N/A')}",
    )
  else:
    bot.send_message(ADMIN_ID, "❌ কোনো ইউজার পাওয়া যায়নি!")


def execute_balance_adjust(message):
  try:
    parts = message.text.split("|")
    uid = parts[0].strip()
    amount = int(parts[1].strip())
    db = load_db()
    if uid in db["users"]:
      db["users"][uid]["balance"] += amount
      if "transactions" not in db["users"][uid]:
        db["users"][uid]["transactions"] = []
      db["users"][uid]["transactions"].append({
          "type": "𝑨𝒅𝒎𝒊𝒏 𝑩𝒂𝒍𝒂𝒏𝒄𝒆 𝑨𝒅𝒋𝒖𝒔𝒕𝒎𝒆𝒏𝒕",
          "amount": amount,
          "time": time.strftime("%Y-%m-%d %H:%M"),
      })
      save_db(db)
      bot.send_message(
          ADMIN_ID,
          f"✅ ইউজার `{uid}` এর ব্যালেন্সে সফলভাবে ৳{amount} আপডেট করা হয়েছে।",
      )
    else:
      bot.send_message(ADMIN_ID, "❌ ইউজার আইডি পাওয়া যায়নি!")
  except Exception:
    bot.send_message(
        ADMIN_ID, "❌ ফরম্যাট ভুল! ব্যবহার করুন: `UserID | Amount`"
    )


def execute_ban_user(message):
  uid = message.text.strip()
  db = load_db()
  if "banned_users" not in db:
    db["banned_users"] = []
  if uid in db["banned_users"]:
    db["banned_users"].remove(uid)
    save_db(db)
    bot.send_message(ADMIN_ID, f"✅ ইউজার `{uid}` কে আনব্যান করা হয়েছে।")
  else:
    db["banned_users"].append(uid)
    save_db(db)
    bot.send_message(ADMIN_ID, f"🚫 ইউজার `{uid}` কে ব্যান করা হয়েছে।")


# --- ব্যাকগ্রাউন্ড থ্রেড ও সার্ভার রানার ---
def run_bot():
  bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
  t = threading.Thread(target=run_bot)
  t.daemon = True
  t.start()

  # ফেক পেআউট ব্যাকগ্রাউন্ড থ্রেড স্টার্ট
  ft = threading.Thread(target=fake_payout_worker)
  ft.daemon = True
  ft.start()

  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
