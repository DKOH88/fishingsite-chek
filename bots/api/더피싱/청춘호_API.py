# -*- coding: utf-8 -*-
"""
청춘호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 비활성화
"""
from base_api_bot import TheFishingAPIBot


class 청춘호APIBot(TheFishingAPIBot):
    BASE_URL = "http://xn--ox6bwq60s.kr/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "5304"
    PROVIDER_NAME = "청춘호"
    RESERVATION_TYPE = "2step"  # popu2 방식
    HAS_SEAT_SELECTION = False


if __name__ == "__main__":
    bot = 청춘호APIBot()
    bot.run()
