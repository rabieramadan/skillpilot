"""
SkillPilot Database Models - Single-Institution Architecture
PostgreSQL with Flask-SQLAlchemy

Roles: superadmin, admin, teacher, student
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

def generate_uuid():
    return str(uuid.uuid4())


# ============================================
# SITE SETTINGS (Replaces Institution for single-tenant)
# ============================================

class SiteSettings(db.Model):
    """Site-wide settings and branding (singleton)"""
    __tablename__ = 'site_settings'

    id = db.Column(db.Integer, primary_key=True, default=1)

    # Branding
    site_name = db.Column(db.String(100), default='SkillPilot')
    site_name_ar = db.Column(db.String(100), default='سكيل بايلوت')
    logo_url = db.Column(db.String(500))
    logo_url_2 = db.Column(db.String(500))  # Secondary logo
    favicon_url = db.Column(db.String(500))
    primary_color = db.Column(db.String(7), default='#1B5E20')
    secondary_color = db.Column(db.String(7), default='#2E7D32')

    # Hero Section
    hero_title = db.Column(db.String(255), default='AI-Powered Training Platform')
    hero_title_ar = db.Column(db.String(255), default='منصة تدريب مدعومة بالذكاء الاصطناعي')
    hero_subtitle = db.Column(db.Text, default='Empower your learning journey with cutting-edge AI technology')
    hero_subtitle_ar = db.Column(db.Text, default='مكّن رحلتك التعليمية بتقنية الذكاء الاصطناعي المتطورة')
    hero_image_url = db.Column(db.String(500))

    # Footer/Contact
    footer_text = db.Column(db.Text)
    contact_email = db.Column(db.String(255))

    # Registration Settings
    allow_student_registration = db.Column(db.Boolean, default=True)
    allow_teacher_registration = db.Column(db.Boolean, default=True)

    # Payment
    paypal_link = db.Column(db.String(500))

    # Landing Page Sections (JSON for flexible configuration)
    # Structure: [{"id": "features", "enabled": true, "title": "...", "content": "...", "image_url": "..."}, ...]
    landing_sections = db.Column(db.Text)  # JSON string for landing page sections
    
    # Additional landing page fields
    about_title = db.Column(db.String(255), default='About Us')
    about_title_ar = db.Column(db.String(255), default='معلومات عنا')
    about_content = db.Column(db.Text)
    about_content_ar = db.Column(db.Text)
    about_image_url = db.Column(db.String(500))
    
    features_title = db.Column(db.String(255), default='Our Features')
    features_title_ar = db.Column(db.String(255), default='ميزاتنا')
    features_content = db.Column(db.Text)  # JSON array of feature items
    
    courses_section_title = db.Column(db.String(255), default='Our Courses')
    courses_section_title_ar = db.Column(db.String(255), default='دوراتنا')
    courses_section_enabled = db.Column(db.Boolean, default=True)
    
    testimonials_title = db.Column(db.String(255), default='What Our Students Say')
    testimonials_title_ar = db.Column(db.String(255), default='ماذا يقول طلابنا')
    testimonials_content = db.Column(db.Text)  # JSON array of testimonial items
    testimonials_enabled = db.Column(db.Boolean, default=True)
    
    cta_title = db.Column(db.String(255), default='Start Your Learning Journey')
    cta_title_ar = db.Column(db.String(255), default='ابدأ رحلتك التعليمية')
    cta_subtitle = db.Column(db.Text)
    cta_subtitle_ar = db.Column(db.Text)
    cta_button_text = db.Column(db.String(100), default='Get Started')
    cta_button_text_ar = db.Column(db.String(100), default='ابدأ الآن')
    cta_button_url = db.Column(db.String(500))
    
    # Additional branding
    logo_dark_url = db.Column(db.String(500))  # Logo for dark mode
    accent_color = db.Column(db.String(7), default='#4CAF50')  # Accent/highlight color
    header_bg_color = db.Column(db.String(7), default='#1B5E20')  # Header background
    
    # Contact Information
    address = db.Column(db.Text)
    address_ar = db.Column(db.Text)
    phone = db.Column(db.String(50))
    
    # Social Media Links (JSON: {"facebook": "url", "twitter": "url", ...})
    social_links = db.Column(db.Text)  # JSON string
    
    # Hero Section CTA Buttons (JSON array for multiple buttons)
    hero_buttons = db.Column(db.Text)  # JSON: [{"text": "...", "url": "...", "style": "primary"}, ...]
    
    # Custom CSS for advanced styling
    custom_css = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================
# PASSWORD RESET TOKEN
# ============================================

class PasswordResetToken(db.Model):
    """Secure password reset tokens"""
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    token_hash = db.Column(db.String(255), nullable=False)  # SHA-256 hash of token
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)  # NULL if not used
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))  # IP that requested the reset
    
    # Relationship
    user = db.relationship('User', backref=db.backref('reset_tokens', lazy='dynamic'))


# ============================================
# USER MODELS
# ============================================

class User(db.Model):
    """Users - Single institution architecture"""
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)

    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(255))
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    full_name_ar = db.Column(db.String(255))  # Arabic name for bilingual support

    # Role: superadmin, admin, teacher, student
    role = db.Column(db.String(20), default='student')
    is_active = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=True)  # For teachers pending admin approval

    # Profile
    avatar_url = db.Column(db.String(500))
    phone = db.Column(db.String(50))
    bio = db.Column(db.Text)
    language = db.Column(db.String(10), default='en')

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    enrollments = db.relationship('Enrollment', backref='user', lazy='dynamic')
    submissions = db.relationship('AssignmentSubmission', backref='student', lazy='dynamic', foreign_keys='AssignmentSubmission.user_id')
    exam_results = db.relationship('ExamResult', backref='user', lazy='dynamic')
    learning_progress = db.relationship('LearningProgress', backref='user', lazy='dynamic')


# ============================================
# COURSE MODELS (Moodle-like structure)
# ============================================

class Course(db.Model):
    """Courses with weekly structure"""
    __tablename__ = 'courses'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    institution_id = db.Column(db.String(36), nullable=True)  # Optional institution reference

    code = db.Column(db.String(50))
    title = db.Column(db.String(255), nullable=False)
    title_ar = db.Column(db.String(255))  # Arabic title
    description = db.Column(db.Text)
    description_ar = db.Column(db.Text)  # Arabic description
    thumbnail_url = db.Column(db.String(500))

    # Course settings
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    is_published = db.Column(db.Boolean, default=False)
    is_self_paced = db.Column(db.Boolean, default=False)

    # Grading
    passing_threshold = db.Column(db.Float, default=50.0)
    certificate_enabled = db.Column(db.Boolean, default=True)

    # Pricing
    requires_payment = db.Column(db.Boolean, default=False)
    price = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='USD')

    # Meeting/Broadcast Links
    meet_link = db.Column(db.String(500))  # Google Meet link
    zoom_link = db.Column(db.String(500))  # Zoom meeting link
    youtube_broadcast_link = db.Column(db.String(500))  # YouTube livestream/broadcast link

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    instructors = db.relationship('CourseInstructor', backref='course', lazy='dynamic')
    weeks = db.relationship('CourseWeek', backref='course', lazy='dynamic', order_by='CourseWeek.week_number')
    enrollments = db.relationship('Enrollment', backref='course', lazy='dynamic')
    exams = db.relationship('Exam', backref='course', lazy='dynamic')


class CourseInstructor(db.Model):
    """Course instructors (many-to-many)"""
    __tablename__ = 'course_instructors'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), default='instructor')  # instructor, teaching_assistant
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CourseWeek(db.Model):
    """Weekly modules within a course"""
    __tablename__ = 'course_weeks'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    
    week_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # Dates
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    materials = db.relationship('WeekMaterial', backref='week', lazy='dynamic', order_by='WeekMaterial.order_index')
    assignments = db.relationship('Assignment', backref='week', lazy='dynamic')
    
    __table_args__ = (
        db.UniqueConstraint('course_id', 'week_number', name='unique_week_per_course'),
    )


class WeekMaterial(db.Model):
    """Learning materials within a week (videos, documents, links)"""
    __tablename__ = 'week_materials'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    week_id = db.Column(db.String(36), db.ForeignKey('course_weeks.id'), nullable=False)
    
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    material_type = db.Column(db.String(20))  # video, document, link, pdf, audio, image
    
    # Content
    file_url = db.Column(db.String(500))
    external_url = db.Column(db.String(500))
    content_html = db.Column(db.Text)
    
    # File metadata (original name, size, mime type)
    file_name = db.Column(db.String(255))
    file_size = db.Column(db.Integer)  # Size in bytes
    mime_type = db.Column(db.String(100))
    
    # Metadata for personalized learning
    duration_minutes = db.Column(db.Integer)
    difficulty_level = db.Column(db.String(20), default='intermediate')  # beginner, intermediate, advanced
    topics = db.Column(db.JSON, default=list)  # Topic tags for AI matching
    
    order_index = db.Column(db.Integer, default=0)
    is_required = db.Column(db.Boolean, default=True)
    is_published = db.Column(db.Boolean, default=True)
    
    # Visibility/Scheduling for teacher approval workflow
    visibility_state = db.Column(db.String(20), default='draft')  # draft, approved, scheduled
    available_at = db.Column(db.DateTime)  # When scheduled content becomes visible
    approved_at = db.Column(db.DateTime)
    approved_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_material_visibility', 'week_id', 'visibility_state', 'available_at'),
    )


class Assignment(db.Model):
    """Weekly assignments"""
    __tablename__ = 'assignments'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    week_id = db.Column(db.String(36), db.ForeignKey('course_weeks.id'), nullable=False)
    
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    instructions = db.Column(db.Text)
    
    # Assignment type
    assignment_type = db.Column(db.String(20), default='submission')  # submission, quiz, discussion
    
    # Dates
    open_date = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime)
    close_date = db.Column(db.DateTime)
    
    # Grading
    max_points = db.Column(db.Float, default=100.0)
    weight = db.Column(db.Float, default=1.0)  # Contribution to final grade
    allow_late = db.Column(db.Boolean, default=False)
    late_penalty_percent = db.Column(db.Float, default=10.0)
    
    # Submission settings
    max_attempts = db.Column(db.Integer, default=1)
    allowed_file_types = db.Column(db.JSON, default=list)
    
    # Topics for AI matching
    topics = db.Column(db.JSON, default=list)
    
    is_published = db.Column(db.Boolean, default=False)
    
    # Visibility/Scheduling for teacher approval workflow
    visibility_state = db.Column(db.String(20), default='draft')  # draft, approved, scheduled
    available_at = db.Column(db.DateTime)  # When scheduled content becomes visible
    approved_at = db.Column(db.DateTime)
    approved_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    submissions = db.relationship('AssignmentSubmission', backref='assignment', lazy='dynamic')
    
    __table_args__ = (
        db.Index('idx_assignment_visibility', 'week_id', 'visibility_state', 'available_at'),
    )


class AssignmentSubmission(db.Model):
    """Student assignment submissions"""
    __tablename__ = 'assignment_submissions'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    assignment_id = db.Column(db.String(36), db.ForeignKey('assignments.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    # Submission content
    submission_text = db.Column(db.Text)
    file_url = db.Column(db.String(500))
    file_name = db.Column(db.String(255))
    
    # Status
    status = db.Column(db.String(20), default='draft')  # draft, submitted, graded, returned
    attempt_number = db.Column(db.Integer, default=1)
    
    submitted_at = db.Column(db.DateTime)
    
    # Grading
    score = db.Column(db.Float)
    feedback = db.Column(db.Text)
    graded_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    graded_at = db.Column(db.DateTime)
    
    # Late submission tracking
    is_late = db.Column(db.Boolean, default=False)
    late_penalty_applied = db.Column(db.Float, default=0.0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================
# ENROLLMENT MODELS
# ============================================

class Enrollment(db.Model):
    """Student enrollments in courses"""
    __tablename__ = 'enrollments'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    
    status = db.Column(db.String(20), default='pending')  # pending, approved, blocked, completed
    payment_status = db.Column(db.String(20), default='not_required')  # not_required, pending, paid, waived
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Progress tracking
    progress_percent = db.Column(db.Float, default=0.0)
    current_week = db.Column(db.Integer, default=1)
    
    # Final grade
    final_grade = db.Column(db.Float)
    certificate_issued = db.Column(db.Boolean, default=False)
    certificate_issued_at = db.Column(db.DateTime)
    
    # Certificate approval workflow for course completion
    certificate_status = db.Column(db.String(20), default='not_eligible')  # not_eligible, pending, approved, rejected, issued, force_issued
    certificate_approved_by = db.Column(db.String(36))
    certificate_approved_at = db.Column(db.DateTime)
    certificate_url = db.Column(db.String(500))
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'course_id', name='unique_enrollment'),
        db.Index('idx_enrollment_course', 'course_id'),
    )


# ============================================
# EXAM / ASSESSMENT MODELS
# ============================================

class Exam(db.Model):
    """Exams/Quizzes for courses"""
    __tablename__ = 'exams'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    week_id = db.Column(db.String(36), db.ForeignKey('course_weeks.id'), nullable=True)
    
    title = db.Column(db.String(255), nullable=False)
    title_ar = db.Column(db.String(255))  # Arabic title
    description = db.Column(db.Text)
    description_ar = db.Column(db.Text)  # Arabic description
    exam_type = db.Column(db.String(20), default='quiz')  # quiz, midterm, final, entry_survey, exit_exam, exit_survey
    
    # Timing
    open_date = db.Column(db.DateTime)
    close_date = db.Column(db.DateTime)
    time_limit_minutes = db.Column(db.Integer)
    
    # Grading
    passing_threshold = db.Column(db.Float, default=50.0)
    max_attempts = db.Column(db.Integer, default=1)
    
    # Settings
    shuffle_questions = db.Column(db.Boolean, default=False)
    show_results = db.Column(db.Boolean, default=True)
    
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('ExamQuestion', backref='exam', lazy='dynamic', order_by='ExamQuestion.order_index')
    results = db.relationship('ExamResult', backref='exam', lazy='dynamic')


class ExamQuestion(db.Model):
    """Exam questions - bilingual support (Arabic/English)"""
    __tablename__ = 'exam_questions'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    exam_id = db.Column(db.String(36), db.ForeignKey('exams.id'), nullable=False)
    
    # Bilingual question text
    question_text = db.Column(db.Text, nullable=False)  # English (default)
    question_text_ar = db.Column(db.Text)  # Arabic
    
    question_type = db.Column(db.String(20), default='multiple_choice')  # multiple_choice, true_false, short_answer, essay
    
    # Bilingual options
    options = db.Column(db.JSON, default=list)  # English options
    options_ar = db.Column(db.JSON, default=list)  # Arabic options
    
    correct_answer = db.Column(db.String(255))
    correct_answer_ar = db.Column(db.String(255))  # Arabic correct answer text
    points = db.Column(db.Float, default=1.0)
    
    # Metadata for personalized learning
    topic = db.Column(db.String(100))
    topic_ar = db.Column(db.String(100))  # Arabic topic
    difficulty = db.Column(db.String(20), default='medium')  # easy, medium, hard
    
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # For AI-generated questions
    is_ai_generated = db.Column(db.Boolean, default=False)
    source_file = db.Column(db.String(255))  # Original file used for generation


class ExamResult(db.Model):
    """Student exam results"""
    __tablename__ = 'exam_results'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    exam_id = db.Column(db.String(36), db.ForeignKey('exams.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    attempt_number = db.Column(db.Integer, default=1)
    answers = db.Column(db.JSON, default=dict)  # {question_id: answer}
    
    # Results
    score = db.Column(db.Float)
    total_points = db.Column(db.Float)
    percentage = db.Column(db.Float)
    passed = db.Column(db.Boolean)
    
    # Timing
    started_at = db.Column(db.DateTime)
    submitted_at = db.Column(db.DateTime)
    time_spent_seconds = db.Column(db.Integer)
    
    # Certificate
    certificate_generated = db.Column(db.Boolean, default=False)
    certificate_url = db.Column(db.String(500))
    
    # Certificate approval workflow
    certificate_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, issued, force_issued
    certificate_approved_by = db.Column(db.String(36))  # Admin/Teacher who approved
    certificate_approved_at = db.Column(db.DateTime)
    
    # Allow repeat exam
    repeat_allowed = db.Column(db.Boolean, default=False)
    repeat_allowed_by = db.Column(db.String(36))
    repeat_allowed_at = db.Column(db.DateTime)
    max_repeat_attempts = db.Column(db.Integer, default=1)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_exam_result_user', 'user_id'),
    )


# ============================================
# SURVEY MODELS
# ============================================

class Survey(db.Model):
    """Surveys (entry, exit, feedback)"""
    __tablename__ = 'surveys'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=True)

    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    survey_type = db.Column(db.String(20))  # entry_survey, exit_survey, training_feedback

    is_required = db.Column(db.Boolean, default=False)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    questions = db.relationship('SurveyQuestion', backref='survey', lazy='dynamic')
    responses = db.relationship('SurveyResponse', backref='survey', lazy='dynamic')


class SurveyQuestion(db.Model):
    """Survey questions - bilingual support (Arabic/English)"""
    __tablename__ = 'survey_questions'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    survey_id = db.Column(db.String(36), db.ForeignKey('surveys.id'), nullable=False)
    
    # Bilingual question text
    question_text = db.Column(db.Text, nullable=False)  # English (default)
    question_text_ar = db.Column(db.Text)  # Arabic
    
    question_type = db.Column(db.String(20), default='multiple_choice')  # multiple_choice, rating, text, likert, true_false
    
    # Bilingual options
    options = db.Column(db.JSON, default=list)  # English options
    options_ar = db.Column(db.JSON, default=list)  # Arabic options
    
    # Correct answer for scored surveys (index into options array)
    correct_answer = db.Column(db.Integer)  # Index of correct option (0, 1, 2, etc.)
    
    is_required = db.Column(db.Boolean, default=True)
    order_index = db.Column(db.Integer, default=0)
    
    # For AI-generated questions
    is_ai_generated = db.Column(db.Boolean, default=False)
    source_file = db.Column(db.String(255))  # Original file used for generation


class SurveyResponse(db.Model):
    """Student survey responses"""
    __tablename__ = 'survey_responses'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    survey_id = db.Column(db.String(36), db.ForeignKey('surveys.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    answers = db.Column(db.JSON, default=dict)  # {question_id: answer}
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================
# PERSONALIZED LEARNING MODELS
# ============================================

class LearningProgress(db.Model):
    """Track student progress through materials"""
    __tablename__ = 'learning_progress'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    material_id = db.Column(db.String(36), db.ForeignKey('week_materials.id'), nullable=False)
    
    # Progress
    status = db.Column(db.String(20), default='not_started')  # not_started, in_progress, completed
    progress_percent = db.Column(db.Float, default=0.0)
    time_spent_seconds = db.Column(db.Integer, default=0)
    
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'material_id', name='unique_progress'),
    )


class LearningRecommendation(db.Model):
    """AI-generated personalized recommendations"""
    __tablename__ = 'learning_recommendations'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    
    # Recommendation type
    recommendation_type = db.Column(db.String(50))  # review_material, extra_practice, skip_ahead, take_break
    
    # Target content
    target_type = db.Column(db.String(20))  # material, assignment, exam
    target_id = db.Column(db.String(36))
    
    # Recommendation details
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    priority = db.Column(db.Integer, default=5)  # 1-10, higher = more urgent
    
    # AI reasoning
    reason = db.Column(db.Text)
    confidence_score = db.Column(db.Float)
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, viewed, accepted, dismissed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    viewed_at = db.Column(db.DateTime)


class StudentPerformanceSnapshot(db.Model):
    """Aggregated student performance metrics for AI analysis"""
    __tablename__ = 'student_performance_snapshots'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    week_number = db.Column(db.Integer)
    
    # Performance metrics
    average_assignment_score = db.Column(db.Float)
    average_exam_score = db.Column(db.Float)
    materials_completed_percent = db.Column(db.Float)
    engagement_score = db.Column(db.Float)  # Based on time spent, interactions
    
    # Strengths and weaknesses by topic
    strong_topics = db.Column(db.JSON, default=list)
    weak_topics = db.Column(db.JSON, default=list)
    
    # Learning patterns
    preferred_material_types = db.Column(db.JSON, default=list)
    optimal_study_times = db.Column(db.JSON, default=list)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_snapshot_user_course', 'user_id', 'course_id'),
    )


# ============================================
# PROMPT LIBRARY MODELS
# ============================================

class PromptCategory(db.Model):
    """Prompt library categories"""
    __tablename__ = 'prompt_categories'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)

    name = db.Column(db.String(100), nullable=False)
    name_ar = db.Column(db.String(100))  # Arabic translation
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))
    order_index = db.Column(db.Integer, default=0)

    prompts = db.relationship('Prompt', backref='category', lazy='dynamic')


class Prompt(db.Model):
    """Prompt library prompts"""
    __tablename__ = 'prompts'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    category_id = db.Column(db.String(36), db.ForeignKey('prompt_categories.id'), nullable=False)

    title = db.Column(db.String(255), nullable=False)
    title_ar = db.Column(db.String(255))
    content = db.Column(db.Text, nullable=False)
    content_ar = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================
# AUDIT / ACTIVITY LOGGING
# ============================================

class AuditLog(db.Model):
    """System audit log for compliance"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)

    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.String(36))

    old_values = db.Column(db.JSON)
    new_values = db.Column(db.JSON)

    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_audit_user', 'user_id'),
        db.Index('idx_audit_created', 'created_at'),
    )


