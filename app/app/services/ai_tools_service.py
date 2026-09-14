"""
AI Tools Service - Comprehensive AI-powered tools for all user roles
Provides text generation, summarization, translation, content creation, and analysis tools
"""
import json
from typing import Dict, Any, List, Optional
from app.services.ai_service import AIService

AI_TOOLS_CONFIG = {
    "common": [
        {
            "id": "text_generator",
            "name": "Text Generator",
            "name_ar": "مولد النصوص",
            "icon": "fa-pen-fancy",
            "description": "Generate creative, professional, or academic text on any topic",
            "description_ar": "إنشاء نصوص إبداعية أو مهنية أو أكاديمية حول أي موضوع",
            "category": "content"
        },
        {
            "id": "summarizer",
            "name": "Text Summarizer",
            "name_ar": "ملخص النصوص",
            "icon": "fa-compress-alt",
            "description": "Condense long documents into key points and summaries",
            "description_ar": "تلخيص المستندات الطويلة إلى نقاط رئيسية وملخصات",
            "category": "content"
        },
        {
            "id": "translator",
            "name": "Smart Translator",
            "name_ar": "المترجم الذكي",
            "icon": "fa-language",
            "description": "Translate text between English, Arabic, and other languages",
            "description_ar": "ترجمة النصوص بين الإنجليزية والعربية واللغات الأخرى",
            "category": "content"
        },
        {
            "id": "grammar_checker",
            "name": "Grammar & Style Checker",
            "name_ar": "مدقق القواعد والأسلوب",
            "icon": "fa-spell-check",
            "description": "Check and improve grammar, spelling, and writing style",
            "description_ar": "فحص وتحسين القواعد والإملاء وأسلوب الكتابة",
            "category": "content"
        },
        {
            "id": "paraphraser",
            "name": "Paraphraser",
            "name_ar": "معيد الصياغة",
            "icon": "fa-sync-alt",
            "description": "Rewrite text while preserving meaning with different tones",
            "description_ar": "إعادة صياغة النص مع الحفاظ على المعنى بأساليب مختلفة",
            "category": "content"
        }
    ],
    "teacher": [
        {
            "id": "lesson_planner",
            "name": "Lesson Plan Generator",
            "name_ar": "مولد خطط الدروس",
            "icon": "fa-chalkboard-teacher",
            "description": "Create detailed lesson plans with objectives, activities, and assessments",
            "description_ar": "إنشاء خطط دروس مفصلة مع الأهداف والأنشطة والتقييمات",
            "category": "teaching"
        },
        {
            "id": "question_generator",
            "name": "Question Bank Generator",
            "name_ar": "مولد بنك الأسئلة",
            "icon": "fa-question-circle",
            "description": "Generate exam questions based on Bloom's Taxonomy levels",
            "description_ar": "إنشاء أسئلة امتحانات بناءً على مستويات تصنيف بلوم",
            "category": "assessment"
        },
        {
            "id": "rubric_creator",
            "name": "Rubric Creator",
            "name_ar": "منشئ معايير التقييم",
            "icon": "fa-table",
            "description": "Create grading rubrics for assignments and projects",
            "description_ar": "إنشاء معايير تقييم للواجبات والمشاريع",
            "category": "assessment"
        },
        {
            "id": "feedback_generator",
            "name": "Student Feedback Generator",
            "name_ar": "مولد ملاحظات الطلاب",
            "icon": "fa-comment-dots",
            "description": "Generate personalized constructive feedback for student work",
            "description_ar": "إنشاء ملاحظات بناءة مخصصة لأعمال الطلاب",
            "category": "assessment"
        },
        {
            "id": "presentation_creator",
            "name": "Presentation Outline Creator",
            "name_ar": "منشئ مخطط العروض",
            "icon": "fa-desktop",
            "description": "Create presentation outlines and slide content",
            "description_ar": "إنشاء مخططات العروض ومحتوى الشرائح",
            "category": "teaching"
        },
        {
            "id": "differentiation_tool",
            "name": "Content Differentiation Tool",
            "name_ar": "أداة تمييز المحتوى",
            "icon": "fa-users-cog",
            "description": "Adapt content for different learning levels and styles",
            "description_ar": "تكييف المحتوى لمستويات وأنماط تعلم مختلفة",
            "category": "teaching"
        },
        {
            "id": "activity_generator",
            "name": "Learning Activity Generator",
            "name_ar": "مولد أنشطة التعلم",
            "icon": "fa-puzzle-piece",
            "description": "Create engaging learning activities and exercises",
            "description_ar": "إنشاء أنشطة تعليمية وتمارين جذابة",
            "category": "teaching"
        },
        {
            "id": "content_simplifier",
            "name": "Content Simplifier",
            "name_ar": "مبسط المحتوى",
            "icon": "fa-level-down-alt",
            "description": "Simplify complex topics for different comprehension levels",
            "description_ar": "تبسيط المواضيع المعقدة لمستويات فهم مختلفة",
            "category": "teaching"
        }
    ],
    "student": [
        {
            "id": "content_chat",
            "name": "Chat with Content",
            "name_ar": "الدردشة مع المحتوى",
            "icon": "fa-comments",
            "description": "Ask questions about your course documents, slides, and materials",
            "description_ar": "اطرح أسئلة حول مستندات الدورة والشرائح والمواد",
            "category": "learning"
        },
        {
            "id": "study_assistant",
            "name": "Study Assistant",
            "name_ar": "مساعد الدراسة",
            "icon": "fa-graduation-cap",
            "description": "Get explanations, examples, and study tips for any topic",
            "description_ar": "احصل على شروحات وأمثلة ونصائح دراسية لأي موضوع",
            "category": "learning"
        },
        {
            "id": "flashcard_generator",
            "name": "Flashcard Generator",
            "name_ar": "مولد البطاقات التعليمية",
            "icon": "fa-clone",
            "description": "Create study flashcards from your notes or topics",
            "description_ar": "إنشاء بطاقات تعليمية من ملاحظاتك أو مواضيعك",
            "category": "learning"
        },
        {
            "id": "concept_explainer",
            "name": "Concept Explainer",
            "name_ar": "شارح المفاهيم",
            "icon": "fa-lightbulb",
            "description": "Get simple explanations for complex concepts",
            "description_ar": "احصل على شروحات بسيطة للمفاهيم المعقدة",
            "category": "learning"
        },
        {
            "id": "practice_quiz",
            "name": "Practice Quiz Generator",
            "name_ar": "مولد اختبارات التدريب",
            "icon": "fa-tasks",
            "description": "Generate practice quizzes to test your knowledge",
            "description_ar": "إنشاء اختبارات تدريبية لاختبار معرفتك",
            "category": "assessment"
        },
        {
            "id": "essay_helper",
            "name": "Essay Writing Helper",
            "name_ar": "مساعد كتابة المقالات",
            "icon": "fa-file-alt",
            "description": "Get help with essay structure, thesis, and arguments",
            "description_ar": "احصل على مساعدة في هيكل المقال والأطروحة والحجج",
            "category": "writing"
        },
        {
            "id": "note_organizer",
            "name": "Note Organizer",
            "name_ar": "منظم الملاحظات",
            "icon": "fa-sticky-note",
            "description": "Organize and structure your study notes",
            "description_ar": "تنظيم وهيكلة ملاحظات دراستك",
            "category": "learning"
        },
        {
            "id": "learning_path_advisor",
            "name": "Learning Path Advisor",
            "name_ar": "مستشار مسار التعلم",
            "icon": "fa-route",
            "description": "Get personalized study recommendations and learning paths",
            "description_ar": "احصل على توصيات دراسية مخصصة ومسارات تعلم",
            "category": "planning"
        },
        {
            "id": "motivation_coach",
            "name": "Motivation Coach",
            "name_ar": "مدرب التحفيز",
            "icon": "fa-star",
            "description": "Get motivational support and study productivity tips",
            "description_ar": "احصل على دعم تحفيزي ونصائح لإنتاجية الدراسة",
            "category": "support"
        }
    ],
    "admin": [
        {
            "id": "report_generator",
            "name": "Report Generator",
            "name_ar": "مولد التقارير",
            "icon": "fa-chart-bar",
            "description": "Generate comprehensive analytics and performance reports",
            "description_ar": "إنشاء تقارير تحليلية شاملة وتقارير الأداء",
            "category": "analytics"
        },
        {
            "id": "policy_writer",
            "name": "Policy Document Writer",
            "name_ar": "كاتب وثائق السياسات",
            "icon": "fa-file-contract",
            "description": "Draft policy documents and guidelines",
            "description_ar": "صياغة وثائق السياسات والإرشادات",
            "category": "documentation"
        },
        {
            "id": "announcement_creator",
            "name": "Announcement Creator",
            "name_ar": "منشئ الإعلانات",
            "icon": "fa-bullhorn",
            "description": "Create professional announcements and communications",
            "description_ar": "إنشاء إعلانات واتصالات مهنية",
            "category": "communication"
        },
        {
            "id": "email_composer",
            "name": "Email Composer",
            "name_ar": "محرر البريد الإلكتروني",
            "icon": "fa-envelope",
            "description": "Compose professional emails for various purposes",
            "description_ar": "تحرير رسائل بريد إلكتروني مهنية لأغراض مختلفة",
            "category": "communication"
        },
        {
            "id": "meeting_minutes",
            "name": "Meeting Minutes Generator",
            "name_ar": "مولد محاضر الاجتماعات",
            "icon": "fa-clipboard-list",
            "description": "Generate structured meeting minutes from notes",
            "description_ar": "إنشاء محاضر اجتماعات منظمة من الملاحظات",
            "category": "documentation"
        },
        {
            "id": "course_description",
            "name": "Course Description Writer",
            "name_ar": "كاتب وصف المقررات",
            "icon": "fa-book-open",
            "description": "Create professional course descriptions and outlines",
            "description_ar": "إنشاء أوصاف ومخططات مقررات مهنية",
            "category": "curriculum"
        },
        {
            "id": "data_analyzer",
            "name": "Data Insights Analyzer",
            "name_ar": "محلل رؤى البيانات",
            "icon": "fa-chart-line",
            "description": "Analyze data and extract meaningful insights",
            "description_ar": "تحليل البيانات واستخراج رؤى ذات معنى",
            "category": "analytics"
        },
        {
            "id": "compliance_checker",
            "name": "Compliance Checker",
            "name_ar": "مدقق الامتثال",
            "icon": "fa-shield-alt",
            "description": "Check documents for compliance with standards",
            "description_ar": "فحص المستندات للتأكد من الامتثال للمعايير",
            "category": "quality"
        }
    ]
}

