import asyncio
import logging
import os
from dotenv import load_dotenv

# Load Env FIRST
load_dotenv()

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from config import ADMIN_USER_IDS

ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Router
router = Router()

class AdminStates(StatesGroup):
    search_user = State()
    waiting_for_broadcast = State()
    manage_credits = State()

# --- Helpers ---
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS

def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 User Manager", callback_data="admin:users"),
         InlineKeyboardButton(text="📢 Broadcast", callback_data="admin:broadcast")],
        [InlineKeyboardButton(text="📊 Full Stats", callback_data="admin:stats"),
         InlineKeyboardButton(text="⚙️ Settings", callback_data="admin:settings")],
    ])

# --- Dashboard ---
@router.message(Command("start"))
@router.message(Command("admin"))
async def admin_dashboard(message: Message):
    uid = message.from_user.id
    logger.info(f"Command /admin from {uid}. Is Admin? {is_admin(uid)}")
    
    if not is_admin(uid):
        await message.reply("⛔ Access Denied.")
        return

    await show_admin_dashboard(message)

async def show_admin_dashboard(message: Message, is_edit: bool = False):
    # Basic stats
    # Basic stats
    try:
        users_count = await db.get_users_count()
        ref_count = await db.get_referrals_count()
        active_status = "✅ Active"
    except Exception:
        users_count = "Error"
        ref_count = "Error"
        active_status = "⚠️ DB Error"

    text = (
        f"👮‍♂️ **Admin Panel**\n\n"
        f"👥 Users: `{users_count}`\n"
        f"🔗 Referrals: `{ref_count}`\n"
        f"🤖 System: {active_status}\n\n"
        "Select a module:"
    )
    
    if is_edit:
        await message.edit_text(text, reply_markup=get_main_kb())
    else:
        await message.answer(text, reply_markup=get_main_kb())

# --- User Manager ---
@router.callback_query(lambda c: c.data == "admin:users")
async def user_manager_home(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Callback admin:users from {callback.from_user.id}")
    await callback.message.edit_text(
        "👥 **User Management**\n\n"
        "Send me a **User ID** or **Referral Code** to manage a user.\n"
        "Or click Back.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin:home")]])
    )
    await state.set_state(AdminStates.search_user)

@router.message(AdminStates.search_user)
async def process_user_search(message: Message, state: FSMContext):
    query = message.text.strip()
    
    # Try ID first
    user = None
    if query.isdigit():
        user = await db.get_user(int(query))
    
    # Try Referral Code
    if not user:
        user = await db.get_user_by_referral_code(query)

    if not user:
        await message.reply("❌ User not found. Try again or /cancel.")
        return

    # Show User Profile
    await show_user_profile(message, user)
    await state.clear()

async def show_user_profile(message: Message, user: dict):
    uid = user['id']
    creds = user.get('credits', 0)
    is_prem = user.get('is_premium', False)
    status = "🌟 Premium" if is_prem else "👤 Free"
    
    text = (
        f"👤 **User Profile**\n"
        f"ID: `{uid}`\n"
        f"Name: {user.get('first_name', 'Unknown')}\n"
        f"Credits: `{creds}`\n"
        f"Status: **{status}**\n"
        f"Referrals: {user.get('referral_count', 0)}"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add 100 Credits", callback_data=f"act:add_creds:{uid}:100"),
         InlineKeyboardButton(text="➖ Remove 100", callback_data=f"act:rem_creds:{uid}:100")],
        [InlineKeyboardButton(text="🌟 Toggle Premium", callback_data=f"act:tog_prem:{uid}")],
        [InlineKeyboardButton(text="🚫 Ban User", callback_data=f"act:ban:{uid}")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin:users")]
    ])
    
    await message.answer(text, reply_markup=kb)

# --- Actions ---
@router.callback_query(lambda c: c.data.startswith("act:add_creds:"))
async def add_credits(callback: CallbackQuery):
    _, _, uid, amt = callback.data.split(":")
    await db.update_credits(int(uid), int(amt))
    await callback.answer(f"Added {amt} credits!")
    
    # Refresh Profile
    user = await db.get_user(int(uid))
    await callback.message.delete()
    await show_user_profile(callback.message, user)

