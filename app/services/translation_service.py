"""
Translation Service for SkillPilot
Uses OpenAI for automatic English <-> Arabic translation
"""

import os
import json
from openai import OpenAI

def get_openai_client():
    """Get OpenAI client with API key"""
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def translate_text(text, source_lang='en', target_lang='ar'):
    """
    Translate text between English and Arabic using OpenAI
    
    Args:
        text: Text to translate
        source_lang: Source language ('en' or 'ar')
        target_lang: Target language ('en' or 'ar')
    
    Returns:
        Translated text or original if translation fails
    """
    if not text or not text.strip():
        return text
    
    client = get_openai_client()
    if not client:
        print("Translation service: No OpenAI API key configured")
        return text
    
    try:
        lang_names = {'en': 'English', 'ar': 'Arabic'}
        source_name = lang_names.get(source_lang, 'English')
        target_name = lang_names.get(target_lang, 'Arabic')
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a professional translator. Translate the following text from {source_name} to {target_name}. Only provide the translation, no explanations or additional text. Maintain the same tone and meaning."
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        translated = response.choices[0].message.content.strip()
        return translated
        
    except Exception as e:
        print(f"Translation error: {e}")
        return text


def translate_to_arabic(text):
    """Translate English text to Arabic"""
    return translate_text(text, source_lang='en', target_lang='ar')


def translate_to_english(text):
    """Translate Arabic text to English"""
    return translate_text(text, source_lang='ar', target_lang='en')


def translate_course_content(title, description=None, source_lang='en'):
    """
    Translate course title and description
    
    Args:
        title: Course title
        description: Course description (optional)
        source_lang: Source language ('en' or 'ar')
    
    Returns:
        dict with translated title and description
    """
    target_lang = 'ar' if source_lang == 'en' else 'en'
    
    result = {
        'title': translate_text(title, source_lang, target_lang) if title else '',
        'description': translate_text(description, source_lang, target_lang) if description else ''
    }
    
    return result


def translate_survey_exam_content(questions, source_lang='en'):
    """
    Translate survey/exam questions and options
    
    Args:
        questions: List of question dicts with 'text' and 'options'
        source_lang: Source language ('en' or 'ar')
    
    Returns:
        List of translated question dicts
    """
    if not questions:
        return []
    
    target_lang = 'ar' if source_lang == 'en' else 'en'
    translated_questions = []
    
    for q in questions:
        translated_q = q.copy()
        
        if 'text' in q:
            translated_q['text_translated'] = translate_text(q['text'], source_lang, target_lang)
        
        if 'question_text' in q:
            translated_q['question_text_translated'] = translate_text(q['question_text'], source_lang, target_lang)
        
        if 'options' in q and isinstance(q['options'], list):
            translated_q['options_translated'] = [
                translate_text(opt, source_lang, target_lang) for opt in q['options']
            ]
        
        translated_questions.append(translated_q)
    
    return translated_questions


def batch_translate(texts, source_lang='en', target_lang='ar'):
    """
    Translate multiple texts at once for efficiency
    
    Args:
        texts: List of texts to translate
        source_lang: Source language
        target_lang: Target language
    
    Returns:
        List of translated texts
    """
    if not texts:
        return []
    
    client = get_openai_client()
    if not client:
        print("Translation service: No OpenAI API key configured")
        return texts
    
    try:
        lang_names = {'en': 'English', 'ar': 'Arabic'}
        source_name = lang_names.get(source_lang, 'English')
        target_name = lang_names.get(target_lang, 'Arabic')
        
        numbered_texts = "\n".join([f"{i+1}. {text}" for i, text in enumerate(texts)])
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a professional translator. Translate each numbered item from {source_name} to {target_name}.
Return ONLY a JSON array of translated strings in the same order.
Example input: "1. Hello\n2. World"
Example output: ["مرحبا", "العالم"]
Only output the JSON array, nothing else."""
                },
                {
                    "role": "user",
                    "content": numbered_texts
                }
            ],
            temperature=0.3,
            max_tokens=4000
        )
        
        result_text = response.choices[0].message.content.strip()
        if result_text.startswith('```'):
            result_text = result_text.split('\n', 1)[1]
            if result_text.endswith('```'):
                result_text = result_text.rsplit('```', 1)[0]
        
        translated = json.loads(result_text)
        
        if len(translated) == len(texts):
            return translated
        else:
            return [translate_text(t, source_lang, target_lang) for t in texts]
            
    except Exception as e:
        print(f"Batch translation error: {e}")
        return [translate_text(t, source_lang, target_lang) for t in texts]


def auto_translate_model_fields(model_instance, fields_mapping):
    """
    Automatically translate model fields
    
    Args:
        model_instance: SQLAlchemy model instance
        fields_mapping: Dict mapping source fields to target fields
                       e.g. {'title': 'title_ar', 'description': 'description_ar'}
    
    Returns:
        Updated model instance
    """
    for source_field, target_field in fields_mapping.items():
        source_value = getattr(model_instance, source_field, None)
        if source_value and not getattr(model_instance, target_field, None):
            translated = translate_to_arabic(source_value)
            setattr(model_instance, target_field, translated)
    
    return model_instance
