import subprocess
import sys

# DETACHED_PROCESS flag ensures process keeps running even if VS Code closes
DETACHED_PROCESS = 0x00000008

bot_out = open("bot.log", "a", encoding="utf-8")
subprocess.Popen(
    [sys.executable, "bot.py"], 
    stdout=bot_out, 
    stderr=bot_out,
    creationflags=DETACHED_PROCESS
)

print("🚀 Bot script is now fully detached and running like nohup!")