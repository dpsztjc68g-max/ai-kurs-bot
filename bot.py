# -*- coding: utf-8 -*-
"""
«Жасанды интеллект курсы» — Telegram сату боты (Дамеш Тауасарова)

Қосымша кітапхана керек емес: тек Python 3.9+.
Іске қосу:  python3 bot.py
Баптаулар төмендегі CONFIG бөлімінде немесе хостингтің "Environment variables" бөлімінде.

Жұмыс реті:
  Клиент /start → мәзір → «Курсты сатып алу» → Kaspi деректері → «✅ Төледім»
  → чектің фотосын жібереді → чек төлем тобына барады («✅ Растау» / «❌ Бас тарту»)
  → «Растау» басылса: бот клиентке курс тобына БІР РЕТТІК сілтеме + бонус PDF жібереді.
"""
import json
import os
import time
import uuid
import urllib.request
import urllib.parse
import urllib.error

# ============================ CONFIG ============================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")                # BotFather берген токен
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")        # «Жасанды интеллект курс төлемі» тобының ID-і (минуспен басталады)
COURSE_CHAT_ID = os.getenv("COURSE_CHAT_ID", "")      # «Жасанды интеллект курс» тобының ID-і (минуспен басталады)
KASPI_PHONE = os.getenv("KASPI_PHONE", "8 705 184 15 56")
KASPI_NAME = os.getenv("KASPI_NAME", "Аякоз А.")
PRICE = os.getenv("PRICE", "4 990 ₸")
OLD_PRICE = os.getenv("OLD_PRICE", "15 000 ₸")
MANAGER = os.getenv("MANAGER", "@Damesh2001")
SITE_URL = os.getenv("SITE_URL", "")                  # сайттың сілтемесі (жұмыстар үшін)
INSTAGRAM = "https://instagram.com/damesh_tauassarova"
BONUS_PDF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Kurs-bonustary.pdf")
GIFT_LINKS = os.getenv("GIFT_LINKS", "")              # сыйлық каналдарының сілтемелері, әр жолы бөлек (міндетті емес)
# ================================================================

API = f"https://api.telegram.org/bot{BOT_TOKEN}/"
waiting_receipt = set()      # чек жіберуі керек клиенттер
bonus_file_id = None         # PDF бір рет жүктелген соң қайта қолданылады


# ---------------------------- Telegram API ----------------------------
def call(method, data=None, files=None, timeout=60):
    url = API + method
    try:
        if files:
            boundary = uuid.uuid4().hex
            body = b""
            for k, v in (data or {}).items():
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, ensure_ascii=False)
                body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n").encode()
            for k, path in files.items():
                with open(path, "rb") as f:
                    content = f.read()
                fname = os.path.basename(path)
                body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{fname}\"\r\n"
                         f"Content-Type: application/pdf\r\n\r\n").encode() + content + b"\r\n"
            body += f"--{boundary}--\r\n".encode()
            req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        else:
            payload = json.dumps(data or {}, ensure_ascii=False).encode()
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode())
        except Exception:
            err = {"description": str(e)}
        print("API қатесі:", method, err)
        return {"ok": False, **err}
    except Exception as e:
        print("Желі қатесі:", method, e)
        return {"ok": False, "description": str(e)}


def send(chat_id, text, kb=None):
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb:
        data["reply_markup"] = {"inline_keyboard": kb}
    return call("sendMessage", data)


def btn(text, data=None, url=None):
    b = {"text": text}
    if url:
        b["url"] = url
    else:
        b["callback_data"] = data
    return b


# ---------------------------- Мәтіндер ----------------------------
def main_menu():
    rows = [
        [btn("📚 Курс бағдарламасы", "program")],
        [btn("🎬 Менің жұмыстарым", "works")],
        [btn(f"💰 Курсты сатып алу — {PRICE}", "buy")],
        [btn("❓ Жиі қойылатын сұрақтар", "faq")],
        [btn("👩‍💻 Менеджерге жазу", "manager")],
    ]
    return rows


def back_buy():
    return [[btn(f"💰 Курсты сатып алу — {PRICE}", "buy")], [btn("⬅️ Мәзірге оралу", "menu")]]


WELCOME = (
    "Сәлеметсіз бе! 👋 Мен — <b>Дамеш Тауасарова</b>, жасанды интеллект маманы.\n\n"
    "🎬 <b>«Жасанды интеллект курсы»</b> — телефонмен-ақ кино деңгейіндегі видео, "
    "AI мульт, нейрофото және контент жасауды үйренесіз.\n\n"
    "✅ 16 практикалық сабақ\n"
    "✅ Шексіз доступ\n"
    "✅ Нөлден, қадам-қадаммен\n\n"
    f"💰 Бүгінгі баға: <s>{OLD_PRICE}</s> <b>{PRICE}</b>\n\n"
    "Төмендегі бөлімді таңдаңыз 👇"
)

