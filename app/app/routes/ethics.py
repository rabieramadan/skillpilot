"""
Ethics Assessment Module Routes
Handles professional ethics assessments with multiple levels and PayPal integration
"""

from flask import Blueprint, request, jsonify, session, current_app
from datetime import datetime
import json
import uuid
import os
import re
from app.services.ai_service import AIService
from functools import wraps
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import blue, black
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
import io

ethics_bp = Blueprint('ethics', __name__, url_prefix='/api/ethics')

# Data file paths
ETHICS_DATA_FILE = 'ethics_assessments.json'
ETHICS_SETTINGS_FILE = 'ethics_settings.json'


def authenticated_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin', False):
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def load_ethics_data():
    """Load ethics assessment data"""
    if not os.path.exists(ETHICS_DATA_FILE):
        return {
            'sessions': [],
            'scenarios': [],
            'certificates': [],
            'payments': [],
            'admin_settings': {
                'module_enabled': True,
                'pricing': {'basic': 29.99, 'intermediate': 49.99, 'advanced': 79.99},
                'waived_users': [],
                'passing_score': 50,
                'paypal_payment_link': ''
            }
        }
    
    with open(ETHICS_DATA_FILE, 'r') as f:
        return json.load(f)


def save_ethics_data(data):
    """Save ethics assessment data"""
    with open(ETHICS_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_ethics_settings():
    """Load ethics settings configuration"""
    if not os.path.exists(ETHICS_SETTINGS_FILE):
        return {
            'certificate_categories': [],
            'professional_domains': []
        }
    
    with open(ETHICS_SETTINGS_FILE, 'r') as f:
        return json.load(f)


def get_level_from_categories(level_id, settings):
    """Get level information from category-based structure"""
    categories = settings.get('certificate_categories', [])
    for category in categories:
        for level in category.get('levels', []):
            if level['id'] == level_id:
                return level
    return None


def get_category_from_level_id(level_id, settings):
    """Get category information from level ID"""
    categories = settings.get('certificate_categories', [])
    for category in categories:
        for level in category.get('levels', []):
            if level['id'] == level_id:
                return category
    return None


def extract_json_from_response(response_text):
    """Extract JSON from AI response"""
    import re
    
    # Try direct JSON parse
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Try extracting from markdown code blocks
    json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try finding JSON object
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    raise ValueError("No valid JSON found in response")


# ============================================
# Admin Routes
# ============================================

@ethics_bp.route('/admin/settings', methods=['GET'])
@authenticated_required
@admin_required
def get_admin_settings():
    """Get ethics module admin settings"""
    data = load_ethics_data()
    return jsonify({
        'success': True,
        'settings': data.get('admin_settings', {})
    })


@ethics_bp.route('/admin/settings', methods=['PUT'])
@authenticated_required
@admin_required
def update_admin_settings():
    """Update ethics module admin settings"""
    new_settings = request.json
    data = load_ethics_data()
    
    if 'admin_settings' not in data:
        data['admin_settings'] = {}
    
    data['admin_settings'].update(new_settings)
    save_ethics_data(data)
    
    return jsonify({
        'success': True,
        'settings': data['admin_settings']
    })


@ethics_bp.route('/admin/waive-payment', methods=['POST'])
@authenticated_required
@admin_required
def waive_payment():
    """Waive payment for a specific user"""
    req_data = request.json
    user_id = req_data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    data = load_ethics_data()
    if 'admin_settings' not in data:
        data['admin_settings'] = {'waived_users': []}
    
    if 'waived_users' not in data['admin_settings']:
        data['admin_settings']['waived_users'] = []
    
    if user_id not in data['admin_settings']['waived_users']:
        data['admin_settings']['waived_users'].append(user_id)
        save_ethics_data(data)
    
    return jsonify({
        'success': True,
        'message': f'Payment waived for user {user_id}'
    })


@ethics_bp.route('/admin/unwaive-payment', methods=['POST'])
@authenticated_required
@admin_required
def unwaive_payment():
    """Remove payment waiver for a user"""
    req_data = request.json
    user_id = req_data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    data = load_ethics_data()
    if 'admin_settings' in data and 'waived_users' in data['admin_settings']:
        if user_id in data['admin_settings']['waived_users']:
            data['admin_settings']['waived_users'].remove(user_id)
            save_ethics_data(data)
    
    return jsonify({
        'success': True,
        'message': f'Payment waiver removed for user {user_id}'
    })


# ============================================
# Ethics Assessment Routes
# ============================================

@ethics_bp.route('/levels', methods=['GET'])
@authenticated_required
def get_certificate_levels():
    """Get available certificate categories and levels"""
    settings = load_ethics_settings()
    return jsonify({
        'success': True,
        'categories': settings.get('certificate_categories', [])
    })


@ethics_bp.route('/domains', methods=['GET'])
@authenticated_required
def get_professional_domains():
    """Get available professional domains"""
    settings = load_ethics_settings()
    return jsonify({
        'success': True,
        'domains': settings.get('professional_domains', [])
    })


@ethics_bp.route('/check-payment-status', methods=['POST'])
@authenticated_required
def check_payment_status():
    """Check if user needs to pay or has payment waived/verified"""
    user_id = session.get('user_id')
    req_data = request.json
    level_id = req_data.get('level')
    
    data = load_ethics_data()
    admin_settings = data.get('admin_settings', {})
    waived_users = admin_settings.get('waived_users', [])
    
    # Check if module is enabled
    if not admin_settings.get('module_enabled', True):
        return jsonify({'error': 'Ethics assessment module is currently disabled'}), 403
    
    # Check if payment is waived
    payment_waived = user_id in waived_users
    
    # Check if user has verified payment for this level
    verified_payment = any(
        p['user_id'] == user_id and 
        p['level'] == level_id and 
        p.get('verified', False)
        for p in data.get('payments', [])
    )
    
    # Get pricing from level object in category structure
    settings = load_ethics_settings()
    level_info = get_level_from_categories(level_id, settings)
    amount = level_info['price'] if level_info else 0
    
    # No payment required if waived OR verified
    payment_required = not (payment_waived or verified_payment)
    
    return jsonify({
        'success': True,
        'payment_required': payment_required,
        'payment_waived': payment_waived,
        'payment_verified': verified_payment,
        'amount': amount,
        'currency': 'USD'
    })


@ethics_bp.route('/create-session', methods=['POST'])
@authenticated_required
def create_ethics_session():
    """Create a new ethics assessment session"""
    user_id = session.get('user_id')
    req_data = request.json
    
    required_fields = ['level', 'domain', 'jobTitle', 'profession', 'country', 'gender', 'educationLevel', 'language']
    missing = [f for f in required_fields if f not in req_data]
    
    if missing:
        return jsonify({'error': f'Missing fields: {", ".join(missing)}'}), 400
    
    # Create session
    session_id = str(uuid.uuid4())
    settings = load_ethics_settings()
    level_info = get_level_from_categories(req_data['level'], settings)
    
    if not level_info:
        return jsonify({'error': 'Invalid certificate level'}), 400
    
    data = load_ethics_data()
    new_session = {
        'session_id': session_id,
        'user_id': user_id,
        'level': req_data['level'],
        'domain': req_data['domain'],
        'job_title': req_data['jobTitle'],
        'profession': req_data['profession'],
        'country': req_data['country'],
        'gender': req_data['gender'],
        'education_level': req_data['educationLevel'],
        'language': req_data.get('language', 'en'),
        'total_questions': level_info['questions'],
        'current_question': 0,
        'questions_completed': 0,
        'is_completed': False,
        'final_score': None,
        'passed': None,
        'created_at': datetime.now().isoformat(),
        'completed_at': None
    }
    
    data['sessions'].append(new_session)
    save_ethics_data(data)
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'total_questions': level_info['questions']
    })


