import qrcode
import os
from PIL import Image
import socket


def get_local_ip():
    """获取本机IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"


def generate_qr_code(material_id, material_name, base_url=None):
    """为物资生成唯一二维码 - 智能选择最佳地址"""
    if base_url is None:
        # 优先使用IP地址，兼容性最好
        local_ip = get_local_ip()
        base_url = f"http://{local_ip}:5000"

    qr_data = f"{base_url}/scan/{material_id}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    qr_dir = "static/qrcodes"
    os.makedirs(qr_dir, exist_ok=True)
    filename = f"material_{material_id}_{material_name}.png".replace(' ', '_')
    filepath = os.path.join(qr_dir, filename)

    img.save(filepath)
    print(f"✅ 二维码已生成: {qr_data}")
    return filename


def get_hostname():
    """获取主机名"""
    import socket
    return socket.gethostname()

def batch_generate_qr_codes(materials):
    """批量生成二维码"""
    from app import create_app
    app = create_app()

    with app.app_context():
        for material in materials:
            generate_qr_code(material.id, material.name)

    print(f"🎉 已为 {len(materials)} 个物资生成二维码")