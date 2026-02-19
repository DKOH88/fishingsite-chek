# -*- coding: utf-8 -*-
"""
으리호 API 봇 (더피싱)
패턴: 3단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 으리호APIBot(TheFishingAPIBot):
    BASE_URL = "http://www.mscufishing.com/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "4920"
    PROVIDER_NAME = "으리호"
    RESERVATION_TYPE = "3step"  # popup 방식
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['4', '1', '11', '9', '5', '2', '10', '8', '6', '3', '7']


if __name__ == "__main__":
    bot = 으리호APIBot()
    bot.run()
