import asyncio, re, sqlite3, random, os
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import JoinChannelRequest

API_ID = int(os.environ.get('API_ID', '0'))
API_HASH = os.environ.get('API_HASH', '')
PHONE = os.environ.get('PHONE', '')
ADMIN_ID = 8045154977

conn = sqlite3.connect('leads.db')
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, chat TEXT, message TEXT, country TEXT, lang TEXT, sent TEXT, status TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS chats (username TEXT PRIMARY KEY, country TEXT)')
conn.commit()

HOURLY_LIMIT = 40
client = TelegramClient('bot_session', API_ID, API_HASH)
hourly_sent = 0
hour_start = datetime.now()

SEARCH_QUERIES = [
    "русские в Дубае", "Дубай русские", "Russians in Dubai", "Dubai crypto", "Dubai P2P",
    "русские в Турции", "Стамбул русские", "Russians in Istanbul", "Turkey crypto",
    "русские в Грузии", "Тбилиси русские", "Tbilisi expats", "Georgia crypto",
    "русские в Армении", "Ереван русские", "Yerevan expats", "Armenia crypto",
    "Москва крипта", "crypto OTC", "P2P exchange", "buy crypto cash", "sell USDT",
]

TRIGGERS = [
    r'обменять?\s*(?:доллар|евро|лир|рубл|крипт|usdt|btc|eth)',
    r'нужны\s*(?:наличны|кэш|доллары|евро|лиры)',
    r'(?:продать|куплю)\s*(?:доллар|евро|крипту|usdt|btc)',
    r'\b(?:usdt|btc|eth)\b',
    r'(?:exchange|swap|trade|buy|sell)\s*(?:crypto|btc|usdt)',
    r'(?:need|want)\s*(?:cash|exchange|p2p)',
]

MESSAGES = {
    'turkey': {'ru': "USDT Global Net\n\nДобрый день. Работаем в Турции: Стамбул, Анталья, Алания, Бодрум и др. Выезд курьера.\nМин: $500. Курс Binance.\nЗаявка: @CryptoXExchanger_bot\n\nСумма и направление?",
               'en': "USDT Global Net\n\nHello. We operate in Turkey: Istanbul, Antalya, Alanya, Bodrum etc.\nCourier available.\nMin: $500.\nOrder: @CryptoXExchanger_bot\n\nAmount?"},
    'uae': {'ru': "USDT Global Net\n\nДобрый день. Работаем в ОАЭ: Дубай. Выезд курьера.\nМин: $500.\nЗаявка: @CryptoXExchanger_bot\n\nСумма?",
            'en': "USDT Global Net\n\nHello. UAE: Dubai. Courier available.\nMin: $500.\nOrder: @CryptoXExchanger_bot\n\nAmount?"},
    'georgia': {'ru': "USDT Global Net\n\nДобрый день. Грузия: Тбилиси. Выезд курьера.\nМин: $500.\nЗаявка: @CryptoXExchanger_bot",
                'en': "USDT Global Net\n\nHello. Georgia: Tbilisi. Courier.\nMin: $500.\nOrder: @CryptoXExchanger_bot"},
    'armenia': {'ru': "USDT Global Net\n\nДобрый день. Армения. Выезд курьера.\nМин: $500.\nЗаявка: @CryptoXExchanger_bot",
                'en': "USDT Global Net\n\nHello. Armenia. Courier.\nMin: $500.\nOrder: @CryptoXExchanger_bot"},
    'russia': {'ru': "USDT Global Net\n\nДобрый день. Россия: 30+ городов. Выезд курьера.\nМин: $500.\nЗаявка: @CryptoXExchanger_bot",
               'en': "USDT Global Net\n\nHello. Russia: 30+ cities. Courier.\nMin: $500.\nOrder: @CryptoXExchanger_bot"},
    'unknown': {'ru': "USDT Global Net\n\nДобрый день. Работаем в РФ, Турции, Грузии, Армении, ОАЭ.\nМин: $500.\nЗаявка: @CryptoXExchanger_bot\n\nВаш город?",
                'en': "USDT Global Net\n\nHello. Russia, Turkey, Georgia, Armenia, UAE.\nMin: $500.\nOrder: @CryptoXExchanger_bot\n\nYour city?"},
}

COUNTRY_MAP = {
    'uae': ['dubai', 'дубай', 'оаэ', 'uae', 'dxb', 'aed'],
    'turkey': ['istanbul', 'стамбул', 'antalya', 'турци', 'turkey', 'try'],
    'georgia': ['tbilisi', 'тбилиси', 'batumi', 'грузи', 'georgia', 'gel'],
    'armenia': ['yerevan', 'ереван', 'армени', 'armenia', 'amd'],
    'russia': ['moscow', 'москва', 'россия', 'russia', 'rub'],
}

def detect_country(text, chat=''):
    t = (text + ' ' + chat).lower()
    for c, kw in COUNTRY_MAP.items():
        if any(k in t for k in kw): return c
    return 'unknown'

def detect_lang(text):
    return 'ru' if len(re.findall(r'[а-яё]', text)) > len(re.findall(r'[a-z]', text)) else 'en'

async def safe_send(user_id, text):
    global hourly_sent, hour_start
    if (datetime.now() - hour_start).seconds > 3600:
        hourly_sent = 0; hour_start = datetime.now()
    if hourly_sent >= HOURLY_LIMIT: return False
    await asyncio.sleep(random.randint(30, 90))
    try:
        await client.send_message(user_id, text)
        hourly_sent += 1
        return True
    except: return False

async def search_and_join():
    for q in SEARCH_QUERIES:
        try:
            r = await client(SearchRequest(q=q, limit=10))
            for c in r.chats:
                u = getattr(c, 'username', None)
                if u and getattr(c, 'participants_count', 0) > 200:
                    cursor.execute('SELECT username FROM chats WHERE username=?', (f'@{u}',))
                    if not cursor.fetchone():
                        cursor.execute('INSERT OR IGNORE INTO chats VALUES (?,?)', (f'@{u}', detect_country(getattr(c,'title',''))))
                        conn.commit()
                        try: await client(JoinChannelRequest(u))
                        except: pass
            await asyncio.sleep(3)
        except: await asyncio.sleep(5)

@client.on(events.NewMessage())
async def handler(event):
    if not event.text: return
    chat = event.chat
    cu = getattr(chat, 'username', None)
    if not cu: return
    cursor.execute('SELECT username FROM chats WHERE username=?', (f'@{cu}',))
    if not cursor.fetchone(): return
    if not any(re.search(p, event.text.lower()) for p in TRIGGERS): return
    s = event.sender
    uid = s.id
    uname = f"@{s.username}" if s.username else f"id{uid}"
    country = detect_country(event.text, chat.title or '')
    lang = detect_lang(event.text)
    cursor.execute('INSERT INTO leads (user_id, username, chat, message, country, lang, sent, status) VALUES (?,?,?,?,?,?,?,?)',
                  (uid, uname, f'@{cu}', event.text, country, lang, datetime.now().isoformat(), 'sent'))
    conn.commit()
    msg = MESSAGES.get(country, MESSAGES['unknown']).get(lang, MESSAGES['unknown']['en'])
    await safe_send(uid, msg)

async def main():
    await client.start(phone=PHONE)
    print("Bot started")
    asyncio.create_task(auto_loop())
    await client.run_until_disconnected()

async def auto_loop():
    while True:
        await search_and_join()
        await asyncio.sleep(21600)

if __name__ == '__main__':
    asyncio.run(main())
