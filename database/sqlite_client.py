import os
import logging
import aiosqlite
import json
from typing import Optional, Dict, List, Any

# Configure logging
logger = logging.getLogger(__name__)

class SQLiteClient:
    _instance = None
    db_path: str
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SQLiteClient, cls).__new__(cls)
            cls._instance.db_path = os.getenv("SQLITE_DB_PATH", "database/downloader_bot.db")
        return cls._instance

    async def connect(self):
        """Initialize the database"""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
            # Create DB file and apply schema if not exists
            async with aiosqlite.connect(self.db_path) as conn:
                with open("database/schema.sql", "r") as f:
                    schema = f.read()
                await conn.executescript(schema)
                await conn.commit()
            logger.info("SQLite database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SQLite: {e}")
            raise e

    async def close(self):
        """Close the database interface"""
        logger.info("SQLite close called")

    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Telegram ID"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute("SELECT * FROM users WHERE id = ?", (telegram_id,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching user {telegram_id}: {e}")
            return None

    async def get_user_by_referral_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get user by referral code"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute("SELECT id FROM users WHERE referral_code = ?", (code,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching user by referral code {code}: {e}")
            return None

    async def create_user(self, telegram_id: int, username: str, first_name: str, last_name: str = None, referrer_id: int = None) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        try:
            import uuid
            referral_code = uuid.uuid4().hex[:8]
            
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                await conn.execute("""
                    INSERT INTO users (id, username, first_name, last_name, referral_code, credits, referred_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (telegram_id, username, first_name, last_name, referral_code, 10, referrer_id))
                await conn.commit()

                async with conn.execute("SELECT * FROM users WHERE id = ?", (telegram_id,)) as cursor:
                    row = await cursor.fetchone()
                    user_data = dict(row) if row else None

                if referrer_id:
                    try:
                        await conn.execute("""
                            INSERT INTO referrals (referrer_id, referred_id, status)
                            VALUES (?, ?, 'completed')
                        """, (referrer_id, telegram_id))
                        from config import REFERRAL_REWARD_CREDITS
                        
                        async with conn.execute("SELECT * FROM users WHERE id = ?", (referrer_id,)) as cursor:
                            referrer = await cursor.fetchone()
                            if referrer:
                                new_credits = referrer['credits'] + REFERRAL_REWARD_CREDITS
                                new_total_ref_credits = referrer['total_ref_credits'] + REFERRAL_REWARD_CREDITS
                                new_referral_count = referrer['referral_count'] + 1
                                
                                await conn.execute("""
                                    UPDATE users 
                                    SET credits = ?, total_ref_credits = ?, referral_count = ?
                                    WHERE id = ?
                                """, (new_credits, new_total_ref_credits, new_referral_count, referrer_id))
                        await conn.commit()
                        logger.info(f"Rewarded referrer {referrer_id}: +{REFERRAL_REWARD_CREDITS} creds")
                        
                    except aiosqlite.IntegrityError:
                        logger.warning("Skipping reward: User was already referred.")
                    except Exception as ref_e:
                        logger.error(f"Error creating referral record: {ref_e}")

            return user_data
        except Exception as e:
            logger.error(f"Error creating user {telegram_id}: {e}")
            return None

    async def update_credits(self, telegram_id: int, amount: int) -> bool:
        """Update user credits"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute("SELECT credits FROM users WHERE id = ?", (telegram_id,)) as cursor:
                    user = await cursor.fetchone()
                if not user:
                    return False
                
                new_credits = user[0] + amount
                if new_credits < 0:
                    return False
                
                cursor = await conn.execute("UPDATE users SET credits = ? WHERE id = ?", (new_credits, telegram_id))
                await conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating credits for {telegram_id}: {e}")
            return False
        return False

    async def ensure_referral_code(self, telegram_id: int) -> str:
        """Ensure user has a referral code"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute("SELECT referral_code FROM users WHERE id = ?", (telegram_id,)) as cursor:
                    user = await cursor.fetchone()
                
                if user and user[0]:
                    return user[0]
                
                import uuid
                new_code = str(uuid.uuid4())[:8]
                await conn.execute("UPDATE users SET referral_code = ? WHERE id = ?", (new_code, telegram_id))
                await conn.commit()
                return new_code
        except Exception as e:
            logger.error(f"Error ensuring referral code: {e}")
            return "error"

    async def log_download(self, user_id: int, url: str, platform: str, file_type: str, resolution: str = None, file_size: int = 0) -> bool:
        """Log a download"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    INSERT INTO downloads (user_id, url, platform, file_type, resolution, file_size)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, url, platform, file_type, resolution, file_size))
                await conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error logging download: {e}")
            return False
        return False

    async def get_user_stats(self, telegram_id: int) -> Dict[str, Any]:
        """Get user statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute("SELECT COUNT(*) FROM downloads WHERE user_id = ?", (telegram_id,)) as cursor:
                    total_downloads = (await cursor.fetchone())[0]
                async with conn.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (telegram_id,)) as cursor:
                    total_referrals = (await cursor.fetchone())[0]
                
                async with conn.execute("SELECT total_ref_credits FROM users WHERE id = ?", (telegram_id,)) as cursor:
                    user = await cursor.fetchone()
                    total_ref_credits = user[0] if user else 0
                
                return {
                    "total_downloads": total_downloads,
                    "total_referrals": total_referrals,
                    "total_ref_credits": total_ref_credits
                }
        except Exception as e:
            logger.error(f"Error fetching stats for {telegram_id}: {e}")
            return {"total_downloads": 0, "total_referrals": 0}
        return {"total_downloads": 0, "total_referrals": 0}

    async def get_settings(self, telegram_id: int) -> Dict[str, Any]:
        """Get user settings"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute("SELECT settings FROM users WHERE id = ?", (telegram_id,)) as cursor:
                    row = await cursor.fetchone()
                if row and row[0]:
                    settings = row[0]
                    if isinstance(settings, str):
                        return json.loads(settings)
                    return settings
            return {}
        except Exception as e:
            logger.error(f"Error fetching settings for {telegram_id}: {e}")
            return {}

    async def update_settings(self, telegram_id: int, key: str, value: Any) -> bool:
        """Update a specific setting key"""
        try:
            current_settings = await self.get_settings(telegram_id)
            current_settings[key] = value
            
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("UPDATE users SET settings = ? WHERE id = ?", (json.dumps(current_settings), telegram_id))
                await conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating settings for {telegram_id}: {e}")
            return False

    async def log_admin_action(self, admin_id: int, action: str, details: dict):
        """Log admin action"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    INSERT INTO admin_logs (admin_id, action, details)
                    VALUES (?, ?, ?)
                """, (admin_id, action, json.dumps(details)))
                await conn.commit()
        except Exception as e:
            logger.error(f"Error logging admin action: {e}")

    async def get_cached_file(self, url: str, variant: str) -> Optional[str]:
        """Check if file is already cached"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute("SELECT file_id FROM file_cache WHERE url = ? AND variant = ?", (url, variant)) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else None
        except Exception as e:
            logger.error(f"Error fetching cached file: {e}")
            return None

    async def save_cached_file(self, url: str, variant: str, file_id: str):
        """Save file_id to cache"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    INSERT INTO file_cache (url, variant, file_id)
                    VALUES (?, ?, ?)
                    ON CONFLICT(url, variant) DO UPDATE SET file_id=excluded.file_id
                """, (url, variant, file_id))
                await conn.commit()
        except Exception as e:
            logger.error(f"Error caching file: {e}")

    # --- Admin Helpers ---

    async def get_users_count(self) -> int:
        """Get total number of users"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute("SELECT COUNT(*) FROM users") as cursor:
                    return (await cursor.fetchone())[0]
        except Exception as e:
            logger.error(f"Error getting users count: {e}")
            return 0
        return 0

    async def get_referrals_count(self) -> int:
        """Get total number of referrals"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute("SELECT COUNT(*) FROM referrals") as cursor:
                    return (await cursor.fetchone())[0]
        except Exception as e:
            logger.error(f"Error getting referrals count: {e}")
            return 0
        return 0

    async def get_downloads_count(self) -> int:
        """Get total number of downloads"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute("SELECT COUNT(*) FROM downloads") as cursor:
                    return (await cursor.fetchone())[0]
        except Exception as e:
            logger.error(f"Error getting downloads count: {e}")
            return 0
        return 0

    async def get_all_user_ids(self) -> List[int]:
        """Get all user IDs (for broadcast)"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute("SELECT id FROM users") as cursor:
                    rows = await cursor.fetchall()
                    return [r[0] for r in rows]
        except Exception as e:
            logger.error(f"Error getting all user ids: {e}")
            return []

    async def update_user_premium(self, user_id: int, is_premium: bool) -> bool:
        """Update user premium status"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute("UPDATE users SET is_premium = ? WHERE id = ?", (int(is_premium), user_id))
                await conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating premium status: {e}")
            return False

# Global instance
db = SQLiteClient()
