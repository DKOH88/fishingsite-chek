# 뉴성령호 예약 봇 (2-step, 좌석선택 없음)
from base_bot import BaseFishingBot

class NewsungryunghoBot(BaseFishingBot):
    SITE_URL = "sungryungho.com"
    PA_N_UID = "830"
    PROVIDER_NAME = "뉴성령호"
    STEPS = 2
    HAS_SEAT_SELECTION = False
    API_VERSION = "v5.2_seat1"
    USE_HTTPS = False

if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
    bot = NewsungryunghoBot(config)
    bot.run()
