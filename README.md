# 🤖 RoboWarehouse - WDR机器人实验室物资管理系统

基于 Python Flask 的二维码物资管理系统，支持扫码借用和归还。

## 功能特性
- 微信扫码借用/归还物资
- 身份验证防止恶意操作  
- 实时物资状态监控
- 管理员后台管理
- 二维码批量打印

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```
### 初始化数据
```bash
python init_data.py
```
### 启动服务
```bash
python run.py
```

### 访问后台
```bash
管理界面: http://localhost:5000/admin

调试页面: http://localhost:5000/debug

API接口: http://localhost:5000/api/materials
```
