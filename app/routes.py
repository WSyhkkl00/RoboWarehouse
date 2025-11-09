from flask import Blueprint, request, jsonify, render_template
from datetime import datetime, timedelta
from .models import db, Material, BorrowRecord

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """首页"""
    return jsonify({
        "message": "欢迎使用合肥工业大学宣城校区WDR实验室机器人物资管理系统",
        "version": "1.0.0",
        "endpoints": {
            "借用物资": "POST /api/borrow/{material_id}",
            "物资列表": "GET /api/materials",
            "生成二维码": "POST /api/generate-qrcodes"
        }
    })


from app.utils.feishu_service import feishu_notifier


@main_bp.route('/api/borrow/<int:material_id>', methods=['POST'])
def borrow_material(material_id):
    """借用物资API"""
    data = request.get_json()
    if not data:
        data = request.form

    borrower = data.get('borrower', '').strip()
    student_id = data.get('student_id', '').strip()

    if not borrower:
        return jsonify({"error": "请输入借用人姓名"}), 400

    material = Material.query.get(material_id)
    if not material:
        return jsonify({"error": "物资不存在"}), 404

    if material.status != 'available':
        return jsonify({"error": f"物资 [{material.name}] 当前不可用，状态: {material.status}"}), 400

    # 更新物资状态
    material.status = 'borrowed'
    material.current_holder = borrower
    material.borrow_time = datetime.now()
    material.expected_return = datetime.now() + timedelta(days=7)

    # 创建借用记录
    record = BorrowRecord(
        material_id=material_id,
        borrower=borrower,
        student_id=student_id,
        borrow_time=datetime.now()
    )

    db.session.add(record)
    db.session.commit()

    # 🚀 发送飞书通知（同步方式）
    try:
        feishu_notifier.send_borrow_notification(
            material.name,
            borrower,
            student_id,
            material.borrow_time
        )
    except Exception as e:
        print(f"⚠️ 飞书通知发送失败，但不影响借用: {e}")

    return jsonify({
        "success": True,
        "message": f"✅ 成功借用 [{material.name}]",
        "data": {
            "material": material.name,
            "borrower": borrower,
            "borrow_time": material.borrow_time.strftime("%Y-%m-%d %H:%M"),
            "expected_return": material.expected_return.strftime("%Y-%m-%d")
        }
    })


@main_bp.route('/api/materials')
def list_materials():
    """获取物资列表"""
    materials = Material.query.all()
    return jsonify({
        "success": True,
        "data": [material.to_dict() for material in materials]
    })


@main_bp.route('/api/generate-qrcodes')
def generate_all_qrcodes():
    """为所有物资生成二维码"""
    materials = Material.query.all()

    from .utils.qr_generator import batch_generate_qr_codes
    batch_generate_qr_codes(materials)

    return jsonify({
        "success": True,
        "message": f"已为 {len(materials)} 个物资生成二维码",
        "qrcode_dir": "static/qrcodes/"
    })


