# -*- coding: utf-8 -*-
"""
헤라호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 비활성화
"""
from base_api_bot import TheFishingAPIBot


class 헤라호APIBot(TheFishingAPIBot):
    BASE_URL = "https://ssfish.kr/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "3609"
    PROVIDER_NAME = "헤라호"
    RESERVATION_TYPE = "2step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = False


if __name__ == "__main__":
    bot = 헤라호APIBot()
    bot.run()
