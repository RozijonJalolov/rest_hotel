import os
import sys
import uvicorn

PORT = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath("website"))
    from website.main import app
    print(f"Starting standalone Sam Rest Hotel Web Server on port {PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
