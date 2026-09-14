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

    # Feature Toggles
    attendance_tracking_enabled = db.Column(db.Boolean, default=True)
    
    # App Freeze/Maintenance Mode
    app_frozen = db.Column(db.Boolean, default=False)
    freeze_message = db.Column(db.Text, default='The platform is currently under maintenance. Please try again later.')
    freeze_message_ar = db.Column(db.Text, default='المنصة حالياً تحت الصيانة. يرجى المحاولة لاحقاً.')
    frozen_at = db.Column(db.DateTime)
    frozen_by = db.Column(db.String(100))

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
# ISSUED CERTIFICATE (verification registry)
# ============================================

class IssuedCertificate(db.Model):
    """Lightweight verification record for every certificate generated by
    the bulk endpoints — works for BOTH class-mode (linked to an
    Enrollment) and no-class-mode (CSV-only) certificates.

    The QR code on the certificate points to /verify/<cert_number>, and
    that route looks the row up here.
    """
    __tablename__ = 'issued_certificates'

    cert_number   = db.Column(db.String(40), primary_key=True)
    student_name  = db.Column(db.String(255), nullable=False)
    course_title  = db.Column(db.String(255))
    issued_at     = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    final_grade   = db.Column(db.Float)
    language      = db.Column(db.String(8), default='en')
    enrollment_id = db.Column(db.String(36))  # nullable: empty for no-class certs
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)


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

    # Personal recognition (used by EthicalSense and other personalization features)
    job_title = db.Column(db.String(150))
    profession = db.Column(db.String(150))
    organization = db.Column(db.String(200))
    country = db.Column(db.String(100))
    region = db.Column(db.String(100))
    gender = db.Column(db.String(30))
    education_level = db.Column(db.String(80))
    date_of_birth = db.Column(db.Date)

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

    # Registration control
    registration_open = db.Column(db.Boolean, default=True)  # Admin can close registration per-course

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

    # Per-question rubric for short_answer/essay grading. List of
    # {name, name_ar, max, description, description_ar}. When NULL the
    # default rubric in app.services.assessment_service is used.
    rubric = db.Column(db.JSON)

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

    # Anti-cheating / proctoring (browser-side signals recorded during the attempt)
    proctoring_events = db.Column(db.JSON)  # [{type, at, detail}] capped list
    violation_count = db.Column(db.Integer, default=0)
    
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


class EnrollmentMonthlyRubric(db.Model):
    """
    Per-(enrollment, month) editable rubric used by the Batch Monthly Report.

    Holds the 10 performance scores (1-4) that aren't auto-tracked anywhere
    else, plus an editable warning-letters count, an optional final-grade
    override, and free-text notes. The report-export endpoint upserts a row
    here whenever the admin saves the editable preview, so subsequent
    exports for the same month start with the previous edits.
    """
    __tablename__ = 'enrollment_monthly_rubrics'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    enrollment_id = db.Column(db.String(36), db.ForeignKey('enrollments.id'), nullable=False)
    period_start = db.Column(db.Date, nullable=False)  # first day of the month

    # JSON map: {criterion_key: 1..4}. Keys match BATCH_REPORT_PERFORMANCE_CRITERIA.
    performance_scores = db.Column(db.JSON, default=dict)

    warning_letters = db.Column(db.Integer, default=0)
    final_grade_override = db.Column(db.Float)  # null = use computed
    notes = db.Column(db.Text)

    updated_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('enrollment_id', 'period_start', name='unique_rubric_per_month'),
        db.Index('idx_rubric_period', 'period_start'),
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
    # Descriptions deliberately name model families rather than specific
    # versions: the version list lives in app/services/model_registry.py and
    # changes far more often than this table.
    PROVIDERS = {
        'openai': {'name': 'OpenAI', 'env_var': 'OPENAI_API_KEY', 'description': 'GPT chat and image models'},
        'claude': {'name': 'Anthropic Claude', 'env_var': 'CLAUDE_API_KEY', 'description': 'Claude Opus / Sonnet / Haiku'},
        'gemini': {'name': 'Google Gemini', 'env_var': 'GEMINI_API_KEY', 'description': 'Gemini Pro / Flash'},
        'perplexity': {'name': 'Perplexity', 'env_var': 'PERPLEXITY_API_KEY', 'description': 'Sonar, answers grounded in live search'},
        'grok': {'name': 'xAI Grok', 'env_var': 'GROK_API_KEY', 'description': 'Grok chat models'},
        'deepseek': {'name': 'DeepSeek', 'env_var': 'DEEPSEEK_API_KEY', 'description': 'DeepSeek chat and reasoning models'},
        # Image generation is billed against the OpenAI key.
        'images': {'name': 'Image generation', 'env_var': 'OPENAI_API_KEY', 'description': 'GPT Image (replaces DALL-E)'},
        'heygen': {'name': 'HeyGen', 'env_var': 'HEYGEN_API_KEY', 'description': 'AI avatar video generation'},
        'bedrock': {'name': 'AWS Bedrock', 'env_var': 'BEDROCK_API_KEY', 'description': 'Claude and open models on AWS (format: access_key|secret_key|region)'},
        'paypal': {'name': 'PayPal', 'env_var': 'PAYPAL_CLIENT_ID', 'description': 'Payments (format: client_id|client_secret|mode[sandbox|live])'},
    }
    
    def __repr__(self):
        return f'<ApiCredential {self.provider}>'


