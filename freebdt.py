import json
import os
import threading
import time
import telebot
from flask import Flask

# --- কনফিগারেশন ---
TOKEN = "9059189356:AAFgK65y6dCivPJo_bYnZtmxANT8zgfjgDs"  # আপনার টেলিগ্রাম বটের টোকেন এখানে দিন
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
                "📢 **স্বাগতম আমাদের অফিশিয়াল আর্নিং প্ল্যাটফর্মে!**"
            ),
        },
        "channels": [],  # [{"id": "@channel", "name": "Channel Name"}]
        "payouts": [],
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
            "pinned_notice": "📢 **স্বাগতম!**",
        },
        "channels": [],
        "payouts": [],
        "fake_payouts_active": True,
    }


def save_db(data):
  with open(DB_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)


bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")
app = Flask(__name__)


@app.route("/")
def home():
  return "Telegram Secure Earning Bot is running live!"


# --- মেইন মেনু কিবোর্ড (আপনার নির্দিষ্ট লেআউট অনুযায়ী) ---
def get_main_keyboard(user_id):
  markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  # ১ম লাইন: My Balance, Invite Friend
  markup.add(
      telebot.types.KeyboardButton("💰 My Balance"),
      telebot.types.KeyboardButton("👥 Invite Friend"),
  )
  # ২য় লাইন: Withdraw Money
  markup.add(telebot.types.KeyboardButton("💳 Withdraw Money"))
  # ৩য় লাইন: Daily Bonus, Top Leaders
  markup.add(
      telebot.types.KeyboardButton("🎁 Daily Bonus"),
      telebot.types.KeyboardButton("🏆 Top Leaders"),
  )
  # সবার নিচে এডমিন প্যানেল (যদি এডমিন হন)
  if user_id == ADMIN_ID:
    markup.add(telebot.types.KeyboardButton("👑 Admin Panel"))
  return markup


# --- ফোর্স জয়েন চেক ফাংশন (হাই সিকিউরিটি) ---
def check_forced_join(user_id):
  db = load_db()
  channels = db.get("channels", [])
  if not channels:
    return True, []  # কোনো চ্যানেল সেট করা না থাকলে পাস

  not_joined = []
  for ch in channels:
    ch_id = ch["id"]
    try:
      member = bot.get_chat_member(ch_id, user_id)
      if member.status not in ["creator", "administrator", "member"]:
        not_joined.append(ch)
    except Exception:
      # বট চ্যানেলে অ্যাডমিন না থাকলে বা অন্য এরর হলে বাইপাস বা নট জয়েন্ড ধরতে পারে
      not_joined.append(ch)

  return len(not_joined) == 0, not_joined


# --- /start কমান্ড ও সিকিউরিটি লেয়ার ---
@bot.message_handler(commands=["start"])
def cmd_start(message):
  user_id = str(message.from_user.id)
  username = message.from_user.username or "No_Username"
  name = message.from_user.first_name

  db = load_db()
  config = db["settings"]

  # মেইনটেনেন্স চেক
  if config.get("maintenance") and int(user_id) != ADMIN_ID:
    bot.send_message(
        message.chat.id,
        "🛠️ **সিস্টেম আপডেট চলছে!**\n\nবট সাময়িকভাবে বন্ধ রয়েছে। দয়া করে কিছু"
        " সময় পর চেষ্টা করুন।",
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
              f"📢 Join {ch['name']}", url=ch["link"]
          )
      )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "🔄 Check Membership", callback_data="check_join"
        )
    )
    bot.send_message(
        message.chat.id,
        "🚨 **সিকিউরিটি অ্যালার্ট!**\n\nবট ব্যবহার করার জন্য নিচের চ্যানেলগুলোতে"
        " অবশ্যই জয়েন করতে হবে। জয়েন করার পর নিচে **Check Membership**"
        " বাটনে ক্লিক করুন।",
        reply_markup=markup,
    )
    return

  # রেফারেল পার্সিং
  args = message.text.split()
  referrer_id = None
  if len(args) > 1 and args[1].startswith("ref_"):
    referrer_id = args[1].replace("ref_", "")

  # নতুন ইউজার রেজিস্ট্রেশন
  if user_id not in db["users"]:
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
    }

    # রেফার বোনাস ও কাউন্ট
    if referrer_id and referrer_id != user_id and referrer_id in db["users"]:
      ref_bonus = config.get("refer_bonus", 10)
      db["users"][referrer_id]["balance"] += ref_bonus
      db["users"][referrer_id]["today_earn"] += ref_bonus
      db["users"][referrer_id]["referrals"] += 1
      try:
        bot.send_message(
            int(referrer_id),
            f"🔥 **নতুন রেফার যুক্ত হয়েছে!**\nআপনার অ্যাকাউন্টে বোনাস হিসেবে"
            f" **৳{ref_bonus}** যোগ করা হয়েছে।",
        )
      except Exception:
        pass

    save_db(db)
    # সাইন-আপ বোনাসের সুন্দর পপআপ নোটিফিকেশন
    bot.send_message(
        message.chat.id,
        f"🎉 **অভিনন্দন {name}!**\n\nসফলভাবে সিকিউরিটি চেক পার করার জন্য আপনি"
        f" সাইন-আপ বোনাস **৳{signup_bonus}** ফ্রি পেয়েছেন! 🎁",
    )

  # পিন্ড নোটিশসহ মেইন মেনু ওপেন
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
    bot.delete_message(call.message.chat.id, call.message.message_id)
    cmd_start(call.message)
  else:
    bot.answer_callback_query(
        call.id,
        "❌ আপনি এখনো সব চ্যানেলে জয়েন করেননি! দয়া করে জয়েন করুন।",
        show_alert=True,
    )


