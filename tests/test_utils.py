import pytest
import os
from app.utils.qr_generator import get_local_ip


class TestQRGenerator:
    """二维码生成器测试"""

    def test_get_local_ip(self):
        """测试获取本地IP"""
        ip = get_local_ip()
        assert ip is not None
        assert isinstance(ip, str)