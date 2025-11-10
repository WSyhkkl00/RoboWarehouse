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
            qr_filename = generate_qr_code(material.id, material.model_name, f"http://{current_ip}:5000")
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