# 캡틴호 예약 봇 (2-step + 좌석선택)
from base_bot import BaseFishingBot

class CaptainhoBot(BaseFishingBot):
    SITE_URL = "captainfishing.net"
    PA_N_UID = "2771"
    PROVIDER_NAME = "캡틴호"
    STEPS = 2
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
    bot = CaptainhoBot(config)
    bot.run()
