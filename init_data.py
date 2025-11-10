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
            # C型开发板
            {"model_name": "C型开发板（stm32F407）", "serial_number": "C板-001", "category": "控制板"},
            {"model_name": "C型开发板（stm32F407）", "serial_number": "C板-002", "category": "控制板"},
            {"model_name": "C型开发板（stm32F407）", "serial_number": "C板-003", "category": "控制板"},
            {"model_name": "C型开发板（stm32F407）", "serial_number": "C板-004", "category": "控制板"},
            {"model_name": "C型开发板（stm32F407）", "serial_number": "C板-005", "category": "控制板"},
            {"model_name": "C型开发板（stm32F407）", "serial_number": "C板-006", "category": "控制板"},
            # ... 总共10个

            # 3508电机
            {"model_name": "3508电机", "serial_number": "3508-001", "category": "电机"},
            {"model_name": "3508电机", "serial_number": "3508-002", "category": "电机"},
            # ... 总共5个

            # C620电调
            {"model_name": "C620电调（3508用）", "serial_number": "C620-001", "category": "电调"},
            {"model_name": "C620电调（3508用）", "serial_number": "C620-002", "category": "电调"},
            # ... 总共5个

            # H7开发板
            {"model_name": "H7开发板", "serial_number": "H7-001", "category": "控制板"},
            {"model_name": "H7开发板", "serial_number": "H7-002", "category": "控制板"},
            # ... 总共5个

            # 4310电机
            {"model_name": "达妙4310电机", "serial_number": "4310-001", "category": "电机"},
            {"model_name": "达妙4310电机", "serial_number": "4310-002", "category": "电机"},
            # ... 总共5个

            # 大疆遥控器
            {"model_name": "大疆官方遥控器", "serial_number": "遥控器-001", "category": "遥控器"},
            {"model_name": "大疆官方遥控器", "serial_number": "遥控器-002", "category": "遥控器"},
            # ... 总共5个

            # 接收机
            {"model_name": "大疆官方遥控器接收机", "serial_number": "接收机-001", "category": "接收机"},
            {"model_name": "大疆官方遥控器接收机", "serial_number": "接收机-002", "category": "接收机"},
            # ... 总共4个
        ]

        created_count = 0
        for item in materials_data:
            # 检查是否已存在（通过编号检查）
            existing = Material.query.filter_by(serial_number=item["serial_number"]).first()
            if not existing:
                material = Material(
                    model_name=item["model_name"],
                    serial_number=item["serial_number"],
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
            qr_filename = generate_qr_code(material.id, material.model_name)  # 改为 model_name
            material.qr_code = qr_filename

        db.session.commit()
        print("🎉 物资数据初始化完成！")
        print("📁 二维码文件保存在: static/qrcodes/")
        print("🌐 启动服务后访问: http://localhost:5000")


if __name__ == '__main__':
    init_materials()