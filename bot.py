import os
import time
import requests
from threading import Thread
from flask import Flask
import telebot

# Получаем токены из переменных окружения Render
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = os.getenv("GITHUB_OWNER")  # Ваш юзернейм или организация на GitHub
REPO_NAME = os.getenv("GITHUB_REPO")  # Название репозитория

bot = telebot.TeleBot(TOKEN)

# --- МИНИ-СЕРВЕР ДЛЯ ПРЕДОТВРАЩЕНИЯ ЗАСЫПАНИЯ НА RENDER ---
app = Flask("")


@app.route("/")
def home():
  return "Bot is active!"


def run_web():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


def keep_alive():
  t = Thread(target=run_web)
  t.start()


# -----------------------------------------------------------


@bot.message_handler(commands=["start"])
def send_welcome(message):
  bot.reply_to(
      message,
      "Привет! Отправь мне текст или код, и я соберу из него APK через GitHub"
      " Actions.",
  )


@bot.message_handler(func=lambda message: True)
def handle_message(message):
  user_text = message.text
  bot.reply_to(
      message, "🔄 Принято! Обновляю код в репозитории и запускаю сборку APK..."
  )

  try:
    # 1. Шаг: Обновляем main.py в репозитории GitHub
    file_path = "main.py"
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    # Получаем текущий SHA файла (требуется GitHub API для обновления)
    r = requests.get(url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None

    import base64

    encoded_content = base64.b64encode(user_text.encode("utf-8")).decode(
        "utf-8"
    )

    data = {
        "message": "Update main.py via Telegram bot",
        "content": encoded_content,
        "sha": sha,
    }

    r_put = requests.put(url, headers=headers, json=data)
    if r_put.status_code not in [200, 201]:
      bot.reply_to(
          message,
          f"❌ Ошибка при обновлении файла на GitHub: {r_put.text}",
      )
      return

    # 2. Шаг: Запускаем GitHub Action (workflow_dispatch)
    dispatch_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/build.yml/dispatches"
    dispatch_data = {"ref": "main"}
    r_disp = requests.post(dispatch_url, headers=headers, json=dispatch_data)

    if r_disp.status_code != 204:
      bot.reply_to(
          message, f"❌ Не удалось запустить сборку: {r_disp.text}"
      )
      return

    bot.reply_to(
        message,
        "⚙️ Сборка APK запущена на сервере GitHub. Это займет несколько минут...",
    )

    # 3. Шаг: Ожидание и поиск артефакта (APK)
    time.sleep(30)  # Даем время ворфлоу на запуск
    run_id = None

    for _ in range(20):  # Ждем максимум ~10 минут
      runs_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs"
      r_runs = requests.get(runs_url, headers=headers)
      if r_runs.status_code == 200:
        runs = r_runs.json().get("workflow_runs", [])
        if runs:
          latest_run = runs[0]
          if latest_run["status"] == "completed":
            run_id = latest_run["id"]
            break
      time.sleep(30)

    if not run_id:
      bot.reply_to(
          message,
          "⏱ Время ожидания истекло или сборка еще идет. Проверьте GitHub.",
      )
      return

    # 4. Шаг: Скачивание и отправка APK пользователю
    artifacts_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs/{run_id}/artifacts"
    r_art = requests.get(artifacts_url, headers=headers)

    if r_art.status_code == 200:
      artifacts = r_art.json().get("artifacts", [])
      if artifacts:
        artifact_download_url = artifacts[0]["archive_download_url"]
        # Скачиваем архив с артефактом
        r_zip = requests.get(
            artifact_download_url,
            headers=headers,
            allow_redirects=True,
        )

        zip_path = "apk_package.zip"
        with open(zip_path, "wb") as f:
          f.write(r_zip.content)

        # Отправляем файл пользователю в Telegram
        with open(zip_path, "rb") as f:
          bot.send_document(
              message.chat.id, f, caption="✅ Готово! Вот ваш собранный APK."
          )
        return

    bot.reply_to(
        message, "❌ Сборка завершена, но артефакт (APK) не найден."
    )

  except Exception as e:
    bot.reply_to(message, f"⚠️ Произошла ошибка: {str(e)}")


if __name__ == "__main__":
  # Запускаем веб-сервер для UptimeRobot перед стартом бота
  keep_alive()
  # Запуск самого бота
  bot.infinity_polling()

