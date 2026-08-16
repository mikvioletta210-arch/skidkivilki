import json
from pathlib import Path

class SeenDB:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        try:
            self.items=set(json.loads(self.path.read_text(encoding="utf-8")))
        except Exception:
            self.items=set()
    def has(self,url): return url in self.items
    def add(self,url): self.items.add(url)
    def save(self):
        self.path.write_text(json.dumps(list(self.items)[-10000:],ensure_ascii=False),encoding="utf-8")
