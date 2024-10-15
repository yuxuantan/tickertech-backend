import telebot
# Initialize the bot with your token

import os
from dotenv import load_dotenv

load_dotenv()

bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_API_TOKEN"))

# Function to send a message
def send_message(chat_ids=[27392018], message="Hi there!"):
    for chat_id in chat_ids:
        bot.send_message(chat_id, message, parse_mode= 'Markdown')