# ============================================
# PHASE 1 — PERSONALIZATION & ETHICSENSE MODELS
# (additive; never modifies existing models)
# ============================================

class LearnerProfile(db.Model):
    """
    Per-user personalization profile.
    Captures goals, preferences, accessibility needs, and
    aggregated signals used by the adaptive engine and
    recommended learning paths.
    """
    __tablename__ = 'learner_profiles'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, unique=True)

    # Goals and interests (free-form + structured)
    primary_goal = db.Column(db.String(255))           # e.g. "Become a data analyst"
    primary_goal_ar = db.Column(db.String(255))
    target_role = db.Column(db.String(255))            # SkillMatch-aligned occupation code
    interests = db.Column(db.JSON, default=list)       # list[str] tags

    # Preferences
    preferred_language = db.Column(db.String(8), default='en')         # 'en' | 'ar'
    preferred_difficulty = db.Column(db.String(20), default='adaptive')# beginner|intermediate|advanced|adaptive
    preferred_modalities = db.Column(db.JSON, default=list)            # ['video','reading','interactive','avatar']
    daily_study_minutes = db.Column(db.Integer, default=30)
    timezone = db.Column(db.String(64))

    # Accessibility (Phase 8 will surface these in UI)
    high_contrast = db.Column(db.Boolean, default=False)
    dyslexia_mode = db.Column(db.Boolean, default=False)
    text_to_speech = db.Column(db.Boolean, default=False)
    reduce_motion = db.Column(db.Boolean, default=False)
    font_scale = db.Column(db.Float, default=1.0)

    # Engagement signals (rolled up by adaptive engine)
    engagement_score = db.Column(db.Float, default=0.0)        # 0-100
    streak_days = db.Column(db.Integer, default=0)
    last_active_at = db.Column(db.DateTime)

    # EthicSense linkage (denormalized snapshot)
    ethics_overall_score = db.Column(db.Float)                 # 0-100
    ethics_last_assessed_at = db.Column(db.DateTime)

    # Onboarding status
    onboarding_completed = db.Column(db.Boolean, default=False)
    onboarded_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('learner_profile', uselist=False))


class Skill(db.Model):
    """
    Canonical skill in the platform skill graph.
    Used by SkillMatch (Phase 7) and adaptive recommendations.
    """
    __tablename__ = 'skills'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    code = db.Column(db.String(64), unique=True, nullable=False)  # stable slug, e.g. 'python.basics'
    name = db.Column(db.String(120), nullable=False)
    name_ar = db.Column(db.String(120))
    description = db.Column(db.Text)
    description_ar = db.Column(db.Text)

    # Taxonomy
    category = db.Column(db.String(64))         # e.g. 'data', 'language', 'soft_skills'
    domain = db.Column(db.String(64))           # broader grouping
    parent_skill_id = db.Column(db.String(36), db.ForeignKey('skills.id'))
    level_max = db.Column(db.Integer, default=5)

    # External alignment (optional)
    esco_code = db.Column(db.String(32))        # European Skills/Competences/Qualifications/Occupations
    onet_code = db.Column(db.String(32))        # O*NET reference

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    children = db.relationship('Skill', backref=db.backref('parent', remote_side=[id]))

    __table_args__ = (
        db.Index('idx_skill_code', 'code'),
        db.Index('idx_skill_category', 'category'),
    )


class LearnerSkill(db.Model):
    """Per-user mastery level for a skill (0..level_max)."""
    __tablename__ = 'learner_skills'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    skill_id = db.Column(db.String(36), db.ForeignKey('skills.id'), nullable=False)

    level = db.Column(db.Integer, default=0)            # current mastery 0..level_max
    confidence = db.Column(db.Float, default=0.0)       # 0..1 (model confidence)
    target_level = db.Column(db.Integer)                # learner's stated target
    evidence_count = db.Column(db.Integer, default=0)   # # of evidence items contributing
    source = db.Column(db.String(32), default='system') # system|self|teacher|exam
    last_evidence_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    skill = db.relationship('Skill')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'skill_id', name='unique_learner_skill'),
        db.Index('idx_learner_skill_user', 'user_id'),
    )


