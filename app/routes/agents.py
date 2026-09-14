"""
AIACMate Pro - Agentic AI Lab Routes
Handles agent creation, execution, and management
"""

from flask import Blueprint, request, jsonify, session, current_app
from functools import wraps
import json
import os
import uuid
from datetime import datetime
from app.services.ai_service import AIService
import asyncio

agents_bp = Blueprint('agents', __name__, url_prefix='/api/agents')

AGENTS_FILE = 'agents.json'
AGENT_EXECUTIONS_FILE = 'agent_executions.json'

# Model to provider mapping
MODEL_TO_PROVIDER = {
    'gpt-4': 'openai',
    'gpt-4o': 'openai',
    'gpt-4-turbo': 'openai',
    'gpt-3.5-turbo': 'openai',
    'claude-3.5-sonnet': 'claude',
    'claude-3-opus': 'claude',
    'claude-3-sonnet': 'claude',
    'claude-3-haiku': 'claude',
    'gemini-pro': 'gemini',
    'gemini-2.0-flash': 'gemini',
    'gemini-1.5-flash': 'gemini',
    'grok-3': 'grok',
    'grok-3-mini': 'grok',
    'deepseek-chat': 'deepseek',
    'llama-3-70b': 'llama',
    'perplexity-large': 'perplexity',
    'perplexity-small': 'perplexity'
}

def get_api_key_for_provider(provider):
    """Get API key for a given provider"""
    key_map = {
        'openai': 'OPENAI_API_KEY',
        'claude': 'CLAUDE_API_KEY',
        'gemini': 'GEMINI_API_KEY',
        'grok': 'GROK_API_KEY',
        'deepseek': 'DEEPSEEK_API_KEY',
        'llama': 'LLAMA_API_KEY',
        'perplexity': 'PERPLEXITY_API_KEY'
    }
    return current_app.config.get(key_map.get(provider, 'OPENAI_API_KEY'))


