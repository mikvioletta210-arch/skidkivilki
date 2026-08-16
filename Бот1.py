import logging
import os
from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
from sources.deals import DealCollector
from sources.utils import channel_value, get_env_int, is_admin, normalize_channel, safe_html
logging.basicConfig(format='%(asctime)s | %(levelname)s | %(name)s | %(message)s', level=logging.INFO)
log = logging.getLogger('skidkivilki')
TOKEN = os.getenv('BOT_TOKEN', '').strip()
CHANNEL = normalize_channel(os.getenv('CHANNEL_ID', '@skidkivilki'))
SCAN_INTERVAL = max(300, get_env_int('SCAN_INTERVAL', 600))
MAX_POSTS_PER_SCAN = max(1, get_env_int('MAX_POSTS_PER_SCAN', 8))
collector = DealCollector()
async def publish_deals(context: ContextTypes.DEFAULT_TYPE) -> int:
    deals = await collector.collect(limit=MAX_POSTS_PER_SCAN)
    published = 0
    for deal in deals:
        try:
            await context.bot.send_message(chat_id=channel_value(CHANNEL), text=deal.to_telegram_html(), parse_mode=ParseMode.HTML, disable_web_page_preview=False)
            collector.mark_published(deal)
            published += 1
        except Exception:
            log.exception('Не удалось опубликовать: %s', deal.url)
    return published
async def scheduled_scan(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        log.info('Автоматическая проверка скидок')
        count = await publish_deals(context)
        log.info('Опубликовано: %s', count)
    except Exception:
        log.exception('Ошибка автоматической проверки')
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text('🦊 <b>Скидки Вилки запущен!</b>\n\n/scan — проверить новые скидки\n/test — тест канала\n/settings — настройки\n\nАвтоматическая проверка работает сама.', parse_mode=ParseMode.HTML)
async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user):
        await update.effective_message.reply_text('⛔ Команда доступна только владельцу.')
        return
    await update.effective_message.reply_text('🔎 Проверяю источники...')
    try:
        count = await publish_deals(context)
        await update.effective_message.reply_text(f'✅ Готово. Опубликовано: {count}')
    except Exception as exc:
        log.exception('Scan failed')
        await update.effective_message.reply_text('❌ Ошибка сканирования:\n' + safe_html(str(exc)), parse_mode=ParseMode.HTML)
async def test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user):
        await update.effective_message.reply_text('⛔ Команда доступна только владельцу.')
        return
    try:
        await context.bot.send_message(chat_id=channel_value(CHANNEL), text='🔥 <b>ТЕСТОВАЯ СКИДКА</b>\n\n🎁 Пример автоматической публикации\n💰 Цена: <b>39,99 €</b>\n🏪 Магазин: пример магазина\n\n👉 <a href="https://example.com">ЗАБРАТЬ СКИДКУ</a>\n\n#скидка #тест', parse_mode=ParseMode.HTML)
        await update.effective_message.reply_text('✅ Тест опубликован в канале.')
    except Exception as exc:
        log.exception('Test failed')
        await update.effective_message.reply_text('❌ Не удалось отправить тест.\n' + safe_html(str(exc)), parse_mode=ParseMode.HTML)
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user):
        await update.effective_message.reply_text('⛔ Команда доступна только владельцу.')
        return
    await update.effective_message.reply_text(f'⚙️ <b>Настройки</b>\n\nКанал: <code>{safe_html(CHANNEL)}</code>\nИнтервал: <b>{SCAN_INTERVAL // 60} мин</b>\nИсточников: <b>{collector.feed_count}</b>\nМаксимум за проверку: <b>{MAX_POSTS_PER_SCAN}</b>\n\nPepper отключён. Система использует RSS-источники.', parse_mode=ParseMode.HTML)
async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([BotCommand('start', 'запустить бота'), BotCommand('scan', 'проверить скидки'), BotCommand('test', 'тест канала'), BotCommand('settings', 'настройки')])
def main() -> None:
    if not TOKEN:
        raise RuntimeError('Не задана переменная BOT_TOKEN')
    if not CHANNEL:
        raise RuntimeError('Не задана переменная CHANNEL_ID')
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('scan', scan))
    app.add_handler(CommandHandler('test', test))
    app.add_handler(CommandHandler('settings', settings))
    if app.job_queue is None:
        raise RuntimeError('JobQueue недоступен. Проверь requirements.txt')
    app.job_queue.run_repeating(scheduled_scan, interval=SCAN_INTERVAL, first=20, name='automatic_deal_scan')
    log.info('Бот запущен: канал=%s, интервал=%s сек', CHANNEL, SCAN_INTERVAL)
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
if __name__ == '__main__':
    main()
