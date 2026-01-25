import asyncio
from telethon import TelegramClient, events
from telegram import Bot
from datetime import datetime
import os

# 콘솔 제목 설정
os.system('title "🤖 Upbit & Bithumb Listing Bot 💹🚀"')

# 설정
api_id = 26563117
api_hash = 'fdd49a5f3e144987fcb4878e879ed735'
bot_token = '7417808547:AAFAojmo5Dq5BsjK9udJGVWRhC05OhDs-JY'
channel_username = '@shrimp_notice'
my_chat_id = 393163178

# 객체 생성
client = TelegramClient('session_name', api_id, api_hash)
bot = Bot(token=bot_token)
seen_messages = set()

# 테스트 모드 (True: 모든 메시지 알림, False: 키워드 필터링)
TEST_MODE = False

# 상태 출력
def print_status():
    now = datetime.now().strftime('%H:%M:%S')
    print(f"\n🟢 [{now}] 새우 채널 감지 중...\n")

# 감지 핸들러
@client.on(events.NewMessage(chats=channel_username))
async def handler(event):
    msg_id = event.id
    if msg_id in seen_messages:
        return
    seen_messages.add(msg_id)

    text = event.message.message
    print(f"\n[감지됨] 새로운 메시지:\n{text}\n")

    should_alert = TEST_MODE or any(
        kw in text for kw in ['디지털 자산 추가', '원화 마켓 추가', '신규 거래지원 안내 (KRW', '퀴즈']
    )

    if should_alert:
        try:
            await bot.send_message(chat_id=my_chat_id, text=f"[📢 상장 공지]\n{text}")
            print("✅ 텔레그램 전송 완료.")
        except Exception as e:
            print(f"❌ 전송 실패: {e}")
    else:
        print("⛔ 키워드 미일치 → 알림 생략")

    # 다시 감지 상태 출력
    print_status()

# 메인 실행 함수
async def main():
    print_status()
    await client.start()
    await client.run_until_disconnected()

# 실행
if __name__ == '__main__':
    client.loop.run_until_complete(main())
