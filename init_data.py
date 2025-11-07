"""
初始化机器人社团物资数据
"""
import os
import sys

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Material
from app.utils.qr_generator import generate_qr_code


def init_materials():
    """初始化物资数据"""
    app = create_app()

    with app.app_context():
        # 清空现有数据（可选）
        # db.drop_all()
        # db.create_all()

        # 定义实验室常用物资
        materials_data = [
            {"name": "3508电机", "category": "电机"},
            {"name": "6020电机", "category": "电机"},
            {"name": "2006电机", "category": "电机"},
            {"name": "4310电机", "category": "电机"},
            {"name": "C620电调", "category": "电调"},
            {"name": "C610电调", "category": "电调"},
            {"name": "C板", "category": "控制板"},
            {"name": "达妙开发板", "category": "控制板"},
        ]

        created_count = 0
        for item in materials_data:
            # 检查是否已存在
            existing = Material.query.filter_by(name=item["name"]).first()
            if not existing:
                material = Material(
                    name=item["name"],
                    category=item["category"]
                )
                db.session.add(material)
                created_count += 1

        db.session.commit()
        print(f"✅ 已创建 {created_count} 个物资记录")

        # 为所有物资生成二维码
        all_materials = Material.query.all()
        print(f"🔄 开始为 {len(all_materials)} 个物资生成二维码...")

        for material in all_materials:
            qr_filename = generate_qr_code(material.id, material.name)
            material.qr_code = qr_filename

        db.session.commit()
        print("🎉 物资数据初始化完成！")
        print("📁 二维码文件保存在: static/qrcodes/")
        print("🌐 启动服务后访问: http://localhost:5000")


if __name__ == '__main__':
    init_materials()