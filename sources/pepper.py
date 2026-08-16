import re, aiohttp
from dataclasses import dataclass
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlsplit,urlunsplit

@dataclass
class Deal:
    url:str
    title:str
    new_price:float|None
    old_price:float|None
    discount:int
    store:str|None
    description:str
    image:str|None

def clean(x):
    return re.sub(r"\s+"," ",BeautifulSoup(x or "","html.parser").get_text(" ",strip=True)).strip()

def price(x):
    m=re.search(r"(\d[\d\s]*(?:[.,]\d{1,2})?)\s*₽",(x or "").replace("\xa0"," "))
    if not m: return None
    try: return float(m.group(1).replace(" ","").replace(",","."))
    except: return None

def norm(u):
    p=urlsplit(u)
    return urlunsplit((p.scheme,p.netloc,p.path,"",""))

class PepperSource:
    def __init__(self,feed,min_discount):
        self.feed,self.min=feed,min_discount

    async def fetch_new(self):
        headers={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1"}
        async with aiohttp.ClientSession(headers=headers,timeout=aiohttp.ClientTimeout(total=30)) as s:
            async with s.get(self.feed) as r:
                r.raise_for_status()
                html=await r.text(errors="ignore")
            soup=BeautifulSoup(html,"html.parser")
            urls=[]
            for a in soup.find_all("a",href=True):
                u=norm(urljoin(self.feed,a["href"]))
                if "/deals/" in u and u not in urls:
                    urls.append(u)
                if len(urls)>=40: break

            out=[]
            for u in urls:
                try:
                    async with s.get(u) as r:
                        page=await r.text(errors="ignore")
                    sp=BeautifulSoup(page,"html.parser")
                    ogt=sp.find("meta",property="og:title")
                    ogd=sp.find("meta",property="og:description")
                    ogi=sp.find("meta",property="og:image")
                    title=clean(ogt.get("content","")) if ogt else (clean(sp.title.get_text()) if sp.title else "")
                    desc=clean(ogd.get("content","")) if ogd else ""
                    img=ogi.get("content") if ogi else None
                    text=desc+" "+clean(sp.get_text(" ",strip=True))[:10000]
                    vals=[price(m.group(0)) for m in re.finditer(r"\d[\d\s]*(?:[.,]\d{1,2})?\s*₽",text)]
                    vals=list(dict.fromkeys(v for v in vals if v))
                    if len(vals)>=2 and max(vals[:2])>min(vals[:2]):
                        old,new=max(vals[:2]),min(vals[:2])
                    else:
                        old,new=None,(vals[0] if vals else None)
                    pm=re.search(r"(\d{1,3})\s*%",text)
                    disc=int(pm.group(1)) if pm else (round((1-new/old)*100) if old and new else 0)
                    if new and disc>=self.min:
                        out.append(Deal(u,title[:220],new,old,disc,None,desc[:350],img))
                except Exception:
                    continue
            return sorted(out,key=lambda d:d.discount,reverse=True)
