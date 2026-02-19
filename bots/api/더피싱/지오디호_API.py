# -*- coding: utf-8 -*-
"""
지오디호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 지오디호APIBot(TheFishingAPIBot):
    BASE_URL = "https://www.teamgod.kr/_core/module/reservation_boat_v5.1"
    PA_N_UID = "5295"
    PROVIDER_NAME = "지오디호"
    RESERVATION_TYPE = "2step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['10', '20', '1', '11', '9', '19', '2', '12']


if __name__ == "__main__":
    bot = 지오디호APIBot()
    bot.run()
