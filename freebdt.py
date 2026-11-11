import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from pymongo import MongoClient

# --- কনফিগারেশন (আপনার তথ্যগুলো এখানে বসাবেন) ---
TOKEN = "9059189356:AAGJ5YGLVw_cvvK8OQlkyX6hDYHtZBpMGPA"
ADMIN_ID = 7833766898  # আপনার টেলিগ্রাম আইডি
MONGO_URI = "YOUR_MONGODB_ATLAS_CONNECTION_STRING_HERE"

# --- ডাটাবেজ কানেকশন ---
client = MongoClient(MONGO_URI)
db = client["free_income_bdt"]
users_col = db["users"]
settings_col = db["settings"]
channels_col = db["channels"]
tasks_col = db["tasks"]

# ডিফল্ট সেটিংস ইনিশিয়ালাইজ
if not settings_col.find_one({"_id": "config"}):
  settings_col.insert_one({
      "_id": "config",
      "signup_bonus": 50,
      "refer_bonus": 10,
      "min_withdraw": 500,
      "maintenance": False,
      "auto_payout": True,
  })

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)


# --- স্টেট মেশিন (FSM) ---
class AdminStates(StatesGroup):
  waiting_for_broadcast = State()
  waiting_for_channel = State()
  waiting_for_bonus = State()
  waiting_for_min_withdraw = State()
  waiting_for_user_adjust = State()


# --- হেল্পার ফাংশনস ---
def get_config():
  return settings_col.find_one({"_id": "config"})


async def check_user_channels(user_id: int) -> bool:
  """বাধ্যতামূলক চ্যানেল জয়েন চেক এবং আন-জয়েন ডিটেক্টর"""
  channels = list(channels_col.find())
  if not channels:
    return True
  for ch in channels:
    try:
      member = await bot.get_chat_member(
          chat_id=ch["chat_id"], user_id=user_id
      )
      if member.status in ["left", "kicked"]:
        return False
    except Exception:
      continue
  return True


