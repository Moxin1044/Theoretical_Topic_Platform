from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from urllib.parse import urlparse  # Using Python's built-in URL parsing
from config import Config
from models import db, User, Question, Paper
from sqlalchemy import or_
from flask_migrate import Migrate
import pandas as pd
import io
import csv
from datetime import datetime
import os
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
migrate = Migrate(app, db)  # Initialize Flask-Migrate

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user is None or not user.check_password(request.form['password']):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# Frontend routes
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    papers = Paper.query.order_by(Paper.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('index.html', papers=papers)

@app.route('/paper/<int:id>')
def view_paper(id):
    paper = Paper.query.get_or_404(id)
    return render_template('paper.html', paper=paper)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    questions = Question.query.filter(
        or_(
            Question.content.ilike(f'%{query}%'),
            Question.correct_answer.ilike(f'%{query}%')
        )
    ).order_by(Question.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('search.html', questions=questions, query=query)

# Admin routes
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('index'))
    questions_count = Question.query.count()
    papers_count = Paper.query.count()
    users_count = User.query.count()
    return render_template('admin/dashboard.html',
                         questions_count=questions_count,
                         papers_count=papers_count,
                         users_count=users_count)

@app.route('/admin/questions', methods=['GET', 'POST'])
@login_required
def manage_questions():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('index'))
    if request.method == 'POST':
        question = Question(
            type=request.form['type'],
            content=request.form['content'],
            options=request.form.getlist('options[]') if 'options[]' in request.form else None,
            correct_answer=request.form['correct_answer'],
            explanation=request.form['explanation'],
            created_by=current_user
        )
        db.session.add(question)
        db.session.commit()
        flash('Question added successfully.')
        return redirect(url_for('manage_questions'))
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    if query:
        questions = Question.query.filter(
            or_(
                Question.content.ilike(f'%{query}%'),
                Question.correct_answer.ilike(f'%{query}%')
            )
        ).order_by(Question.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    else:
        questions = Question.query.order_by(Question.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('admin/questions.html', questions=questions, query=query)

@app.route('/admin/papers', methods=['GET', 'POST'])
@login_required
def manage_papers():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('index'))
    if request.method == 'POST':
        paper = Paper(
            title=request.form['title'],
            description=request.form['description'],
            created_by=current_user
        )
        question_ids = request.form.getlist('questions[]')
        questions = Question.query.filter(Question.id.in_(question_ids)).all()
        paper.questions = questions
        db.session.add(paper)
        db.session.commit()
        flash('Paper added successfully.')
        return redirect(url_for('manage_papers'))
    page = request.args.get('page', 1, type=int)
    per_page = 20
    papers = Paper.query.order_by(Paper.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    questions = Question.query.all()
    return render_template('admin/papers.html', papers=papers, questions=questions)

# API routes for AJAX operations
@app.route('/admin/api/questions')
@login_required
def admin_api_questions():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    query = request.args.get('q', '')
    
    if query:
        questions = Question.query.filter(
            or_(
                Question.content.ilike(f'%{query}%'),
                Question.correct_answer.ilike(f'%{query}%')
            )
        ).order_by(Question.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    else:
        questions = Question.query.order_by(Question.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'items': [q.to_dict() for q in questions.items],
        'total': questions.total,
        'pages': questions.pages,
        'page': questions.page,
        'per_page': questions.per_page,
        'has_prev': questions.has_prev,
        'has_next': questions.has_next,
        'prev_num': questions.prev_num,
        'next_num': questions.next_num
    })

@app.route('/api/question/<int:id>', methods=['PUT', 'DELETE'])
@login_required
def api_question(id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    question = Question.query.get_or_404(id)
    if request.method == 'DELETE':
        db.session.delete(question)
        db.session.commit()
        return jsonify({'message': 'Question deleted'})
    data = request.get_json()
    question.content = data.get('content', question.content)
    question.type = data.get('type', question.type)
    question.options = data.get('options', question.options)
    question.correct_answer = data.get('correct_answer', question.correct_answer)
    question.explanation = data.get('explanation', question.explanation)
    db.session.commit()
    return jsonify(question.to_dict())

# Export template route
@app.route('/admin/questions/template')
@login_required
def export_template():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    # Create a sample DataFrame with Chinese column names
    df = pd.DataFrame({
        '题目类型': ['单选题', '多选题', '问答题', '填空题'],
        '题目内容': [
            '示例：1+1=?', 
            '示例：以下哪些是编程语言？', 
            '示例：简述Python的特点',
            '示例：___是世界上最大的搜索引擎'
        ],
        '选项': [
            'A.1|B.2|C.3|D.4',
            'A.Python|B.Word|C.Java|D.Excel',
            '',
            ''
        ],
        '正确答案': [
            'B',
            'A,C',
            '1.简单易学\n2.开源免费\n3.跨平台',
            '谷歌'
        ],
        '解析': [
            '1+1=2',
            'Python和Java是编程语言',
            '这是解析',
            '截至2024年谷歌仍是最大搜索引擎'
        ]
    })
    
    # Create Excel writer
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='题目模板')
        worksheet = writer.sheets['题目模板']
        
        # Adjust column widths
        for idx, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
    
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='question_template.xlsx'
    )

# Export questions route
@app.route('/admin/questions/export')
@login_required
def export_questions():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    question_ids = request.args.get('ids')
    paper_id = request.args.get('paper_id')
    
    if paper_id:
        paper = Paper.query.get_or_404(paper_id)
        questions = paper.questions
        filename_prefix = f'paper_{paper.id}_questions'
    elif question_ids:
        ids = [int(id) for id in question_ids.split(',')]
        questions = Question.query.filter(Question.id.in_(ids)).all()
        filename_prefix = 'selected_questions'
    else:
        questions = Question.query.all()
        filename_prefix = 'all_questions'
    
    # Create DataFrame with Chinese column names
    data = []
    for question in questions:
        data.append({
            '题目ID': question.id,
            '题目类型': {
                'single_choice': '单选题',
                'multiple_choice': '多选题',
                'essay': '问答题',
                'fill_blank': '填空题'
            }.get(question.type, question.type),
            '题目内容': question.content,
            '选项': '|'.join(question.options) if question.options else '',
            '正确答案': question.correct_answer,
            '解析': question.explanation or ''
        })
    
    df = pd.DataFrame(data)
    
    # Create Excel writer
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='题目列表')
        worksheet = writer.sheets['题目列表']
        
        # Adjust column widths
        for idx, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
    
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{filename_prefix}_{timestamp}.xlsx'
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

