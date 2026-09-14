import requests
from datetime import datetime
from typing import List, Dict, Any
import json
import os
import base64
import mimetypes
from werkzeug.utils import secure_filename

# Import AI libraries with error handling
try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None

try:
    import google.generativeai as genai

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None

try:
    import boto3

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None

from PIL import Image
import io


class AIService:
    def __init__(self):
        self.providers = {
            'openai': self._chat_openai,
            'claude': self._chat_claude,
            'gemini': self._chat_gemini,
            'grok': self._chat_grok,
            'deepseek': self._chat_deepseek,
            'llama': self._chat_llama,
            'perplexity': self._chat_perplexity,
            'dalle': self._generate_dalle,
            'clarifai': self._analyze_clarifai,
            'census': self._query_census,
            'dify': self._chat_dify,
            'bedrock': self._chat_bedrock,
            'llama_bedrock': self._chat_llama_bedrock,
            'mistral_bedrock': self._chat_mistral_bedrock,
            'amazon_nova': self._chat_amazon_nova,
            'cohere_bedrock': self._chat_cohere_bedrock,
            'ai21_bedrock': self._chat_ai21_bedrock,
            'stable_diffusion': self._generate_stable_diffusion
        }

    def chat(self, provider: str, message: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        if provider not in self.providers:
            return {'error': f'Unsupported provider: {provider}'}

        if conversation_history is None:
            conversation_history = []

        try:
            return self.providers[provider](message, api_key, files, conversation_history, version, language)
        except Exception as e:
            return {'error': str(e)}

    def _extract_file_content(self, file_path: str) -> str:
        """Extract text content from a file for memory persistence"""
        if not os.path.exists(file_path):
            return ""
        
        mime_type, _ = mimetypes.guess_type(file_path)
        
        try:
            # Handle text files
            if mime_type in ['text/plain', 'text/csv', 'application/json']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()[:15000]
            
            # Handle PDFs and other documents
            from app.utils.file_handler import FileHandler
            return FileHandler.extract_text(file_path)[:15000]
        except Exception as e:
            print(f"DEBUG: Error extracting content from {file_path}: {e}")
            return f"[Could not extract content: {str(e)}]"

    def _process_files_for_openai(self, files: List[str], api_key: str) -> List[Dict[str, Any]]:
        """Process uploaded files for OpenAI API"""
        processed_files = []

        if not files:
            print("DEBUG: No files to process")
            return processed_files

        print(f"DEBUG: Processing {len(files)} files")

        try:
            for file_path in files:
                if not os.path.exists(file_path):
                    print(f"DEBUG: File does not exist: {file_path}")
                    continue

                print(f"DEBUG: Processing file: {file_path}")
                mime_type, _ = mimetypes.guess_type(file_path)
                print(f"DEBUG: File MIME type: {mime_type}")

                # Handle images directly in message content
                if mime_type and mime_type.startswith('image/'):
                    try:
                        with open(file_path, 'rb') as f:
                            image_data = base64.b64encode(f.read()).decode('utf-8')
                            processed_files.append({
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:{mime_type};base64,{image_data}'
                                }
                            })
                            print(f"DEBUG: Added image file: {os.path.basename(file_path)}")
                    except Exception as e:
                        print(f"DEBUG: Error processing image {file_path}: {e}")

                # Handle text files
                elif mime_type in ['text/plain', 'text/csv', 'application/json']:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()[:10000]  # Limit content size
                            processed_files.append({
                                'type': 'text',
                                'text': f"File: {os.path.basename(file_path)}\n\nContent:\n{content}"
                            })
                            print(f"DEBUG: Added text file: {os.path.basename(file_path)}")
                    except Exception as e:
                        print(f"DEBUG: Error reading text file {file_path}: {e}")
                        processed_files.append({
                            'type': 'text',
                            'text': f"Could not read file {os.path.basename(file_path)}: {str(e)}"
                        })

                # For PDFs and other files, extract text if possible
                else:
                    try:
                        from app.utils.file_handler import FileHandler
                        text_content = FileHandler.extract_text(file_path)
                        processed_files.append({
                            'type': 'text',
                            'text': f"File: {os.path.basename(file_path)} (Type: {mime_type or 'unknown'})\n\nContent:\n{text_content[:5000]}"
                        })
                        print(f"DEBUG: Added extracted text from: {os.path.basename(file_path)}")
                    except Exception as e:
                        print(f"DEBUG: Error extracting from {file_path}: {e}")
                        processed_files.append({
                            'type': 'text',
                            'text': f"Uploaded file: {os.path.basename(file_path)} (Type: {mime_type or 'unknown'}) - Could not extract content: {str(e)}"
                        })

        except Exception as e:
            print(f"DEBUG: Error in file processing: {e}")
            processed_files.append({
                'type': 'text',
                'text': f"Error processing files: {str(e)}"
            })

        print(f"DEBUG: Finished processing, {len(processed_files)} items created")
        return processed_files

    def _chat_openai(self, message: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        if not api_key:
            return {'error': 'OpenAI API key required'}

        if conversation_history is None:
            conversation_history = []

        print(f"DEBUG: OpenAI called with {len(files or [])} files and {len(conversation_history)} history messages")

        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            # Process files
            file_content = self._process_files_for_openai(files, api_key)
            print(f"DEBUG: Processed {len(file_content)} file content items")

            # Build message content for current message
            content = [{'type': 'text', 'text': message}]
            content.extend(file_content)

            # Choose model based on whether we have images
            has_images = any(item.get('type') == 'image_url' for item in content)
            # Use gpt-4o for vision (not deprecated) and gpt-4-turbo for text
            model = 'gpt-4o' if has_images else 'gpt-4-turbo'

            print(f"DEBUG: Using model {model}, has_images: {has_images}")

            # Build messages array with conversation history
            messages = []
            
            # Add language instruction as system message if Arabic
            if language == 'ar':
                messages.append({
                    'role': 'system',
                    'content': 'You are a helpful AI assistant. Please respond in Arabic language. يرجى الرد باللغة العربية.'
                })
            
            for hist_msg in conversation_history:
                messages.append({
                    'role': hist_msg.get('role', 'user'),
                    'content': hist_msg.get('content', '')
                })
            
            # Add current message
            messages.append({'role': 'user', 'content': content})

            data = {
                'model': model,
                'messages': messages,
                'max_tokens': 4000,  # Increased for longer responses
                'temperature': 0.7
            }

            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    'text': result['choices'][0]['message']['content'],
                    'provider': 'openai',
                    'timestamp': datetime.now().isoformat(),
                    'model': model
                }
            else:
                print(f"DEBUG: OpenAI API error: {response.status_code} - {response.text}")
                return {'error': f'OpenAI API error: {response.status_code} - {response.text}'}

        except Exception as e:
            print(f"DEBUG: Exception in OpenAI chat: {str(e)}")
            return {'error': f'OpenAI API error: {str(e)}'}

    def _chat_claude(self, message: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        if not ANTHROPIC_AVAILABLE:
            return {'error': 'Anthropic library not installed'}

        if not api_key:
            return {'error': 'Claude API key required'}

        if conversation_history is None:
            conversation_history = []

        print(f"DEBUG: Claude called with {len(conversation_history)} history messages")

        try:
            client = anthropic.Anthropic(api_key=api_key)

            # Build messages array with conversation history
            messages = []
            for hist_msg in conversation_history:
                role = hist_msg.get('role', 'user')
                content_text = hist_msg.get('content', '')
                messages.append({
                    "role": role,
                    "content": content_text
                })

            # Process files for Claude (current message)
            content = [{"type": "text", "text": message}]

            if files:
                for file_path in files:
                    if not os.path.exists(file_path):
                        continue

                    mime_type, _ = mimetypes.guess_type(file_path)

                    # Claude can handle images
                    if mime_type and mime_type.startswith('image/'):
                        with open(file_path, 'rb') as f:
                            image_data = base64.b64encode(f.read()).decode('utf-8')
                            content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": image_data
                                }
                            })
                    # Handle text files
                    elif mime_type in ['text/plain', 'text/csv', 'application/json']:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                file_content = f.read()[:10000]
                                content.append({
                                    "type": "text",
                                    "text": f"\n\nFile: {os.path.basename(file_path)}\n{file_content}"
                                })
                        except Exception as e:
                            content.append({
                                "type": "text",
                                "text": f"\n\nCould not read file {os.path.basename(file_path)}: {str(e)}"
                            })
                    # Handle PDFs, Word docs, and other documents
                    else:
                        try:
                            from app.utils.file_handler import FileHandler
                            text_content = FileHandler.extract_text(file_path)
                            content.append({
                                "type": "text",
                                "text": f"\n\nFile: {os.path.basename(file_path)} (Type: {mime_type or 'unknown'})\n\nContent:\n{text_content[:8000]}"
                            })
                        except Exception as e:
                            content.append({
                                "type": "text",
                                "text": f"\n\nUploaded file: {os.path.basename(file_path)} (Type: {mime_type or 'unknown'}) - Could not extract content: {str(e)}"
                            })

            # Add current message to messages array
            messages.append({"role": "user", "content": content})

            # Build system instruction for language
            system_instruction = None
            if language == 'ar':
                system_instruction = "You are a helpful AI assistant. Please respond in Arabic language. يرجى الرد باللغة العربية."

            # Use Claude 3 Haiku (fast, accessible model)
            create_params = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 4000,  # Increased for longer responses
                "messages": messages
            }
            
            # Add system instruction if language is Arabic
            if system_instruction:
                create_params["system"] = system_instruction
            
            response = client.messages.create(**create_params)

            return {
                'text': response.content[0].text,
                'provider': 'claude',
                'timestamp': datetime.now().isoformat(),
                'model': 'claude-3-sonnet'
            }
        except Exception as e:
            return {'error': f'Claude API error: {str(e)}'}

    def _chat_bedrock(self, message: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        """AWS Bedrock integration using Claude models via boto3"""
        if not BOTO3_AVAILABLE:
            return {'error': 'boto3 library not installed. Install with: pip install boto3'}
        
        if not api_key or '|' not in api_key:
            return {'error': 'AWS credentials required. Format: access_key|secret_key|region'}
        
        if conversation_history is None:
            conversation_history = []
        
        try:
            # Parse AWS credentials from api_key format: access_key|secret_key|region
            parts = api_key.split('|')
            aws_access_key = parts[0]
            aws_secret_key = parts[1]
            aws_region = parts[2] if len(parts) > 2 else 'us-west-2'
            
            # Initialize Bedrock runtime client
            bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name=aws_region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            )
            
            # Build messages array with conversation history
            messages = []
            for hist_msg in conversation_history:
                role = hist_msg.get('role', 'user')
                content_text = hist_msg.get('content', '')
                messages.append({
                    "role": role,
                    "content": [{"type": "text", "text": content_text}]
                })
            
            # Process files for current message
            content = [{"type": "text", "text": message}]
            
            if files:
                for file_path in files:
                    if not os.path.exists(file_path):
                        continue
                    
                    mime_type, _ = mimetypes.guess_type(file_path)
                    
                    # Bedrock Claude can handle images
                    if mime_type and mime_type.startswith('image/'):
                        with open(file_path, 'rb') as f:
                            image_data = base64.b64encode(f.read()).decode('utf-8')
                            content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": image_data
                                }
                            })
                    # Handle text files and documents
                    else:
                        try:
                            if mime_type in ['text/plain', 'text/csv', 'application/json']:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    file_content = f.read()[:10000]
                            else:
                                from app.utils.file_handler import FileHandler
                                file_content = FileHandler.extract_text(file_path)[:10000]
                            
                            content.append({
                                "type": "text",
                                "text": f"\n\nFile: {os.path.basename(file_path)}\n{file_content}"
                            })
                        except Exception as e:
                            content.append({
                                "type": "text",
                                "text": f"\n\nCould not read file {os.path.basename(file_path)}: {str(e)}"
                            })
            
            # Add current message
            messages.append({
                "role": "user",
                "content": content
            })
            
            # Use selected version or default to Claude Sonnet 4
            model_id = version if version else "anthropic.claude-sonnet-4-20250514-v1:0"
            
            # Get max_tokens from config or use default
            from config.config import Config
            config = Config()
            max_tokens = getattr(config, 'BEDROCK_MAX_TOKENS', 4000)
            temperature = getattr(config, 'BEDROCK_TEMPERATURE', 0.7)
            
            # Prepare request payload
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": messages,
                "temperature": temperature
            }
            
            # Call Bedrock API
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(payload)
            )
            
            # Parse response with error handling
            try:
                response_body = response['body'].read()
                result = json.loads(response_body)
                response_text = result['content'][0]['text']
            except (json.JSONDecodeError, KeyError) as e:
                return {'error': f'Failed to parse Bedrock response: {str(e)}'}
            
            # Get model display name from version
            model_names = {
                "anthropic.claude-sonnet-4-5-20250929-v1:0": "Claude Sonnet 4.5",
                "anthropic.claude-opus-4-20250514-v1:0": "Claude Opus 4",
                "anthropic.claude-sonnet-4-20250514-v1:0": "Claude Sonnet 4",
                "anthropic.claude-3-5-haiku-20241022-v1:0": "Claude 3.5 Haiku",
                "anthropic.claude-3-haiku-20240307-v1:0": "Claude 3 Haiku"
            }
            model_display = model_names.get(model_id, model_id) + " (AWS Bedrock)"
            
            return {
                'text': response_text,
                'provider': 'bedrock',
                'timestamp': datetime.now().isoformat(),
                'model': model_display
            }
            
        except Exception as e:
            return {'error': f'AWS Bedrock error: {str(e)}'}

    def _chat_llama_bedrock(self, message: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        """Meta Llama models via AWS Bedrock"""
        if not BOTO3_AVAILABLE:
            return {'error': 'boto3 library not installed'}
        
        if not api_key or '|' not in api_key:
            return {'error': 'AWS credentials required. Format: access_key|secret_key|region'}
        
        try:
            parts = api_key.split('|')
            bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name=parts[2] if len(parts) > 2 else 'us-west-2',
                aws_access_key_id=parts[0],
                aws_secret_access_key=parts[1]
            )
            
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
                'model': f"Llama (AWS Bedrock)"
            }
        except Exception as e:
            return {'error': f'Llama Bedrock error: {str(e)}'}

    def _chat_mistral_bedrock(self, message: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        """Mistral AI models via AWS Bedrock"""
        if not BOTO3_AVAILABLE:
            return {'error': 'boto3 library not installed'}
        
        if not api_key or '|' not in api_key:
            return {'error': 'AWS credentials required'}
        
        try:
            parts = api_key.split('|')
            bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name=parts[2] if len(parts) > 2 else 'us-west-2',
                aws_access_key_id=parts[0],
                aws_secret_access_key=parts[1]
            )
            
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
                'model': f"Mistral (AWS Bedrock)"
            }
        except Exception as e:
            return {'error': f'Mistral Bedrock error: {str(e)}'}

    def _chat_amazon_nova(self, message: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        """Amazon Nova models via AWS Bedrock"""
        if not BOTO3_AVAILABLE:
            return {'error': 'boto3 library not installed'}
        
        if not api_key or '|' not in api_key:
            return {'error': 'AWS credentials required'}
        
        try:
            parts = api_key.split('|')
            bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name=parts[2] if len(parts) > 2 else 'us-west-2',
                aws_access_key_id=parts[0],
                aws_secret_access_key=parts[1]
            )
            
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
                'model': f"Amazon Nova (AWS Bedrock)"
            }
        except Exception as e:
            return {'error': f'Amazon Nova error: {str(e)}'}

    def _chat_cohere_bedrock(self, message: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        """Cohere models via AWS Bedrock"""
        if not BOTO3_AVAILABLE:
            return {'error': 'boto3 library not installed'}
        
        if not api_key or '|' not in api_key:
            return {'error': 'AWS credentials required'}
        
        try:
            parts = api_key.split('|')
            bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name=parts[2] if len(parts) > 2 else 'us-west-2',
                aws_access_key_id=parts[0],
                aws_secret_access_key=parts[1]
            )
            
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
                'model': f"Cohere (AWS Bedrock)"
            }
        except Exception as e:
            return {'error': f'Cohere Bedrock error: {str(e)}'}

    def _chat_ai21_bedrock(self, message: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        """AI21 Labs models via AWS Bedrock"""
        if not BOTO3_AVAILABLE:
            return {'error': 'boto3 library not installed'}
        
        if not api_key or '|' not in api_key:
            return {'error': 'AWS credentials required'}
        
        try:
            parts = api_key.split('|')
            bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name=parts[2] if len(parts) > 2 else 'us-west-2',
                aws_access_key_id=parts[0],
                aws_secret_access_key=parts[1]
            )
            
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
                'model': f"AI21 (AWS Bedrock)"
            }
        except Exception as e:
            return {'error': f'AI21 Bedrock error: {str(e)}'}

    def _generate_stable_diffusion(self, prompt: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        """Stable Diffusion image generation via AWS Bedrock"""
        if not BOTO3_AVAILABLE:
            return {'error': 'boto3 library not installed'}
        
        if not api_key or '|' not in api_key:
            return {'error': 'AWS credentials required'}
        
        try:
            parts = api_key.split('|')
            bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name=parts[2] if len(parts) > 2 else 'us-west-2',
                aws_access_key_id=parts[0],
                aws_secret_access_key=parts[1]
            )
            
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

    def _chat_gemini(self, message: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        if not GENAI_AVAILABLE:
            return {'error': 'Google Generative AI library not installed'}

        if not api_key:
            return {'error': 'Gemini API key required'}

        try:
            genai.configure(api_key=api_key)

            # Check if we have images to use vision model
            has_images = False
            content_parts = [message]

            if files:
                for file_path in files:
                    if not os.path.exists(file_path):
                        continue

                    mime_type, _ = mimetypes.guess_type(file_path)

                    if mime_type and mime_type.startswith('image/'):
                        try:
                            with open(file_path, 'rb') as f:
                                image_data = f.read()
                                content_parts.append({
                                    'mime_type': mime_type,
                                    'data': image_data
                                })
                                has_images = True
                        except Exception as e:
                            content_parts.append(f"\nError reading image {os.path.basename(file_path)}: {str(e)}")

                    elif mime_type in ['text/plain', 'text/csv', 'application/json']:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                file_content = f.read()[:10000]
                                content_parts.append(f"\n\nFile: {os.path.basename(file_path)}\n{file_content}")
                        except Exception as e:
                            content_parts.append(f"\nCould not read file {os.path.basename(file_path)}: {str(e)}")
                    # Handle PDFs, Word docs, and other documents
                    else:
                        try:
                            from app.utils.file_handler import FileHandler
                            text_content = FileHandler.extract_text(file_path)
                            content_parts.append(f"\n\nFile: {os.path.basename(file_path)} (Type: {mime_type or 'unknown'})\n\nContent:\n{text_content[:8000]}")
                        except Exception as e:
                            content_parts.append(f"\nUploaded file: {os.path.basename(file_path)} (Type: {mime_type or 'unknown'}) - Could not extract content: {str(e)}")

            model_name = 'gemini-2.0-flash'
            model = genai.GenerativeModel(model_name)

            response = model.generate_content(content_parts)

            return {
                'text': response.text,
                'provider': 'gemini',
                'timestamp': datetime.now().isoformat(),
                'model': model_name
            }
        except Exception as e:
            return {'error': f'Gemini API error: {str(e)}'}

    def _generate_dalle(self, prompt: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        if not api_key:
            return {'error': 'OpenAI API key required for DALL-E'}

        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                'model': 'dall-e-3',
                'prompt': prompt,
                'n': 1,
                'size': '1024x1024',
                'quality': 'standard',
                'response_format': 'b64_json'  # Get base64 instead of URL
            }

            response = requests.post(
                'https://api.openai.com/v1/images/generations',
                headers=headers,
                json=data,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()

                # Save image to uploads directory
                b64_data = result['data'][0]['b64_json']
                image_data = base64.b64decode(b64_data)

                # Generate unique filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'dalle_generated_{timestamp}.png'
                filepath = os.path.join('uploads', filename)

                # Ensure uploads directory exists
                os.makedirs('uploads', exist_ok=True)

                with open(filepath, 'wb') as f:
                    f.write(image_data)

                # Return both base64 and file path with download URL
                return {
                    'text': f'Generated image saved as {filename}',
                    'image_url': f'data:image/png;base64,{b64_data}',
                    'image_path': filepath,
                    'filename': filename,
                    'download_url': f'/api/downloads/dalle/{filename}',
                    'provider': 'dalle',
                    'timestamp': datetime.now().isoformat(),
                    'model': 'dall-e-3'
                }
            else:
                return {'error': f'DALL-E API error: {response.status_code} - {response.text}'}

        except Exception as e:
            return {'error': f'DALL-E API error: {str(e)}'}

    def _chat_grok(self, message: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        """Real Grok API integration using X.AI API"""
        if not api_key:
            return {'error': 'Grok API key required'}

        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            # Add file content to message if files are present
            enhanced_message = message
            if files:
                file_contents = []
                for file_path in files:
                    if not os.path.exists(file_path):
                        continue
                    
                    mime_type, _ = mimetypes.guess_type(file_path)
                    
                    # Grok doesn't support images - warn user
                    if mime_type and mime_type.startswith('image/'):
                        file_contents.append(f"\n\n⚠️ Note: {os.path.basename(file_path)} is an image. Grok doesn't support image analysis.")
                        continue
                    
                    # Handle text files
                    if mime_type in ['text/plain', 'text/csv', 'application/json']:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()[:8000]
                                file_contents.append(f"\n\n--- File: {os.path.basename(file_path)} ---\n{content}")
                        except Exception as e:
                            file_contents.append(f"\n\nCould not read {os.path.basename(file_path)}: {str(e)}")
                    # Handle PDFs, Word docs, and other documents
                    else:
                        try:
                            from app.utils.file_handler import FileHandler
                            text_content = FileHandler.extract_text(file_path)
                            file_contents.append(f"\n\n--- File: {os.path.basename(file_path)} (Type: {mime_type or 'unknown'}) ---\n{text_content[:8000]}")
                        except Exception as e:
                            file_contents.append(f"\n\nUploaded file: {os.path.basename(file_path)} - Could not extract content: {str(e)}")
                
                if file_contents:
                    enhanced_message += "\n\n=== UPLOADED FILES ===\n" + "\n".join(file_contents)

            # Use version parameter or default to grok-3 (grok-beta and grok-2 are deprecated)
            model = version if version else 'grok-3'
            
            data = {
                'model': model,
                'messages': [{'role': 'user', 'content': enhanced_message}],
                'max_tokens': 3000,
                'temperature': 0.7
            }

            response = requests.post(
                'https://api.x.ai/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    'text': result['choices'][0]['message']['content'],
                    'provider': 'grok',
                    'timestamp': datetime.now().isoformat(),
                    'model': result.get('model', 'grok-2-1212'),
                    'usage': result.get('usage', {})
                }
            else:
                return {'error': f'Grok API error: {response.status_code} - {response.text}'}

        except Exception as e:
            return {'error': f'Grok API error: {str(e)}'}

    def _chat_deepseek(self, message: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        """Real DeepSeek API integration"""
        if not api_key:
            return {'error': 'DeepSeek API key required'}

        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            # Add file content to message if files are present
            enhanced_message = message
            if files:
                file_contents = []
                for file_path in files:
                    if not os.path.exists(file_path):
                        continue
                    
                    mime_type, _ = mimetypes.guess_type(file_path)
                    
                    # DeepSeek doesn't support images - warn user
                    if mime_type and mime_type.startswith('image/'):
                        file_contents.append(f"\n\n⚠️ Note: {os.path.basename(file_path)} is an image. DeepSeek doesn't support image analysis.")
                        continue
                    
                    # Handle text files (especially code files for DeepSeek)
                    if mime_type in ['text/plain', 'text/csv', 'application/json'] or \
                       file_path.endswith(('.py', '.js', '.java', '.cpp', '.c', '.ts', '.jsx', '.tsx', '.go', '.rb', '.php', '.html', '.css')):
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()[:10000]  # DeepSeek is good with code
                                file_contents.append(f"\n\n--- File: {os.path.basename(file_path)} ---\n{content}")
                        except Exception as e:
                            file_contents.append(f"\n\nCould not read {os.path.basename(file_path)}: {str(e)}")
                    # Handle PDFs, Word docs, and other documents
                    else:
                        try:
                            from app.utils.file_handler import FileHandler
                            text_content = FileHandler.extract_text(file_path)
                            file_contents.append(f"\n\n--- File: {os.path.basename(file_path)} (Type: {mime_type or 'unknown'}) ---\n{text_content[:8000]}")
                        except Exception as e:
                            file_contents.append(f"\n\nUploaded file: {os.path.basename(file_path)} - Could not extract content: {str(e)}")
                
                if file_contents:
                    enhanced_message += "\n\n=== UPLOADED FILES ===\n" + "\n".join(file_contents)

            # Build messages with system prompt for language control
            messages = []
            
            # Add system message to control response language
            # DeepSeek defaults to Chinese, so we must explicitly set language
            lang_name = 'English' if language == 'en' else 'Arabic' if language == 'ar' else 'English'
            system_prompt = f"You are a helpful AI assistant. Always respond in {lang_name}. Do not respond in Chinese unless the user explicitly asks you to."
            messages.append({'role': 'system', 'content': system_prompt})
            
            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history[-10:]:  # Last 10 messages for context
                    messages.append({
                        'role': msg.get('role', 'user'),
                        'content': msg.get('content', '')
                    })
            
            # Add current user message
            messages.append({'role': 'user', 'content': enhanced_message})
            
            data = {
                'model': 'deepseek-chat',
                'messages': messages,
                'max_tokens': 3000,
                'temperature': 0.7
            }

            response = requests.post(
                'https://api.deepseek.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    'text': result['choices'][0]['message']['content'],
                    'provider': 'deepseek',
                    'timestamp': datetime.now().isoformat(),
                    'model': result.get('model', 'deepseek-chat'),
                    'usage': result.get('usage', {})
                }
            else:
                return {'error': f'DeepSeek API error: {response.status_code} - {response.text}'}

        except Exception as e:
            return {'error': f'DeepSeek API error: {str(e)}'}

    def _chat_llama(self, message: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        file_info = ""
        if files:
            file_names = [os.path.basename(f) for f in files if os.path.exists(f)]
            file_info = f" (with {len(file_names)} file(s): {', '.join(file_names)})"

        return {
            'text': f'Mock Llama response to: "{message}"{file_info}',
            'provider': 'llama',
            'timestamp': datetime.now().isoformat(),
            'model': 'llama-2-70b'
        }

    def _chat_perplexity(self, message: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        if not api_key:
            return {'error': 'Perplexity API key required'}

        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            # Add file information to message if files are present
            enhanced_message = message
            if files:
                file_names = [os.path.basename(f) for f in files if os.path.exists(f)]
                if file_names:
                    enhanced_message += f"\n\nNote: User has uploaded {len(file_names)} file(s): {', '.join(file_names)}"

            # Use version parameter or default to sonar-pro (2025 model)
            model = version if version else 'sonar-pro'

            # Build messages with conversation history
            messages = []
            if conversation_history:
                for msg in conversation_history[-10:]:
                    messages.append({
                        'role': msg.get('role', 'user'),
                        'content': msg.get('content', '')
                    })
            messages.append({'role': 'user', 'content': enhanced_message})

            data = {
                'model': model,
                'messages': messages,
                'max_tokens': 2000,
                'temperature': 0.2,
                'return_citations': True
            }

            # Increased timeout to 120 seconds for Perplexity's search functionality
            response = requests.post(
                'https://api.perplexity.ai/chat/completions',
                headers=headers,
                json=data,
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Add citations if available
                citations = result.get('citations', [])
                if citations:
                    content += "\n\n**Sources:**\n"
                    for i, cite in enumerate(citations[:5], 1):
                        content += f"{i}. {cite}\n"
                
                return {
                    'text': content,
                    'provider': 'perplexity',
                    'timestamp': datetime.now().isoformat(),
                    'model': result.get('model', model),
                    'usage': result.get('usage', {})
                }
            else:
                error_text = response.text[:200] if response.text else 'Unknown error'
                return {'error': f'Perplexity API error: {response.status_code} - {error_text}'}

        except Exception as e:
            return {'error': f'Perplexity API error: {str(e)}'}

    def _analyze_clarifai(self, image_url: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        file_info = ""
        if files:
            file_names = [os.path.basename(f) for f in files if os.path.exists(f)]
            file_info = f" with {len(file_names)} file(s): {', '.join(file_names)}"

        return {
            'text': f'Mock Clarifai analysis of content{file_info}',
            'provider': 'clarifai',
            'timestamp': datetime.now().isoformat(),
            'model': 'general-image-recognition'
        }

    def _query_census(self, query: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
        file_info = ""
        if files:
            file_names = [os.path.basename(f) for f in files if os.path.exists(f)]
            file_info = f" (analyzing {len(file_names)} file(s): {', '.join(file_names)})"

        return {
            'text': f'Mock Census data response for: "{query}"{file_info}',
            'provider': 'census',
            'timestamp': datetime.now().isoformat(),
            'model': 'census-api'
        }

    def generate_image(self, prompt: str, api_key: str) -> Dict[str, Any]:
        return self._generate_dalle(prompt, api_key)

    def analyze_image(self, image_url: str, api_key: str) -> Dict[str, Any]:
        return self._analyze_clarifai(image_url, api_key)
    def _chat_dify(self, message: str, api_key: str, files: List[str] = None, conversation_history: List[Dict[str, str]] = None, version: str = None, language: str = 'en') -> Dict[str, Any]:
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
