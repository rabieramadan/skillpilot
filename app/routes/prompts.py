from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import json
import os
from pathlib import Path
import uuid

prompts_bp = Blueprint('prompts', __name__)

def get_prompts_db_path():
    return Path(__file__).parent.parent.parent / 'prompts_library.json'

def load_prompts_db():
    db_path = get_prompts_db_path()
    if db_path.exists():
        with open(db_path, 'r') as f:
            return json.load(f)
    return {"prompts": [], "categories": ["General", "Analysis", "Coding", "Creative", "Teaching"]}

def save_prompts_db(db):
    db_path = get_prompts_db_path()
    with open(db_path, 'w') as f:
        json.dump(db, f, indent=2)

@prompts_bp.route('/library', methods=['GET'])
def get_prompts_library():
    """Get all saved prompts"""
    db = load_prompts_db()
    category = request.args.get('category')
    
    if category:
        filtered = [p for p in db['prompts'] if p.get('category') == category]
        return jsonify({'prompts': filtered, 'categories': db['categories']})
    
    return jsonify(db)

@prompts_bp.route('/library', methods=['POST'])
def save_prompt():
    """Save a new prompt to library"""
    try:
        data = request.get_json()
        db = load_prompts_db()
        
        prompt = {
            'id': str(uuid.uuid4()),
            'title': data.get('title', 'Untitled Prompt'),
            'content': data.get('content'),
            'category': data.get('category', 'General'),
            'description': data.get('description', ''),
            'tags': data.get('tags', []),
            'model': data.get('model'),
            'parameters': data.get('parameters', {}),
            'created_at': datetime.now().isoformat(),
            'created_by': data.get('user', 'anonymous'),
            'rating': 0,
            'use_count': 0
        }
        
        db['prompts'].append(prompt)
        save_prompts_db(db)
        
        return jsonify({'success': True, 'prompt': prompt})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@prompts_bp.route('/library/<prompt_id>', methods=['PUT'])
