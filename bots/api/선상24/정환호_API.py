# -*- coding: utf-8 -*-
"""
정환호 API 봇 (선상24)
패턴: 동적 조회 (오픈 시 자동 파싱) + 자리선택 비활성화
"""
from base_api_bot import SunSang24APIBot


class 정환호APIBot(SunSang24APIBot):
    BASE_URL = "https://jh.sunsang24.com"
    SUBDOMAIN = "jh"
    PROVIDER_NAME = "정환호"
    HAS_SEAT_SELECTION = False

    ID_MAPPING = {
        # 동적 조회 모드: 예약 오픈 시 schedule_fleet에서 자동 파싱
    }


if __name__ == "__main__":
    bot = 정환호APIBot()
    bot.run()
