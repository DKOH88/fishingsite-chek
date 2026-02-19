# -*- coding: utf-8 -*-
"""
예린호 봇 - 3-step + 자리선택 (알파벳 우선 좌석)
URL: yerinfishing.com
특이사항:
  - 알파벳 좌석 우선 (D, A, C, B 순)
  - API 버전 v5.1 사용
  - 더 느린 SLEEP_INTERVAL (0.05초)
"""

from base_bot import BaseFishingBot


class YerinBot(BaseFishingBot):
    """예린호 예약 봇 (3-step + 자리선택, 알파벳 우선)"""

    # === 필수 설정 ===
    SITE_URL = "yerinfishing.com"
    PA_N_UID = "3515"
    PROVIDER_NAME = "예린호"

    # === 예약 타입 설정 ===
    STEPS = 3
    HAS_SEAT_SELECTION = True
    # 알파벳 좌석 우선
    SEAT_PRIORITY = ['D', 'A', 'C', 'B', '11', '10']

    # === 특수 설정 (예린호 전용) ===
    API_VERSION = "v5.1"  # v5.2_seat1이 아닌 v5.1 사용
    URL_PATH = "popup.step1.php"  # 3-step은 popup 사용
    SLEEP_INTERVAL = 0.05  # 더 느린 간격 (기본값 0.01)
    MAX_SUBMIT_RETRIES = 3  # 더 많은 제출 재시도 (기본값 2)


# 직접 실행 테스트용
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = YerinBot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
