# -*- coding: utf-8 -*-
"""
나폴리호 API 봇 (더피싱)
패턴: 3단계 + 좌석선택 비활성화
"""
from base_api_bot import TheFishingAPIBot


class 나폴리호APIBot(TheFishingAPIBot):
    BASE_URL = "https://www.napoliho.net/_core/module/reservation_boat_v3"
    PA_N_UID = "1484"
    PROVIDER_NAME = "나폴리호"
    RESERVATION_TYPE = "3step"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = False


if __name__ == "__main__":
    bot = 나폴리호APIBot()
    bot.run()
