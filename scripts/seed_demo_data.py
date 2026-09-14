#!/usr/bin/env python3
"""
Seed Demo Data for SkillPilot
Generates realistic test data for classes, enrollments, exams, and submissions
"""

import json
import hashlib
import random
from datetime import datetime, timedelta
from pathlib import Path

# File paths
BASE_DIR = Path(__file__).parent.parent
USERS_FILE = BASE_DIR / 'users.json'
INSTRUCTORS_FILE = BASE_DIR / 'instructors.json'
CLASSES_FILE = BASE_DIR / 'classes.json'
ENROLLMENTS_FILE = BASE_DIR / 'enrollments.json'
CLASS_EXAMS_FILE = BASE_DIR / 'class_exams.json'
CLASS_EXAM_SUBMISSIONS_FILE = BASE_DIR / 'class_exam_submissions.json'

def hash_password(password):
    """Hash a password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_id(prefix, existing_list):
    """Generate unique ID for new entities"""
    if not existing_list:
        return f"{prefix}_1"
    
    # Extract numeric IDs
    numbers = []
    for item in existing_list:
        id_key = [k for k in item.keys() if '_id' in k][0]
        item_id = item[id_key]
        if item_id.startswith(prefix + '_'):
            try:
                numbers.append(int(item_id.split('_')[-1]))
            except:
                pass
    
    next_num = max(numbers) + 1 if numbers else 1
    return f"{prefix}_{next_num}"

def load_json(filepath):
    """Load JSON file"""
    if filepath.exists():
        with open(filepath, 'r') as f:
            return json.load(f)
    return {}

def save_json(filepath, data):
    """Save JSON file"""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved {filepath.name}")

def create_demo_teachers():
    """Create demo teacher accounts"""
    users_data = load_json(USERS_FILE)
    instructors_data = load_json(INSTRUCTORS_FILE)
    
    teachers = [
        {
            "username": "demo_teacher1",
            "password": "teacher123",  # Will be hashed
            "full_name": "Dr. Sarah Johnson",
            "email": "sarah.johnson@skillpilot.edu",
            "phone": "+1-555-0101",
            "organization": "SkillPilot University",
            "role": "Instructor",
            "bio": "AI and Machine Learning expert with 10+ years of experience",
            "expertise": ["AI", "Machine Learning", "Prompt Engineering"]
        },
        {
            "username": "demo_teacher2",
            "password": "teacher123",
            "full_name": "Prof. Ahmed Al-Rashid",
            "email": "ahmed.alrashid@skillpilot.edu",
            "phone": "+968-9999-1234",
            "organization": "SkillPilot University",
            "role": "Instructor",
            "bio": "Ethics and AI specialist, focusing on responsible AI development",
            "expertise": ["Ethics", "AI Governance", "Responsible AI"]
        },
        {
            "username": "demo_teacher3",
            "password": "teacher123",
            "full_name": "Dr. Maria Garcia",
            "email": "maria.garcia@skillpilot.edu",
            "phone": "+34-612-345-678",
            "organization": "SkillPilot University",
            "role": "Instructor",
            "bio": "Agentic AI and autonomous systems researcher",
            "expertise": ["Agentic AI", "Autonomous Systems", "Multi-Agent Systems"]
        }
    ]
    
    created_teachers = []
    for teacher in teachers:
        # Check if already exists
        existing = next((u for u in users_data.get('users', []) if u['username'] == teacher['username']), None)
        if existing:
            created_teachers.append(existing)
            continue
        
        # Create new teacher user
        user_id = generate_id('demo_teacher', users_data.get('users', []))
        new_user = {
            "user_id": user_id,
            "username": teacher['username'],
            "password": hash_password(teacher['password']),
            "full_name": teacher['full_name'],
            "email": teacher['email'],
            "phone": teacher['phone'],
            "organization": teacher['organization'],
            "role": teacher['role'],
            "registered_at": datetime.now().isoformat(),
            "last_login": None
        }
        users_data.setdefault('users', []).append(new_user)
        created_teachers.append(new_user)
        
        # Create instructor profile
        instructor_id = generate_id('demo_inst', instructors_data.get('instructors', []))
        new_instructor = {
            "instructor_id": instructor_id,
            "user_id": user_id,
            "bio": teacher['bio'],
            "expertise": teacher['expertise'],
            "created_at": datetime.now().isoformat()
        }
        instructors_data.setdefault('instructors', []).append(new_instructor)
    
    save_json(USERS_FILE, users_data)
    save_json(INSTRUCTORS_FILE, instructors_data)
    return created_teachers

def create_demo_students():
    """Create demo student accounts"""
    users_data = load_json(USERS_FILE)
    
    students = [
        {"username": "demo_student1", "full_name": "Alice Williams", "email": "alice.w@student.skillpilot.edu"},
        {"username": "demo_student2", "full_name": "Bob Chen", "email": "bob.c@student.skillpilot.edu"},
        {"username": "demo_student3", "full_name": "Charlie Davis", "email": "charlie.d@student.skillpilot.edu"},
        {"username": "demo_student4", "full_name": "Diana Martinez", "email": "diana.m@student.skillpilot.edu"},
        {"username": "demo_student5", "full_name": "Ethan Brown", "email": "ethan.b@student.skillpilot.edu"},
        {"username": "demo_student6", "full_name": "Fatima Al-Said", "email": "fatima.a@student.skillpilot.edu"},
        {"username": "demo_student7", "full_name": "George Taylor", "email": "george.t@student.skillpilot.edu"},
        {"username": "demo_student8", "full_name": "Hannah Lee", "email": "hannah.l@student.skillpilot.edu"},
    ]
    
    created_students = []
    for i, student in enumerate(students):
        # Check if already exists
        existing = next((u for u in users_data.get('users', []) if u['username'] == student['username']), None)
        if existing:
            created_students.append(existing)
            continue
        
        # Create new student user
        user_id = generate_id('demo_student', users_data.get('users', []))
        new_user = {
            "user_id": user_id,
            "username": student['username'],
            "password": hash_password("student123"),
            "full_name": student['full_name'],
            "email": student['email'],
            "phone": f"+1-555-{1200 + i:04d}",
            "organization": "SkillPilot University",
            "role": "Student",
            "registered_at": (datetime.now() - timedelta(days=random.randint(30, 90))).isoformat(),
            "last_login": (datetime.now() - timedelta(days=random.randint(1, 10))).isoformat()
        }
        users_data.setdefault('users', []).append(new_user)
        created_students.append(new_user)
    
    save_json(USERS_FILE, users_data)
    return created_students

def create_demo_classes(teachers):
    """Create demo classes"""
    classes_data = load_json(CLASSES_FILE)
    instructors_data = load_json(INSTRUCTORS_FILE)
    
    # Get instructor IDs for teachers
    teacher_instructor_ids = []
    for teacher in teachers:
        instructor = next((i for i in instructors_data.get('instructors', []) if i['user_id'] == teacher['user_id']), None)
        if instructor:
            teacher_instructor_ids.append(instructor['instructor_id'])
    
    demo_classes = [
        {
            "class_code": "PE-2025W-101",
            "instructor_ids": [teacher_instructor_ids[0]] if teacher_instructor_ids else [],
            "title": "Fundamentals of Prompt Engineering",
            "description": "Learn the basics of prompt engineering, including prompt design, testing, and optimization for various AI models.",
            "semester": "Winter 2025",
            "start_date": "2025-01-15",
            "end_date": "2025-03-20",
            "schedule": "Mon/Wed 9:00-10:30 AM",
            "capacity": 30,
            "course_type": "prompt_engineering",
            "is_enabled": True,
            "is_free": True,
            "price": 0.0
        },
        {
            "class_code": "PE-2025W-102",
            "instructor_ids": [teacher_instructor_ids[0]] if teacher_instructor_ids else [],
            "title": "Advanced Prompt Engineering & A/B Testing",
            "description": "Advanced techniques in prompt engineering with focus on A/B testing, chain-of-thought prompting, and few-shot learning.",
            "semester": "Winter 2025",
            "start_date": "2025-01-15",
            "end_date": "2025-03-20",
            "schedule": "Tue/Thu 2:00-3:30 PM",
            "capacity": 25,
            "course_type": "prompt_engineering",
            "is_enabled": True,
            "is_free": True,
            "price": 0.0
        },
        {
            "class_code": "ETH-2025W-101",
            "instructor_ids": [teacher_instructor_ids[1]] if len(teacher_instructor_ids) > 1 else teacher_instructor_ids[:1],
            "title": "AI Ethics & Professional Responsibility",
            "description": "Explore ethical considerations in AI development, including bias, fairness, transparency, and accountability.",
            "semester": "Winter 2025",
            "start_date": "2025-01-17",
            "end_date": "2025-03-22",
            "schedule": "Wed/Fri 10:00-11:30 AM",
            "capacity": 40,
            "course_type": "ethics_certificate",
            "is_enabled": True,
            "is_free": False,
            "price": 20.0
        },
        {
            "class_code": "AA-2025W-101",
            "instructor_ids": [teacher_instructor_ids[2]] if len(teacher_instructor_ids) > 2 else teacher_instructor_ids[:1],
            "title": "Introduction to Agentic AI Systems",
            "description": "Build autonomous AI agents and multi-agent systems using modern frameworks and techniques.",
            "semester": "Winter 2025",
            "start_date": "2025-01-16",
            "end_date": "2025-03-21",
            "schedule": "Mon/Wed 1:00-2:30 PM",
            "capacity": 20,
            "course_type": "agentic_ai",
            "is_enabled": True,
            "is_free": True,
            "price": 0.0
        }
    ]
    
    created_classes = []
    for cls in demo_classes:
        # Check if already exists
        existing = next((c for c in classes_data.get('classes', []) if c['class_code'] == cls['class_code']), None)
        if existing:
            created_classes.append(existing)
            continue
        
        # Create new class
        class_id = generate_id('demo_class', classes_data.get('classes', []))
        new_class = {
            "class_id": class_id,
            **cls,
            "created_at": datetime.now().isoformat(),
            "payment_url": "",
            "payment_email": "finance@skillpilot.edu",
            "preview_description": cls['description'],
            "preview_toc": [],
            "preview_image": ""
        }
        classes_data.setdefault('classes', []).append(new_class)
        classes_data['class_counter'] = classes_data.get('class_counter', 0) + 1
        created_classes.append(new_class)
    
    save_json(CLASSES_FILE, classes_data)
    return created_classes

def create_demo_enrollments(students, classes):
    """Create demo enrollments with varied statuses"""
    enrollments_data = load_json(ENROLLMENTS_FILE)
    
    # Enroll students in classes with varied statuses
    for cls in classes:
        # Randomly select 5-8 students for each class
        num_students = random.randint(5, min(8, len(students)))
        enrolled_students = random.sample(students, num_students)
        
        for i, student in enumerate(enrolled_students):
            # Check if already enrolled
            existing = next((e for e in enrollments_data.get('enrollments', [])
                           if e['class_id'] == cls['class_id'] and e['student_user_id'] == student['user_id']), None)
            if existing:
                continue
            
            # Determine status (mostly approved for testing)
            if i < num_students - 2:
                status = 'approved'
            elif i == num_students - 1:
                status = 'requested'
            else:
                status = random.choice(['approved', 'blocked'])
            
            enrollment_id = generate_id('demo_enroll', enrollments_data.get('enrollments', []))
            days_ago = random.randint(20, 60)
            requested_at = (datetime.now() - timedelta(days=days_ago)).isoformat()
            
            new_enrollment = {
                "enrollment_id": enrollment_id,
                "class_id": cls['class_id'],
                "student_user_id": student['user_id'],
                "status": status,
                "request_type": "student_request",
                "requested_at": requested_at,
                "approved_at": requested_at if status == 'approved' else None,
                "approved_by": "demo_teacher" if status == 'approved' else None
            }
            
            if status == 'blocked':
                new_enrollment['blocked_at'] = (datetime.now() - timedelta(days=random.randint(1, 10))).isoformat()
                new_enrollment['blocked_by'] = 'demo_teacher'
            
            enrollments_data.setdefault('enrollments', []).append(new_enrollment)
    
    save_json(ENROLLMENTS_FILE, enrollments_data)
    return enrollments_data.get('enrollments', [])

def create_demo_exams(classes):
    """Create demo exams for each class"""
    exams_data = load_json(CLASS_EXAMS_FILE)
    
    exam_questions = {
        "prompt_engineering": [
            {
                "question_text": "What is the primary goal of prompt engineering?",
                "options": {"A": "Writing code", "B": "Optimizing AI model responses", "C": "Database design", "D": "Network security"},
                "correct_answer": "B",
                "points": 10.0
            },
            {
                "question_text": "Which technique helps AI models provide step-by-step reasoning?",
                "options": {"A": "Zero-shot prompting", "B": "Chain-of-thought prompting", "C": "Random sampling", "D": "Batch processing"},
                "correct_answer": "B",
                "points": 10.0
            },
            {
                "question_text": "What does 'few-shot learning' refer to in prompt engineering?",
                "options": {"A": "Using multiple AI models", "B": "Providing examples in the prompt", "C": "Short prompts only", "D": "Rapid testing"},
                "correct_answer": "B",
                "points": 10.0
            },
            {
                "question_text": "What is A/B testing in the context of prompts?",
                "options": {"A": "Testing two different prompts to compare results", "B": "Using alphabet ordering", "C": "Binary classification", "D": "API benchmarking"},
                "correct_answer": "A",
                "points": 10.0
            },
            {
                "question_text": "Which model is best suited for creative writing tasks?",
                "options": {"A": "GPT-4", "B": "DALL-E", "C": "Whisper", "D": "CLIP"},
                "correct_answer": "A",
                "points": 10.0
            }
        ],
        "ethics_certificate": [
            {
                "question_text": "What is algorithmic bias?",
                "options": {"A": "Errors in code", "B": "Systematic unfairness in AI outputs", "C": "Slow processing", "D": "Network latency"},
                "correct_answer": "B",
                "points": 10.0
            },
            {
                "question_text": "Which principle ensures AI systems are explainable?",
                "options": {"A": "Efficiency", "B": "Transparency", "C": "Speed", "D": "Scalability"},
                "correct_answer": "B",
                "points": 10.0
            },
            {
                "question_text": "What does 'fairness' mean in AI ethics?",
                "options": {"A": "Equal accuracy across all groups", "B": "Faster processing", "C": "Lower costs", "D": "More features"},
                "correct_answer": "A",
                "points": 10.0
            },
            {
                "question_text": "Why is consent important in AI data collection?",
                "options": {"A": "Legal compliance only", "B": "Respecting individual autonomy and privacy", "C": "Faster processing", "D": "Better accuracy"},
                "correct_answer": "B",
                "points": 10.0
            }
        ],
        "agentic_ai": [
            {
                "question_text": "What defines an autonomous AI agent?",
                "options": {"A": "Fast processing", "B": "Ability to act independently toward goals", "C": "Large model size", "D": "Cloud deployment"},
                "correct_answer": "B",
                "points": 10.0
            },
            {
                "question_text": "In multi-agent systems, what is 'emergence'?",
                "options": {"A": "Fast startup", "B": "Complex behaviors arising from agent interactions", "C": "Error handling", "D": "System logging"},
                "correct_answer": "B",
                "points": 10.0
            },
            {
                "question_text": "What is a key challenge in agentic AI?",
                "options": {"A": "Storage space", "B": "Balancing autonomy with safety", "C": "Color schemes", "D": "Font selection"},
                "correct_answer": "B",
                "points": 10.0
            }
        ]
    }
    
    for cls in classes:
        course_type = cls.get('course_type', 'prompt_engineering')
        questions_pool = exam_questions.get(course_type, exam_questions['prompt_engineering'])
        
        # Create 2 exams per class
        for exam_num in range(1, 3):
            exam_id = f"exam_{cls['class_id']}_quiz{exam_num}"
            
            # Check if already exists
            existing = next((e for e in exams_data.get('exams', []) if e['exam_id'] == exam_id), None)
            if existing:
                continue
            
            # Select random questions
            num_questions = min(random.randint(4, 6), len(questions_pool))
            selected_questions = random.sample(questions_pool, num_questions)
            
            # Add question numbers
            formatted_questions = []
            for i, q in enumerate(selected_questions, 1):
                formatted_questions.append({
                    "question_number": str(i),
                    **q
                })
            
            total_points = sum(q['points'] for q in formatted_questions)
            uploaded_at = (datetime.now() - timedelta(days=random.randint(10, 30))).isoformat()
            
            new_exam = {
                "exam_id": exam_id,
                "class_id": cls['class_id'],
                "questions": formatted_questions,
                "total_points": total_points,
                "uploaded_by": cls['instructor_ids'][0] if cls.get('instructor_ids') else 'demo_teacher',
                "uploaded_at": uploaded_at,
                "is_active": True
            }
            
            exams_data.setdefault('exams', []).append(new_exam)
    
    save_json(CLASS_EXAMS_FILE, exams_data)
    return exams_data.get('exams', [])

def create_demo_exam_submissions(enrollments, exams):
    """Create exam submissions with bell-curve distribution"""
    submissions_data = load_json(CLASS_EXAM_SUBMISSIONS_FILE)
    
    # Score distribution (bell curve):
    # 10% high (90-100%), 40% good (70-89%), 30% average (50-69%), 20% failing (30-49%)
    score_ranges = [
        (90, 100, 0.10),  # High performers
        (70, 89, 0.40),   # Good performers
        (50, 69, 0.30),   # Average performers
        (30, 49, 0.20)    # Struggling students
    ]
    
    for exam in exams:
        # Get approved enrollments for this class
        class_enrollments = [e for e in enrollments 
                            if e['class_id'] == exam['class_id'] and e['status'] == 'approved']
        
        if not class_enrollments:
            continue
        
        # 80% of enrolled students submit
        num_submitters = int(len(class_enrollments) * 0.8)
        submitters = random.sample(class_enrollments, num_submitters)
        
        for enrollment in submitters:
            submission_id = f"sub_{exam['exam_id']}_{enrollment['student_user_id']}"
            
            # Check if already exists
            existing = next((s for s in submissions_data.get('submissions', []) 
                           if s['submission_id'] == submission_id), None)
            if existing:
                continue
            
            # Determine score range based on distribution
            rand = random.random()
            cumulative = 0
            for min_pct, max_pct, probability in score_ranges:
                cumulative += probability
                if rand <= cumulative:
                    score_percentage = random.randint(min_pct, max_pct)
                    break
            else:
                score_percentage = random.randint(50, 70)  # Fallback
            
            # Calculate actual score
            total_points = exam['total_points']
            score = (score_percentage / 100.0) * total_points
            score = round(score, 2)
            
            # Generate answers
            answers = {}
            correct_count = 0
            for q in exam['questions']:
                q_num = q['question_number']
                # Probability of correct answer based on score percentage
                if random.random() < (score_percentage / 100.0):
                    answers[q_num] = q['correct_answer']
                    correct_count += 1
                else:
                    # Pick wrong answer
                    options = list(q['options'].keys())
                    options.remove(q['correct_answer'])
                    answers[q_num] = random.choice(options)
            
            # Submit between 1-15 days ago
            submitted_at = (datetime.now() - timedelta(days=random.randint(1, 15))).isoformat()
            
            new_submission = {
                "submission_id": submission_id,
                "exam_id": exam['exam_id'],
                "class_id": exam['class_id'],
                "student_user_id": enrollment['student_user_id'],
                "answers": answers,
                "score": score,
                "total_points": total_points,
                "percentage": score_percentage,
                "submitted_at": submitted_at,
                "graded_at": submitted_at
            }
            
            submissions_data.setdefault('submissions', []).append(new_submission)
    
    save_json(CLASS_EXAM_SUBMISSIONS_FILE, submissions_data)
    return submissions_data.get('submissions', [])

def main():
    """Main seeding function"""
    print("🌱 Starting SkillPilot Demo Data Seeding...")
    print("=" * 50)
    
    print("\n1️⃣  Creating demo teachers...")
    teachers = create_demo_teachers()
    print(f"   Created/verified {len(teachers)} teachers")
    
    print("\n2️⃣  Creating demo students...")
    students = create_demo_students()
    print(f"   Created/verified {len(students)} students")
    
    print("\n3️⃣  Creating demo classes...")
    classes = create_demo_classes(teachers)
    print(f"   Created/verified {len(classes)} classes")
    
    print("\n4️⃣  Creating demo enrollments...")
    enrollments = create_demo_enrollments(students, classes)
    print(f"   Created/verified {len(enrollments)} enrollments")
    
    print("\n5️⃣  Creating demo exams...")
    exams = create_demo_exams(classes)
    print(f"   Created/verified {len(exams)} exams")
    
    print("\n6️⃣  Creating demo exam submissions (with bell-curve distribution)...")
    submissions = create_demo_exam_submissions(enrollments, exams)
    print(f"   Created/verified {len(submissions)} submissions")
    
    print("\n" + "=" * 50)
    print("✅ Demo data seeding completed!")
    print("\n📊 Summary:")
    print(f"   - Teachers: {len(teachers)}")
    print(f"   - Students: {len(students)}")
    print(f"   - Classes: {len(classes)}")
    print(f"   - Enrollments: {len(enrollments)}")
    print(f"   - Exams: {len(exams)}")
    print(f"   - Submissions: {len(submissions)}")
    print("\n🔑 Demo Login Credentials:")
    print("   Teachers: demo_teacher1 / demo_teacher2 / demo_teacher3 (password: teacher123)")
    print("   Students: demo_student1 through demo_student8 (password: student123)")
    print("   Admin: admin (password: admin123)")

if __name__ == "__main__":
    main()