class LearnerSkillHistory(db.Model):
    """Append-only audit of LearnerSkill level changes.

    Written by AdaptiveEngine.recompute_skill_levels() whenever a learner's
    mastery level for a skill changes (or is first observed). Powers the
    learner-facing "Adaptive progress" widget that shows skills the learner
    grew after each tutor session / material completion.
    """
    __tablename__ = 'learner_skill_history'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    skill_id = db.Column(db.String(36), db.ForeignKey('skills.id'), nullable=False)

    previous_level = db.Column(db.Integer, default=0)
    new_level = db.Column(db.Integer, default=0)
    level_max = db.Column(db.Integer, default=5)
    confidence = db.Column(db.Float, default=0.0)
    source = db.Column(db.String(32), default='adaptive')  # adaptive|tutor|material|manual
    course_id = db.Column(db.String(36))                   # optional context

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    skill = db.relationship('Skill')

    __table_args__ = (
        db.Index('idx_learner_skill_history_user', 'user_id', 'created_at'),
    )


class LearningPath(db.Model):
    """
    A personalized sequence of steps (courses / materials / assessments)
    generated for a learner toward a goal. Drives the recommended-path
    UI and the adaptive engine in Phase 2.
    """
    __tablename__ = 'learning_paths'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)

    title = db.Column(db.String(255), nullable=False)
    title_ar = db.Column(db.String(255))
    description = db.Column(db.Text)
    description_ar = db.Column(db.Text)

    goal = db.Column(db.String(255))                # human-readable target
    target_skill_codes = db.Column(db.JSON, default=list)   # list[str]
    estimated_minutes = db.Column(db.Integer)
    difficulty = db.Column(db.String(20), default='adaptive')

    # Status: draft|active|paused|completed|archived
    status = db.Column(db.String(20), default='active')
    progress_percent = db.Column(db.Float, default=0.0)

    # Provenance
    generated_by = db.Column(db.String(32), default='system')   # system|teacher|ai
    # Exact model identifier as sent to the provider, for audit. Resolve it
    # through app.services.model_registry before reusing it: the model may
    # have been retired since the row was written.
    generator_model = db.Column(db.String(64))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    steps = db.relationship('PathStep', backref='path', lazy='dynamic',
                            cascade='all, delete-orphan',
                            order_by='PathStep.order_index')

    __table_args__ = (
        db.Index('idx_path_user_status', 'user_id', 'status'),
    )


class PathStep(db.Model):
    """A single step within a LearningPath."""
    __tablename__ = 'path_steps'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    path_id = db.Column(db.String(36), db.ForeignKey('learning_paths.id'), nullable=False)

    order_index = db.Column(db.Integer, default=0)
    step_type = db.Column(db.String(32), nullable=False)
    # course | material | exam | survey | external | reflection | ethics_scenario

    target_id = db.Column(db.String(36))            # FK to course/material/exam (loose)
    title = db.Column(db.String(255))
    title_ar = db.Column(db.String(255))
    estimated_minutes = db.Column(db.Integer)

    # Adaptive metadata
    primary_skill_code = db.Column(db.String(64))
    rationale = db.Column(db.Text)                  # why this was recommended

    # Status: pending|in_progress|completed|skipped
    status = db.Column(db.String(20), default='pending')
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    __table_args__ = (
        db.Index('idx_path_step_path', 'path_id', 'order_index'),
    )


# ----- EthicSense -----------------------------------------------------------

class EthicsCompetency(db.Model):
    """
    Catalog of ethical competencies tracked by EthicSense.
    Examples: 'academic_integrity', 'data_privacy', 'ai_responsible_use',
    'inclusive_communication', 'professional_conduct'.
    """
    __tablename__ = 'ethics_competencies'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    code = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    name_ar = db.Column(db.String(120))
    description = db.Column(db.Text)
    description_ar = db.Column(db.Text)

    # Pillar grouping (e.g. 'integrity', 'responsibility', 'fairness')
    pillar = db.Column(db.String(40))
    weight = db.Column(db.Float, default=1.0)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LearnerEthicsProfile(db.Model):
    """
    Per-user EthicSense scoring snapshot, refreshed by ethics
    assessments, scenario responses and behavioral signals.
    """
    __tablename__ = 'learner_ethics_profiles'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    competency_id = db.Column(db.String(36), db.ForeignKey('ethics_competencies.id'), nullable=False)

    score = db.Column(db.Float, default=0.0)               # 0-100
    confidence = db.Column(db.Float, default=0.0)          # 0-1
    evidence_count = db.Column(db.Integer, default=0)
    last_assessment_id = db.Column(db.String(36))          # FK-ish to ethics session
    last_signal = db.Column(db.String(40))                 # e.g. 'scenario','quiz','peer_review'

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    competency = db.relationship('EthicsCompetency')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'competency_id', name='unique_learner_ethics_competency'),
        db.Index('idx_learner_ethics_user', 'user_id'),
    )


# ============================================
# v2 PHASES 4–8 — Authoring, Social, Analytics,
# SkillMatch, Enterprise & Accessibility
# All additive; no existing model is altered.
# ============================================

# ----- Phase 4: AI authoring + SCORM/xAPI ----------------------------------

