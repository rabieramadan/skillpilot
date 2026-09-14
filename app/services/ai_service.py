"""Multi-provider AI gateway used by every SkillPilot feature.

:class:`AIService` is the single entry point the routes and the other services
call. It knows *what* to ask for — the tutor's system prompt, the language the
student is working in, which uploaded files matter — and delegates *how* to
ask to :mod:`app.services.ai_transport`, which owns HTTP, retries, model
fallback and response parsing.

Model identifiers are never written here. They come from
:mod:`app.services.model_registry`, so a provider retiring a model is a
one-line change in the catalogue rather than an edit in ninety places.
"""

import base64
import json
import mimetypes
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from werkzeug.utils import secure_filename

from app.services import model_registry as registry
from app.services.ai_transport import (
    AIError,
    build_attachments,
    chat_anthropic,
    chat_gemini,
    chat_openai_compatible,
)
from app.services import ai_transport

# boto3 backs the AWS Bedrock providers only. It is optional: a deployment
# that does not use Bedrock should not be forced to install the AWS SDK.
try:
    import boto3

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _error(provider: str, message: str) -> Dict[str, Any]:
    """The error shape every caller in the codebase already expects."""
    return {'error': message, 'provider': provider, 'timestamp': _now()}


class AIService:
    #: Providers reached through the shared OpenAI-compatible transport.
    OPENAI_COMPATIBLE = ('openai', 'grok', 'deepseek', 'perplexity')

    def __init__(self):
        self.providers = {
            'openai': self._chat_openai,
            'claude': self._chat_claude,
            'gemini': self._chat_gemini,
            'grok': self._chat_grok,
            'deepseek': self._chat_deepseek,
            'perplexity': self._chat_perplexity,
            'dalle': self._generate_dalle,
            # The registry calls this provider 'images'; 'dalle' is the name
            # stored in existing sessions. Both must reach the same handler.
            'images': self._generate_dalle,
            'heygen': self._generate_heygen_video,
            'dify': self._chat_dify,
            'bedrock': self._chat_bedrock,
            'llama_bedrock': self._chat_llama_bedrock,
            'mistral_bedrock': self._chat_mistral_bedrock,
            'amazon_nova': self._chat_amazon_nova,
            'cohere_bedrock': self._chat_cohere_bedrock,
            'ai21_bedrock': self._chat_ai21_bedrock,
            'stable_diffusion': self._generate_stable_diffusion,
        }

    def chat(self, provider: str, message: str, api_key: str,
             files: List[str] = None,
             conversation_history: List[Dict[str, str]] = None,
             version: str = None, language: str = 'en',
             system_prompt: str = None) -> Dict[str, Any]:
        """Ask ``provider`` a question and return a normalised answer.

        Returns ``{'text', 'provider', 'model', 'timestamp', ...}`` on success
        and ``{'error', 'provider', 'timestamp'}`` on failure. Callers only
        ever have to check for the ``error`` key.
        """
        key = registry.PROVIDER_ALIASES.get((provider or '').lower(), provider)
        handler = self.providers.get(key)
        if handler is None:
            return _error(provider, f'Unsupported AI provider: {provider}')

        system = self._compose_system_prompt(system_prompt, language)
        try:
            return handler(
                message, api_key,
                files=files,
                conversation_history=conversation_history or [],
                version=version,
                language=language,
                system=system,
            )
        except AIError as exc:
            return _error(key, exc.message)
        except Exception as exc:  # noqa: BLE001 - a route must never 500 here
            return _error(key, f'Unexpected {key} error: {exc}')

    # -- prompt construction -------------------------------------------------

    #: Applies to every request. Keeps answers grounded in the material the
    #: student actually has, which is the difference between a useful tutor
    #: and a confident guess.
    BASE_INSTRUCTIONS = (
        "You are an assistant inside SkillPilot, a university learning "
        "platform. Answer the question that was asked, directly and without "
        "preamble.\n"
        "- Ground every claim in the attached files and the conversation. "
        "When they do not cover something, say so plainly instead of "
        "inventing a source, a figure, a citation or a quotation.\n"
        "- State facts, dates and numbers only when you are confident of "
        "them; otherwise say what you are unsure about.\n"
        "- Prefer short paragraphs and lists. Use a heading only when the "
        "answer genuinely has sections.\n"
        "- When you are asked for a specific format (JSON, a table, a fixed "
        "number of items), return exactly that and nothing around it."
    )

    LANGUAGE_INSTRUCTIONS = {
        'ar': (
            "Write the entire reply in Modern Standard Arabic. Keep code, "
            "URLs and proper nouns in their original script.\n"
            "اكتب الرد بالكامل باللغة العربية الفصحى."
        ),
        'en': "Write the entire reply in English.",
    }

    def _compose_system_prompt(self, system_prompt: Optional[str],
                               language: str) -> str:
        """Merge the caller's instructions with the platform-wide ones.

        Previously a caller's system prompt was pasted into the *user* message
        between ``[SYSTEM CONTEXT]`` markers. Every provider here supports a
        real system role, which the model weights differently and which a
        student's message cannot overwrite, so the instructions go there.
        """
        parts = [self.BASE_INSTRUCTIONS]
        lang = self.LANGUAGE_INSTRUCTIONS.get(
            (language or 'en').lower(), self.LANGUAGE_INSTRUCTIONS['en'])
        parts.append(lang)
        if system_prompt and system_prompt.strip():
            parts.append(
                'Task-specific instructions, which take precedence over the '
                'general guidance above:\n' + system_prompt.strip()
            )
        return '\n\n'.join(parts)
    @staticmethod
    def build_tutor_system_prompt(course_context: Dict[str, Any],
                                  learner_context: Dict[str, Any],
                                  language: str = 'en') -> str:
        """
        Build a course-aware system prompt for the adaptive tutor.

        course_context expected keys:
            title, code, description, weeks (list[{week_number,title,materials:[{title,topics,difficulty_level,description}]}])
        learner_context expected keys:
            display_name, preferred_difficulty, overall_score, weak_topics (list[str]),
            strong_topics (list[str]), skill_levels (list[{code,name,level,level_max}]),
            primary_goal
        """
        course_context = course_context or {}
        learner_context = learner_context or {}

        lang_line = (
            "Respond in Arabic (العربية)." if language == 'ar'
            else "Respond in English."
        )

        weeks_summary_lines = []
        for w in (course_context.get('weeks') or [])[:12]:
            mats = w.get('materials') or []
            mat_lines = "; ".join(
                f"[id={m.get('id','?')}] {m.get('title','?')} ({m.get('difficulty_level','?')})"
                for m in mats[:8]
            )
            weeks_summary_lines.append(
                f"  - Week {w.get('week_number','?')}: {w.get('title','')} — {mat_lines or 'no materials'}"
            )
        weeks_block = "\n".join(weeks_summary_lines) or "  (no published weeks)"

        skill_lines = []
        for s in (learner_context.get('skill_levels') or [])[:15]:
            skill_lines.append(
                f"  - {s.get('name') or s.get('code')}: {s.get('level',0)}/{s.get('level_max',5)}"
            )
        skills_block = "\n".join(skill_lines) or "  (no skill data yet)"

        weak = ", ".join(learner_context.get('weak_topics') or []) or "none identified"
        strong = ", ".join(learner_context.get('strong_topics') or []) or "none identified"

        difficulty = learner_context.get('preferred_difficulty') or 'adaptive'
        score = learner_context.get('overall_score')
        score_line = f"{score:.0f}/100" if isinstance(score, (int, float)) else "n/a"

        return (
            "You are SkillPilot's adaptive AI course tutor. "
            "Stay strictly grounded in the COURSE MATERIALS below; if the answer is not "
            "covered, say so and suggest the closest material in the course. "
            f"{lang_line}\n\n"
            "=== COURSE ===\n"
            f"Title: {course_context.get('title','(untitled)')}\n"
            f"Code: {course_context.get('code','')}\n"
            f"Description: {(course_context.get('description') or '')[:500]}\n"
            f"Weeks & materials:\n{weeks_block}\n\n"
            "=== LEARNER PROFILE ===\n"
            f"Goal: {learner_context.get('primary_goal') or 'not set'}\n"
            f"Preferred difficulty: {difficulty}\n"
            f"Overall performance: {score_line}\n"
            f"Weak topics (focus more here, scaffold carefully): {weak}\n"
            f"Strong topics (you can stretch further): {strong}\n"
            f"Skill levels:\n{skills_block}\n\n"
            "=== TUTOR RULES ===\n"
            "1. Calibrate difficulty: simpler explanations + more worked examples for "
            "weak topics; deeper questions and challenges for strong topics.\n"
            "2. Cite the relevant week/material title when you reference course content.\n"
            "3. Never invent materials, weeks, or scores. If unsure, say 'not in your "
            "course materials' and recommend what to study next.\n"
            "4. End with one short check-for-understanding question tailored to the "
            "learner's weakest relevant topic.\n"
            "5. CITATIONS: After your answer and check-for-understanding question, "
            "on the very last line, output a citation marker listing the IDs of "
            "the course materials you actually drew from, in the exact form: "
            "[[CITATIONS: id1, id2, id3]]. Use only IDs that appear in the "
            "Weeks & materials list above. If you did not use any specific "
            "material, output [[CITATIONS: none]]. Do not write anything after "
            "this marker.\n"
        )

    def _extract_file_content(self, file_path: str) -> str:
        """Plain text of one uploaded file, for storing alongside the chat.

        Kept as a method because ``app/routes/api.py`` calls it to persist
        file context in the conversation history.
        """
        attachments = build_attachments([file_path])
        for attachment in attachments:
            if not attachment.is_image:
                return attachment.text
            return f'[Image: {attachment.name}]'
        return ''
    def _chat_openai(self, message: str, api_key: str, files: List[str] = None,
                     conversation_history: List[Dict[str, str]] = None,
                     version: str = None, language: str = 'en',
                     system: str = None) -> Dict[str, Any]:
        return self._chat_openai_family('openai', message, api_key, files,
                                        conversation_history, version,
                                        language, system)

    def _chat_grok(self, message: str, api_key: str, files: List[str] = None,
                   conversation_history: List[Dict[str, str]] = None,
                   version: str = None, language: str = 'en',
                   system: str = None) -> Dict[str, Any]:
        return self._chat_openai_family('grok', message, api_key, files,
                                        conversation_history, version,
                                        language, system)

    def _chat_deepseek(self, message: str, api_key: str, files: List[str] = None,
                       conversation_history: List[Dict[str, str]] = None,
                       version: str = None, language: str = 'en',
                       system: str = None) -> Dict[str, Any]:
        return self._chat_openai_family('deepseek', message, api_key, files,
                                        conversation_history, version,
                                        language, system)

    def _chat_perplexity(self, message: str, api_key: str, files: List[str] = None,
                         conversation_history: List[Dict[str, str]] = None,
                         version: str = None, language: str = 'en',
                         system: str = None) -> Dict[str, Any]:
        return self._chat_openai_family('perplexity', message, api_key, files,
                                        conversation_history, version,
                                        language, system)

    def _chat_openai_family(self, provider: str, message: str, api_key: str,
                            files: List[str] = None,
                            conversation_history: List[Dict[str, str]] = None,
                            version: str = None, language: str = 'en',
                            system: str = None) -> Dict[str, Any]:
        """OpenAI, xAI Grok, DeepSeek and Perplexity share one wire format.

        They used to have four near-identical implementations that had drifted
        apart: Grok discarded the conversation history, DeepSeek built its own
        system prompt, and only OpenAI handled images.
        """
        try:
            result = chat_openai_compatible(
                provider,
                api_key=api_key,
                user_text=message,
                system=system or self._compose_system_prompt(None, language),
                history=conversation_history,
                attachments=build_attachments(files),
                model=version,
                max_tokens=self._max_tokens(provider),
            )
        except AIError as exc:
            return _error(provider, exc.message)
        return result.as_dict()

    def _chat_claude(self, message: str, api_key: str, files: List[str] = None,
                     conversation_history: List[Dict[str, str]] = None,
                     version: str = None, language: str = 'en',
                     system: str = None) -> Dict[str, Any]:
        try:
            result = chat_anthropic(
                api_key=api_key,
                user_text=message,
                system=system or self._compose_system_prompt(None, language),
                history=conversation_history,
                attachments=build_attachments(files),
                model=version,
                max_tokens=self._max_tokens('claude'),
            )
        except AIError as exc:
            return _error('claude', exc.message)
        return result.as_dict()

    def _max_tokens(self, provider: str, default: int = 8000) -> int:
        """Output budget for ``provider`` from config.yaml, else a default."""
        block = registry._yaml_models().get(provider) or {}
        try:
            return int(block.get('max_tokens') or default)
        except (TypeError, ValueError):
            return default
    def _parse_aws_credentials(self, api_key: str):
        """Split the ``access_key|secret_key|region`` string used for Bedrock."""
        parts = [p.strip() for p in (api_key or '').split('|')]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            return None
        region = parts[2] if len(parts) > 2 and parts[2] else 'us-west-2'
        return parts[0], parts[1], region

    def _bedrock_client(self, api_key: str):
        """A ``bedrock-runtime`` client, or a ready-to-return error dict."""
        if not BOTO3_AVAILABLE:
            return None, _error('bedrock', 'boto3 is not installed. '
                                           'Run: pip install boto3')
        credentials = self._parse_aws_credentials(api_key)
        if credentials is None:
            return None, _error('bedrock', 'AWS credentials required, in the '
                                           'form access_key|secret_key|region.')
        access_key, secret_key, region = credentials
        return boto3.client(
            service_name='bedrock-runtime',
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        ), None

    def _chat_bedrock(self, message: str, api_key: str, files: List[str] = None,
                    conversation_history: List[Dict[str, str]] = None,
                    version: str = None, language: str = 'en',
                    system: str = None) -> Dict[str, Any]:
        """Claude on AWS Bedrock, through the Anthropic Messages payload."""
        client, failure = self._bedrock_client(api_key)
        if failure is not None:
            return failure

        attachments = build_attachments(files)
        has_image = any(a.is_image for a in attachments)
        model_id = registry.resolve('bedrock', version, vision=has_image)
        entry = registry.get_model('bedrock', model_id)

        content: List[Dict[str, Any]] = []
        if has_image and (entry is None or entry.vision):
            for image in (a for a in attachments if a.is_image):
                content.append({
                    'type': 'image',
                    'source': {
                        'type': 'base64',
                        'media_type': image.mime_type,
                        'data': base64.b64encode(image.data).decode('ascii'),
                    },
                })
        prompt = (message or '').strip() + ai_transport._text_attachment_block(attachments)
        content.append({'type': 'text', 'text': prompt})

        messages = [
            {'role': turn['role'], 'content': [{'type': 'text', 'text': turn['content']}]}
            for turn in ai_transport._normalise_history(conversation_history)
        ]
        messages.append({'role': 'user', 'content': content})

        max_tokens = self._max_tokens('bedrock')
        if entry is not None:
            max_tokens = min(max_tokens, entry.max_output_tokens)
        payload: Dict[str, Any] = {
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': max_tokens,
            'messages': messages,
        }
        if system:
            payload['system'] = system
        # Claude 5 rejects temperature; only send it where the catalogue says
        # the model still accepts one.
        if entry is None or entry.sampling:
            payload['temperature'] = 0.7

        try:
            response = client.invoke_model(modelId=model_id, body=json.dumps(payload))
            result = json.loads(response['body'].read())
        except Exception as exc:  # noqa: BLE001 - botocore raises many types
            detail = str(exc)
            if registry.is_model_unavailable_error(detail):
                return _error('bedrock', f'{model_id} is not enabled for this '
                                         'AWS account or region.')
            return _error('bedrock', f'AWS Bedrock error: {detail[:300]}')

        text = ''.join(
            block.get('text', '')
            for block in (result.get('content') or [])
            if isinstance(block, dict) and block.get('type') == 'text'
        ).strip()
        if not text:
            return _error('bedrock', 'Bedrock returned an empty answer.')

        label = entry.label if entry is not None else model_id
        return {
            'text': text,
            'provider': 'bedrock',
            'model': label,
            'model_id': model_id,
            'timestamp': _now(),
            'usage': result.get('usage') or {},
        }

    def _chat_llama_bedrock(self, message: str, api_key: str, files: List[str] = None,
                    conversation_history: List[Dict[str, str]] = None,
                    version: str = None, language: str = 'en',
                    system: str = None) -> Dict[str, Any]:
        """Meta Llama models via AWS Bedrock"""
        bedrock_runtime, failure = self._bedrock_client(api_key)
        if failure is not None:
            return failure

        try:
            
            # Build prompt with conversation history
            prompt_text = message
            if conversation_history:
                history_text = "\n".join([f"{m['role']}: {m['content']}" for m in conversation_history])
                prompt_text = f"{history_text}\nuser: {message}\nassistant:"
            
            # Handle file uploads
            if files:
                from app.utils.file_handler import FileHandler
                file_texts = []
                for file_path in files:
                    if os.path.exists(file_path):
                        try:
                            content = FileHandler.extract_text(file_path)[:5000]
                            file_texts.append(f"File: {os.path.basename(file_path)}\n{content}")
                        except:
                            pass
                if file_texts:
                    prompt_text = "\n\n".join(file_texts) + "\n\n" + prompt_text
            
            model_id = version or "meta.llama3-2-90b-instruct-v1:0"
            
            payload = {
                "prompt": prompt_text,
                "max_gen_len": 4000,
                "temperature": 0.7,
                "top_p": 0.9
            }
            
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(payload)
            )
            
            try:
                response_body = response['body'].read()
                result = json.loads(response_body)
                response_text = result.get('generation', result.get('text', ''))
            except (json.JSONDecodeError, KeyError) as e:
                return {'error': f'Failed to parse Llama Bedrock response: {str(e)}'}
            
            return {
                'text': response_text,
                'provider': 'llama_bedrock',
                'timestamp': datetime.now().isoformat(),
                'model': "Llama (AWS Bedrock)"
            }
        except Exception as e:
            return {'error': f'Llama Bedrock error: {str(e)}'}

    def _chat_mistral_bedrock(self, message: str, api_key: str, files: List[str] = None,
                    conversation_history: List[Dict[str, str]] = None,
                    version: str = None, language: str = 'en',
                    system: str = None) -> Dict[str, Any]:
        """Mistral AI models via AWS Bedrock"""
        bedrock_runtime, failure = self._bedrock_client(api_key)
        if failure is not None:
            return failure

        try:
            
            prompt_text = message
            if files:
                from app.utils.file_handler import FileHandler
                file_texts = []
                for file_path in files:
                    if os.path.exists(file_path):
                        try:
                            content = FileHandler.extract_text(file_path)[:5000]
                            file_texts.append(f"File: {os.path.basename(file_path)}\n{content}")
                        except:
                            pass
                if file_texts:
                    prompt_text = "\n\n".join(file_texts) + "\n\n" + prompt_text
            
            model_id = version or "mistral.mistral-large-2407-v1:0"
            
            payload = {
                "prompt": f"<s>[INST] {prompt_text} [/INST]",
                "max_tokens": 4000,
                "temperature": 0.7,
                "top_p": 0.9
            }
            
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(payload)
            )
            
            try:
                response_body = response['body'].read()
                result = json.loads(response_body)
                response_text = result['outputs'][0]['text'] if 'outputs' in result else result.get('text', '')
            except (json.JSONDecodeError, KeyError) as e:
                return {'error': f'Failed to parse Mistral Bedrock response: {str(e)}'}
            
            return {
                'text': response_text,
                'provider': 'mistral_bedrock',
                'timestamp': datetime.now().isoformat(),
                'model': "Mistral (AWS Bedrock)"
            }
        except Exception as e:
            return {'error': f'Mistral Bedrock error: {str(e)}'}

    def _chat_amazon_nova(self, message: str, api_key: str, files: List[str] = None,
                    conversation_history: List[Dict[str, str]] = None,
                    version: str = None, language: str = 'en',
                    system: str = None) -> Dict[str, Any]:
        """Amazon Nova models via AWS Bedrock"""
        bedrock_runtime, failure = self._bedrock_client(api_key)
        if failure is not None:
            return failure

        try:
            
            # Build messages with file support
            content = [{"text": message}]
            
            if files:
                for file_path in files:
                    if not os.path.exists(file_path):
                        continue
                    
                    mime_type, _ = mimetypes.guess_type(file_path)
                    
                    if mime_type and mime_type.startswith('image/'):
                        with open(file_path, 'rb') as f:
                            image_data = base64.b64encode(f.read()).decode('utf-8')
                            content.append({
                                "image": {
                                    "format": mime_type.split('/')[-1],
                                    "source": {"bytes": image_data}
                                }
                            })
                    else:
                        try:
                            from app.utils.file_handler import FileHandler
                            file_content = FileHandler.extract_text(file_path)[:5000]
                            content.append({"text": f"\n\nFile: {os.path.basename(file_path)}\n{file_content}"})
                        except:
                            pass
            
            messages = []
            for hist_msg in conversation_history if conversation_history else []:
                messages.append({
                    "role": hist_msg.get('role', 'user'),
                    "content": [{"text": hist_msg.get('content', '')}]
                })
            
            messages.append({"role": "user", "content": content})
            
            model_id = version or "amazon.nova-pro-v1:0"
            
            payload = {
                "messages": messages,
                "inferenceConfig": {
                    "max_new_tokens": 4000,
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            }
            
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(payload)
            )
            
            try:
                response_body = response['body'].read()
                result = json.loads(response_body)
                response_text = result['output']['message']['content'][0]['text']
            except (json.JSONDecodeError, KeyError) as e:
                return {'error': f'Failed to parse Amazon Nova response: {str(e)}'}
            
            return {
                'text': response_text,
                'provider': 'amazon_nova',
                'timestamp': datetime.now().isoformat(),
                'model': "Amazon Nova (AWS Bedrock)"
            }
        except Exception as e:
            return {'error': f'Amazon Nova error: {str(e)}'}

    def _chat_cohere_bedrock(self, message: str, api_key: str, files: List[str] = None,
                    conversation_history: List[Dict[str, str]] = None,
                    version: str = None, language: str = 'en',
                    system: str = None) -> Dict[str, Any]:
        """Cohere models via AWS Bedrock"""
        bedrock_runtime, failure = self._bedrock_client(api_key)
        if failure is not None:
            return failure

        try:
            
            prompt_text = message
            if files:
                from app.utils.file_handler import FileHandler
                file_texts = []
                for file_path in files:
                    if os.path.exists(file_path):
                        try:
                            content = FileHandler.extract_text(file_path)[:5000]
                            file_texts.append(f"File: {os.path.basename(file_path)}\n{content}")
                        except:
                            pass
                if file_texts:
                    prompt_text = "\n\n".join(file_texts) + "\n\n" + prompt_text
            
            chat_history = []
            if conversation_history:
                for msg in conversation_history:
                    chat_history.append({
                        "role": "USER" if msg['role'] == 'user' else "CHATBOT",
                        "message": msg['content']
                    })
            
            model_id = version or "cohere.command-r-plus-v1:0"
            
            payload = {
                "message": prompt_text,
                "chat_history": chat_history,
                "max_tokens": 4000,
                "temperature": 0.7
            }
            
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(payload)
            )
            
            try:
                response_body = response['body'].read()
                result = json.loads(response_body)
                response_text = result['text']
            except (json.JSONDecodeError, KeyError) as e:
                return {'error': f'Failed to parse Cohere Bedrock response: {str(e)}'}
            
            return {
                'text': response_text,
                'provider': 'cohere_bedrock',
                'timestamp': datetime.now().isoformat(),
                'model': "Cohere (AWS Bedrock)"
            }
        except Exception as e:
            return {'error': f'Cohere Bedrock error: {str(e)}'}

    def _chat_ai21_bedrock(self, message: str, api_key: str, files: List[str] = None,
                    conversation_history: List[Dict[str, str]] = None,
                    version: str = None, language: str = 'en',
                    system: str = None) -> Dict[str, Any]:
        """AI21 Labs models via AWS Bedrock"""
        bedrock_runtime, failure = self._bedrock_client(api_key)
        if failure is not None:
            return failure

        try:
            
            prompt_text = message
            if files:
                from app.utils.file_handler import FileHandler
                file_texts = []
                for file_path in files:
                    if os.path.exists(file_path):
                        try:
                            content = FileHandler.extract_text(file_path)[:5000]
                            file_texts.append(f"File: {os.path.basename(file_path)}\n{content}")
                        except:
                            pass
                if file_texts:
                    prompt_text = "\n\n".join(file_texts) + "\n\n" + prompt_text
            
            model_id = version or "ai21.jamba-1-5-large-v1:0"
            
            # Jamba models use messages format
            messages = []
            for hist_msg in conversation_history if conversation_history else []:
                messages.append({
                    "role": hist_msg.get('role', 'user'),
                    "content": hist_msg.get('content', '')
                })
            messages.append({"role": "user", "content": prompt_text})
            
            payload = {
                "messages": messages,
                "max_tokens": 4000,
                "temperature": 0.7,
                "top_p": 0.9
            }
            
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(payload)
            )
            
            try:
                response_body = response['body'].read()
                result = json.loads(response_body)
                response_text = result['choices'][0]['message']['content'] if 'choices' in result else result.get('completion', '')
            except (json.JSONDecodeError, KeyError) as e:
                return {'error': f'Failed to parse AI21 Bedrock response: {str(e)}'}
            
            return {
                'text': response_text,
                'provider': 'ai21_bedrock',
                'timestamp': datetime.now().isoformat(),
                'model': "AI21 (AWS Bedrock)"
            }
        except Exception as e:
            return {'error': f'AI21 Bedrock error: {str(e)}'}

    def _generate_stable_diffusion(self, prompt: str, api_key: str, files: List[str] = None,
                    conversation_history: List[Dict[str, str]] = None,
                    version: str = None, language: str = 'en',
                    system: str = None) -> Dict[str, Any]:
        """Stable Diffusion image generation via AWS Bedrock"""
        bedrock_runtime, failure = self._bedrock_client(api_key)
        if failure is not None:
            return failure

        try:
            
            model_id = version or "stability.sd3-large-v1:0"
            
            payload = {
                "text_prompts": [{"text": prompt, "weight": 1.0}],
                "cfg_scale": 7,
                "steps": 30,
                "seed": 0,
                "width": 1024,
                "height": 1024
            }
            
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(payload)
            )
            
            try:
                response_body = response['body'].read()
                result = json.loads(response_body)
            except (json.JSONDecodeError, KeyError) as e:
                return {'error': f'Failed to parse Stable Diffusion response: {str(e)}'}
            
            # Stable Diffusion returns base64 encoded image
            if 'artifacts' in result:
                image_base64 = result['artifacts'][0]['base64']
                image_url = f"data:image/png;base64,{image_base64}"
                
                return {
                    'text': f'Generated image with Stable Diffusion: "{prompt}"',
                    'provider': 'stable_diffusion',
                    'timestamp': datetime.now().isoformat(),
                    'model': 'Stable Diffusion (AWS Bedrock)',
                    'image_url': image_url
                }
            else:
                return {'error': 'No image generated'}
                
        except Exception as e:
            return {'error': f'Stable Diffusion error: {str(e)}'}

    def _chat_gemini(self, message: str, api_key: str, files: List[str] = None,
                     conversation_history: List[Dict[str, str]] = None,
                     version: str = None, language: str = 'en',
                     system: str = None) -> Dict[str, Any]:
        try:
            result = chat_gemini(
                api_key=api_key,
                user_text=message,
                system=system or self._compose_system_prompt(None, language),
                history=conversation_history,
                attachments=build_attachments(files),
                model=version,
                max_tokens=self._max_tokens('gemini'),
            )
        except AIError as exc:
            return _error('gemini', exc.message)
        return result.as_dict()

    def _generate_dalle(self, prompt: str, api_key: str, files: List[str] = None,
                        conversation_history: List[Dict[str, str]] = None,
                        version: str = None, language: str = 'en',
                        system: str = None) -> Dict[str, Any]:
        """Generate an image and save it under ``uploads/``.

        The provider key is still called ``dalle`` because that is what is
        stored in existing chat sessions; the DALL-E endpoints themselves were
        shut down in May 2026 and the registry maps them onto GPT Image.
        """
        image_config = registry._yaml_models().get('images') or {}
        try:
            generated = ai_transport.generate_image(
                api_key=api_key,
                prompt=prompt,
                model=version,
                size=str(image_config.get('size') or '1024x1024'),
                quality=str(image_config.get('quality') or 'high'),
            )
        except AIError as exc:
            return _error('dalle', exc.message)

        upload_dir = 'uploads'
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(
            f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
        )
        filepath = os.path.join(upload_dir, filename)
        try:
            with open(filepath, 'wb') as handle:
                handle.write(generated['image_bytes'])
        except OSError as exc:
            return _error('dalle', f'Could not save the generated image: {exc}')

        payload = {
            'text': generated.get('revised_prompt') or f'Generated image for: {prompt}',
            'provider': 'dalle',
            'model': generated['model'],
            'timestamp': _now(),
            'image_url': f'/uploads/{filename}',
            'image_path': filepath,
        }
        if generated.get('fallback_from'):
            payload['fallback_from'] = generated['fallback_from']
        return payload
    def _generate_heygen_video(self, message: str, api_key: str, files: List[str] = None,
                    conversation_history: List[Dict[str, str]] = None,
                    version: str = None, language: str = 'en',
                    system: str = None) -> Dict[str, Any]:
        """Generate an AI avatar video using the HeyGen API.
        The `message` is used as the spoken script. `version` may carry a JSON payload with
        avatar_id / voice_id / background overrides; otherwise sensible defaults are used.
        Returns a video_id that the frontend can poll, or a final video_url when ready."""
        if not api_key:
            return {'error': 'HeyGen API key required. Configure it in Admin > AI Settings (HEYGEN_API_KEY).'}

        try:
            import json as _json
            # Allow passing an options JSON via the version field
            opts = {}
            if version:
                try:
                    opts = _json.loads(version) if version.strip().startswith('{') else {}
                except Exception:
                    opts = {}

            avatar_id = opts.get('avatar_id') or 'Daisy-inskirt-20220818'
            voice_id = opts.get('voice_id') or '2d5b0e6cf36f460aa7fc47e3eee4ba54'
            # HeyGen supports Arabic voices; if user picked Arabic, hint via locale
            input_text = (message or '').strip()
            if not input_text:
                return {'error': 'Please provide a script (text) to generate the video.'}

            payload = {
                "video_inputs": [{
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id,
                        "avatar_style": "normal"
                    },
                    "voice": {
                        "type": "text",
                        "input_text": input_text[:1500],
                        "voice_id": voice_id,
                        "locale": 'ar-SA' if language == 'ar' else 'en-US'
                    },
                    "background": {
                        "type": "color",
                        "value": opts.get('background_color', '#f6f6fc')
                    }
                }],
                "dimension": {"width": 1280, "height": 720}
            }

            headers = {
                'X-Api-Key': api_key,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            resp = requests.post(
                'https://api.heygen.com/v2/video/generate',
                headers=headers,
                json=payload,
                timeout=60
            )

            if resp.status_code not in (200, 201):
                return {'error': f'HeyGen error {resp.status_code}: {resp.text[:300]}'}

            data = resp.json() or {}
            video_id = (data.get('data') or {}).get('video_id') or data.get('video_id')
            if not video_id:
                return {'error': 'HeyGen did not return a video_id', 'raw': data}

            return {
                'text': f"🎬 HeyGen video generation started.\n\nVideo ID: `{video_id}`\nStatus: processing\n\nThe video will be available shortly. Use `/api/heygen/status/{video_id}` to poll for the final URL.",
                'provider': 'heygen',
                'timestamp': datetime.now().isoformat(),
                'model': 'heygen-avatar-v2',
                'video_id': video_id,
                'status': 'processing'
            }
        except Exception as e:
            return {'error': f'HeyGen API error: {str(e)}'}

    def heygen_status(self, video_id: str, api_key: str) -> Dict[str, Any]:
        """Poll HeyGen for the rendered video URL."""
        if not api_key:
            return {'error': 'HeyGen API key required'}
        try:
            resp = requests.get(
                f'https://api.heygen.com/v1/video_status.get?video_id={video_id}',
                headers={'X-Api-Key': api_key, 'Accept': 'application/json'},
                timeout=30
            )
            if resp.status_code != 200:
                return {'error': f'HeyGen status error {resp.status_code}: {resp.text[:200]}'}
            data = (resp.json() or {}).get('data') or {}
            return {
                'status': data.get('status'),
                'video_url': data.get('video_url'),
                'thumbnail_url': data.get('thumbnail_url'),
                'duration': data.get('duration'),
                'error': data.get('error'),
            }
        except Exception as e:
            return {'error': f'HeyGen status error: {str(e)}'}

    def generate_image(self, prompt: str, api_key: str,
                       version: str = None) -> Dict[str, Any]:
        """Public image-generation entry point used by ``/api/generate-image``."""
        return self._generate_dalle(prompt, api_key, version=version)

    def _chat_dify(self, message: str, api_key: str, files: List[str] = None,
                    conversation_history: List[Dict[str, str]] = None,
                    version: str = None, language: str = 'en',
                    system: str = None) -> Dict[str, Any]:
        """Chat with Dify AI Application"""
        if not api_key:
            return {'error': 'Dify API key required'}

        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            # Dify Chat Messages API
            data = {
                'inputs': {},
                'query': message,
                'response_mode': 'blocking',
                'conversation_id': '',  # Empty for new conversation
                'user': 'aiacmate-user'
            }

            response = requests.post(
                'https://api.dify.ai/v1/chat-messages',
                headers=headers,
                json=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    'text': result.get('answer', ''),
                    'provider': 'dify',
                    'timestamp': datetime.now().isoformat(),
                    'model': 'Dify AI',
                    'conversation_id': result.get('conversation_id', '')
                }
            else:
                return {'error': f'Dify API error: {response.status_code} - {response.text[:200]}'}

        except Exception as e:
            return {'error': f'Dify API error: {str(e)}'}
