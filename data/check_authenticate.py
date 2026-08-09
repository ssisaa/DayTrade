import ccxt
import os

API_KEY = 'Tj7WqjAQcHpLFx6jzew2GA'
API_SECRET = 'CfpPVQvVAAwGwGTNWpR9AT'

exchange = ccxt.cryptocom({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "enableRateLimit": True,
})

print("Exchange:", exchange.id)
print("API key loaded:", bool(exchange.apiKey))
print("Secret loaded:", bool(exchange.secret))

try:
    balance = exchange.fetch_balance()
    print("Authentication SUCCESS")
    print("USDT:", balance["USDT"]["free"])
    print("EGLD:", balance["EGLD"]["free"])

except Exception as e:
    print("Authentication FAILED")
    print(type(e).__name__)
    print(str(e))