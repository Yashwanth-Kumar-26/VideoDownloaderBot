#!/usr/bin/env python3
"""
Quick setup script for migrating SQLite to PostgreSQL
This helps prepare the database schema for Vercel deployment
"""
import os
import sys

def create_postgres_schema():
    """Generate PostgreSQL schema from SQLite schema"""

    sqlite_schema = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        referral_code TEXT UNIQUE NOT NULL,
        credits INTEGER DEFAULT 0,
        referred_by INTEGER,
        total_ref_credits INTEGER DEFAULT 0,
        referral_count INTEGER DEFAULT 0,
        is_premium BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (referred_by) REFERENCES users (id)
    );

    CREATE TABLE referrals (
        id SERIAL PRIMARY KEY,
        referrer_id INTEGER NOT NULL,
        referred_id INTEGER NOT NULL,
        status TEXT DEFAULT 'completed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (referrer_id) REFERENCES users (id),
        FOREIGN KEY (referred_id) REFERENCES users (id)
    );

    CREATE TABLE downloads (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        url TEXT NOT NULL,
        platform TEXT,
        file_type TEXT,
        resolution TEXT,
        file_size INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );

    CREATE TABLE admin_logs (
        id SERIAL PRIMARY KEY,
        admin_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (admin_id) REFERENCES users (id)
    );

    CREATE TABLE file_cache (
        id SERIAL PRIMARY KEY,
        url TEXT NOT NULL UNIQUE,
        platform TEXT,
        variant TEXT,
        telegram_file_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX idx_users_referral_code ON users(referral_code);
    CREATE INDEX idx_downloads_user_id ON downloads(user_id);
    CREATE INDEX idx_downloads_platform ON downloads(platform);
    CREATE INDEX idx_admin_logs_admin_id ON admin_logs(admin_id);
    CREATE INDEX idx_file_cache_url ON file_cache(url);
    """

    return sqlite_schema


def main():
    print("🗄️  PostgreSQL Schema Migration Helper")
    print("=" * 50)

    postgres_schema = create_postgres_schema()

    print("\n📋 PostgreSQL Schema (for Vercel deployment):\n")
    print(postgres_schema)

    print("\n" + "=" * 50)
    print("\n✅ To use this schema:")
    print("1. Create a PostgreSQL database on Railway/Supabase/etc")
    print("2. Get your DATABASE_URL")
    print("3. Connect to your PostgreSQL database")
    print("4. Run the schema above")
    print("5. Set DATABASE_URL in Vercel environment variables")
    print("6. Deploy to Vercel")

    # Option to save to file
    response = input("\nSave schema to file? (y/n): ").strip().lower()
    if response == 'y':
        filename = "postgresql_schema.sql"
        with open(filename, 'w') as f:
            f.write(postgres_schema)
        print(f"✅ Schema saved to {filename}")


if __name__ == "__main__":
    main()
