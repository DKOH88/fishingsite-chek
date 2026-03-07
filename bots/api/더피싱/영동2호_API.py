# -*- coding: utf-8 -*-
"""
영동2호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 영동2호APIBot(TheFishingAPIBot):
    BASE_URL = "https://www.youngdong2ho.net/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "983"
    PROVIDER_NAME = "영동2호"
    RESERVATION_TYPE = "2step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['1', '11', '10', '20']


if __name__ == "__main__":
    bot = 영동2호APIBot()
    bot.run()
