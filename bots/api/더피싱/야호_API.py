# -*- coding: utf-8 -*-
"""
야호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 야호APIBot(TheFishingAPIBot):
    BASE_URL = "http://xn--2f5b291a.com/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "3904"
    PROVIDER_NAME = "야호"
    RESERVATION_TYPE = "2step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['1', '11', '10', '20', '2', '12']


if __name__ == "__main__":
    bot = 야호APIBot()
    bot.run()
