import pytest
from app.models import Material, BorrowRecord


class TestMaterialModel:
    """物资模型测试"""

    def test_material_creation(self, db):
        """测试物资创建"""
        material = Material(
            name="测试树莓派",
            category="控制器",
            qr_code="test_qr_unique_001.png"  # 使用唯一的QR code
        )
        db.session.add(material)
        db.session.commit()

        assert material.id is not None
        assert material.status == 'available'
        assert material.created_at is not None

    def test_material_to_dict(self, sample_material):
        """测试物资字典转换"""
        material_dict = sample_material.to_dict()

        assert 'id' in material_dict
        assert 'name' in material_dict
        assert 'status' in material_dict
        assert material_dict['name'] == "测试Arduino开发板"


class TestBorrowRecordModel:
    """借用记录模型测试"""

    def test_borrow_record_creation(self, db):
        """测试借用记录创建 - 创建新的物资避免冲突"""
        # 创建新的物资，避免使用fixture中的重复数据
        material = Material(
            name="测试专用物资",
            category="测试类",
            qr_code="test_borrow_record_qr.png"  # 唯一的QR code
        )
        db.session.add(material)
        db.session.commit()

        record = BorrowRecord(
            material_id=material.id,
            borrower="测试用户",
            student_id="20240001"
        )
        db.session.add(record)
        db.session.commit()

        assert record.id is not None
        assert record.status == 'borrowed'
        assert record.borrow_time is not None

    def test_borrow_record_with_fixture(self, sample_borrow_record):
        """使用fixture测试借用记录"""
        assert sample_borrow_record.id is not None
        assert sample_borrow_record.borrower == "测试用户"
        assert sample_borrow_record.status == 'borrowed'