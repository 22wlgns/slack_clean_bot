import os
import pg8000
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import datetime
import pytz

# 환경 변수에서 Slack API 토큰 및 기타 설정 불러오기
slack_token = os.getenv('SLACK_BOT_TOKEN')
channel_id = os.getenv('SLACK_CHANNEL_ID')
db_host = os.getenv('DB_HOST')
db_name = os.getenv('DB_NAME')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')

client = WebClient(token=slack_token)

all_users = ['U040LULRKL2', 'U040U8Y1E5U', 'U040YFZ6QBX', 'U05E56X53L2', 'U044AFP0J2Y', 'U06BL1SGGRW', 'U056ER31738', 'U07FDHR6RPH']

def get_db_connection():
    return pg8000.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password
    )

# DB에서 current_index 가져오기
def get_current_index_from_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT index FROM clean_index WHERE id = 1;")
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                return 0  # 기본값
    finally:
        conn.close()

# DB에 current_index 업데이트하기
def update_current_index_in_db(new_index):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE clean_index SET index = %s WHERE id = 1;", (new_index,))
            conn.commit()
    finally:
        conn.close()

def get_next_user(current_index):
    # 모든 유저 리스트에서 다음 유저 가져오기
    return all_users[current_index % len(all_users)]

def send_message(current_user_id, channel_id):
    try:
        remaining_users = [user_id for user_id in all_users if user_id != current_user_id]
        current_index = all_users.index(current_user_id)
        ordered_users = remaining_users[current_index % len(remaining_users):] + remaining_users[:current_index % len(remaining_users)]

        ordered_users.append(current_user_id)

        # 유저 멘션으로 변환
        ordered_user_mentions = " > ".join([f"<@{user_id}>" for user_id in ordered_users])

        message = f"""*오늘의 청소당번은 <@{current_user_id}>님 입니다🎉*
다음 당번 {ordered_user_mentions}

> 🫧 커피머신, 제빙기, 정수기 닦기
> 🫧 커피머신, 제빙기, 정수기 물받이에 고인물 비우기
> 🫧 커피머신, 제빙기에 오래된 물 갈아주기
> 🫧 커피머신 원두 채우기
> 🫧 전자레인지 내부 물티슈로 닦기
> 🫧 쓰레기통 더러우면 비닐봉투 교체 및 쓰레기통 세척하기
"""
        response = client.chat_postMessage(channel=channel_id, text=message)
        print(f"Message sent to {current_user_id} in {channel_id}: {response['ts']}")
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")

def lambda_handler(event, context):
    current_index = get_current_index_from_db()

    # 현재 요일 가져오기
    seoul_tz = pytz.timezone('Asia/Seoul')
    today = datetime.datetime.now(seoul_tz).strftime('%A').lower()

    # 다음 청소 당번 가져오기
    user_for_today = get_next_user(current_index)

    if user_for_today:
        send_message(user_for_today, channel_id)

        # 청소 당번이 돌았으니 다음 인덱스로 업데이트
        new_index = (current_index + 1) % len(all_users)
        update_current_index_in_db(new_index)
        print(f"Current index after update: {new_index}")
    else:
        print(f"No user assigned for today: {today}")
