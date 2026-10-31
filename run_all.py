import os
import sys
import subprocess
from multiprocessing import Process
import uvicorn

def run_api():
    """Runs the FastAPI website server."""
    port = int(os.environ.get("PORT", 8000))
    # Import app from website
    sys.path.insert(0, os.path.abspath("website"))
    from website.main import app
    uvicorn.run(app, host="0.0.0.0", port=port)

def run_bot():
    """Runs the Telegram bot."""
    bot_script = os.path.abspath("bot/bot.py")
    subprocess.run([sys.executable, bot_script])

if __name__ == "__main__":
    p_api = Process(target=run_api)
    p_bot = Process(target=run_bot)
    
    p_api.start()
    p_bot.start()
    
    p_api.join()
    p_bot.join()
