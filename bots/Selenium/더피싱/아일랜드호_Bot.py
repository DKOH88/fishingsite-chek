# 아일랜드호 예약 봇 (3-step, 좌석선택 없음)
from base_bot import BaseFishingBot

class IslandhoBot(BaseFishingBot):
    SITE_URL = "fishingi.net"
    PA_N_UID = "1444"
    PROVIDER_NAME = "아일랜드호"
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
    bot = IslandhoBot(config)
    bot.run()
