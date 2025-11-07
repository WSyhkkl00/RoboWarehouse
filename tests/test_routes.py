import pytest
import json
from app.models import Material


class TestMaterialRoutes:
    """物资路由测试"""

    def test_get_materials(self, client, sample_material):
        """测试获取物资列表"""
        response = client.get('/api/materials')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) >= 1

    def test_borrow_material_success(self, client, sample_material):
        """测试成功借用物资"""
        borrow_data = {
            "borrower": "测试用户",
            "student_id": "20240001"
        }

        response = client.post(
            f'/api/borrow/{sample_material.id}',
            data=json.dumps(borrow_data),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_borrow_material_missing_data(self, client, sample_material):
        """测试借用物资缺少数据"""
        response = client.post(
            f'/api/borrow/{sample_material.id}',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data