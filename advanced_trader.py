import time
import requests
import pandas as pd
import ta
from binance.client import Client
from binance.enums import *
import math

# === AYARLAR ===
API_KEY = "LfPcYddSlhiddvCtcpqvN5XmcW69rBeUR0wMdomsFVioGqee4HvQRMJEEqBWGnD3"
API_SECRET = "WOLjlFThHqbh79HnJOTOHgpwVGF1fiB3fqt7E7ruUkOJVPcrHwWLEhcCMAk2MtPe"
TELEGRAM_TOKEN = "7924482379:AAFm9Iz-2mG-Zc__AvQFVoe2mF3gm7a43oM"
CHAT_ID = "5857863605"
PAIR = "BTCUSDT"  # Takip edilecek coin
INTERVAL = "15m"  # Zaman aralığı
TAKE_PROFIT = 0.05  # %5 kar
STOP_LOSS = 0.02    # %2 zarar
USE_PERCENT = 1.0   # Tüm bakiye ile işlem

# === BAĞLANTILAR ===
client = Client(API_KEY, API_SECRET)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except:
        print("Telegram gönderilemedi.")

def get_klines(symbol):
    try:
        df = pd.DataFrame(client.get_klines(symbol=symbol, interval=INTERVAL, limit=100))
        df = df.iloc[:, 1:6]
        df.columns = ['open', 'high', 'low', 'close', 'volume']
        df = df.astype(float)
        return df
    except Exception as e:
        print(f"Veri alınamadı: {e}")
        return None

def signal_buy(df):
    ichimoku = ta.trend.IchimokuIndicator(high=df['high'], low=df['low'], window1=9, window2=26, window3=52)
    lead_span_a = ichimoku.ichimoku_a().iloc[-1]
    lead_span_b = ichimoku.ichimoku_b().iloc[-1]
    close_price = df['close'].iloc[-1]
    volume = df['volume'].iloc[-1]
    avg_volume = df['volume'].mean()
    atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range().iloc[-1]

    # Sinyal Koşulları:
    if (
        close_price > lead_span_a and
        close_price > lead_span_b and
        volume > avg_volume * 1.2 and
        atr > df['close'].pct_change().std()
    ):
        return True
    return False

def place_buy():
    usdt = float(client.get_asset_balance(asset='USDT')['free'])
    if usdt < 10:
        print("Yetersiz bakiye.")
        return None
    amount = round((usdt * USE_PERCENT) / float(client.get_symbol_ticker(symbol=PAIR)['price']), 6)
    order = client.order_market_buy(symbol=PAIR, quantity=amount)
    entry_price = float(order['fills'][0]['price'])
    send_telegram(f"🟢 ALIM YAPILDI\nCoin: {PAIR}\nFiyat: {entry_price}")
    return entry_price, amount

def place_sell(amount):
    order = client.order_market_sell(symbol=PAIR, quantity=amount)
    sell_price = float(order['fills'][0]['price'])
    send_telegram(f"🔴 SATIM YAPILDI\nFiyat: {sell_price}")
    return sell_price

def trade_loop():
    in_position = False
    entry_price = 0
    amount = 0

    send_telegram("🤖 Bot aktif! İzleniyor...")

    while True:
        df = get_klines(PAIR)
        if df is None:
            time.sleep(60)
            continue

        if not in_position and signal_buy(df):
            entry_price, amount = place_buy()
            if entry_price:
                in_position = True

        elif in_position:
            current_price = float(client.get_symbol_ticker(symbol=PAIR)['price'])

            if current_price >= entry_price * (1 + TAKE_PROFIT):
                place_sell(amount)
                send_telegram("✅ KÂR ALINDI")
                in_position = False

            elif current_price <= entry_price * (1 - STOP_LOSS):
                place_sell(amount)
                send_telegram("⛔ STOP LOSS TETİKLENDİ")
                in_position = False

        time.sleep(60)

 # === BAŞLAT ===
if __name__ == "__main__":
    print("🤖 Bot başlatılıyor...")
    trade_loop()

