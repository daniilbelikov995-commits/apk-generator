import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import time
import base64
import requests
import telebot
from openai import OpenAI

# Запускаем мини-сервер для Render, чтобы пройти проверку порта
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

Thread(target=run_server, daemon=True).start()

# Получаем настройки из переменных окружения
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

@bot.message_handler(commands=['start'])
def send_welcome(bot_message):
    bot.reply_to(bot_message, "Привет! Отправь мне код или описание приложения, и я соберу APK.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    code = message.text

    bot.send_message(chat_id, "⚙️ Обрабатываю запрос и обновляю репозиторий...")

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 2. Обновляем main.py в репозитории
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/main.py"
    get_res = requests.get(url, headers=headers)
    sha = get_res.json().get("sha") if get_res.status_code == 200 else None

    encoded_content = base64.b64encode(code.encode("utf-8")).decode("utf-8")
    data = {
        "message": "Update generated app",
        "content": encoded_content
    }
    if sha:
        data["sha"] = sha

    requests.put(url, headers=headers, json=data)

    # 3. Запускаем сборку в GitHub Actions
    dispatch_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/build.yml/dispatches"
    requests.post(dispatch_url, headers=headers, json={"ref": "main"})

    bot.send_message(
        chat_id,
        "🚀 Сборка .APK началась на сервере GitHub!\n"
        "⏳ Это занимает примерно **3–4 минуты**.\n"
        "Зайдите во вкладку **Actions** в вашем репозитории, чтобы следить за процессом."
    )

if __name__ == '__main__':
    bot.infinity_polling()