class AuthoringDraft(db.Model):
    """AI authoring wizard draft for a course/lesson plan."""
    __tablename__ = 'authoring_drafts'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    author_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'))

    title = db.Column(db.String(255), nullable=False)
    title_ar = db.Column(db.String(255))
    topic = db.Column(db.Text)
    language = db.Column(db.String(8), default='en')      # en|ar
    target_audience = db.Column(db.String(120))
    learning_outcomes = db.Column(db.JSON, default=list)
    weeks = db.Column(db.JSON, default=list)              # [{title, materials, exam, survey}]
    ethics_tags = db.Column(db.JSON, default=list)        # list[ethics competency codes]

    # Quality + provenance
    quality_score = db.Column(db.Float)                    # 0..100, AI-computed
    quality_breakdown = db.Column(db.JSON)
    generator_model = db.Column(db.String(64))
    status = db.Column(db.String(20), default='draft')     # draft|review|published|archived
    published_at = db.Column(db.DateTime)
    published_course_id = db.Column(db.String(36))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_authoring_author_status', 'author_id', 'status'),
    )


class ContentVersion(db.Model):
    """Versioned snapshot of a piece of content with restore support."""
    __tablename__ = 'content_versions'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    content_type = db.Column(db.String(32), nullable=False)   # course|material|exam|survey|draft
    content_id = db.Column(db.String(36), nullable=False)
    version_number = db.Column(db.Integer, default=1)
    snapshot = db.Column(db.JSON, nullable=False)             # full payload
    change_note = db.Column(db.String(500))
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_content_version_target', 'content_type', 'content_id', 'version_number'),
    )


class ScormPackage(db.Model):
    """Imported / exported SCORM 1.2 or 2004 package metadata."""
    __tablename__ = 'scorm_packages'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'))
    package_name = db.Column(db.String(255), nullable=False)
    scorm_version = db.Column(db.String(16), default='2004')   # '1.2'|'2004'
    direction = db.Column(db.String(8), default='import')      # import|export
    storage_path = db.Column(db.String(500))
    manifest = db.Column(db.JSON)
    size_bytes = db.Column(db.Integer)
    status = db.Column(db.String(20), default='ready')         # processing|ready|failed
    error_message = db.Column(db.Text)
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class XApiStatement(db.Model):
    """Outbound xAPI statement record (LRS-bound)."""
    __tablename__ = 'xapi_statements'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    actor_user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    verb = db.Column(db.String(120), nullable=False)           # e.g. http://adlnet.gov/expapi/verbs/completed
    object_type = db.Column(db.String(32))                     # course|lesson|exam|...
    object_id = db.Column(db.String(36))
    object_name = db.Column(db.String(255))
    result = db.Column(db.JSON)                                # score, success, completion
    context = db.Column(db.JSON)
    statement = db.Column(db.JSON, nullable=False)             # full xAPI statement
    lrs_endpoint = db.Column(db.String(500))
    delivery_status = db.Column(db.String(20), default='pending')  # pending|sent|failed
    delivery_error = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime)

    __table_args__ = (
        db.Index('idx_xapi_actor_verb', 'actor_user_id', 'verb'),
    )


# ----- Phase 5: Engagement, social, parent portal, live ---------------------

class Badge(db.Model):
    """Catalog badge that can be earned by learners."""
    __tablename__ = 'badges'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    code = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    name_ar = db.Column(db.String(120))
    description = db.Column(db.Text)
    description_ar = db.Column(db.Text)
    icon_url = db.Column(db.String(500))
    category = db.Column(db.String(40))                # learning|ethics|community|streak
    xp_reward = db.Column(db.Integer, default=0)
    criteria = db.Column(db.JSON)                      # rule object (declarative)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserBadge(db.Model):
    __tablename__ = 'user_badges'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    badge_id = db.Column(db.String(36), db.ForeignKey('badges.id'), nullable=False)
    awarded_at = db.Column(db.DateTime, default=datetime.utcnow)
    awarded_for = db.Column(db.String(255))            # short reason / event id

    badge = db.relationship('Badge')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'badge_id', name='unique_user_badge'),
        db.Index('idx_user_badge_user', 'user_id'),
    )


class XPEvent(db.Model):
    """Append-only XP ledger. Used to compute totals and leaderboards."""
    __tablename__ = 'xp_events'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Integer, default=0)
    source = db.Column(db.String(40))                  # exam|lesson|forum|peer_review|streak|badge
    source_id = db.Column(db.String(36))
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.Index('idx_xp_user_created', 'user_id', 'created_at'),)


class ForumThread(db.Model):
    __tablename__ = 'forum_threads'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'))
    cohort_id = db.Column(db.String(36))
    author_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text)
    language = db.Column(db.String(8), default='en')
    pinned = db.Column(db.Boolean, default=False)
    locked = db.Column(db.Boolean, default=False)
    post_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ForumPost(db.Model):
    __tablename__ = 'forum_posts'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    thread_id = db.Column(db.String(36), db.ForeignKey('forum_threads.id'), nullable=False)
    author_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    parent_post_id = db.Column(db.String(36), db.ForeignKey('forum_posts.id'))
    sentiment = db.Column(db.String(16))           # positive|neutral|negative (Phase 6)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.Index('idx_forum_post_thread', 'thread_id', 'created_at'),)