TOOL_PROMPTS = {
    "content_chat": """You are a helpful teaching assistant with access to course materials. Answer the student's question based ONLY on the provided document content. If the answer is not in the document, say so clearly.

Document Title: {document_title}
Document Content:
{document_content}

Student's Question: {input}
Language: {language}

Provide a clear, helpful answer based on the document content. Include relevant quotes or references when appropriate.""",

    "text_generator": """You are a professional content writer. Generate high-quality text based on the user's request.
Topic/Request: {input}
Tone: {tone}
Length: {length}
Language: {language}

Generate engaging, well-structured content that matches the specified requirements.""",

    "summarizer": """You are an expert at summarizing text while preserving key information.
Text to summarize:
{input}

Summary type: {summary_type}
Length: {length}
Language: {language}

Provide a clear, concise summary that captures the essential points.""",

    "translator": """You are a professional translator with expertise in multiple languages.
Text to translate:
{input}

Source language: {source_lang}
Target language: {target_lang}

Provide an accurate, natural-sounding translation that preserves the meaning and tone.""",

    "grammar_checker": """You are an expert editor and proofreader.
Text to check:
{input}

Language: {language}
Style preference: {style}

Analyze the text and provide:
1. Corrected version
2. List of corrections made
3. Writing improvement suggestions""",

    "paraphraser": """You are an expert at rewriting text while preserving meaning.
Text to paraphrase:
{input}

Tone: {tone}
Style: {style}
Language: {language}

Provide a paraphrased version that maintains the original meaning but with fresh expression.""",

    "lesson_planner": """You are an experienced curriculum designer and educator.
Topic: {topic}
Subject: {subject}
Grade/Level: {level}
Duration: {duration}
Language: {language}

Create a comprehensive lesson plan including:
1. Learning objectives (SMART goals)
2. Materials needed
3. Introduction/Hook (5-10 min)
4. Main activities with timing
5. Student engagement strategies
6. Assessment methods
7. Differentiation strategies
8. Closure and homework""",

    "question_generator": """You are an expert assessment designer following Bloom's Taxonomy.
Topic: {topic}
Subject: {subject}
Difficulty level: {difficulty}
Question types: {question_types}
Number of questions: {num_questions}
Language: {language}

Generate questions at these Bloom's levels:
- Remembering: Recall facts
- Understanding: Explain concepts
- Applying: Use in new situations
- Analyzing: Break down information
- Evaluating: Make judgments
- Creating: Produce new work

Provide questions with answer keys and point values.""",

    "rubric_creator": """You are an assessment expert skilled in creating fair, comprehensive rubrics.
Assignment: {assignment}
Subject: {subject}
Grade level: {level}
Criteria to evaluate: {criteria}
Language: {language}

Create a detailed rubric with:
1. Clear criteria categories
2. 4-point scale (Exemplary, Proficient, Developing, Beginning)
3. Specific descriptors for each level
4. Point values
5. Total possible points""",

    "feedback_generator": """You are a supportive educator providing constructive feedback.
Student work description: {input}
Assignment type: {assignment_type}
Areas to address: {areas}
Tone: {tone}
Language: {language}

Provide feedback that:
1. Starts with positive observations
2. Identifies specific areas for improvement
3. Offers concrete suggestions
4. Encourages growth mindset
5. Ends with motivation""",

    "study_assistant": """You are a patient, knowledgeable study assistant.
Topic/Question: {input}
Subject area: {subject}
Current understanding level: {level}
Language: {language}

Help the student by:
1. Explaining the concept clearly
2. Providing relevant examples
3. Suggesting study strategies
4. Offering practice problems if applicable
5. Connecting to related concepts""",

    "flashcard_generator": """You are a learning specialist creating effective flashcards.
Topic: {topic}
Content/Notes: {input}
Number of flashcards: {num_cards}
Language: {language}

Create flashcards with:
- Clear, concise questions/prompts on front
- Complete, accurate answers on back
- Mix of factual recall and conceptual understanding
- Progressive difficulty""",

    "concept_explainer": """You are an expert teacher who excels at explaining complex ideas simply.
Concept: {input}
Subject area: {subject}
Current knowledge level: {level}
Learning style preference: {learning_style}
Language: {language}

Explain this concept using:
1. Simple language and analogies
2. Real-world examples
3. Visual descriptions if helpful
4. Step-by-step breakdown
5. Common misconceptions to avoid""",

    "essay_helper": """You are a writing coach helping students improve their essays.
Essay topic: {topic}
Essay type: {essay_type}
Current draft/outline: {input}
Help needed: {help_type}
Language: {language}

Provide guidance on:
1. Thesis statement development
2. Argument structure
3. Evidence and support
4. Transitions and flow
5. Introduction and conclusion hooks""",

    "report_generator": """You are a business analyst creating professional reports.
Report type: {report_type}
Data/Information: {input}
Time period: {period}
Key metrics to include: {metrics}
Language: {language}

Generate a comprehensive report with:
1. Executive summary
2. Key findings
3. Data analysis
4. Trends and patterns
5. Recommendations
6. Action items""",

    "announcement_creator": """You are a communications specialist.
Announcement purpose: {purpose}
Key information: {input}
Target audience: {audience}
Tone: {tone}
Language: {language}

Create a clear, engaging announcement that:
1. Captures attention
2. Delivers key information
3. Includes necessary details
4. Has clear call-to-action
5. Maintains appropriate tone"""
}


