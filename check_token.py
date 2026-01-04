import asyncio
from aiogram import Bot
from config import BOT_TOKEN

async def check():
    print(f"🔍 Checking token: {BOT_TOKEN[:10]}...")
    bot = Bot(token=BOT_TOKEN)
    try:
        me = await bot.get_me()
        print(f"✅ Token is VALID. Bot: @{me.username} ({me.id})")
        
        # If valid, try logging out again
        print("🔌 Attempting logout now...")
        await bot.log_out()
        print("✅ Logout successful.")
    except Exception as e:
        print(f"❌ Token Check Failed: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(check())