class PeerReview(db.Model):
    """Peer review on an AssignmentSubmission."""
    __tablename__ = 'peer_reviews'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    submission_id = db.Column(db.String(36), db.ForeignKey('assignment_submissions.id'), nullable=False)
    reviewer_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    rubric_scores = db.Column(db.JSON)             # {criterion_code: score}
    comment = db.Column(db.Text)
    overall_score = db.Column(db.Float)
    status = db.Column(db.String(20), default='pending')   # pending|completed|flagged
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)


class Cohort(db.Model):
    __tablename__ = 'cohorts'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'))
    name = db.Column(db.String(255), nullable=False)
    name_ar = db.Column(db.String(255))
    starts_on = db.Column(db.Date)
    ends_on = db.Column(db.Date)
    capacity = db.Column(db.Integer)
    instructor_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CohortMember(db.Model):
    __tablename__ = 'cohort_members'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    cohort_id = db.Column(db.String(36), db.ForeignKey('cohorts.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('cohort_id', 'user_id', name='unique_cohort_member'),)


class GuardianLink(db.Model):
    """Links a parent/guardian user to a learner with consent + scope."""
    __tablename__ = 'guardian_links'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    guardian_user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    learner_user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    relationship = db.Column(db.String(40))                  # parent|guardian|other
    status = db.Column(db.String(20), default='pending')     # pending|active|revoked
    consent_token = db.Column(db.String(64))
    consent_granted_at = db.Column(db.DateTime)
    can_view_grades = db.Column(db.Boolean, default=True)
    can_view_attendance = db.Column(db.Boolean, default=True)
    can_view_ethics = db.Column(db.Boolean, default=True)
    can_message_instructor = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (
        db.UniqueConstraint('guardian_user_id', 'learner_user_id', name='unique_guardian_learner'),
    )


class LiveSession(db.Model):
    """Scheduled live virtual classroom (Zoom/Teams/Meet/Jitsi)."""
    __tablename__ = 'live_sessions'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'))
    cohort_id = db.Column(db.String(36), db.ForeignKey('cohorts.id'))
    instructor_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)

    title = db.Column(db.String(255), nullable=False)
    title_ar = db.Column(db.String(255))
    provider = db.Column(db.String(20), default='jitsi')     # zoom|teams|meet|jitsi
    join_url = db.Column(db.String(1000))
    host_url = db.Column(db.String(1000))
    embed_url = db.Column(db.String(1000))                   # iframe-safe URL
    starts_at = db.Column(db.DateTime, nullable=False)
    ends_at = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer)
    status = db.Column(db.String(20), default='scheduled')   # scheduled|live|ended|cancelled
    recording_url = db.Column(db.String(1000))
    attached_lesson_id = db.Column(db.String(36))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.Index('idx_live_session_course_start', 'course_id', 'starts_at'),)


class LiveAttendance(db.Model):
    __tablename__ = 'live_attendance'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    session_id = db.Column(db.String(36), db.ForeignKey('live_sessions.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    left_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer, default=0)
    source = db.Column(db.String(20), default='auto')        # auto|manual|provider
    __table_args__ = (db.UniqueConstraint('session_id', 'user_id', name='unique_live_attendance'),)


# ----- Phase 6: Analytics, sentiment, at-risk alerts ------------------------

class CohortAnalyticsSnapshot(db.Model):
    """Periodic rollup of cohort/course analytics."""
    __tablename__ = 'cohort_analytics_snapshots'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'))
    cohort_id = db.Column(db.String(36), db.ForeignKey('cohorts.id'))
    captured_at = db.Column(db.DateTime, default=datetime.utcnow)
    learner_count = db.Column(db.Integer, default=0)
    active_learner_count = db.Column(db.Integer, default=0)
    avg_progress_percent = db.Column(db.Float, default=0.0)
    avg_exam_score = db.Column(db.Float)
    completion_rate = db.Column(db.Float)
    avg_engagement_score = db.Column(db.Float)
    avg_sentiment = db.Column(db.Float)
    at_risk_count = db.Column(db.Integer, default=0)
    item_analytics = db.Column(db.JSON)             # per-question difficulty/discrimination
    heatmap = db.Column(db.JSON)                    # week x metric grid


class SentimentSignal(db.Model):
    """A single sentiment observation derived from text."""
    __tablename__ = 'sentiment_signals'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    source = db.Column(db.String(40), nullable=False)       # chat|forum|survey|feedback
    source_id = db.Column(db.String(36))
    text_excerpt = db.Column(db.Text)
    sentiment_label = db.Column(db.String(16))              # positive|neutral|negative
    sentiment_score = db.Column(db.Float)                   # -1..1
    detected_emotions = db.Column(db.JSON)                  # ["frustration","confidence"]
    language = db.Column(db.String(8), default='en')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.Index('idx_sentiment_user_created', 'user_id', 'created_at'),)


class AtRiskAlert(db.Model):
    __tablename__ = 'at_risk_alerts'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'))
    cohort_id = db.Column(db.String(36), db.ForeignKey('cohorts.id'))
    risk_score = db.Column(db.Float, default=0.0)           # 0..100
    risk_level = db.Column(db.String(16), default='low')    # low|medium|high|critical
    factors = db.Column(db.JSON)                            # [{factor, weight, value}]
    recommended_actions = db.Column(db.JSON)
    status = db.Column(db.String(20), default='open')       # open|acknowledged|resolved|dismissed
    acknowledged_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    acknowledged_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.Index('idx_atrisk_user_status', 'user_id', 'status'),)


