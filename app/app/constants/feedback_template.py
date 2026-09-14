"""
Fixed Feedback Survey Template - Standardized for All Courses
This template is immutable and applies uniformly across the entire system.
Version: 1.2 - Includes rating questions and text-based feedback questions
"""

FEEDBACK_TEMPLATE_VERSION = "1.2"
FEEDBACK_TEMPLATE_NAME = "Standard Course Feedback Survey"
FEEDBACK_TEMPLATE_NAME_AR = "استبيان التقييم الموحد للدورات"

STANDARD_FEEDBACK_QUESTIONS = [
    {
        "id": "FB001",
        "category": "course_materials",
        "category_en": "Course Materials",
        "category_ar": "مواد الدورة",
        "question_en": "How would you rate the quality of the course materials?",
        "question_ar": "كيف تقيم جودة مواد الدورة؟",
        "type": "rating",
        "scale_label_en": "1 = Poor, 5 = Excellent",
        "scale_label_ar": "1 = ضعيف، 5 = ممتاز",
        "options_en": ["1 - Poor", "2 - Fair", "3 - Good", "4 - Very Good", "5 - Excellent"],
        "options_ar": ["1 - ضعيف", "2 - مقبول", "3 - جيد", "4 - جيد جداً", "5 - ممتاز"],
        "required": True,
        "order": 1
    },
    {
        "id": "FB002",
        "category": "course_materials",
        "category_en": "Course Materials",
        "category_ar": "مواد الدورة",
        "question_en": "The course content was well-organized and easy to follow.",
        "question_ar": "كان محتوى الدورة منظماً جيداً وسهل المتابعة.",
        "type": "likert",
        "scale_label_en": "1 = Strongly Disagree, 5 = Strongly Agree",
        "scale_label_ar": "1 = أرفض بشدة، 5 = أوافق بشدة",
        "options_en": ["1 - Strongly Disagree", "2 - Disagree", "3 - Neutral", "4 - Agree", "5 - Strongly Agree"],
        "options_ar": ["1 - أرفض بشدة", "2 - أرفض", "3 - محايد", "4 - أوافق", "5 - أوافق بشدة"],
        "required": True,
        "order": 2
    },
    {
        "id": "FB003",
        "category": "course_materials",
        "category_en": "Course Materials",
        "category_ar": "مواد الدورة",
        "question_en": "The learning resources (videos, documents, exercises) were helpful.",
        "question_ar": "كانت مصادر التعلم (الفيديوهات، المستندات، التمارين) مفيدة.",
        "type": "likert",
        "scale_label_en": "1 = Strongly Disagree, 5 = Strongly Agree",
        "scale_label_ar": "1 = أرفض بشدة، 5 = أوافق بشدة",
        "options_en": ["1 - Strongly Disagree", "2 - Disagree", "3 - Neutral", "4 - Agree", "5 - Strongly Agree"],
        "options_ar": ["1 - أرفض بشدة", "2 - أرفض", "3 - محايد", "4 - أوافق", "5 - أوافق بشدة"],
        "required": True,
        "order": 3
    },
    {
        "id": "FB004",
        "category": "teacher",
        "category_en": "Instructor Evaluation",
        "category_ar": "تقييم المدرب",
        "question_en": "How would you rate the instructor's knowledge of the subject?",
        "question_ar": "كيف تقيم معرفة المدرب بالموضوع؟",
        "type": "rating",
        "scale_label_en": "1 = Poor, 5 = Excellent",
        "scale_label_ar": "1 = ضعيف، 5 = ممتاز",
        "options_en": ["1 - Poor", "2 - Fair", "3 - Good", "4 - Very Good", "5 - Excellent"],
        "options_ar": ["1 - ضعيف", "2 - مقبول", "3 - جيد", "4 - جيد جداً", "5 - ممتاز"],
        "required": True,
        "order": 4
    },
    {
        "id": "FB005",
        "category": "teacher",
        "category_en": "Instructor Evaluation",
        "category_ar": "تقييم المدرب",
        "question_en": "The instructor explained concepts clearly and effectively.",
        "question_ar": "شرح المدرب المفاهيم بوضوح وفعالية.",
        "type": "likert",
        "scale_label_en": "1 = Strongly Disagree, 5 = Strongly Agree",
        "scale_label_ar": "1 = أرفض بشدة، 5 = أوافق بشدة",
        "options_en": ["1 - Strongly Disagree", "2 - Disagree", "3 - Neutral", "4 - Agree", "5 - Strongly Agree"],
        "options_ar": ["1 - أرفض بشدة", "2 - أرفض", "3 - محايد", "4 - أوافق", "5 - أوافق بشدة"],
        "required": True,
        "order": 5
    },
    {
        "id": "FB006",
        "category": "teacher",
        "category_en": "Instructor Evaluation",
        "category_ar": "تقييم المدرب",
        "question_en": "The instructor was responsive to questions and provided helpful feedback.",
        "question_ar": "كان المدرب متجاوباً مع الأسئلة وقدم ملاحظات مفيدة.",
        "type": "likert",
        "scale_label_en": "1 = Strongly Disagree, 5 = Strongly Agree",
        "scale_label_ar": "1 = أرفض بشدة، 5 = أوافق بشدة",
        "options_en": ["1 - Strongly Disagree", "2 - Disagree", "3 - Neutral", "4 - Agree", "5 - Strongly Agree"],
        "options_ar": ["1 - أرفض بشدة", "2 - أرفض", "3 - محايد", "4 - أوافق", "5 - أوافق بشدة"],
        "required": True,
        "order": 6
    },
    {
        "id": "FB007",
        "category": "teacher",
        "category_en": "Instructor Evaluation",
        "category_ar": "تقييم المدرب",
        "question_en": "The instructor created an engaging learning environment.",
        "question_ar": "أنشأ المدرب بيئة تعليمية جذابة.",
        "type": "likert",
        "scale_label_en": "1 = Strongly Disagree, 5 = Strongly Agree",
        "scale_label_ar": "1 = أرفض بشدة، 5 = أوافق بشدة",
        "options_en": ["1 - Strongly Disagree", "2 - Disagree", "3 - Neutral", "4 - Agree", "5 - Strongly Agree"],
        "options_ar": ["1 - أرفض بشدة", "2 - أرفض", "3 - محايد", "4 - أوافق", "5 - أوافق بشدة"],
        "required": True,
        "order": 7
    },
    {
        "id": "FB008",
        "category": "venue",
        "category_en": "Training Venue",
        "category_ar": "مكان التدريب",
        "question_en": "How would you rate the training venue/facility?",
        "question_ar": "كيف تقيم مكان/منشأة التدريب؟",
        "type": "rating",
        "scale_label_en": "1 = Poor, 5 = Excellent",
        "scale_label_ar": "1 = ضعيف، 5 = ممتاز",
        "options_en": ["1 - Poor", "2 - Fair", "3 - Good", "4 - Very Good", "5 - Excellent"],
        "options_ar": ["1 - ضعيف", "2 - مقبول", "3 - جيد", "4 - جيد جداً", "5 - ممتاز"],
        "required": True,
        "order": 8
    },
    {
        "id": "FB009",
        "category": "venue",
        "category_en": "Training Venue",
        "category_ar": "مكان التدريب",
        "question_en": "The training room was comfortable and conducive to learning.",
        "question_ar": "كانت قاعة التدريب مريحة ومناسبة للتعلم.",
        "type": "likert",
        "scale_label_en": "1 = Strongly Disagree, 5 = Strongly Agree",
        "scale_label_ar": "1 = أرفض بشدة، 5 = أوافق بشدة",
        "options_en": ["1 - Strongly Disagree", "2 - Disagree", "3 - Neutral", "4 - Agree", "5 - Strongly Agree"],
        "options_ar": ["1 - أرفض بشدة", "2 - أرفض", "3 - محايد", "4 - أوافق", "5 - أوافق بشدة"],
        "required": True,
        "order": 9
    },
    {
        "id": "FB010",
        "category": "venue",
        "category_en": "Training Venue",
        "category_ar": "مكان التدريب",
        "question_en": "The technical equipment (computers, projectors, internet) worked well.",
        "question_ar": "عملت المعدات التقنية (الحواسيب، أجهزة العرض، الإنترنت) بشكل جيد.",
        "type": "likert",
        "scale_label_en": "1 = Strongly Disagree, 5 = Strongly Agree",
        "scale_label_ar": "1 = أرفض بشدة، 5 = أوافق بشدة",
        "options_en": ["1 - Strongly Disagree", "2 - Disagree", "3 - Neutral", "4 - Agree", "5 - Strongly Agree"],
        "options_ar": ["1 - أرفض بشدة", "2 - أرفض", "3 - محايد", "4 - أوافق", "5 - أوافق بشدة"],
        "required": True,
        "order": 10
    },
    {
        "id": "FB011",
        "category": "overall",
        "category_en": "Overall Satisfaction",
        "category_ar": "الرضا العام",
        "question_en": "Overall, how satisfied are you with this training course?",
        "question_ar": "بشكل عام، ما مدى رضاك عن هذه الدورة التدريبية؟",
        "type": "rating",
        "scale_label_en": "1 = Very Dissatisfied, 5 = Very Satisfied",
        "scale_label_ar": "1 = غير راضٍ جداً، 5 = راضٍ جداً",
        "options_en": ["1 - Very Dissatisfied", "2 - Dissatisfied", "3 - Neutral", "4 - Satisfied", "5 - Very Satisfied"],
        "options_ar": ["1 - غير راضٍ جداً", "2 - غير راضٍ", "3 - محايد", "4 - راضٍ", "5 - راضٍ جداً"],
        "required": True,
        "order": 11
    },
    {
        "id": "FB012",
        "category": "overall",
        "category_en": "Overall Satisfaction",
        "category_ar": "الرضا العام",
        "question_en": "Would you recommend this course to others?",
        "question_ar": "هل توصي بهذه الدورة للآخرين؟",
        "type": "likert",
        "scale_label_en": "1 = Definitely Not, 5 = Definitely Yes",
        "scale_label_ar": "1 = بالتأكيد لا، 5 = بالتأكيد نعم",
        "options_en": ["1 - Definitely Not", "2 - Probably Not", "3 - Maybe", "4 - Probably Yes", "5 - Definitely Yes"],
        "options_ar": ["1 - بالتأكيد لا", "2 - على الأرجح لا", "3 - ربما", "4 - على الأرجح نعم", "5 - بالتأكيد نعم"],
        "required": True,
        "order": 12
    },
    {
        "id": "FB013",
        "category": "feedback",
        "category_en": "Open Feedback",
        "category_ar": "ملاحظات مفتوحة",
        "question_en": "What did you like most about this training course?",
        "question_ar": "ما الذي أعجبك أكثر في هذه الدورة التدريبية؟",
        "type": "long_text",
        "scale_label_en": "",
        "scale_label_ar": "",
        "options_en": [],
        "options_ar": [],
        "required": False,
        "order": 13
    },
    {
        "id": "FB014",
        "category": "feedback",
        "category_en": "Open Feedback",
        "category_ar": "ملاحظات مفتوحة",
        "question_en": "What aspects of the training could be improved?",
        "question_ar": "ما الجوانب التي يمكن تحسينها في التدريب؟",
        "type": "long_text",
        "scale_label_en": "",
        "scale_label_ar": "",
        "options_en": [],
        "options_ar": [],
        "required": False,
        "order": 14
    },
    {
        "id": "FB015",
        "category": "feedback",
        "category_en": "Open Feedback",
        "category_ar": "ملاحظات مفتوحة",
        "question_en": "Please share any additional comments or suggestions.",
        "question_ar": "يرجى مشاركة أي تعليقات أو اقتراحات إضافية.",
        "type": "long_text",
        "scale_label_en": "",
        "scale_label_ar": "",
        "options_en": [],
        "options_ar": [],
        "required": False,
        "order": 15
    }
]


