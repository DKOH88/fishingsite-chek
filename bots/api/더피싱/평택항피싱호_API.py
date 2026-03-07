# -*- coding: utf-8 -*-
"""
평택항피싱호 API 봇 (더피싱)
패턴: 3단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 평택항피싱호APIBot(TheFishingAPIBot):
    BASE_URL = "http://www.ptfishing.net/_core/module/reservation_boat_v5.1"
    PA_N_UID = "2396"
    PROVIDER_NAME = "평택항피싱호"
    RESERVATION_TYPE = "3step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['22', '23', '21', '24', '11', '10']


if __name__ == "__main__":
    bot = 평택항피싱호APIBot()
    bot.run()
