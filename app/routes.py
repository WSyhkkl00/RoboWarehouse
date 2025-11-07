from flask import Blueprint, request, jsonify, render_template
from datetime import datetime, timedelta
from .models import db, Material, BorrowRecord
from .utils.feishu_bot import send_borrow_notification
from .utils.qr_generator import generate_qr_code

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
    material.expected_return = datetime.now() + timedelta(days=7)  # 默认借用7天

    # 创建借用记录
    record = BorrowRecord(
        material_id=material_id,
        borrower=borrower,
        student_id=student_id,
        borrow_time=datetime.now()
    )

    db.session.add(record)
    db.session.commit()

    # 异步发送飞书通知
    # send_borrow_notification.delay(
    #     material.name,
    #     borrower,
    #     student_id,
    #     material.borrow_time
    # )

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
    """简易管理页面"""
    materials = Material.query.all()

    # 使用双花括号来转义，避免格式化冲突
    html = """
    <html>
        <head>
            <title>机器人社团物资管理</title>
            <meta charset="utf-8">
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 40px; 
                    line-height: 1.6;
                }}
                .material {{ 
                    border: 1px solid #ddd; 
                    padding: 15px; 
                    margin: 10px 0; 
                    border-radius: 5px; 
                }}
                .available {{ 
                    background: #f0fff0; 
                    border-left: 4px solid #52c41a;
                }}
                .borrowed {{ 
                    background: #fff0f0; 
                    border-left: 4px solid #ff4d4f;
                }}
                h1 {{ 
                    color: #1890ff; 
                    border-bottom: 2px solid #1890ff;
                    padding-bottom: 10px;
                }}
                a {{ 
                    color: #1890ff; 
                    text-decoration: none;
                }}
                a:hover {{ 
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            <h1>🤖 机器人社团物资管理</h1>
            <p>共 <strong>{count}</strong> 个物资</p>
            <div>
    """.format(count=len(materials))

    for material in materials:
        status_text = "🟢 可借用" if material.status == 'available' else "🔴 已借出"
        status_class = "available" if material.status == 'available' else "borrowed"

        html += """
            <div class="material {status_class}">
                <h3>{name} (#{id})</h3>
                <p><strong>分类:</strong> {category} | <strong>状态:</strong> {status_text}</p>
                <p><strong>当前持有人:</strong> {holder}</p>
                <p><a href="/qrcodes/{qr_code}" target="_blank">📷 查看/打印二维码</a></p>
                <p><a href="/borrow/{id}">🔗 直接借用链接</a></p>
            </div>
        """.format(
            status_class=status_class,
            name=material.name,
            id=material.id,
            category=material.category,
            status_text=status_text,
            holder=material.current_holder or '无',
            qr_code=material.qr_code
        )

    html += """
            </div>
            <hr>
            <p>
                <a href="/api/materials">📊 JSON数据接口</a> | 
                <a href="/">🏠 返回首页</a>
            </p>
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
    """扫码选择页面 - 选择借用或归还"""
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
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    margin: 50px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    display: inline-block;
                }}
                .btn {{
                    display: block;
                    width: 200px;
                    padding: 15px;
                    margin: 10px auto;
                    border: none;
                    border-radius: 8px;
                    font-size: 16px;
                    cursor: pointer;
                    text-decoration: none;
                }}
                .borrow-btn {{
                    background: #52c41a;
                    color: white;
                }}
                .info-btn {{
                    background: #1890ff;
                    color: white;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>🤖 机器人社团</h2>
                <h3>{material.name}</h3>
                <p>状态: <span style="color: green;">🟢 可借用</span></p>

                <a href="/borrow/{material_id}" class="btn borrow-btn">
                    📥 借用此物资
                </a>
                <a href="/qrinfo/{material_id}" class="btn info-btn">
                    ℹ️ 查看信息
                </a>
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
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    margin: 50px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    display: inline-block;
                }}
                .btn {{
                    display: block;
                    width: 200px;
                    padding: 15px;
                    margin: 10px auto;
                    border: none;
                    border-radius: 8px;
                    font-size: 16px;
                    cursor: pointer;
                    text-decoration: none;
                }}
                .return-btn {{
                    background: #ff4d4f;
                    color: white;
                }}
                .info-btn {{
                    background: #1890ff;
                    color: white;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>🤖 机器人社团</h2>
                <h3>{material.name}</h3>
                <p>状态: <span style="color: red;">🔴 已借出</span></p>
                <p>借用人: {material.current_holder}</p>

                <a href="/return/{material_id}" class="btn return-btn">
                    📤 归还此物资
                </a>
                <a href="/qrinfo/{material_id}" class="btn info-btn">
                    ℹ️ 查看信息
                </a>
            </div>
        </body>
        </html>
        """


@main_bp.route('/return/<int:material_id>')
def return_page(material_id):
    """归还物资页面 - 需要身份验证"""
    material = Material.query.get_or_404(material_id)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>归还 {material.name}</title>
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
            h2 {{ color: #ff4d4f; margin-top: 0; }}
            .material-info {{ 
                background: #fff2f0; 
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
            .btn {{
                width: 100%;
                padding: 12px;
                background: #ff4d4f;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
            }}
            .btn:hover {{ background: #ff7875; }}
            .btn:disabled {{ background: #ccc; cursor: not-allowed; }}
            #result {{ margin-top: 20px; padding: 15px; border-radius: 5px; }}
            .success {{ background: #f6ffed; border: 1px solid #b7eb8f; color: #52c41a; }}
            .error {{ background: #fff2f0; border: 1px solid #ffccc7; color: #ff4d4f; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📤 归还物资</h2>
            <div class="material-info">
                <h3>{material.name}</h3>
                <p><strong>分类:</strong> {material.category}</p>
                <p><strong>当前借用人:</strong> {material.current_holder or '未知'}</p>
                <p><strong>借用时间:</strong> {material.borrow_time.strftime('%Y-%m-%d %H:%M') if material.borrow_time else '未知'}</p>
            </div>

            <form id="returnForm">
                <div class="form-group">
                    <label for="borrower">姓名 *</label>
                    <input type="text" id="borrower" placeholder="请输入借用人姓名" required>
                </div>
                <div class="form-group">
                    <label for="student_id">学号 *</label>
                    <input type="text" id="student_id" placeholder="请输入学号" required>
                </div>
                <button type="submit" class="btn" id="submitBtn">确认归还</button>
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
                    resultDiv.innerHTML = '❌ 请输入姓名和学号';
                    return;
                }}

                submitBtn.disabled = true;
                submitBtn.textContent = '验证中...';
                resultDiv.innerHTML = '验证身份信息...';

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
                            ✅ <strong>${{result.message}}</strong><br>
                            🕒 归还时间: ${{result.data.return_time}}
                        `;
                        document.getElementById('returnForm').style.display = 'none';
                    }} else {{
                        resultDiv.className = 'error';
                        resultDiv.innerHTML = `❌ ${{result.error}}`;
                        submitBtn.disabled = false;
                        submitBtn.textContent = '确认归还';
                    }}
                }} catch (error) {{
                    resultDiv.className = 'error';
                    resultDiv.innerHTML = '❌ 网络错误，请重试';
                    submitBtn.disabled = false;
                    submitBtn.textContent = '确认归还';
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