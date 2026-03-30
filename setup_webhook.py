#!/usr/bin/env python3
"""
Setup script for Vercel deployment
Run this after deploying to Vercel to register the webhook with Telegram
"""
import os
import sys
import asyncio
import aiohttp

from config import BOT_TOKEN


async def register_webhook(bot_token: str, webhook_url: str) -> bool:
    """
    Register webhook URL with Telegram

    Args:
        bot_token: Telegram bot token
        webhook_url: Full URL to webhook endpoint (e.g., https://your-app.vercel.app/api/webhook)

    Returns:
        True if successful, False otherwise
    """

    url = f"https://api.telegram.org/bot{bot_token}/setWebhook"

    async with aiohttp.ClientSession() as session:
        try:
            response = await session.post(
                url,
                json={
                    "url": webhook_url,
                    "max_connections": 40,
                    "allowed_updates": [
                        "message",
                        "callback_query",
                        "inline_query",
                        "chosen_inline_result"
                    ]
                }
            )

            data = await response.json()

            if response.status == 200 and data.get("ok"):
                print(f"✅ Webhook registered successfully!")
                print(f"   URL: {webhook_url}")
                return True
            else:
                print(f"❌ Failed to register webhook")
                print(f"   Response: {data}")
                return False

        except Exception as e:
            print(f"❌ Error registering webhook: {e}")
            return False


async def get_webhook_info(bot_token: str) -> None:
    """Get current webhook information"""

    url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"

    async with aiohttp.ClientSession() as session:
        try:
            response = await session.get(url)
            data = await response.json()

            if data.get("ok"):
                info = data.get("result", {})
                print("\n📊 Current Webhook Info:")
                print(f"   URL: {info.get('url', 'Not set')}")
                print(f"   Pending Update Count: {info.get('pending_update_count', 0)}")
                print(f"   Max Allowed Connections: {info.get('max_allowed_connections', 0)}")

        except Exception as e:
            print(f"Error getting webhook info: {e}")


async def main():
    """Main setup function"""

    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not found in environment variables")
        sys.exit(1)

    # Get webhook URL from environment or ask user
    webhook_url = os.getenv("WEBHOOK_URL")

    if not webhook_url:
        print("❌ WEBHOOK_URL not found in environment variables")
        print("\nTo set up the webhook, you need to:")
        print("1. Deploy this app to Vercel")
        print("2. Get your Vercel URL (e.g., https://your-app.vercel.app)")
        print("3. Set WEBHOOK_URL environment variable to: https://your-app.vercel.app/api/webhook")
        print("4. Re-run this script")
        sys.exit(1)

    print(f"🔧 Setting up Telegram webhook on Vercel...")
    print(f"   Bot Token: {BOT_TOKEN[:20]}...")
    print(f"   Webhook URL: {webhook_url}")

    # Register webhook
    success = await register_webhook(BOT_TOKEN, webhook_url)

    # Get current info
    await get_webhook_info(BOT_TOKEN)

    if success:
        print("\n✅ Setup complete! Your bot is ready to receive updates.")
    else:
        print("\n⚠️  Webhook setup completed with errors. Check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