# ----- Phase 7: SkillMatch + Teacher PD -------------------------------------

class Occupation(db.Model):
    """Occupation in SkillMatch (ESCO/O*NET aligned)."""
    __tablename__ = 'occupations'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    code = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    name_ar = db.Column(db.String(255))
    description = db.Column(db.Text)
    description_ar = db.Column(db.Text)
    sector = db.Column(db.String(80))
    esco_code = db.Column(db.String(32))
    onet_code = db.Column(db.String(32))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class OccupationSkill(db.Model):
    """Skill required for an occupation, with weight and target level."""
    __tablename__ = 'occupation_skills'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    occupation_id = db.Column(db.String(36), db.ForeignKey('occupations.id'), nullable=False)
    skill_id = db.Column(db.String(36), db.ForeignKey('skills.id'), nullable=False)
    target_level = db.Column(db.Integer, default=3)
    importance = db.Column(db.Float, default=1.0)           # 0..1 weight
    is_essential = db.Column(db.Boolean, default=True)
    __table_args__ = (
        db.UniqueConstraint('occupation_id', 'skill_id', name='unique_occupation_skill'),
    )


class LabourMarketSignal(db.Model):
    """Latest labour-market data point for an occupation/sector/region."""
    __tablename__ = 'labour_market_signals'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    occupation_id = db.Column(db.String(36), db.ForeignKey('occupations.id'))
    sector = db.Column(db.String(80))
    region = db.Column(db.String(80), default='OM')         # ISO country / region code
    source = db.Column(db.String(64))                       # 'oman_mol'|'ncsi'|'job_portal'|...
    period = db.Column(db.String(16))                       # 'Q1-2026', '2026'
    open_postings = db.Column(db.Integer)
    median_salary = db.Column(db.Float)
    growth_rate_5yr = db.Column(db.Float)
    growth_rate_10yr = db.Column(db.Float)
    demand_index = db.Column(db.Float)                      # 0..100
    raw_payload = db.Column(db.JSON)
    captured_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.Index('idx_lm_occupation_period', 'occupation_id', 'period'),)


class TeacherPDTrack(db.Model):
    """Credentialed Professional Development track for educators."""
    __tablename__ = 'teacher_pd_tracks'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    code = db.Column(db.String(64), unique=True, nullable=False)   # e.g. 'pd.ai_literacy'
    name = db.Column(db.String(255), nullable=False)
    name_ar = db.Column(db.String(255))
    description = db.Column(db.Text)
    description_ar = db.Column(db.Text)
    track_type = db.Column(db.String(40))                  # ai_literacy|pedagogy|ethicsense_trainer
    estimated_hours = db.Column(db.Integer)
    credential_name = db.Column(db.String(120))
    is_trainer_of_trainers = db.Column(db.Boolean, default=False)
    syllabus = db.Column(db.JSON)                          # [{module, hours, outcomes}]
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TeacherPDEnrollment(db.Model):
    __tablename__ = 'teacher_pd_enrollments'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    track_id = db.Column(db.String(36), db.ForeignKey('teacher_pd_tracks.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='enrolled')   # enrolled|in_progress|completed|certified
    progress_percent = db.Column(db.Float, default=0.0)
    final_score = db.Column(db.Float)
    certificate_id = db.Column(db.String(36))
    certificate_url = db.Column(db.String(500))
    issued_at = db.Column(db.DateTime)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    __table_args__ = (
        db.UniqueConstraint('track_id', 'user_id', name='unique_pd_enrollment'),
    )


# ----- Phase 8: Enterprise, compliance, accessibility, public API -----------

class Organization(db.Model):
    """Multi-tenant organization (additive; default org used for legacy data)."""
    __tablename__ = 'organizations'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    code = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    name_ar = db.Column(db.String(255))
    domain = db.Column(db.String(255))
    region = db.Column(db.String(40), default='OM')
    data_residency = db.Column(db.String(40), default='OM')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class OrganizationMember(db.Model):
    __tablename__ = 'organization_members'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    org_role = db.Column(db.String(40), default='member')   # owner|admin|member
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('organization_id', 'user_id', name='unique_org_member'),)


class SsoConfiguration(db.Model):
    """SAML 2.0 / OIDC configuration per organization."""
    __tablename__ = 'sso_configurations'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False)
    protocol = db.Column(db.String(16), nullable=False)     # saml|oidc
    display_name = db.Column(db.String(120))
    enabled = db.Column(db.Boolean, default=False)

    # SAML
    saml_entity_id = db.Column(db.String(255))
    saml_sso_url = db.Column(db.String(500))
    saml_x509_cert = db.Column(db.Text)
    saml_attribute_map = db.Column(db.JSON)

    # OIDC
    oidc_issuer = db.Column(db.String(500))
    oidc_client_id = db.Column(db.String(255))
    oidc_client_secret_encrypted = db.Column(db.Text)
    oidc_scopes = db.Column(db.String(255), default='openid profile email')
    oidc_redirect_uri = db.Column(db.String(500))

    just_in_time_provisioning = db.Column(db.Boolean, default=True)
    default_role = db.Column(db.String(20), default='student')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (db.Index('idx_sso_org_protocol', 'organization_id', 'protocol'),)


