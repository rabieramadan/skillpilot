/**
 * Student Class Dashboard - Class-Centric Interface
 * All student interactions scoped by class/course
 */

class StudentClassDashboard {
    constructor() {
        this.classes = [];
        this.currentClass = null;
        this.currentTab = 'overview';
    }

    async init() {
        console.log('Initializing Student Class Dashboard...');
        await this.loadClasses();
        this.setupEventListeners();
    }

    async loadAdaptiveProgress() {
        try {
            const response = await fetch(
                '/api/v1/personalization/adaptive-progress?days=7',
                { credentials: 'include' }
            );
            if (!response.ok) return;
            const data = await response.json();
            this.renderAdaptiveProgress(data);
        } catch (err) {
            console.warn('Error loading adaptive progress:', err);
        }
    }

    renderAdaptiveProgress(data) {
        const container = document.getElementById('studentClassesContainer');
        if (!container || !data || data.error) return;

        const gained = data.gained_skills || [];
        const next = data.next_step;

        // Hide widget entirely until the learner has at least one signal —
        // either a recent skill change OR a recommended next step.
        if (gained.length === 0 && !next) return;

        const existing = document.getElementById('adaptiveProgressCard');
        const html = `
            <div class="adaptive-progress-card" id="adaptiveProgressCard"
                 data-testid="card-adaptive-progress"
                 style="background:linear-gradient(135deg,#f0f4ff 0%,#fdf2ff 100%);
                        border:1px solid #e0e0f5;border-radius:12px;
                        padding:20px;margin-bottom:24px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                    <i class="fas fa-bolt" style="color:#7c3aed;font-size:20px;"></i>
                    <h3 style="margin:0;font-size:18px;" data-testid="text-adaptive-progress-title">
                        Adaptive progress
                    </h3>
                    <span style="font-size:12px;color:#666;margin-left:auto;"
                          data-testid="text-adaptive-window">
                        Last ${data.window_days || 7} days
                    </span>
                </div>

                ${gained.length > 0 ? `
                    <div style="margin-bottom:14px;" data-testid="section-skills-grown">
                        <div style="font-size:13px;color:#555;margin-bottom:8px;font-weight:600;">
                            Skills you grew
                        </div>
                        <div style="display:flex;flex-direction:column;gap:8px;">
                            ${gained.slice(0, 4).map((s) => `
                                <div data-testid="row-skill-delta-${s.skill_code}"
                                     style="display:flex;align-items:center;gap:10px;
                                            background:#fff;border-radius:8px;padding:8px 12px;">
                                    <div style="flex:1;min-width:0;">
                                        <div style="font-weight:500;font-size:14px;
                                                    overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
                                             data-testid="text-skill-name-${s.skill_code}">
                                            ${s.skill_name || s.skill_code}
                                        </div>
                                        <div style="font-size:11px;color:#777;">
                                            via ${s.last_source || 'adaptive'}
                                        </div>
                                    </div>
                                    <div style="font-size:12px;color:#444;">
                                        Lv ${s.previous_level} → <strong>Lv ${s.new_level}</strong>
                                    </div>
                                    <div data-testid="text-skill-delta-${s.skill_code}"
                                         style="background:#dcfce7;color:#166534;
                                                font-weight:600;font-size:12px;
                                                padding:3px 8px;border-radius:999px;">
                                        +${s.delta}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : `
                    <div style="font-size:13px;color:#666;margin-bottom:14px;"
                         data-testid="text-no-skill-deltas">
                        No skill level changes yet this week — keep learning to see growth here.
                    </div>
                `}

                ${next ? `
                    <div data-testid="section-next-step"
                         style="background:#fff;border-radius:8px;padding:12px;
                                border-left:3px solid #7c3aed;">
                        <div style="font-size:12px;color:#777;margin-bottom:4px;">
                            Recommended next step
                        </div>
                        <div style="font-weight:600;font-size:14px;margin-bottom:4px;"
                             data-testid="text-next-step-title">
                            ${next.title || next.step_type}
                        </div>
                        <div style="font-size:12px;color:#555;">
                            ${next.primary_skill_code ? `Builds: <strong>${next.primary_skill_code}</strong>` : ''}
                            ${next.estimated_minutes ? ` &middot; ~${next.estimated_minutes} min` : ''}
                        </div>
                        ${next.rationale ? `
                            <div style="font-size:12px;color:#666;margin-top:6px;font-style:italic;">
                                ${next.rationale}
                            </div>
                        ` : ''}
                    </div>
                ` : ''}
            </div>
        `;

        if (existing) {
            existing.outerHTML = html;
        } else {
            container.insertAdjacentHTML('afterbegin', html);
        }
    }

    setupEventListeners() {
        document.addEventListener('click', (e) => {
            // Handle tab button clicks (also check parent for icon/text clicks)
            const tabBtn = e.target.closest('.class-tab-btn');
            if (tabBtn) {
                const tab = tabBtn.dataset.tab;
                console.log('Tab clicked:', tab);
                this.switchTab(tab);
            }
            // Handle back button clicks
            const backBtn = e.target.closest('.back-to-classes');
            if (backBtn) {
                this.showClassList();
            }
            // Handle certificate download button clicks
            const downloadBtn = e.target.closest('[data-testid="button-download-certificate"]');
            if (downloadBtn) {
                e.preventDefault();
                this.downloadCertificate();
            }
        });
    }

    async downloadCertificate() {
        if (!this.currentClass) return;
        
        const classId = this.currentClass.class.id;
        const studentName = this.currentClass.class.title || 'Certificate';
        
        try {
            const response = await fetch(`/api/student/class/${classId}/certificate/download`, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                throw new Error('Failed to download certificate');
            }
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Certificate_${studentName.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Error downloading certificate:', error);
            alert('Failed to download certificate. Please try again.');
        }
    }

    async loadClasses() {
        try {
            const response = await fetch('/api/student/classes', {
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.classes = data.classes || [];
            this.renderClassList();
        } catch (error) {
            console.error('Error loading classes:', error);
            this.showError('Failed to load your classes');
        }
    }

    renderClassList() {
        const container = document.getElementById('studentClassesContainer');
        if (!container) return;

        if (this.classes.length === 0) {
            container.innerHTML = `
                <div class="empty-state" data-testid="empty-classes">
                    <i class="fas fa-graduation-cap" style="font-size: 48px; color: #ccc;"></i>
                    <h3>No Classes Yet</h3>
                    <p>You are not enrolled in any classes. Contact your administrator to get enrolled.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="classes-grid" data-testid="classes-grid">
                ${this.classes.map(cls => this.renderClassCard(cls)).join('')}
            </div>
        `;
        // Refresh the adaptive widget every time the class list is re-rendered
        // (e.g. after returning from a class) so deltas stay current.
        this.loadAdaptiveProgress().catch((e) =>
            console.warn('adaptive progress load failed', e));
    }

    renderClassCard(cls) {
        const progressPercent = cls.progress_percent || 0;
        const surveysCompleted = cls.surveys?.completed || 0;
        const surveysTotal = cls.surveys?.total || 0;
        const examsCompleted = cls.exams?.completed || 0;
        const examsTotal = cls.exams?.total || 0;
        
        const certificateStatus = cls.certificate_status || 'not_started';
        const certificateBadge = this.getCertificateBadge(certificateStatus);

        return `
            <div class="class-card" onclick="window.studentClassDashboard.openClass('${cls.id}')" data-testid="class-card-${cls.id}">
                <div class="class-card-header">
                    <div class="class-thumbnail" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                        <i class="fas fa-book-open"></i>
                    </div>
                    <div class="class-info">
                        <span class="class-code">${cls.code || ''}</span>
                        <h3 class="class-title">${cls.title}</h3>
                    </div>
                </div>
                
                <div class="class-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progressPercent}%"></div>
                    </div>
                    <span class="progress-text">${Math.round(progressPercent)}% Complete</span>
                </div>

                <div class="class-stats">
                    <div class="stat-item" data-testid="stat-surveys-${cls.id}">
                        <i class="fas fa-clipboard-list"></i>
                        <span>${surveysCompleted}/${surveysTotal} Surveys</span>
                    </div>
                    <div class="stat-item" data-testid="stat-exams-${cls.id}">
                        <i class="fas fa-file-alt"></i>
                        <span>${examsCompleted}/${examsTotal} Exams</span>
                    </div>
                    <div class="stat-item" data-testid="stat-certificate-${cls.id}">
                        ${certificateBadge}
                    </div>
                </div>

                <div class="class-card-footer">
                    <button class="btn-primary" onclick="event.stopPropagation(); window.studentClassDashboard.openClass('${cls.id}')" data-testid="button-open-class-${cls.id}">
                        <i class="fas fa-arrow-right"></i> Open Class
                    </button>
                </div>
            </div>
        `;
    }

    getCertificateBadge(status) {
        const badges = {
            'not_started': '<i class="fas fa-certificate" style="color: #ccc;"></i> <span>Not Started</span>',
            'pending': '<i class="fas fa-hourglass-half" style="color: #f39c12;"></i> <span>Pending</span>',
            'approved': '<i class="fas fa-check-circle" style="color: #27ae60;"></i> <span>Approved</span>',
            'not_eligible': '<i class="fas fa-times-circle" style="color: #e74c3c;"></i> <span>Not Eligible</span>'
        };
        return badges[status] || badges['not_started'];
    }

    async openClass(classId) {
        console.log('Opening class:', classId);
        try {
            const response = await fetch(`/api/student/class/${classId}/dashboard`, {
                credentials: 'include'
            });

            console.log('Class dashboard response status:', response.status);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Class dashboard data:', data);
            this.currentClass = data;
            this.renderClassDashboard();
        } catch (error) {
            console.error('Error loading class dashboard:', error);
            this.showError('Failed to load class dashboard');
        }
    }

    renderClassDashboard() {
        const container = document.getElementById('studentClassesContainer');
        if (!container || !this.currentClass) return;

        const cls = this.currentClass.class;
        const enrollment = this.currentClass.enrollment;
        const materials = this.currentClass.materials;
        const surveys = this.currentClass.surveys || [];
        const exams = this.currentClass.exams || [];
        const certificate = this.currentClass.certificate;

        container.innerHTML = `
            <div class="class-dashboard" data-testid="class-dashboard-${cls.id}">
                <!-- Back Button & Header -->
                <div class="dashboard-header">
                    <button class="back-to-classes btn-secondary" data-testid="button-back-to-classes">
                        <i class="fas fa-arrow-left"></i> Back to Classes
                    </button>
                    <div class="class-header-info">
                        <span class="class-code">${cls.code || ''}</span>
                        <h2>${cls.title}</h2>
                        <p>${cls.description || ''}</p>
                    </div>
                </div>

                <!-- Progress Overview -->
                <div class="progress-overview">
                    <div class="progress-bar large">
                        <div class="progress-fill" style="width: ${enrollment.progress_percent || 0}%"></div>
                    </div>
                    <span class="progress-text">${Math.round(enrollment.progress_percent || 0)}% Complete</span>
                </div>

                <!-- Tab Navigation -->
                <div class="class-tabs">
                    <button class="class-tab-btn active" data-tab="overview" data-testid="tab-overview">
                        <i class="fas fa-home"></i> Overview
                    </button>
                    <button class="class-tab-btn" data-tab="materials" data-testid="tab-materials">
                        <i class="fas fa-book"></i> Materials (${materials.total || 0})
                    </button>
                    <button class="class-tab-btn" data-tab="surveys" data-testid="tab-surveys">
                        <i class="fas fa-clipboard-list"></i> Surveys (${surveys.length})
                    </button>
                    <button class="class-tab-btn" data-tab="exams" data-testid="tab-exams">
                        <i class="fas fa-file-alt"></i> Exams (${exams.length})
                    </button>
                    <button class="class-tab-btn" data-tab="certificate" data-testid="tab-certificate">
                        <i class="fas fa-certificate"></i> Certificate
                    </button>
                </div>

                <!-- Tab Content -->
                <div class="class-tab-content">
                    ${this.renderOverviewTab()}
                </div>
            </div>
        `;

        this.currentTab = 'overview';
    }

    switchTab(tab) {
        console.log('Switching to tab:', tab);
        this.currentTab = tab;
        
        // Update active state on tab buttons
        document.querySelectorAll('.class-dashboard .class-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });

        // Find the tab content container within the class dashboard
        const contentContainer = document.querySelector('.class-dashboard .class-tab-content');
        if (!contentContainer) {
            console.error('Tab content container not found!');
            return;
        }

        // Render the appropriate tab content
        let content = '';
        switch (tab) {
            case 'overview':
                content = this.renderOverviewTab();
                break;
            case 'materials':
                content = this.renderMaterialsTab();
                break;
            case 'surveys':
                content = this.renderSurveysTab();
                break;
            case 'exams':
                content = this.renderExamsTab();
                break;
            case 'certificate':
                content = this.renderCertificateTab();
                break;
        }
        
        contentContainer.innerHTML = content;
        console.log('Tab content updated for:', tab);
    }

    renderOverviewTab() {
        const cls = this.currentClass.class;
        const materials = this.currentClass.materials;
        const surveys = this.currentClass.surveys || [];
        const exams = this.currentClass.exams || [];
        const certificate = this.currentClass.certificate;

        const completedSurveys = surveys.filter(s => s.is_completed).length;
        const completedExams = exams.filter(e => e.best_result).length;

        return `
            <div class="overview-tab" data-testid="overview-content">
                <div class="overview-grid">
                    <div class="overview-card">
                        <div class="card-icon" style="background: #3498db;">
                            <i class="fas fa-book"></i>
                        </div>
                        <div class="card-info">
                            <span class="card-value">${materials.completed || 0}/${materials.total || 0}</span>
                            <span class="card-label">Materials Completed</span>
                        </div>
                    </div>
                    
                    <div class="overview-card">
                        <div class="card-icon" style="background: #9b59b6;">
                            <i class="fas fa-clipboard-list"></i>
                        </div>
                        <div class="card-info">
                            <span class="card-value">${completedSurveys}/${surveys.length}</span>
                            <span class="card-label">Surveys Completed</span>
                        </div>
                    </div>
                    
                    <div class="overview-card">
                        <div class="card-icon" style="background: #e74c3c;">
                            <i class="fas fa-file-alt"></i>
                        </div>
                        <div class="card-info">
                            <span class="card-value">${completedExams}/${exams.length}</span>
                            <span class="card-label">Exams Completed</span>
                        </div>
                    </div>
                    
                    <div class="overview-card">
                        <div class="card-icon" style="background: ${certificate.status === 'approved' ? '#27ae60' : '#95a5a6'};">
                            <i class="fas fa-certificate"></i>
                        </div>
                        <div class="card-info">
                            <span class="card-value">${this.formatCertificateStatus(certificate.status)}</span>
                            <span class="card-label">Certificate Status</span>
                        </div>
                    </div>
                </div>

                ${cls.meet_link || cls.zoom_link ? `
                    <div class="meeting-links">
                        <h4><i class="fas fa-video"></i> Class Meeting Links</h4>
                        ${cls.meet_link ? `<a href="${cls.meet_link}" target="_blank" class="meeting-link" data-testid="link-meet"><i class="fab fa-google"></i> Google Meet</a>` : ''}
                        ${cls.zoom_link ? `<a href="${cls.zoom_link}" target="_blank" class="meeting-link" data-testid="link-zoom"><i class="fas fa-video"></i> Zoom</a>` : ''}
                    </div>
                ` : ''}

                <div class="quick-actions">
                    <h4>Quick Actions</h4>
                    <div class="actions-grid">
                        ${surveys.filter(s => !s.is_completed).length > 0 ? 
                            `<button class="action-btn" onclick="window.studentClassDashboard.switchTab('surveys')" data-testid="action-pending-surveys">
                                <i class="fas fa-clipboard-list"></i> Complete Pending Surveys (${surveys.filter(s => !s.is_completed).length})
                            </button>` : ''}
                        ${exams.filter(e => e.can_take && !e.best_result?.passed).length > 0 ? 
                            `<button class="action-btn" onclick="window.studentClassDashboard.switchTab('exams')" data-testid="action-pending-exams">
                                <i class="fas fa-file-alt"></i> Take Pending Exams (${exams.filter(e => e.can_take && !e.best_result?.passed).length})
                            </button>` : ''}
                        <button class="action-btn" onclick="window.studentClassDashboard.switchTab('materials')" data-testid="action-materials">
                            <i class="fas fa-book"></i> Continue Learning
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    renderMaterialsTab() {
        const materials = this.currentClass.materials;
        const weeks = materials.weeks || [];

        if (weeks.length === 0) {
            return `
                <div class="empty-state" data-testid="empty-materials">
                    <i class="fas fa-book-open"></i>
                    <p>No materials available yet.</p>
                </div>
            `;
        }

        return `
            <div class="materials-tab" data-testid="materials-content">
                ${weeks.map(week => `
                    <div class="week-section" data-testid="week-${week.week_number}">
                        <div class="week-header">
                            <h4><i class="fas fa-calendar-week"></i> Week ${week.week_number}: ${week.title}</h4>
                            <span class="week-progress">${week.materials.filter(m => m.is_completed).length}/${week.materials.length} completed</span>
                        </div>
                        <div class="materials-list">
                            ${week.materials.map(mat => `
                                <div class="material-item ${mat.is_completed ? 'completed' : ''}" data-testid="material-${mat.id}">
                                    <div class="material-icon">
                                        ${this.getMaterialIcon(mat.material_type)}
                                    </div>
                                    <div class="material-info">
                                        <span class="material-title">${mat.title}</span>
                                        ${mat.duration_minutes ? `<span class="material-duration">${mat.duration_minutes} min</span>` : ''}
                                    </div>
                                    <div class="material-status">
                                        ${mat.is_completed ? 
                                            '<i class="fas fa-check-circle" style="color: #27ae60;"></i>' : 
                                            `<span class="progress-text">${Math.round(mat.progress_percent || 0)}%</span>`}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    getMaterialIcon(type) {
        const icons = {
            'video': '<i class="fas fa-play-circle" style="color: #e74c3c;"></i>',
            'document': '<i class="fas fa-file-alt" style="color: #3498db;"></i>',
            'pdf': '<i class="fas fa-file-pdf" style="color: #e74c3c;"></i>',
            'link': '<i class="fas fa-external-link-alt" style="color: #9b59b6;"></i>',
            'quiz': '<i class="fas fa-question-circle" style="color: #f39c12;"></i>'
        };
        return icons[type] || '<i class="fas fa-file" style="color: #95a5a6;"></i>';
    }

    renderSurveysTab() {
        const surveys = this.currentClass.surveys || [];

        if (surveys.length === 0) {
            return `
                <div class="empty-state" data-testid="empty-surveys">
                    <i class="fas fa-clipboard-list"></i>
                    <p>No surveys available for this class.</p>
                </div>
            `;
        }

        return `
            <div class="surveys-tab" data-testid="surveys-content">
                ${surveys.map(survey => `
                    <div class="survey-card ${survey.is_completed ? 'completed' : ''}" data-testid="survey-${survey.id}">
                        <div class="survey-info">
                            <h4>${survey.title}</h4>
                            <p>${survey.description || ''}</p>
                            <div class="survey-meta">
                                <span><i class="fas fa-question-circle"></i> ${survey.questions_count} questions</span>
                                <span class="survey-type">${this.formatSurveyType(survey.survey_type)}</span>
                                ${survey.is_required ? '<span class="required-badge">Required</span>' : ''}
                            </div>
                        </div>
                        <div class="survey-action">
                            ${survey.is_completed ? 
                                `<span class="completed-badge" data-testid="survey-completed-${survey.id}">
                                    <i class="fas fa-check-circle"></i> Completed
                                </span>` :
                                `<button class="btn-primary" onclick="window.studentClassDashboard.openSurvey('${survey.id}')" data-testid="button-take-survey-${survey.id}">
                                    <i class="fas fa-pencil-alt"></i> Take Survey
                                </button>`}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    formatSurveyType(type) {
        const types = {
            'entry_survey': 'Entry Survey',
            'training_feedback': 'Training Feedback',
            'exit_survey': 'Exit Survey',
            'general': 'General Survey'
        };
        return types[type] || type;
    }

    renderExamsTab() {
        const exams = this.currentClass.exams || [];

        if (exams.length === 0) {
            return `
                <div class="empty-state" data-testid="empty-exams">
                    <i class="fas fa-file-alt"></i>
                    <p>No exams available for this class.</p>
                </div>
            `;
        }

        const isAr = window.i18n && window.i18n.getCurrentLanguage() === 'ar';
        
        return `
            <div class="exams-tab" data-testid="exams-content">
                ${exams.map(exam => {
                    const examTitle = isAr && exam.title_ar ? exam.title_ar : exam.title;
                    const examDesc = isAr && exam.description_ar ? exam.description_ar : (exam.description || '');
                    return `
                    <div class="exam-card" data-testid="exam-${exam.id}">
                        <div class="exam-info">
                            <h4>${examTitle}</h4>
                            <p>${examDesc}</p>
                            <div class="exam-meta">
                                <span><i class="fas fa-question-circle"></i> ${exam.questions_count} questions</span>
                                ${exam.time_limit_minutes ? `<span><i class="fas fa-clock"></i> ${exam.time_limit_minutes} min</span>` : ''}
                                <span><i class="fas fa-redo"></i> ${exam.attempts_used}/${exam.max_attempts || '∞'} attempts</span>
                                <span><i class="fas fa-percent"></i> Pass: ${exam.passing_threshold}%</span>
                            </div>
                        </div>
                        
                        ${exam.best_result ? `
                            <div class="exam-result ${exam.best_result.passed ? 'passed' : 'failed'}">
                                <span class="result-score">${Math.round(exam.best_result.percentage)}%</span>
                                <span class="result-status">${exam.best_result.passed ? 'Passed' : 'Failed'}</span>
                            </div>
                        ` : ''}
                        
                        <div class="exam-action">
                            ${exam.can_take ? 
                                `<button class="btn-primary" onclick="window.studentClassDashboard.startExam('${exam.id}')" data-testid="button-take-exam-${exam.id}">
                                    <i class="fas fa-play"></i> ${exam.attempts_used > 0 ? 'Retake Exam' : 'Start Exam'}
                                </button>` :
                                `<span class="attempts-exhausted" data-testid="exam-no-attempts-${exam.id}">
                                    <i class="fas fa-ban"></i> No attempts remaining
                                </span>`}
                        </div>
                    </div>
                `;}).join('')}
            </div>
        `;
    }

    renderCertificateTab() {
        const certificate = this.currentClass.certificate;
        const cls = this.currentClass.class;
        const classId = this.currentClass.class.id;

        return `
            <div class="certificate-tab" data-testid="certificate-content">
                <div class="certificate-status-card">
                    <div class="certificate-icon ${certificate.status === 'approved' || certificate.status === 'force_issued' ? 'approved' : ''}">
                        <i class="fas fa-certificate"></i>
                    </div>
                    <h3>${this.formatCertificateStatus(certificate.status)}</h3>
                    <p>${this.getCertificateMessage(certificate)}</p>
                    
                    ${(certificate.is_issued || certificate.status === 'approved' || certificate.status === 'force_issued') ? 
                        `<a href="/api/student/class/${classId}/certificate/download" class="btn-success" target="_blank" download data-testid="button-download-certificate">
                            <i class="fas fa-download"></i> Download Certificate
                        </a>` : ''}
                </div>

                <div class="certificate-requirements">
                    <h4>Certificate Requirements</h4>
                    <ul class="requirements-list">
                        <li class="${certificate.progress_percent >= 80 ? 'completed' : ''}">
                            <i class="fas ${certificate.progress_percent >= 80 ? 'fa-check-circle' : 'fa-circle'}"></i>
                            Complete at least 80% of course materials (Currently: ${Math.round(certificate.progress_percent || 0)}%)
                        </li>
                        <li class="${certificate.requirements?.all_exams_passed ? 'completed' : ''}">
                            <i class="fas ${certificate.requirements?.all_exams_passed ? 'fa-check-circle' : 'fa-circle'}"></i>
                            Pass all required exams
                        </li>
                        ${cls.certificate_enabled ? '' : 
                            `<li class="warning">
                                <i class="fas fa-exclamation-triangle"></i>
                                Certificate is not enabled for this course
                            </li>`}
                    </ul>
                </div>

                ${certificate.exam_results && certificate.exam_results.length > 0 ? `
                    <div class="exam-results-summary">
                        <h4>Exam Results</h4>
                        <div class="results-list">
                            ${certificate.exam_results.map(result => `
                                <div class="result-item ${result.passed ? 'passed' : 'failed'}">
                                    <span class="exam-title">${result.exam_title}</span>
                                    <span class="exam-score">${Math.round(result.percentage || 0)}%</span>
                                    <i class="fas ${result.passed ? 'fa-check-circle' : 'fa-times-circle'}"></i>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }

    formatCertificateStatus(status) {
        const statuses = {
            'not_started': 'Not Started',
            'pending': 'Pending Approval',
            'approved': 'Certificate Approved',
            'force_issued': 'Certificate Issued',
            'not_eligible': 'Not Eligible'
        };
        return statuses[status] || status;
    }

    getCertificateMessage(certificate) {
        switch (certificate.status) {
            case 'approved':
            case 'force_issued':
                return 'Congratulations! Your certificate has been approved and is ready for download.';
            case 'pending':
                return 'Your certificate request is pending approval. Please wait for the instructor/admin to review.';
            case 'not_eligible':
                return 'You are not yet eligible for a certificate. Please complete the requirements below.';
            default:
                return 'Complete the course requirements to become eligible for a certificate.';
        }
    }

    async openSurvey(surveyId) {
        const survey = this.currentClass.surveys.find(s => s.id === surveyId);
        if (!survey) return;

        if (survey.is_completed) {
            alert('You have already completed this survey.');
            return;
        }

        try {
            const classId = this.currentClass.class.id;
            const response = await fetch(`/api/student/class/${classId}/surveys`, {
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error('Failed to load survey questions');
            }

            const data = await response.json();
            const fullSurvey = data.surveys.find(s => s.id === surveyId);
            
            if (!fullSurvey || !fullSurvey.questions || fullSurvey.questions.length === 0) {
                alert('No questions available for this survey.');
                return;
            }

            this.showSurveyModal(fullSurvey);
        } catch (error) {
            console.error('Error loading survey:', error);
            alert(error.message);
        }
    }

    showSurveyModal(survey) {
        const modal = document.createElement('div');
        modal.className = 'exam-modal-overlay';
        modal.id = 'surveyModal';
        modal.dataset.testid = 'survey-modal';

        modal.innerHTML = `
            <div class="exam-modal">
                <div class="exam-modal-header">
                    <h3>${survey.title}</h3>
                    <span class="survey-type-badge">${survey.survey_type || 'Survey'}</span>
                </div>
                
                ${survey.description ? `<p class="survey-description">${survey.description}</p>` : ''}
                
                <div class="exam-questions" id="surveyQuestions">
                    ${survey.questions.map((q, idx) => this.renderSurveyQuestion(q, idx, survey.questions.length)).join('')}
                </div>
                
                <div class="exam-modal-footer">
                    <button class="btn-secondary" onclick="window.studentClassDashboard.closeSurveyModal()" data-testid="button-cancel-survey">
                        Cancel
                    </button>
                    <button class="btn-primary" onclick="window.studentClassDashboard.submitSurvey('${survey.id}')" data-testid="button-submit-survey">
                        <i class="fas fa-paper-plane"></i> Submit Survey
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    }

    renderSurveyQuestion(question, index, total) {
        let inputHtml = '';
        
        switch (question.question_type) {
            case 'true_false':
                const isArabicTF = window.i18n && window.i18n.getCurrentLanguage() === 'ar';
                const tfOptions = isArabicTF 
                    ? [{ label: 'صحيح', value: 'True' }, { label: 'خطأ', value: 'False' }]
                    : [{ label: 'True', value: 'True' }, { label: 'False', value: 'False' }];
                inputHtml = `
                    <div class="question-options">
                        ${tfOptions.map((opt, optIdx) => `
                            <label class="option-label" data-testid="option-${question.id}-${optIdx}">
                                <input type="radio" 
                                       name="question_${question.id}" 
                                       value="${opt.value}">
                                <span>${opt.label}</span>
                            </label>
                        `).join('')}
                    </div>
                `;
                break;
            case 'multiple_choice':
            case 'single_choice':
                const isArabic = window.i18n && window.i18n.getCurrentLanguage() === 'ar';
                const optionsToShow = isArabic && question.options_ar && question.options_ar.length > 0 
                    ? question.options_ar 
                    : (question.options || []);
                inputHtml = `
                    <div class="question-options">
                        ${optionsToShow.map((opt, optIdx) => `
                            <label class="option-label" data-testid="option-${question.id}-${optIdx}">
                                <input type="${question.question_type === 'multiple_choice' ? 'checkbox' : 'radio'}" 
                                       name="question_${question.id}" 
                                       value="${question.options ? question.options[optIdx] : opt}">
                                <span>${opt}</span>
                            </label>
                        `).join('')}
                    </div>
                `;
                break;
            case 'rating':
            case 'likert':
                const isArabicRating = window.i18n && window.i18n.getCurrentLanguage() === 'ar';
                const ratingOptions = isArabicRating && question.options_ar && question.options_ar.length > 0 
                    ? question.options_ar 
                    : (question.options || ['1 - Poor', '2 - Fair', '3 - Good', '4 - Very Good', '5 - Excellent']);
                inputHtml = `
                    <div class="rating-scale-options">
                        ${ratingOptions.map((opt, idx) => `
                            <label class="rating-scale-label" data-testid="rating-${question.id}-${idx + 1}">
                                <input type="radio" name="question_${question.id}" value="${idx + 1}">
                                <span class="rating-option-text">${opt}</span>
                            </label>
                        `).join('')}
                    </div>
                `;
                break;
            case 'text':
            case 'long_text':
            default:
                inputHtml = `
                    <textarea name="question_${question.id}" 
                              placeholder="Enter your response..." 
                              class="survey-textarea"
                              data-testid="textarea-${question.id}"
                              rows="${question.question_type === 'long_text' ? 4 : 2}"></textarea>
                `;
                break;
        }

        const isArabicLang = window.i18n && window.i18n.getCurrentLanguage() === 'ar';
        const questionText = isArabicLang && question.question_text_ar 
            ? question.question_text_ar 
            : question.question_text;

        return `
            <div class="exam-question" data-question-id="${question.id}" data-testid="survey-question-${index + 1}">
                <h4>Question ${index + 1} of ${total} ${question.is_required ? '<span class="required">*</span>' : ''}</h4>
                <p class="question-text">${questionText}</p>
                ${inputHtml}
            </div>
        `;
    }

    closeSurveyModal() {
        const modal = document.getElementById('surveyModal');
        if (modal) {
            modal.remove();
        }
    }

    async submitSurvey(surveyId) {
        const answers = {};
        const questions = document.querySelectorAll('#surveyQuestions .exam-question');
        
        questions.forEach(qEl => {
            const questionId = qEl.dataset.questionId;
            const checkboxes = qEl.querySelectorAll('input[type="checkbox"]:checked');
            const radio = qEl.querySelector('input[type="radio"]:checked');
            const textarea = qEl.querySelector('textarea');
            
            if (checkboxes.length > 0) {
                answers[questionId] = Array.from(checkboxes).map(cb => cb.value);
            } else if (radio) {
                answers[questionId] = radio.value;
            } else if (textarea) {
                answers[questionId] = textarea.value;
            }
        });

        try {
            const classId = this.currentClass.class.id;
            const response = await fetch(`/api/student/class/${classId}/surveys/${surveyId}/submit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ answers })
            });

            const data = await this._safeJson(response, 'Could not save your survey response. Please check your connection and try again.');

            if (!response.ok || (data && data.success === false)) {
                throw new Error((data && data.error) || `Failed to submit survey (status ${response.status})`);
            }

            // Show score if available
            if (data && data.score) {
                alert(`Survey Submitted!\n\nScore: ${data.score.correct}/${data.score.total}\nPercentage: ${data.score.percentage}%`);
            } else {
                alert('Survey submitted successfully!');
            }
            this.closeSurveyModal();

            // Refresh the class dashboard to update completion status
            await this.openClass(classId);
        } catch (error) {
            console.error('Error submitting survey:', error);
            alert(error.message || 'Failed to submit survey');
        }
    }

    async startExam(examId) {
        const exam = this.currentClass.exams.find(e => e.id === examId);
        if (!exam) return;

        const isAr = window.i18n && window.i18n.getCurrentLanguage() === 'ar';
        const examTitle = isAr && exam.title_ar ? exam.title_ar : exam.title;
        if (!confirm(`Are you ready to start "${examTitle}"?\n\nTime limit: ${exam.time_limit_minutes || 'No limit'} minutes\nQuestions: ${exam.questions_count}\nPassing score: ${exam.passing_threshold}%`)) {
            return;
        }

        try {
            const classId = this.currentClass.class.id;
            const response = await fetch(`/api/student/class/${classId}/exams/${examId}/start`, {
                method: 'POST',
                credentials: 'include'
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Failed to start exam');
            }

            const data = await response.json();
            this.showExamModal(data);
        } catch (error) {
            console.error('Error starting exam:', error);
            alert(error.message);
        }
    }

    showExamModal(examData) {
        const modal = document.createElement('div');
        modal.className = 'exam-modal-overlay';
        modal.id = 'examModal';
        modal.dataset.testid = 'exam-modal';
        
        const questions = examData.questions || [];
        const exam = examData.exam;
        const isAr = window.i18n && window.i18n.getCurrentLanguage() === 'ar';
        const examTitle = isAr && exam.title_ar ? exam.title_ar : exam.title;

        modal.innerHTML = `
            <div class="exam-modal">
                <div class="exam-modal-header">
                    <h3>${examTitle}</h3>
                    <div class="exam-timer" id="examTimer" data-testid="exam-timer">
                        ${exam.time_limit_minutes ? `<i class="fas fa-clock"></i> <span id="timerDisplay">${exam.time_limit_minutes}:00</span>` : ''}
                    </div>
                </div>
                
                <div class="exam-questions" id="examQuestions">
                    ${questions.map((q, idx) => {
                        const isAr = window.i18n && window.i18n.getCurrentLanguage() === 'ar';
                        const qText = isAr && q.question_text_ar ? q.question_text_ar : q.question_text;
                        let opts = isAr && q.options_ar && q.options_ar.length > 0 ? q.options_ar : (q.options || []);
                        // Handle true/false questions - provide default options if empty
                        if (q.question_type === 'true_false' && (!opts || opts.length === 0)) {
                            opts = isAr ? ['صحيح', 'خطأ'] : ['True', 'False'];
                        }
                        return `
                        <div class="exam-question" data-question-id="${q.id}" data-question-type="${q.question_type || 'multiple_choice'}" data-testid="question-${idx + 1}">
                            <h4>Question ${idx + 1} of ${questions.length}</h4>
                            <p class="question-text">${qText}</p>
                            <div class="question-options">
                                ${opts.map((opt, optIdx) => `
                                    <label class="option-label" data-testid="option-${q.id}-${optIdx}">
                                        <input type="radio" name="question_${q.id}" value="${q.question_type === 'true_false' ? (optIdx === 0 ? 'True' : 'False') : optIdx}">
                                        <span>${opt}</span>
                                    </label>
                                `).join('')}
                            </div>
                        </div>
                    `;}).join('')}
                </div>
                
                <div class="exam-modal-footer">
                    <button class="btn-secondary" onclick="window.studentClassDashboard.closeExamModal()" data-testid="button-cancel-exam">
                        Cancel
                    </button>
                    <button class="btn-primary" onclick="window.studentClassDashboard.submitExam('${exam.id}', '${examData.started_at}')" data-testid="button-submit-exam">
                        <i class="fas fa-paper-plane"></i> Submit Exam
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        this._activeExamId = exam.id;
        this._activeExamStartedAt = examData.started_at;
        this.startExamProctoring();

        if (exam.time_limit_minutes) {
            this.startExamTimer(exam.time_limit_minutes, exam.id, examData.started_at);
        }
    }

    // ---- Anti-cheating: record browser signals + warn the student ----
    startExamProctoring() {
        // Idempotent: never double-attach listeners
        this.stopExamProctoring();
        this.proctoringEvents = [];
        this._lastBlurAt = 0;
        this.violationCount = 0;
        const VIOLATION_LIMIT = 3;
        const record = (type, detail = '') => {
            if (this.proctoringEvents.length < 200) {
                this.proctoringEvents.push({ type, at: new Date().toISOString(), detail });
            }
            const isViolation = type !== 'tab_focus' && type !== 'contextmenu_blocked';
            if (isViolation) {
                this.violationCount++;
                if (this.violationCount >= VIOLATION_LIMIT) {
                    // Stop proctoring so no further events trigger this path
                    this.stopExamProctoring();
                    const banner = document.getElementById('proctorWarningBanner');
                    if (banner) banner.style.display = 'none';
                    const isAr = window.i18n && window.i18n.getCurrentLanguage() === 'ar';
                    alert(isAr
                        ? `⚠️ وصلت إلى ${VIOLATION_LIMIT} مخالفات. سيتم إرسال اختبارك تلقائياً بإجاباتك الحالية.`
                        : `⚠️ You have reached ${VIOLATION_LIMIT} violations. Your exam is being submitted automatically with your current answers.`);
                    this.submitExam(this._activeExamId, this._activeExamStartedAt, true);
                    return;
                }
                this.showProctoringWarning(type, this.violationCount, VIOLATION_LIMIT);
            }
        };
        // window.blur and visibilitychange often both fire for one tab switch —
        // coalesce them into a single tab_blur within a 2-second window.
        const recordBlur = (detail) => {
            const now = Date.now();
            if (now - this._lastBlurAt < 2000) return;
            this._lastBlurAt = now;
            record('tab_blur', detail);
        };

        this._proctorHandlers = {
            blur: () => recordBlur('Left the exam window'),
            focus: () => { if (this.proctoringEvents.length < 200) this.proctoringEvents.push({ type: 'tab_focus', at: new Date().toISOString(), detail: '' }); },
            visibilitychange: () => { if (document.hidden) recordBlur('Tab hidden'); },
            fullscreenchange: () => {
                // Only a violation when *leaving* fullscreen mid-exam
                if (!document.fullscreenElement && document.getElementById('examModal')) {
                    record('fullscreen_exit', 'Exited fullscreen');
                }
            },
            beforeunload: (e) => {
                record('navigation_attempt', 'Tried to leave the exam page');
                e.preventDefault();
                e.returnValue = '';
            },
            copy: (e) => { record('copy_detected', 'Copy attempt'); e.preventDefault(); },
            paste: (e) => { record('paste_detected', 'Paste attempt'); e.preventDefault(); },
            contextmenu: (e) => {
                const modal = document.getElementById('examModal');
                if (modal && modal.contains(e.target)) {
                    e.preventDefault();
                    if (this.proctoringEvents.length < 200) this.proctoringEvents.push({ type: 'contextmenu_blocked', at: new Date().toISOString(), detail: '' });
                }
            },
        };
        window.addEventListener('blur', this._proctorHandlers.blur);
        window.addEventListener('focus', this._proctorHandlers.focus);
        window.addEventListener('beforeunload', this._proctorHandlers.beforeunload);
        document.addEventListener('visibilitychange', this._proctorHandlers.visibilitychange);
        document.addEventListener('fullscreenchange', this._proctorHandlers.fullscreenchange);
        document.addEventListener('copy', this._proctorHandlers.copy);
        document.addEventListener('paste', this._proctorHandlers.paste);
        document.addEventListener('contextmenu', this._proctorHandlers.contextmenu);

        // Disable text selection inside the exam questions
        const q = document.getElementById('examQuestions');
        if (q) { q.style.userSelect = 'none'; q.style.webkitUserSelect = 'none'; }
    }

    stopExamProctoring() {
        clearTimeout(this._proctorWarnTimer);
        if (!this._proctorHandlers) return;
        window.removeEventListener('blur', this._proctorHandlers.blur);
        window.removeEventListener('focus', this._proctorHandlers.focus);
        window.removeEventListener('beforeunload', this._proctorHandlers.beforeunload);
        document.removeEventListener('visibilitychange', this._proctorHandlers.visibilitychange);
        document.removeEventListener('fullscreenchange', this._proctorHandlers.fullscreenchange);
        document.removeEventListener('copy', this._proctorHandlers.copy);
        document.removeEventListener('paste', this._proctorHandlers.paste);
        document.removeEventListener('contextmenu', this._proctorHandlers.contextmenu);
        this._proctorHandlers = null;
    }

    showProctoringWarning(type, count, limit) {
        const isAr = window.i18n && window.i18n.getCurrentLanguage() === 'ar';
        const messages = {
            tab_blur: isAr ? 'مغادرة نافذة الاختبار' : 'Leaving the exam window',
            copy_detected: isAr ? 'محاولة نسخ' : 'Copy attempt',
            paste_detected: isAr ? 'محاولة لصق' : 'Paste attempt',
            fullscreen_exit: isAr ? 'الخروج من وضع ملء الشاشة' : 'Exiting fullscreen',
            navigation_attempt: isAr ? 'محاولة مغادرة الصفحة' : 'Attempt to leave the page',
        };
        const action = messages[type] || (isAr ? 'نشاط مشبوه' : 'Suspicious activity');
        const remaining = (limit && count) ? limit - count : null;
        let msg;
        if (remaining !== null) {
            msg = isAr
                ? `⚠️ تحذير ${count}/${limit}: ${action}. تبقى لك ${remaining} تحذير(ات) قبل الإرسال التلقائي.`
                : `⚠️ Warning ${count}/${limit}: ${action}. ${remaining} warning(s) left before auto-submit.`;
        } else {
            msg = `⚠️ ${action}`;
        }

        let el = document.getElementById('proctorWarningBanner');
        if (!el) {
            el = document.createElement('div');
            el.id = 'proctorWarningBanner';
            el.setAttribute('data-testid', 'banner-proctor-warning');
            el.style.cssText = 'position:fixed;top:12px;left:50%;transform:translateX(-50%);z-index:99999;'
                + 'background:#c62828;color:#fff;padding:12px 24px;border-radius:8px;font-weight:600;'
                + 'box-shadow:0 4px 14px rgba(0,0,0,.35);max-width:90vw;text-align:center;font-size:1rem;';
            document.body.appendChild(el);
        }
        el.textContent = msg;
        el.style.display = 'block';
        clearTimeout(this._proctorWarnTimer);
        this._proctorWarnTimer = setTimeout(() => { el.style.display = 'none'; }, 6000);
    }

    startExamTimer(minutes, examId, startedAt) {
        let timeLeft = minutes * 60;
        const timerDisplay = document.getElementById('timerDisplay');
        
        this.examTimer = setInterval(() => {
            timeLeft--;
            const mins = Math.floor(timeLeft / 60);
            const secs = timeLeft % 60;
            timerDisplay.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
            
            if (timeLeft <= 0) {
                clearInterval(this.examTimer);
                alert('Time is up! Your exam will be submitted automatically.');
                this.submitExam(examId, startedAt);
            }
        }, 1000);
    }

    async submitExam(examId, startedAt, forceSubmit = false) {
        const answers = {};
        // Collect every kind of answer the exam UI may render, not just radios.
        document.querySelectorAll('#examQuestions .exam-question').forEach(q => {
            const questionId = q.dataset.questionId;
            if (!questionId) return;
            const radio = q.querySelector('input[type="radio"]:checked');
            const checkboxes = q.querySelectorAll('input[type="checkbox"]:checked');
            const textarea = q.querySelector('textarea');
            const textInput = q.querySelector('input[type="text"]');
            if (radio) {
                answers[questionId] = radio.value;
            } else if (checkboxes.length > 0) {
                answers[questionId] = Array.from(checkboxes).map(cb => cb.value);
            } else if (textarea && textarea.value.trim()) {
                answers[questionId] = textarea.value.trim();
            } else if (textInput && textInput.value.trim()) {
                answers[questionId] = textInput.value.trim();
            }
        });

        try {
            const classId = this.currentClass.class.id;
            const response = await fetch(`/api/student/class/${classId}/exams/${examId}/submit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    answers,
                    started_at: startedAt,
                    time_spent_seconds: Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000),
                    proctoring_events: this.proctoringEvents || [],
                    force_submitted: forceSubmit
                })
            });

            const data = await this._safeJson(response, 'Could not save your exam answers. Please check your connection and try again.');

            if (this.examTimer) {
                clearInterval(this.examTimer);
            }

            this.closeExamModal();

            if (response.ok && data && data.success !== false) {
                const r = data.result || {};
                const isAr = window.i18n && window.i18n.getCurrentLanguage() === 'ar';
                const violationNote = forceSubmit
                    ? (isAr ? `\n⚠️ تم الإرسال تلقائياً بسبب 3 مخالفات (مخالفات: ${this.violationCount ?? 3})` : `\n⚠️ Auto-submitted due to 3 violations (violations: ${this.violationCount ?? 3})`)
                    : '';
                alert(`${isAr ? 'تم إرسال الاختبار!' : 'Exam Submitted!'}\n\n${isAr ? 'الدرجة' : 'Score'}: ${r.score ?? 0}/${r.total_points ?? 0}\n${isAr ? 'النسبة' : 'Percentage'}: ${r.percentage ?? 0}%\n${isAr ? 'النتيجة' : 'Result'}: ${r.passed ? (isAr ? 'ناجح ✓' : 'PASSED ✓') : (isAr ? 'راسب ✗' : 'FAILED ✗')}${violationNote}`);
                await this.openClass(classId);
            } else {
                throw new Error((data && data.error) || `Failed to submit exam (status ${response.status})`);
            }
        } catch (error) {
            console.error('Error submitting exam:', error);
            alert(error.message || 'Failed to submit exam');
        }
    }

    /**
     * Read a fetch Response as JSON without throwing the cryptic
     * "Unexpected token < in JSON at position 0" error when the
     * server happens to return an HTML error page (e.g. a 500 from
     * production with debug=False, a proxy timeout, or a session
     * expiry redirect). Always returns a plain object.
     */
    async _safeJson(response, fallbackMessage) {
        let text = '';
        try { text = await response.text(); } catch (_) { text = ''; }
        if (!text) {
            return { success: response.ok, error: response.ok ? null : (fallbackMessage || `HTTP ${response.status}`) };
        }
        try {
            return JSON.parse(text);
        } catch (_) {
            // Server returned HTML / plain text (likely an error page).
            return {
                success: false,
                error: response.ok
                    ? (fallbackMessage || 'Server returned an unexpected response.')
                    : (fallbackMessage || `Server error (status ${response.status}). Please try again.`)
            };
        }
    }

    closeExamModal() {
        const modal = document.getElementById('examModal');
        if (modal) {
            modal.remove();
        }
        if (this.examTimer) {
            clearInterval(this.examTimer);
        }
        this.stopExamProctoring();
        const banner = document.getElementById('proctorWarningBanner');
        if (banner) banner.remove();
    }

    showClassList() {
        this.currentClass = null;
        this.renderClassList();
    }

    showError(message) {
        const container = document.getElementById('studentClassesContainer');
        if (container) {
            container.innerHTML = `
                <div class="error-state" data-testid="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>${message}</p>
                    <button class="btn-primary" onclick="window.studentClassDashboard.loadClasses()">
                        <i class="fas fa-redo"></i> Try Again
                    </button>
                </div>
            `;
        }
    }
}

window.studentClassDashboard = new StudentClassDashboard();
