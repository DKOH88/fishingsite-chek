# -*- coding: utf-8 -*-
"""
블랙호 API 봇 (더피싱)
패턴: 3단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 블랙호APIBot(TheFishingAPIBot):
    BASE_URL = "http://kungpyeong.com/_core/module/reservation_boat_v5.1"
    PA_N_UID = "4393"
    PROVIDER_NAME = "블랙호"
    RESERVATION_TYPE = "3step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['20', '1', '11', '10', '19', '2']


if __name__ == "__main__":
    bot = 블랙호APIBot()
    bot.run()
