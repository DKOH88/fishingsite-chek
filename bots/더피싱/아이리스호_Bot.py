# 아이리스호 예약 봇 (2-step + 좌석선택, v5.1 API)
from base_bot import BaseFishingBot

class IrishoBot(BaseFishingBot):
    SITE_URL = "irisho.kr"
    PA_N_UID = "1545"
    PROVIDER_NAME = "아이리스호"
    STEPS = 2
    HAS_SEAT_SELECTION = True
    API_VERSION = "v5.1"
    USE_HTTPS = False

if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
    bot = IrishoBot(config)
    bot.run()
