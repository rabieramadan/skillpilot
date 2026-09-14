#!/usr/bin/env python3
"""
Database Demo Data Seed Script for SkillPilot
Creates comprehensive demo data in PostgreSQL for testing all features:
- Institutions with admins, teachers, and students
- Courses with weekly materials
- Entry surveys, exams, and feedback surveys
- Student enrollments and progress
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, Institution, User, Course, CourseInstructor, CourseWeek, WeekMaterial
from app.models import Enrollment, Exam, ExamQuestion, ExamResult, Survey, SurveyQuestion, SurveyResponse
from datetime import datetime, timedelta
import hashlib
import uuid
import random

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_uuid():
    return str(uuid.uuid4())

# Demo institutions configuration - Single institution: UNIZWA
DEMO_INSTITUTIONS = [
    {
        'name': 'UNIZWA',
        'slug': 'unizwa',
        'admin_email': 'admin@unizwa.edu.om',
        'country': 'Oman',
        'billing_status': 'active',
        'subscription_plan': 'enterprise'
    }
]

# Demo users per institution
DEMO_USERS = {
    'admin': {'full_name': 'Institution Admin', 'role': 'institution_admin'},
    'teachers': [
        {'username': 'teacher1', 'full_name': 'Dr. Sarah Johnson', 'email': 'sarah.j@'},
        {'username': 'teacher2', 'full_name': 'Prof. Michael Chen', 'email': 'michael.c@'},
    ],
    'students': [
        {'username': 'student1', 'full_name': 'Alice Williams', 'email': 'alice.w@'},
        {'username': 'student2', 'full_name': 'Bob Martinez', 'email': 'bob.m@'},
        {'username': 'student3', 'full_name': 'Carol Davis', 'email': 'carol.d@'},
        {'username': 'student4', 'full_name': 'David Brown', 'email': 'david.b@'},
        {'username': 'student5', 'full_name': 'Eva Thompson', 'email': 'eva.t@'},
    ]
}

# Demo courses per institution - Based on attached training documents
DEMO_COURSES = [
    {
        'code': 'PPE101',
        'title': 'Practical Prompt Engineering',
        'description': 'A comprehensive hands-on guide to effectively communicating with Large Language Models (LLMs). Learn the mechanics of how LLMs work, master prompt components, and apply advanced techniques for complex tasks. Authored by Professor Rabie A. Ramadan, University of Nizwa.',
        'weeks': [
            {'title': 'Chapter 1: Understanding LLMs and Mastering Basic Prompts', 'materials': ['Introduction to LLMs', 'Tokens and Context Windows', 'Temperature and Creativity Control', 'Anatomy of Effective Prompts']},
            {'title': 'Chapter 2: Basic Prompt Patterns - Your Essential Toolkit', 'materials': ['Clear Instruction Pattern', 'Specific Context Pattern', 'Persona Assignment Pattern', 'Few-Shot Example Pattern']},
            {'title': 'Chapter 3: Strategic Prompt Patterns for Complex Tasks', 'materials': ['Chain-of-Thought Pattern', 'Outline Expansion Pattern', 'Fact Checklist Pattern', 'Iterative Refinement']},
            {'title': 'Chapter 4: Advanced Prompt Patterns and Templates', 'materials': ['Output Customization', 'Semantic Filter Pattern', 'Cognitive Verifier Pattern', 'Context Control']},
            {'title': 'Chapter 5: Prompt Engineering for Content Creation', 'materials': ['Marketing and Copywriting', 'Creative Writing and Storytelling', 'Summarization Techniques', 'Information Extraction']},
            {'title': 'Chapter 6: Advanced Prompting Techniques and Reasoning Models', 'materials': ['Auto Chain-of-Thought', 'Tree of Thought', 'Graph of Thought', 'Multi-modal Prompting']},
            {'title': 'Chapter 7: Ethical Considerations and Future Trends', 'materials': ['Bias and Fairness', 'Security and Privacy', 'Prompt Injection Defense', 'Emerging Trends']},
        ]
    },
    {
        'code': 'MHAI101',
        'title': 'Mental Health and AI - Complete Training Program',
        'description': 'A comprehensive 6-month training program for healthcare professionals, psychologists, social workers, and tech professionals interested in digital mental health. Covers clinical foundations, AI applications, ethics, and implementation. Hybrid delivery with lectures, hands-on labs, and clinical exposure.',
        'weeks': [
            {'title': 'Month 1 Week 1-2: Clinical Mental Health Foundations', 'materials': ['Mental Health Landscape Overview', 'DSM-5 and ICD-11 Frameworks', 'Evidence-Based Treatments', 'Crisis Intervention Basics']},
            {'title': 'Month 1 Week 3-4: Digital Mental Health Ecosystem', 'materials': ['Technology in Mental Health History', 'Digital Health Apps and Telehealth', 'Regulatory Framework (FDA, HIPAA, GDPR)', 'Digital Therapeutics vs Wellness Apps']},
            {'title': 'Month 2 Week 1-2: Programming and Data Foundations', 'materials': ['Python for Healthcare AI', 'Healthcare Data Formats (FHIR, HL7)', 'Data Cleaning and Preprocessing', 'Git and Version Control']},
            {'title': 'Month 2 Week 3-4: Machine Learning Fundamentals', 'materials': ['Supervised vs Unsupervised Learning', 'Neural Networks Introduction', 'NLP Basics', 'Working with Pre-trained Models']},
            {'title': 'Month 3 Week 1-2: AI for Assessment and Diagnosis', 'materials': ['AI-Powered Screening Tools', 'Suicide Risk Prediction', 'Clinical Text NLP', 'Voice Biomarkers for Mental Health']},
            {'title': 'Month 3 Week 3-4: AI for Treatment and Intervention', 'materials': ['Therapeutic Chatbots', 'AI-Powered CBT Apps', 'VR Therapy Applications', 'Remote Patient Monitoring']},
            {'title': 'Month 4 Week 1-2: Ethics and Professional Responsibility', 'materials': ['Ethical Frameworks in Healthcare AI', 'Algorithmic Bias and Fairness', 'Privacy and Data Security', 'Professional Boundaries with AI']},
            {'title': 'Month 4 Week 3-4: Clinical Validation and Evidence', 'materials': ['Research Methodology for Digital Health', 'Clinical Trial Design for AI', 'Validation Frameworks', 'Implementation Science']},
            {'title': 'Month 5: Capstone Project Development', 'materials': ['Project Planning and Literature Review', 'Technical Implementation', 'User Testing', 'Documentation and Presentation']},
            {'title': 'Month 6 Week 1-2: Specialization Tracks', 'materials': ['Clinical Implementation Track', 'AI Product Development Track', 'Research and Analytics Track', 'Policy and Advocacy Track']},
            {'title': 'Month 6 Week 3-4: Career Launch and Certification', 'materials': ['Final Project Presentations', 'Portfolio Development', 'Interview Preparation', 'Certification Exam']},
        ]
    },
    {
        'code': 'AISEC101',
        'title': 'AI and Security Training',
        'description': 'A 6-month intensive program combining AI and cybersecurity. Learn Python security essentials, machine learning for threat detection, adversarial attacks, secure AI deployment, and build AI-powered security tools. Total 240 hours of comprehensive training.',
        'weeks': [
            {'title': 'Month 1-2 Week 1: Python and Linux Security Essentials', 'materials': ['Python Security Programming', 'Linux Security Fundamentals', 'Security Scripting', 'Hands-on Lab Exercises']},
            {'title': 'Month 1-2 Week 2: ML Basics and Cryptography', 'materials': ['Machine Learning Fundamentals', 'Cryptography Principles', 'Encryption Algorithms', 'Practical Cryptography']},
            {'title': 'Month 1-2 Week 3: Neural Networks and Network Security', 'materials': ['Neural Network Architecture', 'Network Security Protocols', 'Deep Learning for Security', 'Protocol Analysis']},
            {'title': 'Month 1-2 Week 4: Data Security and Privacy-Preserving ML', 'materials': ['Data Security Principles', 'Privacy-Preserving Techniques', 'Secure ML Pipelines', 'Compliance Requirements']},
            {'title': 'Month 3-4 Week 1: Adversarial Attacks', 'materials': ['FGSM Attacks', 'Model Poisoning', 'Evasion Techniques', 'Attack Detection']},
            {'title': 'Month 3-4 Week 2: AI for Threat Detection', 'materials': ['Anomaly Detection Systems', 'SIEM Integration', 'Threat Intelligence', 'Real-time Monitoring']},
            {'title': 'Month 3-4 Week 3: Secure AI Deployment', 'materials': ['Model Encryption', 'API Security', 'Secure Inference', 'Production Security']},
            {'title': 'Month 3-4 Week 4: Malware and Phishing Detection', 'materials': ['ML-Based Malware Detection', 'Phishing Detection Models', 'Behavioral Analysis', 'Threat Classification']},
            {'title': 'Month 5-6 Week 1: AI Red Teaming', 'materials': ['Red Team Methodology', 'Attacking ML Systems', 'Vulnerability Assessment', 'Penetration Testing']},
            {'title': 'Month 5-6 Week 2: Automated Penetration Testing', 'materials': ['AI-Powered Pen Testing', 'Automation Tools', 'Vulnerability Scanning', 'Report Generation']},
            {'title': 'Month 5-6 Week 3: Secure LLM Applications', 'materials': ['LLM Security Principles', 'Prompt Injection Defense', 'Input Validation', 'Output Sanitization']},
            {'title': 'Month 5-6 Week 4: Capstone Project', 'materials': ['Project Planning', 'AI Security Tool Development', 'Testing and Validation', 'Final Presentation']},
        ]
    },
    {
        'code': 'AIVOC101',
        'title': 'AI Vocational Training',
        'description': 'A comprehensive 6-month AI vocational training program covering Python fundamentals, machine learning, neural networks, NLP, LLM engineering, model deployment, and generative AI. Includes hands-on projects and capstone presentation. Total 240 hours.',
        'weeks': [
            {'title': 'Month 1-2 Week 1: Python Basics', 'materials': ['Python Fundamentals', 'NumPy Essentials', 'Pandas Data Analysis', 'Practice Exercises']},
            {'title': 'Month 1-2 Week 2: Machine Learning Fundamentals', 'materials': ['Supervised Learning', 'Unsupervised Learning', 'Model Evaluation', 'Scikit-learn Basics']},
            {'title': 'Month 1-2 Week 3: Neural Networks', 'materials': ['Backpropagation', 'Activation Functions', 'Network Architectures', 'Training Techniques']},
            {'title': 'Month 1-2 Week 4: Computer Vision Basics', 'materials': ['Image Processing', 'CNN Architectures', 'Object Detection', 'Image Classification']},
            {'title': 'Month 3-4 Week 1: Natural Language Processing', 'materials': ['Tokenization', 'Transformers', 'BERT Models', 'GPT Architecture']},
            {'title': 'Month 3-4 Week 2: LLM Prompt Engineering', 'materials': ['Prompt Design', 'Fine-tuning Techniques', 'RAG Systems', 'Context Management']},
            {'title': 'Month 3-4 Week 3: Model Deployment', 'materials': ['Flask and FastAPI', 'Docker Containers', 'Cloud Platforms', 'API Design']},
            {'title': 'Month 3-4 Week 4: Project - Build Chatbot or Classifier', 'materials': ['Project Planning', 'Implementation', 'Testing', 'Documentation']},
            {'title': 'Month 5-6 Week 1: AI Ethics', 'materials': ['Bias Detection', 'Responsible AI Practices', 'Fairness in ML', 'Ethical Guidelines']},
            {'title': 'Month 5-6 Week 2: MLOps', 'materials': ['Monitoring Systems', 'Model Versioning', 'CI/CD Pipelines', 'Production Best Practices']},
            {'title': 'Month 5-6 Week 3: Generative AI', 'materials': ['Stable Diffusion', 'Midjourney APIs', 'Image Generation', 'Creative Applications']},
            {'title': 'Month 5-6 Week 4: Final Capstone Project', 'materials': ['Project Development', 'Presentation Preparation', 'Peer Review', 'Final Demonstration']},
        ]
    },
    {
        'code': 'SECVOC101',
        'title': 'Security Vocational Training',
        'description': 'A 6-month cybersecurity vocational training covering network fundamentals, Linux security, cryptography, penetration testing, web vulnerabilities, defensive security, and compliance. Includes hands-on labs and Capture The Flag exercises. Total 240 hours.',
        'weeks': [
            {'title': 'Month 1-2 Week 1: Network Basics', 'materials': ['TCP/IP Fundamentals', 'DNS and Firewalls', 'VPN Technology', 'Network Architecture']},
            {'title': 'Month 1-2 Week 2: Linux Security', 'materials': ['Bash Scripting', 'System Hardening', 'User Management', 'Security Configuration']},
            {'title': 'Month 1-2 Week 3: Cryptography', 'materials': ['Encryption and Hashing', 'PKI Infrastructure', 'SSL/TLS Protocols', 'Key Management']},
            {'title': 'Month 1-2 Week 4: Authentication', 'materials': ['Password Security', 'Multi-Factor Authentication', 'OAuth and SSO', 'Identity Management']},
            {'title': 'Month 3-4 Week 1: Penetration Testing Methodology', 'materials': ['Reconnaissance', 'Scanning Techniques', 'Exploitation', 'Post-Exploitation']},
            {'title': 'Month 3-4 Week 2: Web Vulnerabilities', 'materials': ['OWASP Top 10', 'SQL Injection', 'XSS Attacks', 'CSRF Protection']},
            {'title': 'Month 3-4 Week 3: Network Attacks', 'materials': ['Packet Sniffing', 'Man-in-the-Middle', 'Port Scanning', 'Network Exploitation']},
            {'title': 'Month 3-4 Week 4: Security Tools', 'materials': ['Metasploit Framework', 'Burp Suite', 'Nmap', 'Wireshark']},
            {'title': 'Month 5-6 Week 1: SIEM and Incident Response', 'materials': ['Log Analysis', 'Incident Response Procedures', 'Threat Hunting', 'Forensics Basics']},
            {'title': 'Month 5-6 Week 2: Malware Analysis', 'materials': ['Sandboxing', 'Threat Intelligence', 'Malware Types', 'Reverse Engineering Basics']},
            {'title': 'Month 5-6 Week 3: Cloud Security', 'materials': ['AWS Security Services', 'Azure Security', 'Cloud Architecture Security', 'Container Security']},
            {'title': 'Month 5-6 Week 4: Compliance and Capstone CTF', 'materials': ['GDPR Compliance', 'ISO 27001', 'SOC 2 Standards', 'Capture The Flag Exercise']},
        ]
    },
    {
        'code': 'AIIT101',
        'title': 'AI for Information Technology',
        'description': 'A comprehensive course exploring AI applications in Information Technology. Learn how AI transforms IT operations, infrastructure management, help desk automation, system monitoring, and IT service delivery. Ideal for IT professionals looking to leverage AI in their work.',
        'weeks': [
            {'title': 'Week 1: Introduction to AI in IT', 'materials': ['AI Overview for IT Professionals', 'Current AI Landscape in IT', 'Use Cases and Applications', 'Getting Started with AI Tools']},
            {'title': 'Week 2: AI for IT Operations (AIOps)', 'materials': ['AIOps Fundamentals', 'Automated Monitoring', 'Predictive Maintenance', 'Incident Management']},
            {'title': 'Week 3: AI-Powered Help Desk and Support', 'materials': ['Chatbots for IT Support', 'Ticket Classification', 'Knowledge Base Automation', 'Self-Service Portals']},
            {'title': 'Week 4: AI in Infrastructure Management', 'materials': ['Capacity Planning with AI', 'Resource Optimization', 'Cloud Cost Management', 'Automated Provisioning']},
            {'title': 'Week 5: AI for Network Management', 'materials': ['Network Traffic Analysis', 'Anomaly Detection', 'Performance Optimization', 'Predictive Network Issues']},
            {'title': 'Week 6: AI in Cybersecurity for IT', 'materials': ['Threat Detection with AI', 'Automated Security Response', 'Vulnerability Assessment', 'Security Monitoring']},
            {'title': 'Week 7: AI for Data Management', 'materials': ['Data Quality Automation', 'Intelligent Data Classification', 'Database Optimization', 'Backup and Recovery AI']},
            {'title': 'Week 8: Implementing AI in IT Projects', 'materials': ['Project Planning', 'Tool Selection', 'Integration Strategies', 'Best Practices and Capstone']},
        ]
    }
]

# Generic exam questions for AI/Tech courses
AI_EXAM_QUESTIONS = [
    {'text': 'What is Artificial Intelligence?', 'type': 'multiple_choice',
     'options': ['A: Computer programs that mimic human intelligence', 'B: A type of robot', 'C: A programming language', 'D: A database system'],
     'correct': 'A', 'points': 10, 'difficulty': 'easy', 'topic': 'AI Basics'},
    {'text': 'What is Machine Learning?', 'type': 'multiple_choice',
     'options': ['A: Programming computers manually', 'B: A subset of AI where systems learn from data', 'C: A type of hardware', 'D: Internet connectivity'],
     'correct': 'B', 'points': 10, 'difficulty': 'easy', 'topic': 'ML Basics'},
    {'text': 'What is a neural network?', 'type': 'multiple_choice',
     'options': ['A: A social media platform', 'B: A computing system inspired by biological neural networks', 'C: A type of internet connection', 'D: A file format'],
     'correct': 'B', 'points': 15, 'difficulty': 'medium', 'topic': 'Neural Networks'},
    {'text': 'What is prompt engineering?', 'type': 'multiple_choice',
     'options': ['A: Building hardware', 'B: Crafting effective inputs for AI models', 'C: Installing software', 'D: Network configuration'],
     'correct': 'B', 'points': 15, 'difficulty': 'medium', 'topic': 'Prompt Engineering'},
    {'text': 'What does NLP stand for?', 'type': 'multiple_choice',
     'options': ['A: Natural Language Processing', 'B: Network Logic Protocol', 'C: New Learning Platform', 'D: Neural Learning Program'],
     'correct': 'A', 'points': 10, 'difficulty': 'easy', 'topic': 'NLP'},
]

SECURITY_EXAM_QUESTIONS = [
    {'text': 'What is the primary purpose of encryption?', 'type': 'multiple_choice',
     'options': ['A: To compress data', 'B: To protect data confidentiality', 'C: To speed up networks', 'D: To delete files'],
     'correct': 'B', 'points': 10, 'difficulty': 'easy', 'topic': 'Cryptography'},
    {'text': 'What does OWASP stand for?', 'type': 'multiple_choice',
     'options': ['A: Open Web Application Security Project', 'B: Online Web Access Security Protocol', 'C: Operating Web Application Software Program', 'D: Open Wireless Access Security Policy'],
     'correct': 'A', 'points': 15, 'difficulty': 'medium', 'topic': 'Web Security'},
    {'text': 'What is SQL injection?', 'type': 'multiple_choice',
     'options': ['A: A database backup method', 'B: An attack that exploits vulnerabilities in database queries', 'C: A type of encryption', 'D: A programming language'],
     'correct': 'B', 'points': 15, 'difficulty': 'medium', 'topic': 'Web Vulnerabilities'},
    {'text': 'What is multi-factor authentication?', 'type': 'multiple_choice',
     'options': ['A: Using only passwords', 'B: Using two or more verification methods', 'C: Using biometrics only', 'D: Using no authentication'],
     'correct': 'B', 'points': 10, 'difficulty': 'easy', 'topic': 'Authentication'},
    {'text': 'What is a firewall?', 'type': 'multiple_choice',
     'options': ['A: A physical wall', 'B: A network security system that monitors and controls traffic', 'C: A type of virus', 'D: A backup device'],
     'correct': 'B', 'points': 10, 'difficulty': 'easy', 'topic': 'Network Security'},
]

# Survey questions templates
ENTRY_SURVEY_QUESTIONS = [
    {'text': 'What is your current experience level with AI?', 'type': 'multiple_choice', 'options': ['Beginner', 'Intermediate', 'Advanced', 'Expert']},
    {'text': 'What are your primary learning goals?', 'type': 'multiple_choice', 'options': ['Career advancement', 'Personal interest', 'Academic requirement', 'Business application']},
    {'text': 'How many hours per week can you dedicate to learning?', 'type': 'multiple_choice', 'options': ['1-3 hours', '4-6 hours', '7-10 hours', 'More than 10 hours']},
    {'text': 'What is your preferred learning style?', 'type': 'multiple_choice', 'options': ['Video lectures', 'Reading materials', 'Hands-on projects', 'Discussion-based']},
]

FEEDBACK_SURVEY_QUESTIONS = [
    {'text': 'How would you rate the overall course quality?', 'type': 'rating', 'options': ['1', '2', '3', '4', '5']},
    {'text': 'The course content met my expectations', 'type': 'likert', 'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree']},
    {'text': 'The instructor was knowledgeable and helpful', 'type': 'likert', 'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree']},
    {'text': 'I would recommend this course to others', 'type': 'likert', 'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree']},
    {'text': 'What could be improved in this course?', 'type': 'text', 'options': []},
]

# Exam questions templates
EXAM_QUESTIONS = [
    {'text': 'What is Artificial Intelligence?', 'type': 'multiple_choice', 
     'options': ['A: Computer programs that mimic human intelligence', 'B: A type of robot', 'C: A programming language', 'D: A database system'],
     'correct': 'A', 'points': 10, 'difficulty': 'easy', 'topic': 'AI Basics'},
    {'text': 'Which of the following is a type of machine learning?', 'type': 'multiple_choice',
     'options': ['A: Supervised Learning', 'B: Internet Learning', 'C: Manual Learning', 'D: Static Learning'],
     'correct': 'A', 'points': 10, 'difficulty': 'easy', 'topic': 'ML Types'},
    {'text': 'What is a neural network?', 'type': 'multiple_choice',
     'options': ['A: A social media platform', 'B: A computing system inspired by biological neural networks', 'C: A type of internet connection', 'D: A file format'],
     'correct': 'B', 'points': 15, 'difficulty': 'medium', 'topic': 'Neural Networks'},
    {'text': 'Deep learning is a subset of machine learning.', 'type': 'multiple_choice',
     'options': ['A: True', 'B: False'],
     'correct': 'A', 'points': 10, 'difficulty': 'easy', 'topic': 'Deep Learning'},
    {'text': 'What is prompt engineering?', 'type': 'multiple_choice',
     'options': ['A: Building hardware', 'B: Crafting effective inputs for AI models', 'C: Installing software', 'D: Network configuration'],
     'correct': 'B', 'points': 15, 'difficulty': 'medium', 'topic': 'Prompt Engineering'},
]


def create_simple_demo_accounts(institution, courses=None):
    """Create simple demo accounts with easy-to-remember credentials for each institution"""
    simple_accounts = [
        {'username': 'demoadmin', 'password': 'demo123', 'role': 'institution_admin', 'full_name': 'Demo Admin', 'email': 'demoadmin@demo.edu'},
        {'username': 'demoteacher1', 'password': 'demo123', 'role': 'instructor', 'full_name': 'Demo Teacher', 'email': 'demoteacher@demo.edu'},
        {'username': 'demostudent1', 'password': 'demo123', 'role': 'student', 'full_name': 'Demo Student', 'email': 'demostudent@demo.edu'},
    ]
    
    created = []
    demo_student = None
    for account in simple_accounts:
        # Check for existing user with this username in THIS institution
        existing = User.query.filter_by(
            username=account['username'],
            institution_id=institution.id
        ).first()
        if not existing:
            user = User(
                id=generate_uuid(),
                institution_id=institution.id,
                username=account['username'],
                email=f"{account['username']}@{institution.slug}.edu",
                password_hash=hash_password(account['password']),
                full_name=account['full_name'],
                role=account['role'],
                is_active=True
            )
            db.session.add(user)
            created.append(user)
            print(f"  ✓ Created simple demo: {account['username']} / {account['password']} ({account['role']})")
            if account['role'] == 'student':
                demo_student = user
        else:
            print(f"  ✓ Simple demo exists: {account['username']}")
            created.append(existing)
            if account['role'] == 'student':
                demo_student = existing
    
    # Enroll demo student in all courses for this institution
    if demo_student and courses:
        for course in courses:
            existing_enrollment = Enrollment.query.filter_by(
                user_id=demo_student.id,
                course_id=course.id
            ).first()
            if not existing_enrollment:
                enrollment = Enrollment(
                    id=generate_uuid(),
                    user_id=demo_student.id,
                    course_id=course.id,
                    status='approved',
                    enrolled_at=datetime.now()
                )
                db.session.add(enrollment)
                print(f"  ✓ Enrolled demostudent1 in: {course.title}")
    
    return created


def create_demo_data():
    """Main function to create all demo data"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("SKILLPILOT DATABASE DEMO DATA SEEDER")
        print("=" * 60)
        
        created_data = {
            'institutions': [],
            'users': [],
            'courses': [],
            'surveys': [],
            'exams': []
        }
        
        for inst_config in DEMO_INSTITUTIONS:
            print(f"\n📦 Processing Institution: {inst_config['name']}")
            
            # Check if institution already exists
            existing_inst = Institution.query.filter_by(slug=inst_config['slug']).first()
            if existing_inst:
                print(f"  ✓ Institution exists: {existing_inst.id}")
                institution = existing_inst
            else:
                # Create institution
                institution = Institution(
                    id=generate_uuid(),
                    name=inst_config['name'],
                    slug=inst_config['slug'],
                    admin_email=inst_config['admin_email'],
                    country=inst_config.get('country', 'Unknown'),
                    billing_status=inst_config.get('billing_status', 'trial'),
                    is_active=True
                )
                db.session.add(institution)
                db.session.flush()
                print(f"  ✓ Created institution: {institution.id}")
            
            created_data['institutions'].append(institution)
            
            # Track courses created for this institution (for demo enrollments)
            institution_courses = []
            
            # Create institution admin
            admin_username = f"admin_{inst_config['slug'].replace('-', '_')}"
            existing_admin = User.query.filter_by(
                username=admin_username,
                institution_id=institution.id
            ).first()
            
            if not existing_admin:
                admin_user = User(
                    id=generate_uuid(),
                    institution_id=institution.id,
                    username=admin_username,
                    email=inst_config['admin_email'],
                    password_hash=hash_password('admin123'),
                    full_name=f"{inst_config['name']} Admin",
                    role='institution_admin',
                    is_active=True
                )
                db.session.add(admin_user)
                print(f"  ✓ Created admin: {admin_username} (password: admin123)")
                created_data['users'].append(admin_user)
            else:
                print(f"  ✓ Admin exists: {admin_username}")
            
            # Create teachers
            teachers = []
            for i, teacher_config in enumerate(DEMO_USERS['teachers'], 1):
                teacher_username = f"{teacher_config['username']}_{inst_config['slug'].replace('-', '_')}"
                existing_teacher = User.query.filter_by(
                    username=teacher_username,
                    institution_id=institution.id
                ).first()
                
                if not existing_teacher:
                    teacher = User(
                        id=generate_uuid(),
                        institution_id=institution.id,
                        username=teacher_username,
                        email=f"{teacher_config['email']}{inst_config['slug']}.edu",
                        password_hash=hash_password('teacher123'),
                        full_name=teacher_config['full_name'],
                        role='instructor',
                        is_active=True
                    )
                    db.session.add(teacher)
                    teachers.append(teacher)
                    print(f"  ✓ Created teacher: {teacher_username} (password: teacher123)")
                    created_data['users'].append(teacher)
                else:
                    teachers.append(existing_teacher)
                    print(f"  ✓ Teacher exists: {teacher_username}")
            
            # Create students
            students = []
            for student_config in DEMO_USERS['students']:
                student_username = f"{student_config['username']}_{inst_config['slug'].replace('-', '_')}"
                existing_student = User.query.filter_by(
                    username=student_username,
                    institution_id=institution.id
                ).first()
                
                if not existing_student:
                    student = User(
                        id=generate_uuid(),
                        institution_id=institution.id,
                        username=student_username,
                        email=f"{student_config['email']}{inst_config['slug']}.edu",
                        password_hash=hash_password('student123'),
                        full_name=student_config['full_name'],
                        role='student',
                        is_active=True
                    )
                    db.session.add(student)
                    students.append(student)
                    print(f"  ✓ Created student: {student_username} (password: student123)")
                    created_data['users'].append(student)
                else:
                    students.append(existing_student)
                    print(f"  ✓ Student exists: {student_username}")
            
            db.session.flush()
            
            # Create courses
            for course_idx, course_config in enumerate(DEMO_COURSES):
                course_code = f"{course_config['code']}_{inst_config['slug'][:3].upper()}"
                existing_course = Course.query.filter_by(
                    code=course_code,
                    institution_id=institution.id
                ).first()
                
                if not existing_course:
                    course = Course(
                        id=generate_uuid(),
                        institution_id=institution.id,
                        code=course_code,
                        title=course_config['title'],
                        description=course_config['description'],
                        is_published=True,
                        start_date=datetime.now().date(),
                        end_date=(datetime.now() + timedelta(days=90)).date(),
                        passing_threshold=60.0,
                        certificate_enabled=True
                    )
                    db.session.add(course)
                    db.session.flush()
                    print(f"  ✓ Created course: {course_code}")
                    created_data['courses'].append(course)
                    institution_courses.append(course)
                    
                    # Assign teacher to course
                    if teachers:
                        teacher_for_course = teachers[course_idx % len(teachers)]
                        existing_instructor = CourseInstructor.query.filter_by(
                            course_id=course.id,
                            user_id=teacher_for_course.id
                        ).first()
                        if not existing_instructor:
                            instructor_link = CourseInstructor(
                                id=generate_uuid(),
                                course_id=course.id,
                                user_id=teacher_for_course.id,
                                role='instructor'
                            )
                            db.session.add(instructor_link)
                            print(f"    → Assigned {teacher_for_course.username} as instructor")
                    
                    # Create weekly materials
                    for week_num, week_config in enumerate(course_config['weeks'], 1):
                        week = CourseWeek(
                            id=generate_uuid(),
                            course_id=course.id,
                            week_number=week_num,
                            title=week_config['title'],
                            is_published=True,
                            start_date=(datetime.now() + timedelta(weeks=week_num-1)).date(),
                            end_date=(datetime.now() + timedelta(weeks=week_num)).date()
                        )
                        db.session.add(week)
                        db.session.flush()
                        
                        # Create materials for each week
                        for mat_idx, material_title in enumerate(week_config['materials']):
                            material = WeekMaterial(
                                id=generate_uuid(),
                                week_id=week.id,
                                title=material_title,
                                material_type='document',
                                external_url='#',
                                order_index=mat_idx,
                                is_published=True
                            )
                            db.session.add(material)
                    
                    # Determine exam questions based on course type
                    is_security_course = 'Security' in course_config['title'] or 'SEC' in course_config['code']
                    entry_questions = ENTRY_SURVEY_QUESTIONS
                    exam_questions = SECURITY_EXAM_QUESTIONS if is_security_course else AI_EXAM_QUESTIONS
                    feedback_questions = FEEDBACK_SURVEY_QUESTIONS
                    
                    # Create Entry Survey for the course
                    entry_survey = Survey(
                        id=generate_uuid(),
                        course_id=course.id,
                        institution_id=institution.id,
                        title=f"Entry Survey - {course_config['title']}",
                        description="Please complete this survey before starting the course",
                        survey_type='entry_survey',
                        is_required=True,
                        is_published=True
                    )
                    db.session.add(entry_survey)
                    db.session.flush()
                    
                    for q_idx, q in enumerate(entry_questions):
                        question = SurveyQuestion(
                            id=generate_uuid(),
                            survey_id=entry_survey.id,
                            question_text=q['text'],
                            question_type=q['type'],
                            options=q['options'],
                            is_required=True,
                            order_index=q_idx
                        )
                        db.session.add(question)
                    print(f"    → Created Entry Survey with {len(entry_questions)} questions")
                    created_data['surveys'].append(entry_survey)
                    
                    # Create Exam for the course
                    exam = Exam(
                        id=generate_uuid(),
                        course_id=course.id,
                        title=f"Course Exam - {course_config['title']}",
                        description="Complete this exam to test your knowledge and earn your certificate",
                        exam_type='final',
                        passing_threshold=60.0,
                        time_limit_minutes=60,
                        max_attempts=3,
                        shuffle_questions=True,
                        show_results=True,
                        is_published=True
                    )
                    db.session.add(exam)
                    db.session.flush()
                    
                    for q_idx, q in enumerate(exam_questions):
                        question = ExamQuestion(
                            id=generate_uuid(),
                            exam_id=exam.id,
                            question_text=q['text'],
                            question_type=q['type'],
                            options=q['options'],
                            correct_answer=q['correct'],
                            points=q['points'],
                            difficulty=q['difficulty'],
                            topic=q['topic'],
                            order_index=q_idx
                        )
                        db.session.add(question)
                    print(f"    → Created Course Exam with {len(exam_questions)} questions")
                    created_data['exams'].append(exam)
                    
                    # Create Feedback Survey for the course
                    feedback_survey = Survey(
                        id=generate_uuid(),
                        course_id=course.id,
                        institution_id=institution.id,
                        title=f"Training Feedback - {course_config['title']}",
                        description="Please provide your feedback about the course",
                        survey_type='training_feedback',
                        is_required=True,
                        is_published=True
                    )
                    db.session.add(feedback_survey)
                    db.session.flush()
                    
                    for q_idx, q in enumerate(feedback_questions):
                        question = SurveyQuestion(
                            id=generate_uuid(),
                            survey_id=feedback_survey.id,
                            question_text=q['text'],
                            question_type=q['type'],
                            options=q['options'],
                            is_required=True,
                            order_index=q_idx
                        )
                        db.session.add(question)
                    print(f"    → Created Feedback Survey with {len(feedback_questions)} questions")
                    created_data['surveys'].append(feedback_survey)
                    
                    # Enroll students in the course and create demo responses
                    for student in students:
                        # Create enrollment
                        existing_enrollment = Enrollment.query.filter_by(
                            user_id=student.id,
                            course_id=course.id
                        ).first()
                        
                        if not existing_enrollment:
                            enrollment = Enrollment(
                                id=generate_uuid(),
                                user_id=student.id,
                                course_id=course.id,
                                status='active',
                                payment_status='not_required',
                                progress_percent=75.0,
                                current_week=3
                            )
                            db.session.add(enrollment)
                            
                            # Create entry survey response (use correct questions based on class type)
                            entry_response = SurveyResponse(
                                id=generate_uuid(),
                                survey_id=entry_survey.id,
                                user_id=student.id,
                                answers={
                                    str(i): entry_questions[i % len(entry_questions)]['options'][0]
                                    for i in range(len(entry_questions))
                                }
                            )
                            db.session.add(entry_response)
                            
                            # Create exam result (some pass, some fail for variety)
                            score = random.randint(50, 100)
                            passed = score >= 60
                            exam_result = ExamResult(
                                id=generate_uuid(),
                                exam_id=exam.id,
                                user_id=student.id,
                                attempt_number=1,
                                score=score,
                                total_points=60,
                                percentage=score,
                                passed=passed,
                                started_at=datetime.now() - timedelta(hours=2),
                                submitted_at=datetime.now() - timedelta(hours=1),
                                time_spent_seconds=2400,
                                certificate_status='pending' if passed else 'not_eligible'
                            )
                            db.session.add(exam_result)
                            
                            # Create feedback survey response (use correct questions based on class type)
                            feedback_answers = {}
                            for i, q in enumerate(feedback_questions):
                                if q['type'] == 'rating':
                                    feedback_answers[str(i)] = '4'
                                elif q['type'] == 'likert':
                                    feedback_answers[str(i)] = 'Agree'
                                elif q['type'] == 'text':
                                    feedback_answers[str(i)] = 'Great training overall!'
                                else:
                                    feedback_answers[str(i)] = q['options'][0] if q['options'] else ''
                            
                            feedback_response = SurveyResponse(
                                id=generate_uuid(),
                                survey_id=feedback_survey.id,
                                user_id=student.id,
                                answers=feedback_answers
                            )
                            db.session.add(feedback_response)
                    
                    print(f"    → Enrolled {len(students)} students with survey responses and exam results")
                    
                else:
                    print(f"  ✓ Course exists: {course_code}")
                    institution_courses.append(existing_course)
            
            # Create simple demo accounts for this institution (with enrollments)
            print("\n  🎯 Creating Simple Demo Accounts (for quick testing):")
            simple_users = create_simple_demo_accounts(institution, institution_courses)
            created_data['users'].extend(simple_users)
        
        # Commit all changes
        db.session.commit()
        
        print("\n" + "=" * 60)
        print("DEMO DATA CREATION COMPLETE!")
        print("=" * 60)
        print(f"\nCreated/verified: {len(created_data['institutions'])} institutions")
        
        print("\n📝 LOGIN CREDENTIALS:")
        print("-" * 40)
        print("Institution Admins: admin_<slug> / admin123")
        print("Teachers: teacher1_<slug> / teacher123")
        print("          teacher2_<slug> / teacher123")
        print("Students: student1_<slug> / student123")
        print("          student2_<slug> / student123")
        print("          (and so on...)")
        print("-" * 40)
        print("\nExample logins:")
        print("  Admin: admin_ai_training_academy / admin123")
        print("  Teacher: teacher1_ai_training_academy / teacher123")
        print("  Student: student1_ai_training_academy / student123")
        
        return created_data


if __name__ == '__main__':
    create_demo_data()
