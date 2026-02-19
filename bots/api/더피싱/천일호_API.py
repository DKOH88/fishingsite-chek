# -*- coding: utf-8 -*-
"""
천일호 API 봇 (더피싱)
패턴: 3단계 + 좌석선택 비활성화
"""
from base_api_bot import TheFishingAPIBot


class 천일호APIBot(TheFishingAPIBot):
    BASE_URL = "http://fishing1001.com/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "1443"
    PROVIDER_NAME = "천일호"
    RESERVATION_TYPE = "3step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = False


if __name__ == "__main__":
    bot = 천일호APIBot()
    bot.run()
