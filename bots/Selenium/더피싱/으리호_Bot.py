# 으리호 예약 봇 (3-step + 좌석선택)
from base_bot import BaseFishingBot

class EurihoBot(BaseFishingBot):
    SITE_URL = "mscufishing.com"
    PA_N_UID = "4920"
    PROVIDER_NAME = "으리호"
    STEPS = 3
    HAS_SEAT_SELECTION = True
    API_VERSION = "v5.2_seat1"
    USE_HTTPS = False

if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
    bot = EurihoBot(config)
    bot.run()
