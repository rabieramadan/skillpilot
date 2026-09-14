// i18n Translation System for SkillPilot
// Supports Arabic and English with RTL support

const translations = {
    en: {
        // Navigation
        nav_chat: "AI Assistant",
        nav_library: "Templates",
        nav_assessments: "Assessments",
        nav_my_learning: "My Learning",
        nav_management: "Management",
        nav_tools: "AI Tools",
        nav_my_classes: "Enrolled Courses",
        nav_available_courses: "Browse Courses",
        nav_entry_survey: "Entry Survey",
        nav_exit_exam: "Exit Exam",
        nav_training_feedback: "Training Feedback",
        nav_my_certificates: "My Certificates",
        nav_profile: "Profile",
        nav_admin_home: "Admin Home",
        nav_courses: "Courses",
        nav_students: "Students",
        nav_instructors: "Instructors",
        nav_certificates: "Certificates",
        nav_sessions: "Sessions",
        nav_analytics: "Analytics",
        nav_ab_test: "A/B Test",
        nav_student_management: "Student Management",
        nav_course_materials: "Course Materials",
        nav_classes: "Classes",
        nav_admin: "Admin",
        nav_agentic_ai_lab: "Agentic AI Lab",
        nav_ethics_certificate: "Ethics Certificate",
        nav_my_institution: "My Institution",
        nav_institutions: "Institutions",
        nav_teacher_dashboard: "Dashboard",
        
        // Simplified Menu Labels (used by data-i18n attributes)
        chat: "AI Assistant",
        library: "Templates",
        available_courses: "Browse Courses",
        my_courses: "Enrolled Courses",
        ai_tools: "AI Lab",
        dashboard: "Dashboard",
        profile: "Profile",
        admin_dashboard: "Admin Panel",
        courses: "Courses",
        users: "Users",
        
        // User Actions
        admin_logout: "Admin Logout",
        attendance: "Attendance",
        logout: "Logout",
        
        // Prompt Library Modal
        prompt_details: "Prompt Details",
        copy_to_clipboard: "Copy to Clipboard",
        use_prompt: "Use Prompt",
        prompt_copied: "Prompt copied to clipboard!",
        prompt_loaded: "Prompt loaded to chat. Ready to send!",
        editable_note: "Editable - changes won't affect original",
        prompt_content: "Prompt Content",
        
        // Login Modal
        login_title: "User Login - SkillPilot",
        login_subtitle: "Students, Teachers, and Staff",
        tab_login: "Login",
        tab_register: "Register",
        label_username: "Username",
        label_password: "Password",
        label_fullname: "Full Name",
        label_email: "Email",
        label_phone: "Phone",
        label_organization: "Organization",
        placeholder_username: "Enter your username",
        placeholder_password: "Enter your password",
        placeholder_fullname: "Enter your full name",
        placeholder_email: "Enter your email",
        placeholder_choose_username: "Choose a username",
        placeholder_choose_password: "Choose a password (min 6 characters)",
        placeholder_phone: "Enter your phone number",
        placeholder_organization: "Enter your organization",
        btn_login: "Login",
        btn_register: "Register",
        
        // Security Questions
        security_questions_title: "Security Questions",
        security_q1: "Mother's maiden name?",
        security_q2: "City where you were born?",
        security_q3: "Favorite teacher's name?",
        security_answer_placeholder: "Answer for account recovery",
        registration_note: "All registrations are for Student accounts. Instructors are assigned by administrators.",
        
        // Admin Login
        admin_login_title: "Administrator Login",
        admin_login_subtitle: "Authorized Personnel Only",
        admin_credentials_note: "Use your administrator credentials",
        
        // Profile
        profile_title: "User Profile",
        profile_personal_info: "Personal Information",
        profile_account_info: "Account Information",
        profile_security: "Security & Recovery",
        btn_update_profile: "Update Profile",
        btn_change_password: "Change Password",
        profile_update_success: "Profile updated successfully",
        profile_update_error: "Error updating profile",
        
        // Certificates
        certificate_title: "Exit Exam Results",
        certificate_score: "Score",
        certificate_status: "Status",
        certificate_date: "Completion Date",
        status_pending: "PENDING APPROVAL",
        status_approved: "APPROVED",
        status_failed: "NOT PASSED",
        btn_download_certificate: "Download Certificate",
        btn_approve_download: "Approve & Download",
        btn_force_pass: "Force Pass",
        btn_retake: "Allow Retake",
        certificate_pending_msg: "Your certificate is pending admin approval",
        certificate_failed_msg: "Score below passing threshold (60%)",
        
        // Ethics Certificate
        ethics_no_categories: "No certificate categories available",
        ethics_questions: "Questions",
        ethics_start_assessment: "Start Assessment",
        ethics_payment_required: "Payment Required",
        ethics_pay_now: "Pay Now",
        ethics_payment_processing: "Processing...",
        ethics_payment_instructions: "You will be redirected to PayPal to complete your payment of $",
        ethics_payment_note: "After payment, please wait for admin verification before taking the exam.",
        ethics_select_domain: "Select Professional Domain",
        ethics_select_language: "Select Language",
        ethics_job_title: "Job Title",
        ethics_profession: "Profession",
        ethics_country: "Country",
        ethics_gender: "Gender",
        ethics_education: "Education Level",
        ethics_male: "Male",
        ethics_female: "Female",
        ethics_other: "Other",
        ethics_prefer_not_say: "Prefer not to say",
        ethics_high_school: "High School",
        ethics_bachelors: "Bachelor's Degree",
        ethics_masters: "Master's Degree",
        ethics_doctorate: "Doctorate",
        ethics_no_sessions: "No assessment sessions yet",
        ethics_session_in_progress: "In Progress",
        ethics_session_completed: "Completed",
        ethics_session_passed: "PASSED",
        ethics_session_failed: "FAILED",
        ethics_continue: "Continue Assessment",
        ethics_view_certificate: "View Certificate",
        ethics_scenario_loading: "Loading ethical scenario...",
        ethics_select_action: "Select your action:",
        ethics_submit_answer: "Submit Answer",
        ethics_next_question: "Next Question",
        ethics_complete_assessment: "Complete Assessment",
        ethics_evaluation: "Evaluation",
        ethics_your_score: "Your Score",
        ethics_feedback: "Feedback",
        ethics_correct_action: "Correct Action",
        ethics_improvement_tips: "Improvement Tips",
        ethics_final_results: "Final Results",
        ethics_total_score: "Total Score",
        ethics_status: "Status",
        ethics_certificate_ready: "Your certificate is ready!",
        ethics_domain_healthcare: "Healthcare & Medical",
        ethics_domain_business: "Business & Finance",
        ethics_domain_education: "Education & Academia",
        ethics_domain_technology: "Technology & AI",
        ethics_domain_prompt: "Select your professional domain:\n1. Healthcare & Medical\n2. Business & Finance\n3. Education & Academia\n\nEnter 1, 2, or 3:",
        ethics_payment_confirm: "This assessment costs $",
        ethics_payment_confirm_continue: " USD. You will be redirected to PayPal to complete payment. Continue?",
        ethics_payment_popup_blocked: "Please allow popups to complete payment. Click OK to continue.",
        ethics_payment_instructions_full: "Payment Instructions:\n\n1. Complete payment on the PayPal page that just opened\n2. After payment, return to this page\n3. Your payment will be verified by admin\n4. You'll receive notification when approved to start the assessment\n\nNote: This may take a few minutes to 24 hours depending on admin availability.",
        ethics_payment_not_configured: "Payment link not configured. Please contact administrator.",
        ethics_payment_failed: "Payment processing failed. Please try again.",
        ethics_session_create_failed: "Failed to create session",
        ethics_session_create_error: "Failed to create assessment session.",
        ethics_answer_submit_failed: "Failed to submit answer",
        ethics_complete_failed: "Failed to complete assessment.",
        ethics_professional: "Professional",
        ethics_general: "General",
        ethics_load_categories_failed: "Failed to load certificate categories",
        ethics_load_sessions_failed: "Failed to load your sessions",
        ethics_level_basic: "Basic",
        ethics_level_intermediate: "Intermediate",
        ethics_level_advanced: "Advanced",
        ethics_complexity_basic: "Basic",
        ethics_complexity_intermediate: "Intermediate",
        ethics_complexity_advanced: "Advanced",
        ethics_category_general: "General Professional Ethics",
        ethics_category_general_desc: "Core ethical principles for professional workplace situations",
        ethics_category_ai: "AI Professional Ethics",
        ethics_category_ai_desc: "Ethical principles for AI development and deployment",
        ethics_level_basic_name: "Basic Level",
        ethics_level_intermediate_name: "Intermediate Level",
        ethics_level_advanced_name: "Advanced Level",
        ethics_level_basic_desc_general: "Foundational ethical principles for workplace situations",
        ethics_level_intermediate_desc_general: "Advanced ethical decision-making scenarios",
        ethics_level_advanced_desc_general: "Complex multi-stakeholder ethical challenges",
        ethics_level_basic_desc_ai: "Foundational AI ethics and responsible AI practices",
        ethics_level_intermediate_desc_ai: "Advanced AI bias, fairness, and accountability scenarios",
        ethics_level_advanced_desc_ai: "Complex AI governance and societal impact challenges",
        
        // Class Management
        class_details: "Class Details",
        class_name: "Class Name",
        class_code: "Class Code",
        class_schedule: "Schedule",
        class_instructor: "Instructor",
        class_students: "Students",
        class_description: "Description",
        btn_add_student: "Add Student",
        btn_remove_student: "Remove Student",
        btn_upload_file: "Upload File",
        btn_delete_file: "Delete File",
        student_added_success: "Student added to class successfully. Refreshing class details...",
        student_removed_success: "Student removed from class successfully. Refreshing class details...",
        
        // Survey & Exam
        survey_title: "Entry Survey",
        exam_title: "Exit Exam",
        feedback_title: "Training Feedback",
        btn_submit_survey: "Submit Survey",
        btn_submit_exam: "Submit Exam",
        btn_submit_feedback: "Submit Feedback",
        survey_completed: "Survey completed successfully",
        exam_completed: "Exam submitted successfully",
        
        // Class Exams & Statistics
        exam_statistics: "Exam Statistics",
        survey_statistics: "Survey Statistics",
        exam_management: "Class Exam Management",
        upload_exam_csv: "Upload Exam Questions (CSV)",
        upload_exam: "Upload Exam",
        download_template: "Download Template",
        exam_template_info: "Upload a CSV file containing exam questions. Download the template to see the required format.",
        statistics_analytics: "Statistics & Analytics",
        exam_stats_button: "Exam Statistics",
        survey_stats_button: "Survey Statistics",
        total_submissions: "Total Submissions",
        average_score: "Average Score",
        pass_rate: "Pass Rate",
        highest_score: "Highest Score",
        score_distribution: "Score Distribution",
        question_difficulty: "Question Difficulty Analysis",
        individual_results: "Individual Student Results",
        total_responses: "Total Responses",
        enrolled_students: "Enrolled Students",
        response_rate: "Response Rate",
        question_responses: "Question Response Distribution",
        no_submissions: "No exam submissions yet",
        no_responses: "No survey responses yet",
        click_to_view_stats: "Click a button above to view statistics",
        take_exam: "Take Exam",
        exam_instructions: "Read all questions carefully and select the best answer.",
        submit_answers: "Submit Answers",
        question_number: "Question",
        your_answer: "Your Answer",
        correct_answer: "Correct Answer",
        points: "Points",
        exam_results: "Exam Results",
        your_score: "Your Score",
        downloading_template: "Downloading exam template...",
        exam_uploaded: "Exam uploaded successfully!",
        select_csv: "Please select a CSV file to upload",
        upload_csv_only: "Please upload a CSV file",
        
        // Admin Class Management
        class_enrollment_management: "Class Enrollment Management",
        class_management_desc: "Click on any class card to view and manage enrolled students",
        loading_classes: "Loading classes...",
        view_students: "View Students",
        student_name: "Student Name",
        student_email: "Email",
        student_status: "Status",
        actions: "Actions",
        approve: "Approve",
        block: "Block",
        remove: "Remove",
        status_approved: "Approved",
        status_blocked: "Blocked",
        status_requested: "Requested",
        status_rejected: "Rejected",
        no_students_enrolled: "No students enrolled yet",
        approve_confirm: "Approve this student enrollment?",
        block_confirm: "Block this student from accessing the class?",
        remove_confirm: "Are you sure you want to completely remove this student from the class? This action cannot be undone.",
        student_status_updated: "Student status updated successfully!",
        student_removed: "Student removed successfully!",
        
        // Admin Dashboard
        admin_dashboard: "Admin Dashboard",
        admin_users: "Manage Users",
        admin_models: "Manage Models",
        admin_settings: "System Settings",
        admin_reports: "Reports",
        total_users: "Total Users",
        total_classes: "Total Classes",
        total_instructors: "Total Instructors",
        
        // Common
        save: "Save",
        cancel: "Cancel",
        delete: "Delete",
        edit: "Edit",
        view: "View",
        add: "Add",
        remove: "Remove",
        confirm: "Confirm",
        close: "Close",
        search: "Search",
        filter: "Filter",
        export: "Export",
        import: "Import",
        loading: "Loading...",
        error: "Error",
        success: "Success",
        warning: "Warning",
        required: "Required",
        optional: "Optional",
        yes: "Yes",
        no: "No",
        select: "Select",
        none: "None",
        all: "All",
        
        // Messages
        confirm_delete: "Are you sure you want to delete this?",
        confirm_force_pass: "Are you sure you want to override this result and mark as passed?",
        action_success: "Action completed successfully",
        action_error: "An error occurred",
        no_data: "No data available",
        
        // Language Toggle
        language: "Language",
        switch_to_arabic: "العربية",
        switch_to_english: "English",
        btn_language: "العربية",
        btn_back: "Back",
        
        // AI Tools Suite
        ai_tools_suite: "AI Tools Suite",
        ai_tools_suite_title: "AI Tools Suite",
        ai_tools_suite_desc: "Comprehensive AI-powered tools for content creation, analysis, and productivity",
        select_ai_model: "AI Model:",
        select_output_language: "Output Language:",
        common_tools: "Common Tools",
        teacher_tools: "Teacher Tools",
        student_tools: "Student Tools",
        admin_tools: "Admin Tools",
        tool_content_chat: "Chat with Content",
        tool_content_chat_desc: "Ask questions about course documents",
        tool_study_assistant: "Study Assistant",
        tool_study_assistant_desc: "Get explanations and study tips",
        tool_flashcards: "Flashcard Generator",
        tool_flashcards_desc: "Create study flashcards",
        tool_concept: "Concept Explainer",
        tool_concept_desc: "Get simple explanations",
        tool_quiz: "Practice Quiz",
        tool_quiz_desc: "Generate practice quizzes",
        tool_essay: "Essay Helper",
        tool_essay_desc: "Get writing assistance",
        tool_notes: "Note Organizer",
        tool_notes_desc: "Organize your notes",
        tool_learning_path: "Learning Path",
        tool_learning_path_desc: "Get study recommendations"
    },
    
    ar: {
        // Navigation - الملاحة
        nav_chat: "مساعد الذكاء",
        nav_library: "القوالب",
        nav_assessments: "التقييمات",
        nav_my_learning: "تعلمي",
        nav_management: "الإدارة",
        nav_tools: "أدوات الذكاء",
        nav_my_classes: "دوراتي المسجلة",
        nav_available_courses: "تصفح الدورات",
        nav_entry_survey: "الاستبيان الأولي",
        nav_exit_exam: "الاختبار النهائي",
        nav_training_feedback: "تقييم التدريب",
        nav_my_certificates: "شهاداتي",
        nav_profile: "الملف الشخصي",
        nav_admin_home: "لوحة الإدارة",
        nav_courses: "الدورات",
        nav_students: "الطلاب",
        nav_instructors: "المدربون",
        nav_certificates: "الشهادات",
        nav_sessions: "الجلسات",
        nav_analytics: "التحليلات",
        nav_ab_test: "اختبار أ/ب",
        nav_student_management: "إدارة الطلاب",
        nav_course_materials: "مواد الدورات",
        nav_classes: "الصفوف",
        nav_admin: "الإدارة",
        nav_agentic_ai_lab: "مختبر الذكاء الاصطناعي",
        nav_ethics_certificate: "شهادة الأخلاقيات",
        nav_my_institution: "مؤسستي",
        nav_institutions: "المؤسسات",
        nav_teacher_dashboard: "لوحة التحكم",
        
        // Simplified Menu Labels - تسميات القائمة المبسطة
        chat: "مساعد الذكاء",
        library: "القوالب",
        available_courses: "تصفح الدورات",
        my_courses: "دوراتي المسجلة",
        ai_tools: "معمل الذكاء",
        dashboard: "لوحة التحكم",
        profile: "الملف الشخصي",
        admin_dashboard: "لوحة الإدارة",
        courses: "الدورات",
        users: "المستخدمون",
        
        // User Actions - إجراءات المستخدم
        admin_logout: "تسجيل خروج المسؤول",
        attendance: "الحضور",
        logout: "تسجيل الخروج",
        
        // Prompt Library Modal - نافذة مكتبة البرومبتات
        prompt_details: "تفاصيل البرومبت",
        copy_to_clipboard: "نسخ إلى الحافظة",
        use_prompt: "استخدام البرومبت",
        prompt_copied: "تم نسخ البرومبت إلى الحافظة!",
        prompt_loaded: "تم تحميل البرومبت للمحادثة. جاهز للإرسال!",
        editable_note: "قابل للتعديل - التغييرات لن تؤثر على الأصل",
        prompt_content: "محتوى البرومبت",
        
        // Login Modal - نافذة تسجيل الدخول
        login_title: "تسجيل الدخول - SkillPilot",
        login_subtitle: "الطلاب والمعلمون والموظفون",
        tab_login: "تسجيل الدخول",
        tab_register: "التسجيل",
        label_username: "اسم المستخدم",
        label_password: "كلمة المرور",
        label_fullname: "الاسم الكامل",
        label_email: "البريد الإلكتروني",
        label_phone: "الهاتف",
        label_organization: "المؤسسة",
        placeholder_username: "أدخل اسم المستخدم",
        placeholder_password: "أدخل كلمة المرور",
        placeholder_fullname: "أدخل اسمك الكامل",
        placeholder_email: "أدخل بريدك الإلكتروني",
        placeholder_choose_username: "اختر اسم المستخدم",
        placeholder_choose_password: "اختر كلمة المرور (6 أحرف على الأقل)",
        placeholder_phone: "أدخل رقم هاتفك",
        placeholder_organization: "أدخل اسم مؤسستك",
        btn_login: "تسجيل الدخول",
        btn_register: "تسجيل",
        
        // Security Questions - أسئلة الأمان
        security_questions_title: "أسئلة الأمان",
        security_q1: "اسم عائلة والدتك قبل الزواج؟",
        security_q2: "المدينة التي ولدت فيها؟",
        security_q3: "اسم معلمك المفضل؟",
        security_answer_placeholder: "الإجابة لاستعادة الحساب",
        registration_note: "جميع التسجيلات لحسابات الطلاب. يتم تعيين المدربين من قبل المسؤولين.",
        
        // Admin Login - تسجيل دخول المسؤول
        admin_login_title: "تسجيل دخول المسؤول",
        admin_login_subtitle: "للموظفين المصرح لهم فقط",
        admin_credentials_note: "استخدم بيانات اعتماد المسؤول الخاصة بك",
        
        // Profile - الملف الشخصي
        profile_title: "الملف الشخصي",
        profile_personal_info: "المعلومات الشخصية",
        profile_account_info: "معلومات الحساب",
        profile_security: "الأمان والاسترداد",
        btn_update_profile: "تحديث الملف الشخصي",
        btn_change_password: "تغيير كلمة المرور",
        profile_update_success: "تم تحديث الملف الشخصي بنجاح",
        profile_update_error: "خطأ في تحديث الملف الشخصي",
        
        // Certificates - الشهادات
        certificate_title: "نتائج الاختبار النهائي",
        certificate_score: "الدرجة",
        certificate_status: "الحالة",
        certificate_date: "تاريخ الإكمال",
        status_pending: "في انتظار الموافقة",
        status_approved: "تمت الموافقة",
        status_failed: "لم ينجح",
        btn_download_certificate: "تحميل الشهادة",
        btn_approve_download: "الموافقة والتحميل",
        btn_force_pass: "اجتياز إجباري",
        btn_retake: "السماح بإعادة الاختبار",
        certificate_pending_msg: "شهادتك في انتظار موافقة المسؤول",
        certificate_failed_msg: "الدرجة أقل من درجة النجاح (60%)",
        
        // Ethics Certificate - شهادة الأخلاقيات
        ethics_no_categories: "لا توجد فئات شهادات متاحة",
        ethics_questions: "الأسئلة",
        ethics_start_assessment: "بدء التقييم",
        ethics_payment_required: "الدفع مطلوب",
        ethics_pay_now: "ادفع الآن",
        ethics_payment_processing: "جاري المعالجة...",
        ethics_payment_instructions: "سيتم توجيهك إلى PayPal لإكمال دفع $",
        ethics_payment_note: "بعد الدفع، يرجى انتظار تأكيد المسؤول قبل البدء بالاختبار.",
        ethics_select_domain: "اختر المجال المهني",
        ethics_select_language: "اختر اللغة",
        ethics_job_title: "المسمى الوظيفي",
        ethics_profession: "المهنة",
        ethics_country: "البلد",
        ethics_gender: "الجنس",
        ethics_education: "المستوى التعليمي",
        ethics_male: "ذكر",
        ethics_female: "أنثى",
        ethics_other: "آخر",
        ethics_prefer_not_say: "أفضل عدم الإفصاح",
        ethics_high_school: "الثانوية العامة",
        ethics_bachelors: "بكالوريوس",
        ethics_masters: "ماجستير",
        ethics_doctorate: "دكتوراه",
        ethics_no_sessions: "لا توجد جلسات تقييم بعد",
        ethics_session_in_progress: "قيد التنفيذ",
        ethics_session_completed: "مكتمل",
        ethics_session_passed: "ناجح",
        ethics_session_failed: "راسب",
        ethics_continue: "متابعة التقييم",
        ethics_view_certificate: "عرض الشهادة",
        ethics_scenario_loading: "جاري تحميل السيناريو الأخلاقي...",
        ethics_select_action: "اختر إجراءك:",
        ethics_submit_answer: "إرسال الإجابة",
        ethics_next_question: "السؤال التالي",
        ethics_complete_assessment: "إكمال التقييم",
        ethics_evaluation: "التقييم",
        ethics_your_score: "درجتك",
        ethics_feedback: "الملاحظات",
        ethics_correct_action: "الإجراء الصحيح",
        ethics_improvement_tips: "نصائح للتحسين",
        ethics_final_results: "النتائج النهائية",
        ethics_total_score: "الدرجة الإجمالية",
        ethics_status: "الحالة",
        ethics_certificate_ready: "شهادتك جاهزة!",
        ethics_domain_healthcare: "الرعاية الصحية والطب",
        ethics_domain_business: "الأعمال والمالية",
        ethics_domain_education: "التعليم والأكاديميا",
        ethics_domain_technology: "التكنولوجيا والذكاء الاصطناعي",
        ethics_domain_prompt: "اختر مجالك المهني:\n1. الرعاية الصحية والطب\n2. الأعمال والمالية\n3. التعليم والأكاديميا\n\nأدخل 1 أو 2 أو 3:",
        ethics_payment_confirm: "تكلفة هذا التقييم $",
        ethics_payment_confirm_continue: " دولار أمريكي. سيتم توجيهك إلى PayPal لإكمال الدفع. هل تريد المتابعة؟",
        ethics_payment_popup_blocked: "يرجى السماح بالنوافذ المنبثقة لإكمال الدفع. انقر فوق موافق للمتابعة.",
        ethics_payment_instructions_full: "تعليمات الدفع:\n\n1. أكمل الدفع في صفحة PayPal التي فُتحت\n2. بعد الدفع، عد إلى هذه الصفحة\n3. سيتم التحقق من دفعك من قبل المسؤول\n4. ستتلقى إشعارًا عند الموافقة لبدء التقييم\n\nملاحظة: قد يستغرق هذا من بضع دقائق إلى 24 ساعة حسب توفر المسؤول.",
        ethics_payment_not_configured: "لم يتم تكوين رابط الدفع. يرجى الاتصال بالمسؤول.",
        ethics_payment_failed: "فشلت معالجة الدفع. يرجى المحاولة مرة أخرى.",
        ethics_session_create_failed: "فشل في إنشاء الجلسة",
        ethics_session_create_error: "فشل في إنشاء جلسة التقييم.",
        ethics_answer_submit_failed: "فشل في إرسال الإجابة",
        ethics_complete_failed: "فشل في إكمال التقييم.",
        ethics_professional: "محترف",
        ethics_general: "عام",
        ethics_load_categories_failed: "فشل تحميل فئات الشهادات",
        ethics_load_sessions_failed: "فشل تحميل جلساتك",
        ethics_level_basic: "أساسي",
        ethics_level_intermediate: "متوسط",
        ethics_level_advanced: "متقدم",
        ethics_complexity_basic: "أساسي",
        ethics_complexity_intermediate: "متوسط",
        ethics_complexity_advanced: "متقدم",
        ethics_category_general: "أخلاقيات العمل المهني العامة",
        ethics_category_general_desc: "المبادئ الأخلاقية الأساسية لبيئة العمل المهنية",
        ethics_category_ai: "أخلاقيات المهنيين في الذكاء الاصطناعي",
        ethics_category_ai_desc: "المبادئ الأخلاقية لتطوير ونشر الذكاء الاصطناعي",
        ethics_level_basic_name: "المستوى الأساسي",
        ethics_level_intermediate_name: "المستوى المتوسط",
        ethics_level_advanced_name: "المستوى المتقدم",
        ethics_level_basic_desc_general: "المبادئ الأخلاقية الأساسية لمواقف العمل",
        ethics_level_intermediate_desc_general: "سيناريوهات متقدمة لاتخاذ القرارات الأخلاقية",
        ethics_level_advanced_desc_general: "تحديات أخلاقية معقدة متعددة أصحاب المصلحة",
        ethics_level_basic_desc_ai: "أخلاقيات الذكاء الاصطناعي الأساسية وممارسات الذكاء الاصطناعي المسؤول",
        ethics_level_intermediate_desc_ai: "سيناريوهات متقدمة للتحيز والعدالة والمساءلة في الذكاء الاصطناعي",
        ethics_level_advanced_desc_ai: "تحديات حوكمة الذكاء الاصطناعي والتأثير المجتمعي المعقدة",
        
        // Class Management - إدارة الصفوف
        class_details: "تفاصيل الصف",
        class_name: "اسم الصف",
        class_code: "رمز الصف",
        class_schedule: "الجدول الزمني",
        class_instructor: "المدرب",
        class_students: "الطلاب",
        class_description: "الوصف",
        btn_add_student: "إضافة طالب",
        btn_remove_student: "إزالة طالب",
        btn_upload_file: "رفع ملف",
        btn_delete_file: "حذف ملف",
        student_added_success: "تمت إضافة الطالب إلى الصف بنجاح. جاري تحديث التفاصيل...",
        student_removed_success: "تمت إزالة الطالب من الصف بنجاح. جاري تحديث التفاصيل...",
        
        // Survey & Exam - الاستبيان والاختبار
        survey_title: "الاستبيان الأولي",
        exam_title: "الاختبار النهائي",
        feedback_title: "تقييم التدريب",
        btn_submit_survey: "إرسال الاستبيان",
        btn_submit_exam: "إرسال الاختبار",
        btn_submit_feedback: "إرسال التقييم",
        survey_completed: "تم إكمال الاستبيان بنجاح",
        exam_completed: "تم إرسال الاختبار بنجاح",
        
        // Class Exams & Statistics - اختبارات وإحصائيات الصفوف
        exam_statistics: "إحصائيات الاختبار",
        survey_statistics: "إحصائيات الاستبيان",
        exam_management: "إدارة اختبار الصف",
        upload_exam_csv: "رفع أسئلة الاختبار (CSV)",
        upload_exam: "رفع الاختبار",
        download_template: "تحميل النموذج",
        exam_template_info: "قم برفع ملف CSV يحتوي على أسئلة الاختبار. حمّل النموذج لرؤية التنسيق المطلوب.",
        statistics_analytics: "الإحصائيات والتحليلات",
        exam_stats_button: "إحصائيات الاختبار",
        survey_stats_button: "إحصائيات الاستبيان",
        total_submissions: "إجمالي التسليمات",
        average_score: "متوسط الدرجة",
        pass_rate: "نسبة النجاح",
        highest_score: "أعلى درجة",
        score_distribution: "توزيع الدرجات",
        question_difficulty: "تحليل صعوبة الأسئلة",
        individual_results: "نتائج الطلاب الفردية",
        total_responses: "إجمالي الإجابات",
        enrolled_students: "الطلاب المسجلون",
        response_rate: "معدل الاستجابة",
        question_responses: "توزيع إجابات الأسئلة",
        no_submissions: "لا توجد تسليمات اختبار بعد",
        no_responses: "لا توجد إجابات استبيان بعد",
        click_to_view_stats: "انقر على زر أعلاه لعرض الإحصائيات",
        take_exam: "أداء الاختبار",
        exam_instructions: "اقرأ جميع الأسئلة بعناية واختر أفضل إجابة.",
        submit_answers: "إرسال الإجابات",
        question_number: "السؤال",
        your_answer: "إجابتك",
        correct_answer: "الإجابة الصحيحة",
        points: "النقاط",
        exam_results: "نتائج الاختبار",
        your_score: "درجتك",
        downloading_template: "جاري تحميل نموذج الاختبار...",
        exam_uploaded: "تم رفع الاختبار بنجاح!",
        select_csv: "يرجى اختيار ملف CSV للرفع",
        upload_csv_only: "يرجى رفع ملف CSV",
        
        // Admin Class Management - إدارة تسجيل الصفوف
        class_enrollment_management: "إدارة تسجيل الصفوف",
        class_management_desc: "انقر على أي بطاقة صف لعرض وإدارة الطلاب المسجلين",
        loading_classes: "جاري تحميل الصفوف...",
        view_students: "عرض الطلاب",
        student_name: "اسم الطالب",
        student_email: "البريد الإلكتروني",
        student_status: "الحالة",
        actions: "الإجراءات",
        approve: "موافقة",
        block: "حظر",
        remove: "إزالة",
        status_approved: "مُوافق عليه",
        status_blocked: "محظور",
        status_requested: "مطلوب",
        status_rejected: "مرفوض",
        no_students_enrolled: "لا يوجد طلاب مسجلون بعد",
        approve_confirm: "هل تريد الموافقة على تسجيل هذا الطالب؟",
        block_confirm: "هل تريد حظر هذا الطالب من الوصول إلى الصف؟",
        remove_confirm: "هل أنت متأكد من إزالة هذا الطالب من الصف بالكامل؟ لا يمكن التراجع عن هذا الإجراء.",
        student_status_updated: "تم تحديث حالة الطالب بنجاح!",
        student_removed: "تم إزالة الطالب بنجاح!",
        
        // Admin Dashboard - لوحة تحكم المسؤول
        admin_dashboard: "لوحة تحكم المسؤول",
        admin_users: "إدارة المستخدمين",
        admin_models: "إدارة النماذج",
        admin_settings: "إعدادات النظام",
        admin_reports: "التقارير",
        total_users: "إجمالي المستخدمين",
        total_classes: "إجمالي الصفوف",
        total_instructors: "إجمالي المدربين",
        
        // Common - عام
        save: "حفظ",
        cancel: "إلغاء",
        delete: "حذف",
        edit: "تعديل",
        view: "عرض",
        add: "إضافة",
        remove: "إزالة",
        confirm: "تأكيد",
        close: "إغلاق",
        search: "بحث",
        filter: "تصفية",
        export: "تصدير",
        import: "استيراد",
        loading: "جاري التحميل...",
        error: "خطأ",
        success: "نجاح",
        warning: "تحذير",
        required: "مطلوب",
        optional: "اختياري",
        yes: "نعم",
        no: "لا",
        select: "اختر",
        none: "لا يوجد",
        all: "الكل",
        
        // Messages - الرسائل
        confirm_delete: "هل أنت متأكد من الحذف؟",
        confirm_force_pass: "هل أنت متأكد من تجاوز هذه النتيجة ووضع علامة النجاح؟",
        action_success: "تمت العملية بنجاح",
        action_error: "حدث خطأ",
        no_data: "لا توجد بيانات",
        
        // Language Toggle - تبديل اللغة
        language: "اللغة",
        switch_to_arabic: "العربية",
        switch_to_english: "English",
        btn_language: "English",
        btn_back: "رجوع",
        
        // AI Tools Suite - مجموعة أدوات الذكاء الاصطناعي
        ai_tools_suite: "مجموعة أدوات الذكاء",
        ai_tools_suite_title: "مجموعة أدوات الذكاء الاصطناعي",
        ai_tools_suite_desc: "أدوات ذكاء اصطناعي شاملة لإنشاء المحتوى والتحليل والإنتاجية",
        select_ai_model: "نموذج الذكاء:",
        select_output_language: "لغة الإخراج:",
        common_tools: "الأدوات العامة",
        teacher_tools: "أدوات المعلم",
        student_tools: "أدوات الطالب",
        admin_tools: "أدوات الإدارة",
        tool_content_chat: "الدردشة مع المحتوى",
        tool_content_chat_desc: "اطرح أسئلة عن مستندات الدورة",
        tool_study_assistant: "مساعد الدراسة",
        tool_study_assistant_desc: "احصل على شروحات ونصائح دراسية",
        tool_flashcards: "مولد البطاقات التعليمية",
        tool_flashcards_desc: "إنشاء بطاقات تعليمية",
        tool_concept: "شارح المفاهيم",
        tool_concept_desc: "احصل على شروحات بسيطة",
        tool_quiz: "اختبار تدريبي",
        tool_quiz_desc: "إنشاء اختبارات تدريبية",
        tool_essay: "مساعد المقالات",
        tool_essay_desc: "احصل على مساعدة في الكتابة",
        tool_notes: "منظم الملاحظات",
        tool_notes_desc: "نظم ملاحظاتك",
        tool_learning_path: "مسار التعلم",
        tool_learning_path_desc: "احصل على توصيات دراسية"
    }
};

