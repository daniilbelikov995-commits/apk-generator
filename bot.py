import os
import time
import base64
import requests
import telebot
from openai import OpenAI

# Получаем настройки из переменных окружения
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Привет! Напиши, какое Android-приложение ты хочешь создать, и я скомпилирую для тебя .apk!")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    prompt = message.text
    
    bot.send_message(chat_id, "🧠 Придумываю и пишу Python/Kivy код через OpenAI...")

    # 1. Генерируем Python код приложения
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a Kivy Python expert. Generate ONLY valid runnable Python code using Kivy framework for Android. Do not include markdown code blocks or explanations. Output pure Python code only."},
                {"role": "user", "content": prompt}
            ]
        )
        code = response.choices[0].message.content.strip()
        # Очистка от возможных тэгов markdown
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1])
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка генерации кода: {e}")
        return

    bot.send_message(chat_id, "⚙️ Сохраняю код в GitHub и запускаю облачную компиляцию...")

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 2. Обновляем main.py в репозитории
    url = f"[https://api.github.com/repos/](https://api.github.com/repos/){GITHUB_REPO}/contents/main.py"
    get_res = requests.get(url, headers=headers)
    sha = get_res.json().get("sha") if get_res.status_code == 200 else None

    encoded_content = base64.b64encode(code.encode('utf-8')).decode('utf-8')
    data = {
        "message": "Update generated app",
        "content": encoded_content
    }
    if sha:
        data["sha"] = sha

    requests.put(url, headers=headers, json=data)

    # 3. Запускаем сборку в GitHub Actions
    dispatch_url = f"[https://api.github.com/repos/](https://api.github.com/repos/){GITHUB_REPO}/dispatches"
    requests.post(dispatch_url, headers=headers, json={"event_type": "build_apk"})

    bot.send_message(
        chat_id, 
        "🚀 Сборка .APK началась на серверах GitHub!\n\n"
        "⏳ Это занимает примерно **3–4 минутки**.\n"
        "Зайдите во вкладку **Actions** в вашем репозитории на GitHub, чтобы скачать готовый файл приложения, когда сборка завершится!"
    )

if __name__ == '__main__':
    bot.infinity_polling()