def get_standard_feedback_template():
    """
    Returns the fixed, standardized feedback survey template.
    This template is immutable and the same for all courses.
    """
    return {
        "version": FEEDBACK_TEMPLATE_VERSION,
        "name": FEEDBACK_TEMPLATE_NAME,
        "name_ar": FEEDBACK_TEMPLATE_NAME_AR,
        "description": "Standard feedback survey for evaluating course materials, instructor, and training venue. Includes rating scales and open text questions for detailed feedback.",
        "description_ar": "استبيان تقييم موحد لتقييم مواد الدورة والمدرب ومكان التدريب. يتضمن مقاييس التقييم وأسئلة نصية مفتوحة للحصول على ملاحظات تفصيلية.",
        "questions": STANDARD_FEEDBACK_QUESTIONS.copy(),
        "total_questions": len(STANDARD_FEEDBACK_QUESTIONS),
        "categories": [
            {"id": "course_materials", "name_en": "Course Materials", "name_ar": "مواد الدورة", "question_count": 3},
            {"id": "teacher", "name_en": "Instructor Evaluation", "name_ar": "تقييم المدرب", "question_count": 4},
            {"id": "venue", "name_en": "Training Venue", "name_ar": "مكان التدريب", "question_count": 3},
            {"id": "overall", "name_en": "Overall Satisfaction", "name_ar": "الرضا العام", "question_count": 2},
            {"id": "feedback", "name_en": "Open Feedback", "name_ar": "ملاحظات مفتوحة", "question_count": 3}
        ],
        "is_standard_template": True,
        "editable": False
    }


def get_feedback_questions_for_survey():
    """
    Returns the feedback questions formatted for adding to a survey.
    Field names match the SurveyQuestion model and the add-feedback-questions endpoint.
    """
    return [
        {
            "question_text": q["question_en"],
            "question_text_ar": q["question_ar"],
            "question_type": q["type"],
            "options": q["options_en"],
            "options_ar": q["options_ar"],
            "is_required": q["required"],
            "order_index": q["order"],
            "category": q["category"],
            "template_id": q["id"],
            "category_en": q["category_en"],
            "category_ar": q["category_ar"],
            "scale_label_en": q.get("scale_label_en", ""),
            "scale_label_ar": q.get("scale_label_ar", "")
        }
        for q in STANDARD_FEEDBACK_QUESTIONS
    ]
