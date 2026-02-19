# -*- coding: utf-8 -*-
"""
양파호 봇 - 2-step, 자리선택 없음
"""

from base_bot import BaseFishingBot


class Xnog5bo0wvncBot(BaseFishingBot):
    """양파호 예약 봇"""

    SITE_URL = "xn--og5bo0wvnc.kr"
    PA_N_UID = "3950"
    PROVIDER_NAME = "양파호"
    STEPS = 2
    HAS_SEAT_SELECTION = False


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = Xnog5bo0wvncBot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
