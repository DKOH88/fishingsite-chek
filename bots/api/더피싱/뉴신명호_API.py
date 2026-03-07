# -*- coding: utf-8 -*-
"""
뉴신명호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 뉴신명호APIBot(TheFishingAPIBot):
    BASE_URL = "http://www.shinmyungho.com/_core/module/reservation_boat_v5.1"
    PA_N_UID = "2212"
    PROVIDER_NAME = "뉴신명호"
    RESERVATION_TYPE = "2step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['1', '20', '10', '11']


if __name__ == "__main__":
    bot = 뉴신명호APIBot()
    bot.run()
