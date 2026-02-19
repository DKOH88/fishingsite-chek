# -*- coding: utf-8 -*-
"""
라라호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 라라호APIBot(TheFishingAPIBot):
    BASE_URL = "https://raraho.kr/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "3924"
    PROVIDER_NAME = "라라호"
    RESERVATION_TYPE = "2step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['11', '1', '20', '10', '12', '2', '19', '9']


if __name__ == "__main__":
    bot = 라라호APIBot()
    bot.run()