class ApiKey(db.Model):
    """Public REST API key with scopes (versioned at /api/v1)."""
    __tablename__ = 'api_keys'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    name = db.Column(db.String(120), nullable=False)
    prefix = db.Column(db.String(12), nullable=False)       # first 8 chars, shown to user
    key_hash = db.Column(db.String(128), nullable=False)    # sha256 of full key
    scopes = db.Column(db.JSON, default=list)               # ['read:courses','write:enrollments',...]
    rate_limit_per_minute = db.Column(db.Integer, default=120)
    last_used_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)
    revoked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.Index('idx_apikey_prefix', 'prefix'),)


class AuditEvent(db.Model):
    """Tamper-evident audit log entry. Append-only."""
    __tablename__ = 'audit_events'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    actor_user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    actor_api_key_id = db.Column(db.String(36), db.ForeignKey('api_keys.id'))
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'))
    action = db.Column(db.String(80), nullable=False)        # e.g. 'user.login','course.publish'
    resource_type = db.Column(db.String(40))
    resource_id = db.Column(db.String(36))
    ip_address = db.Column(db.String(64))
    user_agent = db.Column(db.String(255))
    details = db.Column(db.JSON)
    severity = db.Column(db.String(16), default='info')      # info|warning|error|critical
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (
        db.Index('idx_audit_actor_created', 'actor_user_id', 'created_at'),
        db.Index('idx_audit_action', 'action'),
    )


class ConsentRecord(db.Model):
    """GDPR / Oman PDPL / FERPA / CCPA consent log."""
    __tablename__ = 'consent_records'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    consent_type = db.Column(db.String(40), nullable=False)  # tos|privacy|marketing|proctoring|parental
    framework = db.Column(db.String(20))                     # gdpr|pdpl|ferpa|ccpa
    version = db.Column(db.String(20))
    granted = db.Column(db.Boolean, default=True)
    ip_address = db.Column(db.String(64))
    user_agent = db.Column(db.String(255))
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    revoked_at = db.Column(db.DateTime)
    __table_args__ = (db.Index('idx_consent_user_type', 'user_id', 'consent_type'),)


# ============================================
# PHASE 3 — SMART ASSESSMENT, RETENTION & TRANSPARENT PROCTORING
# ============================================

class AssessmentAttempt(db.Model):
    """
    Granular assessment attempt log.

    Complements the legacy ExamResult model by adding:
      - explicit `attempt_kind` (initial | retention | practice | rubric_only)
      - `consent_proctoring` and `accommodation_opt_out`
      - rubric grading output for free-text answers
      - flagged status with human-readable explanations

    No biometric, video, audio, or face data is ever stored. Only the signals
    listed in `app.services.assessment_service.PROCTORING_SIGNALS` are recorded.
    """
    __tablename__ = 'assessment_attempts'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    exam_id = db.Column(db.String(36), db.ForeignKey('exams.id'), nullable=True)
    exam_result_id = db.Column(db.String(36), db.ForeignKey('exam_results.id'), nullable=True)

    # Retention scheduling fields
    attempt_kind = db.Column(db.String(20), default='initial')
    # initial | retention | practice | rubric_only
    skill_id = db.Column(db.String(36), db.ForeignKey('skills.id'), nullable=True)

    # Consent / accommodations (transparent proctoring)
    consent_proctoring = db.Column(db.Boolean, default=False)
    accommodation_opt_out = db.Column(db.Boolean, default=False)
    consent_signals = db.Column(db.JSON, default=list)  # list of signal codes the learner accepted

    # Status & timing
    status = db.Column(db.String(20), default='in_progress')
    # in_progress | submitted | graded | abandoned
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime)
    time_spent_seconds = db.Column(db.Integer)

    # Score
    score = db.Column(db.Float)
    total_points = db.Column(db.Float)
    percentage = db.Column(db.Float)

    # Rubric grading output (per question, per criterion).
    # Shape:
    #   { question_id: {
    #       "criteria": [
    #         {"name": "...", "name_ar": "...", "score": 3, "max": 5,
    #          "feedback": "...", "feedback_ar": "..."}
    #       ],
    #       "total": 12, "max_total": 20, "comment": "...", "comment_ar": "..."
    #     } }
    rubric_results = db.Column(db.JSON, default=dict)

    # Transparent flagging
    flagged = db.Column(db.Boolean, default=False)
    flag_reasons = db.Column(db.JSON, default=list)
    # Each entry: {"code": "many_tab_blurs", "description": "...",
    #              "description_ar": "...", "evidence_count": 3}
    teacher_review_status = db.Column(db.String(20), default='pending')
    # pending | dismissed | confirmed | excused
    teacher_notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    events = db.relationship(
        'ProctoringEvent',
        backref='attempt',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )

    __table_args__ = (
        db.Index('idx_attempt_user', 'user_id'),
        db.Index('idx_attempt_exam', 'exam_id'),
        db.Index('idx_attempt_flagged', 'flagged'),
        db.Index('idx_attempt_kind', 'attempt_kind'),
    )


