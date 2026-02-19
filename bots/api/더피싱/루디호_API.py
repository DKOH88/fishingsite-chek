# -*- coding: utf-8 -*-
"""
루디호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 비활성화
"""
from base_api_bot import TheFishingAPIBot


class 루디호APIBot(TheFishingAPIBot):
    BASE_URL = "http://rudyfishing.com/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "3468"
    PROVIDER_NAME = "루디호"
    RESERVATION_TYPE = "2step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = False


if __name__ == "__main__":
    bot = 루디호APIBot()
    bot.run()
