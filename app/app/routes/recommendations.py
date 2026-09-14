"""
API routes for personalized learning recommendations.
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime

recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/api/recommendations')

try:
    from app.models import db, LearningRecommendation, User, Course
    from app.services.recommendation_engine import (
        RecommendationEngine, AdaptiveContentEngine,
        get_user_recommendations, analyze_user_performance, get_study_plan
    )
    HAS_DB = True
except ImportError:
    HAS_DB = False


def require_auth(f):
    """Decorator to require authentication."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated


@recommendations_bp.route('/performance', methods=['GET'])
@require_auth
def get_performance_analysis():
    """Get performance analysis for the current user."""
    user_id = session.get('user_id')
    course_id = request.args.get('course_id')
    
    try:
        analysis = analyze_user_performance(user_id, course_id)
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/suggestions', methods=['GET'])
@require_auth
def get_suggestions():
    """Get personalized learning recommendations."""
    user_id = session.get('user_id')
    course_id = request.args.get('course_id')
    limit = request.args.get('limit', 5, type=int)
    
    try:
        recommendations = get_user_recommendations(user_id, course_id, limit)
        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/next-content', methods=['GET'])
@require_auth
def get_next_content():
    """Get the next recommended content for the student."""
    user_id = session.get('user_id')
    course_id = request.args.get('course_id')
    
    if not course_id:
        return jsonify({'error': 'course_id is required'}), 400
        
    try:
        engine = RecommendationEngine(user_id, course_id)
        next_content = engine.get_next_suggested_content()
        return jsonify({
            'success': True,
            'next_content': next_content
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/study-plan', methods=['GET'])
@require_auth
def get_personalized_study_plan():
    """Generate a personalized study plan."""
    user_id = session.get('user_id')
    course_id = request.args.get('course_id')
    weeks = request.args.get('weeks', 4, type=int)
    
    if not course_id:
        return jsonify({'error': 'course_id is required'}), 400
        
    try:
        plan = get_study_plan(user_id, course_id, weeks)
        return jsonify({
            'success': True,
            'study_plan': plan
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/adaptive-content', methods=['GET'])
@require_auth
def get_adaptive_content():
    """Get content adapted to student's current level."""
    user_id = session.get('user_id')
    course_id = request.args.get('course_id')
    content_type = request.args.get('type', 'material')
    
    if not course_id:
        return jsonify({'error': 'course_id is required'}), 400
        
    try:
        engine = AdaptiveContentEngine(course_id)
        content = engine.get_difficulty_adjusted_content(user_id, content_type)
        return jsonify({
            'success': True,
            'content': content,
            'content_type': content_type
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/history', methods=['GET'])
@require_auth
def get_recommendation_history():
    """Get history of recommendations for the user."""
    if not HAS_DB:
        return jsonify({'error': 'Database not available'}), 500
        
    user_id = session.get('user_id')
    course_id = request.args.get('course_id')
    status = request.args.get('status')
    limit = request.args.get('limit', 20, type=int)
    
    try:
        query = LearningRecommendation.query.filter_by(user_id=user_id)
        
        if course_id:
            query = query.filter_by(course_id=course_id)
        if status:
            query = query.filter_by(status=status)
            
        recommendations = query.order_by(
            LearningRecommendation.created_at.desc()
        ).limit(limit).all()
        
        return jsonify({
            'success': True,
            'recommendations': [{
                'id': r.id,
                'type': r.recommendation_type,
                'title': r.title,
                'description': r.description,
                'priority': r.priority,
                'status': r.status,
                'action': r.action,
                'created_at': r.created_at.isoformat() if r.created_at else None
            } for r in recommendations]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/<recommendation_id>/action', methods=['POST'])
@require_auth
def update_recommendation_action():
    """Update the status of a recommendation after user action."""
    if not HAS_DB:
        return jsonify({'error': 'Database not available'}), 500
        
    user_id = session.get('user_id')
    recommendation_id = request.view_args.get('recommendation_id')
    data = request.get_json() or {}
    
    action = data.get('action')
    if action not in ['viewed', 'accepted', 'dismissed', 'completed']:
        return jsonify({'error': 'Invalid action. Must be: viewed, accepted, dismissed, or completed'}), 400
        
    try:
        recommendation = LearningRecommendation.query.filter_by(
            id=recommendation_id,
            user_id=user_id
        ).first()
        
        if not recommendation:
            return jsonify({'error': 'Recommendation not found'}), 404
            
        if action == 'viewed':
            recommendation.status = 'viewed'
        elif action == 'accepted':
            recommendation.status = 'accepted'
        elif action == 'dismissed':
            recommendation.status = 'dismissed'
        elif action == 'completed':
            recommendation.status = 'completed'
            
        recommendation.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Recommendation marked as {action}',
            'recommendation': {
                'id': recommendation.id,
                'status': recommendation.status
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/generate', methods=['POST'])
@require_auth
def generate_and_save_recommendations():
    """Generate and save new recommendations for the user."""
    if not HAS_DB:
        return jsonify({'error': 'Database not available'}), 500
        
    user_id = session.get('user_id')
    data = request.get_json() or {}
    course_id = data.get('course_id')
    
    try:
        engine = RecommendationEngine(user_id, course_id)
        engine.analyze_performance()
        saved_ids = engine.save_recommendations()
        
        return jsonify({
            'success': True,
            'message': f'Generated {len(saved_ids)} new recommendations',
            'recommendation_ids': saved_ids
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/dashboard', methods=['GET'])
@require_auth
def get_learning_dashboard():
    """Get a comprehensive learning dashboard for the student."""
    user_id = session.get('user_id')
    course_id = request.args.get('course_id')
    
    try:
        engine = RecommendationEngine(user_id, course_id)
        performance = engine.analyze_performance()
        recommendations = engine.generate_recommendations(5)
        next_content = engine.get_next_suggested_content() if course_id else None
        
        dashboard = {
            'user_id': user_id,
            'performance': {
                'overall_score': performance.get('overall_score', 0),
                'completion_rate': performance.get('completion_rate', 0),
                'learning_velocity': performance.get('learning_velocity', 'normal'),
                'engagement_level': performance.get('engagement_level', 'active'),
                'strengths': performance.get('strengths', []),
                'weaknesses': performance.get('weaknesses', [])
            },
            'recommendations': recommendations,
            'next_content': next_content,
            'suggested_pace': performance.get('suggested_pace', 'maintain'),
            'stats': {
                'average_assignment_score': performance.get('average_assignment_score', 0),
                'average_exam_score': performance.get('average_exam_score', 0),
                'materials_progress': performance.get('materials_progress', 0)
            }
        }
        
        return jsonify({
            'success': True,
            'dashboard': dashboard
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
