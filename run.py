# #!/usr/bin/env python3
# """
# RoboWarehouse - 机器人社团物资管理系统
# 启动文件
# """
# import os
# import sys
# import socket
#
# # 添加当前目录到Python路径
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
#
# from app import create_app
#
# app = create_app()
#
# if __name__ == '__main__':
#     # 获取本机IP和主机名
#     hostname = socket.gethostname()
#     local_ip = socket.gethostbyname(hostname)
#
#     print("🚀 启动 RoboWarehouse 物资管理系统...")
#     print(f"🏠 主机名: {hostname}")
#     print(f"📡 IP地址: {local_ip}")
#     print("📱 访问地址:")
#     print(f"   http://{hostname}:5000  (推荐)")
#     print(f"   http://{local_ip}:5000")
#     print("📊 管理界面: /admin")
#     print("🛑 按 Ctrl+C 停止服务")
#     print("-" * 50)
#
#     app.run(
#         host='0.0.0.0',  # 允许所有网络访问
#         port=5000,
#         debug=True
#     )
import os
import sys
import socket
from app import create_app, db
from app.models import Material


def update_qrcodes_with_current_ip():
    """每次启动时更新二维码为当前IP"""
    app = create_app()
    with app.app_context():
        current_ip = socket.gethostbyname(socket.gethostname())
        materials = Material.query.all()

        for material in materials:
            from app.utils.qr_generator import generate_qr_code
            qr_filename = generate_qr_code(material.id, material.name, f"http://{current_ip}:5000")
            material.qr_code = qr_filename

        db.session.commit()
        print(f"✅ 二维码已更新为当前IP: {current_ip}")


if __name__ == '__main__':
    # 每次启动都更新二维码
    update_qrcodes_with_current_ip()

    app = create_app()
    current_ip = socket.gethostbyname(socket.gethostname())

    print(f"🚀 系统已启动: http://{current_ip}:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)