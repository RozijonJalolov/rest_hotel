import os
import sys
import subprocess
from multiprocessing import Process
import uvicorn

PORT = int(os.environ.get("PORT", 8000))
BOT_TOKEN = os.environ.get("BOT_TOKEN", "9134381937:AAFRc5qcuIzAURuBg5PifRJRUl2crzjXyZk")
API_KEY = os.environ.get("API_KEY", "hotel_secret_api_key_123")
API_BASE_URL = os.environ.get("API_BASE_URL", f"http://127.0.0.1:{PORT}")

os.environ["BOT_TOKEN"] = BOT_TOKEN
os.environ["API_KEY"] = API_KEY
os.environ["API_BASE_URL"] = API_BASE_URL

def run_api():
    """Runs the FastAPI website server."""
    sys.path.insert(0, os.path.abspath("website"))
    from website.main import app
    uvicorn.run(app, host="0.0.0.0", port=PORT)

def run_bot():
    """Runs the Telegram bot."""
    bot_script = os.path.abspath("bot/bot.py")
    env = os.environ.copy()
    env["BOT_TOKEN"] = BOT_TOKEN
    env["API_KEY"] = API_KEY
    env["API_BASE_URL"] = API_BASE_URL
    subprocess.run([sys.executable, bot_script], env=env)

if __name__ == "__main__":
    p_api = Process(target=run_api)
    p_bot = Process(target=run_bot)
    
    p_api.start()
    p_bot.start()
    
    p_api.join()
    p_bot.join()
