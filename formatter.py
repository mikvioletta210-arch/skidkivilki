from html import escape

def money(v):
    return "—" if v is None else f"{v:,.0f}".replace(","," ")+" ₽"

def format_deal(d):
    lines=[f"🐺 <b>{escape(d.title)}</b>","",f"🔥 <b>−{d.discount}%</b>"]
    if d.old_price:
        lines.append(f"💰 Было: <s>{money(d.old_price)}</s>")
    lines.append(f"💸 Сейчас: <b>{money(d.new_price)}</b>")
    if d.store:
        lines.append(f"🛍 {escape(d.store)}")
    if d.description:
        lines += ["",f"📝 {escape(d.description[:300])}"]
    lines += ["","⚡️ Цена и наличие могут измениться.","","Источник: Pepper.ru"]
    return "\n".join(lines)