LESSONS = [
    "ChatGPT: баптау және тегін қолдану", "Grok", "Gemini",
    "Нейрофото: бір фотодан ондаған образ", "Midjourney", "Seedream және Meta AI",
    "Flow", "Kling AI", "VeoSeeBot", "Syntx AI", "Вау-эффект видеолар",
    "AI мультфильм және сериал", "Бизнеске жарнама видео", "Suno: ЖИ ән және дыбыстау",
    "Монтаж және ЖИ шақырту", "TikTok, Instagram: монетизация",
]

PROGRAM = "📚 <b>Курс бағдарламасы — 16 сабақ</b>\n\n" + "\n".join(
    f"{i}. {name}" for i, name in enumerate(LESSONS, 1)
) + "\n\n🎁 <b>Сыйлықтар:</b> тапсырыс алу шаблоны, 30 дайын видео промпт, промпт-каналдар"

FAQ = (
    "❓ <b>Жиі қойылатын сұрақтар</b>\n\n"
    "<b>Мен нөлденмін, үлгеремін бе?</b>\nИә. Курс нөлден бастайтындарға арналған, бәрі қадам-қадаммен.\n\n"
    "<b>Компьютер керек пе?</b>\nЖоқ, телефонның өзі жеткілікті.\n\n"
    "<b>Сатып алған соң не болады?</b>\nТөлеп, чекті жібересіз. Тексерілген соң курс тобына сілтеме келеді.\n\n"
    "<b>Сабақтарды қашанға дейін көремін?</b>\nШексіз. Кез келген уақытта қайта көре аласыз.\n\n"
    "<b>AI құралдары ақылы ма?</b>\nТегін нұсқаларын тиімді қолдануды үйретемін."
)


def buy_text():
    return (
        f"💰 <b>«Жасанды интеллект курсы»</b>\n"
        f"Баға: <s>{OLD_PRICE}</s> <b>{PRICE}</b>\n\n"
        f"💳 <b>Kaspi аударым:</b>\n"
        f"Нөмір: <code>{KASPI_PHONE}</code>\n"
        f"Алушы: {KASPI_NAME}\n"
        f"Сома: {PRICE}\n\n"
        "Төлеген соң «✅ Төледім» батырмасын басып, чектің скриншотын жіберіңіз."
    )


# ---------------------------- Әрекеттер ----------------------------
def show_menu(chat_id):
    send(chat_id, WELCOME, main_menu())


def on_callback(cq):
    data = cq.get("data", "")
    user = cq["from"]
    chat_id = cq["message"]["chat"]["id"]
    call("answerCallbackQuery", {"callback_query_id": cq["id"]})

    if data == "menu":
        show_menu(chat_id)
    elif data == "program":
        send(chat_id, PROGRAM, back_buy())
    elif data == "works":
        kb = []
        if SITE_URL:
            kb.append([btn("🎬 Жұмыстарымды көру", url=SITE_URL)])
        kb.append([btn("📸 Instagram", url=INSTAGRAM)])
        kb += back_buy()
        send(chat_id, "🎬 <b>Менің AI жұмыстарым</b>\n\nВидеоларды жасанды интеллектпен өзім жасадым. "
                      "Курста дәл осылай жасауды үйренесіз 👇", kb)
    elif data == "faq":
        send(chat_id, FAQ, back_buy())
    elif data == "manager":
        send(chat_id, f"👩‍💻 Сұрағыңыз болса, жазыңыз: {MANAGER}", [[btn("⬅️ Мәзірге оралу", "menu")]])
    elif data == "buy":
        send(chat_id, buy_text(), [[btn("✅ Төледім", "paid")], [btn("⬅️ Мәзірге оралу", "menu")]])
    elif data == "paid":
        waiting_receipt.add(user["id"])
        send(chat_id, "📎 Чектің <b>скриншотын</b> осында жіберіңіз (фото немесе файл).")
    elif data.startswith("ok:") or data.startswith("no:"):
        handle_decision(cq, data)


