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
            "id": "programming_tutor",
            "name": "Programming Tutor",
            "name_ar": "مدرّس البرمجة",
            "icon": "fa-code",
            "description": "Interactive programming lessons with runnable, production-quality code examples",
            "description_ar": "دروس برمجة تفاعلية مع أمثلة كود حقيقية قابلة للتشغيل",
            "category": "programming"
        },
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

# Global directive appended to every tool prompt. Forces any code the model
# emits to be complete, runnable, and copy-pasteable into a real project —
# not pseudo-code, not snippets with "..." or "# your code here" placeholders.
CODE_OUTPUT_RULES = """

---
CODE OUTPUT STANDARDS (apply only when your answer contains code):
1. Wrap every code block in a fenced markdown block with the language tag,
   e.g. ```python ... ``` or ```javascript ... ```.
2. Code must be COMPLETE and RUNNABLE as-is. Include all imports, type
   hints where idiomatic, and any setup needed to execute the example.
3. Never use placeholders like `...`, `# TODO`, `# your code here`,
   `pass`, or omitted function bodies. Write the real implementation.
4. Handle obvious error cases (invalid input, missing files, network
   failures) the way production code would. Prefer raising specific
   exceptions over silent failures.
5. Add a short header comment explaining what the file does, and inline
   comments only where the intent is non-obvious.
6. After the code, list:
   - How to run it (exact command, e.g. `python solution.py` or
     `node index.js`).
   - Expected output for the given example input.
   - Any package install commands required (e.g. `pip install requests`).
7. Never invent APIs, library names, or function signatures. If you're
   not sure something exists, say so and use only standard-library APIs."""

TOOL_PROMPTS = {
    "programming_tutor": """You are an expert programming instructor and senior software engineer. Teach the requested topic in a clear, hands-on lesson that the learner can immediately try in their own editor.

Programming language: {pl_language}
Topic / concept: {input}
Learner level: {learner_level}
Lesson focus: {lesson_focus}
Interface language: {language}

Structure your response in this exact order, using markdown headings:

## 1. What you'll learn
Two or three bullet points stating the concrete skill the learner will walk away with.

## 2. Concept explanation
Explain the topic in plain language with one or two real-world analogies. Tailor the depth to the learner level (avoid jargon for beginners; assume fundamentals for advanced).

## 3. Worked example
A small, realistic problem the concept solves. Show the COMPLETE solution as a single runnable file. Include imports, a `__main__` guard (or equivalent entry point), realistic example data, and the expected output as a comment at the bottom. The code must run unchanged.

## 4. Step-by-step walkthrough
Reference specific lines from your code and explain why each non-trivial line is there.

## 5. Common pitfalls
Three to five mistakes learners typically make with this topic, each with a one-line fix.

## 6. Practice exercises
Two exercises ordered easy → harder. For each, give:
- The problem statement
- A starter code block with the function signature and docstring already filled in (but the body must be a real working solution, NOT `pass` — collapse it under a `<details>` block titled "Reference solution" so learners can attempt it first).
- Sample input and expected output.

## 7. Where to go next
Two or three follow-up topics or library docs links (only well-known, real URLs — never invent links).""",

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
            'gpt-4.1-mini': 'openai',
            'gpt-4.1-nano': 'openai',
            'gpt-4o': 'openai',
            'gpt-4o-mini': 'openai',
            'o3-mini': 'openai',
            'gpt-4': 'openai',
            'gpt-4-turbo': 'openai',
            'claude-sonnet-4-5-20250929': 'claude',
            'claude-opus-4-20250514': 'claude',
            'claude-sonnet-4-20250514': 'claude',
            'claude-haiku-3-5-20241022': 'claude',
            'claude-3-opus': 'claude',
            'claude-3-sonnet': 'claude',
            'claude-3-haiku': 'claude',
            'gemini-2.5-flash': 'gemini',
            'gemini-2.5-pro': 'gemini',
            'gemini-2.0-flash': 'gemini',
            'gemini-1.5-pro': 'gemini',
            'gemini-pro': 'gemini',
            'deepseek-chat': 'deepseek',
            'deepseek-reasoner': 'deepseek',
            'deepseek-coder': 'deepseek',
            'grok-3': 'grok',
            'grok-3-mini': 'grok',
            'sonar-pro': 'perplexity',
            'sonar': 'perplexity',
            'sonar-reasoning-pro': 'perplexity',
            'sonar-reasoning': 'perplexity',
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
            "duration": "60 minutes",
            # Programming Tutor defaults
            "pl_language": "Python",
            "learner_level": "beginner",
            "lesson_focus": "concept + worked example + practice"
        }
        
        merged_params = {**default_params, **params}
        
        try:
            prompt = prompt_template.format(**merged_params)
        except KeyError as e:
            return {"error": f"Missing required parameter: {e}", "success": False}

        # Append the global code-output standards so every tool produces
        # realistic, copy-pasteable code whenever code is part of the answer.
        prompt = prompt + CODE_OUTPUT_RULES
        
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


