# 페라리호 예약 봇 (2-step, 좌석선택 없음, v5.1 API)
from base_bot import BaseFishingBot

class FerrarihoBot(BaseFishingBot):
    SITE_URL = "xn--oi2bn5b095b4mc.com"
    PA_N_UID = "1264"
    PROVIDER_NAME = "페라리호"
    STEPS = 2
    HAS_SEAT_SELECTION = False
    API_VERSION = "v5.1"
    USE_HTTPS = False

if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
    bot = FerrarihoBot(config)
    bot.run()