# --- ইউজার মেনু অপশন হ্যান্ডলার ---
@bot.message_handler(
    func=lambda message: message.text
    in [
        "💰 My Balance",
        "👥 Invite Friend",
        "💳 Withdraw Money",
        "🎁 Daily Bonus",
        "🏆 Top Leaders",
        "👑 Admin Panel",
    ]
)
def handle_user_actions(message):
  user_id = str(message.from_user.id)
  text = message.text
  db = load_db()
  config = db["settings"]

  # অ্যান্টি-আনজয়েন লাইভ সিকিউরিটি অডিট
  is_joined, _ = check_forced_join(int(user_id))
  if not is_joined and int(user_id) != ADMIN_ID:
    bot.send_message(
        message.chat.id,
        "🚨 **সিকিউরিটি অ্যালার্ট!**\nআপনি আমাদের অফিশিয়াল চ্যানেল থেকে লিভ"
        " নিয়েছেন। পুনরায় চ্যানেলে জয়েন করে `/start` কমান্ড দিন।",
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
      },
  )

  if text == "💰 My Balance":
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📜 Balance History", callback_data="bal_history"
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

  elif text == "👥 Invite Friend":
    bot_info = bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    ref_bonus = config.get("refer_bonus", 10)
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📊 My Referrals", callback_data="my_refs"
        ),
        telebot.types.InlineKeyboardButton(
            "📤 Share Link",
            url=f"https://t.me/share/url?url={link}&text=Join%20this%20amazing%20earning%20bot%20and%20get%20bonus!",
        ),
    )
    bot.send_message(
        message.chat.id,
        f"🔗 **আপনার রেফারেল লিংক:**\n\n`{link}`\n\n📌 প্রতি রেফারে নিশ্চিত"
        f" কমিশন পাবেন **৳{ref_bonus}**!",
        reply_markup=markup,
    )

  elif text == "💳 Withdraw Money":
    balance = user_data.get("balance", 0)
    min_w = config.get("min_withdraw", 500)

    # প্রোগ্রেস বার তৈরি
    progress_val = min(balance, min_w)
    percent = int((progress_val / min_w) * 10)
    bar = "🟢" * percent + "⚪" * (10 - percent)

    markup = telebot.types.InlineKeyboardMarkup()
    if balance >= min_w:
      markup.add(
          telebot.types.InlineKeyboardButton(
              "💸 উত্তোলন করুন (Withdraw)", callback_data="start_withdraw"
          )
      )

    bot.send_message(
        message.chat.id,
        f"💳 **উইথড্র পোর্টাল:**\n\n💰 মোট ব্যালেন্স: **৳{balance}**\n🎯 ন্যূনতম"
        f" লিমিট: **৳{min_w}**\n\nপ্রোগ্রেস:\n{bar}"
        f" `({balance}/{min_w})`\n\n{('✅ উইথড্র করার জন্য আপনার পর্যাপ্ত ব্যালেন্স রয়েছে!' if balance >= min_w else '❌ পর্যাপ্ত ব্যালেন্স নেই। রেফার করে ব্যালেন্স পূর্ণ করুন।')}",
        reply_markup=markup,
    )

  elif text == "🎁 Daily Bonus":
    import time

    now = time.time()
    last_time = user_data.get("last_bonus_time", 0)
    # শর্ত: ২৪ ঘণ্টায় ১ বার এবং অন্তত ১টি রেফার থাকতে হবে
    if user_data.get("referrals", 0) < 1:
      bot.send_message(
          message.chat.id,
          "❌ **ডেইলি বোনাস পাওয়ার শর্ত:**\nডেইলি বোনাস ক্লেইম করতে হলে আপনার অন্তত"
          " **১টি সফল রেফার** থাকতে হবে!",
      )
      return

    if now - last_time < 86400:
      remaining = int(86400 - (now - last_time))
      hrs = remaining // 3600
      mins = (remaining % 3600) // 60
      bot.send_message(
          message.chat.id,
          f"⏳ আপনি ইতিমধ্যে ডেইলি বোনাস নিয়েছেন!\nপরবর্তী বোনাসের জন্য অপেক্ষা"
          f" করুন: **{hrs} ঘণ্টা {mins} মিনিট**।",
      )
    else:
      bonus_amt = 15
      db["users"][user_id]["balance"] += bonus_amt
      db["users"][user_id]["today_earn"] += bonus_amt
      db["users"][user_id]["last_bonus_time"] = now
      save_db(db)
      bot.send_message(
          message.chat.id,
          f"🎁 অভিনন্দন! আপনি সফলভাবে ডেইলি বোনাস হিসেবে **৳{bonus_amt}** ক্লেইম"
          " করেছেন!",
      )

  elif text == "🏆 Top Leaders":
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

  elif text == "👑 Admin Panel" and int(user_id) == ADMIN_ID:
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📈 Live Overview", callback_data="adm_stats"
        ),
        telebot.types.InlineKeyboardButton(
            "🔍 User Lookup", callback_data="adm_lookup"
        ),
        telebot.types.InlineKeyboardButton(
            "➕ Add Force-Join", callback_data="adm_addch"
        ),
        telebot.types.InlineKeyboardButton(
            "📋 List Channels", callback_data="adm_listch"
        ),
        telebot.types.InlineKeyboardButton(
            "💳 Payout Requests", callback_data="adm_payouts"
        ),
        telebot.types.InlineKeyboardButton(
            "⚙️ Set Min Withdraw", callback_data="adm_minw"
        ),
        telebot.types.InlineKeyboardButton(
            "🎁 Sign-up Bonus", callback_data="adm_subonus"
        ),
        telebot.types.InlineKeyboardButton(
            "👥 Refer Bonus", callback_data="adm_refbonus"
        ),
        telebot.types.InlineKeyboardButton(
            "📢 Broadcast All", callback_data="adm_bc"
        ),
        telebot.types.InlineKeyboardButton(
            "🛠️ Maintenance", callback_data="adm_maint"
        ),
        telebot.types.InlineKeyboardButton(
            "🤖 Auto-Payout", callback_data="adm_autopay"
        ),
        telebot.types.InlineKeyboardButton(
            "⚙️ Adjust Balance", callback_data="adm_adj"
        ),
    )
    bot.send_message(
        message.chat.id,
        "👑 **মাস্টার অ্যাডমিন কন্ট্রোল প্যানেল:**\nনিচের অপশনগুলো থেকে বট ফুল"
        " কন্ট্রোল করুন:",
        reply_markup=markup,
    )


