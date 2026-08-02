import base64
import os
from threading import Thread
from flask import Flask
import requests
import telebot

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = os.getenv("GITHUB_OWNER")
REPO_NAME = os.getenv("GITHUB_REPO")

bot = telebot.TeleBot(TOKEN)

# Веб-сервер для UptimeRobot, чтобы бот не засыпал на бесплатном хостинге (например, Render)
app = Flask("")


@app.route("/")
def home():
  return "Bot is active and running!"


def run_web():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


def keep_alive():
  t = Thread(target=run_web)
  t.start()


@bot.message_handler(commands=["start"])
def send_welcome(message):
  bot.reply_to(
      message,
      "Привет! Отправь мне код Python, и я запущу его сборку в APK через"
      " GitHub Actions.",
  )


@bot.message_handler(func=lambda message: True)
def handle_message(message):
  user_text = message.text
  chat_id = message.chat.id
  bot.reply_to(message, "🔄 Обновляю код и запускаю сборку APK на GitHub...")

  try:
    file_path = "main.py"
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    # Получаем SHA текущего файла (необходимо для обновления через GitHub API)
    r = requests.get(url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None

    encoded_content = base64.b64encode(user_text.encode("utf-8")).decode(
        "utf-8"
    )

    data = {
        "message": f"Update main.py from Telegram chat {chat_id}",
        "content": encoded_content,
        "sha": sha,
    }

    # Записываем обновленный код в репозиторий
    r_put = requests.put(url, headers=headers, json=data)
    if r_put.status_code not in [200, 201]:
      bot.reply_to(message, f"❌ Ошибка записи на GitHub: {r_put.text}")
      return

    # Запускаем GitHub Actions и передаем chat_id через inputs
    dispatch_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/build.yml/dispatches"
    dispatch_data = {"ref": "main", "inputs": {"chat_id": str(chat_id)}}
    r_disp = requests.post(dispatch_url, headers=headers, json=dispatch_data)

    if r_disp.status_code == 204:
      bot.reply_to(
          message,
          "🚀 Сборка успешно запущена! Как только компиляция завершится,"
          " готовый APK придет сюда.",
      )
    else:
      bot.reply_to(
          message,
          f"❌ Ошибка запуска ворфлоу (проверьте имя файла build.yml):"
          f" {r_disp.text}",
      )

  except Exception as e:
    bot.reply_to(message, f"⚠️ Ошибка: {str(e)}")


if __name__ == "__main__":
  # Запускаем веб-сервер для предотвращения засыпания
  keep_alive()
  # Запускаем бота
  bot.infinity_polling()