class ProctoringEvent(db.Model):
    """
    A single transparent proctoring signal observed during an attempt.

    Allowed `event_type` values must be one of the keys in
    `app.services.assessment_service.PROCTORING_SIGNALS`.
    No biometric / camera / microphone data is ever accepted.
    """
    __tablename__ = 'proctoring_events'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    attempt_id = db.Column(
        db.String(36), db.ForeignKey('assessment_attempts.id'), nullable=False
    )

    event_type = db.Column(db.String(40), nullable=False)
    # tab_blur | tab_focus | paste_detected | copy_detected |
    # fullscreen_exit | window_resize | time_anomaly | navigation_attempt

    severity = db.Column(db.String(10), default='info')  # info | warn | high
    payload = db.Column(db.JSON, default=dict)
    # Small, non-identifying payload. Examples:
    # {"chars": 245} for paste_detected, {"duration_ms": 4200} for tab_blur

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_event_attempt', 'attempt_id'),
        db.Index('idx_event_type', 'event_type'),
    )


# ============================================
# END PHASE 3
# ============================================


class DataRequest(db.Model):
    """Subject Access / Erasure request (GDPR Art.15/17, PDPL parity)."""
    __tablename__ = 'data_requests'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    request_type = db.Column(db.String(20), nullable=False)  # export|erasure|rectification
    framework = db.Column(db.String(20))
    status = db.Column(db.String(20), default='received')    # received|in_progress|completed|denied
    handled_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    notes = db.Column(db.Text)
    artifact_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    __table_args__ = (db.Index('idx_data_request_user', 'user_id', 'status'),)


class ScheduledJobRun(db.Model):
    """Distributed lock + status row for background scheduled jobs.

    One row per job_name. Used so that across multiple workers (Waitress /
    Gunicorn / Replit Scheduled Deployments) only a single worker performs a
    given job per interval, and admins can inspect the last successful run.
    """
    __tablename__ = 'scheduled_job_runs'
    job_name = db.Column(db.String(80), primary_key=True)
    locked_until = db.Column(db.DateTime)             # while > utcnow(), another worker holds it
    locked_by = db.Column(db.String(120))             # informational: hostname:pid
    last_started_at = db.Column(db.DateTime)
    last_success_at = db.Column(db.DateTime)
    last_error_at = db.Column(db.DateTime)
    last_error = db.Column(db.Text)
    last_result = db.Column(db.JSON)
    run_count = db.Column(db.Integer, default=0)
    success_count = db.Column(db.Integer, default=0)
    failure_count = db.Column(db.Integer, default=0)


# ============================================
# ADMIN KEY/VALUE CONFIG (SMTP, feature flags, misc)
# ============================================

class Notification(db.Model):
    """In-app notification + queueable email digest entry.

    `kind` is a short event slug (e.g. 'enrollment.completed', 'exam.graded',
    'forum.reply', 'at_risk.alert'). `payload` stores small JSON context for
    rendering the message. `read_at` is set when the user dismisses it.
    `email_sent_at` is set when the digest mailer flushes it (no-op when SMTP
    is not configured — entries simply remain queued).
    """
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), index=True, nullable=False)
    kind = db.Column(db.String(80), index=True, nullable=False)
    title = db.Column(db.String(240), nullable=False)
    body = db.Column(db.Text)
    url = db.Column(db.String(400))
    payload = db.Column(db.JSON)
    severity = db.Column(db.String(16), default='info')  # info | success | warning | critical
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    read_at = db.Column(db.DateTime)
    email_sent_at = db.Column(db.DateTime)


class KeyValueSetting(db.Model):
    """Generic admin key/value store for settings that don't warrant a column.

    Used by the System Administration page for SMTP/email config, feature
    flags, and other small admin-managed values. Values are stored as text
    (JSON-encoded for structured data).
    """
    __tablename__ = 'kv_settings'
    key = db.Column(db.String(120), primary_key=True)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(120))
