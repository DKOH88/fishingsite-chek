# -*- coding: utf-8 -*-
"""
예린호 API 봇 (더피싱)
패턴: 3단계 + 좌석선택 (알파벳 우선)
"""
from base_api_bot import TheFishingAPIBot


class 예린호APIBot(TheFishingAPIBot):
    BASE_URL = "http://www.yerinfishing.com/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "3515"
    PROVIDER_NAME = "예린호"
    RESERVATION_TYPE = "3step"  # popup 방식
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위 (알파벳 우선)
    SEAT_PRIORITY = ['D', 'A', 'C', 'B', '11', '10', '9', '8', '7', '6', '5', '4', '3', '2', '1']


if __name__ == "__main__":
    bot = 예린호APIBot()
    bot.run()
