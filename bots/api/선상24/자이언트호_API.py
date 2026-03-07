# -*- coding: utf-8 -*-
"""
자이언트호 API 봇 (선상24)
패턴: 동적 조회 (오픈 시 자동 파싱) + 자리선택 비활성화
"""
from base_api_bot import SunSang24APIBot


class 자이언트호APIBot(SunSang24APIBot):
    BASE_URL = "https://rkclgh.sunsang24.com"
    SUBDOMAIN = "rkclgh"
    PROVIDER_NAME = "자이언트호"
    HAS_SEAT_SELECTION = False

    ID_MAPPING = {
        # 동적 조회 모드: 예약 오픈 시 schedule_fleet에서 자동 파싱
    }


if __name__ == "__main__":
    bot = 자이언트호APIBot()
    bot.run()
