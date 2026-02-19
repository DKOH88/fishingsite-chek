# -*- coding: utf-8 -*-
"""
헌터호 API 봇 (더피싱)
패턴: 3단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 헌터호APIBot(TheFishingAPIBot):
    BASE_URL = "http://www.mscufishing.com/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "4443"
    PROVIDER_NAME = "헌터호"
    RESERVATION_TYPE = "3step"  # popup 방식
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['1', '19', '2', '18', '10', '11', '9', '12', '17', '3', '8', '13', '15', '7', '14', '4', '5', '6']


if __name__ == "__main__":
    bot = 헌터호APIBot()
    bot.run()
