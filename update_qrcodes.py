import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Material
from app.utils.qr_generator import generate_qr_code


def final_fix_qrcodes():
    """最终修复 - 使用主机名生成二维码"""
    app = create_app()

    with app.app_context():
        materials = Material.query.all()

        print("🔄 使用主机名重新生成二维码...")

        for material in materials:
            # 不传base_url，让函数自动使用主机名
            qr_filename = generate_qr_code(material.id, material.name)
            material.qr_code = qr_filename
            print(f"✅ 更新: {material.name}")

        db.session.commit()
        print("🎉 二维码更新完成！")
        print("💡 现在二维码使用主机名，换网络也能用！")


if __name__ == '__main__':
    final_fix_qrcodes()