# Import questions route
@app.route('/admin/questions/import', methods=['POST'])
@login_required
def import_questions():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    if 'file' not in request.files:
        flash('No file uploaded', 'danger')
        return redirect(url_for('manage_questions'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('manage_questions'))
    
    if not file.filename.endswith('.xlsx'):
        flash('Please upload an Excel file (.xlsx)', 'danger')
        return redirect(url_for('manage_questions'))
    
    try:
        # Read Excel file
        df = pd.read_excel(file)
        
        # Validate required columns
        required_columns = ['题目类型', '题目内容', '正确答案']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            flash(f'Missing required columns: {", ".join(missing_columns)}', 'danger')
            return redirect(url_for('manage_questions'))
        
        # Clean and validate data
        success_count = 0
        error_count = 0
        error_messages = []
        
        for index, row in df.iterrows():
            try:
                # Skip row if required fields are empty
                if pd.isna(row['题目类型']) or pd.isna(row['题目内容']) or pd.isna(row['正确答案']):
                    error_count += 1
                    error_messages.append(f'Row {index + 2}: Missing required fields')
                    continue
                
                # Convert question type
                type_mapping = {
                    '单选题': 'single_choice',
                    '多选题': 'multiple_choice',
                    '问答题': 'essay',
                    '填空题': 'fill_blank'
                }
                
                question_type = type_mapping.get(str(row['题目类型']).strip())
                if not question_type:
                    error_count += 1
                    error_messages.append(f'Row {index + 2}: Invalid question type "{row["题目类型"]}"')
                    continue
                
                # Process options
                options = None
                if '选项' in df.columns and not pd.isna(row['选项']):
                    options = [opt.strip() for opt in str(row['选项']).split('|') if opt.strip()]
                    if question_type in ['single_choice', 'multiple_choice'] and not options:
                        error_count += 1
                        error_messages.append(f'Row {index + 2}: Choice questions must have options')
                        continue
                
                # Create question
                question = Question(
                    type=question_type,
                    content=str(row['题目内容']).strip(),
                    options=options,
                    correct_answer=str(row['正确答案']).strip(),
                    explanation=str(row['解析']).strip() if '解析' in df.columns and not pd.isna(row['解析']) else None,
                    created_by=current_user
                )
                
                db.session.add(question)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                error_messages.append(f'Row {index + 2}: {str(e)}')
                continue
        
        # Commit all successful questions
        try:
            db.session.commit()
            message_parts = []
            if success_count > 0:
                message_parts.append(f'Successfully imported {success_count} questions')
            if error_count > 0:
                message_parts.append(f'Failed to import {error_count} questions')
                for msg in error_messages[:5]:  # Show first 5 errors
                    flash(msg, 'danger')
                if len(error_messages) > 5:
                    flash(f'... and {len(error_messages) - 5} more errors', 'danger')
            
            flash(' | '.join(message_parts), 'success' if success_count > 0 else 'danger')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Database error: {str(e)}', 'danger')
            
    except Exception as e:
        flash(f'Error reading file: {str(e)}', 'danger')
    
    return redirect(url_for('manage_questions'))

# 编辑题目
@app.route('/admin/questions/<int:question_id>', methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    question = Question.query.get_or_404(question_id)
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            question.type = data['type']
            question.content = data['content']
            question.options = data['options'].split('|') if data['options'] else None
            question.correct_answer = data['correct_answer']
            question.explanation = data['explanation']
            
            db.session.commit()
            return jsonify({'message': '题目更新成功'})
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    return jsonify({
        'id': question.id,
        'type': question.type,
        'content': question.content,
        'options': '|'.join(question.options) if question.options else '',
        'correct_answer': question.correct_answer,
        'explanation': question.explanation or ''
    })

# 删除题目
@app.route('/admin/questions/<int:question_id>', methods=['DELETE'])
@login_required
def delete_question(question_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    question = Question.query.get_or_404(question_id)
    try:
        db.session.delete(question)
        db.session.commit()
        return jsonify({'message': '题目删除成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# 编辑试卷
@app.route('/admin/papers/<int:paper_id>', methods=['GET', 'POST'])
@login_required
def edit_paper(paper_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    paper = Paper.query.get_or_404(paper_id)
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            paper.title = data['title']
            paper.description = data['description']
            
            # 更新试卷题目
            if 'questions' in data:
                question_ids = data['questions']
                paper.questions = Question.query.filter(Question.id.in_(question_ids)).all()
            
            db.session.commit()
            return jsonify({'message': '试卷更新成功'})
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    return jsonify({
        'id': paper.id,
        'title': paper.title,
        'description': paper.description,
        'questions': [{'id': q.id, 'content': q.content} for q in paper.questions]
    })

# 删除试卷
@app.route('/admin/papers/<int:paper_id>', methods=['DELETE'])
@login_required
def delete_paper(paper_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    paper = Paper.query.get_or_404(paper_id)
    try:
        db.session.delete(paper)
        db.session.commit()
        return jsonify({'message': '试卷删除成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# 获取题目列表的API
@app.route('/admin/api/questions')
@login_required
def get_questions_list():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    questions = Question.query.all()
    return jsonify([{
        'id': q.id,
        'type': {
            'single_choice': '单选题',
            'multiple_choice': '多选题',
            'essay': '问答题',
            'fill_blank': '填空题'
        }.get(q.type, q.type),
        'content': q.content
    } for q in questions])

@app.route('/admin/questions/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_questions():
    try:
        data = request.get_json()
        question_ids = data.get('question_ids', [])
        
        if not question_ids:
            return jsonify({'error': '未选择任何题目'}), 400
            
        # Delete questions from database
        Question.query.filter(Question.id.in_(question_ids)).delete(synchronize_session=False)
        db.session.commit()
        
        return jsonify({
            'message': f'成功删除 {len(question_ids)} 个题目',
            'deleted_count': len(question_ids)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/questions/clear-all', methods=['POST'])
@login_required
def clear_all_questions():
    try:
        # Delete all questions from database
        count = Question.query.count()
        Question.query.delete()
        db.session.commit()
        
        return jsonify({
            'message': f'成功清空题库，共删除 {count} 个题目',
            'deleted_count': count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 用户管理API
@app.route('/admin/api/users')
@login_required
def admin_api_users():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    query = request.args.get('q', '')
    user_query = User.query
    if query:
        user_query = user_query.filter(
            or_(User.username.ilike(f'%{query}%'), User.email.ilike(f'%{query}%'))
        )
    users = user_query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'items': [
            {
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'is_admin': u.is_admin,
                'created_at': u.created_at.isoformat()
            } for u in users.items
        ],
        'total': users.total,
        'pages': users.pages,
        'page': users.page,
        'per_page': users.per_page,
        'has_prev': users.has_prev,
        'has_next': users.has_next,
        'prev_num': users.prev_num,
        'next_num': users.next_num
    })

@app.route('/api/user', methods=['POST'])
@login_required
def api_create_user():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json()
    if not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing fields'}), 400
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    user = User(
        username=data['username'],
        email=data['email'],
        is_admin=data.get('is_admin', False)
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User created'})

@app.route('/api/user/<int:id>', methods=['PUT', 'DELETE'])
@login_required
def api_update_delete_user(id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    user = User.query.get_or_404(id)
    if request.method == 'DELETE':
        if user.id == current_user.id:
            return jsonify({'error': 'Cannot delete yourself'}), 400
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted'})
    data = request.get_json()
    if 'username' in data:
        if User.query.filter(User.username == data['username'], User.id != id).first():
            return jsonify({'error': 'Username already exists'}), 400
        user.username = data['username']
    if 'email' in data:
        if User.query.filter(User.email == data['email'], User.id != id).first():
            return jsonify({'error': 'Email already exists'}), 400
        user.email = data['email']
    if 'is_admin' in data:
        user.is_admin = data['is_admin']
    db.session.commit()
    return jsonify({'message': 'User updated'})

@app.route('/api/user/change_password', methods=['POST'])
@login_required
def api_change_password():
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    if not old_password or not new_password:
        return jsonify({'error': 'Missing fields'}), 400
    if not current_user.check_password(old_password):
        return jsonify({'error': 'Old password incorrect'}), 400
    current_user.set_password(new_password)
    db.session.commit()
    return jsonify({'message': 'Password changed'})

# 用户管理页面
@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('index'))
    return render_template('admin/users.html')

def ensure_admin_user():
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            user = User(username='admin', email='admin@example.com', is_admin=True)
            user.set_password('admin123')
            db.session.add(user)
            db.session.commit()

if __name__ == '__main__':
    ensure_admin_user()
    app.run()
