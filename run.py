#!/usr/bin/env python3
# run.py wrapper script mapping to requested python environment
import asyncio
import sys
import os
import subprocess

PYTHON_EXECUTABLE = "/home/siddu/MyProJects/MainPython/Vir/bin/python"

async def run_bot(script_name):
    print(f"🔄 Starting {script_name}...")
    process = await asyncio.create_subprocess_exec(
        PYTHON_EXECUTABLE, script_name,
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
    print("🚀 Local Environment Started. Launching Bots...")
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
