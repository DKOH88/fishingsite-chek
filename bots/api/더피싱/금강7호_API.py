# -*- coding: utf-8 -*-
"""
금강7호 API 봇 (더피싱)
패턴: 3단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 금강7호APIBot(TheFishingAPIBot):
    BASE_URL = "http://www.kumkangho.co.kr/_core/module/reservation_boat_v5.1"
    PA_N_UID = "1839"
    PROVIDER_NAME = "금강7호"
    RESERVATION_TYPE = "3step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['11', '10', '20', '1']


if __name__ == "__main__":
    bot = 금강7호APIBot()
    bot.run()
