# 와이파이호 예약 봇 (2-step + 좌석선택)
from base_bot import BaseFishingBot

class WifihoBot(BaseFishingBot):
    SITE_URL = "khanfishing.com"
    PA_N_UID = "5264"
    PROVIDER_NAME = "와이파이호"
    STEPS = 2
    HAS_SEAT_SELECTION = True
    API_VERSION = "v5.2_seat1"
    USE_HTTPS = True

if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
    bot = WifihoBot(config)
    bot.run()
