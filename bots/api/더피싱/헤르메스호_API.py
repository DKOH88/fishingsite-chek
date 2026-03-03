# -*- coding: utf-8 -*-
"""
헤르메스호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 헤르메스호APIBot(TheFishingAPIBot):
    BASE_URL = "http://hermes.thefishing.kr/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "5579"
    PROVIDER_NAME = "헤르메스호"
    RESERVATION_TYPE = "2step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['15', '8', '7', '14', '1', '9', '6', '13', '2', '10', '5', '12', '3', '11', '4']


if __name__ == "__main__":
    bot = 헤르메스호APIBot()
    bot.run()
