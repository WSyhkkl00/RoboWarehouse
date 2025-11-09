import requests
import json
import logging

logger = logging.getLogger(__name__)


class FeishuNotification:
    def __init__(self):
        self.app_id = "cli_a98549cb29399013"
        self.app_secret = "gp0d4SMwkxQwQOiUnlWJmbhzyOcajlF4"
        self.base_url = "https://open.feishu.cn/open-apis"
        self.access_token = None
        # 使用chat_id发送到群组
        self.chat_id = "oc_503b5b47c243d0d94824926b79df22ba"  # 这是chat_id

    def get_tenant_access_token(self):
        """获取访问令牌"""
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        data = {"app_id": self.app_id, "app_secret": self.app_secret}

        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 0:
                self.access_token = result["tenant_access_token"]
                logger.info("✅ 飞书访问令牌获取成功")
                return True
            else:
                logger.error(f"❌ 获取飞书访问令牌失败: {result}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 飞书网络请求失败: {e}")
            return False

    def send_borrow_notification(self, material_name, borrower, student_id, borrow_time):
        """发送借用通知"""
        if not self.access_token:
            if not self.get_tenant_access_token():
                return False

        url = f"{self.base_url}/im/v1/messages"
        params = {"receive_id_type": "chat_id"}  # ⚠️ 改为chat_id
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }

        # 创建消息卡片
        message_content = self._create_borrow_card(material_name, borrower, student_id, borrow_time)

        data = {
            "receive_id": self.chat_id,  # ⚠️ 使用chat_id
            "msg_type": "interactive",
            "content": json.dumps(message_content)
        }

        try:
            response = requests.post(url, params=params, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()

            print(f"🔍 飞书API响应: {result}")  # 调试信息

            if result.get("code") == 0:
                logger.info(f"✅ 飞书通知发送成功: {borrower} 借用了 {material_name}")
                return True
            else:
                logger.error(f"❌ 飞书通知发送失败: {result}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 飞书消息发送请求失败: {e}")
            return False

    def _create_borrow_card(self, material_name, borrower, student_id, borrow_time):
        """创建借用通知消息卡片"""
        return {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "实验室物资借用通知"
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
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "📊 查看物资状态"
                            },
                            "type": "primary",
                            "url": "http://192.168.1.2:5000/admin"  # ⚠️ 改为实际IP
                        }
                    ]
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


# 创建全局实例
feishu_notifier = FeishuNotification()