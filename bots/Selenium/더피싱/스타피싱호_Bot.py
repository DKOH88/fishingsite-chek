# 스타피싱호 예약 봇 (2-step + 좌석선택)
from base_bot import BaseFishingBot

class StarfishinghoBot(BaseFishingBot):
    SITE_URL = "jstar.thefishing.kr"
    PA_N_UID = "1925"
    PROVIDER_NAME = "스타피싱호"
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
    bot = StarfishinghoBot(config)
    bot.run()
