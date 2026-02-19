# 팀루피호 예약 봇 (2-step, 좌석선택 없음)
from base_bot import BaseFishingBot

class TeamloopyhoBot(BaseFishingBot):
    SITE_URL = "masterfishing.kr"
    PA_N_UID = "6161"
    PROVIDER_NAME = "팀루피호"
    STEPS = 3
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
    bot = TeamloopyhoBot(config)
    bot.run()
