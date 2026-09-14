"""
Survey Routes - Handle survey submission, AI analysis, and PDF generation
"""

from flask import Blueprint, request, jsonify, send_file, session
from datetime import datetime
from typing import Optional
import json
import os
from pathlib import Path
import requests
from functools import wraps

survey_bp = Blueprint('survey', __name__, url_prefix='/api/survey')


def admin_required(f):
    """Decorator to require admin authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'error': 'Admin authentication required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# File paths
SURVEY_DATA_FILE = 'users_survey_data.json'
SURVEY_QUESTIONS_FILE = 'survey_questions.json'
EXIT_EXAM_DATA_FILE = 'users_exit_exam_data.json'
EXIT_EXAM_QUESTIONS_FILE = 'exit_exam_questions.json'
CERTIFICATES_DIR = 'certificates'
SETTINGS_FILE = 'admin_settings.json'
EXAM_DATA_DIR = 'exam_data'
SURVEYS_DIR = os.path.join(EXAM_DATA_DIR, 'surveys')
EXIT_EXAMS_DIR = os.path.join(EXAM_DATA_DIR, 'exit_exams')

# Ensure directories exist
Path(CERTIFICATES_DIR).mkdir(exist_ok=True)
Path(SURVEYS_DIR).mkdir(parents=True, exist_ok=True)
Path(EXIT_EXAMS_DIR).mkdir(parents=True, exist_ok=True)


def load_settings():
    """Load admin settings from JSON file"""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"survey_enabled": True, "exit_exam_enabled": True}


def save_settings(settings):
    """Save admin settings to JSON file"""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def load_survey_data():
    """Load survey data from JSON file"""
    if os.path.exists(SURVEY_DATA_FILE):
        with open(SURVEY_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"users": []}


def save_survey_data(data):
    """Save survey data to JSON file"""
    with open(SURVEY_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_survey_questions():
    """Load survey questions from JSON file"""
    if os.path.exists(SURVEY_QUESTIONS_FILE):
        with open(SURVEY_QUESTIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"questions": []}


def load_exit_exam_data():
    """Load exit exam data from JSON file"""
    if os.path.exists(EXIT_EXAM_DATA_FILE):
        with open(EXIT_EXAM_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"users": []}


def load_users():
    """Load users from JSON file"""
    if os.path.exists('users.json'):
        with open('users.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"users": []}


def save_exit_exam_data(data):
    """Save exit exam data to JSON file"""
    with open(EXIT_EXAM_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_exit_exam_questions():
    """Load exit exam questions from JSON file"""
    if os.path.exists(EXIT_EXAM_QUESTIONS_FILE):
        with open(EXIT_EXAM_QUESTIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"questions": []}


def generate_true_false_questions_with_openai(api_key: str, count: int = 5) -> list:
    """
    Generate true/false questions using OpenAI API
    
    Args:
        api_key: OpenAI API key
        count: Number of questions to generate (default 5)
    
    Returns:
        List of question dictionaries or empty list if failed
    """
    if not api_key:
        # Avoid leaking auth state into stdout/log aggregators.
        pass
        return []
    
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        prompt = f"""Generate exactly {count} true/false questions about AI and prompt engineering fundamentals.
        
Format your response as a JSON array with this exact structure:
[
    {{
        "id": 1,
        "question": "Question text here",
        "type": "true_false",
        "options": ["True", "False"],
        "correct_answer": "True"
    }}
]

Topics to cover:
- What is prompt engineering
- Best practices for writing prompts
- Common prompt patterns
- AI model capabilities and limitations
- Effective techniques for improving AI responses

