/**
 * AI Tools Suite - JavaScript functionality
 * Provides comprehensive AI-powered tools for all user roles
 */

(function() {
    'use strict';

    const OPTION_TRANSLATIONS = {
        'professional': 'مهني',
        'casual': 'عادي',
        'academic': 'أكاديمي',
        'creative': 'إبداعي',
        'formal': 'رسمي',
        'short': 'قصير',
        'medium': 'متوسط',
        'long': 'طويل',
        'detailed': 'مفصل',
        'key points': 'النقاط الرئيسية',
        'paragraph': 'فقرة',
        'bullet points': 'نقاط متعددة',
        'executive summary': 'ملخص تنفيذي',
        'brief': 'موجز',
        'comprehensive': 'شامل',
        'auto-detect': 'كشف تلقائي',
        'English': 'الإنجليزية',
        'Arabic': 'العربية',
        'French': 'الفرنسية',
        'Spanish': 'الإسبانية',
        'German': 'الألمانية',
        'Chinese': 'الصينية',
        'informal': 'غير رسمي',
        'business': 'أعمال',
        'standard': 'قياسي',
        'fluent': 'سلس',
        'concise': 'موجز',
        'simplified': 'مبسط',
        'elementary': 'ابتدائي',
        'middle school': 'متوسط',
        'high school': 'ثانوي',
        'university': 'جامعي',
        '30 minutes': '30 دقيقة',
        '45 minutes': '45 دقيقة',
        '60 minutes': '60 دقيقة',
        '90 minutes': '90 دقيقة',
        '2 hours': 'ساعتان',
        'easy': 'سهل',
        'hard': 'صعب',
        'mixed': 'مختلط',
        'multiple choice': 'اختيار متعدد',
        'true/false': 'صح/خطأ',
        'short answer': 'إجابة قصيرة',
        'essay': 'مقال',
        'encouraging': 'تشجيعي',
        'constructive': 'بنّاء',
        'balanced': 'متوازن',
        'beginner': 'مبتدئ',
        'intermediate': 'متوسط',
        'advanced': 'متقدم',
        'visual': 'بصري',
        'examples': 'أمثلة',
        'step-by-step': 'خطوة بخطوة',
        'analogies': 'تشبيهات',
        'argumentative': 'جدلي',
        'expository': 'توضيحي',
        'narrative': 'سردي',
        'descriptive': 'وصفي',
        'compare-contrast': 'مقارنة ومقابلة',
        'thesis development': 'تطوير الأطروحة',
        'outline creation': 'إنشاء مخطط',
        'introduction': 'مقدمة',
        'conclusion': 'خاتمة',
        'full structure': 'هيكل كامل',
        'summary': 'ملخص',
        'executive': 'تنفيذي',
        'progress': 'تقدم',
        'analytics': 'تحليلات',
        'daily': 'يومي',
        'weekly': 'أسبوعي',
        'monthly': 'شهري',
        'quarterly': 'ربع سنوي',
        'yearly': 'سنوي',
        'event': 'حدث',
        'policy update': 'تحديث سياسة',
        'reminder': 'تذكير',
        'celebration': 'احتفال',
        'urgent notice': 'إشعار عاجل',
        'all users': 'جميع المستخدمين',
        'students': 'الطلاب',
        'teachers': 'المعلمين',
        'staff': 'الموظفين',
        'specific group': 'مجموعة محددة',
        'friendly': 'ودي',
        'urgent': 'عاجل',
        'celebratory': 'احتفالي',
        'informative': 'معلوماتي',
        'group work': 'عمل جماعي',
        'individual': 'فردي',
        'game-based': 'قائم على الألعاب',
        'discussion': 'نقاش',
        'hands-on': 'عملي',
        'research': 'بحث',
        '5-10 minutes': '5-10 دقائق',
        '15-20 minutes': '15-20 دقيقة',
        '45+ minutes': '45+ دقيقة',
        'general audience': 'جمهور عام',
        'ESL learner': 'متعلم اللغة الإنجليزية',
        'struggling learners': 'المتعلمين المتعثرين',
        'on-level learners': 'المتعلمين على المستوى',
        'advanced learners': 'المتعلمين المتقدمين',
        'ESL learners': 'متعلمي اللغة الإنجليزية',
        'visual learners': 'المتعلمين البصريين',
        'content modification': 'تعديل المحتوى',
        'activity adaptation': 'تكييف النشاط',
        'assessment adjustment': 'تعديل التقييم',
        'scaffolding': 'الدعم التدريجي',
        'outline': 'مخطط',
        'mind map': 'خريطة ذهنية',
        'Cornell notes': 'ملاحظات كورنيل',
        '1 hour/week': 'ساعة/أسبوع',
        '3-5 hours/week': '3-5 ساعات/أسبوع',
        '10+ hours/week': '10+ ساعات/أسبوع',
        'full-time': 'دوام كامل',
        'procrastination': 'التسويف',
        'lack of focus': 'قلة التركيز',
        'low confidence': 'ضعف الثقة',
        'burnout': 'الإرهاق',
        'exam anxiety': 'قلق الامتحان',
        'general motivation': 'تحفيز عام',
        'academic integrity': 'النزاهة الأكاديمية',
        'attendance': 'الحضور',
        'grading': 'التقييم',
        'behavior': 'السلوك',
        'safety': 'السلامة',
        'technology use': 'استخدام التكنولوجيا',
        'privacy': 'الخصوصية',
        'course-level': 'مستوى المقرر',
        'department': 'القسم',
        'institution-wide': 'على مستوى المؤسسة',
        'announcement': 'إعلان',
        'follow-up': 'متابعة',
        'request': 'طلب',
        'thank you': 'شكر',
        'notification': 'إشعار',
        'parents': 'أولياء الأمور',
        'colleagues': 'الزملاء',
        'administrators': 'المسؤولين',
        'general': 'عام',
        'faculty': 'هيئة التدريس',
        'committee': 'اللجنة',
        'planning': 'التخطيط',
        'review': 'المراجعة',
        'action items only': 'عناصر العمل فقط',
        'introductory': 'تمهيدي',
        'graduate': 'دراسات عليا',
        '1 credit': '1 ساعة معتمدة',
        '2 credits': '2 ساعة معتمدة',
        '3 credits': '3 ساعات معتمدة',
        '4 credits': '4 ساعات معتمدة',
        'trend analysis': 'تحليل الاتجاهات',
        'comparison': 'المقارنة',
        'summary statistics': 'إحصاءات موجزة',
        'insights extraction': 'استخراج الرؤى',
        'recommendations': 'التوصيات',
        'GDPR': 'اللائحة العامة لحماية البيانات',
        'FERPA': 'قانون حقوق الأسرة التعليمية',
        'accessibility (WCAG)': 'إمكانية الوصول',
        'copyright': 'حقوق النشر',
        'academic standards': 'المعايير الأكاديمية',
        'institutional policy': 'سياسة المؤسسة',
        'minimal': 'بسيط',
        'corporate': 'مؤسسي',
        'project': 'مشروع',
        'presentation': 'عرض تقديمي',
        'exam': 'امتحان',
        'homework': 'واجب منزلي',
        'beginner': 'مبتدئ',
        'intermediate': 'متوسط',
        'advanced': 'متقدم',
        'Python': 'بايثون',
        'JavaScript': 'جافاسكريبت',
        'TypeScript': 'تايب سكريبت',
        'Java': 'جافا',
        'concept + worked example + practice': 'مفهوم + مثال محلول + تمرين',
        'syntax basics': 'أساسيات الصياغة',
        'algorithm walkthrough': 'شرح خوارزمية',
        'debugging session': 'جلسة تصحيح أخطاء',
        'project tutorial': 'درس مشروع كامل',
        'interview prep': 'تحضير مقابلات'
    };

    const TOOL_CONFIGS = {
        programming_tutor: {
            title: 'Programming Tutor',
            title_ar: 'مدرّس البرمجة',
            icon: 'fa-code',
            fields: [
                { id: 'pl_language', label: 'Programming Language', label_ar: 'لغة البرمجة', type: 'select', options: ['Python', 'JavaScript', 'TypeScript', 'Java', 'C#', 'C++', 'Go', 'Rust', 'PHP', 'Ruby', 'SQL', 'HTML/CSS', 'Bash'] },
                { id: 'learner_level', label: 'Your Level', label_ar: 'مستواك', type: 'select', options: ['beginner', 'intermediate', 'advanced'] },
                { id: 'lesson_focus', label: 'Lesson Focus', label_ar: 'محور الدرس', type: 'select', options: ['concept + worked example + practice', 'syntax basics', 'algorithm walkthrough', 'debugging session', 'project tutorial', 'interview prep'] }
            ],
            inputPlaceholder: 'Enter the topic you want to learn (e.g., "list comprehensions", "async/await", "binary search")...',
            inputPlaceholder_ar: 'أدخل الموضوع الذي تريد تعلمه (مثال: "قوائم الفهم"، "async/await"، "البحث الثنائي")...'
        },
        text_generator: {
            title: 'Text Generator',
            title_ar: 'مولد النصوص',
            icon: 'fa-pen-fancy',
            fields: [
                { id: 'tone', label: 'Tone', label_ar: 'النبرة', type: 'select', options: ['professional', 'casual', 'academic', 'creative', 'formal'] },
                { id: 'length', label: 'Length', label_ar: 'الطول', type: 'select', options: ['short', 'medium', 'long', 'detailed'] }
            ],
            inputPlaceholder: 'Enter the topic or subject you want to write about...',
            inputPlaceholder_ar: 'أدخل الموضوع الذي تريد الكتابة عنه...'
        },
        summarizer: {
            title: 'Text Summarizer',
            title_ar: 'ملخص النصوص',
            icon: 'fa-compress-alt',
            fields: [
                { id: 'summary_type', label: 'Summary Type', label_ar: 'نوع الملخص', type: 'select', options: ['key points', 'paragraph', 'bullet points', 'executive summary'] },
                { id: 'length', label: 'Length', label_ar: 'الطول', type: 'select', options: ['brief', 'medium', 'comprehensive'] }
            ],
            inputPlaceholder: 'Paste the text you want to summarize...',
            inputPlaceholder_ar: 'الصق النص الذي تريد تلخيصه...'
        },
        translator: {
            title: 'Smart Translator',
            title_ar: 'المترجم الذكي',
            icon: 'fa-language',
            fields: [
                { id: 'source_lang', label: 'Source Language', label_ar: 'اللغة المصدر', type: 'select', options: ['auto-detect', 'English', 'Arabic', 'French', 'Spanish', 'German', 'Chinese'] },
                { id: 'target_lang', label: 'Target Language', label_ar: 'اللغة الهدف', type: 'select', options: ['English', 'Arabic', 'French', 'Spanish', 'German', 'Chinese'] }
            ],
            inputPlaceholder: 'Enter text to translate...',
            inputPlaceholder_ar: 'أدخل النص للترجمة...'
        },
        grammar_checker: {
            title: 'Grammar & Style Checker',
            title_ar: 'مدقق القواعد والأسلوب',
            icon: 'fa-spell-check',
            fields: [
                { id: 'style', label: 'Writing Style', label_ar: 'أسلوب الكتابة', type: 'select', options: ['formal', 'informal', 'academic', 'business', 'creative'] }
            ],
            inputPlaceholder: 'Paste the text you want to check...',
            inputPlaceholder_ar: 'الصق النص الذي تريد التحقق منه...'
        },
        paraphraser: {
            title: 'Paraphraser',
            title_ar: 'معيد الصياغة',
            icon: 'fa-sync-alt',
            fields: [
                { id: 'tone', label: 'Tone', label_ar: 'النبرة', type: 'select', options: ['professional', 'casual', 'academic', 'simplified', 'formal'] },
                { id: 'style', label: 'Style', label_ar: 'الأسلوب', type: 'select', options: ['standard', 'fluent', 'creative', 'concise'] }
            ],
            inputPlaceholder: 'Enter text to paraphrase...',
            inputPlaceholder_ar: 'أدخل النص لإعادة الصياغة...'
        },
        lesson_planner: {
            title: 'Lesson Plan Generator',
            title_ar: 'مولد خطط الدروس',
            icon: 'fa-chalkboard-teacher',
            fields: [
                { id: 'subject', label: 'Subject', label_ar: 'المادة', type: 'text', placeholder: 'e.g., Mathematics, Science' },
                { id: 'level', label: 'Grade/Level', label_ar: 'المستوى', type: 'select', options: ['elementary', 'middle school', 'high school', 'university', 'professional'] },
                { id: 'duration', label: 'Duration', label_ar: 'المدة', type: 'select', options: ['30 minutes', '45 minutes', '60 minutes', '90 minutes', '2 hours'] }
            ],
            inputPlaceholder: 'Enter the lesson topic...',
            inputPlaceholder_ar: 'أدخل موضوع الدرس...'
        },
        question_generator: {
            title: 'Question Bank Generator',
            title_ar: 'مولد بنك الأسئلة',
            icon: 'fa-question-circle',
            fields: [
                { id: 'subject', label: 'Subject', label_ar: 'المادة', type: 'text', placeholder: 'e.g., History, Biology' },
                { id: 'difficulty', label: 'Difficulty', label_ar: 'الصعوبة', type: 'select', options: ['easy', 'medium', 'hard', 'mixed'] },
                { id: 'question_types', label: 'Question Types', label_ar: 'أنواع الأسئلة', type: 'select', options: ['multiple choice', 'true/false', 'short answer', 'essay', 'mixed'] },
                { id: 'num_questions', label: 'Number of Questions', label_ar: 'عدد الأسئلة', type: 'number', value: 5 }
            ],
            inputPlaceholder: 'Enter the topic for questions...',
            inputPlaceholder_ar: 'أدخل الموضوع للأسئلة...'
        },
        rubric_creator: {
            title: 'Rubric Creator',
            title_ar: 'منشئ معايير التقييم',
            icon: 'fa-table',
            fields: [
                { id: 'assignment', label: 'Assignment Type', label_ar: 'نوع الواجب', type: 'text', placeholder: 'e.g., Essay, Project, Presentation' },
                { id: 'level', label: 'Level', label_ar: 'المستوى', type: 'select', options: ['elementary', 'middle school', 'high school', 'university'] },
                { id: 'criteria', label: 'Criteria (comma-separated)', label_ar: 'المعايير', type: 'text', placeholder: 'e.g., Content, Organization, Grammar' }
            ],
            inputPlaceholder: 'Describe the assignment...',
            inputPlaceholder_ar: 'صف الواجب...'
        },
        feedback_generator: {
            title: 'Student Feedback Generator',
            title_ar: 'مولد ملاحظات الطلاب',
            icon: 'fa-comment-dots',
            fields: [
                { id: 'assignment_type', label: 'Assignment Type', label_ar: 'نوع الواجب', type: 'select', options: ['essay', 'project', 'presentation', 'exam', 'homework'] },
                { id: 'areas', label: 'Areas to Address', label_ar: 'المجالات', type: 'text', placeholder: 'e.g., content, structure, clarity' },
                { id: 'tone', label: 'Feedback Tone', label_ar: 'نبرة الملاحظات', type: 'select', options: ['encouraging', 'constructive', 'detailed', 'balanced'] }
            ],
            inputPlaceholder: 'Describe the student work...',
            inputPlaceholder_ar: 'صف عمل الطالب...'
        },
        study_assistant: {
            title: 'Study Assistant',
            title_ar: 'مساعد الدراسة',
            icon: 'fa-graduation-cap',
            fields: [
                { id: 'subject', label: 'Subject Area', label_ar: 'مجال الدراسة', type: 'text', placeholder: 'e.g., Physics, Literature' },
                { id: 'level', label: 'Your Level', label_ar: 'مستواك', type: 'select', options: ['beginner', 'intermediate', 'advanced'] }
            ],
            inputPlaceholder: 'Ask your question or enter the topic you need help with...',
            inputPlaceholder_ar: 'اطرح سؤالك أو أدخل الموضوع الذي تحتاج مساعدة فيه...'
        },
        flashcard_generator: {
            title: 'Flashcard Generator',
            title_ar: 'مولد البطاقات التعليمية',
            icon: 'fa-clone',
            fields: [
                { id: 'topic', label: 'Topic', label_ar: 'الموضوع', type: 'text', placeholder: 'e.g., Vocabulary, Key Concepts' },
                { id: 'num_cards', label: 'Number of Cards', label_ar: 'عدد البطاقات', type: 'number', value: 10 }
            ],
            inputPlaceholder: 'Enter content or notes to create flashcards from...',
            inputPlaceholder_ar: 'أدخل المحتوى أو الملاحظات لإنشاء البطاقات...'
        },
        concept_explainer: {
            title: 'Concept Explainer',
            title_ar: 'شارح المفاهيم',
            icon: 'fa-lightbulb',
            fields: [
                { id: 'subject', label: 'Subject Area', label_ar: 'مجال الدراسة', type: 'text', placeholder: 'e.g., Chemistry, Economics' },
                { id: 'level', label: 'Understanding Level', label_ar: 'مستوى الفهم', type: 'select', options: ['beginner', 'intermediate', 'advanced'] },
                { id: 'learning_style', label: 'Learning Style', label_ar: 'نمط التعلم', type: 'select', options: ['visual', 'examples', 'step-by-step', 'analogies'] }
            ],
            inputPlaceholder: 'Enter the concept you want explained...',
            inputPlaceholder_ar: 'أدخل المفهوم الذي تريد شرحه...'
        },
        essay_helper: {
            title: 'Essay Writing Helper',
            title_ar: 'مساعد كتابة المقالات',
            icon: 'fa-file-alt',
            fields: [
                { id: 'essay_type', label: 'Essay Type', label_ar: 'نوع المقال', type: 'select', options: ['argumentative', 'expository', 'narrative', 'descriptive', 'compare-contrast'] },
                { id: 'help_type', label: 'Help Needed', label_ar: 'نوع المساعدة', type: 'select', options: ['thesis development', 'outline creation', 'introduction', 'conclusion', 'full structure'] }
            ],
            inputPlaceholder: 'Enter your essay topic or current draft...',
            inputPlaceholder_ar: 'أدخل موضوع مقالك أو المسودة الحالية...'
        },
        report_generator: {
            title: 'Report Generator',
            title_ar: 'مولد التقارير',
            icon: 'fa-chart-bar',
            fields: [
                { id: 'report_type', label: 'Report Type', label_ar: 'نوع التقرير', type: 'select', options: ['summary', 'detailed', 'executive', 'progress', 'analytics'] },
                { id: 'period', label: 'Time Period', label_ar: 'الفترة الزمنية', type: 'select', options: ['daily', 'weekly', 'monthly', 'quarterly', 'yearly'] },
                { id: 'metrics', label: 'Key Metrics', label_ar: 'المقاييس الرئيسية', type: 'text', placeholder: 'e.g., enrollment, completion, satisfaction' }
            ],
            inputPlaceholder: 'Enter data or information for the report...',
            inputPlaceholder_ar: 'أدخل البيانات أو المعلومات للتقرير...'
        },
        announcement_creator: {
            title: 'Announcement Creator',
            title_ar: 'منشئ الإعلانات',
            icon: 'fa-bullhorn',
            fields: [
                { id: 'purpose', label: 'Purpose', label_ar: 'الغرض', type: 'select', options: ['event', 'policy update', 'reminder', 'celebration', 'urgent notice'] },
                { id: 'audience', label: 'Audience', label_ar: 'الجمهور', type: 'select', options: ['all users', 'students', 'teachers', 'staff', 'specific group'] },
                { id: 'tone', label: 'Tone', label_ar: 'النبرة', type: 'select', options: ['formal', 'friendly', 'urgent', 'celebratory', 'informative'] }
            ],
            inputPlaceholder: 'Enter the key information for the announcement...',
            inputPlaceholder_ar: 'أدخل المعلومات الرئيسية للإعلان...'
        },
        presentation_creator: {
            title: 'Presentation Creator',
            title_ar: 'منشئ العروض التقديمية',
            icon: 'fa-desktop',
            fields: [
                { id: 'num_slides', label: 'Number of Slides', label_ar: 'عدد الشرائح', type: 'number', value: 10 },
                { id: 'style', label: 'Style', label_ar: 'الأسلوب', type: 'select', options: ['professional', 'academic', 'creative', 'minimal', 'corporate'] }
            ],
            inputPlaceholder: 'Enter the presentation topic...',
            inputPlaceholder_ar: 'أدخل موضوع العرض التقديمي...'
        },
        activity_generator: {
            title: 'Activity Generator',
            title_ar: 'مولد الأنشطة',
            icon: 'fa-puzzle-piece',
            fields: [
                { id: 'activity_type', label: 'Activity Type', label_ar: 'نوع النشاط', type: 'select', options: ['group work', 'individual', 'game-based', 'discussion', 'hands-on', 'research'] },
                { id: 'duration', label: 'Duration', label_ar: 'المدة', type: 'select', options: ['5-10 minutes', '15-20 minutes', '30 minutes', '45+ minutes'] },
                { id: 'level', label: 'Level', label_ar: 'المستوى', type: 'select', options: ['beginner', 'intermediate', 'advanced'] }
            ],
            inputPlaceholder: 'Enter the topic for the learning activity...',
            inputPlaceholder_ar: 'أدخل موضوع النشاط التعليمي...'
        },
        content_simplifier: {
            title: 'Content Simplifier',
            title_ar: 'مبسط المحتوى',
            icon: 'fa-level-down-alt',
            fields: [
                { id: 'target_level', label: 'Target Reading Level', label_ar: 'مستوى القراءة المستهدف', type: 'select', options: ['elementary', 'middle school', 'high school', 'general audience', 'ESL learner'] }
            ],
            inputPlaceholder: 'Paste the complex text you want to simplify...',
            inputPlaceholder_ar: 'الصق النص المعقد الذي تريد تبسيطه...'
        },
        differentiation_tool: {
            title: 'Differentiation Tool',
            title_ar: 'أداة التمايز',
            icon: 'fa-users-cog',
            fields: [
                { id: 'learner_type', label: 'Learner Type', label_ar: 'نوع المتعلم', type: 'select', options: ['struggling learners', 'on-level learners', 'advanced learners', 'ESL learners', 'visual learners'] },
                { id: 'adaptation_type', label: 'Adaptation Type', label_ar: 'نوع التكييف', type: 'select', options: ['content modification', 'activity adaptation', 'assessment adjustment', 'scaffolding'] }
            ],
            inputPlaceholder: 'Enter the content or activity to differentiate...',
            inputPlaceholder_ar: 'أدخل المحتوى أو النشاط للتمايز...'
        },
        practice_quiz: {
            title: 'Practice Quiz Generator',
            title_ar: 'مولد الاختبارات التدريبية',
            icon: 'fa-tasks',
            fields: [
                { id: 'num_questions', label: 'Number of Questions', label_ar: 'عدد الأسئلة', type: 'number', value: 10 },
                { id: 'difficulty', label: 'Difficulty', label_ar: 'الصعوبة', type: 'select', options: ['easy', 'medium', 'hard', 'mixed'] },
                { id: 'format', label: 'Format', label_ar: 'التنسيق', type: 'select', options: ['multiple choice', 'true/false', 'short answer', 'mixed'] }
            ],
            inputPlaceholder: 'Enter the topic for the practice quiz...',
            inputPlaceholder_ar: 'أدخل موضوع الاختبار التدريبي...'
        },
        note_organizer: {
            title: 'Note Organizer',
            title_ar: 'منظم الملاحظات',
            icon: 'fa-sticky-note',
            fields: [
                { id: 'format', label: 'Output Format', label_ar: 'تنسيق الإخراج', type: 'select', options: ['outline', 'mind map', 'bullet points', 'Cornell notes', 'summary'] }
            ],
            inputPlaceholder: 'Paste your notes here to organize...',
            inputPlaceholder_ar: 'الصق ملاحظاتك هنا للتنظيم...'
        },
        learning_path_advisor: {
            title: 'Learning Path Advisor',
            title_ar: 'مستشار مسار التعلم',
            icon: 'fa-route',
            fields: [
                { id: 'current_level', label: 'Current Level', label_ar: 'المستوى الحالي', type: 'select', options: ['beginner', 'intermediate', 'advanced'] },
                { id: 'time_available', label: 'Time Available', label_ar: 'الوقت المتاح', type: 'select', options: ['1 hour/week', '3-5 hours/week', '10+ hours/week', 'full-time'] }
            ],
            inputPlaceholder: 'Enter your learning goals and current knowledge...',
            inputPlaceholder_ar: 'أدخل أهدافك التعليمية ومعرفتك الحالية...'
        },
        motivation_coach: {
            title: 'Motivation Coach',
            title_ar: 'مدرب التحفيز',
            icon: 'fa-star',
            fields: [
                { id: 'challenge', label: 'Challenge Type', label_ar: 'نوع التحدي', type: 'select', options: ['procrastination', 'lack of focus', 'low confidence', 'burnout', 'exam anxiety', 'general motivation'] }
            ],
            inputPlaceholder: 'Describe what you are struggling with...',
            inputPlaceholder_ar: 'صف ما تعاني منه...'
        },
        content_chat: {
            title: 'Chat with Content',
            title_ar: 'الدردشة مع المحتوى',
            icon: 'fa-comments',
            isDocumentBased: true,
            fields: [
                { id: 'file_id', label: 'Select Document', label_ar: 'اختر المستند', type: 'document_select' }
            ],
            inputPlaceholder: 'Ask a question about the selected document...',
            inputPlaceholder_ar: 'اطرح سؤالاً عن المستند المختار...'
        },
        policy_writer: {
            title: 'Policy Writer',
            title_ar: 'كاتب السياسات',
            icon: 'fa-file-contract',
            fields: [
                { id: 'policy_type', label: 'Policy Type', label_ar: 'نوع السياسة', type: 'select', options: ['academic integrity', 'attendance', 'grading', 'behavior', 'safety', 'technology use', 'privacy'] },
                { id: 'scope', label: 'Scope', label_ar: 'النطاق', type: 'select', options: ['course-level', 'department', 'institution-wide'] }
            ],
            inputPlaceholder: 'Enter the key points to include in the policy...',
            inputPlaceholder_ar: 'أدخل النقاط الرئيسية لتضمينها في السياسة...'
        },
        email_composer: {
            title: 'Email Composer',
            title_ar: 'محرر البريد الإلكتروني',
            icon: 'fa-envelope',
            fields: [
                { id: 'email_type', label: 'Email Type', label_ar: 'نوع البريد', type: 'select', options: ['announcement', 'reminder', 'follow-up', 'request', 'thank you', 'notification'] },
                { id: 'recipient', label: 'Recipient', label_ar: 'المستلم', type: 'select', options: ['students', 'parents', 'colleagues', 'administrators', 'general'] },
                { id: 'tone', label: 'Tone', label_ar: 'النبرة', type: 'select', options: ['formal', 'friendly', 'professional', 'urgent'] }
            ],
            inputPlaceholder: 'Enter the main points for the email...',
            inputPlaceholder_ar: 'أدخل النقاط الرئيسية للبريد الإلكتروني...'
        },
        meeting_minutes: {
            title: 'Meeting Minutes Generator',
            title_ar: 'مولد محاضر الاجتماعات',
            icon: 'fa-clipboard-list',
            fields: [
                { id: 'meeting_type', label: 'Meeting Type', label_ar: 'نوع الاجتماع', type: 'select', options: ['department', 'faculty', 'committee', 'planning', 'review', 'general'] },
                { id: 'format', label: 'Format', label_ar: 'التنسيق', type: 'select', options: ['formal', 'informal', 'action items only', 'detailed'] }
            ],
            inputPlaceholder: 'Enter the meeting notes or agenda...',
            inputPlaceholder_ar: 'أدخل ملاحظات الاجتماع أو جدول الأعمال...'
        },
        course_description: {
            title: 'Course Description Writer',
            title_ar: 'كاتب وصف المقرر',
            icon: 'fa-book-open',
            fields: [
                { id: 'course_level', label: 'Course Level', label_ar: 'مستوى المقرر', type: 'select', options: ['introductory', 'intermediate', 'advanced', 'graduate'] },
                { id: 'credits', label: 'Credit Hours', label_ar: 'الساعات المعتمدة', type: 'select', options: ['1 credit', '2 credits', '3 credits', '4 credits'] }
            ],
            inputPlaceholder: 'Enter course title and main topics...',
            inputPlaceholder_ar: 'أدخل عنوان المقرر والموضوعات الرئيسية...'
        },
        data_analyzer: {
            title: 'Data Analyzer',
            title_ar: 'محلل البيانات',
            icon: 'fa-chart-line',
            fields: [
                { id: 'analysis_type', label: 'Analysis Type', label_ar: 'نوع التحليل', type: 'select', options: ['trend analysis', 'comparison', 'summary statistics', 'insights extraction', 'recommendations'] }
            ],
            inputPlaceholder: 'Paste the data or describe what you want to analyze...',
            inputPlaceholder_ar: 'الصق البيانات أو صف ما تريد تحليله...'
        },
        compliance_checker: {
            title: 'Compliance Checker',
            title_ar: 'مدقق الامتثال',
            icon: 'fa-shield-alt',
            fields: [
                { id: 'standard', label: 'Standard/Framework', label_ar: 'المعيار/الإطار', type: 'select', options: ['GDPR', 'FERPA', 'accessibility (WCAG)', 'copyright', 'academic standards', 'institutional policy'] }
            ],
            inputPlaceholder: 'Enter the content or policy to check...',
            inputPlaceholder_ar: 'أدخل المحتوى أو السياسة للتحقق منها...'
        }
    };

    let currentTool = null;
    let lastResult = null;
    const PROMPT_CACHE = {};

    const aiTools = {
        _renderPromptLibrary: function(toolId, isArabic) {
            const extraFieldsContainer = document.getElementById('aiToolExtraFields');
            const wrap = document.createElement('div');
            wrap.id = 'aiToolPromptLibrary';
            wrap.style.cssText = 'margin: 8px 0 14px;';
            wrap.innerHTML = `
                <div style="font-size:12px; font-weight:600; color:#6b7280; margin-bottom:6px; display:flex; align-items:center; gap:6px;">
                    <i class="fas fa-bolt" style="color:#f59e0b;"></i>
                    ${isArabic ? 'موجّهات جاهزة' : 'Ready-made prompts'}
                </div>
                <div id="aiToolPromptChips" style="display:flex; flex-wrap:wrap; gap:6px;">
                    <span style="font-size:12px; color:#9ca3af;">${isArabic ? 'جارٍ التحميل...' : 'Loading...'}</span>
                </div>`;
            extraFieldsContainer.appendChild(wrap);

            const render = (prompts) => {
                const chipsBox = document.getElementById('aiToolPromptChips');
                if (!chipsBox) return;
                chipsBox.innerHTML = '';
                if (!prompts || prompts.length === 0) {
                    chipsBox.innerHTML = `<span style="font-size:12px; color:#9ca3af;">${isArabic ? 'لا توجد موجّهات جاهزة لهذه الأداة.' : 'No ready-made prompts for this tool.'}</span>`;
                    return;
                }
                prompts.forEach((p, idx) => {
                    const chip = document.createElement('button');
                    chip.type = 'button';
                    chip.className = 'skp-prompt-chip';
                    chip.setAttribute('data-testid', `chip-prompt-${idx}`);
                    chip.style.cssText = 'border:1px solid #d1d5db; background:#f9fafb; color:#374151; padding:6px 10px; border-radius:14px; font-size:12px; cursor:pointer; transition:all 0.15s;';
                    chip.onmouseover = () => { chip.style.background = '#eef2ff'; chip.style.borderColor = '#6366f1'; chip.style.color = '#4338ca'; };
                    chip.onmouseout  = () => { chip.style.background = '#f9fafb'; chip.style.borderColor = '#d1d5db'; chip.style.color = '#374151'; };
                    const title = isArabic && p.title_ar ? p.title_ar : p.title;
                    chip.textContent = title;
                    chip.title = isArabic && p.prompt_ar ? p.prompt_ar : p.prompt;
                    chip.onclick = () => {
                        const inputEl = document.getElementById('aiToolInput');
                        inputEl.value = isArabic && p.prompt_ar ? p.prompt_ar : p.prompt;
                        inputEl.focus();
                        if (p.params && typeof p.params === 'object') {
                            Object.keys(p.params).forEach(k => {
                                const fieldEl = document.getElementById(`aiTool_${k}`);
                                if (fieldEl) fieldEl.value = p.params[k];
                            });
                        }
                    };
                    chipsBox.appendChild(chip);
                });
            };

            if (PROMPT_CACHE[toolId]) {
                render(PROMPT_CACHE[toolId]);
                return;
            }
            fetch(`/api/ai-tools/prompts/${encodeURIComponent(toolId)}`)
                .then(r => r.json())
                .then(d => {
                    const prompts = (d && d.success && Array.isArray(d.prompts)) ? d.prompts : [];
                    PROMPT_CACHE[toolId] = prompts;
                    render(prompts);
                })
                .catch(() => render([]));
        },

        openTool: function(toolId) {
            currentTool = toolId;
            const config = TOOL_CONFIGS[toolId];
            if (!config) {
                console.error('Unknown tool:', toolId);
                return;
            }

            const lang = window.i18n?.currentLang || 'en';
            const isArabic = lang === 'ar';

            document.getElementById('aiToolModalTitle').innerHTML = 
                `<i class="fas ${config.icon}"></i> ${isArabic && config.title_ar ? config.title_ar : config.title}`;
            
            const inputEl = document.getElementById('aiToolInput');
            inputEl.value = '';
            inputEl.placeholder = isArabic && config.inputPlaceholder_ar ? config.inputPlaceholder_ar : config.inputPlaceholder;
            
            const extraFieldsContainer = document.getElementById('aiToolExtraFields');
            extraFieldsContainer.innerHTML = '';

            // Render the ready-made prompt library above the input as one-click chips.
            this._renderPromptLibrary(toolId, isArabic);
            
            if (config.fields && config.fields.length > 0) {
                config.fields.forEach(field => {
                    const fieldDiv = document.createElement('div');
                    fieldDiv.className = 'form-group';
                    fieldDiv.style.marginTop = '12px';
                    
                    const label = document.createElement('label');
                    label.innerHTML = `<i class="fas fa-tag"></i> ${isArabic && field.label_ar ? field.label_ar : field.label}`;
                    fieldDiv.appendChild(label);
                    
                    let inputElement;
                    if (field.type === 'document_select') {
                        inputElement = document.createElement('select');
                        inputElement.className = 'form-control';
                        inputElement.innerHTML = `<option value="">${isArabic ? 'جاري التحميل...' : 'Loading documents...'}</option>`;
                        
                        fetch('/api/ai-tools/my-documents')
                            .then(res => res.json())
                            .then(data => {
                                inputElement.innerHTML = '';
                                const defaultOpt = document.createElement('option');
                                defaultOpt.value = '';
                                defaultOpt.textContent = isArabic ? '-- اختر مستنداً --' : '-- Select a document --';
                                inputElement.appendChild(defaultOpt);
                                
                                if (data.documents && data.documents.length > 0) {
                                    data.documents.forEach(doc => {
                                        const option = document.createElement('option');
                                        option.value = doc.file_id;
                                        option.textContent = `${doc.filename} (${doc.class_name})`;
                                        inputElement.appendChild(option);
                                    });
                                } else {
                                    const noDocsOpt = document.createElement('option');
                                    noDocsOpt.value = '';
                                    noDocsOpt.textContent = isArabic ? 'لا توجد مستندات متاحة' : 'No documents available';
                                    inputElement.appendChild(noDocsOpt);
                                }
                            })
                            .catch(err => {
                                console.error('Failed to load documents:', err);
                                inputElement.innerHTML = `<option value="">${isArabic ? 'فشل تحميل المستندات' : 'Failed to load documents'}</option>`;
                            });
                    } else if (field.type === 'select') {
                        inputElement = document.createElement('select');
                        inputElement.className = 'form-control';
                        field.options.forEach(opt => {
                            const option = document.createElement('option');
                            option.value = opt;
                            const displayText = isArabic && OPTION_TRANSLATIONS[opt] 
                                ? OPTION_TRANSLATIONS[opt] 
                                : opt.charAt(0).toUpperCase() + opt.slice(1);
                            option.textContent = displayText;
                            inputElement.appendChild(option);
                        });
                    } else if (field.type === 'number') {
                        inputElement = document.createElement('input');
                        inputElement.type = 'number';
                        inputElement.className = 'form-control';
                        inputElement.value = field.value || 5;
                        inputElement.min = 1;
                        inputElement.max = 50;
                    } else {
                        inputElement = document.createElement('input');
                        inputElement.type = 'text';
                        inputElement.className = 'form-control';
                        inputElement.placeholder = field.placeholder || '';
                    }
                    
                    inputElement.id = `aiTool_${field.id}`;
                    inputElement.setAttribute('data-testid', `input-tool-${field.id}`);
                    fieldDiv.appendChild(inputElement);
                    extraFieldsContainer.appendChild(fieldDiv);
                });
            }
            
            document.getElementById('aiToolModalContent').style.display = 'block';
            document.getElementById('aiToolLoading').style.display = 'none';
            document.getElementById('aiToolResult').style.display = 'none';
            
            document.getElementById('aiToolModal').classList.add('show');
        },

        closeModal: function() {
            document.getElementById('aiToolModal').classList.remove('show');
            currentTool = null;
            this._courseScope = null;
        },

        clearResult: function() {
            document.getElementById('aiToolInput').value = '';
            document.getElementById('aiToolResult').style.display = 'none';
            document.getElementById('aiToolResultContent').textContent = '';
            lastResult = null;
        },

        executeTool: async function() {
            if (!currentTool) return;

            const input = document.getElementById('aiToolInput').value.trim();
            if (!input) {
                alert(window.i18n?.currentLang === 'ar' ? 'الرجاء إدخال نص' : 'Please enter some text');
                return;
            }

            // Empty means "use the server's configured default" — better than
            // pinning a model name here that will be retired.
            const model = document.getElementById('aiToolsModelSelect')?.value || '';
            const language = document.getElementById('aiToolsLanguageSelect')?.value || 'English';

            const config = TOOL_CONFIGS[currentTool];
            const params = { input, language };
            
            if (config.fields) {
                config.fields.forEach(field => {
                    const el = document.getElementById(`aiTool_${field.id}`);
                    if (el) {
                        params[field.id] = el.value;
                    }
                });
            }

            document.getElementById('aiToolModalContent').style.display = 'none';
            document.getElementById('aiToolLoading').style.display = 'block';
            document.getElementById('aiToolResult').style.display = 'none';

            try {
                let endpoint = '/api/ai-tools/execute';
                let body = {
                    tool_id: currentTool,
                    params: params,
                    model: model
                };
                
                if (config.isDocumentBased) {
                    endpoint = '/api/ai-tools/content-chat';
                    body = {
                        file_id: params.file_id,
                        question: input,
                        language: language,
                        model: model
                    };
                } else if (this._courseScope) {
                    // Route through the per-course endpoint so the prompt is
                    // auto-prefixed with course title, structure, and roster summary.
                    endpoint = `/api/teacher/courses/${this._courseScope}/ai-tools/execute`;
                }
                
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });

                const data = await response.json();

                document.getElementById('aiToolLoading').style.display = 'none';
                document.getElementById('aiToolModalContent').style.display = 'block';

                if (data.success && data.result) {
                    lastResult = data.result;
                    document.getElementById('aiToolResultContent').textContent = data.result;
                    document.getElementById('aiToolResult').style.display = 'block';
                } else {
                    alert(data.error || 'Failed to generate result');
                }
            } catch (error) {
                console.error('AI Tool error:', error);
                document.getElementById('aiToolLoading').style.display = 'none';
                document.getElementById('aiToolModalContent').style.display = 'block';
                alert('Error connecting to AI service. Please try again.');
            }
        },

        copyResult: function() {
            if (!lastResult) return;
            
            navigator.clipboard.writeText(lastResult).then(() => {
                const btn = document.querySelector('[data-testid="button-copy-result"]');
                const originalHTML = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
                setTimeout(() => { btn.innerHTML = originalHTML; }, 2000);
            }).catch(err => {
                console.error('Failed to copy:', err);
            });
        },

        downloadResult: function() {
            if (!lastResult) return;
            
            const config = TOOL_CONFIGS[currentTool] || { title: 'AI Tool Result' };
            const blob = new Blob([lastResult], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${config.title.replace(/\s+/g, '_')}_${new Date().toISOString().slice(0,10)}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    };

    window.aiTools = aiTools;
})();
