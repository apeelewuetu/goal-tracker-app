import os
import subprocess
import sys

# DETACHED_PROCESS flag ensures process keeps running even if VS Code closes
DETACHED_PROCESS = 0x00000008

# Force UTF-8 environment variable for spawned child processes
env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

# Open log file explicitly with UTF-8 encoding
bot_out = open("bot.log", "a", encoding="utf-8")

subprocess.Popen(
    [sys.executable, "bot.py"], 
    stdout=bot_out, 
    stderr=bot_out,
    creationflags=DETACHED_PROCESS,
    env=env
)

print("🚀 Bot script is now fully detached and running like nohup!")