# --- ইনলাইন বাটন ও উইথড্র ফ্লো হ্যান্ডলার ---
@bot.callback_query_handler(func=lambda call: True)
def callback_router(call):
  user_id = str(call.from_user.id)
  db = load_db()
  data = call.data

  if data == "bal_history":
    bot.answer_callback_query(
        call.id,
        "📜 হিস্ট্রি: সাইন-আপ বোনাস এবং রেফার কমিশন সফলভাবে যোগ হয়েছে।",
        show_alert=True,
    )

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
            "bkash বিকাশ", callback_data="method_bkash"
        ),
        telebot.types.InlineKeyboardButton(
            "nagad নগদ", callback_data="method_nagad"
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

  # --- অ্যাডমিন কলব্যাকসমূহ ---
  elif data.startswith("adm_") and int(user_id) == ADMIN_ID:
    if data == "adm_stats":
      total_users = len(db["users"])
      total_payouts = len(db.get("payouts", []))
      bot.answer_callback_query(
          call.id,
          f"📈 Live Overview:\n- মোট ইউজার: {total_users}\n- মোট উইথড্র"
          f" রিকোয়েস্ট: {total_payouts}\n- সার্ভার স্ট্যাটাস: Online 🟢",
          show_alert=True,
      )

    elif data == "adm_maint":
      db["settings"]["maintenance"] = not db["settings"].get(
          "maintenance", False
      )
      save_db(db)
      status = "ON 🔴" if db["settings"]["maintenance"] else "OFF 🟢"
      bot.answer_callback_query(
          call.id, f"মেইনটেনেন্স মোড এখন: {status}", show_alert=True
      )

    elif data == "adm_autopay":
      db["settings"]["auto_payout"] = not db["settings"].get(
          "auto_payout", True
      )
      save_db(db)
      status = "ON 🟢" if db["settings"]["auto_payout"] else "OFF 🔴"
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
        txt = "📋 **সংযুক্ত চ্যানেলসমূহ:**\n\n"
        for idx, ch in enumerate(channels, 1):
          txt += f"{idx}. {ch['name']} (`{ch['id']}`)\n"
        bot.send_message(ADMIN_ID, txt)

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
      msg = bot.send_message(
          ADMIN_ID, "📢 সব ইউজারের কাছে পাঠানোর জন্য ব্রডকাস্ট মেসেজটি লিখুন:"
      )
      bot.register_next_step_handler(msg, execute_broadcast)

    elif data == "adm_lookup":
      msg = bot.send_message(
          ADMIN_ID, "🔍 ইউজারের টেলিগ্রাম আইডি বা ইউজারনেম লিখুন:"
      )
      bot.register_next_step_handler(msg, execute_user_lookup)

    elif data == "adm_payouts":
      payouts = db.get("payouts", [])
      if not payouts:
        bot.answer_callback_query(
            call.id, "📭 কোনো পেন্ডিং উইথড্র নেই।", show_alert=True
        )
      else:
        for p in payouts[:5]:
          bot.send_message(
              ADMIN_ID,
              f"💳 **উইথড্র রিকোয়েস্ট:**\n🆔 আইডি: `{p['uid']}`\n📞 মেথড:"
              f" {p['method']} ({p['number']})\n💰 টাকা: **৳{p['amount']}**",
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

  # ব্যালেন্স কেটে নেওয়া এবং রিকোয়েস্ট সেভ করা
  db["users"][user_id]["balance"] -= min_w
  db["users"][user_id]["today_withdraw"] += min_w
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
      f"{min_w}**\n\n২৪ ঘণ্টার মধ্যে পেমেন্ট আপনার অ্যাকাউন্টে পৌঁছে যাবে।",
  )
  try:
    bot.send_message(
        ADMIN_ID,
        f"🚨 **নতুন উইথড্র রিকোয়েস্ট!**\nইউজার আইডি: `{user_id}`\nনম্বর:"
        f" `{number}` ({method})\nটাকা: **৳{min_w}**",
    )
  except Exception:
    pass


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


def execute_broadcast(message):
  text = message.text.strip()
  db = load_db()
  cnt = 0
  for uid in db["users"]:
    try:
      bot.send_message(int(uid), f"📢 **অফিসিয়াল নোটিশ:**\n\n{text}")
      cnt += 1
    except Exception:
      pass
  bot.send_message(
      ADMIN_ID, f"✅ সফলভাবে `{cnt}` জন ইউজারের কাছে ব্রডকাস্ট পাঠানো হয়েছে।"
  )


def execute_user_lookup(message):
  query = message.text.strip()
  db = load_db()
  user_data = db["users"].get(query)
  if not user_data:
    # ইউজারনেম দিয়ে খোঁজার চেষ্টা
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


# --- ব্যাকগ্রাউন্ড থ্রেড ও সার্ভার রানার ---
def run_bot():
  bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
  t = threading.Thread(target=run_bot)
  t.daemon = True
  t.start()

  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