@ethics_bp.route('/generate-scenario', methods=['POST'])
@authenticated_required
def generate_scenario():
    """Generate an ethical scenario using AI"""
    req_data = request.json
    session_id = req_data.get('session_id')
    question_number = req_data.get('question_number', 1)
    
    if not session_id:
        return jsonify({'error': 'Session ID required'}), 400
    
    # Get session
    data = load_ethics_data()
    session_data = next((s for s in data['sessions'] if s['session_id'] == session_id), None)
    
    if not session_data:
        return jsonify({'error': 'Session not found'}), 404
    
    # Check ownership
    if session_data['user_id'] != session.get('user_id'):
        return jsonify({'error': 'Permission denied'}), 403
    
    # Generate scenario using AI
    try:
        ai_service = AIService()
        api_key = current_app.config.get('OPENAI_API_KEY')
        
        if not api_key:
            return jsonify({'error': 'AI service not configured'}), 500
        
        # Build prompt for scenario generation
        level_complexity = {
            'basic': 'straightforward with clear right and wrong choices',
            'intermediate': 'moderately complex with nuanced options',
            'advanced': 'highly complex with multiple stakeholders and competing interests'
        }
        
        # Extract complexity from level ID (e.g., 'general-basic' → 'basic', 'ai-intermediate' → 'intermediate')
        level_id = session_data['level']
        complexity_key = level_id.split('-')[-1] if '-' in level_id else level_id
        complexity = level_complexity.get(complexity_key, 'intermediate')
        
        # Determine language for scenario generation
        language_code = session_data['language']
        language_instruction = ""
        if language_code == 'ar':
            language_instruction = """
IMPORTANT: Generate ALL content in Arabic language:
- The scenario description must be in Arabic
- All 4 options must be in Arabic
- The theme must be in Arabic
Write the entire scenario, options, and theme in Arabic script (العربية)."""
        else:
            language_instruction = "Generate all content in English language."
        
        prompt = f"""Generate a professional ethics scenario for assessment purposes.

Context:
- Profession: {session_data['profession']}
- Domain: {session_data['domain']}
- Complexity: {complexity}

{language_instruction}

Create a realistic ethical dilemma with 4 possible actions. Respond in JSON format:
{{
    "scenario": "detailed scenario description (100-150 words)",
    "options": ["option 1", "option 2", "option 3", "option 4"],
    "correct_option": 0,
    "theme": "ethical theme",
    "complexity_level": "{session_data['level']}"
}}

Make the scenario relevant to {session_data['profession']} in {session_data['domain']}.
Only respond with valid JSON, no additional text."""
        
        response = ai_service.chat(
            provider='openai',
            message=prompt,
            api_key=api_key
        )
        
        if isinstance(response, dict) and 'error' in response:
            return jsonify({'error': 'Failed to generate scenario', 'details': response['error']}), 500
        
        response_text = response.get('text', '')
        scenario_data = extract_json_from_response(response_text)
        
        # Save scenario
        scenario_record = {
            'session_id': session_id,
            'question_number': question_number,
            'scenario': scenario_data['scenario'],
            'options': scenario_data['options'],
            'correct_option': scenario_data['correct_option'],
            'theme': scenario_data.get('theme', 'general_ethics'),
            'complexity_level': session_data['level'],
            'user_choice': None,
            'score': None,
            'feedback': None,
            'is_evaluated': False,
            'created_at': datetime.now().isoformat()
        }
        
        data['scenarios'].append(scenario_record)
        save_ethics_data(data)
        
        return jsonify({
            'success': True,
            'scenario': {
                'scenario_text': scenario_data['scenario'],
                'options': scenario_data['options'],
                'question_number': question_number
            }
        })
        
    except Exception as e:
        print(f"Error generating scenario: {e}")
        return jsonify({'error': 'Failed to generate scenario', 'details': str(e)}), 500


