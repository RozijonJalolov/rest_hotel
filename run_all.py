import os
import sys
import subprocess
from multiprocessing import Process
import uvicorn

# Ensure defaults for server deployment
PORT = int(os.environ.get("PORT", 8000))
os.environ.setdefault("BOT_TOKEN", "9134381937:AAFRc5qcuIzAURuBg5PifRJRUl2crzjXyZk")
os.environ.setdefault("API_KEY", "hotel_secret_api_key_123")
os.environ.setdefault("API_BASE_URL", f"http://127.0.0.1:{PORT}")

def run_api():
    """Runs the FastAPI website server."""
    sys.path.insert(0, os.path.abspath("website"))
    from website.main import app
    uvicorn.run(app, host="0.0.0.0", port=PORT)

def run_bot():
    """Runs the Telegram bot with current environment."""
    bot_script = os.path.abspath("bot/bot.py")
    env = os.environ.copy()
    subprocess.run([sys.executable, bot_script], env=env)

if __name__ == "__main__":
    p_api = Process(target=run_api)
    p_bot = Process(target=run_bot)
    
    p_api.start()
    p_bot.start()
    
    p_api.join()
    p_bot.join()
