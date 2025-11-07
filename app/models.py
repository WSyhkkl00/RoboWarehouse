from . import db
from datetime import datetime


class Material(db.Model):
    """物资模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, comment='物资名称')
    description = db.Column(db.Text, comment='物资描述')
    qr_code = db.Column(db.String(100), unique=True, comment='二维码文件名')
    category = db.Column(db.String(50), default='其他', comment='分类')
    status = db.Column(db.String(20), default='available', comment='状态: available/borrowed/maintenance')
    current_holder = db.Column(db.String(50), comment='当前持有人')
    borrow_time = db.Column(db.DateTime, comment='借用时间')
    expected_return = db.Column(db.DateTime, comment='预计归还时间')
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        """转换为字典，用于JSON序列化"""
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'status': self.status,
            'current_holder': self.current_holder,
            'borrow_time': self.borrow_time.isoformat() if self.borrow_time else None,
            'expected_return': self.expected_return.isoformat() if self.expected_return else None
        }

    def __repr__(self):
        return f'<Material {self.name}>'


class BorrowRecord(db.Model):
    """借用记录模型"""
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)
    borrower = db.Column(db.String(50), nullable=False, comment='借用人')
    student_id = db.Column(db.String(20), comment='学号')
    borrow_time = db.Column(db.DateTime, default=datetime.now, comment='借用时间')
    return_time = db.Column(db.DateTime, comment='归还时间')
    status = db.Column(db.String(20), default='borrowed', comment='状态: borrowed/returned')

    # 关系
    material = db.relationship('Material', backref=db.backref('borrow_records', lazy=True))

    def __repr__(self):
        return f'<BorrowRecord {self.borrower} - {self.material_id}>'