class AIToolsService:
    def __init__(self):
        self.ai_service = AIService()
        self.model_to_provider = {
            'gpt-4.1': 'openai',
            'gpt-4': 'openai',
            'gpt-4-turbo': 'openai',
            'gpt-3.5-turbo': 'openai',
            'claude-3-opus': 'claude',
            'claude-3-sonnet': 'claude',
            'claude-3-haiku': 'claude',
            'gemini-pro': 'gemini',
            'gemini-1.5-pro': 'gemini',
            'deepseek-chat': 'deepseek',
            'deepseek-coder': 'deepseek',
            'grok-1': 'grok',
            'perplexity': 'perplexity',
            'llama': 'llama'
        }
    
    def _get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider from config"""
        from config.config import Config
        config = Config()
        key_mapping = {
            'openai': 'OPENAI_API_KEY',
            'claude': 'CLAUDE_API_KEY',
            'gemini': 'GEMINI_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
            'grok': 'GROK_API_KEY',
            'perplexity': 'PERPLEXITY_API_KEY'
        }
        key_name = key_mapping.get(provider)
        if key_name:
            return getattr(config, key_name, None)
        return None
    
    def get_tools_for_role(self, role: str) -> List[Dict]:
        """Get available tools based on user role"""
        tools = AI_TOOLS_CONFIG.get("common", []).copy()
        
        role_lower = role.lower() if role else ""
        
        if role_lower in ['teacher', 'instructor']:
            tools.extend(AI_TOOLS_CONFIG.get("teacher", []))
        elif role_lower in ['student']:
            tools.extend(AI_TOOLS_CONFIG.get("student", []))
        elif role_lower in ['admin', 'super_admin', 'superadmin', 'institution_admin']:
            tools.extend(AI_TOOLS_CONFIG.get("admin", []))
            tools.extend(AI_TOOLS_CONFIG.get("teacher", []))
        
        return tools
    
    def get_all_tools(self) -> Dict[str, List[Dict]]:
        """Get all tools organized by category"""
        return AI_TOOLS_CONFIG
    
    def execute_tool(self, tool_id: str, params: Dict[str, Any], model: str = "gpt-4.1") -> Dict[str, Any]:
        """Execute an AI tool with given parameters"""
        if tool_id not in TOOL_PROMPTS:
            return {"error": f"Unknown tool: {tool_id}", "success": False}
        
        prompt_template = TOOL_PROMPTS[tool_id]
        
        default_params = {
            "input": "",
            "language": "English",
            "tone": "professional",
            "style": "clear",
            "length": "medium",
            "level": "intermediate",
            "subject": "general",
            "topic": "",
            "summary_type": "key points",
            "source_lang": "auto-detect",
            "target_lang": "English",
            "difficulty": "mixed",
            "question_types": "multiple choice, true/false, short answer",
            "num_questions": "5",
            "num_cards": "10",
            "assignment": "",
            "criteria": "",
            "assignment_type": "general",
            "areas": "content, structure, clarity",
            "learning_style": "mixed",
            "essay_type": "argumentative",
            "help_type": "general improvement",
            "report_type": "summary",
            "period": "current",
            "metrics": "key performance indicators",
            "purpose": "general announcement",
            "audience": "all users",
            "duration": "60 minutes"
        }
        
        merged_params = {**default_params, **params}
        
        try:
            prompt = prompt_template.format(**merged_params)
        except KeyError as e:
            return {"error": f"Missing required parameter: {e}", "success": False}
        
        # Determine provider from model name
        provider = self.model_to_provider.get(model, 'openai')
        
        # Get API key for provider
        api_key = self._get_api_key(provider)
        if not api_key:
            return {
                "success": False,
                "error": f"No API key configured for {provider}. Please configure it in the settings."
            }
        
        try:
            # Use the chat method with proper parameters
            response = self.ai_service.chat(
                provider=provider,
                message=prompt,
                api_key=api_key,
                files=None,
                conversation_history=[],
                version=model,
                language=merged_params.get("language", "en")
            )
            
            # Check for errors in response
            if "error" in response:
                return {
                    "success": False,
                    "error": response.get("error", "Unknown error occurred")
                }
            
            # Extract the text response
            result_text = response.get("text", response.get("content", ""))
            
            return {
                "success": True,
                "result": result_text,
                "tool_id": tool_id,
                "model_used": model
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


ai_tools_service = AIToolsService()
