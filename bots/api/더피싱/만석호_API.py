# -*- coding: utf-8 -*-
"""
만석호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 만석호APIBot(TheFishingAPIBot):
    BASE_URL = "http://www.mscufishing.com/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "3570"
    PROVIDER_NAME = "만석호"
    RESERVATION_TYPE = "2step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['1', '9', '8', '15', '2', '10', '7', '14', '3', '11', '6', '13', '4', '12', '5']


if __name__ == "__main__":
    bot = 만석호APIBot()
    bot.run()
