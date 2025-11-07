from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from celery import Celery
import os

# 创建扩展实例
db = SQLAlchemy()
celery = Celery()


def create_app():
    """应用工厂函数"""
    app = Flask(__name__)

    # 加载配置
    app.config.from_pyfile('../config.py')

    # 确保实例目录存在
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['QR_CODE_DIR'], exist_ok=True)

    # 初始化扩展
    db.init_app(app)
    celery.conf.update(app.config)

    # 注册蓝图
    from .routes import main_bp
    app.register_blueprint(main_bp)

    # 创建数据库表
    with app.app_context():
        db.create_all()

    return app


# 导入模型（必须在db初始化后）
from . import models