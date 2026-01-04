import asyncio
import sys
import os
from asyncio import create_subprocess_exec, subprocess

# This script runs INSIDE the container
async def run_bot(script_name):
    print(f"🔄 Starting {script_name}...")
    process = await create_subprocess_exec(
        sys.executable, script_name,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy()
    )
    
    async def log_stream(stream, label):
        while True:
            line = await stream.readline()
            if not line: break
            print(f"[{label}] {line.decode().strip()}")

    await asyncio.gather(
        log_stream(process.stdout, script_name),
        log_stream(process.stderr, script_name)
    )

async def main():
    print("🚀 Container Started. Launching Bots...")
    # Run both concurrently
    await asyncio.gather(
        run_bot("main.py"),
        run_bot("admin_main.py")
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
