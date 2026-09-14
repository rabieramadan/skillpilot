"""
Auto Survey Service - Automatically creates exit surveys when courses are created
Uses the standardized feedback template for consistent evaluation across all courses.
"""
import uuid
from datetime import datetime


def create_exit_survey_for_course(db, course_id, course_title):
    """
    Automatically create an exit survey for a newly created course.
    Uses the standard feedback template with 12 bilingual questions.

    Args:
        db: Database session
        course_id: The ID of the newly created course
        course_title: Title of the course (for survey naming)

    Returns:
        Survey object if created successfully, None otherwise
    """
    try:
        from app.models import Survey, SurveyQuestion
        from app.constants.feedback_template import get_feedback_questions_for_survey

        # Create the exit survey
        survey_id = str(uuid.uuid4())
        survey = Survey(
            id=survey_id,
            course_id=course_id,
            title=f"Exit Survey - {course_title}",
            description=f"Training evaluation survey for {course_title}. Please provide your feedback to help us improve future courses.",
            survey_type='exit_survey',
            is_required=True,
            is_published=True,
            created_at=datetime.utcnow()
        )
        db.add(survey)
        
        # Add all standard feedback questions
        feedback_questions = get_feedback_questions_for_survey()
        for q in feedback_questions:
            question = SurveyQuestion(
                id=str(uuid.uuid4()),
                survey_id=survey_id,
                question_text=q['question_text'],
                question_text_ar=q['question_text_ar'],
                question_type=q['question_type'],
                options=q['options'],
                options_ar=q['options_ar'],
                is_required=q['is_required'],
                order_index=q['order_index'],
                is_ai_generated=False
            )
            db.add(question)
        
        print(f"[Auto Survey] Created exit survey '{survey.title}' with {len(feedback_questions)} questions for course {course_id}")
        return survey
        
    except Exception as e:
        print(f"[Auto Survey] Error creating exit survey: {e}")
        return None
