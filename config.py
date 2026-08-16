import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    bot_token:str=os.getenv("BOT_TOKEN","")
    channel:str=os.getenv("CHANNEL_USERNAME","@skidkivilki")
    pepper_url:str=os.getenv("PEPPER_URL","https://www.pepper.ru/new")
    auto_post:bool=os.getenv("AUTO_POST","true").lower() in ("1","true","yes","on")
    interval:int=max(5,int(os.getenv("CHECK_INTERVAL","5")))
    min_discount:int=max(0,int(os.getenv("MIN_DISCOUNT","20")))
    max_posts_per_scan:int=max(1,int(os.getenv("MAX_POSTS_PER_SCAN","5")))

settings=Settings()
