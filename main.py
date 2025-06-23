from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import requests
from bs4 import BeautifulSoup
import os
import logging
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Токен бота (будет взят из переменной окружения)
BOT_TOKEN = "7638901123:AAFB_iNyA9dJfv8ONffY605u2_XMEEjeJjQ"

# Функция для создания безопасного имени файла
def sanitize_filename(filename: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

# Функция для поиска и скачивания книг
async def search_and_download_book(query: str, format: str) -> str:
    search_url = f"https://flibusta.is/booksearch?ask={query.replace(' ', '+')}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        response = requests.get(search_url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе к flibusta.is: {e}")
        return "Ошибка при подключении к сайту. Попробуйте позже."

    soup = BeautifulSoup(response.text, 'html.parser')
    book_links = soup.find_all('a', href=True)

    for link in book_links:
        if '/b/' in link['href']:
            book_url = f"https://flibusta.is{link['href']}/{format}"
            try:
                book_response = requests.get(book_url, headers=headers, timeout=30)
                book_response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.error(f"Ошибка при скачивании книги: {e}")
                return "Ошибка при скачивании книги."

            book_title = link.text.strip()
            safe_book_title = sanitize_filename(book_title)
            book_filename = f"{safe_book_title}.{format}"

            with open(book_filename, 'wb') as book_file:
                book_file.write(book_response.content)

            logger.info(f"Книга '{book_title}' успешно скачана.")
            return book_filename

    logger.warning("Книги не найдены.")
    return "Книги не найдены."

# Обработчик команды /start
async def start(update: Update, context):
    await update.message.reply_text(
        "Привет! Отправь мне название книги, и я найду её на flibusta.is и отправлю тебе."
    )

# Обработчик текстовых сообщений
async def handle_message(update: Update, context):
    user_query = update.message.text
    context.user_data['query'] = user_query

    keyboard = [
        [InlineKeyboardButton("FB2", callback_data='fb2')],
        [InlineKeyboardButton("EPUB", callback_data='epub')],
        [InlineKeyboardButton("MOBI", callback_data='mobi')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Выберите формат для скачивания:", reply_markup=reply_markup)

# Обработчик нажатия на кнопку
async def button_callback(update: Update, context):
    query = update.callback_query
    await query.answer()

    user_query = context.user_data.get('query')
    format = query.data

    await query.edit_message_text(text=f"Ищу книгу в формате {format.upper()}...")

    result = await search_and_download_book(user_query, format)
    
    if os.path.exists(result):
        with open(result, 'rb') as book_file:
            book_name = os.path.basename(result)
            await query.message.reply_document(document=book_file, filename=book_name)
        os.remove(result)
        await query.message.delete()
    else:
        await query.message.reply_text(result)

# Основная функция для запуска бота
async def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("Бот запущен.")
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
