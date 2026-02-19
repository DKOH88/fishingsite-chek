# 청광호 예약 봇 (3-step, 좌석선택 없음)
from base_bot import BaseFishingBot

class ChungkwanghoBot(BaseFishingBot):
    SITE_URL = "chungkwangho.net"
    PA_N_UID = "1588"
    PROVIDER_NAME = "청광호"
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
    bot = ChungkwanghoBot(config)
    bot.run()
