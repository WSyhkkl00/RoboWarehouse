import os
import sys


def check_qrcodes():
    """检查二维码文件状态"""
    print("🔍 检查二维码文件...")

    # 二维码目录
    qr_dir = "static/qrcodes"

    # 检查目录是否存在
    if not os.path.exists(qr_dir):
        print(f"❌ 二维码目录不存在: {qr_dir}")
        print("请先运行: python init_data.py")
        return

    # 列出所有文件
    files = os.listdir(qr_dir)
    print(f"📁 二维码目录: {qr_dir}")
    print(f"📄 找到 {len(files)} 个文件:")

    if not files:
        print("❌ 目录为空，没有二维码文件")
        return

    # 检查每个文件
    for i, file in enumerate(sorted(files), 1):
        filepath = os.path.join(qr_dir, file)
        file_exists = os.path.exists(filepath)
        file_size = os.path.getsize(filepath) if file_exists else 0

        status = "✅" if file_exists else "❌"
        print(f"  {i:2d}. {status} {file} ({file_size} bytes)")

    print(f"\n🌐 测试访问地址:")
    for file in files[:3]:  # 只显示前3个的测试地址
        print(f"  http://localhost:5000/qrcodes/{file}")


if __name__ == "__main__":
    check_qrcodes()