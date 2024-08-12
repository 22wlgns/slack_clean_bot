import os
import pg8000
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import datetime

# 환경 변수에서 Slack API 토큰 및 기타 설정 불러오기
slack_token = os.getenv('SLACK_BOT_TOKEN')
channel_id = os.getenv('SLACK_CHANNEL_ID')
user_list = os.getenv('SLACK_USER_LIST').split(",")
db_host = os.getenv('DB_HOST')
db_name = os.getenv('DB_NAME')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')

client = WebClient(token=slack_token)

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

def get_user_for_today(user_list, current_index):
    return user_list[current_index % len(user_list)]

def send_message(user_id, channel_id):
    try:
        message = f"""오늘의 청소당번은 <@{user_id}>님 입니다!
> 1. 커피머신, 제빙기, 정수기 닦기
> 2. 커피머신, 정수기 물받이에 고인물 비우기
> 3. 커피머신, 제빙기에 오래된 물 갈아주기
> 4. 커피머신 원두 채우기
> 5. 전자레인지 내부 물티슈로 닦기"""
        response = client.chat_postMessage(channel=channel_id, text=message)
        print(f"Message sent to {user_id} in {channel_id}: {response['ts']}")
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")

def lambda_handler(event, context):
    current_index = get_current_index_from_db()

    # 현재 요일 확인 (월: 0, 수: 2, 금: 4)
    today = datetime.datetime.now().weekday()
    if today not in [0, 2, 4]:
        print("오늘은 월, 수, 금이 아닙니다.")
        return

    user_id = get_user_for_today(user_list, current_index)
    send_message(user_id, channel_id)

    # 다음 인덱스로 업데이트
    new_index = (current_index + 1) % len(user_list)
    update_current_index_in_db(new_index)
    print(f"Current index after update: {new_index}")
