from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
import json
import uuid
from pathlib import Path
from collections import defaultdict
from functools import wraps
from sqlalchemy import func

analytics_bp = Blueprint('analytics', __name__)

def admin_required(f):
    """Decorator to require admin authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'error': 'Admin authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_lms_stats():
    """Get real LMS statistics from database"""
    from app.models import db, User, Course, Enrollment, ExamResult, SurveyResponse
    
    try:
        total_users = User.query.count()
        total_courses = Course.query.filter_by(is_published=True).count()
        total_enrollments = Enrollment.query.count()
        
        completed_enrollments = Enrollment.query.filter_by(status='completed').count()
        certificates_issued = Enrollment.query.filter_by(certificate_issued=True).count()
        
        students = User.query.filter_by(role='student').count()
        teachers = User.query.filter_by(role='teacher').count()
        
        exam_results = ExamResult.query.count()
        passed_exams = ExamResult.query.filter(ExamResult.score >= 70).count()
        
        survey_responses = SurveyResponse.query.count()
        
        enrollments_by_course = db.session.query(
            Course.title, func.count(Enrollment.id)
        ).join(Enrollment).group_by(Course.id, Course.title).all()
        
        recent_enrollments = Enrollment.query.order_by(
            Enrollment.enrolled_at.desc()
        ).limit(10).all()
        
        return {
            'total_users': total_users,
            'total_courses': total_courses,
            'total_enrollments': total_enrollments,
            'completed_enrollments': completed_enrollments,
            'certificates_issued': certificates_issued,
            'students': students,
            'teachers': teachers,
            'exam_results': exam_results,
            'passed_exams': passed_exams,
            'pass_rate': round((passed_exams / exam_results * 100) if exam_results > 0 else 0, 1),
            'survey_responses': survey_responses,
            'completion_rate': round((completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0, 1),
            'enrollments_by_course': [{'course': c, 'count': n} for c, n in enrollments_by_course],
            'recent_activity': [{
                'student': e.user.full_name if e.user else 'Unknown',
                'course': e.course.title if e.course else 'Unknown',
                'date': e.enrolled_at.isoformat() if e.enrolled_at else None
            } for e in recent_enrollments]
        }
    except Exception as e:
        return {'error': str(e)}

# Token costs per 1K tokens (approximate)
TOKEN_COSTS = {
    'gpt-4-turbo-preview': {'input': 0.01, 'output': 0.03},
    'gpt-4-vision-preview': {'input': 0.01, 'output': 0.03},
    'gpt-4': {'input': 0.03, 'output': 0.06},
    'gpt-4-32k': {'input': 0.06, 'output': 0.12},
    'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
    'claude-3-5-sonnet-20241022': {'input': 0.003, 'output': 0.015},
    'claude-3-opus-20240229': {'input': 0.015, 'output': 0.075},
    'claude-3-sonnet-20240229': {'input': 0.003, 'output': 0.015},
    'claude-3-haiku-20240307': {'input': 0.00025, 'output': 0.00125},
    'gemini-2.0-flash': {'input': 0.00010, 'output': 0.00040},
    'gemini-1.5-flash': {'input': 0.000075, 'output': 0.0003},
    'dall-e-3': {'per_image': 0.04},
    'dall-e-2': {'per_image': 0.02}
}

def get_sessions_db_path():
    return Path(__file__).parent.parent.parent / 'sessions.json'

def load_sessions_db():
    db_path = get_sessions_db_path()
    if db_path.exists():
        with open(db_path, 'r') as f:
            return json.load(f)
    return {"sessions": []}

def calculate_cost(model, input_tokens=0, output_tokens=0, is_image=False):
    """Calculate cost based on model and token usage"""
    if model not in TOKEN_COSTS:
        return 0.0
    
    costs = TOKEN_COSTS[model]
    
    if is_image:
        return costs.get('per_image', 0.0)
    
    input_cost = (input_tokens / 1000) * costs.get('input', 0.0)
    output_cost = (output_tokens / 1000) * costs.get('output', 0.0)
    
    return input_cost + output_cost

@analytics_bp.route('/cost/calculate', methods=['POST'])
@admin_required
def calculate_message_cost():
    """Calculate cost for a message (admin only)"""
    try:
        data = request.get_json()
        model = data.get('model')
        input_tokens = data.get('input_tokens', 0)
        output_tokens = data.get('output_tokens', 0)
        is_image = data.get('is_image', False)
        
        cost = calculate_cost(model, input_tokens, output_tokens, is_image)
        
        return jsonify({
            'cost': cost,
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/dashboard', methods=['GET'])
@admin_required
def get_dashboard_stats():
    """Get LMS analytics dashboard data (admin only)"""
    try:
        lms_stats = get_lms_stats()
        
        if 'error' in lms_stats:
            return jsonify({'error': lms_stats['error']}), 500
        
        stats = {
            'total_sessions': lms_stats['total_enrollments'],
            'total_messages': lms_stats['total_users'],
            'total_cost': lms_stats['completion_rate'],
            'total_tokens': lms_stats['certificates_issued'],
            'models_used': {},
            'lms_stats': lms_stats
        }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/comparison', methods=['POST'])
@admin_required
def create_comparison():
    """Create A/B test comparison (admin only)"""
    try:
        data = request.get_json()
        
        comparison = {
            'id': str(uuid.uuid4()),
            'prompt': data.get('prompt'),
            'models': data.get('models', []),
            'responses': [],
            'created_at': datetime.now().isoformat(),
            'created_by': data.get('user', 'anonymous')
        }
        
        # Save comparison
        db_path = Path(__file__).parent.parent.parent / 'comparisons.json'
        if db_path.exists():
            with open(db_path, 'r') as f:
                comparisons_db = json.load(f)
        else:
            comparisons_db = {'comparisons': []}
        
        comparisons_db['comparisons'].append(comparison)
        
        with open(db_path, 'w') as f:
            json.dump(comparisons_db, f, indent=2)
        
        return jsonify({'success': True, 'comparison': comparison})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/comparison/<comparison_id>/response', methods=['POST'])
@admin_required
def add_comparison_response(comparison_id):
    """Add a response to comparison (admin only)"""
    try:
        data = request.get_json()
        
        db_path = Path(__file__).parent.parent.parent / 'comparisons.json'
        with open(db_path, 'r') as f:
            comparisons_db = json.load(f)
        
        for comparison in comparisons_db['comparisons']:
            if comparison['id'] == comparison_id:
                response = {
                    'model': data.get('model'),
                    'response': data.get('response'),
                    'tokens': data.get('tokens'),
                    'cost': data.get('cost'),
                    'time': data.get('time'),
                    'timestamp': datetime.now().isoformat()
                }
                comparison['responses'].append(response)
                
                with open(db_path, 'w') as f:
                    json.dump(comparisons_db, f, indent=2)
                
                return jsonify({'success': True, 'response': response})
        
        return jsonify({'error': 'Comparison not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/export', methods=['GET'])
@admin_required
def export_analytics():
    """Export all analytics data (admin only)"""
    try:
        sessions_db = load_sessions_db()
        user = request.args.get('user')
        
        if user:
            sessions_db['sessions'] = [s for s in sessions_db['sessions'] if s.get('user') == user]
        
        return jsonify(sessions_db)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
