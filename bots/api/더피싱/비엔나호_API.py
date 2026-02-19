# -*- coding: utf-8 -*-
"""
비엔나호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 없음 (선택적 활성화 가능)
"""
from base_api_bot import TheFishingAPIBot


class 비엔나호APIBot(TheFishingAPIBot):
    BASE_URL = "https://www.vinaho.com/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "3163"
    PROVIDER_NAME = "비엔나호"
    RESERVATION_TYPE = "2step"  # popu2 방식
    HAS_SEAT_SELECTION = False  # 필요시 True로 변경


if __name__ == "__main__":
    bot = 비엔나호APIBot()
    bot.run()
