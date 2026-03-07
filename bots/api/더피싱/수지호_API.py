# -*- coding: utf-8 -*-
"""
수지호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 수지호APIBot(TheFishingAPIBot):
    BASE_URL = "http://xn--9p4b23lv7k.com/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "3461"
    PROVIDER_NAME = "수지호"
    RESERVATION_TYPE = "2step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['C', 'B', 'D', 'A', '10', '11']


if __name__ == "__main__":
    bot = 수지호APIBot()
    bot.run()
