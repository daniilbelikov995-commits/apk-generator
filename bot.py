import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- Ваши данные ---
GITHUB_OWNER = "daniilbelikov995-commits"
GITHUB_REPO = "apk-generator1"
WORKFLOW_FILE = "build.yml"
DEFAULT_BRANCH = "main"
# ------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "🤖 Бот для сборки APK готов! Отправьте команду /build, чтобы запустить"
      " процесс."
  )


async def build_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
  github_token = "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"

  await update.message.reply_text("🔄 Отправляю запрос на сборку APK в GitHub...")

  url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"

  headers = {
      "Authorization": f"Bearer {github_token}",
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
  }

  payload = {"ref": DEFAULT_BRANCH}

  try:
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 204:
      await update.message.reply_text(
          "✅ Сборка успешно запущена на GitHub!\nСледить за прогрессом"
          " можно во вкладке Actions вашего репозитория."
      )
    else:
      await update.message.reply_text(
          f"❌ Ошибка от GitHub (код {response.status_code}):\n{response.text}"
      )
  except Exception as e:
    await update.message.reply_text(f"❌ Ошибка соединения с GitHub: {e}")


def main():
  telegram_token = "8906501599:AAEUHqETfOFMlrIU8OgZ1SbsbM1BUO6mpPc"

  app = ApplicationBuilder().token(telegram_token).build()

  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("build", build_apk))

  print("Бот успешно запущен на ПК и ждет команду /build...")
  app.run_polling()


if __name__ == "__main__":
  main()
