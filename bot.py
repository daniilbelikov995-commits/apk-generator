import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- УКАЖИТЕ СВОИ ДАННЫЕ ЗДЕСЬ ---
GITHUB_OWNER = "ВАШ_НИК_НА_GITHUB"  # Ваш точный логин
GITHUB_REPO = "apk-generator"  # Имя репозитория
WORKFLOW_FILE = "build.yml"  # Имя файла из Шага 1
DEFAULT_BRANCH = "main"  # Или master (проверьте в репозитории)
# ----------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "🤖 Бот готов с нуля! Отправь /build для запуска сборки."
  )


async def build_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
  github_token = os.getenv("GITHUB_TOKEN")

  if not github_token:
    await update.message.reply_text(
        "❌ Ошибка: на сервере не задан GITHUB_TOKEN."
    )
    return

  await update.message.reply_text("🔄 Отправляю запрос на сборку...")

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
          "✅ Сборка успешно запущена! Прогресс виден во вкладке Actions."
      )
    else:
      await update.message.reply_text(
          f"❌ Ошибка от GitHub ({response.status_code}):\n{response.text}"
      )
  except Exception as e:
    await update.message.reply_text(f"❌ Ошибка соединения: {e}")


def main():
  telegram_token = os.getenv("TELEGRAM_TOKEN")
  if not telegram_token:
    print("❌ Не найден TELEGRAM_TOKEN!")
    return

  app = ApplicationBuilder().token(telegram_token).build()

  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("build", build_apk))

  print("Бот запущен и ждет команды...")
  app.run_polling()


if __name__ == "__main__":
  main()
