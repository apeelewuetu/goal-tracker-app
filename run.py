import subprocess
import sys

# DETACHED_PROCESS flag ensures processes keep running even if VS Code closes
DETACHED_PROCESS = 0x00000008

scanner_out = open("scanner.log", "a")
subprocess.Popen(
    [sys.executable, "scanner.py"], 
    stdout=scanner_out, 
    stderr=scanner_out,
    creationflags=DETACHED_PROCESS
)

bot_out = open("bot.log", "a")
subprocess.Popen(
    [sys.executable, "bot.py"], 
    stdout=bot_out, 
    stderr=bot_out,
    creationflags=DETACHED_PROCESS
)

print("🚀 Both scripts are now fully detached and running like nohup!")