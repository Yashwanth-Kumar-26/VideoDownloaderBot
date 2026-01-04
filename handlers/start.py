from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from utils.keyboard import get_main_menu

router = Router()

@router.message(Command("start"))
async def start_command(message: Message, db_user: dict):
    # db_user is injected by AuthMiddleware
    username = message.from_user.first_name
    await message.answer(
        f"👋 Welcome, {username}!\n\n"
        "I can download videos and audio from various platforms.\n"
        "Select an option below to get started:",
        reply_markup=get_main_menu()
    )

@router.callback_query(lambda c: c.data == "menu:main")
@router.callback_query(lambda c: c.data == "start") # Compatibility for old buttons
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "Select an option below:",
        reply_markup=get_main_menu()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "delete")
async def delete_message(callback: CallbackQuery):
    try:
        await callback.message.delete()
        await callback.answer()
    except Exception:
        await callback.answer("Could not delete")
