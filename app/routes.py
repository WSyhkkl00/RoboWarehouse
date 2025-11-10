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
        return jsonify({"error": f"物资 [{material.model_name} ({material.serial_number})] 当前不可用，状态: {material.status}"}), 400

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

    try:
        feishu_notifier.send_borrow_notification(
            f"{material.model_name} ({material.serial_number})",
            borrower,
            student_id,
            material.borrow_time
        )
    except Exception as e:
        print(f"⚠️ 飞书通知发送失败，但不影响借用: {e}")

    return jsonify({
        "success": True,
        "message": f"✅ 成功借用 [{material.model_name} ({material.serial_number})]",
        "data": {
            "material": f"{material.model_name} ({material.serial_number})",
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
    """优化版管理页面 - 简洁清晰版本"""
    materials = Material.query.all()

    # 按型号分组统计
    from collections import defaultdict
    category_stats = defaultdict(lambda: {'total': 0, 'available': 0, 'borrowed': 0, 'materials': []})

    for material in materials:
        category_key = material.model_name
        category_stats[category_key]['total'] += 1
        category_stats[category_key]['materials'].append(material)
        if material.status == 'available':
            category_stats[category_key]['available'] += 1
        elif material.status == 'borrowed':
            category_stats[category_key]['borrowed'] += 1

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>机器人实验室物资管理</title>
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
                background: #f8fafc;
                min-height: 100vh;
                padding: 20px;
                color: #2d3748;
            }}

            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}

            .header {{
                background: white;
                padding: 25px;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                margin-bottom: 25px;
                text-align: center;
                border: 1px solid #e2e8f0;
            }}

            .header h1 {{
                color: #2d3748;
                font-size: 28px;
                font-weight: 700;
                margin-bottom: 8px;
            }}

            .header p {{
                color: #718096;
                margin-bottom: 15px;
            }}

            .stats {{
                display: flex;
                justify-content: center;
                gap: 20px;
                margin-top: 15px;
                flex-wrap: wrap;
            }}

            .stat-card {{
                background: white;
                color: #2d3748;
                padding: 15px;
                border-radius: 8px;
                text-align: center;
                min-width: 100px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                border-left: 4px solid #667eea;
                transition: all 0.3s ease;
            }}

            .stat-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }}

            .stat-number {{
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 4px;
            }}

            .stat-label {{
                font-size: 12px;
                color: #718096;
            }}

            .category-grid {{
                display: grid;
                gap: 20px;
                grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            }}

            .category-card {{
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                border: 1px solid #e2e8f0;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }}

            /* 正常卡片效果 */
            .category-card:hover {{
                transform: translateY(-3px);
                box-shadow: 0 4px 15px rgba(0,0,0,0.12);
            }}

            /* 已借完卡片效果 */
            .category-card.sold-out {{
                background: linear-gradient(135deg, #fff5f5, #fed7d7);
                border: 1px solid #feb2b2;
            }}

            .category-card.sold-out::before {{
                content: '🈳 已借完';
                position: absolute;
                top: 10px;
                right: -30px;
                background: #e53e3e;
                color: white;
                padding: 5px 40px;
                font-size: 12px;
                font-weight: 700;
                transform: rotate(45deg);
                box-shadow: 0 2px 8px rgba(229, 62, 62, 0.3);
            }}

            .category-card.sold-out:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(229, 62, 62, 0.2);
            }}

            .category-card.sold-out .category-name {{
                color: #742a2a;
            }}

            .category-card.sold-out .category-name-short {{
                color: #9b2c2c;
            }}

            .category-card.sold-out .mini-stat.available {{
                background: #fed7d7;
                color: #c53030;
                border: 1px solid #feb2b2;
            }}

            .category-header {{
                margin-bottom: 15px;
                padding-bottom: 15px;
                border-bottom: 1px solid #e2e8f0;
            }}

            .category-card.sold-out .category-header {{
                border-bottom-color: #feb2b2;
            }}

            .category-name {{
                font-size: 18px;
                font-weight: 700;
                color: #2d3748;
                margin-bottom: 8px;
                line-height: 1.3;
                word-break: break-word;
            }}

            .category-name-short {{
                font-size: 14px;
                color: #718096;
                font-weight: 500;
                margin-bottom: 8px;
            }}

            .category-stats {{
                display: flex;
                gap: 12px;
            }}

            .mini-stat {{
                text-align: center;
                padding: 8px;
                border-radius: 6px;
                min-width: 60px;
                font-size: 12px;
                transition: all 0.3s ease;
            }}

            .mini-stat:hover {{
                transform: scale(1.05);
            }}

            .mini-stat.total {{
                background: #ebf8ff;
                color: #3182ce;
            }}

            .mini-stat.available {{
                background: #f0fff4;
                color: #38a169;
            }}

            .mini-stat.borrowed {{
                background: #fff5f5;
                color: #e53e3e;
            }}

            .mini-number {{
                font-size: 16px;
                font-weight: 700;
                margin-bottom: 2px;
            }}

            .mini-label {{
                font-size: 11px;
                font-weight: 600;
            }}

            .items-list {{
                margin-top: 15px;
            }}

            .item-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 0;
                border-bottom: 1px solid #f7fafc;
                transition: all 0.3s ease;
            }}

            .item-row:hover {{
                background: #f8f9fa;
                border-radius: 6px;
                padding: 10px 8px;
            }}

            .item-row:last-child {{
                border-bottom: none;
            }}

            .item-info {{
                display: flex;
                align-items: center;
                gap: 10px;
                flex: 1;
                min-width: 0;
            }}

            .item-serial {{
                font-weight: 600;
                color: #4a5568;
                font-size: 14px;
                min-width: 70px;
                flex-shrink: 0;
            }}

            .item-status {{
                padding: 4px 8px;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 600;
                flex-shrink: 0;
            }}

            .status-available {{
                background: #f0fff4;
                color: #38a169;
                border: 1px solid #9ae6b4;
            }}

            .status-borrowed {{
                background: #fed7d7;
                color: #e53e3e;
                border: 1px solid #fc8181;
            }}

            .item-holder {{
                font-size: 12px;
                color: #718096;
                flex: 1;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                min-width: 0;
            }}

            .item-actions {{
                display: flex;
                gap: 6px;
                flex-shrink: 0;
            }}

            .action-btn {{
                padding: 6px 10px;
                border: none;
                border-radius: 5px;
                font-size: 11px;
                font-weight: 600;
                cursor: pointer;
                text-decoration: none;
                transition: all 0.2s;
                white-space: nowrap;
            }}

            .action-btn:hover {{
                transform: translateY(-1px);
                opacity: 0.9;
            }}

            .qr-btn {{
                background: #3182ce;
                color: white;
            }}

            .borrow-btn {{
                background: #38a169;
                color: white;
            }}

            .detail-btn {{
                background: #805ad5;
                color: white;
            }}

            /* 已借完卡片的按钮样式 */
            .category-card.sold-out .borrow-btn {{
                background: #a0aec0;
                color: #718096;
                cursor: not-allowed;
            }}

            .category-card.sold-out .borrow-btn:hover {{
                transform: none;
                opacity: 1;
            }}

            .footer {{
                margin-top: 30px;
                text-align: center;
                padding: 20px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                border: 1px solid #e2e8f0;
            }}

            .footer-links {{
                display: flex;
                justify-content: center;
                gap: 15px;
                flex-wrap: wrap;
            }}

            .footer-link {{
                padding: 8px 16px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 14px;
                transition: all 0.3s ease;
            }}

            .footer-link:hover {{
                background: #5a67d8;
                transform: translateY(-1px);
            }}

            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(10px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}

            .category-card {{
                animation: fadeIn 0.4s ease forwards;
            }}

            .availability-badge {{
                display: inline-block;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
                margin-left: 8px;
            }}

            .available-badge {{
                background: #f0fff4;
                color: #38a169;
                border: 1px solid #9ae6b4;
            }}

            .soldout-badge {{
                background: #fed7d7;
                color: #e53e3e;
                border: 1px solid #fc8181;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 机器人实验室物资管理</h1>
                <p>按型号分类查看物资状态</p>

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

            <div class="category-grid">
""".format(
        total_count=len(materials),
        available_count=len([m for m in materials if m.status == 'available']),
        borrowed_count=len([m for m in materials if m.status == 'borrowed'])
    )

    # 型号名称映射
    name_mapping = {
        'C型开发板（stm32F407）': 'C型开发板',
        'C620电调（3508用）': 'C620电调',
        '达妙4310电机': '4310电机',
        '大疆官方遥控器': '大疆遥控器',
        '大疆官方遥控器接收机': '遥控器接收机'
    }

    # 按型号分组显示
    for model_name, stats in category_stats.items():
        model_materials = stats['materials']
        short_name = name_mapping.get(model_name, model_name)

        # 判断是否已借完
        is_sold_out = stats['available'] == 0 and stats['total'] > 0
        card_class = "category-card sold-out" if is_sold_out else "category-card"

        # 可用性徽章
        availability_badge = """
            <span class="availability-badge soldout-badge">🈳 已借完</span>
        """ if is_sold_out else """
            <span class="availability-badge available-badge">✅ 有库存</span>
        """

        html += """
                <div class="{card_class}" style="animation-delay: {delay}ms">
                    <div class="category-header">
                        <div>
                            <div class="category-name">{model_name} {availability_badge}</div>
                            <div class="category-name-short">{short_name}</div>
                        </div>
                        <div class="category-stats">
                            <div class="mini-stat total">
                                <div class="mini-number">{total}</div>
                                <div class="mini-label">总数</div>
                            </div>
                            <div class="mini-stat available">
                                <div class="mini-number">{available}</div>
                                <div class="mini-label">可用</div>
                            </div>
                            <div class="mini-stat borrowed">
                                <div class="mini-number">{borrowed}</div>
                                <div class="mini-label">已借</div>
                            </div>
                        </div>
                    </div>

                    <div class="items-list">
        """.format(
            card_class=card_class,
            delay=(list(category_stats.keys()).index(model_name) * 100) % 400,
            model_name=model_name,
            short_name=short_name,
            availability_badge=availability_badge,
            total=stats['total'],
            available=stats['available'],
            borrowed=stats['borrowed']
        )

        # 显示该型号下的每个物资
        for material in model_materials:
            status_class = "status-available" if material.status == 'available' else "status-borrowed"
            status_text = "可用" if material.status == 'available' else "已借"

            html += """
                        <div class="item-row">
                            <div class="item-info">
                                <span class="item-serial">{serial_number}</span>
                                <span class="item-status {status_class}">{status_text}</span>
                                <span class="item-holder">{holder_display}</span>
                            </div>
                            <div class="item-actions">
                                <a href="/qrcodes/{qr_code}" target="_blank" class="action-btn qr-btn">二维码</a>
                                {borrow_button}
                                <a href="/qrinfo/{material_id}" class="action-btn detail-btn">详情</a>
                            </div>
                        </div>
            """.format(
                serial_number=material.serial_number,
                status_class=status_class,
                status_text=status_text,
                holder_display=material.current_holder if material.current_holder else '可借用',
                qr_code=material.qr_code,
                material_id=material.id,
                borrow_button='<a href="/borrow/{}" class="action-btn borrow-btn">借用</a>'.format(
                    material.id) if material.status == 'available' else '<span class="action-btn borrow-btn" style="background: #a0aec0; color: #718096; cursor: not-allowed;">借用</span>'
            )

        html += """
                    </div>
                </div>
        """

    html += """
            </div>

            <div class="footer">
                <div class="footer-links">
                    <a href="/api/materials" class="footer-link">📊 JSON数据</a>
                    <a href="/debug" class="footer-link">🔧 调试</a>
                    <a href="/print-qrcodes" class="footer-link">🖨️ 打印二维码</a>
                    <a href="/" class="footer-link">🏠 首页</a>
                </div>
            </div>
        </div>
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
        f"{material.model_name} ({material.serial_number})",
        f"{material.model_name} ({material.serial_number})",
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
        """.format(f"{material.model_name} ({material.serial_number})", material.id, material.category,
                   material.qr_code)

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
                    <h3>{material.model_name} ({material.serial_number})</h3>
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
                    <h3>{material.model_name} ({material.serial_number})</h3>
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
        <title>物资信息 - {material.model_name} ({material.serial_number})</title>
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
                <p>{material.model_name} ({material.serial_number}) 的完整信息</p>
            </div>

            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">物资名称：</span>
                    <span class="info-value">{material.model_name} ({material.serial_number})</span>
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
         <title>归还 {material.model_name} ({material.serial_number})</title>
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
                        <span class="info-value">{material.model_name} ({material.serial_number})</span>  
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
        "message": f"✅ 成功归还 [{material.model_name} ({material.serial_number})]",
        "data": {
            "material": f"{material.model_name} ({material.serial_number})",
            "borrower": borrower,
            "return_time": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
    })


@main_bp.route('/debug', methods=['GET', 'POST'])
def debug_info():
    """高级调试信息页面 - 添加密码保护"""

    # 检查密码
    if request.method == 'POST':
        password = request.form.get('password')
        if password != '12345678':
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>管理员登录</title>
                <style>
                    body { font-family: Arial; margin: 50px; text-align: center; }
                    .login-box { max-width: 400px; margin: 0 auto; padding: 30px; border: 1px solid #ddd; border-radius: 10px; }
                    input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
                    button { background: #667eea; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
                    .error { color: red; margin-top: 10px; }
                </style>
            </head>
            <body>
                <div class="login-box">
                    <h2>🔧 管理员登录</h2>
                    <p>请输入管理员密码</p>
                    <form method="POST">
                        <input type="password" name="password" placeholder="请输入密码" required>
                        <button type="submit">登录</button>
                    </form>
                    <div class="error">❌ 密码错误，请重试</div>
                </div>
            </body>
            </html>
            """

    # 如果是GET请求，显示登录页面
    if request.method == 'GET':
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>管理员登录</title>
            <style>
                body { font-family: Arial; margin: 50px; text-align: center; background: #f8fafc; }
                .login-box { 
                    max-width: 400px; 
                    margin: 0 auto; 
                    padding: 40px; 
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    border: 1px solid #e2e8f0;
                }
                h2 { color: #2d3748; margin-bottom: 10px; }
                p { color: #718096; margin-bottom: 20px; }
                input { 
                    width: 100%; 
                    padding: 12px; 
                    margin: 15px 0; 
                    border: 1px solid #e2e8f0; 
                    border-radius: 8px;
                    font-size: 16px;
                    transition: border-color 0.3s;
                }
                input:focus {
                    outline: none;
                    border-color: #667eea;
                    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                }
                button { 
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white; 
                    padding: 12px 30px; 
                    border: none; 
                    border-radius: 8px; 
                    cursor: pointer; 
                    font-size: 16px;
                    font-weight: 600;
                    transition: all 0.3s;
                    width: 100%;
                }
                button:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3);
                }
            </style>
        </head>
        <body>
            <div class="login-box">
                <h2>🔧 管理员登录</h2>
                <p>请输入管理员密码访问调试页面</p>
                <form method="POST">
                    <input type="password" name="password" placeholder="请输入密码" required>
                    <button type="submit">进入管理后台</button>
                </form>
            </div>
        </body>
        </html>
        """

    # 密码正确，显示调试页面
    materials = Material.query.all()
    borrow_records = BorrowRecord.query.order_by(BorrowRecord.borrow_time.desc()).limit(50).all()

    html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>管理员调试页面</title>
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
                    background: #f8fafc;
                    min-height: 100vh;
                    padding: 20px;
                    color: #2d3748;
                }}

                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                }}

                .header {{
                    background: white;
                    padding: 25px;
                    border-radius: 12px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                    margin-bottom: 25px;
                    text-align: center;
                    border: 1px solid #e2e8f0;
                }}

                .header h1 {{
                    color: #2d3748;
                    font-size: 28px;
                    font-weight: 700;
                    margin-bottom: 8px;
                }}

                .quick-actions {{
                    display: flex;
                    justify-content: center;
                    gap: 15px;
                    margin: 20px 0;
                    flex-wrap: wrap;
                }}

                .action-btn {{
                    padding: 10px 20px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 600;
                    transition: all 0.3s;
                    border: none;
                    cursor: pointer;
                    font-size: 14px;
                }}

                .action-btn:hover {{
                    background: #5a67d8;
                    transform: translateY(-2px);
                }}

                .danger-btn {{
                    background: #e53e3e;
                }}

                .danger-btn:hover {{
                    background: #c53030;
                }}

                .success-btn {{
                    background: #38a169;
                }}

                .success-btn:hover {{
                    background: #2f855a;
                }}

                .section {{
                    background: white;
                    margin: 20px 0;
                    padding: 25px;
                    border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                    border: 1px solid #e2e8f0;
                }}

                .section h2 {{
                    color: #2d3748;
                    font-size: 22px;
                    font-weight: 700;
                    margin-bottom: 20px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #e2e8f0;
                }}

                .material-grid {{
                    display: grid;
                    gap: 15px;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                }}

                .material-item {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #52c41a;
                    transition: all 0.3s;
                }}

                .material-item.borrowed {{
                    border-left-color: #ff4d4f;
                    background: #fff5f5;
                }}

                .material-item.maintenance {{
                    border-left-color: #faad14;
                    background: #fffbe6;
                }}

                .material-item:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }}

                .material-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 10px;
                }}

                .material-name {{
                    font-weight: 700;
                    color: #2d3748;
                    font-size: 16px;
                }}

                .material-id {{
                    color: #718096;
                    font-size: 12px;
                }}

                .material-status {{
                    padding: 4px 8px;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: 600;
                }}

                .status-available {{
                    background: #f0fff4;
                    color: #38a169;
                    border: 1px solid #9ae6b4;
                }}

                .status-borrowed {{
                    background: #fed7d7;
                    color: #e53e3e;
                    border: 1px solid #fc8181;
                }}

                .status-maintenance {{
                    background: #fff7e6;
                    color: #fa8c16;
                    border: 1px solid #ffc069;
                }}

                .material-details {{
                    font-size: 13px;
                    color: #718096;
                    line-height: 1.5;
                }}

                .material-actions {{
                    display: flex;
                    gap: 8px;
                    margin-top: 10px;
                }}

                .small-btn {{
                    padding: 4px 8px;
                    border: none;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s;
                }}

                .small-btn:hover {{
                    opacity: 0.9;
                    transform: translateY(-1px);
                }}

                .records-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 15px;
                }}

                .records-table th,
                .records-table td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #e2e8f0;
                }}

                .records-table th {{
                    background: #f7fafc;
                    font-weight: 600;
                    color: #4a5568;
                }}

                .records-table tr:hover {{
                    background: #f8f9fa;
                }}

                .status-badge {{
                    padding: 4px 8px;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: 600;
                }}

                .returned {{
                    background: #f0fff4;
                    color: #38a169;
                }}

                .borrowing {{
                    background: #fff7e6;
                    color: #fa8c16;
                }}

                .search-box {{
                    margin-bottom: 20px;
                }}

                .search-box input {{
                    width: 100%;
                    padding: 12px;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    font-size: 14px;
                }}

                .search-box input:focus {{
                    outline: none;
                    border-color: #667eea;
                    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                }}

                .stats-cards {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin-bottom: 20px;
                }}

                .stat-card {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                    border: 1px solid #e2e8f0;
                }}

                .stat-number {{
                    font-size: 24px;
                    font-weight: 700;
                    margin-bottom: 5px;
                }}

                .stat-label {{
                    font-size: 12px;
                    color: #718096;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔧 管理员调试页面</h1>
                    <p>系统管理和监控</p>

                    <div class="quick-actions">
                        <a href="/admin" class="action-btn">📊 返回管理页面</a>
                        <button onclick="generateAllQRCodes()" class="action-btn success-btn">🔄 重新生成所有二维码</button>
                        <button onclick="exportData()" class="action-btn">📤 导出数据</button>
                        <button onclick="clearAllRecords()" class="action-btn danger-btn">🗑️ 清空借用记录</button>
                    </div>
                </div>

                <div class="stats-cards">
                    <div class="stat-card">
                        <div class="stat-number">{total_materials}</div>
                        <div class="stat-label">物资总数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{available_materials}</div>
                        <div class="stat-label">可借用物资</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{borrowed_materials}</div>
                        <div class="stat-label">已借出物资</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{total_records}</div>
                        <div class="stat-label">总借用记录</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{active_records}</div>
                        <div class="stat-label">活跃借用</div>
                    </div>
                </div>

                <div class="section">
                    <h2>📦 物资管理 ({material_count})</h2>
                    <div class="search-box">
                        <input type="text" id="materialSearch" placeholder="🔍 搜索物资名称或编号..." onkeyup="searchMaterials()">
                    </div>
                    <div class="material-grid" id="materialGrid">
        """.format(
        total_materials=len(materials),
        available_materials=len([m for m in materials if m.status == 'available']),
        borrowed_materials=len([m for m in materials if m.status == 'borrowed']),
        total_records=len(borrow_records),
        active_records=len([r for r in borrow_records if r.status == 'borrowed']),
        material_count=len(materials)
    )

    for material in materials:
        status_class = "status-available" if material.status == 'available' else "status-borrowed"
        status_class = "status-maintenance" if material.status == 'maintenance' else status_class
        status_text = "可用" if material.status == 'available' else "借出"
        status_text = "维修" if material.status == 'maintenance' else status_text

        item_class = "material-item"
        if material.status == 'borrowed':
            item_class += " borrowed"
        elif material.status == 'maintenance':
            item_class += " maintenance"

        html += """
                    <div class="{}" data-name="{}" data-serial="{}">
                        <div class="material-header">
                            <div>
                                <div class="material-name">{}</div>
                                <div class="material-id">#{}</div>
                            </div>
                            <div class="material-status {}">{}</div>
                        </div>
                        <div class="material-details">
                            <div>编号: {}</div>
                            <div>分类: {}</div>
                            <div>借用人: {}</div>
                            <div>借用时间: {}</div>
                        </div>
                        <div class="material-actions">
                            <button class="small-btn" style="background: #3182ce; color: white;" onclick="updateStatus({}, 'available')">设为可用</button>
                            <button class="small-btn" style="background: #e53e3e; color: white;" onclick="updateStatus({}, 'borrowed')">设为借出</button>
                            <button class="small-btn" style="background: #faad14; color: white;" onclick="updateStatus({}, 'maintenance')">设为维修</button>
                            <button class="small-btn" style="background: #805ad5; color: white;" onclick="viewDetails({})">详情</button>
                        </div>
                    </div>
        """.format(
            item_class,
            material.model_name.lower(),
            material.serial_number.lower(),
            material.model_name,
            material.id,
            status_class,
            status_text,
            material.serial_number,
            material.category,
            material.current_holder or '无',
            material.borrow_time.strftime('%m-%d %H:%M') if material.borrow_time else '无',
            material.id, material.id, material.id, material.id
        )

    html += """
                </div>
            </div>

            <div class="section">
                <h2>📋 最近借用记录 (最近50条)</h2>
                <div class="search-box">
                    <input type="text" id="recordSearch" placeholder="🔍 搜索借用人或学号..." onkeyup="searchRecords()">
                </div>
                <table class="records-table" id="recordsTable">
                    <thead>
                        <tr>
                            <th>物资</th>
                            <th>借用人</th>
                            <th>学号</th>
                            <th>借用时间</th>
                            <th>归还时间</th>
                            <th>状态</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
    """

    for record in borrow_records:
        material = Material.query.get(record.material_id)
        material_name = material.model_name if material else '未知物资'
        status_class = "returned" if record.status == 'returned' else "borrowing"
        status_text = "✅ 已归还" if record.status == 'returned' else "⏳ 借用中"

        html += """
                        <tr>
                            <td>{}</td>
                            <td>{}</td>
                            <td>{}</td>
                            <td>{}</td>
                            <td>{}</td>
                            <td><span class="status-badge {}">{}</span></td>
                            <td>
                                <button class="small-btn" style="background: #38a169; color: white;" onclick="forceReturn({})">强制归还</button>
                            </td>
                        </tr>
        """.format(
            material_name,
            record.borrower,
            record.student_id or '无',
            record.borrow_time.strftime('%Y-%m-%d %H:%M'),
            record.return_time.strftime('%Y-%m-%d %H:%M') if record.return_time else '未归还',
            status_class,
            status_text,
            record.id
        )

    html += """
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            function searchMaterials() {
                const input = document.getElementById('materialSearch');
                const filter = input.value.toLowerCase();
                const items = document.querySelectorAll('.material-item');

                items.forEach(item => {
                    const name = item.getAttribute('data-name');
                    const serial = item.getAttribute('data-serial');
                    if (name.includes(filter) || serial.includes(filter)) {
                        item.style.display = 'block';
                    } else {
                        item.style.display = 'none';
                    }
                });
            }

            function searchRecords() {
                const input = document.getElementById('recordSearch');
                const filter = input.value.toLowerCase();
                const rows = document.querySelectorAll('.records-table tbody tr');

                rows.forEach(row => {
                    const text = row.textContent.toLowerCase();
                    if (text.includes(filter)) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
            }

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

            async function forceReturn(recordId) {
                if (!confirm('确定要强制归还此物资吗？')) return;

                try {
                    const response = await fetch('/api/admin/force-return', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            record_id: recordId
                        })
                    });

                    const result = await response.json();
                    if (result.success) {
                        alert('强制归还成功！');
                        location.reload();
                    } else {
                        alert('操作失败: ' + result.error);
                    }
                } catch (error) {
                    alert('网络错误: ' + error);
                }
            }

            async function generateAllQRCodes() {
                if (!confirm('确定要重新生成所有二维码吗？')) return;

                try {
                    const response = await fetch('/api/generate-qrcodes');
                    const result = await response.json();
                    alert(result.message);
                } catch (error) {
                    alert('操作失败: ' + error);
                }
            }

            function exportData() {
                alert('导出功能开发中...');
            }

            function clearAllRecords() {
                if (!confirm('⚠️ 确定要清空所有借用记录吗？此操作不可恢复！')) return;
                alert('清空记录功能开发中...');
            }

            function viewDetails(materialId) {
                window.open('/qrinfo/' + materialId, '_blank');
            }
        </script>
    </body>
    </html>
    """
    return html


# 添加强制归还API
@main_bp.route('/api/admin/force-return', methods=['POST'])
def admin_force_return():
    """管理员强制归还物资"""
    data = request.get_json()
    record_id = data.get('record_id')

    if not record_id:
        return jsonify({"error": "缺少参数"}), 400

    record = BorrowRecord.query.get(record_id)
    if not record:
        return jsonify({"error": "记录不存在"}), 404

    material = Material.query.get(record.material_id)
    if not material:
        return jsonify({"error": "物资不存在"}), 404

    # 强制归还
    material.status = 'available'
    material.current_holder = None
    material.borrow_time = None
    material.expected_return = None

    record.status = 'returned'
    record.return_time = datetime.now()

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"✅ 已强制归还 [{material.model_name} ({material.serial_number})]",
        "data": {
            "material": f"{material.model_name} ({material.serial_number})",
            "borrower": record.borrower,
            "return_time": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
    })


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

    return jsonify({
        "success": True,
        "message": f"已更新 {material.model_name} ({material.serial_number}) 状态为 {new_status}",
        "data": {
            "material": f"{material.model_name} ({material.serial_number})",
            "old_status": old_status,
            "new_status": new_status
        }
    })