def on_receipt(msg):
    """Клиент чек жіберді → төлем тобына жібереміз."""
    user = msg["from"]
    uid = user["id"]
    name = (user.get("first_name", "") + " " + user.get("last_name", "")).strip()
    uname = f"@{user['username']}" if user.get("username") else "username жоқ"
    caption = (f"🧾 <b>Жаңа чек</b>\nКлиент: {name} ({uname})\nID: <code>{uid}</code>\nСома: {PRICE}\n\n"
               "Kaspi-ден ақша түскенін тексеріңіз 👇")
    kb = {"inline_keyboard": [[btn("✅ Растау", f"ok:{uid}"), btn("❌ Бас тарту", f"no:{uid}")]]}
    fwd = call("copyMessage", {"chat_id": ADMIN_CHAT_ID, "from_chat_id": msg["chat"]["id"], "message_id": msg["message_id"]})
    call("sendMessage", {"chat_id": ADMIN_CHAT_ID, "text": caption, "parse_mode": "HTML", "reply_markup": kb,
                         **({"reply_to_message_id": fwd["result"]["message_id"]} if fwd.get("ok") else {})})
    waiting_receipt.discard(uid)
    send(uid, "✅ Чегіңіз қабылданды! Төлем тексерілген соң курс сілтемесі осында келеді ⏳")


def send_bonus(uid):
    global bonus_file_id
    if not os.path.exists(BONUS_PDF):
        return
    if bonus_file_id:
        call("sendDocument", {"chat_id": uid, "document": bonus_file_id, "caption": "🎁 Бонус: тапсырыс алу шаблоны + 30 промпт"})
        return
    r = call("sendDocument", {"chat_id": uid, "caption": "🎁 Бонус: тапсырыс алу шаблоны + 30 промпт"},
             files={"document": BONUS_PDF})
    if r.get("ok"):
        bonus_file_id = r["result"]["document"]["file_id"]


def handle_decision(cq, data):
    action, uid = data.split(":", 1)
    uid = int(uid)
    admin = cq["from"].get("first_name", "Әкімші")
    m = cq["message"]
    if action == "ok":
        link = call("createChatInviteLink", {"chat_id": COURSE_CHAT_ID, "member_limit": 1,
                                             "name": f"client {uid}"})
        if not link.get("ok"):
            send(m["chat"]["id"], "⚠️ Сілтеме жасалмады. Бот курс тобында әкімші ме? "
                                  f"Қате: {link.get('description', '')}")
            return
        url = link["result"]["invite_link"]
        gifts = ""
        if GIFT_LINKS.strip():
            gifts = "\n\n🎁 <b>Сыйлық каналдар:</b>\n" + "\n".join(l.strip() for l in GIFT_LINKS.splitlines() if l.strip())
        send(uid, "🎉 <b>Төлеміңіз расталды! Курсқа қош келдіңіз!</b>\n\n"
                  "📚 Сабақтарға кіру (сілтеме тек сізге, бір рет қана жұмыс істейді):" + gifts,
             [[btn("📚 Курс тобына кіру", url=url)]])
        send_bonus(uid)
        status = f"✅ Расталды ({admin}). Сілтеме жіберілді."
    else:
        send(uid, "❌ Өкінішке қарай, төлеміңіз табылмады.\n"
                  f"Қате болса, менеджерге жазыңыз: {MANAGER}", [[btn("💰 Қайта төлеу", "buy")]])
        status = f"❌ Бас тартылды ({admin})."
    call("editMessageText", {"chat_id": m["chat"]["id"], "message_id": m["message_id"],
                             "text": m.get("text", "") + "\n\n" + status})


def on_message(msg):
    chat = msg["chat"]
    text = msg.get("text", "") or ""
    # Топтың ID-ін білу үшін: топта /id деп жазыңыз
    if text.startswith("/id"):
        send(chat["id"], f"Бұл чаттың ID-і: <code>{chat['id']}</code>")
        return
    if chat["type"] != "private":
        return
    uid = msg["from"]["id"]
    if text.startswith("/start"):
        show_menu(chat["id"])
        return
    if uid in waiting_receipt and ("photo" in msg or "document" in msg):
        on_receipt(msg)
        return
    if "photo" in msg or "document" in msg:
        send(chat["id"], "Чек жіберу үшін алдымен «💰 Курсты сатып алу» → «✅ Төледім» батырмасын басыңыз 🙂", main_menu())
        return
    show_menu(chat["id"])


def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN жоқ! Баптауларды толтырыңыз.")
        return
    me = call("getMe")
    print("Бот іске қосылды:", me.get("result", {}).get("username"))
    call("deleteWebhook", {})
    offset = 0
    while True:
        res = call("getUpdates", {"offset": offset, "timeout": 50,
                                  "allowed_updates": ["message", "callback_query"]}, timeout=70)
        if not res.get("ok"):
            time.sleep(3)
            continue
        for upd in res["result"]:
            offset = upd["update_id"] + 1
            try:
                if "callback_query" in upd:
                    on_callback(upd["callback_query"])
                elif "message" in upd:
                    on_message(upd["message"])
            except Exception as e:
                print("Қате:", e)


if __name__ == "__main__":
    main()