# ---------------------------------------------------------------------------
# Ready-made prompt library
# ---------------------------------------------------------------------------
# A curated set of starter prompts surfaced as one-click chips in the tool
# modal. Each entry has a short title (EN/AR) and the actual prompt text
# (EN/AR) that gets dropped into the input field. Optional `params` pre-fill
# matching dropdowns/extra fields on the same form.
PROMPT_LIBRARY: Dict[str, List[Dict[str, Any]]] = {
    "programming_tutor": [
        {"title": "Python: list vs tuple vs set", "title_ar": "بايثون: list مقابل tuple مقابل set",
         "prompt": "Explain the differences between list, tuple, and set in Python. When should I use each one in real code?",
         "prompt_ar": "اشرح الفرق بين list و tuple و set في بايثون. متى أستخدم كل واحدة في كود حقيقي؟",
         "params": {"pl_language": "Python", "learner_level": "beginner"}},
        {"title": "Python: async/await with aiohttp", "title_ar": "بايثون: async/await مع aiohttp",
         "prompt": "Teach me async/await in Python by building a small script that fetches 5 URLs in parallel using aiohttp.",
         "prompt_ar": "علّمني async/await في بايثون عبر بناء سكربت صغير يجلب 5 روابط بالتوازي باستخدام aiohttp.",
         "params": {"pl_language": "Python", "learner_level": "intermediate", "lesson_focus": "project tutorial"}},
        {"title": "JavaScript: promises & error handling", "title_ar": "جافاسكريبت: Promises ومعالجة الأخطاء",
         "prompt": "Explain JavaScript Promises and how to handle errors properly with .catch() and try/await.",
         "prompt_ar": "اشرح Promises في جافاسكريبت وكيفية معالجة الأخطاء بشكل صحيح باستخدام .catch() و try/await.",
         "params": {"pl_language": "JavaScript", "learner_level": "intermediate"}},
        {"title": "SQL: window functions for ranking", "title_ar": "SQL: دوال النوافذ للترتيب",
         "prompt": "Show me how SQL window functions like ROW_NUMBER, RANK, and DENSE_RANK work, with a realistic sales table example.",
         "prompt_ar": "أرني كيف تعمل دوال النوافذ في SQL مثل ROW_NUMBER و RANK و DENSE_RANK، مع مثال جدول مبيعات حقيقي.",
         "params": {"pl_language": "SQL", "learner_level": "intermediate"}},
        {"title": "Algorithm: binary search", "title_ar": "خوارزمية: البحث الثنائي",
         "prompt": "Walk me through binary search with both iterative and recursive implementations and a complexity analysis.",
         "prompt_ar": "اشرح خوارزمية البحث الثنائي مع تنفيذين تكراري وتعاودي مع تحليل التعقيد.",
         "params": {"learner_level": "intermediate", "lesson_focus": "algorithm walkthrough"}},
        {"title": "Debug: why is my function slow?", "title_ar": "تصحيح: لماذا دالتي بطيئة؟",
         "prompt": "I have a function that loops over a million items and is slow. Teach me how to profile it and the top 3 optimization techniques.",
         "prompt_ar": "لدي دالة تمر على مليون عنصر وهي بطيئة. علّمني كيف أحلل أداءها وأهم 3 تقنيات تحسين.",
         "params": {"lesson_focus": "debugging session"}}
    ],
    "text_generator": [
        {"title": "Course welcome message", "title_ar": "رسالة ترحيب بالمقرر",
         "prompt": "Write a warm welcome message for students starting a new online course on Project Management.",
         "prompt_ar": "اكتب رسالة ترحيب دافئة للطلاب الذين يبدأون مقرراً جديداً في إدارة المشاريع.",
         "params": {"tone": "professional", "length": "short"}},
        {"title": "LinkedIn post about a new certificate", "title_ar": "منشور لينكدإن عن شهادة جديدة",
         "prompt": "Write a LinkedIn post celebrating completing a professional certificate in Data Analytics.",
         "prompt_ar": "اكتب منشور لينكدإن للاحتفال بإكمال شهادة مهنية في تحليل البيانات.",
         "params": {"tone": "professional", "length": "short"}},
        {"title": "Blog intro about AI in education", "title_ar": "مقدمة مدونة عن الذكاء الاصطناعي في التعليم",
         "prompt": "Write an engaging blog intro (3 paragraphs) about how AI is transforming online learning.",
         "prompt_ar": "اكتب مقدمة مدونة جذابة (3 فقرات) حول كيف يحوّل الذكاء الاصطناعي التعلم عبر الإنترنت.",
         "params": {"tone": "creative", "length": "medium"}},
        {"title": "Job description: Instructional Designer", "title_ar": "وصف وظيفة: مصمم تعليمي",
         "prompt": "Write a professional job description for an Instructional Designer role at an EdTech company.",
         "prompt_ar": "اكتب وصفاً وظيفياً مهنياً لوظيفة مصمم تعليمي في شركة تقنيات تعليمية.",
         "params": {"tone": "formal", "length": "medium"}}
    ],
    "summarizer": [
        {"title": "Summarize a research paper", "title_ar": "تلخيص ورقة بحثية",
         "prompt": "Summarize this research paper into the abstract, key findings, methodology, and limitations.",
         "prompt_ar": "لخّص هذه الورقة البحثية إلى الملخص والنتائج الرئيسية والمنهجية والقيود.",
         "params": {"summary_type": "executive summary", "length": "comprehensive"}},
        {"title": "TL;DR of a long article", "title_ar": "خلاصة سريعة لمقال طويل",
         "prompt": "Give me a 5-bullet TL;DR of the following article.",
         "prompt_ar": "أعطني خلاصة سريعة من 5 نقاط للمقال التالي.",
         "params": {"summary_type": "bullet points", "length": "brief"}},
        {"title": "Meeting notes → action items", "title_ar": "ملاحظات اجتماع إلى مهام",
         "prompt": "Extract only the action items, owners, and deadlines from these meeting notes.",
         "prompt_ar": "استخرج فقط المهام والمسؤولين والمواعيد النهائية من ملاحظات الاجتماع التالية.",
         "params": {"summary_type": "bullet points", "length": "brief"}}
    ],
    "translator": [
        {"title": "EN → Modern Standard Arabic", "title_ar": "إنجليزي ← عربي فصيح",
         "prompt": "Translate the following text into formal Modern Standard Arabic, preserving tone.",
         "prompt_ar": "ترجم النص التالي إلى العربية الفصحى الحديثة مع الحفاظ على النبرة.",
         "params": {"source_lang": "English", "target_lang": "Arabic"}},
        {"title": "AR → Professional English", "title_ar": "عربي ← إنجليزي مهني",
         "prompt": "Translate the following Arabic text into clear, professional business English.",
         "prompt_ar": "ترجم النص العربي التالي إلى إنجليزية مهنية واضحة.",
         "params": {"source_lang": "Arabic", "target_lang": "English"}},
        {"title": "Localize a UI string", "title_ar": "ترجمة نص واجهة",
         "prompt": "Localize this short UI label, keeping it under 25 characters and preserving the call-to-action feel.",
         "prompt_ar": "ترجم نص واجهة المستخدم القصير هذا مع إبقائه أقل من 25 حرفاً والحفاظ على إحساس الدعوة لاتخاذ إجراء."}
    ],
    "grammar_checker": [
        {"title": "Polish a formal email", "title_ar": "تحسين بريد رسمي",
         "prompt": "Check and polish this email for grammar, tone, and clarity. Keep it formal.",
         "prompt_ar": "افحص وحسّن هذا البريد من حيث القواعد والنبرة والوضوح. أبقه رسمياً.",
         "params": {"style": "formal"}},
        {"title": "Academic essay proofread", "title_ar": "تدقيق مقال أكاديمي",
         "prompt": "Proofread this academic paragraph and suggest stronger word choices.",
         "prompt_ar": "دقق هذه الفقرة الأكاديمية واقترح اختيارات كلمات أقوى.",
         "params": {"style": "academic"}}
    ],
    "paraphraser": [
        {"title": "Make it simpler for students", "title_ar": "اجعله أبسط للطلاب",
         "prompt": "Rewrite this paragraph in simpler language suitable for high-school students.",
         "prompt_ar": "أعد كتابة هذه الفقرة بلغة أبسط مناسبة لطلاب المرحلة الثانوية.",
         "params": {"tone": "simplified", "style": "fluent"}},
        {"title": "More professional tone", "title_ar": "نبرة أكثر مهنية",
         "prompt": "Rewrite this in a more professional, business-appropriate tone.",
         "prompt_ar": "أعد كتابة هذا بنبرة أكثر مهنية ومناسبة للأعمال.",
         "params": {"tone": "professional", "style": "concise"}}
    ],
    "lesson_planner": [
        {"title": "60-min intro to fractions (Grade 4)", "title_ar": "60 دقيقة: مقدمة الكسور (الصف الرابع)",
         "prompt": "Plan a 60-minute lesson introducing fractions to 4th-grade students with hands-on activities.",
         "prompt_ar": "خطط درساً مدته 60 دقيقة لتقديم الكسور لطلاب الصف الرابع مع أنشطة عملية.",
         "params": {"subject": "Mathematics", "level": "elementary", "duration": "60 minutes"}},
        {"title": "90-min: Photosynthesis lab", "title_ar": "90 دقيقة: مختبر التمثيل الضوئي",
         "prompt": "Design a 90-minute lab-based lesson on photosynthesis for high-school biology.",
         "prompt_ar": "صمم درساً مخبرياً مدته 90 دقيقة عن التمثيل الضوئي لطلاب أحياء الثانوية.",
         "params": {"subject": "Biology", "level": "high school", "duration": "90 minutes"}},
        {"title": "Workshop: AI ethics for staff", "title_ar": "ورشة: أخلاقيات الذكاء الاصطناعي للموظفين",
         "prompt": "Build a 2-hour staff workshop on responsible AI use in the workplace.",
         "prompt_ar": "ابنِ ورشة عمل مدتها ساعتان للموظفين حول الاستخدام المسؤول للذكاء الاصطناعي في مكان العمل.",
         "params": {"subject": "Professional Development", "level": "professional", "duration": "2 hours"}}
    ],
    "question_generator": [
        {"title": "10 MCQs on World War II", "title_ar": "10 أسئلة اختيار متعدد عن الحرب العالمية الثانية",
         "prompt": "Generate 10 multiple-choice questions on World War II covering causes, key battles, and outcomes.",
         "prompt_ar": "أنشئ 10 أسئلة اختيار من متعدد عن الحرب العالمية الثانية تغطي الأسباب والمعارك الرئيسية والنتائج.",
         "params": {"subject": "History", "difficulty": "mixed", "num_questions": "10"}},
        {"title": "5 short-answer Qs on cell biology", "title_ar": "5 أسئلة قصيرة عن علم الخلية",
         "prompt": "Generate 5 short-answer questions on cell organelles and their functions.",
         "prompt_ar": "أنشئ 5 أسئلة إجابة قصيرة عن عضيات الخلية ووظائفها.",
         "params": {"subject": "Biology", "question_types": "short answer", "num_questions": "5"}},
        {"title": "Coding interview screen", "title_ar": "اختبار مقابلة برمجة",
         "prompt": "Generate 5 progressively harder Python coding questions suitable for a junior developer screening interview.",
         "prompt_ar": "أنشئ 5 أسئلة برمجة بايثون بصعوبة تصاعدية مناسبة لمقابلة فرز مطور مبتدئ.",
         "params": {"subject": "Computer Science", "difficulty": "mixed", "num_questions": "5"}}
    ],
    "rubric_creator": [
        {"title": "Essay rubric (4 levels)", "title_ar": "معايير تقييم مقال (4 مستويات)",
         "prompt": "Create a 4-level rubric to grade a 1000-word argumentative essay.",
         "prompt_ar": "أنشئ معايير تقييم من 4 مستويات لتقييم مقال جدلي بـ1000 كلمة.",
         "params": {"assignment": "Argumentative essay", "criteria": "thesis, evidence, structure, mechanics"}},
        {"title": "Group project rubric", "title_ar": "معايير تقييم مشروع جماعي",
         "prompt": "Build a rubric for a group project that includes peer-collaboration scoring.",
         "prompt_ar": "ابنِ معايير تقييم لمشروع جماعي تتضمن تقييم التعاون بين الأقران.",
         "params": {"assignment": "Group project", "criteria": "research, collaboration, deliverable, presentation"}}
    ],
    "feedback_generator": [
        {"title": "Encouraging feedback for weak essay", "title_ar": "ملاحظات مشجعة لمقال ضعيف",
         "prompt": "Give encouraging but honest feedback on a student essay that has weak structure but a creative thesis.",
         "prompt_ar": "قدم ملاحظات مشجعة لكن صادقة عن مقال طالب يحتوي على بنية ضعيفة لكن فكرة مبدعة.",
         "params": {"assignment_type": "essay", "tone": "encouraging"}},
        {"title": "Detailed feedback on a project", "title_ar": "ملاحظات مفصلة على مشروع",
         "prompt": "Provide detailed, balanced feedback on a student project covering content, design, and presentation.",
         "prompt_ar": "قدم ملاحظات مفصلة ومتوازنة على مشروع طالب تغطي المحتوى والتصميم والعرض.",
         "params": {"assignment_type": "project", "tone": "balanced"}}
    ],
    "study_assistant": [
        {"title": "Help me understand calculus limits", "title_ar": "ساعدني في فهم نهايات التفاضل",
         "prompt": "I'm stuck on the concept of limits in calculus. Explain it with examples and a simple practice problem.",
         "prompt_ar": "أنا عالق في مفهوم النهايات في التفاضل. اشرحه مع أمثلة ومسألة تدريب بسيطة.",
         "params": {"subject": "Mathematics", "level": "intermediate"}},
        {"title": "Memorization strategies for vocabulary", "title_ar": "استراتيجيات حفظ المفردات",
         "prompt": "What are the best techniques to memorize 50 new English vocabulary words this week?",
         "prompt_ar": "ما هي أفضل التقنيات لحفظ 50 كلمة إنجليزية جديدة هذا الأسبوع؟",
         "params": {"subject": "Languages", "level": "beginner"}},
        {"title": "Exam prep plan (1 week)", "title_ar": "خطة تحضير امتحان (أسبوع)",
         "prompt": "Build me a 7-day study plan to prepare for a final exam in Microeconomics.",
         "prompt_ar": "ابنِ لي خطة دراسية مدتها 7 أيام للتحضير لامتحان نهائي في الاقتصاد الجزئي.",
         "params": {"subject": "Economics", "level": "intermediate"}}
    ],
    "flashcard_generator": [
        {"title": "Anatomy: muscles of the arm", "title_ar": "تشريح: عضلات الذراع",
         "prompt": "Create flashcards covering the major muscles of the human arm and their functions.",
         "prompt_ar": "أنشئ بطاقات تعليمية تغطي العضلات الرئيسية في ذراع الإنسان ووظائفها.",
         "params": {"topic": "Arm anatomy", "num_cards": "15"}},
        {"title": "Spanish travel phrases", "title_ar": "عبارات سفر إسبانية",
         "prompt": "Make flashcards of 20 essential Spanish travel phrases for a tourist.",
         "prompt_ar": "اصنع بطاقات لـ20 عبارة إسبانية أساسية للسفر للسائح.",
         "params": {"topic": "Spanish travel", "num_cards": "20"}}
    ],
    "concept_explainer": [
        {"title": "Quantum entanglement (beginner)", "title_ar": "التشابك الكمي (مبتدئ)",
         "prompt": "Explain quantum entanglement to me as if I'm a complete beginner.",
         "prompt_ar": "اشرح لي التشابك الكمي وكأنني مبتدئ تماماً.",
         "params": {"subject": "Physics", "level": "beginner", "learning_style": "analogies"}},
        {"title": "Compound interest with examples", "title_ar": "الفائدة المركبة مع أمثلة",
         "prompt": "Explain compound interest step-by-step with a real money example.",
         "prompt_ar": "اشرح الفائدة المركبة خطوة بخطوة مع مثال مالي حقيقي.",
         "params": {"subject": "Finance", "level": "intermediate", "learning_style": "step-by-step"}}
    ],
    "essay_helper": [
        {"title": "Build a thesis statement", "title_ar": "بناء بيان أطروحة",
         "prompt": "Help me develop a strong thesis statement for an argumentative essay on social media regulation.",
         "prompt_ar": "ساعدني في تطوير بيان أطروحة قوي لمقال جدلي عن تنظيم وسائل التواصل الاجتماعي.",
         "params": {"essay_type": "argumentative", "help_type": "thesis development"}},
        {"title": "Outline a compare-contrast essay", "title_ar": "مخطط مقال مقارنة وتباين",
         "prompt": "Outline a compare-contrast essay on traditional vs online learning.",
         "prompt_ar": "ضع مخطط مقال مقارنة وتباين بين التعلم التقليدي والتعلم عبر الإنترنت.",
         "params": {"essay_type": "compare-contrast", "help_type": "outline creation"}}
    ],
    "report_generator": [
        {"title": "Monthly enrollment report", "title_ar": "تقرير التسجيل الشهري",
         "prompt": "Generate a monthly enrollment report with key metrics, trends, and recommendations.",
         "prompt_ar": "أنشئ تقرير تسجيل شهري مع المقاييس الرئيسية والاتجاهات والتوصيات.",
         "params": {"report_type": "executive", "period": "monthly", "metrics": "enrollment, completion, satisfaction"}},
        {"title": "Quarterly course performance", "title_ar": "أداء المقررات الفصلي",
         "prompt": "Build a quarterly performance report on top-performing and underperforming courses.",
         "prompt_ar": "ابنِ تقرير أداء فصلي عن المقررات الأعلى والأدنى أداءً.",
         "params": {"report_type": "detailed", "period": "quarterly", "metrics": "completion rate, average score, dropout"}}
    ],
    "announcement_creator": [
        {"title": "New semester kickoff", "title_ar": "انطلاق فصل دراسي جديد",
         "prompt": "Announce the start of a new semester with key dates, expectations, and a motivating tone.",
         "prompt_ar": "أعلن عن بدء فصل دراسي جديد مع التواريخ المهمة والتوقعات ونبرة محفزة.",
         "params": {"purpose": "event", "audience": "students", "tone": "celebratory"}},
        {"title": "System maintenance notice", "title_ar": "إشعار صيانة النظام",
         "prompt": "Write an urgent maintenance notice about a 4-hour platform downtime tonight.",
         "prompt_ar": "اكتب إشعار صيانة عاجل عن توقف المنصة لمدة 4 ساعات الليلة.",
         "params": {"purpose": "urgent notice", "audience": "all users", "tone": "formal"}}
    ],
    "email_composer": [
        {"title": "Reminder: assignment due tomorrow", "title_ar": "تذكير: واجب مستحق غداً",
         "prompt": "Send students a friendly reminder that their assignment is due tomorrow at midnight.",
         "prompt_ar": "أرسل للطلاب تذكيراً ودياً بأن واجبهم مستحق غداً عند منتصف الليل.",
         "params": {"email_type": "reminder", "recipient": "students", "tone": "friendly"}},
        {"title": "Parent: progress update", "title_ar": "ولي الأمر: تحديث التقدم",
         "prompt": "Compose a professional email to a parent updating them on their child's recent progress.",
         "prompt_ar": "اكتب بريداً مهنياً لولي أمر يحدّثه عن تقدم ابنه/ابنته الأخير.",
         "params": {"email_type": "follow-up", "recipient": "parents", "tone": "professional"}}
    ],
    "policy_writer": [
        {"title": "Academic integrity policy", "title_ar": "سياسة النزاهة الأكاديمية",
         "prompt": "Draft an academic integrity policy covering plagiarism, AI use, and consequences.",
         "prompt_ar": "اكتب مسودة سياسة النزاهة الأكاديمية تغطي الانتحال واستخدام الذكاء الاصطناعي والعواقب.",
         "params": {"policy_type": "academic integrity", "scope": "institution-wide"}},
        {"title": "Attendance policy", "title_ar": "سياسة الحضور",
         "prompt": "Write a course-level attendance policy with grace periods and excused-absence rules.",
         "prompt_ar": "اكتب سياسة حضور على مستوى المقرر مع فترات سماح وقواعد الغياب المعذور.",
         "params": {"policy_type": "attendance", "scope": "course-level"}}
    ],
    "data_analyzer": [
        {"title": "Spot trends in completion rates", "title_ar": "اكتشاف اتجاهات معدلات الإكمال",
         "prompt": "Analyze the following monthly completion rate data and identify trends and outliers.",
         "prompt_ar": "حلل بيانات معدل الإكمال الشهرية التالية وحدد الاتجاهات والقيم الشاذة.",
         "params": {"analysis_type": "trend analysis"}},
        {"title": "Compare two cohorts", "title_ar": "مقارنة بين مجموعتين",
         "prompt": "Compare the performance of Cohort A and Cohort B and recommend interventions.",
         "prompt_ar": "قارن أداء المجموعة A والمجموعة B واقترح تدخلات.",
         "params": {"analysis_type": "comparison"}}
    ],
    "compliance_checker": [
        {"title": "GDPR check on a privacy notice", "title_ar": "فحص GDPR لإشعار الخصوصية",
         "prompt": "Check this privacy notice against GDPR requirements and flag any gaps.",
         "prompt_ar": "افحص إشعار الخصوصية هذا مقابل متطلبات GDPR وأشر إلى أي ثغرات.",
         "params": {"standard": "GDPR"}},
        {"title": "WCAG accessibility audit", "title_ar": "مراجعة وصول WCAG",
         "prompt": "Audit this content for WCAG 2.1 AA accessibility compliance.",
         "prompt_ar": "راجع هذا المحتوى للتوافق مع معايير الوصول WCAG 2.1 AA.",
         "params": {"standard": "accessibility (WCAG)"}}
    ]
}


def get_prompt_library_for(tool_id: str) -> List[Dict[str, Any]]:
    """Return ready-made starter prompts for a given tool, or [] if none."""
    return PROMPT_LIBRARY.get(tool_id, [])


ai_tools_service = AIToolsService()
