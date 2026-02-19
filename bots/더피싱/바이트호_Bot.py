# -*- coding: utf-8 -*-
"""
바이트호 봇 - 3-step, 자리선택 없음
"""

from base_bot import BaseFishingBot


class BitehoBot(BaseFishingBot):
    """바이트호 예약 봇"""

    SITE_URL = "biteho.kr"
    PA_N_UID = "1297"
    PROVIDER_NAME = "바이트호"
    STEPS = 3
    HAS_SEAT_SELECTION = False
    URL_PATH = "popup.step1.php"


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = BitehoBot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
