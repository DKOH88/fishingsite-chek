# -*- coding: utf-8 -*-
"""
(신)블루오션호 API 봇 (더피싱)
패턴: 3단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 신블루오션호APIBot(TheFishingAPIBot):
    BASE_URL = "http://www.mscufishing.com/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "5679"
    PROVIDER_NAME = "(신)블루오션호"
    RESERVATION_TYPE = "3step"  # popup 방식
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['1', '17', '8', '9', '2', '16', '7', '10', '3', '15', '6', '11', '4', '14', '5', '12', '13']


if __name__ == "__main__":
    bot = 신블루오션호APIBot()
    bot.run()