def authenticated_required(f):
    """Decorator to require any authenticated user"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') and not session.get('is_admin'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# Data Access Functions
# ============================================

def load_agents():
    """Load agents from JSON file"""
    if os.path.exists(AGENTS_FILE):
        with open(AGENTS_FILE, 'r') as f:
            return json.load(f)
    return {'agents': []}


def save_agents(data):
    """Save agents to JSON file"""
    with open(AGENTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_executions():
    """Load agent executions from JSON file"""
    if os.path.exists(AGENT_EXECUTIONS_FILE):
        with open(AGENT_EXECUTIONS_FILE, 'r') as f:
            return json.load(f)
    return {'executions': []}


def save_executions(data):
    """Save agent executions to JSON file"""
    with open(AGENT_EXECUTIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


# ============================================
# Agent Block Definitions
# ============================================

BLOCK_TYPES = {
    'ai_model': {
        'name': 'AI Model',
        'description': 'Call an AI model with a prompt',
        'inputs': ['prompt'],
        'outputs': ['response'],
        'params': ['model', 'temperature', 'max_tokens']
    },
    'prompt_template': {
        'name': 'Prompt Template',
        'description': 'Create a prompt from a template with variables',
        'inputs': ['variables'],
        'outputs': ['prompt'],
        'params': ['template']
    },
    'variable': {
        'name': 'Variable',
        'description': 'Store and retrieve a value',
        'inputs': [],
        'outputs': ['value'],
        'params': ['name', 'value']
    },
    'condition': {
        'name': 'Condition',
        'description': 'Branch based on a condition',
        'inputs': ['input'],
        'outputs': ['true_path', 'false_path'],
        'params': ['condition_type', 'comparison_value']
    },
    'text_transform': {
        'name': 'Text Transform',
        'description': 'Transform text (uppercase, lowercase, etc.)',
        'inputs': ['text'],
        'outputs': ['result'],
        'params': ['transform_type']
    },
    'output': {
        'name': 'Output',
        'description': 'Display output to user',
        'inputs': ['content'],
        'outputs': [],
        'params': ['label']
    }
}


# ============================================
# Agent Execution Engine
# ============================================

class AgentExecutor:
    def __init__(self, agent_config):
        self.agent_config = agent_config
        self.blocks = {block['id']: block for block in agent_config.get('blocks', [])}
        self.connections = agent_config.get('connections', [])
        self.variables = {}
        self.execution_log = []
        self.outputs = []
        
    def log(self, message, level='info'):
        """Add a log entry"""
        self.execution_log.append({
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        })
    
    def execute(self):
        """Execute the agent workflow"""
        try:
            self.log('Starting agent execution')
            
            # Find the starting block (variable blocks or blocks with no inputs)
            start_blocks = [b for b in self.blocks.values() 
                          if b['type'] == 'variable' or not self.get_incoming_connections(b['id'])]
            
            if not start_blocks:
                raise ValueError('No starting point found in agent workflow')
            
            # Execute each starting block
            for block in start_blocks:
                self.execute_block(block['id'])
            
            self.log('Agent execution completed successfully')
            
            return {
                'success': True,
                'outputs': self.outputs,
                'execution_log': self.execution_log,
                'variables': self.variables
            }
            
        except Exception as e:
            self.log(f'Execution error: {str(e)}', 'error')
            return {
                'success': False,
                'error': str(e),
                'execution_log': self.execution_log
            }
    
    def get_incoming_connections(self, block_id):
        """Get all connections coming into a block"""
        return [c for c in self.connections if c['to_block'] == block_id]
    
    def get_outgoing_connections(self, block_id):
        """Get all connections going out from a block"""
        return [c for c in self.connections if c['from_block'] == block_id]
    
    def execute_block(self, block_id, input_value=None):
        """Execute a specific block"""
        block = self.blocks.get(block_id)
        if not block:
            raise ValueError(f'Block {block_id} not found')
        
        block_type = block['type']
        params = block.get('params', {})
        
        self.log(f'Executing block: {block.get("label", block_type)} ({block_type})')
        
        result = None
        
        if block_type == 'variable':
            # Store or retrieve variable
            var_name = params.get('name', 'var')
            var_value = params.get('value', '')
            self.variables[var_name] = var_value
            result = var_value
            self.log(f'Set variable {var_name} = {var_value}')
            
        elif block_type == 'prompt_template':
            # Create prompt from template
            template = params.get('template', '')
            # Replace variables in template
            for var_name, var_value in self.variables.items():
                template = template.replace(f'{{{var_name}}}', str(var_value))
            result = template
            self.log(f'Created prompt: {result[:100]}...')
            
        elif block_type == 'ai_model':
            # Call AI model
            model = params.get('model', 'gpt-4o')
            prompt = input_value or params.get('prompt', '')
            
            # Get provider from model name
            provider = MODEL_TO_PROVIDER.get(model, 'openai')
            api_key = get_api_key_for_provider(provider)
            
            if not api_key:
                self.log(f'No API key configured for {provider}', 'error')
                result = f"Error: No API key configured for {provider}"
            else:
                self.log(f'Calling AI model: {model} ({provider}) with prompt: {prompt[:100]}...')
                
                # Call actual AI service
                try:
                    ai_service = AIService()
                    response = ai_service.chat(
                        provider=provider,
                        message=prompt,
                        api_key=api_key
                    )
                    # Extract the response text
                    if isinstance(response, dict):
                        result = response.get('response', response.get('text', str(response)))
                    else:
                        result = str(response)
                    self.log(f'AI Response received ({len(result)} chars): {result[:100]}...')
                except Exception as e:
                    self.log(f'AI call failed: {str(e)}', 'error')
                    result = f"Error calling AI model: {str(e)}"
            
        elif block_type == 'text_transform':
            # Transform text
            text = input_value or ''
            transform_type = params.get('transform_type', 'uppercase')
            
            if transform_type == 'uppercase':
                result = text.upper()
            elif transform_type == 'lowercase':
                result = text.lower()
            elif transform_type == 'title':
                result = text.title()
            else:
                result = text
                
            self.log(f'Transformed text: {transform_type}')
            
        elif block_type == 'condition':
            # Evaluate condition
            condition_type = params.get('condition_type', 'contains')
            comparison_value = params.get('comparison_value', '')
            
            if condition_type == 'contains':
                result = comparison_value in str(input_value)
            elif condition_type == 'equals':
                result = str(input_value) == comparison_value
            elif condition_type == 'not_empty':
                result = bool(input_value)
            else:
                result = False
                
            self.log(f'Condition evaluated to: {result}')
            
        elif block_type == 'output':
            # Output result
            label = params.get('label', 'Output')
            content = input_value or params.get('content', '')
            self.outputs.append({
                'label': label,
                'content': content
            })
            self.log(f'Output: {label} = {content[:100]}...')
            return
        
        # Execute connected blocks
        outgoing = self.get_outgoing_connections(block_id)
        for connection in outgoing:
            output_type = connection.get('from_output', 'default')
            
            # For condition blocks, check which path to take
            if block_type == 'condition':
                if (output_type == 'true_path' and result) or \
                   (output_type == 'false_path' and not result):
                    self.execute_block(connection['to_block'], result)
            else:
                self.execute_block(connection['to_block'], result)


# ============================================
# Agent Management Routes
# ============================================

@agents_bp.route('/block-types', methods=['GET'])
@authenticated_required
def get_block_types():
    """Get available block types"""
    # Convert dictionary to array format expected by frontend
    block_types_array = [
        {
            'type': type_key,
            **type_info
        }
        for type_key, type_info in BLOCK_TYPES.items()
    ]
    
    return jsonify({
        'success': True,
        'block_types': block_types_array
    })


def get_agent_for_user(agent_id, user_id, is_admin=False):
    """Get an agent and verify ownership"""
    agents_data = load_agents()
    agent = next((a for a in agents_data['agents'] if a['agent_id'] == agent_id), None)
    
    if not agent:
        return None, "Agent not found"
    
    # Check ownership
    if not is_admin and agent['user_id'] != user_id:
        return None, "Permission denied - you don't own this agent"
    
    return agent, None


@agents_bp.route('/', methods=['GET'])
@authenticated_required
def get_agents():
    """Get user's agents"""
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    agents_data = load_agents()
    
    if is_admin:
        # Admin sees all agents
        user_agents = agents_data.get('agents', [])
    else:
        # Users see only their own agents
        user_agents = [a for a in agents_data.get('agents', []) if a.get('user_id') == user_id]
    
    return jsonify({
        'success': True,
        'agents': user_agents
    })


