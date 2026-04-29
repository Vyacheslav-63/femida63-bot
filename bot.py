import time
import json
import urllib.request
import ssl
import os
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

TOKEN     = os.getenv("TOKEN", "8684491581:AAGqkkxxCZ3O1sCcsWDucpqqzh68RMASXbE")
LAWYER_ID = os.getenv("LAWYER_ID", "415840369")
API       = f"https://api.telegram.org/bot{TOKEN}"
ctx       = ssl.create_default_context()
sessions  = {}
offset    = 0

def api_call(method, data):
    try:
        body = json.dumps(data).encode("utf-8")
        req  = urllib.request.Request(
            f"{API}/{method}", data=body,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        return json.loads(resp.read())
    except Exception as e:
        print(f"[ERR] {method}: {e}")
        return None

def send(chat_id, text, kb=None):
    data = {"chat_id": str(chat_id), "text": text, "parse_mode": "HTML"}
    if kb:
        data["reply_markup"] = json.dumps(kb)
    api_call("sendMessage", data)

def answer_cb(cb_id):
    api_call("answerCallbackQuery", {"callback_query_id": cb_id})

def keyboard():
    return {"inline_keyboard": [
        [{"text": "⚖️ Лизинговый спор",           "callback_data": "leasing"}],
        [{"text": "💼 Взыскание долга / Арбитраж", "callback_data": "arbitrage"}],
        [{"text": "📊 Налоговый спор",             "callback_data": "tax"}],
        [{"text": "🏚 Банкротство",                "callback_data": "bankruptcy"}],
        [{"text": "🏛 Суд общей юрисдикции",        "callback_data": "courts"}],
        [{"text": "❓ Другой вопрос",              "callback_data": "other"}],
    ]}

NAMES = {
    "leasing":    "Лизинговый спор",
    "arbitrage":  "Взыскание долга / Арбитраж",
    "tax":        "Налоговый спор",
    "bankruptcy": "Банкротство",
    "courts":     "Суд общей юрисдикции",
    "other":      "Другой вопрос",
}

ANSWERS = {
    "leasing": (
        "Ключевой документ — <b>Постановление Пленума ВАС РФ №17</b>.\n\n"
        "Лизинговые компании часто незаконно включают будущие платежи в расчёт долга "
        "(запрещено п. 3.6) или занижают цену продажи изъятого имущества. "
        "В 70% дел расчёт сальдо содержит ошибки в пользу лизинговой компании.\n\n"
        "🔍 <b>Уточните:</b> какую сумму предъявляет компания и когда расторгли договор?"
    ),
    "arbitrage": (
        "Для взыскания через <b>арбитражный суд</b> сначала направляется претензия (30 дней).\n\n"
        "Затем иск с расчётом долга, процентов по <b>ст. 395 ГК РФ</b> и неустойки. "
        "Одновременно можно арестовать счета должника. Срок рассмотрения — 3–4 месяца.\n\n"
        "🔍 <b>Уточните:</b> есть ли договор и первичные документы (акты, счета-фактуры)?"
    ),
    "tax": (
        "Главный инструмент защиты — <b>расчётный метод</b> по ПП Президиума ВАС №2341/12: "
        "даже при сомнительных контрагентах расходы принимаются по рыночным ценам.\n\n"
        "В нашей практике есть дело с доначислением 285 млн руб., дошедшее до Верховного суда РФ.\n\n"
        "🔍 <b>Уточните:</b> что доначислила ИФНС и на какой стадии дело?"
    ),
    "bankruptcy": (
        "В банкротстве критично действовать быстро.\n\n"
        "Если вы <b>кредитор</b> — включиться в реестр нужно не позднее 2 месяцев с публикации. "
        "Если <b>должник</b> — важно оценить риски субсидиарной ответственности руководителя.\n\n"
        "🔴 Срок включения в реестр — 2 месяца с публикации!\n\n"
        "🔍 <b>Уточните:</b> вы должник или кредитор? Процедура уже открыта?"
    ),
    "courts": (
        "В судах общей юрисдикции важно подготовить доказательную базу <b>до</b> подачи иска — "
        "апелляция крайне редко принимает новые доказательства.\n\n"
        "Ведём дела в судах Самарской области по семейным, жилищным и гражданским спорам.\n\n"
        "🔍 <b>Уточните:</b> тип спора и на какой стадии находится дело?"
    ),
    "other": (
        "Опишите вашу ситуацию подробнее — юрист Femida63 изучит детали и предложит решение.\n\n"
        "Специализируемся на лизинговых спорах, арбитраже, взыскании долгов и налоговых делах."
    ),
}

def new_session(uname):
    return {"state": "cat", "cat": "", "problem": "", "name": "",
            "phone": "", "tg": f"@{uname}" if uname else "—",
            "time": datetime.now().strftime("%d.%m.%Y %H:%M")}

def notify_lawyer(s):
    text = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏛 <b>НОВАЯ ЗАЯВКА — Femida63</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 <b>Тип дела:</b> {NAMES.get(s['cat'], '—')}\n\n"
        f"💬 <b>Ситуация клиента:</b>\n<i>{s['problem']}</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>КЛИЕНТ:</b>\n"
        f"  Имя: <b>{s['name']}</b>\n"
        f"  Телефон: <b>{s['phone']}</b>\n"
        f"  Telegram: {s['tg']}\n"
        f"  Время: {s['time']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    send(LAWYER_ID, text)

def handle_text(chat_id, text, uname, fname):
    if chat_id not in sessions:
        sessions[chat_id] = new_session(uname)
    s  = sessions[chat_id]
    st = s["state"]

    if text.startswith("/start"):
        sessions[chat_id] = new_session(uname)
        send(chat_id,
             f"Здравствуйте, <b>{fname}</b>! 👋\n\n"
             "Я ассистент юридической компании <b>Femida63</b>.\n"
             "Специализируемся на лизинговых спорах, арбитраже и взыскании долгов.\n\n"
             "Выберите тип вашего вопроса:",
             keyboard())
        return

    if text.startswith("/help"):
        send(chat_id, "🏛 <b>Femida63</b> — юридическая помощь\n\n"
             "/start — начать консультацию\n📞 +7 (929) 713-13-08\n🌐 femida63.ru")
        return

    if st == "cat":
        send(chat_id, "Пожалуйста, выберите категорию из меню выше 👆", keyboard())
    elif st == "describe":
        s["problem"] = text
        s["state"]   = "name"
        send(chat_id, "⏳ Анализирую вашу ситуацию...")
        time.sleep(1)
        send(chat_id, f"📋 <b>Предварительный анализ:</b>\n\n{ANSWERS[s['cat']]}")
        time.sleep(0.5)
        send(chat_id, "Чтобы юрист мог с вами связаться — как вас зовут? 👤")
    elif st == "name":
        s["name"]  = text
        s["state"] = "phone"
        send(chat_id, f"Отлично, <b>{text}</b>! 👍\n\n"
             "Введите номер телефона:\n<i>Пример: +7 912 345-67-89</i>")
    elif st == "phone":
        s["phone"] = text
        s["state"] = "done"
        send(chat_id,
             "✅ <b>Заявка принята!</b>\n\n"
             "Юрист Femida63 свяжется с вами в течение <b>1 часа</b> "
             "в рабочее время (Пн–Пт 9:00–18:00).\n\n"
             "Если срочно — звоните: 📞 <b>+7 (929) 713-13-08</b>")
        print(f"✅ Заявка: {s['name']} | {s['phone']} | {s['tg']}")
        notify_lawyer(s)
    elif st == "done":
        send(chat_id, "Ваша заявка уже передана юристу. Ожидайте звонка!\n\nДля нового вопроса: /start")

def handle_button(chat_id, cb_id, data, uname):
    answer_cb(cb_id)
    if chat_id not in sessions:
        sessions[chat_id] = new_session(uname)
    sessions[chat_id]["cat"]   = data
    sessions[chat_id]["state"] = "describe"
    send(chat_id, f"✅ <b>{NAMES[data]}</b>\n\nОпишите ситуацию подробнее — "
         "чем больше деталей, тем точнее анализ:")

# ── Телеграм-бот в фоновом потоке ─────────────────────────────────────────────
def run_bot():
    global offset
    print("Проверяем подключение к Telegram...")
    result = api_call("getMe", {})
    if result and result.get("ok"):
        print(f"✅ Бот подключён: @{result['result']['username']}")
    else:
        print("❌ Ошибка подключения с Telegram!")
        return

    send(LAWYER_ID, f"🤖 Femida63 Bot запущен!\nВремя: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print("✅ Уведомление юристу отправлено. Ожидаем сообщения...\n")

    while True:
        try:
            result = api_call("getUpdates", {"offset": offset, "timeout": 25})
            if not result or not result.get("ok"):
                time.sleep(3)
                continue
            for u in result["result"]:
                offset = u["update_id"] + 1
                if u.get("message") and u["message"].get("text"):
                    m     = u["message"]
                    cid   = m["chat"]["id"]
                    txt   = m["text"]
                    uname = m["from"].get("username", "")
                    fname = m["from"].get("first_name", "друг")
                    print(f"[{cid}] {fname}: {txt}")
                    handle_text(cid, txt, uname, fname)
                if u.get("callback_query"):
                    cb    = u["callback_query"]
                    cid   = cb["message"]["chat"]["id"]
                    uname = cb["from"].get("username", "")
                    print(f"[{cid}] кнопка: {cb['data']}")
                    handle_button(cid, cb["id"], cb["data"], uname)
        except Exception as e:
            print(f"[ERR] {e}")
            time.sleep(5)

# ── HTTP-сервер в ГЛАВНОМ потоке (требование Render) ──────────────────────────
class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Femida63 Bot is running!")
    def log_message(self, *args):
        pass

PORT = int(os.getenv("PORT", 10000))
print(f"Запускаем веб-сервер на порту {PORT}...")

# Бот — в фоне, HTTP — главный поток
threading.Thread(target=run_bot, daemon=True).start()

print(f"✅ HTTP-сервер слушает порт {PORT}")
HTTPServer(("0.0.0.0", PORT), Health).serve_forever()