Make the questions educational and appropriate for a prompt engineering training course.
Return ONLY the JSON array, no other text."""

        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {'role': 'system', 'content': 'You are an expert AI trainer creating educational assessment questions about prompt engineering. Respond only with valid JSON.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 2000
        }
        
        print(f"DEBUG: Requesting {count} questions from OpenAI...")
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            questions = json.loads(content)
            print(f"DEBUG: Successfully generated {len(questions)} questions from OpenAI")
            return questions
        else:
            print(f"DEBUG: OpenAI API error: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"DEBUG: Exception generating questions with OpenAI: {str(e)}")
        return []


def get_hybrid_exit_exam_questions(api_key: Optional[str] = None) -> dict:
    """
    Get exit exam questions using hybrid approach:
    1. Try to generate true/false questions using OpenAI
    2. Fall back to static questions if OpenAI fails
    3. Combine both sources
    
    Args:
        api_key: Optional OpenAI API key for dynamic generation
    
    Returns:
        Dictionary with questions array
    """
    # Load static questions as fallback
    static_questions_data = load_exit_exam_questions()
    static_questions = static_questions_data.get('questions', [])
    
    # Try to generate true/false questions if API key provided
    generated_questions = []
    if api_key:
        print("DEBUG: Attempting to generate true/false questions with OpenAI...")
        generated_questions = generate_true_false_questions_with_openai(api_key, count=5)
    
    # Combine questions
    if generated_questions:
        print(f"DEBUG: Using {len(generated_questions)} OpenAI-generated + {len(static_questions)} static questions")
        # Adjust IDs to avoid conflicts
        max_static_id = max([q.get('id', 0) for q in static_questions]) if static_questions else 0
        for i, q in enumerate(generated_questions):
            q['id'] = max_static_id + i + 1
            q['source'] = 'openai_generated'
        
        all_questions = static_questions + generated_questions
    else:
        print(f"DEBUG: Using only {len(static_questions)} static questions (OpenAI generation failed or not available)")
        all_questions = static_questions
    
    return {"questions": all_questions}


def save_individual_survey(user_data):
    """Save individual user survey to separate file"""
    user_id = user_data.get('id')
    email = user_data.get('user_info', {}).get('email', 'unknown').replace('@', '_at_').replace('.', '_')
    filename = f"survey_{user_id}_{email}.json"
    filepath = os.path.join(SURVEYS_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, indent=2, ensure_ascii=False)
    
    return filepath


def save_individual_exit_exam(user_data):
    """Save individual user exit exam to separate file"""
    user_id = user_data.get('id')
    email = user_data.get('user_info', {}).get('email', 'unknown').replace('@', '_at_').replace('.', '_')
    filename = f"exit_exam_{user_id}_{email}.json"
    filepath = os.path.join(EXIT_EXAMS_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, indent=2, ensure_ascii=False)
    
    return filepath


@survey_bp.route('/questions', methods=['GET'])
def get_survey_questions():
    """Get all survey questions"""
    try:
        questions = load_survey_questions()
        return jsonify(questions), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@survey_bp.route('/submit', methods=['POST'])
def submit_survey():
    """Submit survey responses and get AI analysis"""
    try:
        # Check if user is logged in
        if not session.get('user_id'):
            return jsonify({"error": "User not logged in. Please login first."}), 401
        
        data = request.json
        
        # Get user info from session
        user_info = {
            "user_id": session.get('user_id'),
            "name": session.get('full_name'),
            "email": session.get('email'),
            "username": session.get('username'),
            "organization": session.get('organization', '')
        }
        answers = data.get("answers", [])
        
        # Validate that user is logged in
        if not user_info["user_id"]:
            return jsonify({"error": "User session expired. Please login again."}), 401
        
        # Calculate score
        questions_data = load_survey_questions()
        questions = questions_data.get("questions", [])
        
        correct_count = 0
        total_questions = len(questions)
        
        for i, answer in enumerate(answers):
            if i < len(questions):
                question = questions[i]
                correct_answer = question.get("correct_answer")
                
                # Handle bilingual correct answers
                if isinstance(correct_answer, dict):
                    # Check if answer matches either English or Arabic version
                    if answer == correct_answer.get("en") or answer == correct_answer.get("ar"):
                        correct_count += 1
                else:
                    # Legacy format: direct string comparison
                    if answer == correct_answer:
                        correct_count += 1
        
        # Calculate score out of 10 and percentage
        score = round((correct_count / total_questions) * 10, 1) if total_questions > 0 else 0
        percentage = round((correct_count / total_questions) * 100, 1) if total_questions > 0 else 0
        
        # Determine pass/fail status (60% is passing grade)
        pass_status = "passed" if percentage >= 60 else "failed"
        
        # Get AI-powered analysis (using the AIService)
        from app.services.ai_service import AIService
        from config.config import Config
        ai_service = AIService()
        
        # Prepare analysis prompt
        analysis_prompt = f"""
        Analyze this AI and Prompt Engineering assessment:
        
        Score: {correct_count}/{total_questions} correct ({score}/10)
        
        User answered {correct_count} questions correctly out of {total_questions} total questions.
        
        Based on this score, provide:
        1. A brief performance evaluation (2-3 sentences)
        2. Three specific recommendations to improve their AI and prompt engineering knowledge
        3. Suggested learning areas to focus on
        
        Format your response as JSON with this structure:
        {{
            "evaluation": "Your evaluation text here",
            "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"],
            "focus_areas": ["area 1", "area 2", "area 3"]
        }}
        """
        
        # Get AI analysis
        ai_analysis = None
        try:
            # Get OpenAI API key from config
            openai_key = Config.OPENAI_API_KEY
            
            if openai_key:
                ai_response = ai_service.chat(
                    provider="openai",
                    message=analysis_prompt,
                    api_key=openai_key,
                    files=None
                )
                
                # Parse AI response
                if ai_response and "text" in ai_response:
                    response_text = ai_response["text"]
                    # Try to extract JSON from response
                    import re
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        ai_analysis = json.loads(json_match.group())
        except Exception as e:
            print(f"AI analysis error: {e}")
        
        # ALWAYS provide default analysis if AI analysis failed or key is missing
        if ai_analysis is None:
            ai_analysis = {
                "evaluation": f"You scored {score}/10 on the assessment. This shows {'excellent' if score >= 8 else 'good' if score >= 6 else 'basic'} understanding of AI and prompt engineering concepts.",
                "recommendations": [
                    "Practice more with different AI models to understand their capabilities",
                    "Study prompt engineering techniques like few-shot learning and chain-of-thought",
                    "Experiment with various prompt structures to see what works best"
                ],
                "focus_areas": [
                    "AI model capabilities and limitations",
                    "Prompt engineering best practices",
                    "Understanding context windows and tokens"
                ]
            }
        
        # Create user record
        # certificate_status: "pending" (awaiting admin approval), "pass" (approved), "fail" (rejected/failed)
        # Students who pass (60%+) get "pending" status, need admin approval to get "pass"
        # Students who fail (<60%) get "fail" status
        cert_status = "pending" if percentage >= 60 else "fail"
        user_record = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "timestamp": datetime.now().isoformat(),
            "user_info": user_info,
            "answers": answers,
            "score": score,
            "percentage": percentage,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "pass_status": pass_status,
            "analysis": ai_analysis,
            "certificate_status": cert_status,  # "pending", "pass", or "fail"
            "can_retake": cert_status == "fail",  # Allow retake only if failed
            "admin_override": False  # Track if admin forced certificate generation
        }
        
        # Save to main file
        survey_data = load_survey_data()
        survey_data["users"].append(user_record)
        save_survey_data(survey_data)
        
        # Save individual user file
        try:
            save_individual_survey(user_record)
        except Exception as e:
            print(f"Warning: Could not save individual survey file: {e}")
        
        # Return results
        return jsonify({
            "success": True,
            "user_id": user_record["id"],
            "score": score,
            "percentage": percentage,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "pass_status": pass_status,
            "analysis": ai_analysis,
            "certificate_status": user_record["certificate_status"],
            "can_retake": user_record["can_retake"]
        }), 200
        
    except Exception as e:
        print(f"Error in submit_survey: {e}")
        return jsonify({"error": str(e)}), 500


@survey_bp.route('/users', methods=['GET'])
@admin_required
def get_survey_users():
    """Get all survey users (admin only)"""
    try:
        survey_data = load_survey_data()
        return jsonify(survey_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@survey_bp.route('/user/<user_id>/status', methods=['PUT'])
@admin_required
def update_user_status(user_id):
    """Update user certificate status (admin only)"""
    try:
        data = request.json
        new_status = data.get("status")
        
        if new_status not in ["pass", "fail"]:
            return jsonify({"error": "Invalid status"}), 400
        
        survey_data = load_survey_data()
        users = survey_data.get("users", [])
        
        # Find and update user
        user_found = False
        for user in users:
            if user["id"] == user_id:
                user["certificate_status"] = new_status
                user_found = True
                break
        
        if not user_found:
            return jsonify({"error": "User not found"}), 404
        
        save_survey_data(survey_data)
        
        return jsonify({"success": True, "status": new_status}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@survey_bp.route('/certificate-status', methods=['PUT'])
@admin_required
def update_certificate_status():
    """Update certificate status for entry survey or exit exam (admin only)"""
    try:
        data = request.json
        user_id = data.get("user_id")
        exam_type = data.get("exam_type")  # "entry_survey" or "exit_exam"
        new_status = data.get("status")
        
        if not user_id or not exam_type or not new_status:
            return jsonify({"error": "Missing required fields"}), 400
        
        if new_status not in ["pass", "fail"]:
            return jsonify({"error": "Invalid status"}), 400
        
        # Determine which data to load
        if exam_type == "exit_exam":
            exam_data = load_exit_exam_data()
            users = exam_data.get("users", [])
        else:
            exam_data = load_survey_data()
            users = exam_data.get("users", [])
        
        # Find and update user
        user_found = False
        for user in users:
            if user["id"] == user_id:
                user["certificate_status"] = new_status
                user_found = True
                break
        
        if not user_found:
            return jsonify({"error": "User not found"}), 404
        
        # Save data
        if exam_type == "exit_exam":
            save_exit_exam_data(exam_data)
        else:
            save_survey_data(exam_data)
        
        return jsonify({"success": True, "status": new_status}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@survey_bp.route('/user/<user_id>/force-certificate', methods=['POST'])
@admin_required
def force_certificate(user_id):
    """Force certificate generation for a user even if they failed (admin only)"""
    try:
        # Log admin override action
        admin_user = session.get('username', 'unknown')
        print(f"ADMIN OVERRIDE: {admin_user} forcing certificate for survey user {user_id}")
        
        survey_data = load_survey_data()
        users = survey_data.get("users", [])
        
        user_found = False
        for user in users:
            if user["id"] == user_id:
                # Log before state
                print(f"  Previous status: {user.get('certificate_status')} | pass_status: {user.get('pass_status')} | score: {user.get('score')}")
                
                user["certificate_status"] = "pass"  # Use "pass" not "passed" to match download check
                user["admin_override"] = True
                user["can_retake"] = False
                user_found = True
                
                # Log after state
                print(f"  New status: passed (admin override) | user: {user.get('user_info', {}).get('name')}")
                break
        
        if not user_found:
            return jsonify({"error": "User not found"}), 404
        
        save_survey_data(survey_data)
        
        return jsonify({"success": True, "message": "Certificate generation forced"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@survey_bp.route('/user/<user_id>/allow-retake', methods=['POST'])
@admin_required
def allow_retake(user_id):
    """Allow a user to retake the survey (admin only)"""
    try:
        survey_data = load_survey_data()
        users = survey_data.get("users", [])
        
        user_found = False
        for user in users:
            if user["id"] == user_id:
                user["can_retake"] = True
                user_found = True
                break
        
        if not user_found:
            return jsonify({"error": "User not found"}), 404
        
        save_survey_data(survey_data)
        
        return jsonify({"success": True, "message": "Retake enabled for user"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@survey_bp.route('/exit-exam/user/<user_id>/force-certificate', methods=['POST'])
@admin_required
def force_exit_exam_certificate(user_id):
    """Force certificate generation for exit exam user even if they failed (admin only)"""
    try:
        # Log admin override action
        admin_user = session.get('username', 'unknown')
        print(f"ADMIN OVERRIDE: {admin_user} forcing certificate for exit exam user {user_id}")
        
        exam_data = load_exit_exam_data()
        users = exam_data.get("users", [])
        
        user_found = False
        for user in users:
            if user["id"] == user_id:
                # Log before state
                print(f"  Previous status: {user.get('certificate_status')} | pass_status: {user.get('pass_status')} | score: {user.get('score')}")
                
                user["certificate_status"] = "pass"  # Use "pass" not "passed" to match download check
                user["admin_override"] = True
                user["can_retake"] = False
                user_found = True
                
                # Log after state
                print(f"  New status: passed (admin override) | user: {user.get('user_info', {}).get('name')}")
                break
        
        if not user_found:
            return jsonify({"error": "User not found"}), 404
        
        save_exit_exam_data(exam_data)
        
        return jsonify({"success": True, "message": "Certificate generation forced"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@survey_bp.route('/exit-exam/user/<user_id>/allow-retake', methods=['POST'])
@admin_required
def allow_exit_exam_retake(user_id):
    """Allow a user to retake the exit exam (admin only)"""
    try:
        exam_data = load_exit_exam_data()
        users = exam_data.get("users", [])
        
        user_found = False
        for user in users:
            if user["id"] == user_id:
                user["can_retake"] = True
                user_found = True
                break
        
        if not user_found:
            return jsonify({"error": "User not found"}), 404
        
        save_exit_exam_data(exam_data)
        
        return jsonify({"success": True, "message": "Retake enabled for user"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_next_certificate_number():
    """Generate next certificate number in format AICA-YYYYMMDD-serial"""
    from datetime import datetime
    
    # Load survey data to get/set certificate counter
    survey_data = load_survey_data()
    
    # Initialize certificate counter if not exists
    if "certificate_counter" not in survey_data:
        survey_data["certificate_counter"] = 1000
    
    # Increment counter
    survey_data["certificate_counter"] += 1
    serial = survey_data["certificate_counter"]
    
    # Save updated counter
    save_survey_data(survey_data)
    
    # Generate certificate number: AICA-YYYYMMDD-serial
    date_str = datetime.now().strftime("%Y%m%d")
    cert_number = f"AICA-{date_str}-{serial}"
    
    return cert_number


@survey_bp.route('/certificate/<user_id>', methods=['GET'])
def generate_certificate(user_id):
    """Generate and download certificate for a user - matches superadmin/class_management professional template"""
    try:
        # Import PDF generation library
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.colors import HexColor, black
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        import io
        import qrcode
        from datetime import datetime
        
        # Load user data
        survey_data = load_survey_data()
        users = survey_data.get("users", [])
        
        user = None
        for u in users:
            if u["id"] == user_id:
                user = u
                break
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Check if certificate has been issued by admin
        if user.get("certificate_status") != "pass":
            return jsonify({"error": "Certificate has not been issued by admin yet"}), 400
        
        # Generate or get certificate number
        if "certificate_number" not in user:
            user["certificate_number"] = get_next_certificate_number()
            save_survey_data(survey_data)
        
        cert_number = user["certificate_number"]
        
        # Get user name - from users.json for up-to-date name
        users_data = load_users()
        real_user_id = user.get("user_info", {}).get("user_id")
        current_user = next((u for u in users_data.get('users', []) if u.get('user_id') == real_user_id), None)
        
        if current_user and current_user.get('full_name'):
            user_name = current_user.get('full_name')
        else:
            user_name = user["user_info"]["name"]
        
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
        c.drawCentredString(page_width / 2, page_height - 115, "OF COMPLETION")
        
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
        c.drawCentredString(page_width / 2, page_height - 235, "has successfully completed the training program")
        
        # Course Title - AI Prompt Engineering Entry Survey
        course_title = "AI Prompt Engineering Entry Survey"
        c.setFillColor(dark_blue)
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(page_width / 2, page_height - 275, course_title)
        
        # Admin override badge if applicable
        if user.get("admin_override"):
            c.setFont("Helvetica-Bold", 11)
            c.setFillColor(HexColor('#dc2626'))
            c.drawCentredString(page_width / 2, page_height - 305, "Administrator Approved")
        
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
                stamp_width = 80
                stamp_height = 80
                stamp_x = 140 - stamp_width/2
                stamp_y = sig_y + 55
                c.drawImage(chair_stamp_path, stamp_x, stamp_y, width=stamp_width, height=stamp_height, preserveAspectRatio=True)
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
        completion_date = datetime.fromisoformat(user["timestamp"]).strftime("%B %d, %Y")
        c.setFillColor(black)
        c.setFont("Helvetica", 10)
        c.drawCentredString(page_width / 2, sig_y + 100, "Date of Issue")
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(page_width / 2, sig_y + 82, completion_date)
        
        # CENTER - QR Code for verification
        qr_size = 90
        from flask import request
        base_url = request.host_url.rstrip('/')
        verification_url = f"{base_url}/api/survey/certificate/{user_id}"
        
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
        
        # Save to file
        filename = f"certificate_{user['user_info']['name'].replace(' ', '_')}_{user_id}.pdf"
        filepath = os.path.join(CERTIFICATES_DIR, filename)
        
        with open(filepath, 'wb') as f:
            f.write(buffer.getvalue())
        
        buffer.seek(0)
        
        # Return PDF file
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Error generating certificate: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@survey_bp.route('/results/<user_id>/pdf', methods=['GET'])
def download_results_pdf(user_id):
    """Generate and download analysis results PDF"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
        import io
        
        # Load user data
        survey_data = load_survey_data()
        users = survey_data.get("users", [])
        
        user = None
        for u in users:
            if u["id"] == user_id:
                user = u
                break
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Create PDF
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # ========================================
        # LOGOS AT TOP - PROMINENT DISPLAY
        # ========================================
        logo_size = 70
        logo_top_position = height - 85
        
        try:
            # AI Logo on left
            ai_logo_path = "static/images/ai-logo.png"
            if os.path.exists(ai_logo_path):
                c.drawImage(ai_logo_path, 50, logo_top_position, 
                           width=logo_size, height=logo_size, 
                           preserveAspectRatio=True, mask='auto')
            
            # AC Logo on right
            ac_logo_path = "static/images/ac-logo.png"
            if os.path.exists(ac_logo_path):
                c.drawImage(ac_logo_path, width - 120, logo_top_position, 
                           width=logo_size, height=logo_size, 
                           preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Error adding logos to results PDF: {e}")
        
        # Title - positioned below logos
        c.setFont("Helvetica-Bold", 22)
        c.setFillColorRGB(0.4, 0.49, 0.92)
        c.drawCentredString(width / 2, height - 110, "AI Prompt Engineering")
        c.drawCentredString(width / 2, height - 135, "Assessment Results")
        
        # Horizontal line
        c.setLineWidth(2)
        c.setStrokeColorRGB(0.4, 0.49, 0.92)
        c.line(50, height - 150, width - 50, height - 150)
        
        # User info
        c.setFont("Helvetica-Bold", 13)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(50, height - 180, f"Name: {user['user_info']['name']}")
        organization = user['user_info'].get('organization', user['user_info'].get('college', 'N/A'))
        c.drawString(50, height - 200, f"College/Unit: {organization}")
        c.drawString(50, height - 220, f"Email: {user['user_info']['email']}")
        
        # Score section with background
        c.setFillColorRGB(0.95, 0.97, 1.0)
        c.rect(50, height - 280, width - 100, 40, fill=1, stroke=0)
        
        c.setFont("Helvetica-Bold", 18)
        c.setFillColorRGB(0.4, 0.49, 0.92)
        c.drawString(60, height - 260, f"Score: {user['score']}/10")
        c.setFont("Helvetica", 14)
        c.drawString(60, height - 275, f"Correct Answers: {user['correct_count']}/{user['total_questions']}")
        
        # Analysis
        if user.get("analysis"):
            analysis = user["analysis"]
            
            # Evaluation
            c.setFont("Helvetica-Bold", 14)
            c.setFillColorRGB(0.4, 0.49, 0.92)
            c.drawString(50, height - 320, "Performance Evaluation:")
            c.setFont("Helvetica", 11)
            c.setFillColorRGB(0, 0, 0)
            
            # Wrap text
            eval_text = analysis.get("evaluation", "")
            words = eval_text.split()
            lines = []
            current_line = []
            for word in words:
                current_line.append(word)
                if len(' '.join(current_line)) > 90:
                    lines.append(' '.join(current_line[:-1]))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
            
            y_pos = height - 340
            for line in lines[:4]:  # Show up to 4 lines
                c.drawString(60, y_pos, line)
                y_pos -= 15
            
            # Recommendations
            c.setFont("Helvetica-Bold", 14)
            c.setFillColorRGB(0.4, 0.49, 0.92)
            c.drawString(50, y_pos - 20, "Recommendations:")
            c.setFont("Helvetica", 11)
            c.setFillColorRGB(0, 0, 0)
            
            y_pos -= 40
            for i, rec in enumerate(analysis.get("recommendations", [])[:4], 1):
                # Wrap recommendation text
                rec_words = rec.split()
                rec_lines = []
                rec_current = []
                for word in rec_words:
                    rec_current.append(word)
                    if len(' '.join(rec_current)) > 85:
                        rec_lines.append(' '.join(rec_current[:-1]))
                        rec_current = [word]
                if rec_current:
                    rec_lines.append(' '.join(rec_current))
                
                c.drawString(60, y_pos, f"{i}. {rec_lines[0]}")
                y_pos -= 15
                for extra_line in rec_lines[1:]:
                    c.drawString(75, y_pos, extra_line)
                    y_pos -= 15
            
            # Focus Areas
            c.setFont("Helvetica-Bold", 14)
            c.setFillColorRGB(0.4, 0.49, 0.92)
            c.drawString(50, y_pos - 20, "Focus Areas:")
            c.setFont("Helvetica", 11)
            c.setFillColorRGB(0, 0, 0)
            
            y_pos -= 40
            for area in analysis.get("focus_areas", [])[:4]:
                c.drawString(60, y_pos, f"• {area}")
                y_pos -= 18
        
        # Footer
        c.setFont("Helvetica", 8)
        c.drawString(50, 30, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        c.save()
        buffer.seek(0)
        
        filename = f"results_{user['user_info']['name'].replace(' ', '_')}_{user_id}.pdf"
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Error generating results PDF: {e}")
        return jsonify({"error": str(e)}), 500

# ===================================
# SETTINGS ROUTES
# ===================================

@survey_bp.route('/settings', methods=['GET'])
def get_settings():
    """Get admin settings for survey and exit exam"""
    try:
        settings = load_settings()
        return jsonify(settings), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@survey_bp.route('/settings', methods=['PUT'])
def update_settings():
    """Update admin settings"""
    try:
        data = request.json
        settings = load_settings()
        
        if 'survey_enabled' in data:
            settings['survey_enabled'] = bool(data['survey_enabled'])
        if 'exit_exam_enabled' in data:
            settings['exit_exam_enabled'] = bool(data['exit_exam_enabled'])
        
        save_settings(settings)
        return jsonify({"success": True, "settings": settings}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===================================
# EXIT EXAM ROUTES
# ===================================

@survey_bp.route('/exit-exam/questions', methods=['GET'])
def get_exit_exam_questions():
    """Get all exit exam questions (static only for performance)"""
    try:
        # Load static questions only - no dynamic generation for better performance
        questions_data = load_exit_exam_questions()
        return jsonify(questions_data), 200
    except Exception as e:
        print(f"ERROR: Failed to get exit exam questions: {e}")
        return jsonify({"error": str(e)}), 500


@survey_bp.route('/exit-exam/submit', methods=['POST'])
def submit_exit_exam():
    """Submit exit exam responses and get AI analysis"""
    try:
        # Check if user is logged in
        if not session.get('user_id'):
            return jsonify({"error": "User not logged in. Please login first."}), 401
        
        data = request.json
        
        # Get user info from session
        user_info = {
            "user_id": session.get('user_id'),
            "name": session.get('full_name'),
            "email": session.get('email'),
            "username": session.get('username'),
            "organization": session.get('organization', '')
        }
        answers = data.get("answers", [])
        
        # Validate that user is logged in
        if not user_info["user_id"]:
            return jsonify({"error": "User session expired. Please login again."}), 401
        
        # Check if this user has already taken the exam and can retake
        exam_data = load_exit_exam_data()
        existing_users = exam_data.get("users", [])
        latest_attempt = None
        for existing_user in existing_users:
            if existing_user.get("user_info", {}).get("user_id") == user_info["user_id"]:
                latest_attempt = existing_user
        
        # If user has taken exam before, check if they can retake
        if latest_attempt and not latest_attempt.get("can_retake", False):
            return jsonify({"error": "You have already passed this exam. Retake is not allowed for passed exams unless enabled by admin."}), 400
        
        # Calculate score
        questions_data = load_exit_exam_questions()
        questions = questions_data.get("questions", [])
        
        correct_count = 0
        total_questions = len(questions)
        
        for i, answer in enumerate(answers):
            if i < len(questions):
                question = questions[i]
                correct_answer = question.get("correct_answer")
                
                # Handle bilingual correct answers
                if isinstance(correct_answer, dict):
                    # Check if answer matches either English or Arabic version
                    if answer == correct_answer.get("en") or answer == correct_answer.get("ar"):
                        correct_count += 1
                else:
                    # Legacy format: direct string comparison
                    if answer == correct_answer:
                        correct_count += 1
        
        # Calculate score out of 10 and percentage
        score = round((correct_count / total_questions) * 10, 1) if total_questions > 0 else 0
        percentage = round((correct_count / total_questions) * 100, 1) if total_questions > 0 else 0
        
        # Determine pass/fail status (60% is passing grade)
        pass_status = "passed" if percentage >= 60 else "failed"
        
        # Get AI-powered analysis
        from app.services.ai_service import AIService
        from config.config import Config
        ai_service = AIService()
        
        # Prepare analysis prompt
        analysis_prompt = f"""
        Analyze this Exit Exam for Prompt Engineering:
        
        Score: {correct_count}/{total_questions} correct ({score}/10)
        
        This is a final exam. User answered {correct_count} questions correctly out of {total_questions} total questions.
        
        Based on this score, provide:
        1. A brief final evaluation (2-3 sentences)
        2. Three specific recommendations for continued learning
        3. Suggested next steps to advance their prompt engineering skills
        
        Format your response as JSON with this structure:
        {{
            "evaluation": "Your evaluation text here",
            "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"],
            "focus_areas": ["area 1", "area 2", "area 3"]
        }}
        """
        
        # Get AI analysis
        ai_analysis = None
        try:
            openai_key = Config.OPENAI_API_KEY
            
            if openai_key:
                ai_response = ai_service.chat(
                    provider="openai",
                    message=analysis_prompt,
                    api_key=openai_key,
                    files=None
                )
                
                if ai_response and "text" in ai_response:
                    response_text = ai_response["text"]
                    import re
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        ai_analysis = json.loads(json_match.group())
        except Exception as e:
            print(f"AI analysis error: {e}")
        
        # Default analysis if AI analysis failed
        if ai_analysis is None:
            # Determine performance level and appropriate messaging
            if score >= 9:
                performance = "excellent"
                evaluation = f"Outstanding performance! You scored {score}/10 on the exit exam, demonstrating excellent mastery of prompt engineering fundamentals."
                recommendations = [
                    "Continue practicing with real-world AI applications",
                    "Explore advanced techniques like meta-prompting and chain-of-thought prompting",
                    "Consider mentoring others in prompt engineering"
                ]
                focus_areas = [
                    "Advanced prompt engineering patterns",
                    "AI safety and ethical considerations",
                    "Domain-specific AI applications"
                ]
            elif score >= 8:
                performance = "very good"
                evaluation = f"Very good work! You scored {score}/10 on the exit exam, showing strong understanding of prompt engineering fundamentals."
                recommendations = [
                    "Continue practicing with real-world AI applications",
                    "Explore advanced techniques like meta-prompting and recursive prompting",
                    "Join AI communities to learn from others' experiences"
                ]
                focus_areas = [
                    "Advanced prompt engineering patterns",
                    "Context optimization techniques",
                    "Multi-model comparison strategies"
                ]
            elif score >= 6:
                performance = "adequate"
                evaluation = f"You passed with a score of {score}/10. This demonstrates adequate understanding of prompt engineering fundamentals, though there's room for improvement."
                recommendations = [
                    "Review the concepts you found challenging",
                    "Practice writing prompts for different use cases",
                    "Study examples of effective prompt patterns"
                ]
                focus_areas = [
                    "Prompt structure and clarity",
                    "Providing context and examples",
                    "Understanding AI model limitations"
                ]
            elif score >= 4:
                performance = "limited"
                evaluation = f"You scored {score}/10 on the exit exam. This indicates limited understanding of prompt engineering fundamentals. More study and practice are needed to achieve proficiency."
                recommendations = [
                    "Review all fundamental concepts of prompt engineering",
                    "Practice with simple prompts before advancing to complex ones",
                    "Study the course materials again with focus on key concepts",
                    "Seek guidance from instructors or experienced practitioners"
                ]
                focus_areas = [
                    "Basic prompt structure and components",
                    "Understanding how AI models process instructions",
                    "Clear communication and specificity in prompts"
                ]
            else:  # score < 4
                performance = "poor"
                evaluation = f"You scored {score}/10 on the exit exam. This indicates significant gaps in understanding prompt engineering fundamentals. We strongly recommend reviewing the foundational concepts before attempting the exam again."
                recommendations = [
                    "Restart the course from the beginning",
                    "Focus on understanding basic AI concepts first",
                    "Practice with guided examples and tutorials",
                    "Seek one-on-one tutoring or additional support",
                    "Take time to fully grasp each concept before moving forward"
                ]
                focus_areas = [
                    "Fundamental AI and LLM concepts",
                    "What prompts are and why they matter",
                    "Basic prompt writing techniques"
                ]
            
            ai_analysis = {
                "evaluation": evaluation,
                "recommendations": recommendations,
                "focus_areas": focus_areas
            }
        
        # Create user record
        # certificate_status: "pending" (awaiting admin approval), "pass" (approved), "fail" (rejected/failed)
        # Students who pass (60%+) get "pending" status, need admin approval to get "pass"
        # Students who fail (<60%) get "fail" status
        cert_status = "pending" if percentage >= 60 else "fail"
        user_record = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "timestamp": datetime.now().isoformat(),
            "user_info": user_info,
            "answers": answers,
            "score": score,
            "percentage": percentage,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "pass_status": pass_status,
            "analysis": ai_analysis,
            "certificate_status": cert_status,  # "pending", "pass", or "fail"
            "can_retake": cert_status == "fail",  # Allow retake only if failed
            "admin_override": False  # Track if admin forced certificate generation
        }
        
        # Save to main file (reload to avoid race condition with duplicate check)
        exam_data = load_exit_exam_data()
        exam_data["users"].append(user_record)
        save_exit_exam_data(exam_data)
        
        # Save individual user file
        try:
            save_individual_exit_exam(user_record)
        except Exception as e:
            print(f"Warning: Could not save individual exit exam file: {e}")
        
        # Return results
        return jsonify({
            "success": True,
            "user_id": user_record["id"],
            "score": score,
            "percentage": percentage,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "pass_status": pass_status,
            "analysis": ai_analysis,
            "certificate_status": user_record["certificate_status"],
            "can_retake": user_record["can_retake"]
        }), 200
        
    except Exception as e:
        print(f"Error submitting exit exam: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@survey_bp.route('/my-certificates', methods=['GET'])
def get_my_certificates():
    """Get certificates for the logged-in user"""
    try:
        # Check if user is logged in
        if not session.get('user_id'):
            return jsonify({"error": "User not logged in"}), 401
        
        user_id = session.get('user_id')
        certificates = []
        
        # Check survey certificates
        survey_data = load_survey_data()
        for user in survey_data.get("users", []):
            if user.get("user_info", {}).get("user_id") == user_id:
                # Check for both "pass" and "passed" to handle old data
                cert_status = user.get("certificate_status", "")
                if cert_status in ["pass", "passed"]:
                    certificates.append({
                        "type": "Entry Survey",
                        "id": user.get("id"),
                        "timestamp": user.get("timestamp"),
                        "score": user.get("score"),
                        "correct_count": user.get("correct_count"),
                        "total_questions": user.get("total_questions"),
                        "percentage": user.get("percentage", 0),
                        "certificate_number": user.get("certificate_number"),
                        "admin_override": user.get("admin_override", False)
                    })
        
        # Check exit exam certificates
        exam_data = load_exit_exam_data()
        for user in exam_data.get("users", []):
            if user.get("user_info", {}).get("user_id") == user_id:
                # Check for both "pass" and "passed" to handle old data
                cert_status = user.get("certificate_status", "")
                if cert_status in ["pass", "passed"]:
                    certificates.append({
                        "type": "Exit Exam",
                        "id": user.get("id"),
                        "timestamp": user.get("timestamp"),
                        "score": user.get("score"),
                        "correct_count": user.get("correct_count"),
                        "total_questions": user.get("total_questions"),
                        "percentage": user.get("percentage", 0),
                        "certificate_number": user.get("certificate_number"),
                        "admin_override": user.get("admin_override", False)
                    })
        
        return jsonify({"certificates": certificates}), 200
        
    except Exception as e:
        print(f"Error getting certificates: {e}")
        return jsonify({"error": str(e)}), 500


@survey_bp.route('/exit-exam/users', methods=['GET'])
@admin_required
def get_exit_exam_users():
    """Get all users who completed the exit exam (admin only)"""
    try:
        exam_data = load_exit_exam_data()
        users = exam_data.get("users", [])
        
        # Fix old data missing percentage and pass_status fields
        for user in users:
            # Compute percentage if missing
            if "percentage" not in user and "correct_count" in user and "total_questions" in user:
                total = user["total_questions"]
                if total > 0:
                    user["percentage"] = round((user["correct_count"] / total) * 100, 1)
                else:
                    user["percentage"] = 0
            
            # Compute pass_status if missing
            if "pass_status" not in user:
                percentage = user.get("percentage", 0)
                user["pass_status"] = "passed" if percentage >= 60 else "failed"
            
            # Normalize certificate_status to "pass"/"fail" if it's "passed"/"failed"
            if user.get("certificate_status") == "passed":
                user["certificate_status"] = "pass"
            elif user.get("certificate_status") == "failed":
                user["certificate_status"] = "fail"
        
        return jsonify({"users": users}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@survey_bp.route('/exit-exam/issue-certificate/<user_id>', methods=['POST'])
@admin_required
def issue_exit_exam_certificate(user_id):
    """Admin endpoint to issue certificate for a user who completed the exit exam"""
    try:
        exam_data = load_exit_exam_data()
        users = exam_data.get("users", [])
        
        user = None
        user_index = None
        for i, u in enumerate(users):
            if u["id"] == user_id:
                user = u
                user_index = i
                break
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Update certificate status to "pass" (issued by admin)
        exam_data["users"][user_index]["certificate_status"] = "pass"
        save_exit_exam_data(exam_data)
        
        return jsonify({
            "success": True,
            "message": "Certificate issued successfully",
            "user_id": user_id
        }), 200
        
    except Exception as e:
        print(f"Error issuing certificate: {e}")
        return jsonify({"error": str(e)}), 500


@survey_bp.route('/exit-exam/certificate/<user_id>', methods=['GET'])
def generate_exit_exam_certificate(user_id):
    """Generate and download certificate for exit exam - uses professional landscape template"""
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.colors import HexColor, black
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        import io
        import qrcode
        from datetime import datetime
        
        # Load user data
        exam_data = load_exit_exam_data()
        users = exam_data.get("users", [])
        
        user = None
        for u in users:
            if u["id"] == user_id:
                user = u
                break
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Check if certificate has been issued by admin (certificate_status changed to "pass")
        if user.get("certificate_status") != "pass":
            return jsonify({"error": "Certificate has not been issued by admin yet"}), 400
        
        # Generate or get certificate number
        if "certificate_number" not in user:
            user["certificate_number"] = get_next_certificate_number()
            save_exit_exam_data(exam_data)
        
        cert_number = user["certificate_number"]
        
        # Get user name from users.json for up-to-date info
        users_data = load_users()
        real_user_id = user.get("user_info", {}).get("user_id")
        current_user = next((u for u in users_data.get('users', []) if u.get('user_id') == real_user_id), None)
        
        if current_user and current_user.get('full_name'):
            user_name = current_user.get('full_name')
        else:
            user_name = user["user_info"]["name"]
        
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
        c.drawCentredString(page_width / 2, page_height - 115, "OF COMPLETION")
        
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
        c.drawCentredString(page_width / 2, page_height - 235, "has successfully completed the training program")
        
        # Course Title - AI Prompt Engineering Training (Exit Exam)
        course_title = "AI Prompt Engineering Training"
        c.setFillColor(dark_blue)
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(page_width / 2, page_height - 275, course_title)
        
        # Admin override badge if applicable
        if user.get("admin_override"):
            c.setFont("Helvetica-Bold", 11)
            c.setFillColor(HexColor('#dc2626'))
            c.drawCentredString(page_width / 2, page_height - 305, "Administrator Approved")
        
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
        completion_date = datetime.fromisoformat(user["timestamp"]).strftime("%B %d, %Y")
        c.setFillColor(black)
        c.setFont("Helvetica", 10)
        c.drawCentredString(page_width / 2, sig_y + 100, "Date of Issue")
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(page_width / 2, sig_y + 82, completion_date)
        
        # CENTER - QR Code for verification
        qr_size = 90
        from flask import request
        base_url = request.host_url.rstrip('/')
        verification_url = f"{base_url}/api/survey/exit-exam/certificate/{user_id}"
        
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
        
        # Save to file
        filename = f"exit_exam_certificate_{user['user_info']['name'].replace(' ', '_')}_{user_id}.pdf"
        filepath = os.path.join(CERTIFICATES_DIR, filename)
        
        with open(filepath, 'wb') as f:
            f.write(buffer.getvalue())
        
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Error generating exit exam certificate: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ===================================
# EXIT SURVEY ROUTES (FEEDBACK COLLECTION)
# ===================================

EXIT_SURVEY_QUESTIONS_FILE = 'exit_survey_questions.json'
EXIT_SURVEY_RESPONSES_FILE = 'exit_survey_responses.json'
EXIT_SURVEYS_DIR = os.path.join(EXAM_DATA_DIR, 'exit_surveys')

# Ensure directory exists
Path(EXIT_SURVEYS_DIR).mkdir(parents=True, exist_ok=True)


def load_exit_survey_questions():
    """Load exit survey questions from JSON file"""
    if os.path.exists(EXIT_SURVEY_QUESTIONS_FILE):
        with open(EXIT_SURVEY_QUESTIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"questions": []}


def load_exit_survey_responses():
    """Load exit survey responses from JSON file"""
    if os.path.exists(EXIT_SURVEY_RESPONSES_FILE):
        with open(EXIT_SURVEY_RESPONSES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"responses": []}


def save_exit_survey_responses(data):
    """Save exit survey responses to JSON file"""
    with open(EXIT_SURVEY_RESPONSES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_individual_exit_survey(response_data):
    """Save individual user exit survey to separate file"""
    user_id = response_data.get('id')
    email = response_data.get('user_info', {}).get('email', 'unknown').replace('@', '_at_').replace('.', '_')
    filename = f"exit_survey_{user_id}_{email}.json"
    filepath = os.path.join(EXIT_SURVEYS_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(response_data, f, indent=2, ensure_ascii=False)
    
    return filepath


@survey_bp.route('/exit-survey/questions', methods=['GET'])
def get_exit_survey_questions():
    """Get all exit survey questions"""
    try:
        questions = load_exit_survey_questions()
        return jsonify(questions), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@survey_bp.route('/exit-survey/submit', methods=['POST'])
def submit_exit_survey():
    """Submit exit survey responses (feedback collection, no scoring)"""
    try:
        # Check if user is logged in
        if not session.get('user_id'):
            return jsonify({"error": "User not logged in. Please login first."}), 401
        
        data = request.json
        
        # Get user info from session
        user_info = {
            "user_id": session.get('user_id'),
            "name": session.get('full_name'),
            "email": session.get('email'),
            "username": session.get('username'),
            "organization": session.get('organization', '')
        }
        responses = data.get("responses", {})
        
        # Validate that user is logged in
        if not user_info["user_id"]:
            return jsonify({"error": "User session expired. Please login again."}), 401
        
        # Create response record
        response_record = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "timestamp": datetime.now().isoformat(),
            "user_info": user_info,
            "responses": responses
        }
        
        # Save to main file
        survey_data = load_exit_survey_responses()
        survey_data["responses"].append(response_record)
        save_exit_survey_responses(survey_data)
        
        # Save individual user file
        try:
            save_individual_exit_survey(response_record)
        except Exception as e:
            print(f"Warning: Could not save individual exit survey file: {e}")
        
        # Return success
        return jsonify({
            "success": True,
            "message": "Thank you for your feedback!",
            "response_id": response_record["id"]
        }), 200
        
    except Exception as e:
        print(f"Error in submit_exit_survey: {e}")
        return jsonify({"error": str(e)}), 500


@survey_bp.route('/exit-survey/responses', methods=['GET'])
@admin_required
def get_exit_survey_responses():
    """Get all exit survey responses (admin only)"""
    try:
        responses = load_exit_survey_responses()
        return jsonify(responses), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