@agents_bp.route('/', methods=['POST'])
@authenticated_required
def create_agent():
    """Create a new agent"""
    data = request.json or {}
    user_id = session.get('user_id')
    
    agent = {
        'agent_id': str(uuid.uuid4()),
        'user_id': user_id,
        'name': data.get('name', 'Untitled Agent'),
        'description': data.get('description', ''),
        'blocks': data.get('blocks', []),
        'connections': data.get('connections', []),
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
    
    agents_data = load_agents()
    agents_data['agents'].append(agent)
    save_agents(agents_data)
    
    return jsonify({
        'success': True,
        'agent': agent
    })


@agents_bp.route('/<agent_id>', methods=['GET'])
@authenticated_required
def get_agent(agent_id):
    """Get a specific agent"""
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    # Verify ownership
    agent, error = get_agent_for_user(agent_id, user_id, is_admin)
    if error:
        return jsonify({'error': error}), 403 if 'Permission' in error else 404
    
    return jsonify({
        'success': True,
        'agent': agent
    })


@agents_bp.route('/<agent_id>', methods=['PUT'])
@authenticated_required
def update_agent(agent_id):
    """Update an agent"""
    data = request.json or {}
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    # Verify ownership
    agent, error = get_agent_for_user(agent_id, user_id, is_admin)
    if error:
        return jsonify({'error': error}), 403 if 'Permission' in error else 404
    
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    agents_data = load_agents()
    
    # Update agent in the data structure
    for idx, a in enumerate(agents_data['agents']):
        if a.get('agent_id') == agent_id:
            agents_data['agents'][idx]['name'] = data.get('name', a['name'])
            agents_data['agents'][idx]['description'] = data.get('description', a['description'])
            agents_data['agents'][idx]['blocks'] = data.get('blocks', a['blocks'])
            agents_data['agents'][idx]['connections'] = data.get('connections', a['connections'])
            agents_data['agents'][idx]['updated_at'] = datetime.now().isoformat()
            agent = agents_data['agents'][idx]
            break
    
    save_agents(agents_data)
    
    return jsonify({
        'success': True,
        'agent': agent
    })


@agents_bp.route('/<agent_id>', methods=['DELETE'])
@authenticated_required
def delete_agent(agent_id):
    """Delete an agent"""
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    # Verify ownership
    agent, error = get_agent_for_user(agent_id, user_id, is_admin)
    if error:
        return jsonify({'error': error}), 403 if 'Permission' in error else 404
    
    agents_data = load_agents()
    
    # Delete agent
    agents_data['agents'] = [a for a in agents_data['agents'] if a['agent_id'] != agent_id]
    save_agents(agents_data)
    
    return jsonify({
        'success': True,
        'message': 'Agent deleted successfully'
    })


@agents_bp.route('/<agent_id>/execute', methods=['POST'])
@authenticated_required
def execute_agent(agent_id):
    """Execute an agent"""
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    # Verify ownership
    agent, error = get_agent_for_user(agent_id, user_id, is_admin)
    if error:
        return jsonify({'error': error}), 403 if 'Permission' in error else 404
    
    # Execute agent
    executor = AgentExecutor(agent)
    result = executor.execute()
    
    # Save execution record
    execution_record = {
        'execution_id': str(uuid.uuid4()),
        'agent_id': agent_id,
        'user_id': user_id,
        'result': result,
        'executed_at': datetime.now().isoformat()
    }
    
    executions_data = load_executions()
    executions_data['executions'].append(execution_record)
    save_executions(executions_data)
    
    return jsonify({
        'success': True,
        'execution': execution_record
    })


@agents_bp.route('/<agent_id>/executions', methods=['GET'])
@authenticated_required
def get_agent_executions(agent_id):
    """Get execution history for an agent"""
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    # Verify ownership
    agent, error = get_agent_for_user(agent_id, user_id, is_admin)
    if error:
        return jsonify({'error': error}), 403 if 'Permission' in error else 404
    
    # Get executions
    executions_data = load_executions()
    agent_executions = [e for e in executions_data['executions'] if e['agent_id'] == agent_id]
    
    # Sort by execution time (newest first)
    agent_executions.sort(key=lambda x: x.get('executed_at', ''), reverse=True)
    
    return jsonify({
        'success': True,
        'executions': agent_executions[:50]  # Limit to last 50 executions
    })


# ============================================
# AI Orchestrator - Auto-Generate Workflows
# ============================================

@agents_bp.route('/orchestrate', methods=['POST'])
@authenticated_required
def orchestrate_workflow():
    """
    AI Orchestrator - Automatically generate multi-agent workflow from a prompt
    
    Takes a natural language prompt and uses GPT-4 to:
    1. Analyze the task requirements
    2. Identify needed specialized agents with names and roles
    3. Create a complete workflow configuration
    """
    data = request.json or {}
    user_prompt = data.get('prompt', '').strip()
    
    if not user_prompt:
        return jsonify({'error': 'Prompt is required'}), 400
    
    user_id = session.get('user_id')
    
    # Define specialized agent roles available
    agent_roles = {
        'researcher': 'Gathers information, conducts research, and provides context',
        'analyst': 'Analyzes data, identifies patterns, and provides insights',
        'writer': 'Creates written content, articles, and documentation',
        'coder': 'Generates code, scripts, and technical solutions',
        'designer': 'Creates designs, visual concepts, and creative solutions',
        'planner': 'Organizes tasks, creates plans, and manages workflows',
        'critic': 'Reviews work, provides feedback, and suggests improvements',
        'coordinator': 'Coordinates between agents and synthesizes results'
    }
    
    # Orchestrator prompt for GPT-4
    orchestrator_prompt = f"""You are an AI Orchestrator that creates multi-agent workflows. Analyze the user's request and design a workflow with specialized AI agents.

User Request: "{user_prompt}"

Available Agent Roles:
{json.dumps(agent_roles, indent=2)}

Create a workflow by:
1. Identifying 2-4 specialized agents needed for this task
2. Assigning each agent a name (e.g., "Sarah the Researcher", "Alex the Analyst")
3. Defining their specific role and what they should accomplish
4. Creating a logical sequence of steps

Respond with a JSON object in this exact format:
{{
  "workflow_name": "Brief descriptive name",
  "description": "What this workflow accomplishes",
  "agents": [
    {{
      "name": "Agent name with role",
      "role_type": "researcher|analyst|writer|coder|designer|planner|critic|coordinator",
      "task": "Specific task for this agent",
      "model": "gpt-4o",
      "prompt": "Detailed prompt for this agent"
    }}
  ],
  "execution_order": ["step 1 description", "step 2 description", ...]
}}

Make it practical and focused on delivering results. Use creative but professional names."""

    response_text = ""  # Initialize for error handling
    try:
        # Call OpenAI GPT-4 as orchestrator
        ai_service = AIService()
        api_key = current_app.config.get('OPENAI_API_KEY')
        
        if not api_key:
            return jsonify({'error': 'OpenAI API key not configured'}), 500
        
        response_data = ai_service.chat(
            provider='openai',
            message=orchestrator_prompt,
            api_key=api_key
        )
        
        # Check for errors
        if isinstance(response_data, dict) and 'error' in response_data:
            return jsonify({
                'error': 'AI service error',
                'details': response_data['error']
            }), 500
        
        # Extract response text
        if isinstance(response_data, dict):
            response_text = response_data.get('text', response_data.get('response', str(response_data)))
        else:
            response_text = str(response_data)
        
        print(f"DEBUG: Orchestrator response (first 200 chars): {response_text[:200]}")
        
        # Extract JSON from response (handle markdown code blocks)
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
            else:
                json_text = response_text
        
        print(f"DEBUG: Extracted JSON (first 200 chars): {json_text[:200]}")
        
        # Parse the orchestrator's response
        workflow_config = json.loads(json_text)
        
        # Create agent configuration blocks
        blocks = []
        for i, agent in enumerate(workflow_config.get('agents', [])):
            blocks.append({
                'id': f'block_{i+1}',
                'type': 'ai_model',
                'name': agent['name'],
                'label': agent['name'],
                'params': {
                    'model': agent.get('model', 'gpt-4o'),
                    'prompt': agent.get('prompt', agent.get('task', '')),
                    'temperature': 0.7,
                    'max_tokens': 2000
                },
                'position': {'x': 100, 'y': 100 + (i * 150)}
            })
        
        # Create the complete agent configuration
        agent_config = {
            'name': workflow_config.get('workflow_name', 'Generated Workflow'),
            'description': workflow_config.get('description', user_prompt),
            'user_id': user_id,
            'blocks': blocks,
            'orchestrator_metadata': {
                'original_prompt': user_prompt,
                'agents': workflow_config.get('agents', []),
                'execution_order': workflow_config.get('execution_order', [])
            }
        }
        
        return jsonify({
            'success': True,
            'workflow': agent_config,
            'message': f'Generated workflow with {len(blocks)} specialized agents'
        })
        
    except json.JSONDecodeError as e:
        print(f"DEBUG: JSON parsing failed. Response text: {response_text[:500]}")
        return jsonify({
            'error': 'Failed to parse orchestrator response',
            'details': str(e),
            'response_preview': response_text[:300]
        }), 500
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate workflow',
            'details': str(e)
        }), 500