@ethics_bp.route('/submit-answer', methods=['POST'])
@authenticated_required
def submit_answer():
    """Submit answer and get evaluation"""
    req_data = request.json
    session_id = req_data.get('session_id')
    question_number = req_data.get('question_number')
    user_choice = req_data.get('user_choice')
    
    if not all([session_id, question_number is not None, user_choice is not None]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Get session and scenario
    data = load_ethics_data()
    session_data = next((s for s in data['sessions'] if s['session_id'] == session_id), None)
    
    if not session_data:
        return jsonify({'error': 'Session not found'}), 404
    
    if session_data['user_id'] != session.get('user_id'):
        return jsonify({'error': 'Permission denied'}), 403
    
    scenario = next((s for s in data['scenarios'] 
                    if s['session_id'] == session_id and s['question_number'] == question_number), None)
    
    if not scenario:
        return jsonify({'error': 'Scenario not found'}), 404
    
    # Evaluate answer using AI
    try:
        ai_service = AIService()
        api_key = current_app.config.get('OPENAI_API_KEY')
        
        # Get session language for evaluation feedback
        session_obj = next((s for s in data['sessions'] if s['session_id'] == session_id), None)
        language_code = session_obj.get('language', 'en') if session_obj else 'en'
        
        language_instruction = ""
        if language_code == 'ar':
            language_instruction = """
IMPORTANT: Provide ALL feedback in Arabic language:
- The feedback must be in Arabic
- The correct_action explanation must be in Arabic
- The improvement tips must be in Arabic
Write the entire evaluation in Arabic script (العربية)."""
        else:
            language_instruction = "Provide all feedback in English language."
        
        prompt = f"""Evaluate this ethical decision:

Scenario: {scenario['scenario']}
User chose: Option {user_choice + 1}: {scenario['options'][user_choice]}
Correct option: Option {scenario['correct_option'] + 1}: {scenario['options'][scenario['correct_option']]}

{language_instruction}

Provide evaluation in JSON format:
{{
    "score": (0-100),
    "feedback": "detailed feedback (100-150 words)",
    "correct_action": "explanation of correct action",
    "improvement_tips": "actionable improvement tips"
}}

Scoring: 100 for correct, 75-85 for reasonable, 50-65 for questionable, 25-40 for poor, 0-20 for unethical.
Only respond with valid JSON."""
        
        response = ai_service.chat(
            provider='openai',
            message=prompt,
            api_key=api_key
        )
        
        response_text = response.get('text', '')
        evaluation = extract_json_from_response(response_text)
        
        # Update scenario with evaluation
        for s in data['scenarios']:
            if s['session_id'] == session_id and s['question_number'] == question_number:
                s['user_choice'] = user_choice
                s['score'] = evaluation['score']
                s['feedback'] = evaluation['feedback']
                s['correct_action'] = evaluation.get('correct_action', '')
                s['improvement_tips'] = evaluation.get('improvement_tips', '')
                s['is_evaluated'] = True
                break
        
        # Update session progress
        for s in data['sessions']:
            if s['session_id'] == session_id:
                s['questions_completed'] = len([sc for sc in data['scenarios'] 
                                               if sc['session_id'] == session_id and sc['is_evaluated']])
                break
        
        save_ethics_data(data)
        
        return jsonify({
            'success': True,
            'evaluation': evaluation
        })
        
    except Exception as e:
        print(f"Error evaluating answer: {e}")
        return jsonify({'error': 'Failed to evaluate answer', 'details': str(e)}), 500


@ethics_bp.route('/complete-session', methods=['POST'])
@authenticated_required
def complete_session():
    """Complete assessment session and generate certificate if passed"""
    req_data = request.json
    session_id = req_data.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'Session ID required'}), 400
    
    # Get session
    data = load_ethics_data()
    session_data = next((s for s in data['sessions'] if s['session_id'] == session_id), None)
    
    if not session_data:
        return jsonify({'error': 'Session not found'}), 404
    
    if session_data['user_id'] != session.get('user_id'):
        return jsonify({'error': 'Permission denied'}), 403
    
    # Calculate final score
    scenarios = [s for s in data['scenarios'] if s['session_id'] == session_id and s['is_evaluated']]
    
    if not scenarios:
        return jsonify({'error': 'No evaluated scenarios found'}), 400
    
    total_score = sum(s.get('score', 0) for s in scenarios)
    final_score = int(total_score / len(scenarios))
    
    # Check if passed (70% threshold)
    admin_settings = data.get('admin_settings', {})
    passing_score = admin_settings.get('passing_score', 70)
    passed = final_score >= passing_score
    
    # Update session
    for s in data['sessions']:
        if s['session_id'] == session_id:
            s['is_completed'] = True
            s['final_score'] = final_score
            s['passed'] = passed
            s['completed_at'] = datetime.now().isoformat()
            break
    
    save_ethics_data(data)
    
    # Generate certificate if passed
    certificate_id = None
    if passed:
        certificate_id = str(uuid.uuid4())
        cert_record = {
            'certificate_id': certificate_id,
            'user_id': session.get('user_id'),
            'session_id': session_id,
            'level': session_data['level'],
            'domain': session_data['domain'],
            'final_score': final_score,
            'passed': True,
            'issued_at': datetime.now().isoformat()
        }
        data['certificates'].append(cert_record)
        save_ethics_data(data)
    
    return jsonify({
        'success': True,
        'final_score': final_score,
        'passed': passed,
        'certificate_id': certificate_id,
        'message': 'Congratulations! You passed the assessment.' if passed else 'Assessment completed. Score below passing threshold.'
    })


