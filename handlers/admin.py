from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_USER_IDS
from database.supabase_client import db
import asyncio
import logging

logger = logging.getLogger(__name__)
router = Router()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS

@router.message(Command("admin"))
async def admin_dashboard(message: Message):
    if not is_admin(message.from_user.id):
        return

    # Fetch stats
    try:
        users = db.client.table("users").select("id", count="exact").execute()
        total_users = users.count
        
        # We could add more stats here like total downloads if we had a table for it
        # downloads = db.client.table("downloads").select("id", count="exact").execute()
        
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        total_users = "Error"

    text = (
        "👮‍♂️ **Admin Dashboard**\n\n"
        f"👥 **Total Users:** `{total_users}`\n"
        f"🤖 **Bot Status:** Active\n"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Broadcast Message", callback_data="admin:broadcast")],
        [InlineKeyboardButton(text="🔄 Refresh Stats", callback_data="admin:refresh")],
        [InlineKeyboardButton(text="🔙 Close", callback_data="delete")]
    ])
    
    await message.reply(text, reply_markup=kb)

@router.callback_query(lambda c: c.data == "admin:broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    
    await callback.message.edit_text(
        "📢 **Broadcast Mode**\n\n"
        "Send the message you want to broadcast to ALL users.\n"
        "Supported: Text, Photo, Video, Animation.\n\n"
        "Type /cancel to abort."
    )
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast)
async def broadcast_process(message: Message, state: FSMContext, bot):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.reply("❌ Broadcast cancelled.")
        return

    users_data = db.client.table("users").select("id").execute().data
    if not users_data:
        await message.reply("⚠️ No users found.")
        await state.clear()
        return

    count = 0
    blocked = 0
    total = len(users_data)
    
    status_msg = await message.reply(f"🚀 Starting broadcast to {total} users...")
    
    # Simple loop for now, ideally queue
    for i, u in enumerate(users_data):
        user_id = u['id']
        try:
            await message.copy_to(chat_id=user_id)
            count += 1
        except Exception as e:
            # Blocked or deactivated
            blocked += 1
        
        if i % 20 == 0:
            await asyncio.sleep(1) # Rate limit protection
            
    await status_msg.edit_text(
        f"✅ **Broadcast Complete**\n\n"
        f"Sent: {count}\n"
        f"Blocked/Failed: {blocked}\n"
        f"Total: {total}"
    )
    await state.clear()

@router.callback_query(lambda c: c.data == "admin:refresh")
async def refresh_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    # Reuse dashboard logic
    await admin_dashboard(callback.message)
    await callback.answer("Refreshed!")
