#!/usr/bin/env python3
"""
Comprueba qué credenciales de redes sociales están configuradas.

Uso:
    cp .env.example .env   # y rellena lo que vayas a usar
    export $(grep -v '^#' .env | xargs)
    python check_credentials.py

No requiere red ni conexión a las APIs: solo mira las variables de
entorno, igual que hacen los adaptadores de stegstr.
"""
import os

PLATFORMS = {
    "Discord": ["DISCORD_WEBHOOK_URL"],
    "Imgur": ["IMGUR_CLIENT_ID"],
    "Telegram": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
    "Reddit": ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_PASSWORD"],
    "Instagram": ["INSTAGRAM_BUSINESS_ACCOUNT_ID", "META_PAGE_ACCESS_TOKEN"],
    "Twitter/X": [
        "TWITTER_BEARER_TOKEN", "TWITTER_API_KEY", "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET",
    ],
    "WhatsApp": ["WHATSAPP_BUSINESS_PHONE_ID", "WHATSAPP_ACCESS_TOKEN", "WHATSAPP_RECIPIENT_PHONE"],
}

print(f"{'Plataforma':<12} {'Estado':<10} Detalle")
print("-" * 70)
for platform, required_vars in PLATFORMS.items():
    missing = [v for v in required_vars if not os.environ.get(v)]
    if not missing:
        print(f"{platform:<12} {'✅ lista':<10} todas las variables presentes")
    else:
        print(f"{platform:<12} {'❌ falta':<10} {', '.join(missing)}")

print()
print("Recuerda: solo necesitas rellenar las plataformas que vayas a usar.")
print("Empieza por Discord o Imgur — son las más rápidas de configurar.")
