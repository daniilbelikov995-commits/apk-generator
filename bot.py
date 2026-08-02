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
    bot.reply_to(bot_message, "Привет! Отправь мне код или описание приложения, и я соберу APK с отправкой готового файла сюда.")

def check_and_send_apk(chat_id, headers):
    # Ожидаем старта ворфлоу (даем GitHub пару секунд на создание рана)
    time.sleep(10)
    
    runs_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs?per_page=1"
    run_id = None
    
    # Пытаемся найти ID последнего активного рана
    for _ in range(5):
        res = requests.get(runs_url, headers=headers)
        if res.status_code == 200:
            runs = res.json().get("workflow_runs", [])
            if runs:
                run_id = runs[0]["id"]
                break
        time.sleep(5)
        
    if not run_id:
        bot.send_message(chat_id, "⚠️ Не удалось отследить запуск сборки в GitHub Actions.")
        return

    bot.send_message(chat_id, "⏳ Сборка идет на сервере, ожидаю завершения...")

    # Опрашиваем статус сборки (максимум ~10 минут)
    status_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs/{run_id}"
    conclusion = None
    
    for _ in range(60):
        time.sleep(10)
        res = requests.get(status_url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            status = data.get("status")
            if status == "completed":
                conclusion = data.get("conclusion")
                break

    if conclusion != "success":
        bot.send_message(chat_id, f"❌ Сборка завершилась с ошибкой или статусом: {conclusion}")
        return

    bot.send_message(chat_id, "📦 Сборка успешна! Скачиваю APK...")

    # Ищем артефакт
    artifacts_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs/{run_id}/artifacts"
    res = requests.get(artifacts_url, headers=headers)
    if res.status_code != 200:
        bot.send_message(chat_id, "❌ Не удалось получить список артефактов.")
        return

    artifacts = res.json().get("artifacts", [])
    if not artifacts:
        bot.send_message(chat_id, "❌ Артефакты сборки не найдены.")
        return

    artifact_download_url = artifacts[0]["archive_download_url"]
    
    # Скачиваем архив с артефактом
    art_res = requests.get(artifact_download_url, headers=headers)
    if art_res.status_code != 200:
        bot.send_message(chat_id, "❌ Ошибка при скачивании артефакта.")
        return

    zip_path = "app.zip"
    with open(zip_path, "wb") as f:
        f.write(art_res.content)

    # Отправляем файл пользователю (если внутри zip один файл, или отправляем сам архив)
    # Чаще всего Buildozer кладет в артефакт сам .apk или архив с ним
    import zipfile
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall("extracted_apk")

    sent = False
    for root, dirs, files in os.walk("extracted_apk"):
        for file in files:
            if file.endswith(".apk"):
                apk_path = os.path.join(root, file)
                with open(apk_path, "rb") as apk_file:
                    bot.send_document(chat_id, apk_file, caption="🎉 Ваш APK файл готов!")
                sent = True
                break
        if sent:
            break

    if not sent:
        # Если структура отличается, отправляем архив целиком
        with open(zip_path, "rb") as zip_file:
            bot.send_document(chat_id, zip_file, caption="🎉 Архив с результатами сборки готов!")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    code = message.text

    bot.send_message(chat_id, "⚙️ Обрабатываю запрос и обновляю репозиторий...")

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Обновляем main.py в репозитории
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

    # Запускаем сборку в GitHub Actions
    dispatch_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/build.yml/dispatches"
    requests.post(dispatch_url, headers=headers, json={"ref": "main"})

    bot.send_message(chat_id, "🚀 Сборка .APK началась на сервере GitHub! Ожидайте, по завершении я пришлю файл.")

    # Запускаем фоновый процесс отслеживания и отправки в Telegram
    Thread(target=check_and_send_apk, args=(chat_id, headers), daemon=True).start()

if __name__ == '__main__':
    bot.infinity_polling()
