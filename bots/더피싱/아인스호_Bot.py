# 아인스호 예약 봇 (2-step, 좌석선택 없음)
from base_bot import BaseFishingBot

class EinshoBot(BaseFishingBot):
    SITE_URL = "einsho.com"
    PA_N_UID = "349"
    PROVIDER_NAME = "아인스호"
    STEPS = 2
    HAS_SEAT_SELECTION = False
    API_VERSION = "v5.2_seat1"
    USE_HTTPS = True

if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
    bot = EinshoBot(config)
    bot.run()