class I18n {
    constructor() {
        // Try to get language from localStorage with error handling
        let savedLang = 'en';
        try {
            savedLang = localStorage.getItem('language') || 'en';
        } catch (e) {
            console.warn('localStorage not available, using default language (en):', e);
        }
        
        this.currentLanguage = savedLang;
        this.translations = translations;
        console.log('I18n initialized with language:', this.currentLanguage);
        this.init();
    }
    
    init() {
        this.updatePageDirection();
        this.updateHtmlLang();
        
        // Translate page once DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.translatePage();
            });
        } else {
            // DOM is already ready
            this.translatePage();
        }
    }
    
    setLanguage(lang) {
        if (lang !== 'en' && lang !== 'ar') {
            console.error('Invalid language:', lang);
            return;
        }
        
        this.currentLanguage = lang;
        
        // Try to save to localStorage with error handling
        try {
            localStorage.setItem('language', lang);
        } catch (e) {
            console.warn('Could not save language to localStorage:', e);
        }
        
        this.updatePageDirection();
        this.updateHtmlLang();
        this.translatePage();
        
        console.log('Language changed to:', lang);
        
        // Trigger custom event for other components to react
        window.dispatchEvent(new CustomEvent('languageChanged', { detail: { language: lang } }));
    }
    
    toggleLanguage() {
        const newLang = this.currentLanguage === 'en' ? 'ar' : 'en';
        this.setLanguage(newLang);
    }
    
    updatePageDirection() {
        if (this.currentLanguage === 'ar') {
            document.documentElement.setAttribute('dir', 'rtl');
            document.body.classList.add('rtl');
        } else {
            document.documentElement.setAttribute('dir', 'ltr');
            document.body.classList.remove('rtl');
        }
    }
    
    updateHtmlLang() {
        document.documentElement.setAttribute('lang', this.currentLanguage);
    }
    
    t(key) {
        const keys = key.split('.');
        let value = this.translations[this.currentLanguage];
        
        for (const k of keys) {
            if (value && typeof value === 'object') {
                value = value[k];
            } else {
                break;
            }
        }
        
        return value || this.translations['en'][key] || key;
    }
    
    translatePage() {
        // Translate all elements with data-i18n attribute
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translation = this.t(key);
            
            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                if (element.hasAttribute('placeholder')) {
                    element.setAttribute('placeholder', translation);
                }
            } else {
                // Preserve HTML structure, only replace text content
                const icon = element.querySelector('i');
                if (icon) {
                    element.innerHTML = icon.outerHTML + ' ' + translation;
                } else {
                    element.textContent = translation;
                }
            }
        });
        
        // Update language toggle button text
        const langBtn = document.getElementById('languageToggleBtn');
        if (langBtn) {
            const langText = langBtn.querySelector('.lang-text');
            if (langText) {
                langText.textContent = this.currentLanguage === 'en' ? 'العربية' : 'English';
            }
        }
    }
    
    getCurrentLanguage() {
        return this.currentLanguage;
    }
    
    isRTL() {
        return this.currentLanguage === 'ar';
    }
}

// Initialize i18n
const i18n = new I18n();

// Export for use in other scripts
window.i18n = i18n;