def update_prompt(prompt_id):
    """Update an existing prompt"""
    try:
        data = request.get_json()
        db = load_prompts_db()
        
        for i, prompt in enumerate(db['prompts']):
            if prompt['id'] == prompt_id:
                db['prompts'][i].update({
                    'title': data.get('title', prompt['title']),
                    'content': data.get('content', prompt['content']),
                    'category': data.get('category', prompt['category']),
                    'description': data.get('description', prompt['description']),
                    'tags': data.get('tags', prompt['tags']),
                    'updated_at': datetime.now().isoformat()
                })
                save_prompts_db(db)
                return jsonify({'success': True, 'prompt': db['prompts'][i]})
        
        return jsonify({'error': 'Prompt not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@prompts_bp.route('/library/<prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    """Delete a prompt"""
    try:
        db = load_prompts_db()
        db['prompts'] = [p for p in db['prompts'] if p['id'] != prompt_id]
        save_prompts_db(db)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@prompts_bp.route('/library/<prompt_id>/use', methods=['POST'])
def increment_use_count(prompt_id):
    """Increment use count for a prompt"""
    try:
        db = load_prompts_db()
        for prompt in db['prompts']:
            if prompt['id'] == prompt_id:
                prompt['use_count'] = prompt.get('use_count', 0) + 1
                save_prompts_db(db)
                return jsonify({'success': True, 'use_count': prompt['use_count']})
        return jsonify({'error': 'Prompt not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@prompts_bp.route('/library/<prompt_id>/rate', methods=['POST'])
def rate_prompt(prompt_id):
    """Rate a prompt"""
    try:
        data = request.get_json()
        rating = data.get('rating', 0)
        
        db = load_prompts_db()
        for prompt in db['prompts']:
            if prompt['id'] == prompt_id:
                prompt['rating'] = rating
                save_prompts_db(db)
                return jsonify({'success': True, 'rating': rating})
        return jsonify({'error': 'Prompt not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@prompts_bp.route('/suggestions', methods=['POST'])
def get_prompt_suggestions():
    """Get AI-powered prompt suggestions"""
    try:
        data = request.get_json()
        task = data.get('task', '')
        context = data.get('context', '')
        
        # Which provider writes the suggestions. Set in the app: block of
        # config.yaml, editable from Admin > Prompt Engineering Settings.
        from app.services import model_registry as registry
        suggestion_model = registry.get_app_setting(
            'prompt_suggestion_provider', 'openai')
        
        # Use AI to generate suggestions
        suggestions = generate_ai_prompt_suggestions(task, context, suggestion_model)
        
        return jsonify({'suggestions': suggestions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_ai_prompt_suggestions(task, context, model='openai'):
    """Generate AI-powered prompt improvement suggestions"""
    try:
        from app.services.ai_service import AIService
        from config.config import Config
        
        if not task:
            return [{
                'type': 'error',
                'title': 'Empty Prompt',
                'message': 'Please provide a task or question'
            }]
        
        # Create a meta-prompt for the AI to analyze the user's prompt
        meta_prompt = f"""You are a prompt engineering expert. Analyze this user prompt and provide 3-5 specific, actionable suggestions to improve it.

User's Prompt: "{task}"
{f'Context: {context}' if context else ''}

Provide suggestions in this exact JSON format:
[
  {{
    "type": "tip",
    "title": "Brief Title",
    "message": "Explanation of the suggestion",
    "example": "Improved version of the prompt"
  }}
]

Focus on: clarity, specificity, role assignment, output format, examples, and advanced techniques like chain-of-thought."""

        # Get AI suggestions
        ai_service = AIService()
        config = Config()
        
        # Get API key for the selected model
        api_key = getattr(config, f'{model.upper()}_API_KEY', None)
        
        if not api_key:
            # Fallback to rule-based suggestions if no API key
            return generate_prompt_suggestions(task, context)
        
        response = ai_service.chat(model, meta_prompt, api_key)
        
        # Parse AI response
        if 'text' in response:
            import json
            import re
            
            # Extract JSON from response
            text = response['text']
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            
            if json_match:
                suggestions = json.loads(json_match.group())
                return suggestions
        
        # Fallback to rule-based if parsing fails
        return generate_prompt_suggestions(task, context)
        
    except Exception as e:
        print(f"Error generating AI suggestions: {e}")
        # Fallback to rule-based suggestions
        return generate_prompt_suggestions(task, context)


def generate_prompt_suggestions(task, context):
    """Generate prompt improvement suggestions"""
    suggestions = []
    
    # Check for common improvements
    if not task:
        return [{
            'type': 'error',
            'title': 'Empty Prompt',
            'message': 'Please provide a task or question'
        }]
    
    # Length check
    if len(task) < 20:
        suggestions.append({
            'type': 'warning',
            'title': 'Too Brief',
            'message': 'Consider adding more details for better results',
            'example': f'{task}. Please provide a detailed explanation with examples and step-by-step instructions.'
        })
    
    # Check for role assignment
    if not any(word in task.lower() for word in ['you are', 'act as', 'imagine you', 'role']):
        suggestions.append({
            'type': 'tip',
            'title': 'Add Role Assignment',
            'message': 'Define a role for better context',
            'example': f'You are an expert educator. {task}'
        })
    
    # Check for output format
    if not any(word in task.lower() for word in ['format', 'structure', 'list', 'steps', 'table']):
        suggestions.append({
            'type': 'tip',
            'title': 'Specify Output Format',
            'message': 'Define the desired output structure',
            'example': f'{task}\n\nProvide the response in a structured format with clear sections.'
        })
    
    # Check for examples
    if not any(word in task.lower() for word in ['example', 'for instance', 'such as']):
        suggestions.append({
            'type': 'tip',
            'title': 'Request Examples',
            'message': 'Ask for examples to enhance understanding',
            'example': f'{task} Please include practical examples to illustrate your points.'
        })
    
    # Advanced techniques
    if len(task) > 50:
        suggestions.append({
            'type': 'advanced',
            'title': 'Use Chain-of-Thought',
            'message': 'For complex tasks, ask the AI to think step-by-step',
            'example': f'{task}\n\nLet\'s approach this step by step:\n1. First, analyze...\n2. Then, consider...'
        })
    
    return suggestions if suggestions else [{
        'type': 'success',
        'title': 'Good Prompt',
        'message': 'Your prompt looks well-structured!'
    }]
