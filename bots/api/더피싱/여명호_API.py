# -*- coding: utf-8 -*-
"""
여명호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 비활성화
"""
from base_api_bot import TheFishingAPIBot


class 여명호APIBot(TheFishingAPIBot):
    BASE_URL = "http://xn--v42bv0rcoar53c6lb.kr/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "5030"
    PROVIDER_NAME = "여명호"
    RESERVATION_TYPE = "2step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = False


if __name__ == "__main__":
    bot = 여명호APIBot()
    bot.run()
