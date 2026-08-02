import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

GITHUB_OWNER = "ВАШ_НИК_НА_GITHUB"
GITHUB_REPO = "apk-generator"
WORKFLOW_FILE = "build.yml"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("Бот готов. Нажми /build")


async def trigger_apk_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
  github_token = os.getenv("GITHUB_TOKEN")

  if not github_token:
    await update.message.reply_text("Ошибка: нет GITHUB_TOKEN на Render")
    return

  url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"

  headers = {
      "Authorization": f"Bearer {github_token}",
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
  }

  payload = {"ref": "main"}

  try:
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 204:
      await update.message.reply_text("Сборка запущена!")
    else:
      await update.message.reply_text(
          f"Ошибка {response.status_code}:\n{response.text}"
      )
  except Exception as e:
    await update.message.reply_text(f"Ошибка запроса: {e}")


def main():
  telegram_token = os.getenv("TELEGRAM_TOKEN")
  app = ApplicationBuilder().token(telegram_token).build()

  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("build", trigger_apk_build))

  app.run_polling()


if __name__ == "__main__":
  main()
