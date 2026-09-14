import json
import hashlib
import random
from datetime import datetime, timedelta

# Generate realistic demo data for all features

# ============= DEMO STUDENTS WITH CERTIFICATES =============
demo_students = [
    {"id": "demo_student_1", "name": "Alice Williams", "email": "alice.w@student.skillpilot.edu", "phone": "+1-555-1200"},
    {"id": "demo_student_2", "name": "Bob Chen", "email": "bob.c@student.skillpilot.edu", "phone": "+1-555-1201"},
    {"id": "demo_student_3", "name": "Charlie Davis", "email": "charlie.d@student.skillpilot.edu", "phone": "+1-555-1202"},
    {"id": "demo_student_4", "name": "Diana Martinez", "email": "diana.m@student.skillpilot.edu", "phone": "+1-555-1203"},
    {"id": "demo_student_5", "name": "Ethan Brown", "email": "ethan.b@student.skillpilot.edu", "phone": "+968-9555-1204"},
    {"id": "demo_student_6", "name": "Fatima Al-Hassan", "email": "fatima.h@student.skillpilot.edu", "phone": "+968-9555-1205"},
    {"id": "demo_student_7", "name": "George Wilson", "email": "george.w@student.skillpilot.edu", "phone": "+1-555-1206"},
    {"id": "demo_student_8", "name": "Hannah Lee", "email": "hannah.l@student.skillpilot.edu", "phone": "+1-555-1207"},
]

# ============= EXIT EXAM DATA WITH DEMO RESULTS =============
exit_exam_data = {"users": [], "certificate_counter": 2000}

correct_answers = [
    "A piece of text (word, part of word, or character) that the model processes",
    "A parameter controlling randomness: lower = more focused, higher = more creative",
    "Instruction, context, input data, and output format",
    "To instruct the AI to adopt a specific role or expertise (e.g., 'Act as a data scientist')",
    "Asking AI questions without providing any examples",
    "Providing a few examples before asking the AI to perform a task",
    "Asking AI to show its reasoning process step-by-step",
    "Context or background information about the task",
    "Gradually refining prompts based on previous AI responses to improve results",
    "Start with a simple, clear prompt and refine based on the response",
    "The maximum amount of text (tokens) an AI model can process at once",
    "Being clear, specific, providing context, and specifying the desired output format",
    "They help clearly separate different parts of the input and prevent confusion",
    "The task/instruction and the desired output format",
    "Initial instructions that set the AI's behavior and role for the entire conversation",
    "Temperature 0.7-0.9 for more creative and diverse output",
    "The clear directive telling the AI what to do (e.g., 'Translate', 'Summarize', 'Explain')",
    "Refine and clarify your prompt with more specific instructions or examples",
    "Role-based (Persona) pattern",
    "It helps the AI understand the background and constraints to generate more relevant responses"
]

# Create exam results for demo students
scores = [95, 85, 100, 70, 90, 80, 55, 65]
for i, student in enumerate(demo_students):
    score_pct = scores[i]
    correct_count = int(score_pct * 20 / 100)
    passed = score_pct >= 60
    
    exam_entry = {
        "id": f"2025112{i+1}100000",
        "timestamp": (datetime.now() - timedelta(days=random.randint(5, 30))).isoformat(),
        "user_info": {
            "user_id": student["id"],
            "name": student["name"],
            "email": student["email"],
            "username": f"demo_student{i+1}",
            "organization": "SkillPilot University"
        },
        "answers": correct_answers[:correct_count] + ["Wrong answer"] * (20 - correct_count),
        "score": score_pct / 10,
        "percentage": score_pct,
        "correct_count": correct_count,
        "total_questions": 20,
        "pass_status": "passed" if passed else "failed",
        "analysis": {
            "evaluation": f"Score: {score_pct}%. " + ("Excellent performance!" if score_pct >= 90 else "Good understanding." if score_pct >= 70 else "Needs improvement."),
            "recommendations": ["Continue practicing", "Review core concepts"],
            "focus_areas": ["Advanced techniques", "Real-world applications"]
        },
        "certificate_status": "pass" if passed else "fail",
        "can_retake": not passed,
        "admin_override": False,
        "certificate_number": f"AICA-2025-{2000 + i}" if passed else None
    }
    exit_exam_data["users"].append(exam_entry)

