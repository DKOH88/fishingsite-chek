# -*- coding: utf-8 -*-
"""
캡틴호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 캡틴호APIBot(TheFishingAPIBot):
    BASE_URL = "http://captainfishing.net/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "2771"
    PROVIDER_NAME = "캡틴호"
    RESERVATION_TYPE = "2step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['9', '8', '20', '19', '21', '18']


if __name__ == "__main__":
    bot = 캡틴호APIBot()
    bot.run()
