# -*- coding: utf-8 -*-
"""
오성스타호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 비활성화
"""
from base_api_bot import TheFishingAPIBot


class 오성스타호APIBot(TheFishingAPIBot):
    BASE_URL = "http://xn--c20b255a3e006c.com/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "3361"
    PROVIDER_NAME = "오성스타호"
    RESERVATION_TYPE = "2step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = False


if __name__ == "__main__":
    bot = 오성스타호APIBot()
    bot.run()