@router.callback_query(lambda c: c.data.startswith("act:rem_creds:"))
async def remove_credits(callback: CallbackQuery):
    _, _, uid, amt = callback.data.split(":")
    await db.update_credits(int(uid), -int(amt))
    await callback.answer(f"Removed {amt} credits!")
    
    # Refresh Profile
    user = await db.get_user(int(uid))
    await callback.message.delete()
    await show_user_profile(callback.message, user)

@router.callback_query(lambda c: c.data.startswith("act:tog_prem:"))
async def toggle_premium(callback: CallbackQuery):
    _, _, uid = callback.data.split(":")
    user = await db.get_user(int(uid))
    new_status = not user.get('is_premium', False)
    
    try:
        await db.update_user_premium(int(uid), new_status)
        await callback.answer(f"Premium set to {new_status}")
    except Exception as e:
        await callback.answer("Error updating premium")
    
    # Refresh
    user = await db.get_user(int(uid))
    await callback.message.delete()
    await show_user_profile(callback.message, user)

@router.callback_query(lambda c: c.data == "admin:broadcast")
async def broadcast_entry(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📢 **Broadcast**\n\n"
        "Send the message (Text, Photo, Video) you want to send to ALL users.\n"
        "Type /cancel to abort."
    )
    await state.set_state(AdminStates.waiting_for_broadcast)

@router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.reply("🚫 Broadcast Cancelled.")
        await show_admin_dashboard(message)
        return

    # Fetch users
    try:
        users_ids = await db.get_all_user_ids()
    except Exception as e:
        await message.reply(f"⚠️ Error fetching users: {e}")
        await state.clear()
        return

    if not users_ids:
        await message.reply("No users found.")
        await state.clear()
        return

    status_msg = await message.reply(f"🚀 Sending to {len(users_ids)} users...")
    
    count = 0
    blocked = 0
    
    for user_id in users_ids:
        try:
            await message.copy_to(chat_id=user_id)
            count += 1
        except Exception:
            blocked += 1
            
        if count % 20 == 0:
            await asyncio.sleep(1) # Rate limit

    await status_msg.edit_text(
        f"✅ **Broadcast Complete**\n\n"
        f"sent: {count}\n"
        f"blocked/failed: {blocked}"
    )
    await state.clear()
    await show_admin_dashboard(message)

@router.callback_query(lambda c: c.data == "admin:stats")
async def show_full_stats(callback: CallbackQuery):
    try:
        # Fetch Aggregated Stats
        total_users = await db.get_users_count()
        total_refs = await db.get_referrals_count()
        total_downloads = await db.get_downloads_count()
        
        # Calculate total credits (might be heavy if many users, keeping it simple for now)
        # For now, just show counts
        
        text = (
            f"📊 **System Statistics**\n\n"
            f"👥 **Total Users**: `{total_users}`\n"
            f"🔗 **Total Referrals**: `{total_refs}`\n"
            f"⬇️ **Total Downloads**: `{total_downloads}`\n\n"
            f"🟢 **Bot Status**: Online\n"
            f"📡 **API Latency**: Normal"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin:home")]])
        )
            
    except Exception as e:
        logger.error(f"Stats Error: {e}")
        await callback.answer("Error fetching stats", show_alert=True)

@router.callback_query(lambda c: c.data == "admin:home")
async def back_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_admin_dashboard(callback.message, is_edit=True)

@router.callback_query(lambda c: c.data == "admin:settings")
async def admin_settings_placeholder(callback: CallbackQuery):
    await callback.answer("Settings coming soon!", show_alert=True)

# --- Main ---
async def main():
    if not ADMIN_BOT_TOKEN:
        logger.error("ADMIN_BOT_TOKEN not found in .env")
        return
        
    bot = Bot(token=ADMIN_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    logger.info(f"🚀 Admin Bot Started... Admins: {ADMIN_USER_IDS}")
    logger.info(f"🚀 Admin Bot Started... Admins: {ADMIN_USER_IDS}")
    
    # Init DB
    try:
        await db.connect()
    except Exception as e:
        logger.error(f"Failed to connect to DB: {e}")
        return

    try:
        await dp.start_polling(bot)
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())