@ethics_bp.route('/my-sessions', methods=['GET'])
@authenticated_required
def get_my_sessions():
    """Get user's ethics assessment sessions"""
    user_id = session.get('user_id')
    data = load_ethics_data()
    
    user_sessions = [s for s in data['sessions'] if s['user_id'] == user_id]
    
    return jsonify({
        'success': True,
        'sessions': user_sessions
    })


@ethics_bp.route('/certificate/<certificate_id>', methods=['GET'])
@authenticated_required
def get_certificate(certificate_id):
    """Get certificate details"""
    user_id = session.get('user_id')
    data = load_ethics_data()
    
    cert = next((c for c in data['certificates'] if c['certificate_id'] == certificate_id), None)
    
    if not cert:
        return jsonify({'error': 'Certificate not found'}), 404
    
    if cert['user_id'] != user_id and not session.get('is_admin', False):
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify({
        'success': True,
        'certificate': cert
    })


# ============================================
# PayPal Payment Routes
# ============================================

@ethics_bp.route('/create-payment', methods=['POST'])
@authenticated_required
def create_payment():
    """Create payment record and return PayPal link for external payment"""
    user_id = session.get('user_id')
    req_data = request.json
    level = req_data.get('level')
    
    if not level:
        return jsonify({'error': 'Certificate level required'}), 400
    
    # Check if payment is waived
    data = load_ethics_data()
    admin_settings = data.get('admin_settings', {})
    waived_users = admin_settings.get('waived_users', [])
    
    if user_id in waived_users:
        return jsonify({'error': 'Payment already waived for this user'}), 400
    
    # Get PayPal payment link
    paypal_link = admin_settings.get('paypal_payment_link', '')
    if not paypal_link:
        return jsonify({'error': 'PayPal payment link not configured. Please contact administrator.'}), 400
    
    # Get pricing from level object in category structure
    settings = load_ethics_settings()
    level_info = get_level_from_categories(level, settings)
    category_info = get_category_from_level_id(level, settings)
    
    if not level_info:
        return jsonify({'error': 'Invalid certificate level'}), 400
    
    amount = level_info['price']
    
    if amount <= 0:
        return jsonify({'error': 'Invalid pricing for this level'}), 400
    
    # Build description with category and level names
    description = f"{category_info['name']} - {level_info['name']}" if category_info else level_info['name']
    
    # Generate payment ID
    payment_id = f"ETHICS-PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}-{user_id}"
    
    # Save payment record as pending verification
    payment_record = {
        'payment_id': payment_id,
        'user_id': user_id,
        'level': level,
        'amount': amount,
        'currency': 'USD',
        'description': description,
        'status': 'pending_verification',  # Admin will manually verify
        'verified': False,
        'created_at': datetime.now().isoformat()
    }
    
    data['payments'].append(payment_record)
    save_ethics_data(data)
    
    return jsonify({
        'success': True,
        'payment_id': payment_id,
        'payment_link': paypal_link,
        'amount': amount,
        'description': description
    })


