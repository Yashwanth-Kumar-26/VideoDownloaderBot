import asyncio
from aiogram import Bot
from config import BOT_TOKEN

async def logout():
    print("🔌 Connecting to Telegram Cloud API to log out...")
    # Initialize bot without custom session (defaults to Cloud API)
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.log_out()
        print("✅ Success! Bot logged out from Cloud API.")
        print("🚀 You can now run 'python main.py' to connect to your Local Server.")
    except Exception as e:
        print(f"❌ Failed to log out: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(logout())
