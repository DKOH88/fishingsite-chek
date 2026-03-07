# -*- coding: utf-8 -*-
"""
흑돼지호 API 봇 (더피싱)
패턴: 3단계 + 좌석선택 비활성화
"""
from base_api_bot import TheFishingAPIBot


class 흑돼지호APIBot(TheFishingAPIBot):
    BASE_URL = "http://blackpigho.kr/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "6130"
    PROVIDER_NAME = "흑돼지호"
    RESERVATION_TYPE = "3step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = False


if __name__ == "__main__":
    bot = 흑돼지호APIBot()
    bot.run()