@ethics_bp.route('/payment-success', methods=['GET'])
@authenticated_required
def payment_success():
    """Handle successful PayPal payment"""
    from app.services.paypal_service import PayPalService
    
    order_id = request.args.get('token')
    
    if not order_id:
        return jsonify({'error': 'Order ID required'}), 400
    
    try:
        paypal = PayPalService()
        result = paypal.capture_order(order_id)
        
        # Update payment record
        data = load_ethics_data()
        for payment in data['payments']:
            if payment['payment_id'] == order_id:
                payment['status'] = 'completed'
                payment['completed_at'] = datetime.now().isoformat()
                payment['capture_id'] = result.get('id')
                break
        
        save_ethics_data(data)
        
        return jsonify({
            'success': True,
            'message': 'Payment successful!',
            'order_id': order_id,
            'status': result.get('status')
        })
        
    except Exception as e:
        print(f"PayPal capture error: {e}")
        return jsonify({'error': 'Failed to complete payment', 'details': str(e)}), 500


@ethics_bp.route('/payment-cancel', methods=['GET'])
@authenticated_required
def payment_cancel():
    """Handle cancelled PayPal payment"""
    order_id = request.args.get('token')
    
    if order_id:
        # Update payment record
        data = load_ethics_data()
        for payment in data['payments']:
            if payment['payment_id'] == order_id:
                payment['status'] = 'cancelled'
                payment['cancelled_at'] = datetime.now().isoformat()
                break
        
        save_ethics_data(data)
    
    return jsonify({
        'success': False,
        'message': 'Payment cancelled',
        'order_id': order_id
    })


# ============================================
# Certificate Generation
# ============================================

def get_next_certificate_number():
    """Generate next certificate number in format ETHICS-YYYYMMDD-serial"""
    data = load_ethics_data()
    
    # Initialize certificate counter if not exists
    if "certificate_counter" not in data:
        data["certificate_counter"] = 1000
    
    # Increment counter
    data["certificate_counter"] += 1
    serial = data["certificate_counter"]
    
    # Save updated counter
    save_ethics_data(data)
    
    # Generate certificate number: ETHICS-YYYYMMDD-serial
    date_str = datetime.now().strftime("%Y%m%d")
    cert_number = f"ETHICS-{date_str}-{serial}"
    
    return cert_number


