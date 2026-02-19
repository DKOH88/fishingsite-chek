# -*- coding: utf-8 -*-
"""
빅스타호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 빅스타호APIBot(TheFishingAPIBot):
    BASE_URL = "http://bigstar.thefishing.kr/_core/module/reservation_boat_v5.1"
    PA_N_UID = "3419"
    PROVIDER_NAME = "빅스타호"
    RESERVATION_TYPE = "2step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['22', '21', '10', '11', '1', '20', '9', '12']


if __name__ == "__main__":
    bot = 빅스타호APIBot()
    bot.run()
