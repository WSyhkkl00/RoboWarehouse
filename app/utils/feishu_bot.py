import requests
import json
from datetime import datetime
from app import celery


@celery.task
def send_borrow_notification(material_name, borrower, student_id, borrow_time=None):
    """发送借用通知到飞书"""
    if borrow_time is None:
        borrow_time = datetime.now()

    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/你的webhook令牌"  # 替换为实际webhook

    message_card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🤖 机器人社团物资借用通知"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**物资名称**: {material_name}\n**借用人**: {borrower}\n**学号**: {student_id}\n**借用时间**: {borrow_time.strftime('%Y-%m-%d %H:%M')}"
                    }
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "请妥善保管物资，按时归还哦～"
                        }
                    ]
                }
            ]
        }
    }

    try:
        response = requests.post(webhook_url, json=message_card, timeout=5)
        if response.status_code == 200:
            print(f"✅ 飞书通知发送成功: {material_name}")
        else:
            print(f"❌ 飞书通知发送失败: {response.text}")
        return response.json()
    except Exception as e:
        print(f"❌ 飞书消息发送异常: {e}")
        return None


def send_return_notification(material_name, borrower, return_time=None):
    """发送归还通知"""
    if return_time is None:
        return_time = datetime.now()

    # 类似的实现，您可以自己补充
    pass