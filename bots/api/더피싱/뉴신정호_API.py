# -*- coding: utf-8 -*-
"""
뉴신정호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 비활성화
"""
from base_api_bot import TheFishingAPIBot


class 뉴신정호APIBot(TheFishingAPIBot):
    BASE_URL = "http://newsj.co.kr/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "4452"
    PROVIDER_NAME = "뉴신정호"
    RESERVATION_TYPE = "2step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = False


if __name__ == "__main__":
    bot = 뉴신정호APIBot()
    bot.run()
