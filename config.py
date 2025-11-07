import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# 基础配置
SECRET_KEY = 'robowarehouse-secret-key-2024'
DEBUG = True

# 数据库配置 - 使用SQLite简化部署
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'material.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Redis配置
REDIS_URL = "redis://localhost:6379/0"

# Celery配置
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = "Asia/Shanghai"

# 飞书机器人配置（先去飞书开放平台创建机器人获取）
FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/你的webhook令牌"

# 应用配置
QR_CODE_DIR = os.path.join(BASE_DIR, 'static', 'qrcodes')