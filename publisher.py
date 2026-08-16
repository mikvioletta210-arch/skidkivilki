from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from formatter import format_deal

class Publisher:
    def __init__(self,bot,channel):
        self.bot,self.channel=bot,channel

    async def publish(self,d):
        kb=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 ЗАБРАТЬ СКИДКУ",url=d.url)]
        ])
        text=format_deal(d)
        if d.image:
            try:
                await self.bot.send_photo(self.channel,d.image,caption=text[:1024],reply_markup=kb)
                return
            except Exception:
                pass
        await self.bot.send_message(self.channel,text,reply_markup=kb,disable_web_page_preview=False)