# ============= SURVEY DATA =============
survey_data = {"users": [], "certificate_counter": 3000}

survey_questions_template = [
    {"question": "How would you rate the course content?", "options": ["Excellent", "Good", "Average", "Poor"]},
    {"question": "How effective was the instructor?", "options": ["Very Effective", "Effective", "Neutral", "Not Effective"]},
    {"question": "Would you recommend this course?", "options": ["Definitely", "Probably", "Maybe", "No"]},
    {"question": "How was the course difficulty?", "options": ["Just Right", "Too Easy", "Too Hard", "Varies"]},
    {"question": "Rate the learning materials", "options": ["Excellent", "Good", "Average", "Poor"]},
]

for i, student in enumerate(demo_students[:6]):
    survey_entry = {
        "id": f"survey_2025_{i+1}",
        "timestamp": (datetime.now() - timedelta(days=random.randint(1, 20))).isoformat(),
        "user_info": {
            "user_id": student["id"],
            "name": student["name"],
            "email": student["email"],
            "username": f"demo_student{i+1}",
            "organization": "SkillPilot University"
        },
        "answers": [random.choice(q["options"]) for q in survey_questions_template],
        "completed": True
    }
    survey_data["users"].append(survey_entry)

# ============= CLASS EXAM SUBMISSIONS =============
class_exam_submissions = {"submissions": []}

# Create submissions for demo classes
for class_num in range(1, 5):
    class_id = f"demo_class_{class_num}"
    for i, student in enumerate(demo_students):
        if random.random() > 0.3:  # 70% chance of submission
            score = random.randint(40, 100)
            total_points = 100
            submission = {
                "submission_id": f"sub_{class_id}_{student['id']}",
                "class_id": class_id,
                "student_user_id": student["id"],
                "student_name": student["name"],
                "answers": {f"q{j}": random.choice(["A", "B", "C", "D"]) for j in range(1, 11)},
                "score": score,
                "total_points": total_points,
                "percentage": score,
                "submitted_at": (datetime.now() - timedelta(days=random.randint(1, 15), hours=random.randint(0, 12))).isoformat(),
                "graded": True
            }
            class_exam_submissions["submissions"].append(submission)

# ============= CLASS EXAMS =============
class_exams = {"exams": []}

for class_num in range(1, 5):
    class_id = f"demo_class_{class_num}"
    exam = {
        "exam_id": f"exam_{class_id}",
        "class_id": class_id,
        "title": f"Final Exam - Course {class_num}",
        "questions": [
            {"id": f"q{j}", "question": f"Sample question {j}", "options": ["A", "B", "C", "D"], "correct": random.choice(["A", "B", "C", "D"]), "points": 10}
            for j in range(1, 11)
        ],
        "total_points": 100,
        "passing_score": 50,
        "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
        "created_by": f"demo_inst_{(class_num % 3) + 1}"
    }
    class_exams["exams"].append(exam)

# ============= SAVE ALL DATA =============
with open('users_exit_exam_data.json', 'w') as f:
    json.dump(exit_exam_data, f, indent=2)
print("✓ Updated users_exit_exam_data.json with demo exam results")

with open('users_survey_data.json', 'w') as f:
    json.dump(survey_data, f, indent=2)
print("✓ Updated users_survey_data.json with demo survey responses")

with open('class_exam_submissions.json', 'w') as f:
    json.dump(class_exam_submissions, f, indent=2)
print("✓ Updated class_exam_submissions.json with demo submissions")

with open('class_exams.json', 'w') as f:
    json.dump(class_exams, f, indent=2)
print("✓ Updated class_exams.json with demo exams")

print("\n✅ All demo data generated successfully!")
