import asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from config import settings
from sources.pepper import PepperSource
from database import SeenDB
from publisher import Publisher

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
bot=Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp=Dispatcher(); db=SeenDB("data/seen.json")
source=PepperSource(settings.pepper_url, settings.min_discount)
publisher=Publisher(bot, settings.channel)

async def scan():
    deals=await source.fetch_new(); posted=0
    for d in deals[:settings.max_posts_per_scan]:
        if db.has(d.url): continue
        try:
            await publisher.publish(d); db.add(d.url); posted+=1; await asyncio.sleep(2)
        except Exception: logging.exception("publish failed")
    db.save(); return posted,len(deals)

@dp.message(CommandStart())
async def start(m:Message):
    await m.answer("🐺 <b>Скидки Вилки</b> запущен.\n\n/scan — проверить скидки\n/test — тест канала\n/settings — настройки")

@dp.message(Command("scan"))
async def scan_cmd(m:Message):
    msg=await m.answer("🔎 Проверяю новые скидки…")
    try:
        posted,found=await scan()
        await msg.edit_text(f"✅ Готово. Найдено: <b>{found}</b>. Опубликовано: <b>{posted}</b>.")
    except Exception as e:
        logging.exception("scan failed")
        await msg.edit_text(f"❌ Ошибка: <code>{str(e)[:900]}</code>")

@dp.message(Command("test"))
async def test(m:Message):
    try:
        await bot.send_message(settings.channel,"🐺 <b>СКИДКИ ВИЛКИ</b>\n\nКанал подключён правильно ✅")
        await m.answer("✅ Тест опубликован в канале.")
    except Exception as e:
        await m.answer(f"❌ Не получилось опубликовать. Проверь права бота в канале.\n<code>{str(e)[:900]}</code>")

@dp.message(Command("settings"))
async def settings_cmd(m:Message):
    await m.answer(f"📢 Канал: <code>{settings.channel}</code>\n🔥 Минимальная скидка: <b>{settings.min_discount}%</b>\n⏱ Интервал: <b>{settings.interval} мин.</b>\n📦 Максимум за проверку: <b>{settings.max_posts_per_scan}</b>")

async def worker():
    await asyncio.sleep(10)
    while True:
        try:
            if settings.auto_post:
                await scan()
        except Exception:
            logging.exception("automatic scan failed")
        await asyncio.sleep(settings.interval*60)

async def main():
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is missing in Railway Variables")
    asyncio.create_task(worker())
    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())