@main_bp.route('/admin')
def admin_page():
    """美化版管理页面 - 带动态交互效果"""
    materials = Material.query.all()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>宣城校区机器人实验室物资管理</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 30px;
                color: #2d3748;
            }}

            .container {{
                max-width: 1000px;
                margin: 0 auto;
            }}

            .header {{
                background: white;
                padding: 30px;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                margin-bottom: 30px;
                text-align: center;
                position: relative;
                overflow: hidden;
            }}

            .header::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, #667eea, #764ba2);
            }}

            .header h1 {{
                color: #2d3748;
                font-size: 36px;
                font-weight: 700;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 15px;
            }}

            .stats {{
                display: flex;
                justify-content: center;
                gap: 30px;
                margin-top: 20px;
                flex-wrap: wrap;
            }}

            .stat-card {{
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                padding: 20px;
                border-radius: 12px;
                text-align: center;
                min-width: 120px;
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
                transition: transform 0.3s ease;
            }}

            .stat-card:hover {{
                transform: translateY(-5px);
            }}

            .stat-number {{
                font-size: 32px;
                font-weight: 700;
                margin-bottom: 5px;
            }}

            .stat-label {{
                font-size: 14px;
                opacity: 0.9;
            }}

            .materials-grid {{
                display: grid;
                gap: 20px;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            }}

            .material-card {{
                background: white;
                padding: 25px;
                border-radius: 16px;
                box-shadow: 0 5px 20px rgba(0,0,0,0.08);
                transition: all 0.3s ease;
                border-left: 4px solid;
                position: relative;
                overflow: hidden;
            }}

            .material-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 30px rgba(0,0,0,0.15);
            }}

            .material-card.available {{
                border-left-color: #52c41a;
            }}

            .material-card.borrowed {{
                border-left-color: #ff4d4f;
            }}

            .material-header {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 15px;
            }}

            .material-name {{
                font-size: 18px;
                font-weight: 700;
                color: #2d3748;
                margin-bottom: 5px;
            }}

            .material-id {{
                color: #718096;
                font-size: 14px;
            }}

            .status-badge {{
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                white-space: nowrap;
            }}

            .status-available {{
                background: #f6ffed;
                color: #52c41a;
                border: 1px solid #b7eb8f;
            }}

            .status-borrowed {{
                background: #fff2f0;
                color: #ff4d4f;
                border: 1px solid #ffccc7;
            }}

            .material-info {{
                margin-bottom: 20px;
            }}

            .info-row {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #f7fafc;
            }}

            .info-label {{
                color: #718096;
                font-weight: 500;
            }}

            .info-value {{
                color: #2d3748;
                font-weight: 600;
            }}

            .action-buttons {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }}

            .action-btn {{
                flex: 1;
                padding: 10px 16px;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
                text-decoration: none;
                text-align: center;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 5px;
                min-width: 120px;
            }}

            .qr-btn {{
                background: linear-gradient(135deg, #1890ff, #40a9ff);
                color: white;
            }}

            .qr-btn:hover {{
                background: linear-gradient(135deg, #096dd9, #1890ff);
                transform: translateY(-2px);
            }}

            .borrow-btn {{
                background: linear-gradient(135deg, #52c41a, #73d13d);
                color: white;
            }}

            .borrow-btn:hover {{
                background: linear-gradient(135deg, #389e0d, #52c41a);
                transform: translateY(-2px);
            }}

            .footer {{
                margin-top: 40px;
                text-align: center;
                padding: 20px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            }}

            .footer-links {{
                display: flex;
                justify-content: center;
                gap: 20px;
                flex-wrap: wrap;
            }}

            .footer-link {{
                padding: 10px 20px;
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                transition: all 0.3s ease;
            }}

            .footer-link:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
            }}

            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(20px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}

            .material-card {{
                animation: fadeIn 0.6s ease forwards;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>宣城校区WDR机器人实验室物资管理系统</h1>
                <p>全面监控物资状态，智能化管理流程</p>

                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">{total_count}</div>
                        <div class="stat-label">物资总数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{available_count}</div>
                        <div class="stat-label">可借用</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{borrowed_count}</div>
                        <div class="stat-label">已借出</div>
                    </div>
                </div>
            </div>

            <div class="materials-grid">
    """.format(
        total_count=len(materials),
        available_count=len([m for m in materials if m.status == 'available']),
        borrowed_count=len([m for m in materials if m.status == 'borrowed'])
    )

    for material in materials:
        status_text = "🟢 可借用" if material.status == 'available' else "🔴 已借出"
        status_class = "available" if material.status == 'available' else "borrowed"
        status_badge_class = "status-available" if material.status == 'available' else "status-borrowed"

        html += """
                <div class="material-card {status_class}" style="animation-delay: {delay}ms">
                    <div class="material-header">
                        <div>
                            <div class="material-name">{name}</div>
                            <div class="material-id">#{id}</div>
                        </div>
                        <div class="status-badge {badge_class}">{status_text}</div>
                    </div>

                    <div class="material-info">
                        <div class="info-row">
                            <span class="info-label">分类</span>
                            <span class="info-value">{category}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">当前持有人</span>
                            <span class="info-value">{holder}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">借用时间</span>
                            <span class="info-value">{borrow_time}</span>
                        </div>
                    </div>

                    <div class="action-buttons">
                        <a href="/qrcodes/{qr_code}" target="_blank" class="action-btn qr-btn">
                            <span>📷</span>
                            <span>二维码</span>
                        </a>
                        <a href="/borrow/{id}" class="action-btn borrow-btn">
                            <span>🔗</span>
                            <span>借用链接</span>
                        </a>
                    </div>
                </div>
        """.format(
            status_class=status_class,
            delay=(materials.index(material) * 100) % 600,
            name=material.name,
            id=material.id,
            badge_class=status_badge_class,
            status_text=status_text,
            category=material.category,
            holder=material.current_holder or '无',
            borrow_time=material.borrow_time.strftime('%Y-%m-%d %H:%M') if material.borrow_time else '无',
            qr_code=material.qr_code
        )

    html += """
            </div>

            <div class="footer">
                <div class="footer-links">
                    <a href="/api/materials" class="footer-link">📊 JSON数据接口</a>
                    <a href="/debug" class="footer-link">🔧 调试页面</a>
                    <a href="/print-qrcodes" class="footer-link">🖨️ 批量打印</a>
                    <a href="/" class="footer-link">🏠 返回首页</a>
                </div>
            </div>
        </div>

        <script>
            // 添加卡片悬停效果
            document.addEventListener('DOMContentLoaded', function() {{
                const cards = document.querySelectorAll('.material-card');

                cards.forEach(card => {{
                    card.addEventListener('mouseenter', function() {{
                        this.style.transform = 'translateY(-8px) scale(1.02)';
                    }});

                    card.addEventListener('mouseleave', function() {{
                        this.style.transform = 'translateY(0) scale(1)';
                    }});
                }});

                // 添加点击波纹效果
                cards.forEach(card => {{
                    card.addEventListener('click', function(e) {{
                        const ripple = document.createElement('div');
                        ripple.style.position = 'absolute';
                        ripple.style.borderRadius = '50%';
                        ripple.style.backgroundColor = 'rgba(102, 126, 234, 0.3)';
                        ripple.style.transform = 'scale(0)';
                        ripple.style.animation = 'ripple 0.6s linear';
                        ripple.style.pointerEvents = 'none';

                        const rect = this.getBoundingClientRect();
                        const size = Math.max(rect.width, rect.height);
                        ripple.style.width = ripple.style.height = size + 'px';
                        ripple.style.left = e.clientX - rect.left - size/2 + 'px';
                        ripple.style.top = e.clientY - rect.top - size/2 + 'px';

                        this.style.position = 'relative';
                        this.appendChild(ripple);

                        setTimeout(() => {{
                            ripple.remove();
                        }}, 600);
                    }});
                }});
            }});

            // 添加CSS动画
            const style = document.createElement('style');
            style.textContent = `
                @keyframes ripple {{
                    to {{
                        transform: scale(4);
                        opacity: 0;
                    }}
                }}
            `;
            document.head.appendChild(style);
        </script>
    </body>
    </html>
    """
    return html


@main_bp.route('/borrow/<int:material_id>')
def borrow_page(material_id):
    """借用页面 - 扫描二维码后访问"""
    material = Material.query.get_or_404(material_id)

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>借用 {}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                max-width: 400px; 
                margin: 50px auto; 
                padding: 20px;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h2 {{ color: #1890ff; margin-top: 0; }}
            .material-info {{ 
                background: #f0f8ff; 
                padding: 15px; 
                border-radius: 5px; 
                margin-bottom: 20px;
            }}
            .form-group {{ margin-bottom: 20px; }}
            label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
            input[type="text"] {{
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                box-sizing: border-box;
            }}
            button {{
                width: 100%;
                padding: 12px;
                background: #1890ff;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
            }}
            button:hover {{ background: #40a9ff; }}
            button:disabled {{ background: #ccc; cursor: not-allowed; }}
            #result {{ margin-top: 20px; padding: 15px; border-radius: 5px; }}
            .success {{ background: #f6ffed; border: 1px solid #b7eb8f; color: #52c41a; }}
            .error {{ background: #fff2f0; border: 1px solid #ffccc7; color: #ff4d4f; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🤖 借用物资</h2>
            <div class="material-info">
                <h3>{}</h3>
                <p><strong>分类:</strong> {}</p>
                <p><strong>状态:</strong> 
                    <span style="color: {};">
                        {}
                    </span>
                </p>
            </div>

            <form id="borrowForm">
                <div class="form-group">
                    <label for="borrower">姓名 *</label>
                    <input type="text" id="borrower" placeholder="请输入您的姓名" required>
                </div>
                <div class="form-group">
                    <label for="student_id">学号</label>
                    <input type="text" id="student_id" placeholder="请输入学号（可选）">
                </div>
                <button type="submit" id="submitBtn">确认借用</button>
            </form>

            <div id="result"></div>
        </div>

        <script>
            document.getElementById('borrowForm').addEventListener('submit', async (e) => {{
                e.preventDefault();

                const borrower = document.getElementById('borrower').value.trim();
                const studentId = document.getElementById('student_id').value.trim();
                const submitBtn = document.getElementById('submitBtn');
                const resultDiv = document.getElementById('result');

                if (!borrower) {{
                    resultDiv.className = 'error';
                    resultDiv.innerHTML = '❌ 请输入姓名';
                    return;
                }}

                submitBtn.disabled = true;
                submitBtn.textContent = '借用中...';
                resultDiv.innerHTML = '处理中...';

                try {{
                    const response = await fetch('/api/borrow/{}', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            borrower: borrower,
                            student_id: studentId
                        }})
                    }});

                    const result = await response.json();

                    if (result.success) {{
                        resultDiv.className = 'success';
                        resultDiv.innerHTML = `
                            ✅ <strong>${{result.message}}</strong><br>
                            📅 预计归还: ${{result.data.expected_return}}<br>
                            👤 借用人: ${{result.data.borrower}}
                        `;
                        document.getElementById('borrowForm').style.display = 'none';
                    }} else {{
                        resultDiv.className = 'error';
                        resultDiv.innerHTML = `❌ ${{result.error}}`;
                        submitBtn.disabled = false;
                        submitBtn.textContent = '确认借用';
                    }}
                }} catch (error) {{
                    resultDiv.className = 'error';
                    resultDiv.innerHTML = '❌ 网络错误，请重试';
                    submitBtn.disabled = false;
                    submitBtn.textContent = '确认借用';
                }}
            }});
        </script>
    </body>
    </html>
    """.format(
        material.name,
        material.name,
        material.category,
        'green' if material.status == 'available' else 'red',
        '🟢 可借用' if material.status == 'available' else '🔴 已借出',
        material_id
    )


@main_bp.route('/qrcodes/<path:filename>')
def serve_qrcode(filename):
    """提供二维码文件访问 - 修复版本"""
    from flask import send_from_directory
    import os
    from urllib.parse import unquote

    # 解码URL中的中文文件名
    filename = unquote(filename)

    # 静态文件目录 - 使用绝对路径
    static_dir = os.path.join(os.getcwd(), 'static')
    qr_dir = os.path.join(static_dir, 'qrcodes')

    print(f"🔍 尝试访问文件: {filename}")
    print(f"📁 查找目录: {qr_dir}")

    # 检查文件是否存在
    file_path = os.path.join(qr_dir, filename)
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return f"文件不存在: {filename}", 404

    print(f"✅ 找到文件: {file_path}")
    return send_from_directory(qr_dir, filename)


@main_bp.route('/print-all-qrcodes')
def print_all_qrcodes():
    """批量查看所有二维码页面"""
    materials = Material.query.all()

    html = """
    <html>
        <head>
            <title>打印所有二维码 - 机器人社团</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial; margin: 20px; }
                .qr-container { 
                    display: inline-block; 
                    margin: 15px; 
                    text-align: center;
                    border: 1px solid #ddd;
                    padding: 10px;
                }
                .qr-title { font-weight: bold; margin-bottom: 5px; }
                @media print {
                    body { margin: 0; }
                    .qr-container { page-break-inside: avoid; }
                }
            </style>
        </head>
        <body>
            <h1>🤖 机器人社团物资二维码</h1>
            <button onclick="window.print()">🖨️ 打印所有二维码</button>
            <div>
    """

    for material in materials:
        html += """
            <div class="qr-container">
                <div class="qr-title">{} (#{})</div>
                <div>{}</div>
                <img src="/qrcodes/{}" width="150" height="150">
            </div>
        """.format(material.name, material.id, material.category, material.qr_code)

    html += """
            </div>
        </body>
    </html>
    """
    return html


@main_bp.route('/scan/<int:material_id>')
def scan_redirect(material_id):
    """扫码选择页面 - 美化版本"""
    material = Material.query.get_or_404(material_id)

    # 根据状态显示不同按钮
    if material.status == 'available':
        # 可借用状态
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>物资操作</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}

                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                }}

                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    max-width: 400px;
                    width: 100%;
                    text-align: center;
                    position: relative;
                    overflow: hidden;
                }}

                .container::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 4px;
                    background: linear-gradient(90deg, #52c41a, #73d13d);
                }}

                .header {{
                    margin-bottom: 25px;
                }}

                .header h2 {{
                    color: #2d3748;
                    font-size: 24px;
                    font-weight: 700;
                    margin-bottom: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 10px;
                }}

                .header h3 {{
                    color: #4a5568;
                    font-size: 20px;
                    margin-bottom: 12px;
                }}

                .status {{
                    display: inline-block;
                    padding: 6px 16px;
                    background: #f6ffed;
                    color: #52c41a;
                    border: 1px solid #b7eb8f;
                    border-radius: 20px;
                    font-weight: 600;
                    font-size: 14px;
                    margin-bottom: 20px;
                }}

                .btn-group {{
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }}

                .btn {{
                    display: block;
                    padding: 16px 24px;
                    border: none;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    text-decoration: none;
                    transition: all 0.3s ease;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                }}

                .btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 8px 20px rgba(0,0,0,0.15);
                }}

                .borrow-btn {{
                    background: linear-gradient(135deg, #52c41a, #73d13d);
                    color: white;
                }}

                .borrow-btn:hover {{
                    background: linear-gradient(135deg, #389e0d, #52c41a);
                    box-shadow: 0 8px 20px rgba(82, 196, 26, 0.3);
                }}

                .info-btn {{
                    background: linear-gradient(135deg, #1890ff, #40a9ff);
                    color: white;
                }}

                .info-btn:hover {{
                    background: linear-gradient(135deg, #096dd9, #1890ff);
                    box-shadow: 0 8px 20px rgba(24, 144, 255, 0.3);
                }}

                .icon {{
                    font-size: 18px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🤖 机器人社团</h2>
                    <h3>{material.name}</h3>
                    <div class="status">🟢 可借用</div>
                </div>

                <div class="btn-group">
                    <a href="/borrow/{material_id}" class="btn borrow-btn">
                        <span class="icon">📥</span>
                        <span>借用此物资</span>
                    </a>
                    <a href="/qrinfo/{material_id}" class="btn info-btn">
                        <span class="icon">ℹ️</span>
                        <span>查看详细信息</span>
                    </a>
                </div>
            </div>
        </body>
        </html>
        """
    else:
        # 已借用状态
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>物资操作</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}

                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                }}

                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    max-width: 400px;
                    width: 100%;
                    text-align: center;
                    position: relative;
                    overflow: hidden;
                }}

                .container::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 4px;
                    background: linear-gradient(90deg, #ff4d4f, #ff7875);
                }}

                .header {{
                    margin-bottom: 25px;
                }}

                .header h2 {{
                    color: #2d3748;
                    font-size: 24px;
                    font-weight: 700;
                    margin-bottom: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 10px;
                }}

                .header h3 {{
                    color: #4a5568;
                    font-size: 20px;
                    margin-bottom: 12px;
                }}

                .status {{
                    display: inline-block;
                    padding: 6px 16px;
                    background: #fff2f0;
                    color: #ff4d4f;
                    border: 1px solid #ffccc7;
                    border-radius: 20px;
                    font-weight: 600;
                    font-size: 14px;
                    margin-bottom: 15px;
                }}

                .borrower-info {{
                    background: #f8f9fa;
                    padding: 12px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    font-size: 14px;
                    color: #6c757d;
                }}

                .btn-group {{
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }}

                .btn {{
                    display: block;
                    padding: 16px 24px;
                    border: none;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    text-decoration: none;
                    transition: all 0.3s ease;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                }}

                .btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 8px 20px rgba(0,0,0,0.15);
                }}

                .return-btn {{
                    background: linear-gradient(135deg, #ff4d4f, #ff7875);
                    color: white;
                }}

                .return-btn:hover {{
                    background: linear-gradient(135deg, #d9363e, #ff4d4f);
                    box-shadow: 0 8px 20px rgba(255, 77, 79, 0.3);
                }}

                .info-btn {{
                    background: linear-gradient(135deg, #1890ff, #40a9ff);
                    color: white;
                }}

                .info-btn:hover {{
                    background: linear-gradient(135deg, #096dd9, #1890ff);
                    box-shadow: 0 8px 20px rgba(24, 144, 255, 0.3);
                }}

                .icon {{
                    font-size: 18px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🤖 机器人社团</h2>
                    <h3>{material.name}</h3>
                    <div class="status">🔴 已借出</div>
                    <div class="borrower-info">
                        📍 当前借用人：{material.current_holder}<br>
                        ⏰ 借用时间：{material.borrow_time.strftime('%Y-%m-%d %H:%M') if material.borrow_time else '未知'}
                    </div>
                </div>

                <div class="btn-group">
                    <a href="/return/{material_id}" class="btn return-btn">
                        <span class="icon">📤</span>
                        <span>归还此物资</span>
                    </a>
                    <a href="/qrinfo/{material_id}" class="btn info-btn">
                        <span class="icon">ℹ️</span>
                        <span>查看详细信息</span>
                    </a>
                </div>
            </div>
        </body>
        </html>
        """


@main_bp.route('/qrinfo/<int:material_id>')
def qr_info_page(material_id):
    """二维码信息页面"""
    material = Material.query.get_or_404(material_id)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>物资信息 - {material.name}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}

            .container {{
                background: white;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                max-width: 450px;
                width: 100%;
            }}

            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}

            .header h2 {{
                color: #2d3748;
                font-size: 28px;
                font-weight: 700;
                margin-bottom: 8px;
            }}

            .info-grid {{
                display: grid;
                gap: 15px;
            }}

            .info-item {{
                display: flex;
                justify-content: space-between;
                padding: 12px 0;
                border-bottom: 1px solid #e2e8f0;
            }}

            .info-label {{
                color: #718096;
                font-weight: 500;
            }}

            .info-value {{
                color: #2d3748;
                font-weight: 600;
            }}

            .status-available {{
                color: #52c41a;
            }}

            .status-borrowed {{
                color: #ff4d4f;
            }}

            .back-btn {{
                display: inline-block;
                margin-top: 25px;
                padding: 12px 24px;
                background: #1890ff;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                transition: all 0.3s ease;
            }}

            .back-btn:hover {{
                background: #096dd9;
                transform: translateY(-2px);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>📋 物资详细信息</h2>
                <p>{material.name} 的完整信息</p>
            </div>

            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">物资名称：</span>
                    <span class="info-value">{material.name}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">物资ID：</span>
                    <span class="info-value">#{material.id}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">分类：</span>
                    <span class="info-value">{material.category}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">当前状态：</span>
                    <span class="info-value {'status-available' if material.status == 'available' else 'status-borrowed'}">
                        {'🟢 可借用' if material.status == 'available' else '🔴 已借出'}
                    </span>
                </div>
                <div class="info-item">
                    <span class="info-label">当前借用人：</span>
                    <span class="info-value">{material.current_holder or '无'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">借用时间：</span>
                    <span class="info-value">{material.borrow_time.strftime('%Y-%m-%d %H:%M') if material.borrow_time else '无'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">预计归还：</span>
                    <span class="info-value">{material.expected_return.strftime('%Y-%m-%d %H:%M') if material.expected_return else '无'}</span>
                </div>
            </div>

            <div style="text-align: center;">
                <a href="/scan/{material_id}" class="back-btn">← 返回操作页面</a>
            </div>
        </div>
    </body>
    </html>
    """


@main_bp.route('/return/<int:material_id>')
def return_page(material_id):
    """归还物资页面 - 美化版本"""
    material = Material.query.get_or_404(material_id)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>归还 {material.name}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}

            .container {{
                background: white;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                max-width: 450px;
                width: 100%;
                position: relative;
                overflow: hidden;
            }}

            .container::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, #ff6b6b, #ffa726);
            }}

            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}

            .header h2 {{
                color: #2d3748;
                font-size: 28px;
                font-weight: 700;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }}

            .header p {{
                color: #718096;
                font-size: 16px;
            }}

            .material-card {{
                background: linear-gradient(135deg, #fff5f5, #fed7d7);
                padding: 20px;
                border-radius: 12px;
                border-left: 4px solid #ff6b6b;
                margin-bottom: 25px;
            }}

            .material-card h3 {{
                color: #2d3748;
                font-size: 20px;
                margin-bottom: 12px;
                display: flex;
                align-items: center;
                gap: 8px;
            }}

            .material-info {{
                display: grid;
                gap: 8px;
            }}

            .info-item {{
                display: flex;
                justify-content: space-between;
                padding: 4px 0;
                border-bottom: 1px solid rgba(255, 107, 107, 0.1);
            }}

            .info-label {{
                color: #718096;
                font-weight: 500;
            }}

            .info-value {{
                color: #2d3748;
                font-weight: 600;
            }}

            .form-group {{
                margin-bottom: 20px;
            }}

            .form-group label {{
                display: block;
                color: #4a5568;
                font-weight: 600;
                margin-bottom: 8px;
                font-size: 14px;
            }}

            .input-group {{
                position: relative;
            }}

            .input-group input {{
                width: 100%;
                padding: 14px 16px;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                font-size: 16px;
                transition: all 0.3s ease;
                background: #f7fafc;
            }}

            .input-group input:focus {{
                outline: none;
                border-color: #667eea;
                background: white;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }}

            .input-group input::placeholder {{
                color: #a0aec0;
            }}

            .btn {{
                width: 100%;
                padding: 16px;
                background: linear-gradient(135deg, #ff6b6b, #ffa726);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
            }}

            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(255, 107, 107, 0.3);
            }}

            .btn:active {{
                transform: translateY(0);
            }}

            .btn:disabled {{
                background: #cbd5e0;
                transform: none;
                box-shadow: none;
                cursor: not-allowed;
            }}

            #result {{
                margin-top: 20px;
                padding: 20px;
                border-radius: 12px;
                text-align: center;
                font-weight: 500;
                transition: all 0.3s ease;
            }}

            .success {{
                background: linear-gradient(135deg, #c6f6d5, #9ae6b4);
                color: #22543d;
                border: 2px solid #48bb78;
            }}

            .error {{
                background: linear-gradient(135deg, #fed7d7, #feb2b2);
                color: #742a2a;
                border: 2px solid #f56565;
            }}

            .loading {{
                background: #edf2f7;
                color: #4a5568;
            }}

            .success-icon {{
                font-size: 48px;
                margin-bottom: 10px;
            }}

            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}

            .loading-spinner {{
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid #ffffff;
                border-radius: 50%;
                border-top-color: transparent;
                animation: spin 1s ease-in-out infinite;
                margin-right: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>📤 归还物资</h2>
                <p>请验证身份信息完成归还</p>
            </div>

            <div class="material-card">
                <h3>🎯 物资信息</h3>
                <div class="material-info">
                    <div class="info-item">
                        <span class="info-label">物资名称：</span>
                        <span class="info-value">{material.name}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">分类：</span>
                        <span class="info-value">{material.category}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">当前状态：</span>
                        <span class="info-value" style="color: #e53e3e;">🔴 已借出</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">借用人：</span>
                        <span class="info-value">{material.current_holder or '未知'}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">借用时间：</span>
                        <span class="info-value">{material.borrow_time.strftime('%Y-%m-%d %H:%M') if material.borrow_time else '未知'}</span>
                    </div>
                </div>
            </div>

            <form id="returnForm">
                <div class="form-group">
                    <label for="borrower">👤 借用人姓名</label>
                    <div class="input-group">
                        <input type="text" id="borrower" placeholder="请输入您的姓名" required>
                    </div>
                </div>

                <div class="form-group">
                    <label for="student_id">🎓 学号</label>
                    <div class="input-group">
                        <input type="text" id="student_id" placeholder="请输入您的学号" required>
                    </div>
                </div>

                <button type="submit" class="btn" id="submitBtn">
                    <span>✅ 确认归还</span>
                </button>
            </form>

            <div id="result"></div>
        </div>

        <script>
            document.getElementById('returnForm').addEventListener('submit', async (e) => {{
                e.preventDefault();

                const borrower = document.getElementById('borrower').value.trim();
                const studentId = document.getElementById('student_id').value.trim();
                const submitBtn = document.getElementById('submitBtn');
                const resultDiv = document.getElementById('result');

                if (!borrower || !studentId) {{
                    resultDiv.className = 'error';
                    resultDiv.innerHTML = '❌ 请输入完整的姓名和学号';
                    return;
                }}

                submitBtn.disabled = true;
                submitBtn.innerHTML = '<div class="loading-spinner"></div>验证身份中...';
                resultDiv.className = 'loading';
                resultDiv.innerHTML = '正在验证您的身份信息，请稍候...';

                try {{
                    const response = await fetch('/api/return/{material_id}', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            borrower: borrower,
                            student_id: studentId
                        }})
                    }});

                    const result = await response.json();

                    if (result.success) {{
                        resultDiv.className = 'success';
                        resultDiv.innerHTML = `
                            <div class="success-icon">🎉</div>
                            <div style="font-size: 18px; margin-bottom: 8px;"><strong>${{result.message}}</strong></div>
                            <div>归还时间：${{result.data.return_time}}</div>
                            <div style="margin-top: 15px; font-size: 14px; opacity: 0.8;">感谢您的使用！</div>
                        `;
                        document.getElementById('returnForm').style.display = 'none';
                        submitBtn.style.display = 'none';
                    }} else {{
                        resultDiv.className = 'error';
                        resultDiv.innerHTML = `
                            <div style="font-size: 18px; margin-bottom: 8px;">❌ 操作失败</div>
                            <div>${{result.error}}</div>
                        `;
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = '✅ 确认归还';
                    }}
                }} catch (error) {{
                    resultDiv.className = 'error';
                    resultDiv.innerHTML = `
                        <div style="font-size: 18px; margin-bottom: 8px;">❌ 网络错误</div>
                        <div>请检查网络连接后重试</div>
                    `;
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '✅ 确认归还';
                }}
            }});
        </script>
    </body>
    </html>
    """


@main_bp.route('/api/return/<int:material_id>', methods=['POST'])
def return_material(material_id):
    """归还物资API - 需要身份验证"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求数据无效"}), 400

    borrower = data.get('borrower', '').strip()
    student_id = data.get('student_id', '').strip()

    if not borrower or not student_id:
        return jsonify({"error": "请输入姓名和学号"}), 400

    material = Material.query.get(material_id)
    if not material:
        return jsonify({"error": "物资不存在"}), 404

    if material.status != 'borrowed':
        return jsonify({"error": f"物资 [{material.name}] 当前状态不可归还"}), 400

    # 查找对应的借用记录
    record = BorrowRecord.query.filter_by(
        material_id=material_id,
        status='borrowed'
    ).first()

    if not record:
        return jsonify({"error": "未找到借用记录"}), 400

    # 验证身份信息
    if record.borrower != borrower or record.student_id != student_id:
        return jsonify({"error": "身份验证失败：姓名或学号不匹配"}), 403

    # 身份验证通过，执行归还
    material.status = 'available'
    previous_holder = material.current_holder
    material.current_holder = None
    material.borrow_time = None
    material.expected_return = None

    # 更新借用记录
    record.status = 'returned'
    record.return_time = datetime.now()

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"✅ 成功归还 [{material.name}]",
        "data": {
            "material": material.name,
            "borrower": borrower,
            "return_time": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
    })


@main_bp.route('/debug')
def debug_info():
    """高级调试信息页面"""
    materials = Material.query.all()
    borrow_records = BorrowRecord.query.order_by(BorrowRecord.borrow_time.desc()).limit(20).all()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>管理员调试页面</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
            .material-item {{ 
                padding: 10px; margin: 5px 0; border-left: 4px solid #52c41a; 
                background: #f6ffed; display: flex; justify-content: space-between; align-items: center;
            }}
            .material-item.borrowed {{ border-left-color: #ff4d4f; background: #fff2f0; }}
            .record-item {{ padding: 8px; margin: 3px 0; background: #f0f8ff; border-radius: 3px; }}
            .btn {{ 
                padding: 5px 10px; margin: 0 5px; border: none; border-radius: 3px; 
                cursor: pointer; text-decoration: none; display: inline-block;
            }}
            .available-btn {{ background: #52c41a; color: white; }}
            .borrowed-btn {{ background: #ff4d4f; color: white; }}
            .maintenance-btn {{ background: #faad14; color: white; }}
            .tooltip {{
                position: relative;
                border-bottom: 1px dotted black;
            }}
            .tooltip .tooltiptext {{
                visibility: hidden;
                width: 300px;
                background-color: black;
                color: #fff;
                text-align: center;
                border-radius: 6px;
                padding: 5px;
                position: absolute;
                z-index: 1;
                bottom: 125%;
                left: 50%;
                margin-left: -150px;
                opacity: 0;
                transition: opacity 0.3s;
            }}
            .tooltip:hover .tooltiptext {{
                visibility: visible;
                opacity: 1;
            }}
        </style>
    </head>
    <body>
        <h1>🤖 管理员调试页面</h1>

        <div class="section">
            <h2>📦 物资状态 ({count})</h2>
    """.format(count=len(materials))

    for material in materials:
        status_color = "green" if material.status == 'available' else "red"
        status_text = "🟢 可借用" if material.status == 'available' else "🔴 已借出"

        # 构建悬停提示信息
        tooltip_info = f"""
        物资ID: {material.id}<br>
        名称: {material.name}<br>
        分类: {material.category}<br>
        状态: {material.status}<br>
        当前借用人: {material.current_holder or '无'}<br>
        借用时间: {material.borrow_time.strftime('%Y-%m-%d %H:%M') if material.borrow_time else '无'}<br>
        预计归还: {material.expected_return.strftime('%Y-%m-%d %H:%M') if material.expected_return else '无'}
        """

        html += """
            <div class="material-item {status_class}">
                <div class="tooltip">
                    <strong>{name}</strong> - <span style="color: {color}">{status}</span>
                    <div class="tooltiptext">{tooltip}</div>
                </div>
                <div>
                    <button class="btn available-btn" onclick="updateStatus({id}, 'available')">设为可用</button>
                    <button class="btn borrowed-btn" onclick="updateStatus({id}, 'borrowed')">设为借出</button>
                    <button class="btn maintenance-btn" onclick="updateStatus({id}, 'maintenance')">设为维修</button>
                </div>
            </div>
        """.format(
            status_class=material.status,
            name=material.name,
            color=status_color,
            status=status_text,
            tooltip=tooltip_info,
            id=material.id
        )

    html += """
        </div>

        <div class="section">
            <h2>📋 最近借用记录</h2>
    """

    for record in borrow_records:
        material = Material.query.get(record.material_id)
        status_color = "green" if record.status == 'returned' else "orange"
        status_text = "✅ 已归还" if record.status == 'returned' else "⏳ 借用中"

        material_name = material.name if material else '未知物资'
        return_time = record.return_time.strftime('%m-%d %H:%M') if record.return_time else ""

        html += """
            <div class="record-item">
                <strong>{material_name}</strong> | 
                借用人: {borrower} ({student_id}) | 
                状态: <span style="color: {color}">{status}</span> | 
                借用: {borrow_time} |
                {return_text}
            </div>
        """.format(
            material_name=material_name,
            borrower=record.borrower,
            student_id=record.student_id,
            color=status_color,
            status=status_text,
            borrow_time=record.borrow_time.strftime('%m-%d %H:%M'),
            return_text=f"归还: {return_time}" if return_time else ""
        )

    html += """
        </div>

        <script>
            async function updateStatus(materialId, newStatus) {
                if (!confirm('确定要修改物资状态吗？')) return;

                try {
                    const response = await fetch('/api/admin/update-status', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            material_id: materialId,
                            status: newStatus
                        })
                    });

                    const result = await response.json();
                    if (result.success) {
                        alert('状态更新成功！');
                        location.reload();
                    } else {
                        alert('更新失败: ' + result.error);
                    }
                } catch (error) {
                    alert('网络错误: ' + error);
                }
            }
        </script>
    </body>
    </html>
    """

    return html


@main_bp.route('/api/admin/update-status', methods=['POST'])
def admin_update_status():
    """管理员手动更新物资状态"""
    data = request.get_json()
    material_id = data.get('material_id')
    new_status = data.get('status')

    if not material_id or not new_status:
        return jsonify({"error": "缺少参数"}), 400

    material = Material.query.get(material_id)
    if not material:
        return jsonify({"error": "物资不存在"}), 404

    # 记录旧状态
    old_status = material.status

    # 更新状态
    material.status = new_status

    # 如果设为可用，清空借用信息
    if new_status == 'available':
        material.current_holder = None
        material.borrow_time = None
        material.expected_return = None

        # 如果有未归还的记录，设为已归还
        record = BorrowRecord.query.filter_by(
            material_id=material_id,
            status='borrowed'
        ).first()
        if record:
            record.status = 'returned'
            record.return_time = datetime.now()

    # 如果设为借出，但没有借用人，设为管理员操作
    elif new_status == 'borrowed' and not material.current_holder:
        material.current_holder = "管理员操作"
        material.borrow_time = datetime.now()
        material.expected_return = datetime.now() + timedelta(days=7)

    db.session.commit()

    print(f"🔧 管理员更新: {material.name} {old_status} -> {new_status}")

    return jsonify({
        "success": True,
        "message": f"已更新 {material.name} 状态为 {new_status}",
        "data": {
            "material": material.name,
            "old_status": old_status,
            "new_status": new_status
        }
    })