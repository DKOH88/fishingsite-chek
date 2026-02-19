# 천일호 예약 봇 (3-step, 좌석선택 없음)
from base_bot import BaseFishingBot

class CheonilhoBot(BaseFishingBot):
    SITE_URL = "fishing1001.com"
    PA_N_UID = "1443"
    PROVIDER_NAME = "천일호"
    STEPS = 3
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
    bot = CheonilhoBot(config)
    bot.run()
