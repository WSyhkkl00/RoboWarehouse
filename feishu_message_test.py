#!/usr/bin/env python3
"""
飞书消息发送器 - 自定义跳转链接版
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import json
from datetime import datetime
import threading


class FeishuMessageGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 飞书消息发送器 v1.0 - 自定义链接版")
        self.root.geometry("800x700")

        self.setup_ui()

    def setup_ui(self):
        """设置用户界面"""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.setup_config_tab(notebook)
        self.setup_message_tab(notebook)
        self.setup_history_tab(notebook)

    def setup_config_tab(self, notebook):
        """配置选项卡"""
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="⚙️ 配置")

        # 应用配置
        config_group = ttk.LabelFrame(config_frame, text="应用配置", padding=10)
        config_group.pack(fill='x', padx=5, pady=5)

        ttk.Label(config_group, text="App ID:").grid(row=0, column=0, sticky='w', pady=2)
        self.app_id = ttk.Entry(config_group, width=50)
        self.app_id.insert(0, "cli_a98549cb29399013")
        self.app_id.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(config_group, text="App Secret:").grid(row=1, column=0, sticky='w', pady=2)
        self.app_secret = ttk.Entry(config_group, width=50, show="*")
        self.app_secret.insert(0, "gp0d4SMwkxQwQOiUnlWJmbhzyOcajlF4")
        self.app_secret.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(config_group, text="接收者ID:").grid(row=2, column=0, sticky='w', pady=2)
        self.receive_id = ttk.Entry(config_group, width=50)
        self.receive_id.insert(0, "ou_038240158a2fd5167b5eb1ca9a000c44")
        self.receive_id.grid(row=2, column=1, padx=5, pady=2)

        # 按钮区域
        button_frame = ttk.Frame(config_group)
        button_frame.grid(row=3, column=1, sticky='e', pady=10)

        ttk.Button(button_frame, text="诊断应用", command=self.diagnose_app).pack(side='left', padx=5)
        ttk.Button(button_frame, text="测试连接", command=self.test_connection).pack(side='left', padx=5)

    def setup_message_tab(self, notebook):
        """消息编辑选项卡"""
        message_frame = ttk.Frame(notebook)
        notebook.add(message_frame, text="📝 消息编辑")

        # 消息类型选择
        type_group = ttk.LabelFrame(message_frame, text="消息类型", padding=10)
        type_group.pack(fill='x', padx=5, pady=5)

        self.message_type = tk.StringVar(value="interactive")
        ttk.Radiobutton(type_group, text="普通文本", variable=self.message_type, value="text").pack(side='left',
                                                                                                    padx=10)
        ttk.Radiobutton(type_group, text="交互卡片", variable=self.message_type, value="interactive").pack(side='left',
                                                                                                           padx=10)

        # 卡片风格选择
        style_group = ttk.LabelFrame(message_frame, text="卡片风格", padding=10)
        style_group.pack(fill='x', padx=5, pady=5)

        self.card_style = tk.StringVar(value="welcome")
        styles = [
            ("🎉 欢迎风格", "welcome"),
            ("🚀 科技风格", "tech"),
            ("⚠️ 告警风格", "alert"),
            ("✅ 成功风格", "success"),
            ("💼 商务风格", "business"),
            ("🎮 原神风格", "genshin")
        ]

        for i, (text, value) in enumerate(styles):
            ttk.Radiobutton(style_group, text=text, variable=self.card_style, value=value).grid(
                row=i // 3, column=i % 3, sticky='w', padx=10, pady=2)

        # 自定义内容区域
        custom_group = ttk.LabelFrame(message_frame, text="自定义内容", padding=10)
        custom_group.pack(fill='x', padx=5, pady=5)

        ttk.Label(custom_group, text="标题:").grid(row=0, column=0, sticky='w', pady=2)
        self.custom_title = ttk.Entry(custom_group, width=50)
        self.custom_title.grid(row=0, column=1, padx=5, pady=2, sticky='ew')

        ttk.Label(custom_group, text="内容:").grid(row=1, column=0, sticky='nw', pady=2)
        self.custom_content = scrolledtext.ScrolledText(custom_group, width=60, height=6)
        self.custom_content.grid(row=1, column=1, padx=5, pady=2, sticky='ew')

        # 自定义链接设置
        link_group = ttk.LabelFrame(message_frame, text="自定义跳转链接", padding=10)
        link_group.pack(fill='x', padx=5, pady=5)

        ttk.Label(link_group, text="按钮1文本:").grid(row=0, column=0, sticky='w', pady=2)
        self.btn1_text = ttk.Entry(link_group, width=15)
        self.btn1_text.insert(0, "查看详情")
        self.btn1_text.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(link_group, text="按钮1链接:").grid(row=0, column=2, sticky='w', pady=2)
        self.btn1_url = ttk.Entry(link_group, width=40)
        self.btn1_url.insert(0, "https://ys.mihoyo.com/main/")
        self.btn1_url.grid(row=0, column=3, padx=5, pady=2, sticky='ew')

        ttk.Label(link_group, text="按钮2文本:").grid(row=1, column=0, sticky='w', pady=2)
        self.btn2_text = ttk.Entry(link_group, width=15)
        self.btn2_text.insert(0, "官方文档")
        self.btn2_text.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(link_group, text="按钮2链接:").grid(row=1, column=2, sticky='w', pady=2)
        self.btn2_url = ttk.Entry(link_group, width=40)
        self.btn2_url.insert(0, "https://open.feishu.cn/document/home/index")
        self.btn2_url.grid(row=1, column=3, padx=5, pady=2, sticky='ew')

        # 按钮区域
        button_frame = ttk.Frame(message_frame)
        button_frame.pack(fill='x', padx=5, pady=10)

        ttk.Button(button_frame, text="🔄 预览消息", command=self.preview_message).pack(side='left', padx=5)
        ttk.Button(button_frame, text="📤 发送消息", command=self.send_message).pack(side='left', padx=5)
        ttk.Button(button_frame, text="🧹 清空内容", command=self.clear_content).pack(side='left', padx=5)

        # 预览区域
        preview_group = ttk.LabelFrame(message_frame, text="消息预览", padding=10)
        preview_group.pack(fill='x', padx=5, pady=5)

        self.preview_text = scrolledtext.ScrolledText(preview_group, width=60, height=6, state='disabled')
        self.preview_text.pack(fill='both', expand=True)

        # 调试信息
        debug_group = ttk.LabelFrame(message_frame, text="调试信息", padding=10)
        debug_group.pack(fill='both', expand=True, padx=5, pady=5)

        self.debug_text = scrolledtext.ScrolledText(debug_group, width=80, height=8)
        self.debug_text.pack(fill='both', expand=True)

    def setup_history_tab(self, notebook):
        """发送记录选项卡"""
        history_frame = ttk.Frame(notebook)
        notebook.add(history_frame, text="📊 发送记录")

        self.history_text = scrolledtext.ScrolledText(history_frame, width=80, height=20)
        self.history_text.pack(fill='both', expand=True, padx=10, pady=10)
        self.history_text.config(state='disabled')

    def diagnose_app(self):
        """诊断应用"""

        def run_diagnose():
            self.debug("开始诊断应用...")

            app_id = self.app_id.get().strip()
            app_secret = self.app_secret.get().strip()

            if not app_id or not app_secret:
                self.debug("❌ App ID 或 App Secret 为空")
                return

            # 测试Token获取
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            data = {"app_id": app_id, "app_secret": app_secret}

            try:
                response = requests.post(url, json=data, timeout=10)
                result = response.json()

                if result.get("code") == 0:
                    self.debug("✅ Token获取成功")
                    token = result["tenant_access_token"]

                    # 测试应用信息
                    info_url = "https://open.feishu.cn/open-apis/application/v3/info"
                    headers = {"Authorization": f"Bearer {token}"}

                    info_response = requests.get(info_url, headers=headers, timeout=10)
                    info_result = info_response.json()

                    if info_result.get("code") == 0:
                        app_info = info_result["data"]
                        self.debug(f"✅ 应用信息获取成功")
                        self.debug(f"   应用名称: {app_info.get('app_name', '未知')}")
                        self.debug(f"   应用状态: {app_info.get('status', '未知')}")
                    else:
                        self.debug(f"❌ 应用信息获取失败: {info_result.get('msg')}")

                else:
                    self.debug(f"❌ Token获取失败: {result.get('msg')}")
                    self.debug(f"   错误代码: {result.get('code')}")

            except Exception as e:
                self.debug(f"❌ 诊断过程出错: {e}")

        threading.Thread(target=run_diagnose).start()

    def test_connection(self):
        """测试连接"""

        def run_test():
            try:
                sender = FeishuMessageSender(
                    self.app_id.get(),
                    self.app_secret.get()
                )
                if sender.get_tenant_access_token():
                    self.debug("✅ 连接测试成功")
                    messagebox.showinfo("测试结果", "✅ 连接成功！Token获取正常")
                else:
                    self.debug("❌ 连接测试失败")
                    messagebox.showerror("测试结果", "❌ 连接失败，请检查配置")
            except Exception as e:
                self.debug(f"❌ 连接测试异常: {e}")
                messagebox.showerror("测试结果", f"❌ 连接失败：{str(e)}")

        threading.Thread(target=run_test).start()

    def preview_message(self):
        """预览消息"""
        try:
            if self.message_type.get() == "text":
                content = self.custom_content.get("1.0", "end").strip()
                if not content:
                    content = "这是测试文本消息"
                preview = f"文本消息预览:\n{content}"
            else:
                card = self.create_card_content()
                preview = f"卡片消息预览:\n{json.dumps(card, indent=2, ensure_ascii=False)}"

            self.preview_text.config(state='normal')
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", preview)
            self.preview_text.config(state='disabled')

        except Exception as e:
            messagebox.showerror("预览错误", f"生成预览时出错：{str(e)}")

    def create_card_content(self):
        """创建卡片内容"""
        title = self.custom_title.get().strip() or self.get_default_title()
        content = self.custom_content.get("1.0", "end").strip() or self.get_default_content()

        base_card = {
            "config": {
                "wide_screen_mode": True,
                "enable_forward": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": title
                },
                "template": self.get_template_color()
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**🕐 发送时间**\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": "**👤 发送者**\nPython机器人"
                            }
                        }
                    ]
                },
                {
                    "tag": "action",
                    "actions": self.get_custom_actions()
                }
            ]
        }

        return base_card

    def get_default_title(self):
        """获取默认标题"""
        titles = {
            "welcome": "🎉 欢迎消息",
            "tech": "🚀 技术通知",
            "alert": "⚠️ 系统告警",
            "success": "✅ 任务完成",
            "business": "💼 商务通知",
            "genshin": "🎮 原神通知"
        }
        return titles.get(self.card_style.get(), "📢 系统通知")

    def get_default_content(self):
        """获取默认内容"""
        contents = {
            "welcome": "**你好！** 👋\n\n这是一条欢迎消息，很高兴为你服务！",
            "tech": "**系统运行状态**\n\n🟢 服务正常\n🔵 性能稳定\n📊 监控中...",
            "alert": "**检测到系统异常**\n\n请及时检查相关服务状态。",
            "success": "**操作执行成功**\n\n任务已完成，一切正常。",
            "business": "**商务通知**\n\n请查收相关业务信息。",
            "genshin": "**🎮 原神游戏通知**\n\n🌅 提瓦特大陆欢迎你！\n⚔️ 新的冒险等待着你\n🌟 点击下方按钮进入官网"
        }
        return contents.get(self.card_style.get(), "这是一条系统通知消息。")

    def get_template_color(self):
        """获取模板颜色"""
        colors = {
            "welcome": "wathet",
            "tech": "blue",
            "alert": "red",
            "success": "green",
            "business": "purple",
            "genshin": "turquoise"
        }
        return colors.get(self.card_style.get(), "blue")

    def get_custom_actions(self):
        """获取自定义动作按钮"""
        actions = []

        # 按钮1
        btn1_text = self.btn1_text.get().strip() or "查看详情"
        btn1_url = self.btn1_url.get().strip()
        if btn1_url:
            actions.append({
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": btn1_text
                },
                "type": "primary",
                "url": btn1_url
            })

        # 按钮2
        btn2_text = self.btn2_text.get().strip() or "官方文档"
        btn2_url = self.btn2_url.get().strip()
        if btn2_url:
            actions.append({
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": btn2_text
                },
                "type": "default",
                "url": btn2_url
            })

        # 如果没有自定义按钮，使用默认按钮
        if not actions:
            actions = [
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "✅ 确认"
                    },
                    "type": "primary",
                    "value": {
                        "action": "confirm"
                    }
                },
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "📖 查看详情"
                    },
                    "type": "default",
                    "url": "https://open.feishu.cn"
                }
            ]

        return actions

    def send_message(self):
        """发送消息"""

        def run_send():
            try:
                sender = FeishuMessageSender(
                    self.app_id.get(),
                    self.app_secret.get()
                )

                receive_id = self.receive_id.get().strip()
                receive_id_type = "open_id" if receive_id.startswith("ou_") else "chat_id"

                self.debug(f"准备发送消息到: {receive_id}")
                self.debug(f"消息类型: {self.message_type.get()}")

                if self.message_type.get() == "text":
                    content = self.custom_content.get("1.0", "end").strip() or "默认文本消息"
                    self.debug(f"文本内容: {content}")
                    result = sender.send_text_message(receive_id, content, receive_id_type)
                else:
                    card_content = self.create_card_content()
                    self.debug(f"卡片内容已生成")
                    result = sender.send_interactive_message(receive_id, card_content, receive_id_type)

                self.debug(f"API响应: {json.dumps(result, ensure_ascii=False)}")

                if result and result.get("code") == 0:
                    self.debug("✅ 消息发送成功！")
                    self.log_history("✅", "发送成功", result['data']['message_id'])
                    messagebox.showinfo("发送结果", "✅ 消息发送成功！")
                else:
                    error_msg = result.get('msg') if result else "未知错误"
                    error_code = result.get('code') if result else "无"
                    self.debug(f"❌ 发送失败: {error_msg} (代码: {error_code})")
                    self.log_history("❌", f"发送失败: {error_msg}")
                    messagebox.showerror("发送结果", f"❌ 发送失败: {error_msg}")

            except Exception as e:
                error_msg = f"发送过程出错: {str(e)}"
                self.debug(f"❌ {error_msg}")
                self.log_history("❌", error_msg)
                messagebox.showerror("发送错误", error_msg)

        threading.Thread(target=run_send).start()

    def debug(self, message):
        """输出调试信息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        self.debug_text.insert("end", log_entry)
        self.debug_text.see("end")
        self.root.update()

    def log_history(self, status, message, msg_id=""):
        """记录发送历史"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {status} {message}"
        if msg_id:
            log_entry += f" (消息ID: {msg_id})"
        log_entry += "\n"

        self.history_text.config(state='normal')
        self.history_text.insert("end", log_entry)
        self.history_text.see("end")
        self.history_text.config(state='disabled')

    def clear_content(self):
        """清空内容"""
        self.custom_title.delete(0, "end")
        self.custom_content.delete("1.0", "end")
        self.preview_text.config(state='normal')
        self.preview_text.delete("1.0", "end")
        self.preview_text.config(state='disabled')


class FeishuMessageSender:
    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = "https://open.feishu.cn/open-apis"
        self.access_token = None

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
                return True
            else:
                print(f"Token获取失败: {result}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"Token请求失败: {e}")
            return False

    def send_text_message(self, receive_id, content, receive_id_type="open_id"):
        """发送文本消息"""
        if not self.access_token:
            if not self.get_tenant_access_token():
                return {"code": -1, "msg": "无法获取访问令牌"}

        url = f"{self.base_url}/im/v1/messages"
        params = {"receive_id_type": receive_id_type}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        data = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": content})
        }

        try:
            response = requests.post(url, params=params, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"消息发送失败: {e}")
            return {"code": -1, "msg": f"网络请求失败: {str(e)}"}

    def send_interactive_message(self, receive_id, card_content, receive_id_type="open_id"):
        """发送交互卡片消息"""
        if not self.access_token:
            if not self.get_tenant_access_token():
                return {"code": -1, "msg": "无法获取访问令牌"}

        url = f"{self.base_url}/im/v1/messages"
        params = {"receive_id_type": receive_id_type}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        data = {
            "receive_id": receive_id,
            "msg_type": "interactive",
            "content": json.dumps(card_content)
        }

        try:
            response = requests.post(url, params=params, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"卡片消息发送失败: {e}")
            return {"code": -1, "msg": f"网络请求失败: {str(e)}"}


def main():
    root = tk.Tk()
    app = FeishuMessageGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()