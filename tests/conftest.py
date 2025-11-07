import pytest
import os
import sys
from app import create_app, db as _db
from app.models import Material, BorrowRecord
import random
import string

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_random_qr_code():
    """生成随机的二维码文件名，避免重复"""
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_qr_{random_str}.png"


@pytest.fixture(scope='session')
def app():
    """创建测试应用"""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False
    })

    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    """测试客户端"""
    return app.test_client()


@pytest.fixture
def db(app):
    """数据库会话"""
    with app.app_context():
        _db.session.begin_nested()
        yield _db
        _db.session.rollback()


@pytest.fixture
def sample_material(db):
    """创建测试物资 - 每次生成唯一的QR code"""
    material = Material(
        name="测试Arduino开发板",
        category="控制器",
        qr_code=generate_random_qr_code()  # 使用随机QR code
    )
    db.session.add(material)
    db.session.commit()
    return material


@pytest.fixture
def sample_borrow_record(db, sample_material):
    """创建测试借用记录"""
    record = BorrowRecord(
        material_id=sample_material.id,
        borrower="测试用户",
        student_id="20240001"
    )
    db.session.add(record)
    db.session.commit()
    return record