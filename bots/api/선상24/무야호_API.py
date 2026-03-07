# -*- coding: utf-8 -*-
"""
무야호 API 봇 (선상24)
패턴: 동적 조회 (오픈 시 자동 파싱) + 자리선택 활성화
"""
from base_api_bot import SunSang24APIBot


class 무야호APIBot(SunSang24APIBot):
    BASE_URL = "https://marineho.sunsang24.com"
    SUBDOMAIN = "marineho"
    PROVIDER_NAME = "무야호"
    HAS_SEAT_SELECTION = True

    SEAT_PRIORITY = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']

    ID_MAPPING = {
        # 동적 조회 모드: 예약 오픈 시 schedule_fleet에서 자동 파싱
    }


if __name__ == "__main__":
    bot = 무야호APIBot()
    bot.run()