@ethics_bp.route('/download-certificate/<certificate_id>', methods=['GET'])
@authenticated_required
def download_certificate(certificate_id):
    """Download certificate PDF using professional landscape template - matches superadmin template"""
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.colors import HexColor, black
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        import io
        import qrcode
        
        user_id = session.get('user_id')
        data = load_ethics_data()
        
        # Get certificate
        cert = next((c for c in data['certificates'] if c['certificate_id'] == certificate_id), None)
        
        if not cert:
            return jsonify({'error': 'Certificate not found'}), 404
        
        if cert['user_id'] != user_id and not session.get('is_admin', False):
            return jsonify({'error': 'Permission denied'}), 403
        
        # Get certificate number
        if 'certificate_number' not in cert:
            cert['certificate_number'] = get_next_certificate_number()
            save_ethics_data(data)
        
        cert_number = cert['certificate_number']
        
        # Get user info
        from app.routes.auth import load_users
        users = load_users()
        user = next((u for u in users.get('users', []) if u.get('user_id') == cert['user_id']), None)
        user_name = user.get('full_name', 'Unknown User') if user else 'Unknown User'
        
        # Get level info from category structure
        settings = load_ethics_settings()
        level_info = get_level_from_categories(cert['level'], settings)
        category_info = get_category_from_level_id(cert['level'], settings)
        
        # Build full certificate name (Category + Level)
        if level_info and category_info:
            certificate_type = f"{category_info['name']} - {level_info['name']}"
        elif level_info:
            certificate_type = level_info['name']
        else:
            certificate_type = cert['level'].title()
        
        # Get domain info
        domains = settings.get('professional_domains', [])
        domain_info = next((d for d in domains if d['id'] == cert['domain']), None)
        domain_name = domain_info['name'] if domain_info else cert['domain'].title()
        
        # Create PDF in memory - LANDSCAPE A4 like superadmin template
        buffer = io.BytesIO()
        page_width, page_height = landscape(A4)
        c = canvas.Canvas(buffer, pagesize=landscape(A4))
        
        # Define colors - Professional teal/blue theme matching NATD branding
        primary_color = HexColor('#1a5c5e')  # Teal from NATD logo
        secondary_color = HexColor('#2d7d80')
        gold_color = HexColor('#c4a35a')  # Gold accent
        dark_blue = HexColor('#1a3a5c')
        
        # ========================================
        # CERTIFICATE BORDER - Security Pattern
        # ========================================
        
        # Outer decorative border
        c.setStrokeColor(primary_color)
        c.setLineWidth(3)
        c.rect(20, 20, page_width - 40, page_height - 40)
        
        # Inner decorative border
        c.setStrokeColor(gold_color)
        c.setLineWidth(1.5)
        c.rect(35, 35, page_width - 70, page_height - 70)
        
        # Corner ornaments
        corner_size = 25
        for x, y in [(40, 40), (page_width - 65, 40), (40, page_height - 65), (page_width - 65, page_height - 65)]:
            c.setFillColor(gold_color)
            c.circle(x + corner_size/2, y + corner_size/2, corner_size/3, fill=1, stroke=0)
        
        # ========================================
        # HEADER - INSTITUTIONAL LOGOS
        # ========================================
        
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        images_path = os.path.join(base_path, 'static', 'images')
        
        logo_size = 75
        logo_y = page_height - 140
        
        # AIAC logo (left)
        aiac_logo_path = os.path.join(images_path, 'aiac-logo.png')
        if os.path.exists(aiac_logo_path):
            try:
                c.drawImage(aiac_logo_path, 50, logo_y, width=logo_size, height=logo_size, preserveAspectRatio=True, mask='auto')
            except:
                pass
        
        # NATD logo (left, next to AIAC)
        natd_logo_path = os.path.join(images_path, 'NATD_Logo.png')
        if os.path.exists(natd_logo_path):
            try:
                c.drawImage(natd_logo_path, 130, logo_y, width=logo_size, height=logo_size, preserveAspectRatio=True, mask='auto')
            except:
                pass
        
        # AC logo (right)
        ac_logo_path = os.path.join(images_path, 'ac-logo.png')
        if os.path.exists(ac_logo_path):
            try:
                c.drawImage(ac_logo_path, page_width - 165, logo_y - 20, width=115, height=115, preserveAspectRatio=True, mask='auto')
            except:
                pass
        
        # ========================================
        # CERTIFICATE TITLE
        # ========================================
        
        c.setFillColor(primary_color)
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(page_width / 2, page_height - 90, "CERTIFICATE")
        
        c.setFillColor(gold_color)
        c.setFont("Helvetica", 16)
        c.drawCentredString(page_width / 2, page_height - 115, "OF PROFESSIONAL ETHICS")
        
        # Decorative line under title
        c.setStrokeColor(gold_color)
        c.setLineWidth(2)
        c.line(page_width/2 - 120, page_height - 125, page_width/2 + 120, page_height - 125)
        
        # ========================================
        # CERTIFICATE BODY
        # ========================================
        
        c.setFillColor(black)
        c.setFont("Helvetica", 14)
        c.drawCentredString(page_width / 2, page_height - 160, "This is to certify that")
        
        # Student Name - Large and prominent
        c.setFillColor(primary_color)
        max_name_width = page_width - 120
        name_font_size = 28
        c.setFont("Helvetica-Bold", name_font_size)
        name_width = c.stringWidth(user_name, "Helvetica-Bold", name_font_size)
        
        while name_width > max_name_width and name_font_size > 16:
            name_font_size -= 2
            c.setFont("Helvetica-Bold", name_font_size)
            name_width = c.stringWidth(user_name, "Helvetica-Bold", name_font_size)
        
        c.drawCentredString(page_width / 2, page_height - 195, user_name)
        
        # Decorative underline for name
        c.setStrokeColor(gold_color)
        c.setLineWidth(1)
        underline_width = min(name_width + 40, max_name_width)
        c.line(page_width/2 - underline_width/2, page_height - 205, page_width/2 + underline_width/2, page_height - 205)
        
        c.setFillColor(black)
        c.setFont("Helvetica", 14)
        c.drawCentredString(page_width / 2, page_height - 235, "has successfully completed the Professional Ethics Assessment")
        
        # Certificate Type and Domain
        c.setFillColor(dark_blue)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(page_width / 2, page_height - 270, certificate_type)
        
        c.setFont("Helvetica", 14)
        c.setFillColor(secondary_color)
        c.drawCentredString(page_width / 2, page_height - 295, f"Professional Field: {domain_name}")
        
        # Score badge
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(HexColor('#059669') if cert['final_score'] >= 50 else HexColor('#dc2626'))
        c.drawCentredString(page_width / 2, page_height - 320, f"Score: {cert['final_score']}% - {'PASSED' if cert.get('passed', cert['final_score'] >= 50) else 'COMPLETED'}")
        
        # ========================================
        # SIGNATURE & STAMP SECTION
        # ========================================
        
        sig_y = 120
        
        # LEFT side - Chair Signature
        signature_path = os.path.join(images_path, 'signature.png')
        if os.path.exists(signature_path):
            try:
                c.drawImage(signature_path, 80, sig_y - 5, width=120, height=50, preserveAspectRatio=True, mask='auto')
            except:
                pass
        
        # LEFT side - Chair Stamp
        chair_stamp_path = os.path.join(images_path, 'aiac-stamp.png')
        if os.path.exists(chair_stamp_path):
            try:
                c.drawImage(chair_stamp_path, 50, sig_y + 25, width=100, height=100, preserveAspectRatio=True, mask='auto')
            except:
                pass
        
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        c.line(60, sig_y, 220, sig_y)
        
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(140, sig_y - 15, "Prof. Rabie A. Ramadan")
        c.setFont("Helvetica", 9)
        c.drawCentredString(140, sig_y - 28, "AI Applications Chair")
        c.drawCentredString(140, sig_y - 40, "University of Nizwa")
        
        # CENTER - Date of Issue
        issue_date = datetime.fromisoformat(cert['issued_at']).strftime("%B %d, %Y")
        c.setFillColor(black)
        c.setFont("Helvetica", 10)
        c.drawCentredString(page_width / 2, sig_y + 100, "Date of Issue")
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(page_width / 2, sig_y + 82, issue_date)
        
        # CENTER - QR Code for verification
        qr_size = 90
        from flask import request
        base_url = request.host_url.rstrip('/')
        verification_url = f"{base_url}/api/ethics/certificate/{certificate_id}"
        
        qr = qrcode.QRCode(version=1, box_size=5, border=1)
        qr.add_data(verification_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        center_x = page_width / 2
        c.drawImage(ImageReader(qr_buffer), center_x - qr_size/2, sig_y - 15, width=qr_size, height=qr_size, mask='auto')
        
        c.setFillColor(secondary_color)
        c.setFont("Helvetica", 8)
        c.drawCentredString(center_x, sig_y - 30, "Scan to Verify")
        
        # Certificate number (below QR)
        c.setFont("Helvetica", 9)
        c.setFillColor(secondary_color)
        c.drawCentredString(page_width / 2, sig_y - 45, f"Certificate No: {cert_number}")
        
        # RIGHT side - Academy Director Signature
        signature2_path = os.path.join(images_path, 'signature2.png')
        if os.path.exists(signature2_path):
            try:
                c.drawImage(signature2_path, page_width - 200, sig_y - 5, width=120, height=50, preserveAspectRatio=True, mask='auto')
            except:
                pass
        
        # RIGHT side - NATD Stamp
        natd_stamp_path = os.path.join(images_path, 'NATD_stamp.png')
        if os.path.exists(natd_stamp_path):
            try:
                c.drawImage(natd_stamp_path, page_width - 180, sig_y + 35, width=110, height=110, preserveAspectRatio=True, mask='auto')
            except:
                pass
        
        # Signature line for NATD (right side)
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        c.line(page_width - 220, sig_y, page_width - 60, sig_y)
        
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(page_width - 140, sig_y - 15, "Academy Director")
        c.setFont("Helvetica", 9)
        c.drawCentredString(page_width - 140, sig_y - 28, "Nizwa Academy for")
        c.drawCentredString(page_width - 140, sig_y - 40, "Training and Development")
        
        # ========================================
        # FOOTER
        # ========================================
        
        c.setFillColor(HexColor('#cccccc'))
        c.setFont("Helvetica", 8)
        c.drawCentredString(page_width / 2, 35, "This certificate is digitally generated and verifiable. Any unauthorized alteration renders this certificate void.")
        
        c.setFillColor(secondary_color)
        c.setFont("Helvetica", 8)
        c.drawCentredString(page_width / 2, 22, "University of Nizwa - AI Applications Chair | Nizwa Academy for Training and Development")
        
        # Save PDF
        c.save()
        buffer.seek(0)
        
        from flask import send_file
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'ethics_certificate_{cert_number}.pdf'
        )
        
    except Exception as e:
        print(f"Error generating certificate: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to generate certificate', 'details': str(e)}), 500

# ============================================
# Class-Based Access Control for Ethics Certificate
# ============================================

@ethics_bp.route('/admin/class-settings', methods=['GET'])
@authenticated_required
@admin_required
def get_class_settings():
    """Get Ethics Certificate class-specific settings"""
    try:
        data = load_ethics_data()
        admin_settings = data.get('admin_settings', {})
        
        # Load classes to provide class list
        import json
        classes_file = 'classes.json'
        if os.path.exists(classes_file):
            with open(classes_file, 'r') as f:
                classes_data = json.load(f)
                classes = classes_data.get('classes', [])
        else:
            classes = []
        
        return jsonify({
            'success': True,
            'settings': {
                'module_enabled': admin_settings.get('module_enabled', True),
                'enabled_classes': admin_settings.get('enabled_classes', []),
                'all_for_course_type': admin_settings.get('all_for_course_type', True),
                'paypal_payment_link': admin_settings.get('paypal_payment_link', ''),
                'passing_score': admin_settings.get('passing_score', 50)
            },
            'classes': classes
        })
        
    except Exception as e:
        print(f"Error getting class settings: {e}")
        return jsonify({'error': str(e)}), 500


@ethics_bp.route('/admin/class-settings', methods=['POST'])
@authenticated_required
@admin_required
def update_class_settings():
    """Update Ethics Certificate class-specific settings"""
    try:
        request_data = request.json
        data = load_ethics_data()
        
        if 'admin_settings' not in data:
            data['admin_settings'] = {}
        
        admin_settings = data['admin_settings']
        
        # Update settings
        if 'module_enabled' in request_data:
            admin_settings['module_enabled'] = request_data['module_enabled']
        
        if 'enabled_classes' in request_data:
            admin_settings['enabled_classes'] = request_data['enabled_classes']
        
        if 'all_for_course_type' in request_data:
            admin_settings['all_for_course_type'] = request_data['all_for_course_type']
        
        if 'paypal_payment_link' in request_data:
            admin_settings['paypal_payment_link'] = request_data['paypal_payment_link']
        
        if 'passing_score' in request_data:
            admin_settings['passing_score'] = int(request_data['passing_score'])
        
        save_ethics_data(data)
        
        return jsonify({
            'success': True,
            'message': 'Class settings updated successfully',
            'settings': admin_settings
        })
        
    except Exception as e:
        print(f"Error updating class settings: {e}")
        return jsonify({'error': str(e)}), 500


@ethics_bp.route('/admin/verify-payment/<payment_id>', methods=['POST'])
@authenticated_required
@admin_required
def verify_payment(payment_id):
    """Admin endpoint to manually verify a payment"""
    try:
        data = load_ethics_data()
        
        # Find payment record
        payment = next((p for p in data.get('payments', []) if p['payment_id'] == payment_id), None)
        
        if not payment:
            return jsonify({'error': 'Payment not found'}), 404
        
        # Mark as verified
        payment['verified'] = True
        payment['verified_at'] = datetime.now().isoformat()
        payment['status'] = 'verified'
        
        save_ethics_data(data)
        
        return jsonify({
            'success': True,
            'message': 'Payment verified successfully',
            'payment': payment
        })
        
    except Exception as e:
        print(f"Error verifying payment: {e}")
        return jsonify({'error': str(e)}), 500


@ethics_bp.route('/admin/pending-payments', methods=['GET'])
@authenticated_required
@admin_required
def get_pending_payments():
    """Get all pending payments for admin verification"""
    try:
        data = load_ethics_data()
        
        # Get all unverified payments
        pending_payments = [
            p for p in data.get('payments', [])
            if not p.get('verified', False)
        ]
        
        # Enrich with user info
        from app.routes.auth import load_users
        users = load_users()
        
        for payment in pending_payments:
            user = next((u for u in users if u.get('id') == payment['user_id']), None)
            if user:
                payment['user_name'] = user.get('name', 'Unknown')
                payment['user_email'] = user.get('email', 'Unknown')
        
        return jsonify({
            'success': True,
            'payments': pending_payments
        })
        
    except Exception as e:
        print(f"Error loading pending payments: {e}")
        return jsonify({'error': str(e)}), 500


@ethics_bp.route('/check-access', methods=['GET'])
@authenticated_required
def check_ethics_access():
    """Check if current user has access to Ethics Certificate"""
    try:
        user_id = session.get('user_id')
        
        # Load settings
        data = load_ethics_data()
        admin_settings = data.get('admin_settings', {})
        
        # Check if module is enabled
        if not admin_settings.get('module_enabled', True):
            return jsonify({
                'success': True,
                'has_access': False,
                'reason': 'Module is currently disabled by admin'
            })
        
        # Check if access is granted to all ethics_certificate course types
        if admin_settings.get('all_for_course_type', True):
            # Load user's enrollments and check if enrolled in ethics_certificate course
            import json
            enrollments_file = 'enrollments.json'
            classes_file = 'classes.json'
            
            if os.path.exists(enrollments_file) and os.path.exists(classes_file):
                with open(enrollments_file, 'r') as f:
                    enrollments_data = json.load(f)
                with open(classes_file, 'r') as f:
                    classes_data = json.load(f)
                
                # Get user's active enrollments
                user_enrollments = [e for e in enrollments_data.get('enrollments', []) 
                                   if e['user_id'] == user_id and 
                                   e.get('enrollment_status') == 'active' and
                                   e.get('payment_verified', True)]
                
                enrolled_class_ids = [e['class_id'] for e in user_enrollments]
                
                # Check if any enrolled class has ethics_certificate course type
                for cls in classes_data.get('classes', []):
                    if cls['class_id'] in enrolled_class_ids:
                        if cls.get('course_type') == 'ethics_certificate':
                            return jsonify({
                                'success': True,
                                'has_access': True,
                                'reason': 'Enrolled in Ethics Certificate course'
                            })
            
            return jsonify({
                'success': True,
                'has_access': False,
                'reason': 'Not enrolled in any Ethics Certificate course'
            })
        
        # Check specific enabled classes
        enabled_classes = admin_settings.get('enabled_classes', [])
        if not enabled_classes:
            return jsonify({
                'success': True,
                'has_access': False,
                'reason': 'No classes enabled for Ethics Certificate'
            })
        
        # Check if user is enrolled in any enabled class
        import json
        enrollments_file = 'enrollments.json'
        
        if os.path.exists(enrollments_file):
            with open(enrollments_file, 'r') as f:
                enrollments_data = json.load(f)
            
            user_enrollments = [e for e in enrollments_data.get('enrollments', []) 
                               if e['user_id'] == user_id and 
                               e.get('enrollment_status') == 'active' and
                               e.get('payment_verified', True)]
            
            enrolled_class_ids = [e['class_id'] for e in user_enrollments]
            
            # Check if user is enrolled in any enabled class
            for class_id in enabled_classes:
                if class_id in enrolled_class_ids:
                    return jsonify({
                        'success': True,
                        'has_access': True,
                        'reason': 'Enrolled in enabled class'
                    })
        
        return jsonify({
            'success': True,
            'has_access': False,
            'reason': 'Not enrolled in any enabled Ethics Certificate class'
        })
        
    except Exception as e:
        print(f"Error checking Ethics Certificate access: {e}")
        return jsonify({'error': str(e)}), 500