# ============================================
# REGISTRATION REQUEST MODEL
# ============================================

class RegistrationRequest(db.Model):
    """Pending registration requests for teachers and students"""
    __tablename__ = 'registration_requests'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)

    # User info (before account creation)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50))

    # Role requested: teacher, student
    requested_role = db.Column(db.String(20), nullable=False)

    # For teachers - course(s) they want to teach
    requested_courses = db.Column(db.JSON, default=list)  # List of course IDs

    # For students - course(s) they want to enroll in
    selected_courses = db.Column(db.JSON, default=list)  # List of course IDs

    # Status: pending, approved, rejected
    status = db.Column(db.String(20), default='pending')
    rejection_reason = db.Column(db.Text)

    # Processing info
    reviewed_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_registration_status', 'status'),
    )


class CoursePayment(db.Model):
    """Track course payment transactions"""
    __tablename__ = 'course_payments'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    enrollment_id = db.Column(db.String(36), db.ForeignKey('enrollments.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    
    # Payment details
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    
    # PayPal transaction info
    paypal_order_id = db.Column(db.String(100))
    paypal_capture_id = db.Column(db.String(100))
    paypal_payer_email = db.Column(db.String(255))
    
    # Status: pending, paid, failed, refunded, waived
    status = db.Column(db.String(20), default='pending')
    
    # For manual approval
    approved_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    enrollment = db.relationship('Enrollment', backref=db.backref('payment', uselist=False))
    user = db.relationship('User', foreign_keys=[user_id], backref='course_payments')
    course = db.relationship('Course', backref='payments')
    
    __table_args__ = (
        db.Index('idx_payment_user', 'user_id'),
        db.Index('idx_payment_status', 'status'),
    )


# ============================================
# TEACHER-STUDENT MESSAGING
# ============================================

class TeacherStudentMessage(db.Model):
    """Messages between teachers and students"""
    __tablename__ = 'teacher_student_messages'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    
    # Participants
    teacher_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    student_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    sender_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    # Message content
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')  # text, file, ai_report
    file_url = db.Column(db.String(500))
    
    # Status
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course', backref='messages')
    teacher = db.relationship('User', foreign_keys=[teacher_id], backref='sent_teacher_messages')
    student = db.relationship('User', foreign_keys=[student_id], backref='received_student_messages')
    sender = db.relationship('User', foreign_keys=[sender_id])
    
    __table_args__ = (
        db.Index('idx_message_course', 'course_id'),
        db.Index('idx_message_teacher_student', 'teacher_id', 'student_id'),
    )


# ============================================
# ATTENDANCE TRACKING MODELS
# ============================================

class Attendance(db.Model):
    """Daily attendance tracking per class/course"""
    __tablename__ = 'attendance'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    # Attendance date
    attendance_date = db.Column(db.Date, nullable=False)
    
    # Status: present, absent, late, excused
    status = db.Column(db.String(20), default='present')
    
    # Optional notes
    notes = db.Column(db.Text)
    notes_ar = db.Column(db.Text)  # Arabic notes
    
    # Who recorded it
    recorded_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course', backref='attendance_records')
    student = db.relationship('User', foreign_keys=[user_id], backref='attendance')
    recorder = db.relationship('User', foreign_keys=[recorded_by])
    
    __table_args__ = (
        db.UniqueConstraint('course_id', 'user_id', 'attendance_date', name='unique_daily_attendance'),
        db.Index('idx_attendance_course_date', 'course_id', 'attendance_date'),
    )


class AIPerformanceReport(db.Model):
    """AI-generated student performance reports"""
    __tablename__ = 'ai_performance_reports'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    student_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    generated_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    # Report content
    performance_summary = db.Column(db.Text)
    strengths = db.Column(db.JSON, default=list)
    areas_for_improvement = db.Column(db.JSON, default=list)
    recommended_actions = db.Column(db.JSON, default=list)
    suggested_learning_methods = db.Column(db.JSON, default=list)
    extra_assignments_suggested = db.Column(db.JSON, default=list)
    
    # Metrics at time of report
    current_progress = db.Column(db.Float)
    average_score = db.Column(db.Float)
    assignments_completed = db.Column(db.Integer)
    materials_completed = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student = db.relationship('User', foreign_keys=[student_id], backref='performance_reports')
    course = db.relationship('Course', backref='performance_reports')
    generator = db.relationship('User', foreign_keys=[generated_by])


# ============================================
# API CREDENTIALS (Encrypted Storage)
# ============================================

class ApiCredential(db.Model):
    """Encrypted API credentials for AI providers"""
    __tablename__ = 'api_credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), unique=True, nullable=False)  # e.g., 'openai', 'claude', 'gemini'
    encrypted_key = db.Column(db.Text)  # Fernet-encrypted API key
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Supported providers with their display names and env var names
    PROVIDERS = {
        'openai': {'name': 'OpenAI', 'env_var': 'OPENAI_API_KEY', 'description': 'GPT-4, DALL-E'},
        'claude': {'name': 'Anthropic Claude', 'env_var': 'CLAUDE_API_KEY', 'description': 'Claude AI'},
        'gemini': {'name': 'Google Gemini', 'env_var': 'GEMINI_API_KEY', 'description': 'Gemini AI'},
        'perplexity': {'name': 'Perplexity', 'env_var': 'PERPLEXITY_API_KEY', 'description': 'Research AI'},
        'grok': {'name': 'xAI Grok', 'env_var': 'GROK_API_KEY', 'description': 'Grok AI'},
        'deepseek': {'name': 'DeepSeek', 'env_var': 'DEEPSEEK_API_KEY', 'description': 'DeepSeek AI'},
    }
    
    def __repr__(self):
        return f'<ApiCredential {self.provider}>'
