import os
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from supabase import create_client, Client
from supabase.client import ClientOptions
from postgrest.base_request_builder import APIResponse

# Configure logging
logger = logging.getLogger(__name__)

class SupabaseClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
            cls._instance.client = None
        return cls._instance

    def __init__(self):
        if not self.client:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            
            if not url or not key:
                logger.warning("Supabase URL or Key not found in environment variables.")
                return

            try:
                self.client: Client = create_client(url, key)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")

    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Telegram ID"""
        try:
            response = self.client.table("users").select("*").eq("id", telegram_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching user {telegram_id}: {e}")
            return None

    async def get_user_by_referral_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get user by referral code"""
        try:
            response = self.client.table("users").select("id").eq("referral_code", code).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching user by referral code {code}: {e}")
            return None

    async def create_user(self, telegram_id: int, username: str, first_name: str, last_name: str = None, referrer_id: int = None) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        try:
            # Generate a simple referral code if not exists
            import uuid
            referral_code = str(uuid.uuid4())[:8]
            
            data = {
                "id": telegram_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "referral_code": referral_code,
                "credits": 10  # Default starting credits
            }
            
            if referrer_id:
                data["referred_by"] = referrer_id

            response = self.client.table("users").insert(data).execute()
            
            # If there was a referrer, create referral record
            if referrer_id and response.data:
                try:
                    self.client.table("referrals").insert({
                        "referrer_id": referrer_id,
                        "referred_id": telegram_id,
                        "status": "completed"
                    }).execute()
                    
                    # Reward the referrer
                    from config import REFERRAL_REWARD_CREDITS
                    
                    # Fetch current stats to increment
                    referrer = await self.get_user(referrer_id)
                    if referrer:
                        new_credits = referrer.get("credits", 0) + REFERRAL_REWARD_CREDITS
                        new_total_ref_credits = referrer.get("total_ref_credits", 0) + REFERRAL_REWARD_CREDITS
                        new_referral_count = referrer.get("referral_count", 0) + 1
                        
                        self.client.table("users").update({
                            "credits": new_credits,
                            "total_ref_credits": new_total_ref_credits,
                            "referral_count": new_referral_count
                        }).eq("id", referrer_id).execute()
                        
                        logger.info(f"Rewarded referrer {referrer_id}: +{REFERRAL_REWARD_CREDITS} creds, +1 count.")

                except Exception as ref_e:
                    logger.error(f"Error creating referral record (User {telegram_id}, Referrer {referrer_id}): {ref_e}")
                    # If duplicate key, it means this user was already referred. We do NOT reward again.
                    if "duplicate key" in str(ref_e) or "constraint" in str(ref_e):
                         logger.warning("Skipping reward: User was already referred.")

            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating user {telegram_id}: {e}")
            return None

    async def update_credits(self, telegram_id: int, amount: int) -> bool:
        """Update user credits (add or subtract)"""
        try:
            # First get current credits
            user = await self.get_user(telegram_id)
            if not user:
                return False
            
            new_credits = user.get("credits", 0) + amount
            if new_credits < 0:
                return False # Not enough credits
                
            response = self.client.table("users").update({"credits": new_credits}).eq("id", telegram_id).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error updating credits for {telegram_id}: {e}")
            return False

    async def ensure_referral_code(self, telegram_id: int) -> str:
        """Ensure user has a referral code, generate if missing"""
        try:
            user = await self.get_user(telegram_id)
            if user and user.get("referral_code"):
                return user["referral_code"]
            
            import uuid
            new_code = str(uuid.uuid4())[:8]
            self.client.table("users").update({"referral_code": new_code}).eq("id", telegram_id).execute()
            return new_code
        except Exception as e:
            logger.error(f"Error ensuring referral code for {telegram_id}: {e}")
            return "error"  # Not enough credits
                
            response = self.client.table("users").update({"credits": new_credits}).eq("id", telegram_id).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error updating credits for {telegram_id}: {e}")
            return False

    async def log_download(self, user_id: int, url: str, platform: str, file_type: str, resolution: str = None, file_size: int = 0) -> bool:
        """Log a download"""
        try:
            data = {
                "user_id": user_id,
                "url": url,
                "platform": platform,
                "file_type": file_type,
                "resolution": resolution,
                "file_size": file_size
            }
            self.client.table("downloads").insert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Error logging download: {e}")
            return False

    async def get_user_stats(self, telegram_id: int) -> Dict[str, Any]:
        """Get user statistics"""
        try:
            # Get download count
            downloads = self.client.table("downloads").select("id", count="exact").eq("user_id", telegram_id).execute()
            total_downloads = downloads.count if downloads.count else 0
            
            # Get referral count
            referrals = self.client.table("referrals").select("id", count="exact").eq("referrer_id", telegram_id).execute()
            total_referrals = referrals.count if referrals.count else 0
            
            # Get user for stats
            user = await self.get_user(telegram_id)
            total_ref_credits = user.get("total_ref_credits", 0) if user else 0
            
            return {
                "total_downloads": total_downloads,
                "total_referrals": total_referrals, # Keep using dynamic count as main source of truth for count
                "total_ref_credits": total_ref_credits
            }
        except Exception as e:
            logger.error(f"Error fetching stats for {telegram_id}: {e}")
            return {"total_downloads": 0, "total_referrals": 0}

    async def get_settings(self, telegram_id: int) -> Dict[str, Any]:
        """Get user settings"""
        try:
            response = self.client.table("users").select("settings").eq("id", telegram_id).execute()
            if response.data and response.data[0].get("settings"):
                return response.data[0]["settings"]
            return {}
        except Exception as e:
            logger.error(f"Error fetching settings for {telegram_id}: {e}")
            return {}

    async def update_settings(self, telegram_id: int, key: str, value: Any) -> bool:
        """Update a specific setting key"""
        try:
            # Get current settings first
            current_settings = await self.get_settings(telegram_id)
            if current_settings is None:
                current_settings = {}
            
            # Update key
            current_settings[key] = value
            
            # Save back
            self.client.table("users").update({"settings": current_settings}).eq("id", telegram_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating settings for {telegram_id}: {e}")
            return False

    async def log_admin_action(self, admin_id: int, action: str, details: dict):
        """Log admin action"""
        try:
            self.client.table("admin_logs").insert({
                "admin_id": admin_id,
                "action": action,
                "details": details
            }).execute()
        except Exception as e:
            logger.error(f"Error logging admin action: {e}")

    async def get_cached_file(self, url: str, variant: str) -> Optional[str]:
        """Check if file is already cached"""
        try:
            response = self.client.table("file_cache").select("file_id").eq("url", url).eq("variant", variant).execute()
            if response.data:
                return response.data[0]['file_id']
            return None
        except Exception as e:
            logger.error(f"Error fetching cached file: {e}")
            return None

    async def save_cached_file(self, url: str, variant: str, file_id: str):
        """Save file_id to cache"""
        try:
            self.client.table("file_cache").upsert({
                "url": url,
                "variant": variant,
                "file_id": file_id
            }, on_conflict="url,variant").execute()
        except Exception as e:
            logger.error(f"Error caching file: {e}")

# Global instance
db = SupabaseClient()
