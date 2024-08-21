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

teams = {
    'monday': [('U05E56X53L2', 'U05H9QD4HCK'), ('U06BL1SGGRW', 'U056ER31738')],
    'wednesday': [('U044AFP0J2Y', 'U06P18S3MU2', 'U05HA0ERSP5'), ('U040LULRKL2', 'U07FDHR6RPH')],
    'friday': [('U04SG0Y3FQS', 'U04SG0Y3FQS'), ('U040U8Y1E5U', 'U040YFZ6QBX')]
}

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

def get_today_teams(day_of_week, current_index):
    # 요일에 따라 맞는 팀 리스트 가져오기
    day_teams = teams[day_of_week]
    return day_teams[current_index % len(day_teams)]

def send_message(user_ids, channel_id):
    try:
        user_mentions = " ".join([f"<@{user_id}>" for user_id in user_ids])
        message = f"""오늘의 청소당번은 {user_mentions}님들 입니다!
> 1. 커피머신, 제빙기, 정수기 닦기
> 2. 커피머신, 정수기 물받이에 고인물 비우기
> 3. 커피머신, 제빙기에 오래된 물 갈아주기
> 4. 커피머신 원두 채우기
> 5. 전자레인지 내부 물티슈로 닦기
> 6. 쓰레기통 더러우면 비닐봉투 교체 및 쓰레기통 세척하기"""
        response = client.chat_postMessage(channel=channel_id, text=message)
        print(f"Message sent to {user_mentions} in {channel_id}: {response['ts']}")
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")

def lambda_handler(event, context):
    current_index = get_current_index_from_db()

    # 현재 요일 가져오기
    seoul_tz = pytz.timezone('Asia/Seoul')
    today = datetime.datetime.now(seoul_tz).strftime('%A').lower()

    team_for_today = get_today_teams(today, current_index)
    if team_for_today:
        send_message(team_for_today, channel_id)

        # 금요일에만 인덱스를 업데이트
        if today == 'friday':
            new_index = (current_index + 1) % len(teams['monday'])
            update_current_index_in_db(new_index)
            print(f"Current index after update: {new_index}")
        else:
            print(f"Index remains the same: {current_index}")
    else:
        print(f"No teams assigned for today: {today}")
