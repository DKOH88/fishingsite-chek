# 나폴리호 예약 봇 (3-step, 좌석선택 없음, v3 API)
from base_bot import BaseFishingBot

class NapolihoBot(BaseFishingBot):
    SITE_URL = "napoliho.net"
    PA_N_UID = "1484"
    PROVIDER_NAME = "나폴리호"
    STEPS = 3
    HAS_SEAT_SELECTION = False
    API_VERSION = "v3"
    USE_HTTPS = True

if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
    bot = NapolihoBot(config)
    bot.run()
