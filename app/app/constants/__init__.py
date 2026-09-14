"""Constants module for SkillPilot"""
from .feedback_template import (
    FEEDBACK_TEMPLATE_VERSION,
    FEEDBACK_TEMPLATE_NAME,
    FEEDBACK_TEMPLATE_NAME_AR,
    STANDARD_FEEDBACK_QUESTIONS,
    get_standard_feedback_template,
    get_feedback_questions_for_survey
)

__all__ = [
    'FEEDBACK_TEMPLATE_VERSION',
    'FEEDBACK_TEMPLATE_NAME',
    'FEEDBACK_TEMPLATE_NAME_AR',
    'STANDARD_FEEDBACK_QUESTIONS',
    'get_standard_feedback_template',
    'get_feedback_questions_for_survey'
]
