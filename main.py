import logging
import os
from flask import Flask, render_template, request, jsonify
from bot import create_bot

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/status')
def status():
    return jsonify({"status": "Bot is running"})

@app.route('/ping')
def ping():
    """Endpoint for uptime monitoring services to ping"""
    return "OK", 200

if __name__ == "__main__":
    # Create and run the bot
    bot = create_bot()
    bot.run_polling()