# মেইন মেনু রিপ্লাই কিবোর্ড
def get_main_keyboard(user_id: int):
  kb = [
      [
          KeyboardButton(text="💰 আমার ব্যালেন্স"),
          KeyboardButton(text="👥 ইনভাইট ও রেফার"),
      ],
      [
          KeyboardButton(text="🎁 ডেইলি বোনাস"),
          KeyboardButton(text="💳 টাকা তুলুন (bKash/Nagad)"),
      ],
      [
          KeyboardButton(text="🏆 লিডারবোর্ড"),
          KeyboardButton(text="🎯 মাইক্রো টাস্ক"),
      ],
      [KeyboardButton(text="ℹ️ হেল্প ও রুলস")],
  ]
  if user_id == ADMIN_ID:
    kb.append([KeyboardButton(text="👑 এডমিন প্যানেল")])
  return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# --- স্টার্ট ও ফোর্স-জয়েন হ্যান্ডলার ---
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
  config = get_config()
  user_id = message.from_user.id
  username = message.from_user.username or "No Username"

  if config.get("maintenance") and user_id != ADMIN_ID:
    await message.answer(
        "🛠️ সিস্টেম আপডেট চলছে। দয়া করে কিছু সময় পর আবার চেষ্টা করুন।"
    )
    return

  # রেফারেল লিংক ট্র্যাক
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
        "referred_by": referrer_id,
    })

    if referrer_id and referrer_id != user_id:
      ref_bonus = config.get("refer_bonus", 10)
      users_col.update_one(
          {"telegram_id": referrer_id},
          {"$inc": {"balance": ref_bonus, "referrals": 1}},
      )
      try:
        await bot.send_message(
            referrer_id,
            f"🔥 নতুন রেফার যুক্ত হয়েছে! আপনার অ্যাকাউন্টে ৳{ref_bonus} যোগ করা হয়েছে।",
        )
      except Exception:
        pass

  # ফোর্স-জয়েন চেক
  if not await check_user_channels(user_id):
    channels = list(channels_col.find())
    buttons = [
        [
            InlineKeyboardButton(
                text=f"📢 Join Channel {idx}", url=ch["invite_link"]
            )
        ]
        for idx, ch in enumerate(channels, 1)
    ]
    buttons.append([
        InlineKeyboardButton(
            text="✅ আমি জয়েন করেছি, ভেরিফাই করুন", callback_data="verify_join"
        )
    ])
    await message.answer(
        "⚠️ **বাধ্যতামূলক নোটিশ:**\n\nবট ব্যবহার করতে হলে আমাদের নিচের চ্যানেলগুলোতে অবশ্যই জয়েন করতে হবে!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    return

  await message.answer(
      "🎉 স্বাগতম! আপনার মূল মেনু ওপেন হয়েছে। নিচ থেকে অপশন সিলেক্ট করুন:",
      reply_markup=get_main_keyboard(user_id),
  )


@router.callback_query(F.data == "verify_join")
async def verify_join_callback(callback: CallbackQuery):
  if not await check_user_channels(callback.from_user.id):
    await callback.answer(
        "❌ আপনি এখনও সব চ্যানেলে জয়েন করেননি!", show_alert=True
    )
    return
  await callback.message.delete()
  await callback.message.answer(
      "✅ ভেরিফিকেশন সফল!",
      reply_markup=get_main_keyboard(callback.from_user.id),
  )


# --- মেইন মেনু টেক্সট হ্যান্ডলার ও আন-জয়েন সিকিউরিটি গার্ড ---
@router.message(
    F.text.in_({
        "💰 আমার ব্যালেন্স",
        "👥 ইনভাইট ও রেফার",
        "🎁 ডেইলি বোনাস",
        "💳 টাকা তুলুন (bKash/Nagad)",
        "🏆 লিডারবোর্ড",
        "🎯 মাইক্রো টাস্ক",
        "ℹ️ হেল্প ও রুলস",
    })
)
async def main_menu_actions(message: Message):
  user_id = message.from_user.id

  # রিয়েল-টাইম আন-জয়েন ডিটেক্টর সিকিউরিটি
  if not await check_user_channels(user_id):
    channels = list(channels_col.find())
    buttons = [
        [
            InlineKeyboardButton(
                text=f"📢 Join Channel {idx}", url=ch["invite_link"]
            )
        ]
        for idx, ch in enumerate(channels, 1)
    ]
    buttons.append([
        InlineKeyboardButton(
            text="✅ পুনরায় ভেরিফাই করুন", callback_data="verify_join"
        )
    ])
    await message.answer(
        "⚠️ **সতর্কবার্তা!** আপনি চ্যানেল থেকে লিভ নিয়েছেন। পুনরায় বট ব্যবহার করতে আবার জয়েন করুন!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    return

  text = message.text
  user = users_col.find_one({"telegram_id": user_id})
  config = get_config()

  if text == "💰 আমার ব্যালেন্স":
    await message.answer(
        f"📊 **আপনার ওয়ালেট:**\n\n🆔 আইডি: `{user_id}`\n💰 ব্যালেন্স: **৳{user.get('balance', 0)}**\n👥 রেফার: **{user.get('referrals', 0)} জন**"
    )

  elif text == "👥 ইনভাইট ও রেফার":
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    bonus = config.get("refer_bonus", 10)
    await message.answer(
        f"🔗 **আপনার রেফারেল লিংক:**\n\n`{link}`\n\n📌 প্রতি রেফারে পাবেন **৳{bonus}**!"
    )

  elif text == "🎁 ডেইলি বোনাস":
    users_col.update_one({"telegram_id": user_id}, {"$inc": {"balance": 10}})
    await message.answer("🎁 আপনি ডেইলি বোনাস হিসেবে **৳১০** পেয়েছেন!")

  elif text == "💳 টাকা তুলুন (bKash/Nagad)":
    min_w = config.get("min_withdraw", 500)
    if user.get("balance", 0) < min_w:
      await message.answer(
          f"❌ পর্যাপ্ত ব্যালেন্স নেই! ন্যূনতম উইথড্র **৳{min_w}**।"
      )
    else:
      # অটো-পেমেন্ট সিমুলেটর লজিক
      if config.get("auto_payout", True):
        await message.answer(
            "✅ উইথড্র রিকোয়েস্ট সফল! সিমুলেটেড মোডে ৫ মিনিটের মধ্যে আপনার bKash নম্বরে টাকা পাঠানো হবে।"
        )
      else:
        await message.answer(
            "✅ উইথড্র রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে।"
        )

  elif text == "🏆 লিডারবোর্ড":
    tops = list(users_col.find().sort("referrals", -1).limit(5))
    txt = "🏆 **টপ লিডারবোর্ড:**\n\n"
    for i, u in enumerate(tops, 1):
      txt += f"{i}. @{u.get('username')} — {u.get('referrals', 0)} রেফার\n"
    await message.answer(txt)

  elif text == "🎯 মাইক্রো টাস্ক":
    tasks = list(tasks_col.find())
    if not tasks:
      await message.answer("📭 বর্তমানে কোনো নতুন টাস্ক নেই।")
    else:
      txt = "🎯 **চলমান টাস্কসমূহ:**\n"
      for t in tasks:
        txt += f"• {t['title']} (রিওয়ার্ড: ৳{t['reward']})\n"
      await message.answer(txt)

  elif text == "ℹ️ হেল্প ও রুলস":
    await message.answer(
        "ℹ️ নিয়ম মেনে কাজ করুন। ফেক রেফার বা স্প্যামিং করলে আইডি ব্যান করা হবে।"
    )


# --- মাস্টার অ্যাডমিন কন্ট্রোল প্যানেল (ইনলাইন বাটন সহ) ---
@router.message(F.text == "👑 এডমিন প্যানেল")
async def admin_panel(message: Message):
  if message.from_user.id != ADMIN_ID:
    return

  markup = InlineKeyboardMarkup(inline_keyboard=[
      [
          InlineKeyboardButton(
              text="📊 লাইভ স্ট্যাটস", callback_data="adm_stats"
          ),
          InlineKeyboardButton(
              text="📢 ব্রডকাস্ট", callback_data="adm_broadcast"
          ),
      ],
      [
          InlineKeyboardButton(
              text="➕ চ্যানেল যোগ", callback_data="adm_add_ch"
          ),
          InlineKeyboardButton(
              text="📋 চ্যানেল লিস্ট", callback_data="adm_list_ch"
          ),
      ],
      [
          InlineKeyboardButton(
              text="🎁 বোনাস সেটিংস", callback_data="adm_bonus_set"
          ),
          InlineKeyboardButton(
              text="📉 উইথড্র লিমিট", callback_data="adm_min_w"
          ),
      ],
      [
          InlineKeyboardButton(
              text="🛠️ মেইনটেনেন্স মোড টগল", callback_data="adm_maint"
          ),
          InlineKeyboardButton(
              text="🤖 অটো-পেমেন্ট টগল", callback_data="adm_autopay"
          ),
      ],
  ])
  await message.answer(
      "👑 **মাস্টার অ্যাডমিন প্যানেল:**\nনিচের অপশনগুলো থেকে কন্ট্রোল করুন:",
      reply_markup=markup,
  )


@router.callback_query(F.data == "adm_stats")
async def cb_stats(cb: CallbackQuery):
  if cb.from_user.id != ADMIN_ID:
    return
  total = users_col.count_documents({})
  await cb.message.edit_text(
      f"📊 **স্ট্যাটিস্টিক্স:**\n\n👥 মোট ইউজার: `{total}`\n🟢 সার্ভার: `Online`"
  )


@router.callback_query(F.data == "adm_maint")
async def cb_maint(cb: CallbackQuery):
  if cb.from_user.id != ADMIN_ID:
    return
  cfg = get_config()
  ns = not cfg.get("maintenance", False)
  settings_col.update_one({"_id": "config"}, {"$set": {"maintenance": ns}})
  await cb.answer(f"মেইনটেনেন্স মোড: {'ON' * ns or 'OFF'}", show_alert=True)


@router.callback_query(F.data == "adm_autopay")
async def cb_autopay(cb: CallbackQuery):
  if cb.from_user.id != ADMIN_ID:
    return
  cfg = get_config()
  ns = not cfg.get("auto_payout", True)
  settings_col.update_one({"_id": "config"}, {"$set": {"auto_payout": ns}})
  await cb.answer(f"অটো-পেমেন্ট সিমুলেটর: {'ON' * ns or 'OFF'}", show_alert=True)


@router.callback_query(F.data == "adm_add_ch")
async def cb_add_ch(cb: CallbackQuery, state: FSMContext):
  if cb.from_user.id != ADMIN_ID:
    return
  await cb.message.answer(
      "চ্যানেল আইডি এবং ইনভাইট লিংক দিন এই ফরম্যাটে:\n`chat_id|https://t.me/...`"
  )
  await state.set_state(AdminStates.waiting_for_channel)


@router.message(AdminStates.waiting_for_channel)
async def save_ch(message: Message, state: FSMContext):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    cid, link = message.text.split("|")
    channels_col.insert_one(
        {"chat_id": int(cid.strip()), "invite_link": link.strip()}
    )
    await message.answer("✅ চ্যানেল সফলভাবে যুক্ত হয়েছে!")
  except Exception:
    await message.answer("❌ ফরম্যাট ভুল হয়েছে।")
  await state.clear()


@router.callback_query(F.data == "adm_list_ch")
async def cb_list_ch(cb: CallbackQuery):
  if cb.from_user.id != ADMIN_ID:
    return
  chs = list(channels_col.find())
  txt = "📋 **সংযুক্ত চ্যানেলসমূহ:**\n\n"
  for idx, c in enumerate(chs, 1):
    txt += f"{idx}. ID: `{c['chat_id']}` | Link: {c['invite_link']}\n"
  await cb.message.edit_text(txt)


@router.callback_query(F.data == "adm_broadcast")
async def cb_bc(cb: CallbackQuery, state: FSMContext):
  if cb.from_user.id != ADMIN_ID:
    return
  await cb.message.answer("ব্রডকাস্ট করার জন্য মেসেজটি লিখুন:")
  await state.set_state(AdminStates.waiting_for_broadcast)


@router.message(AdminStates.waiting_for_broadcast)
async def exec_bc(message: Message, state: FSMContext):
  if message.from_user.id != ADMIN_ID:
    return
  txt = message.text
  users = list(users_col.find({}, {"telegram_id": 1}))
  cnt = 0
  for u in users:
    try:
      await bot.send_message(u["telegram_id"], f"📢 **অফিসিয়াল ঘোষণা:**\n\n{txt}")
      cnt += 1
      await asyncio.sleep(0.04)
    except Exception:
      pass
  await message.answer(f"✅ সফলভাবে `{cnt}` জন ইউজারের কাছে ব্রডকাস্ট পাঠানো হয়েছে।")
  await state.clear()


# --- রেন্ডার ওয়েব সার্ভিস মেইন লুপ ---
async def main():
  print("🤖 রেন্ডার সার্ভিসের জন্য বট সফলভাবে চালু হয়েছে...")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
