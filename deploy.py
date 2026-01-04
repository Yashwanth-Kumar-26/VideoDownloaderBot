import os
import subprocess
import sys

def run_command(cmd):
    """Runs a shell command and exits if it fails."""
    print(f"⚡ Running: {cmd}")
    ret_code = subprocess.call(cmd, shell=True)
    if ret_code != 0:
        print(f"❌ Command failed: {cmd}")
        sys.exit(ret_code)

def main():
    print("🐳 Initializing Full Stack Deployment...")
    
    # Check if .env exists
    if not os.path.exists(".env"):
        print("❌ Error: .env file not found!")
        sys.exit(1)
        
    # Read .env to get API ID/HASH for the Server
    env_vars = {}
    with open(".env") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                env_vars[key] = val

    api_id = env_vars.get("TELEGRAM_API_ID")
    api_hash = env_vars.get("TELEGRAM_API_HASH")
    
    if not api_id or not api_hash:
        print("❌ TELEGRAM_API_ID or TELEGRAM_API_HASH missing in .env")
        sys.exit(1)

    # 1. Create Network
    print("\n🌐 Creating Docker Network...")
    run_command("docker network create telegram-bot-net || true")

    # 2. Start Local API Server
    print("\n📡 Starting Local Telegram API Server...")
    run_command("docker rm -f telegram-api-server || true")
    
    api_cmd = (
        f"docker run -d --name telegram-api-server "
        f"--network telegram-bot-net "
        f"-e TELEGRAM_API_ID={api_id} "
        f"-e TELEGRAM_API_HASH={api_hash} "
        f"-v telegram-api-data:/var/lib/telegram-bot-api "
        f"aiogram/telegram-bot-api:latest --local"
    )
    run_command(api_cmd)

    # 3. Build Bot Image
    print("\n🔨 Building Bot Image...")
    run_command("docker build -t telegram-downloader-bot .")

    # 4. Start Bot Container
    print("\n🚀 Starting Bot Container...")
    run_command("docker rm -f telegram-downloader-container || true")
    
    # Connect to the API server via network alias 'telegram-api-server'
    bot_cmd = (
        f"docker run -d --name telegram-downloader-container "
        f"--network telegram-bot-net "
        f"--env-file .env "
        f"-e LOCAL_API_URL=http://telegram-api-server:8081 "
        f"-v $(pwd)/downloads:/app/downloads "
        f"--restart unless-stopped "
        f"telegram-downloader-bot"
    )
    run_command(bot_cmd)

    print("\n✅ Full Stack Deployed!")
    print("1. API Server: Running (internal)")
    print("2. Bots: Running")
    print("📜 Logs: docker logs -f telegram-downloader-container")

if __name__ == "__main__":
    main()
