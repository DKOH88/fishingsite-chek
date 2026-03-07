# -*- coding: utf-8 -*-
"""
나대세호 API 봇 (더피싱)
패턴: 3단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 나대세호APIBot(TheFishingAPIBot):
    BASE_URL = "http://www.mscufishing.com/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "2956"
    PROVIDER_NAME = "나대세호"
    RESERVATION_TYPE = "3step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['10', '11', '1', '20', '9', '12', '2', '19', '8', '13', '3', '18', '7', '14', '4', '17', '6', '15', '5', '16']


if __name__ == "__main__":
    bot = 나대세호APIBot()
    bot.run()
