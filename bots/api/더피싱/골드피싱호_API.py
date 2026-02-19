# -*- coding: utf-8 -*-
"""
골드피싱 API 봇 (더피싱)
패턴: 3단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 골드피싱APIBot(TheFishingAPIBot):
    BASE_URL = "http://www.mscufishing.com/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "2954"
    PROVIDER_NAME = "골드피싱"
    RESERVATION_TYPE = "3step"  # popup 방식
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['11', '1', '20', '10', '12', '2', '19', '9', '13', '3', '18', '8', '14', '4', '17', '715', '5', '16', '6']


if __name__ == "__main__":
    bot = 골드피싱APIBot()
    bot.run()
