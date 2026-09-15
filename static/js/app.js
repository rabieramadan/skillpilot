// SkillPilot - Advanced JavaScript Application

class SkillPilot {
    constructor() {
        this.currentSession = null;
        this.selectedModel = null;
        this.selectedVersion = null;
        this.conversationMessages = [];
        this.conversationMemory = []; // Track last 60 messages (30 exchanges) per session for follow-up context
        this.chatSessions = []; // Stored chat sessions (Claude-style history)
        this.currentSessionId = null;
        this.totalCost = 0;
        this.totalTokens = 0;
        this.modelsConfig = {};
        this.isAdmin = false;
        this.userRole = null;
        this.userId = null;
        this.presentmateSession = null; // PresentMate conversation session
        this.presentmateInstructionsShown = false; // Track if instructions were shown
        this.navigationHistory = []; // Track navigation history for back button
        this.currentTab = null; // Track current active tab
        
        this.init();
    }

    async init() {
        await this.checkAdminStatus();
        await this.checkUserRole();
        await this.loadModels();
        await this.loadPromptLibrary();
        this.setupEventListeners();
        this.setupTabNavigation();
        this.updateAdminUI();
        this.updateRoleUI();
        
        // Initialize courses manager for role-based UI
        if (window.coursesManager && this.userRole === 'Student') {
            await window.coursesManager.init();
        }
        
        // Preload questions for faster tab switching
        this.preloadQuestions();
    }
    
    async preloadQuestions() {
        // Preload all question sets in background for instant tab switching
        try {
            // Preload entry survey questions
            if (!this.surveyQuestions || this.surveyQuestions.length === 0) {
                const surveyData = await this.loadSurveyQuestions();
                if (surveyData && surveyData.questions) {
                    this.surveyQuestions = surveyData.questions;
                }
            }
            
            // Preload exit exam questions
            if (!this.exitExamQuestions || this.exitExamQuestions.length === 0) {
                const examData = await this.loadExitExamQuestions();
                if (examData && examData.questions) {
                    this.exitExamQuestions = examData.questions;
                }
            }
            
            // Preload training evaluation questions  
            if (!this.exitSurveyQuestions || this.exitSurveyQuestions.length === 0) {
                const response = await fetch('/api/survey/exit-survey/questions');
                const data = await response.json();
                if (data && data.questions) {
                    this.exitSurveyQuestions = data.questions;
                }
            }
        } catch (error) {
            console.log('Background question preload failed (non-critical):', error);
        }
    }

    async checkAdminStatus() {
        try {
            const response = await fetch('/api/auth/check', {
                credentials: 'include'
            });
            const data = await response.json();
            const role = (data.role || '').toLowerCase();
            // Super-admin role variants
            const SUPER_ADMIN_ROLES = ['super_admin', 'superadmin'];
            // Any-admin role variants (super admin counts as admin too)
            const ADMIN_ROLES = [
                'super_admin', 'superadmin',
                'admin', 'administrator',
                'institution_admin', 'institutionadmin',
                'org_admin', 'orgadmin'
            ];
            this.isSuperAdmin = SUPER_ADMIN_ROLES.includes(role) || false;
            // Trust either the explicit session flag OR a recognized admin role string,
            // so a stale/missing is_admin flag never hides the admin cards from a real admin.
            this.isAdmin = data.is_admin === true || ADMIN_ROLES.includes(role) || this.isSuperAdmin || false;
            this.userId = data.user_id || null;
        } catch (error) {
            console.error('Error checking admin status:', error);
            this.isAdmin = false;
            this.isSuperAdmin = false;
        }
    }

    async checkUserRole() {
        try {
            // First try to get role from /api/auth/check (includes database users)
            const authResponse = await fetch('/api/auth/check', {
                credentials: 'include'
            });
            if (authResponse.ok) {
                const authData = await authResponse.json();
                if (authData.role) {
                    this.userRole = authData.role;
                    this.hasApprovedEnrollment = authData.has_approved_enrollment || false;
                    return;
                }
            }
            
            // Fallback: Fetch user role from users endpoint (JSON file users)
            if (this.userId) {
                const response = await fetch('/api/auth/users');
                if (response.ok) {
                    const data = await response.json();
                    const currentUser = data.users.find(u => u.user_id === this.userId);
                    if (currentUser) {
                        this.userRole = currentUser.role;
                    }
                }
            }
        } catch (error) {
            console.error('Error checking user role:', error);
        }
    }

    updateAdminUI() {
        const adminOnlyElements = document.querySelectorAll('.admin-only');
        const superAdminOnlyElements = document.querySelectorAll('.super-admin-only');

        if (this.isAdmin || this.isSuperAdmin) {
            adminOnlyElements.forEach(el => {
                el.classList.add('role-visible');
            });
        } else {
            adminOnlyElements.forEach(el => {
                el.classList.remove('role-visible');
            });
        }

        if (this.isSuperAdmin) {
            superAdminOnlyElements.forEach(el => {
                el.classList.add('role-visible');
            });
        } else {
            superAdminOnlyElements.forEach(el => {
                el.classList.remove('role-visible');
            });
        }
    }

    updateRoleUI() {
        const studentOnlyElements = document.querySelectorAll('.student-only');
        const instructorOnlyElements = document.querySelectorAll('.instructor-only');
        const instructorOrAdminElements = document.querySelectorAll('.instructor-or-admin-only');
        const instructorOrSuperAdminElements = document.querySelectorAll('.instructor-or-super-admin-only');
        
        // Remove role-visible class from all role-specific elements
        studentOnlyElements.forEach(el => el.classList.remove('role-visible'));
        instructorOnlyElements.forEach(el => el.classList.remove('role-visible'));
        instructorOrAdminElements.forEach(el => el.classList.remove('role-visible'));
        instructorOrSuperAdminElements.forEach(el => el.classList.remove('role-visible'));
        
        // Normalize role to lowercase for comparison
        const normalizedRole = (this.userRole || '').toLowerCase();

        // The AI chat entry follows the admin switch for every role, so this
        // runs before the role branches -- the super admin one returns early.
        this.applyAiChatVisibility();

        // SUPER ADMIN CAN SEE EVERYTHING
        if (this.isSuperAdmin) {
            studentOnlyElements.forEach(el => el.classList.add('role-visible'));
            instructorOnlyElements.forEach(el => el.classList.add('role-visible'));
            instructorOrAdminElements.forEach(el => el.classList.add('role-visible'));
            instructorOrSuperAdminElements.forEach(el => el.classList.add('role-visible'));
            this.syncMenuGroupVisibility();
            return; // Super admin has full access, no need to check other conditions
        }
        
        // Show elements based on user role using CSS class
        if (normalizedRole === 'student') {
            studentOnlyElements.forEach(el => {
                el.classList.add('role-visible');
            });
            // Students are kept off the authoring-side AI tabs, but the chat
            // is the administrator's call: it is the default tab, so bouncing
            // them off it made the chat appear for a moment and then vanish,
            // with no menu entry to get back to it.
            const staffOnlyTabs = ['ai-tools-suite', 'library', 'agentic-ai-lab'];
            if (!this.aiChatEnabled()) {
                staffOnlyTabs.push('chat');
            }
            const activeBtn = document.querySelector('.menu-item.active');
            const activeTab = activeBtn ? activeBtn.getAttribute('data-tab') : null;
            if (!activeTab || staffOnlyTabs.includes(activeTab)) {
                setTimeout(() => { this.showTab('my-classes'); }, 0);
            }
        } else if (normalizedRole === 'instructor' || normalizedRole === 'teacher') {
            instructorOnlyElements.forEach(el => {
                el.classList.add('role-visible');
            });
            // Instructors/Teachers can also see instructor-or-admin elements
            instructorOrAdminElements.forEach(el => {
                el.classList.add('role-visible');
            });
            // Instructors/Teachers can also see instructor-or-super-admin elements
            instructorOrSuperAdminElements.forEach(el => {
                el.classList.add('role-visible');
            });
        }
        
        // Admin can see instructor-or-admin elements too
        if (this.isAdmin) {
            instructorOrAdminElements.forEach(el => {
                el.classList.add('role-visible');
            });
        }

        // A group with nothing visible left in it should not be on the bar.
        this.syncMenuGroupVisibility();

        // Chat gating for students without an approved enrollment
        this.updateChatGating();
    }

    /** Show a menu group when anything inside it is visible, hide it when
     *  nothing is.
     *
     *  Groups carry their own role class, so the "Artificial Intelligence"
     *  group stayed hidden for students and took the AI chat entry with it,
     *  however the admin switch was set. The items inside keep their own
     *  rules -- a student sees the group only because the chat entry is in
     *  it, not the authoring tools beside it.
     */
    syncMenuGroupVisibility() {
        document.querySelectorAll('.top-cards-menu .menu-group').forEach(group => {
            const items = [...group.querySelectorAll('.menu-item')];
            const anyVisible = items.some(item => {
                const restricted = [...item.classList].some(
                    name => name.endsWith('-only') || name === 'ai-chat-item');
                return restricted ? item.classList.contains('role-visible') : true;
            });
            group.classList.toggle('role-visible', anyVisible);
        });
    }

    /** Has an administrator switched the AI chat on? Defaults to on, which
     *  is what the server reports when the setting has never been touched. */
    aiChatEnabled() {
        return window.SKP_AI_CHAT_ENABLED !== false;
    }

    /** Show or hide the AI chat menu entry to match the admin switch.
     *
     *  The entry used to be marked instructor-or-admin-only, so a student
     *  had no way to reach the chat however the switch was set, and the tab
     *  they landed on by default was taken away from them a moment later.
     */
    applyAiChatVisibility() {
        const enabled = this.aiChatEnabled();
        document.querySelectorAll('.ai-chat-item').forEach(el => {
            el.classList.toggle('role-visible', enabled);
        });

        // Nobody should be sitting on the chat tab once it is switched off.
        if (!enabled) {
            const active = document.querySelector('.menu-item.active');
            if (active && active.getAttribute('data-tab') === 'chat') {
                const fallback = document.querySelector(
                    '.top-cards-menu .menu-item.role-visible:not(.ai-chat-item)');
                const tab = fallback ? fallback.getAttribute('data-tab') : null;
                setTimeout(() => { this.showTab(tab || 'profile'); }, 0);
            }
        }
    }

    updateChatGating() {
        const gate = document.getElementById('chatEnrollmentGate');
        const layout = document.getElementById('chatActualLayout');
        if (!gate || !layout) return;
        const normalizedRole = (this.userRole || '').toLowerCase();
        const isStudent = normalizedRole === 'student';
        const locked = isStudent && !this.hasApprovedEnrollment;
        gate.style.display   = locked ? 'flex' : 'none';
        layout.style.display = locked ? 'none' : '';
    }

    setupEventListeners() {
        // Send message
        document.getElementById('sendBtn').addEventListener('click', () => this.sendMessage());
        document.getElementById('messageInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Phase 2: course tutor mode toggle
        const tutorToggle = document.getElementById('tutorModeToggle');
        const tutorSelect = document.getElementById('tutorCourseSelect');
        const tutorAvatarWrap = document.getElementById('tutorAvatarWrap');
        if (tutorToggle && tutorSelect) {
            tutorToggle.addEventListener('change', async () => {
                const on = tutorToggle.checked;
                tutorSelect.style.display = on ? 'inline-block' : 'none';
                if (tutorAvatarWrap) tutorAvatarWrap.style.display = on ? 'inline-flex' : 'none';
                if (on && tutorSelect.options.length <= 1) {
                    await this.loadTutorCourses();
                }
            });
        }

        // File upload
        document.getElementById('fileInput').addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            document.getElementById('filesList').textContent = files.map(f => f.name).join(', ');
            this.renderChatFiles(files.map(f => f.name));
        });

        // New chat (Claude-style)
        const newChatBtn = document.getElementById('newChatBtn');
        if (newChatBtn) newChatBtn.addEventListener('click', () => this.startNewChat());

        // Chat history collapse/expand toggle
        const historyToggle = document.getElementById('chatHistoryToggle');
        const historySidebar = document.getElementById('chatHistorySidebar');
        const chatLayout = document.querySelector('.chat-layout.claude-style');
        const applyHistoryCollapsed = (collapsed) => {
            if (!historySidebar || !chatLayout) return;
            historySidebar.classList.toggle('collapsed', collapsed);
            chatLayout.classList.toggle('history-collapsed', collapsed);
            if (historyToggle) {
                historyToggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
                historyToggle.setAttribute('title', collapsed ? 'Show chat history' : 'Hide chat history');
            }
        };
        const savedCollapsed = localStorage.getItem('chatHistoryCollapsed') === '1';
        applyHistoryCollapsed(savedCollapsed);
        if (historyToggle) {
            historyToggle.addEventListener('click', () => {
                const nowCollapsed = !historySidebar.classList.contains('collapsed');
                applyHistoryCollapsed(nowCollapsed);
                localStorage.setItem('chatHistoryCollapsed', nowCollapsed ? '1' : '0');
            });
        }

        // Top menu: tap-to-toggle dropdowns (works alongside CSS hover)
        document.querySelectorAll('.top-cards-menu .menu-group').forEach(group => {
            const title = group.querySelector('.menu-group-title');
            if (!title) return;
            title.addEventListener('click', (e) => {
                e.stopPropagation();
                const wasOpen = group.classList.contains('open');
                document.querySelectorAll('.top-cards-menu .menu-group.open').forEach(g => g.classList.remove('open'));
                if (!wasOpen) group.classList.add('open');
            });
        });
        document.addEventListener('click', () => {
            document.querySelectorAll('.top-cards-menu .menu-group.open').forEach(g => g.classList.remove('open'));
        });
        // Close dropdown after a menu item is chosen
        document.querySelectorAll('.top-cards-menu .menu-item').forEach(item => {
            item.addEventListener('click', () => {
                const g = item.closest('.menu-group');
                if (g) g.classList.remove('open');
            });
        });

        // Initial render of saved chat sessions
        this.loadChatSessionsFromStorage();
        this.renderChatHistory();

        // Prompt helper
        document.getElementById('promptHelper').addEventListener('click', () => this.showPromptHelper());

        // Modal close
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.target.closest('.modal').classList.remove('show');
            });
        });

        // Clear chat
        const clearChatBtn = document.getElementById('clearChat');
        if (clearChatBtn) clearChatBtn.addEventListener('click', () => this.clearChat());

        // Export chat
        const exportChatBtn = document.getElementById('exportChat');
        if (exportChatBtn) exportChatBtn.addEventListener('click', () => this.exportChat());

        // Comparison
        const runComparisonBtn = document.getElementById('runComparison');
        if (runComparisonBtn) runComparisonBtn.addEventListener('click', () => this.runComparison());

        // Sessions
        const newSessionBtn = document.getElementById('newSession');
        if (newSessionBtn) newSessionBtn.addEventListener('click', () => this.startNewSession());
        
        const endSessionBtn = document.getElementById('endSession');
        if (endSessionBtn) endSessionBtn.addEventListener('click', () => this.endCurrentSession());

        // Admin authentication
        // Admin login is now handled via separate /admin-login page
    }

    async loadTutorCourses() {
        const sel = document.getElementById('tutorCourseSelect');
        if (!sel) return;
        try {
            const resp = await fetch('/api/courses/list', { credentials: 'include' });
            const data = await resp.json();
            sel.innerHTML = '';
            const placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = 'Select a course…';
            sel.appendChild(placeholder);
            (data.courses || []).forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = `${c.code ? c.code + ' — ' : ''}${c.title}`;
                sel.appendChild(opt);
            });
            if (!data.courses || data.courses.length === 0) {
                placeholder.textContent = 'No courses available';
            }
        } catch (e) {
            console.error('Tutor: failed to load courses', e);
            sel.innerHTML = '<option value="">Could not load courses</option>';
        }
    }

    async sendTutorMessage(message) {
        const input = document.getElementById('messageInput');
        const courseSelect = document.getElementById('tutorCourseSelect');
        const avatarToggle = document.getElementById('tutorAvatarToggle');
        const summary = document.getElementById('tutorContextSummary');
        const courseId = courseSelect ? courseSelect.value : '';
        if (!courseId) {
            this.showNotification('Pick a course for tutor mode first', 'warning');
            return;
        }
        try {
            this.addMessageToUI('user', message);
            input.value = '';
            const loadingId = this.addMessageToUI('ai', '<div class="loading"></div>');

            const currentLanguage = window.i18n ? window.i18n.currentLanguage : 'en';
            const provider = (this.selectedModel || 'openai').toLowerCase();
            const body = {
                course_id: courseId,
                message: message,
                provider: provider,
                version: this.selectedVersion || undefined,
                language: currentLanguage,
                conversation_history: this.conversationMemory || [],
                want_avatar: !!(avatarToggle && avatarToggle.checked),
            };

            const resp = await fetch('/api/v1/tutor/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(body),
            });
            const data = await resp.json();
            document.getElementById(loadingId)?.remove();

            if (data.error) {
                this.addMessageToUI('ai', `❌ Tutor error: ${data.error}`);
                return;
            }
            this.addMessageToUI('ai', data.text, data);
            this.updateCostTracking(data);
            this.updateConversationMemory(message, data.text);

            if (Array.isArray(data.citations) && data.citations.length > 0) {
                const panel = document.createElement('div');
                panel.className = 'tutor-citations';
                panel.setAttribute('data-testid', 'panel-tutor-citations');
                panel.style.cssText =
                    'margin-top:8px;padding:8px 10px;border-left:3px solid #6c8cff;' +
                    'background:rgba(108,140,255,0.08);border-radius:4px;font-size:0.9em;';

                const header = document.createElement('div');
                header.style.cssText = 'font-weight:600;margin-bottom:4px;';
                const icon = document.createElement('i');
                icon.className = 'fas fa-book-open';
                header.appendChild(icon);
                header.appendChild(document.createTextNode(' Sources from your course'));
                panel.appendChild(header);

                const list = document.createElement('ul');
                list.style.cssText = 'margin:0;padding-left:18px;';

                const safeUrl = (raw) => {
                    if (!raw || typeof raw !== 'string') return null;
                    const trimmed = raw.trim();
                    if (!trimmed) return null;
                    if (trimmed.startsWith('/') && !trimmed.startsWith('//')) return trimmed;
                    try {
                        const u = new URL(trimmed, window.location.origin);
                        if (u.protocol === 'http:' || u.protocol === 'https:') return u.href;
                    } catch (_) { /* fall through */ }
                    return null;
                };

                data.citations.forEach(c => {
                    const li = document.createElement('li');
                    li.style.margin = '2px 0';
                    const labelText = `Week ${c.week_number ?? '?'}: ${c.title || 'Untitled'}`;
                    const url = safeUrl(c.url);
                    if (url) {
                        const a = document.createElement('a');
                        a.href = url;
                        a.target = '_blank';
                        a.rel = 'noopener noreferrer';
                        a.setAttribute('data-testid', `link-tutor-citation-${c.id}`);
                        a.textContent = labelText;
                        li.appendChild(a);
                    } else {
                        const span = document.createElement('span');
                        span.setAttribute('data-testid', `text-tutor-citation-${c.id}`);
                        span.textContent = labelText;
                        li.appendChild(span);
                    }
                    list.appendChild(li);
                });
                panel.appendChild(list);
                this.addMessageToUI('ai', panel.outerHTML);
            }

            if (summary && data.context_summary) {
                const cs = data.context_summary;
                summary.style.display = 'inline';
                summary.textContent =
                    `Grounded: ${cs.materials_grounded || 0} materials · ` +
                    `Level: ${cs.preferred_difficulty || 'adaptive'} · ` +
                    `Score: ${cs.overall_score != null ? Math.round(cs.overall_score) : 'n/a'}`;
            }
            if (data.avatar && data.avatar.video_id) {
                this.embedAvatarVideo(data.avatar.video_id, data.avatar.status_url);
            }
        } catch (e) {
            console.error('Tutor send failed', e);
            this.addMessageToUI('ai', `❌ Tutor error: ${e.message}`);
        }
    }

    embedAvatarVideo(videoId, statusUrl) {
        const fallbackUrl = statusUrl || `/api/heygen/status/${videoId}`;
        const messageId = this.addMessageToUI(
            'ai',
            `<div class="tutor-avatar-block" data-video-id="${videoId}">
                <div class="tutor-avatar-loading" data-testid="status-tutor-avatar-${videoId}" style="display:flex; align-items:center; gap:10px; padding:12px; background:#f3f4f6; border-radius:8px;">
                    <div class="loading"></div>
                    <span>🎬 Rendering avatar instructor video… this can take a minute.</span>
                </div>
            </div>`
        );

        const block = document.querySelector(`#${messageId} .tutor-avatar-block[data-video-id="${videoId}"]`);
        if (!block) return;

        const startedAt = Date.now();
        const maxMs = 5 * 60 * 1000; // give up after 5 minutes
        const intervalMs = 4000;

        const renderFailure = (msg) => {
            block.innerHTML = `
                <div style="padding:12px; background:#fef2f2; border:1px solid #fecaca; border-radius:8px;">
                    <div style="margin-bottom:6px;">⚠️ Avatar video unavailable: ${msg || 'render failed'}.</div>
                    <a href="${fallbackUrl}" target="_blank" rel="noopener noreferrer"
                       data-testid="link-tutor-avatar-${videoId}">Check status / download manually</a>
                </div>`;
        };

        const renderReady = (videoUrl, thumb) => {
            block.innerHTML = `
                <div style="margin-top:8px;">
                    <video controls preload="metadata" playsinline
                           ${thumb ? `poster="${thumb}"` : ''}
                           style="width:100%; max-width:560px; border-radius:8px; background:#000;"
                           data-testid="video-tutor-avatar-${videoId}">
                        <source src="${videoUrl}" type="video/mp4">
                        Your browser doesn't support embedded video.
                        <a href="${videoUrl}" target="_blank" rel="noopener noreferrer">Download the video</a>.
                    </video>
                    <div style="margin-top:6px; font-size:0.85em;">
                        <a href="${videoUrl}" target="_blank" rel="noopener noreferrer"
                           data-testid="link-tutor-avatar-${videoId}">Open video in new tab</a>
                    </div>
                </div>`;
        };

        const poll = async () => {
            if (!document.body.contains(block)) return; // user navigated away
            if (Date.now() - startedAt > maxMs) {
                renderFailure('timed out waiting for render');
                return;
            }
            try {
                const resp = await fetch(`/api/heygen/status/${encodeURIComponent(videoId)}`);
                const data = await resp.json().catch(() => ({}));
                if (!resp.ok) {
                    renderFailure(data.error || `status ${resp.status}`);
                    return;
                }
                const status = (data.status || '').toLowerCase();
                if (status === 'completed' && data.video_url) {
                    renderReady(data.video_url, data.thumbnail_url);
                    return;
                }
                if (status === 'failed' || data.error) {
                    renderFailure(data.error || 'HeyGen reported a failure');
                    return;
                }
                setTimeout(poll, intervalMs);
            } catch (err) {
                console.error('Avatar status poll failed', err);
                setTimeout(poll, intervalMs);
            }
        };

        setTimeout(poll, 1500);
    }

    setupTabNavigation() {
        // Navigation is now handled in the right-side menu via inline script
        // This function is kept for backward compatibility
        // The actual tab switching is handled by the right-side menu navigation script in index.html
    }

    async loadTabData(tabName) {
        switch(tabName) {
            case 'analytics':
                await this.loadAnalytics();
                break;
            case 'library':
                await this.loadPromptLibrary();
                break;
            case 'sessions':
                await this.loadSessions();
                break;
            case 'survey':
                // Setup survey event listeners if not already done
                this.setupSurveyEventListeners();
                break;
            case 'exit-exam':
                // Setup exit exam event listeners if not already done
                this.setupExitExamEventListeners();
                // Load exit exam immediately if not already loaded
                const examContainer = document.getElementById('examQuestions');
                if (examContainer && examContainer.innerHTML.trim() === '') {
                    this.loadExitExam();
                }
                break;
            case 'presentmate':
                // Show instructions for PresentMate
                this.showPresentMateInstructions();
                break;
            case 'my-courses':
                // Student courses tab - course browsing and enrollment
                if (window.studentCoursesManager) {
                    await window.studentCoursesManager.init();
                }
                break;
            case 'my-classes':
                // Student classes tab - Class-centric dashboard
                if (window.studentClassDashboard) {
                    await window.studentClassDashboard.init();
                }
                break;
            case 'my-certificates':
                // Student certificates tab
                await this.loadMyCertificates();
                break;
            case 'instructor-classes':
                // Instructor classes tab
                if (window.classManager) {
                    await window.classManager.loadInstructorClasses();
                }
                break;
            case 'instructors':
                // Admin instructors tab
                if (this.isAdmin && window.classManager) {
                    await window.classManager.loadInstructors();
                    await window.classManager.loadAllClasses();
                    await this.loadEnrollmentManagementDropdowns();
                }
                break;
            case 'classes':
                // Admin classes management tab - load courses table and class cards
                if (this.isAdmin && window.classManager) {
                    await window.classManager.loadCoursesManagementTable();
                    // Load admin class cards for student enrollment management
                    if (window.loadAdminClassCards) {
                        await window.loadAdminClassCards();
                    }
                }
                break;
            case 'admin':
                if (this.isAdmin) {
                    await this.loadAdminPanel();
                    await this.refreshSurveyUsers();
                    // Initialize Ethics Certificate admin settings
                    if (window.adminEthicsSettings) {
                        await window.adminEthicsSettings.init();
                    }
                }
                break;
            case 'student-management':
                // Student management tab - load students
                if (window.studentManager) {
                    await window.studentManager.loadStudents();
                }
                break;
            case 'course-materials':
                // Course materials tab - load classes for selection
                if (window.courseMaterialsManager) {
                    await window.courseMaterialsManager.loadClasses();
                }
                break;
            case 'agentic-ai-lab':
                // Agentic AI Lab tab
                if (window.agenticAILab) {
                    await window.agenticAILab.init();
                }
                break;
            case 'ethics-certificate':
                // Ethics Certificate tab - reinitialize on every activation (idempotent)
                if (window.ethicsCertificate) {
                    await window.ethicsCertificate.init();
                } else {
                    console.error('Ethics Certificate module not loaded');
                }
                break;
            case 'ai-config':
                // AI Configuration tab - load AI provider status
                if (this.isAdmin) {
                    await this.loadAIConfiguration();
                }
                break;
            case 'certificates':
                // Certificates management tab - data loads on button click, not automatically
                break;
        }
    }

    async loadAIConfiguration() {
        const container = document.getElementById('aiProvidersStatus');
        if (!container) return;
        
        container.innerHTML = '<div style="text-align: center; padding: 40px; color: #666;"><i class="fas fa-spinner fa-spin fa-2x"></i><p style="margin-top: 16px;">Loading AI configuration...</p></div>';
        
        try {
            const response = await fetch('/admin/api/ai-config', {
                credentials: 'include'
            });
            
            if (!response.ok) throw new Error('Failed to load AI configuration');
            
            const data = await response.json();
            const providers = data.providers || [];
            
            if (providers.length === 0) {
                container.innerHTML = '<p style="text-align: center; color: #666;">No AI providers configured</p>';
                return;
            }
            
            let html = '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px;">';
            
            providers.forEach(provider => {
                const isConfigured = provider.configured;
                const statusColor = isConfigured ? '#27ae60' : '#e74c3c';
                const statusIcon = isConfigured ? 'check-circle' : 'times-circle';
                const statusText = isConfigured ? 'Configured' : 'Not Configured';
                const sourceText = provider.source === 'env' ? '(from environment)' : (provider.source === 'database' ? '(from database)' : '');
                
                html += `
                    <div style="padding: 20px; background: ${isConfigured ? '#e8f5e9' : '#fff'}; border-radius: 10px; border: 1px solid ${isConfigured ? '#a5d6a7' : '#ddd'};" data-testid="card-ai-provider-${provider.id}">
                        <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <i class="fas fa-${statusIcon}" style="color: ${statusColor}; font-size: 1.3rem;"></i>
                                <strong style="font-size: 1.1rem;">${provider.name}</strong>
                            </div>
                            <span style="font-size: 0.8rem; color: ${statusColor};">${statusText} ${sourceText}</span>
                        </div>
                        <div style="font-size: 0.85rem; color: #666; margin-bottom: 12px;">${provider.description}</div>
                        ${isConfigured ? `<div style="font-size: 0.85rem; color: #888; margin-bottom: 12px;">Current key: <code>${provider.key_preview}</code></div>` : ''}
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            <input type="password" id="api-key-${provider.id}" placeholder="Enter API key..." style="flex: 1; min-width: 150px; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 0.9rem;" data-testid="input-api-key-${provider.id}">
                            <button onclick="window.app.saveAPIKey('${provider.id}')" style="padding: 8px 16px; background: #1B5E20; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem;" data-testid="button-save-key-${provider.id}">
                                <i class="fas fa-save"></i> Save
                            </button>
                            ${isConfigured && provider.source === 'database' ? `
                            <button onclick="window.app.deleteAPIKey('${provider.id}')" style="padding: 8px 12px; background: #e74c3c; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem;" data-testid="button-delete-key-${provider.id}">
                                <i class="fas fa-trash"></i>
                            </button>
                            ` : ''}
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
            container.innerHTML = html;
            
        } catch (error) {
            console.error('Error loading AI configuration:', error);
            container.innerHTML = '<div style="text-align: center; padding: 40px; color: #e74c3c;"><i class="fas fa-exclamation-triangle fa-2x"></i><p style="margin-top: 16px;">Failed to load AI configuration</p></div>';
        }
    }
    
    async saveAPIKey(providerId) {
        const input = document.getElementById(`api-key-${providerId}`);
        const apiKey = input ? input.value.trim() : '';
        
        if (!apiKey) {
            alert('Please enter an API key');
            return;
        }
        
        try {
            const response = await fetch('/admin/api/ai-credentials', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ provider: providerId, api_key: apiKey })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                alert(data.message || 'API key saved successfully');
                input.value = '';
                await this.loadAIConfiguration();
            } else {
                alert(data.error || 'Failed to save API key');
            }
        } catch (error) {
            console.error('Error saving API key:', error);
            alert('Failed to save API key');
        }
    }
    
    async deleteAPIKey(providerId) {
        if (!confirm('Are you sure you want to delete this API key?')) return;
        
        try {
            const response = await fetch(`/admin/api/ai-credentials/${providerId}`, {
                method: 'DELETE',
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (response.ok) {
                alert(data.message || 'API key deleted');
                await this.loadAIConfiguration();
            } else {
                alert(data.error || 'Failed to delete API key');
            }
        } catch (error) {
            console.error('Error deleting API key:', error);
            alert('Failed to delete API key');
        }
    }

    showPresentMateInstructions() {
        // Only show instructions once per session
        if (this.presentmateInstructionsShown) return;
        this.presentmateInstructionsShown = true;
        
        const container = document.getElementById('messagesContainer');
        // Remove welcome message if it exists
        const welcome = container.querySelector('.welcome-message');
        if (welcome) welcome.remove();
        
        const instructionsMessage = `## 🎨 Welcome to PresentMate!

**PresentMate** is your AI-powered presentation generator that uses multiple AI models to create professional presentations with stunning visuals.

### 📝 How to Use:

**Step 1: Generate Your Slides**
Type your presentation request, for example:
- "Create a presentation about Climate Change with 5 slides"
- "Make a presentation on Machine Learning for beginners with 7 slides"
- "Generate a business proposal presentation with 6 slides"

You can also attach documents or files for PresentMate to use as reference.

**Step 2: Convert to Your Preferred Format**
Once your slides are generated, type one of these commands:
- \`pptx\` or \`powerpoint\` - Download as PowerPoint presentation
- \`html\` - Download as standalone HTML webpage
- \`json\` - Get the data in JSON format

### 🤖 AI Models Used:
- **GPT-4 (OpenAI)** - Generates presentation structure and outline
- **Claude (Anthropic)** - Refines and enhances content
- **DALL-E (OpenAI)** - Creates custom images for each slide

### ✨ Features:
- **AI-Generated Visuals**: Each slide gets a custom image
- **Professional Layouts**: Polished designs for both PowerPoint and HTML
- **Multiple Formats**: Convert to PPTX, HTML, or JSON
- **Smart Caching**: Generate once, convert to multiple formats

**Ready to create? Just type your presentation topic below!** 👇`;

        this.addMessageToUI('ai', instructionsMessage);
    }

    showTab(tabName) {
        // Find the menu item for this tab
        const menuItem = document.querySelector(`.menu-item[data-tab="${tabName}"]`);
        if (menuItem) {
            menuItem.click();
        } else {
            // Fallback: manually switch tabs
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            const tabContent = document.getElementById(`${tabName}-tab`);
            if (tabContent) {
                tabContent.classList.add('active');
                this.loadTabData(tabName);
            }
        }
    }

    navigateBack() {
        // Navigate to previous tab in history
        if (this.navigationHistory.length === 0) {
            console.log('No navigation history to go back to');
            return;
        }
        
        // Pop the last tab from history
        const previousTab = this.navigationHistory.pop();
        
        // Update currentTab to the tab we're navigating back to
        this.currentTab = previousTab;
        
        // Update back button visibility
        const backBtn = document.getElementById('globalBackBtn');
        if (backBtn) {
            backBtn.style.display = this.navigationHistory.length > 0 ? 'inline-flex' : 'none';
        }
        
        // Navigate to previous tab without adding to history
        const menuItem = document.querySelector(`.menu-item[data-tab="${previousTab}"]`);
        if (menuItem && window.handleMenuClick) {
            window.handleMenuClick(menuItem, false); // false = don't add to history
        } else {
            // Fallback
            this.showTab(previousTab);
        }
    }

    startEthicsCertification(track, level) {
        // Legacy function - now just navigate to ethics certificate tab
        // The actual ethics system uses ethics_certificate.js
        this.showTab('ethics-certificate');
    }

    async loadModels() {
        try {
            const response = await fetch('/api/admin/models');
            const data = await response.json();
            this.modelsConfig = data.models;
            this.renderModels();
            this.renderComparisonModels();
        } catch (error) {
            console.error('Error loading models:', error);
        }
    }

    getModelCapabilities(provider) {
        const capabilities = {
            'openai': { 
                icon: 'fa-brain', 
                tips: ['Text & code generation', 'File analysis (PDF, images)', 'Vision support', 'Function calling', 'Best for: coding, analysis, creative writing']
            },
            'claude': { 
                icon: 'fa-comments', 
                tips: ['Long context (200K tokens)', 'Document analysis', 'Nuanced reasoning', 'Safe & helpful', 'Best for: research, writing, complex tasks']
            },
            'gemini': { 
                icon: 'fa-google', 
                tips: ['Multimodal (text, images, video)', 'Fast responses', 'Large context window', 'Best for: quick queries, multimedia']
            },
            // The catalogue calls this provider 'images'. 'dalle' is kept
            // because older saved chat sessions still name it.
            'images': {
                icon: 'fa-image',
                tips: ['Answers with a picture, not text', 'Describe what you want to see',
                       'GPT Image (replaces DALL-E)', 'Best for: graphics, illustrations, design']
            },
            'dalle': {
                icon: 'fa-image',
                tips: ['Answers with a picture, not text', 'Describe what you want to see',
                       'GPT Image (replaces DALL-E)', 'Best for: graphics, illustrations, design']
            },
            'perplexity': { 
                icon: 'fa-search', 
                tips: ['Real-time web search', 'Up-to-date information', 'Source citations', 'Best for: research, news, current events']
            },
            'grok': { 
                icon: 'fa-bolt', 
                tips: ['Real-time knowledge', 'Witty responses', 'Uncensored answers', 'Best for: casual chat, current topics']
            },
            'deepseek': { 
                icon: 'fa-code', 
                tips: ['Code specialized', 'Cost effective', 'Fast inference', 'Best for: programming, debugging']
            }
        };
        return capabilities[provider] || { icon: 'fa-robot', tips: ['AI assistant'] };
    }

    renderModels() {
        const container = document.getElementById('modelsList');
        container.innerHTML = '';

        // Sort models: enabled first, then disabled
        const sortedModels = Object.entries(this.modelsConfig).sort(([, a], [, b]) => {
            if (a.enabled === b.enabled) return 0;
            return a.enabled ? -1 : 1;
        });

        sortedModels.forEach(([provider, config]) => {
            const modelItem = document.createElement('div');
            modelItem.className = 'model-item';
            
            // Unusable either way: switched off, or no key to call it with.
            if (!config.enabled || config.has_api_key === false) {
                modelItem.classList.add('model-disabled');
            }

            // "Active" has to mean "you can use this now". The catalogue's
            // enabled flag only says the provider is switched on; without a
            // key the request fails the moment it is sent.
            const usable = config.enabled && config.has_api_key !== false;
            const statusBadge = usable
                ? '<span class="model-status-badge status-active">Active</span>'
                : `<span class="model-status-badge status-inactive" title="${
                    config.enabled
                      ? 'No API key is configured for this provider. Add one in Administration > API Keys & Integrations.'
                      : 'Switched off in config.yaml.'
                  }">${config.enabled ? 'No API key' : 'Disabled'}</span>`;

            const caps = this.getModelCapabilities(provider);
            const tooltipContent = caps.tips.map(t => `• ${t}`).join('\n');

            // "OpenAI Images" reads better than "IMAGES"; the label comes
            // from config.yaml so renaming a provider needs no code change.
            const displayName = config.label || provider.toUpperCase();
            const kindBadge = config.kind === 'image'
                ? '<span class="model-kind-badge" title="Replies with a generated image">'
                  + '<i class="fas fa-image"></i> image</span>'
                : '';

            modelItem.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <strong>${displayName}</strong>
                        ${kindBadge}
                        <span class="model-help-hint" title="${tooltipContent}" style="cursor: help; color: #6b7280; font-size: 14px;">
                            <i class="fas fa-question-circle"></i>
                        </span>
                    </div>
                    ${statusBadge}
                </div>
                <select class="model-version-select" data-provider="${provider}" ${!usable ? 'disabled' : ''}>
                    ${config.versions
                        .filter(v => v.enabled)
                        .map(v => `
                            <option value="${v.id}" ${v.id === config.default_version ? 'selected' : ''}>
                                ${v.name}
                            </option>
                        `).join('')}
                </select>
            `;

            // Only wire up a provider that can actually answer.
            if (config.enabled && config.has_api_key !== false) {
                const selectElement = modelItem.querySelector('select');
                
                modelItem.addEventListener('click', (e) => {
                    // Select this model (even if clicking on select element)
                    document.querySelectorAll('.model-item').forEach(item => item.classList.remove('selected'));
                    modelItem.classList.add('selected');
                    const version = selectElement ? selectElement.value : config.default_version || '';
                    this.selectModel(provider, version);
                    
                    // If clicking on option, stop propagation to prevent conflicts
                    if (e.target.tagName === 'OPTION') {
                        e.stopPropagation();
                    }
                });

                if (selectElement) {
                    selectElement.addEventListener('change', (e) => {
                        // Ensure the model card is also selected when changing version
                        document.querySelectorAll('.model-item').forEach(item => item.classList.remove('selected'));
                        modelItem.classList.add('selected');
                        this.selectModel(provider, e.target.value);
                    });
                }
            }

            container.appendChild(modelItem);
        });

        // Start on a usable provider. Nothing was selected until the person
        // clicked a card, so opening the chat and typing did nothing at all:
        // sendMessage() bails out when no model is set.
        this.selectDefaultModel();
    }

    /** Select the first provider that can actually answer, unless the person
     *  has already chosen one. */
    selectDefaultModel() {
        if (this.selectedModel && this.selectedVersion) return;

        const usable = Object.entries(this.modelsConfig || {})
            .filter(([, config]) => config.enabled && config.has_api_key !== false)
            // A chat provider, not an image one: typing a question and
            // getting a picture back is not a sensible default.
            .filter(([, config]) => config.kind !== 'image');
        if (!usable.length) return;

        const [provider, config] = usable[0];
        const card = document.querySelector(`.model-item select[data-provider="${provider}"]`);
        const version = (card && card.value) || config.default_version;
        if (!version) return;

        this.selectModel(provider, version);
        const item = card ? card.closest('.model-item') : null;
        if (item) {
            document.querySelectorAll('.model-item').forEach(
                el => el.classList.remove('selected'));
            item.classList.add('selected');
        }
    }

    selectModel(provider, version) {
        this.selectedModel = provider;
        this.selectedVersion = version;

        // An image provider answers with a picture, so ask for a description
        // rather than a question.
        const input = document.getElementById('messageInput');
        const config = this.modelsConfig[provider] || {};
        if (input) {
            input.placeholder = config.kind === 'image'
                ? 'Describe the image you want, for example: a watercolour of Nizwa fort at sunrise'
                : (input.dataset.defaultPlaceholder
                   || 'Type your message here...');
        }
    }

    renderComparisonModels() {
        const container = document.getElementById('comparisonModelsSelection');
        if (!container) return;
        
        container.innerHTML = '';
        
        // Sort models: enabled first, then disabled (alphabetically within each group)
        const sortedModels = Object.entries(this.modelsConfig).sort(([, a], [, b]) => {
            if (a.enabled === b.enabled) return 0;
            return a.enabled ? -1 : 1;
        });
        
        sortedModels.forEach(([provider, config]) => {
            if (!config.enabled || config.has_api_key === false) return;
            // Comparison puts answers side by side; an image provider has no
            // answer to line up against the others.
            if (config.kind === 'image') return;

            const label = document.createElement('label');
            label.className = 'comparison-model-label';
            label.innerHTML = `
                <input type="checkbox" value="${provider}" class="comparison-model-checkbox">
                <span>${config.label || provider.toUpperCase()}</span>
            `;
            container.appendChild(label);
        });
    }

    selectAllModels() {
        document.querySelectorAll('.comparison-model-checkbox').forEach(cb => {
            cb.checked = true;
        });
        this.showNotification('All models selected', 'success');
    }

    deselectAllModels() {
        document.querySelectorAll('.comparison-model-checkbox').forEach(cb => {
            cb.checked = false;
        });
        this.showNotification('All models deselected', 'info');
    }

    async sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();

        if (!message) return;
        
        if (!this.selectedModel || !this.selectedVersion) {
            this.showNotification('Please select a model first', 'warning');
            return;
        }

        // Special handling for PresentMate
        if (this.selectedModel === 'presentmate') {
            return this.handlePresentMate(message);
        }

        // Phase 2: course tutor mode — route through adaptive tutor API
        const tutorToggle = document.getElementById('tutorModeToggle');
        if (tutorToggle && tutorToggle.checked) {
            return this.sendTutorMessage(message);
        }

        try {
            // Add user message
            this.addMessageToUI('user', message);
            input.value = '';

            // Get files
            const fileInput = document.getElementById('fileInput');
            const files = fileInput ? fileInput.files : [];
            
            const formData = new FormData();
            formData.append('message', message);
            formData.append('api_key', ''); // Will be fetched from config
            formData.append('version', this.selectedVersion || '');
            
            // Include current language for AI responses
            const currentLanguage = window.i18n ? window.i18n.currentLanguage : 'en';
            formData.append('language', currentLanguage);
            
            // Include conversation history for context (last 4 messages / 2 exchanges)
            formData.append('conversation_history', JSON.stringify(this.conversationMemory));

            for (let file of files) {
                formData.append('files', file);
            }

            const apiUrl = `/api/chat/${this.selectedModel}`;
            console.log('📡 Sending to:', apiUrl);

            // Show loading
            const loadingId = this.addMessageToUI('ai', '<div class="loading"></div>');

            const response = await fetch(apiUrl, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            // Remove loading
            document.getElementById(loadingId)?.remove();

            if (data.error) {
                this.addMessageToUI('ai', `❌ Error: ${data.error}`);
            } else {
                this.addMessageToUI('ai', data.text, data);
                this.updateCostTracking(data);
                
                // Update conversation memory with file context for persistent file memory
                let memoryMessage = message;
                if (data.file_context) {
                    memoryMessage = message + "\n\n[UPLOADED FILE CONTENT]\n" + data.file_context;
                    console.log('📎 File content stored in memory for follow-up questions');
                }
                this.updateConversationMemory(memoryMessage, data.text);
                
                // Add to session if active
                if (this.currentSession) {
                    await this.addMessageToSession(data);
                }
            }

            // Clear files
            const fileInputClear = document.getElementById('fileInput');
            const filesList = document.getElementById('filesList');
            if (fileInputClear) fileInputClear.value = '';
            if (filesList) filesList.textContent = '';

        } catch (error) {
            console.error('Error:', error);
            this.addMessageToUI('ai', `❌ Error: ${error.message}`);
        }
    }

    async handlePresentMate(message) {
        const input = document.getElementById('messageInput');
        
        try {
            // Check if user is asking for conversion
            const convertMatch = message.match(/^(convert|pptx|powerpoint|html|web|json|data)/i);
            
            if (this.presentmateSession && convertMatch) {
                // User wants to convert the generated slides
                this.addMessageToUI('user', message);
                input.value = '';
                
                // Extract the format from the message first
                let format = 'json'; // default
                const msgLower = message.toLowerCase();
                if (msgLower.includes('pptx') || msgLower.includes('powerpoint') || msgLower.includes('ppt')) {
                    format = 'pptx';
                } else if (msgLower.includes('html') || msgLower.includes('web')) {
                    format = 'html';
                } else if (msgLower.includes('json')) {
                    format = 'json';
                }
                
                // Show status updates with proper timing
                const statusId = this.addMessageToUI('ai', '🎨 **Preparing to generate visuals...**');
                
                // Sequential status updates
                await new Promise(resolve => setTimeout(() => {
                    const elem = document.getElementById(statusId);
                    if (elem) elem.querySelector('.message-content').innerHTML = '🖼️ **Communicating with DALL-E (OpenAI) to generate images...**';
                    resolve();
                }, 500));
                
                await new Promise(resolve => setTimeout(() => {
                    const elem = document.getElementById(statusId);
                    if (elem) elem.querySelector('.message-content').innerHTML = '💾 **Embedding images into presentation...**';
                    resolve();
                }, 800));
                
                // Make the API call
                const response = await fetch('/api/presentmate/convert', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: this.presentmateSession,
                        format: format
                    })
                });
                
                const data = await response.json();
                
                // Final status
                const elem = document.getElementById(statusId);
                if (elem) elem.querySelector('.message-content').innerHTML = `📄 **Building your ${format.toUpperCase()} file...**`;
                
                await new Promise(resolve => setTimeout(() => {
                    document.getElementById(statusId)?.remove();
                    resolve();
                }, 400));
                
                if (data.error) {
                    this.addMessageToUI('ai', `❌ Error: ${data.error}`);
                    return;
                }
                
                if (data.status === 'success') {
                    let resultMessage = `✅ ${data.message}\n\n`;
                    
                    // Show image statistics
                    if (data.images_embedded) {
                        resultMessage += `🎨 **${data.images_embedded} AI-generated visuals embedded!**\n\n`;
                    }
                    
                    if (data.download_url) {
                        resultMessage += `📥 **[Click here to download your presentation](${data.download_url})**\n\n`;
                        resultMessage += `**File:** ${data.filename}\n`;
                        resultMessage += `**Format:** ${data.format.toUpperCase()}`;
                    } else if (data.html) {
                        resultMessage += `\n\n**Your HTML presentation is ready!**\n\n`;
                        resultMessage += '```html\n' + data.html.substring(0, 800) + '...\n```';
                    } else if (data.data) {
                        resultMessage += `\n\n**JSON Data:**\n\n`;
                        resultMessage += '```json\n' + JSON.stringify(data.data, null, 2).substring(0, 1000) + '...\n```';
                    }
                    
                    this.addMessageToUI('ai', resultMessage);
                    this.showNotification('Conversion completed with AI visuals!', 'success');
                }
                
                return;
            }
            
            // Generate new slides from user's message
            this.addMessageToUI('user', message);
            input.value = '';
            
            // Show status updates with proper timing
            const statusId = this.addMessageToUI('ai', '🔍 **Analyzing your request...**');
            
            // Prepare form data
            const fileInput = document.getElementById('fileInput');
            const files = fileInput ? fileInput.files : [];
            
            const formData = new FormData();
            formData.append('message', message);
            
            for (let file of files) {
                formData.append('files', file);
            }
            
            // Update status messages sequentially
            await new Promise(resolve => setTimeout(() => {
                const elem = document.getElementById(statusId);
                if (elem) elem.querySelector('.message-content').innerHTML = '💬 **Communicating with GPT-4 (OpenAI) for outline...**';
                resolve();
            }, 600));
            
            await new Promise(resolve => setTimeout(() => {
                const elem = document.getElementById(statusId);
                if (elem) elem.querySelector('.message-content').innerHTML = '🤖 **Communicating with Claude (Anthropic) for content...**';
                resolve();
            }, 800));
            
            // Make the API call
            const response = await fetch('/api/presentmate/generate', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            // Final status
            const elem = document.getElementById(statusId);
            if (elem) elem.querySelector('.message-content').innerHTML = '📥 **Finalizing presentation structure...**';
            
            await new Promise(resolve => setTimeout(() => {
                document.getElementById(statusId)?.remove();
                
                if (data.error) {
                    this.addMessageToUI('ai', `❌ Error: ${data.error}\n\n${data.message || ''}`);
                    return;
                }
                
                if (data.status === 'generated') {
                    // Store session for conversion
                    this.presentmateSession = data.session_id;
                    
                    // Show generated slides content
                    let resultMessage = `📊 **${data.message}**\n\n`;
                    resultMessage += '---\n\n';
                    resultMessage += data.slides_text;
                    resultMessage += '\n\n---\n\n';
                    resultMessage += data.conversion_prompt + '\n\n';
                    resultMessage += '**Type:** `pptx`, `html`, or `json` to convert and download with AI-generated visuals!';
                    
                    this.addMessageToUI('ai', resultMessage);
                    this.showNotification('Slides generated! Choose a format to convert.', 'success');
                }
                
                // Clear files
                const fileInputClear = document.getElementById('fileInput');
                const filesList = document.getElementById('filesList');
                if (fileInputClear) fileInputClear.value = '';
                if (filesList) filesList.textContent = '';
                
                resolve();
            }, 400));
            
        } catch (error) {
            console.error('PresentMate Error:', error);
            this.addMessageToUI('ai', `❌ Error: ${error.message}`);
            this.presentmateSession = null;
        }
    }

    addMessageToUI(role, content, metadata = {}) {
        const container = document.getElementById('messagesContainer');
        
        // Remove welcome message
        const welcome = container.querySelector('.welcome-message');
        if (welcome) welcome.remove();
        
        const messageId = 'msg-' + Date.now();
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        messageDiv.id = messageId;
        
        // Format content based on role and metadata
        let formattedContent = content;
        
        // For AI responses, render markdown with syntax highlighting
        if (role === 'ai' && typeof marked !== 'undefined') {
            try {
                // Configure marked for safe rendering with syntax highlighting
                marked.setOptions({
                    breaks: true,
                    gfm: true,
                    headerIds: false,
                    mangle: false,
                    highlight: function(code, lang) {
                        if (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang)) {
                            try {
                                return hljs.highlight(code, { language: lang }).value;
                            } catch (e) {}
                        }
                        return code;
                    }
                });
                formattedContent = marked.parse(content);
            } catch (e) {
                console.error('Markdown rendering error:', e);
                formattedContent = content;
            }
        } else {
            // For user messages, escape HTML and preserve line breaks
            formattedContent = content.replace(/&/g, '&amp;')
                                      .replace(/</g, '&lt;')
                                      .replace(/>/g, '&gt;')
                                      .replace(/\n/g, '<br>');
        }
        
        // Add image if present (for DALL-E and other image generation)
        let imageHtml = '';
        if (metadata.image_url) {
            imageHtml = `<div style="margin-top: 15px;">
                <img src="${metadata.image_url}" alt="Generated Image" 
                     style="max-width: 100%; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            </div>`;
        }
        
        messageDiv.innerHTML = `
            <div class="message-content">${formattedContent}</div>
            ${imageHtml}
            ${role === 'user' ? `
                <div class="message-actions">
                    <button onclick="app.editMessage('${messageId}')"><i class="fas fa-edit"></i></button>
                    <button onclick="app.repeatMessage('${messageId}')"><i class="fas fa-redo"></i></button>
                </div>
            ` : `
                <div class="message-actions ai-actions" style="margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap;">
                    <button onclick="app.copyMessage('${messageId}')" title="Copy response" style="padding: 6px 12px; background: #e5e7eb; border: none; border-radius: 6px; cursor: pointer; font-size: 12px;">
                        <i class="fas fa-copy"></i> Copy
                    </button>
                    <button onclick="app.downloadFullResponse('${messageId}')" title="Download as file" style="padding: 6px 12px; background: #e5e7eb; border: none; border-radius: 6px; cursor: pointer; font-size: 12px;">
                        <i class="fas fa-download"></i> Download
                    </button>
                </div>
            `}
            ${metadata.model ? `<div style="margin-top: 10px; font-size: 0.85em; opacity: 0.8;">
                <i class="fas fa-robot"></i> ${metadata.model} | 
                <i class="fas fa-clock"></i> ${new Date().toLocaleTimeString()}
            </div>` : ''}
        `;
        
        // Add download buttons to code blocks and apply syntax highlighting
        if (role === 'ai') {
            // Apply syntax highlighting to all code blocks
            if (typeof hljs !== 'undefined') {
                messageDiv.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightElement(block);
                });
            }
            this.addCodeBlockActions(messageDiv, messageId);
            this.renderCharts(messageDiv);
        }

        container.appendChild(messageDiv);
        container.scrollTop = container.scrollHeight;

        this.conversationMessages.push({ role, content, metadata, timestamp: new Date().toISOString() });
        this.updateMessageCount();
        this.addToConversationHistory(content);

        return messageId;
    }

    editMessage(messageId) {
        const messageDiv = document.getElementById(messageId);
        const content = messageDiv.querySelector('.message-content').textContent;
        document.getElementById('messageInput').value = content;
        messageDiv.style.opacity = '0.5';
    }

    repeatMessage(messageId) {
        const messageDiv = document.getElementById(messageId);
        const content = messageDiv.querySelector('.message-content').textContent;
        document.getElementById('messageInput').value = content;
        this.sendMessage();
    }

    copyMessage(messageId) {
        const messageDiv = document.getElementById(messageId);
        const content = messageDiv.querySelector('.message-content').textContent;
        navigator.clipboard.writeText(content).then(() => {
            this.showNotification('Copied to clipboard!', 'success');
        }).catch(err => {
            console.error('Copy failed:', err);
            this.showNotification('Failed to copy', 'error');
        });
    }

    addCodeBlockActions(messageDiv, messageId) {
        const codeBlocks = messageDiv.querySelectorAll('pre code');
        codeBlocks.forEach((codeBlock, index) => {
            const pre = codeBlock.parentElement;
            if (pre.previousElementSibling && pre.previousElementSibling.classList.contains('code-actions')) return;
            
            // Detect language from class
            const langClass = codeBlock.className.match(/language-(\w+)/);
            const lang = langClass ? langClass[1] : 'text';
            const ext = this.getFileExtension(lang);
            
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'code-actions';
            actionsDiv.innerHTML = `
                <span class="language-label"><i class="fas fa-code"></i> ${lang}</span>
                <div style="display: flex; gap: 6px;">
                    <button onclick="app.copyCode(this)" title="Copy code">
                        <i class="fas fa-copy"></i> Copy
                    </button>
                    <button onclick="app.downloadCode(this, '${ext}')" title="Download as file">
                        <i class="fas fa-download"></i> .${ext}
                    </button>
                </div>
            `;
            pre.style.marginTop = '0';
            pre.style.borderRadius = '0 0 8px 8px';
            pre.parentElement.insertBefore(actionsDiv, pre);
        });
    }

    getFileExtension(lang) {
        const extMap = {
            'javascript': 'js', 'js': 'js', 'python': 'py', 'py': 'py',
            'html': 'html', 'css': 'css', 'json': 'json', 'sql': 'sql',
            'java': 'java', 'cpp': 'cpp', 'c': 'c', 'csharp': 'cs', 'cs': 'cs',
            'php': 'php', 'ruby': 'rb', 'go': 'go', 'rust': 'rs',
            'typescript': 'ts', 'ts': 'ts', 'bash': 'sh', 'shell': 'sh',
            'yaml': 'yaml', 'yml': 'yml', 'xml': 'xml', 'markdown': 'md', 'md': 'md'
        };
        return extMap[lang.toLowerCase()] || 'txt';
    }

    copyCode(button) {
        const actionsDiv = button.closest('.code-actions');
        const pre = actionsDiv.nextElementSibling;
        const code = pre.querySelector('code').textContent;
        navigator.clipboard.writeText(code).then(() => {
            const originalHtml = button.innerHTML;
            button.innerHTML = '<i class="fas fa-check"></i> Copied!';
            button.style.color = '#10b981';
            setTimeout(() => { 
                button.innerHTML = originalHtml;
                button.style.color = '';
            }, 2000);
        });
    }

    downloadCode(button, ext) {
        const actionsDiv = button.closest('.code-actions');
        const pre = actionsDiv.nextElementSibling;
        const code = pre.querySelector('code').textContent;
        const blob = new Blob([code], { type: 'text/plain; charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `code_${Date.now()}.${ext}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        this.showNotification(`Downloaded code as .${ext} file`, 'success');
    }

    async downloadAsFile(content, filename) {
        // Download AI-generated content as a file
        try {
            const response = await fetch('/api/download-file', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content, filename })
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                a.click();
                URL.revokeObjectURL(url);
                this.showNotification(`Downloaded ${filename}`, 'success');
            } else {
                this.fallbackDownload(content, filename);
            }
        } catch (error) {
            this.fallbackDownload(content, filename);
        }
    }

    fallbackDownload(content, filename) {
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
        this.showNotification(`Downloaded ${filename}`, 'success');
    }

    downloadFullResponse(messageId) {
        const messageDiv = document.getElementById(messageId);
        if (!messageDiv) return;
        
        const content = messageDiv.querySelector('.message-content').innerText;
        const filename = `ai_response_${Date.now()}.txt`;
        this.downloadAsFile(content, filename);
    }

    renderCharts(messageDiv) {
        const content = messageDiv.querySelector('.message-content');
        if (!content) return;
        
        // Look for chart data patterns in the response
        const chartPattern = /```chart\s*([\s\S]*?)```/gi;
        let html = content.innerHTML;
        let match;
        let chartIndex = 0;
        
        while ((match = chartPattern.exec(html)) !== null) {
            try {
                const chartData = JSON.parse(match[1]);
                const chartId = `chart-${Date.now()}-${chartIndex++}`;
                const chartHtml = `<div style="margin: 15px 0; padding: 15px; background: #fff; border-radius: 8px; border: 1px solid #e5e7eb;">
                    <canvas id="${chartId}" style="max-height: 300px;"></canvas>
                </div>`;
                html = html.replace(match[0], chartHtml);
                
                // Schedule chart rendering after DOM update
                setTimeout(() => {
                    if (typeof Chart !== 'undefined') {
                        const ctx = document.getElementById(chartId);
                        if (ctx) new Chart(ctx, chartData);
                    }
                }, 100);
            } catch (e) {
                console.error('Chart parsing error:', e);
            }
        }
        
        content.innerHTML = html;
    }

    addToConversationHistory(message) {
        const container = document.getElementById('conversationHistory');
        if (!container) {
            // Element doesn't exist, skip history update
            return;
        }
        
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.textContent = message.substring(0, 50) + (message.length > 50 ? '...' : '');
        historyItem.onclick = () => {
            document.getElementById('messageInput').value = message;
        };
        container.insertBefore(historyItem, container.firstChild);
        
        // Keep only last 10
        while (container.children.length > 10) {
            container.removeChild(container.lastChild);
        }
    }

    /* ===== Claude-style chat history (sidebar) ===== */
    loadChatSessionsFromStorage() {
        try {
            const raw = localStorage.getItem('skillpilot_chat_sessions');
            this.chatSessions = raw ? JSON.parse(raw) : [];
            if (!Array.isArray(this.chatSessions)) this.chatSessions = [];
        } catch (e) { this.chatSessions = []; }
    }

    saveChatSessionsToStorage() {
        try {
            // Keep only the 30 most recent sessions
            const trimmed = this.chatSessions.slice(-30);
            this.chatSessions = trimmed;
            localStorage.setItem('skillpilot_chat_sessions', JSON.stringify(trimmed));
        } catch (e) { /* quota */ }
    }

    persistCurrentSession() {
        if (!this.conversationMemory || this.conversationMemory.length === 0) return;
        if (!this.currentSessionId) {
            this.currentSessionId = 'sess_' + Date.now();
        }
        const firstUser = this.conversationMemory.find(m => m.role === 'user');
        const title = (firstUser?.content || 'New chat').slice(0, 60);
        const idx = this.chatSessions.findIndex(s => s.id === this.currentSessionId);
        const entry = {
            id: this.currentSessionId,
            title,
            updatedAt: Date.now(),
            messages: this.conversationMemory.slice(-60),
            files: this._chatFiles || []
        };
        if (idx >= 0) this.chatSessions[idx] = entry;
        else this.chatSessions.push(entry);
        this.saveChatSessionsToStorage();
        this.renderChatHistory();
    }

    renderChatHistory() {
        const list = document.getElementById('chatHistoryList');
        if (!list) return;
        if (!this.chatSessions || this.chatSessions.length === 0) {
            list.innerHTML = '<div class="chat-history-empty" data-i18n="no_chats_yet">No previous chats yet</div>';
            return;
        }
        const sorted = [...this.chatSessions].sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
        list.innerHTML = sorted.map(s => `
            <div class="chat-history-item ${s.id === this.currentSessionId ? 'active' : ''}" data-session-id="${s.id}" data-testid="chat-history-${s.id}">
                <span class="chat-title" title="${(s.title || '').replace(/"/g, '&quot;')}">${this._escape(s.title || 'Chat')}</span>
                <button class="chat-delete" data-delete-id="${s.id}" title="Delete chat"><i class="fas fa-times"></i></button>
            </div>
        `).join('');
        list.querySelectorAll('.chat-history-item').forEach(el => {
            el.addEventListener('click', (e) => {
                if (e.target.closest('.chat-delete')) return;
                this.loadChatSession(el.dataset.sessionId);
            });
        });
        list.querySelectorAll('.chat-delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteChatSession(btn.dataset.deleteId);
            });
        });
    }

    _escape(s) {
        return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    }

    loadChatSession(sessionId) {
        const sess = this.chatSessions.find(s => s.id === sessionId);
        if (!sess) return;
        this.currentSessionId = sessionId;
        this.conversationMemory = (sess.messages || []).slice();
        this._chatFiles = sess.files || [];
        // Rebuild messages container
        const container = document.getElementById('messagesContainer');
        if (container) {
            container.innerHTML = '';
            this.conversationMemory.forEach(m => {
                const div = document.createElement('div');
                div.className = 'message ' + (m.role === 'user' ? 'user' : 'ai');
                div.innerHTML = `<div class="message-content">${this._escape(m.content).replace(/\n/g, '<br>')}</div>`;
                container.appendChild(div);
            });
            container.scrollTop = container.scrollHeight;
        }
        this.renderChatFiles(this._chatFiles);
        this.renderChatHistory();
    }

    deleteChatSession(sessionId) {
        this.chatSessions = this.chatSessions.filter(s => s.id !== sessionId);
        this.saveChatSessionsToStorage();
        if (this.currentSessionId === sessionId) {
            this.startNewChat();
        } else {
            this.renderChatHistory();
        }
    }

    startNewChat() {
        this.currentSessionId = null;
        this.conversationMemory = [];
        this._chatFiles = [];
        const container = document.getElementById('messagesContainer');
        if (container) {
            container.innerHTML = `<div class="welcome-message">
                <h2>New Chat</h2>
                <p>Ask anything to start a fresh conversation. Up to 30 exchanges remembered.</p>
            </div>`;
        }
        const filesList = document.getElementById('filesList');
        if (filesList) filesList.textContent = '';
        this.renderChatFiles([]);
        this.renderChatHistory();
    }

    renderChatFiles(fileNames) {
        this._chatFiles = Array.isArray(fileNames) ? fileNames : [];
        const list = document.getElementById('chatFilesList');
        if (!list) return;
        if (this._chatFiles.length === 0) {
            list.innerHTML = '<div class="chat-files-empty" data-i18n="no_files_attached">No files attached</div>';
            return;
        }
        list.innerHTML = this._chatFiles.map(name => {
            const ext = (name.split('.').pop() || '').toLowerCase();
            const icon = {
                pdf: 'fa-file-pdf', doc: 'fa-file-word', docx: 'fa-file-word',
                xls: 'fa-file-excel', xlsx: 'fa-file-excel', csv: 'fa-file-csv',
                ppt: 'fa-file-powerpoint', pptx: 'fa-file-powerpoint',
                png: 'fa-file-image', jpg: 'fa-file-image', jpeg: 'fa-file-image', gif: 'fa-file-image',
                txt: 'fa-file-lines', json: 'fa-file-code', xml: 'fa-file-code',
                py: 'fa-file-code', js: 'fa-file-code', html: 'fa-file-code'
            }[ext] || 'fa-file';
            return `<div class="chat-file-pill"><i class="fas ${icon}"></i><span>${this._escape(name)}</span></div>`;
        }).join('');
    }

    updateConversationMemory(userMessage, aiResponse) {
        // Add user message
        this.conversationMemory.push({
            role: 'user',
            content: userMessage
        });

        // Add AI response
        this.conversationMemory.push({
            role: 'assistant',
            content: aiResponse
        });

        // Keep last 60 messages (30 exchanges) per session for rich follow-up context
        // File content is included in user messages, so we need more history
        if (this.conversationMemory.length > 60) {
            this.conversationMemory = this.conversationMemory.slice(-60);
        }
        // Persist current chat session to history
        try { this.persistCurrentSession(); } catch (e) { /* noop */ }

        console.log('Conversation memory updated:', this.conversationMemory.length, 'messages');
    }

    async showPromptHelper() {
        const message = document.getElementById('messageInput').value;
        const modal = document.getElementById('promptHelperModal');
        const content = document.getElementById('suggestionsContent');
        
        // Show modal immediately with loading state
        content.innerHTML = `
            <div class="loading-suggestions" style="text-align: center; padding: 40px;">
                <i class="fas fa-spinner fa-spin" style="font-size: 48px; color: #667eea; margin-bottom: 20px;"></i>
                <h3 style="color: #667eea; margin-bottom: 10px;">🤖 Analyzing Your Prompt...</h3>
                <p style="color: #666;">AI is reviewing your message and preparing helpful suggestions</p>
                <div class="loading-dots" style="margin-top: 20px;">
                    <span style="animation: blink 1.4s infinite; font-size: 24px; color: #667eea;">●</span>
                    <span style="animation: blink 1.4s infinite 0.2s; font-size: 24px; color: #667eea; margin: 0 10px;">●</span>
                    <span style="animation: blink 1.4s infinite 0.4s; font-size: 24px; color: #667eea;">●</span>
                </div>
            </div>
        `;
        modal.classList.add('show');
        
        try {
            const response = await fetch('/api/prompts/suggestions', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ task: message })
            });

            const data = await response.json();
            
            // Update with actual suggestions
            content.innerHTML = data.suggestions.map(s => `
                <div class="suggestion ${s.type}">
                    <strong>
                        <i class="fas fa-${this.getSuggestionIcon(s.type)}"></i> 
                        ${s.title}
                    </strong>
                    <p>${s.message}</p>
                    ${s.example ? `
                        <button onclick="app.applyExample(\`${s.example.replace(/`/g, '\\`')}\`)" 
                                style="margin-top: 10px; padding: 8px 16px; background: #667eea; color: white; 
                                       border: none; border-radius: 6px; cursor: pointer;">
                            <i class="fas fa-magic"></i> Apply Example
                        </button>
                    ` : ''}
                </div>
            `).join('');

        } catch (error) {
            console.error('Error getting suggestions:', error);
            content.innerHTML = `
                <div class="suggestion error" style="text-align: center; padding: 30px;">
                    <i class="fas fa-exclamation-circle" style="font-size: 48px; color: #e74c3c; margin-bottom: 15px;"></i>
                    <h3 style="color: #e74c3c;">Unable to Get Suggestions</h3>
                    <p style="color: #666;">There was an error getting AI suggestions. Please try again.</p>
                    <button onclick="document.getElementById('promptHelperModal').classList.remove('show')" 
                            style="margin-top: 15px; padding: 8px 20px; background: #667eea; color: white; 
                                   border: none; border-radius: 6px; cursor: pointer;">
                        Close
                    </button>
                </div>
            `;
        }
    }

    getSuggestionIcon(type) {
        const icons = {
            'tip': 'lightbulb',
            'warning': 'exclamation-triangle',
            'success': 'check-circle',
            'error': 'times-circle',
            'advanced': 'star'
        };
        return icons[type] || 'info-circle';
    }

    applyExample(example) {
        document.getElementById('messageInput').value = example;
        document.getElementById('promptHelperModal').classList.remove('show');
    }

    async saveCurrentPrompt() {
        const message = document.getElementById('messageInput').value;
        if (!message) {
            this.showNotification('Please enter a prompt first', 'warning');
            return;
        }

        const title = prompt('Enter a title for this prompt:');
        if (!title) return;

        const category = prompt('Enter category (General/Analysis/Coding/Creative/Teaching):', 'General');

        try {
            const response = await fetch('/api/prompts/library', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    title,
                    content: message,
                    category,
                    model: this.selectedModel,
                    parameters: { version: this.selectedVersion }
                })
            });

            const data = await response.json();
            if (data.success) {
                this.showNotification('✅ Prompt saved successfully!', 'success');
                await this.loadPromptLibrary();
            }
        } catch (error) {
            console.error('Error saving prompt:', error);
            this.showNotification('Error saving prompt', 'error');
        }
    }

    async loadPromptLibrary() {
        try {
            const response = await fetch('/api/prompts/library');
            const data = await response.json();
            
            // Store all prompts for filtering
            this.allPrompts = data.prompts || [];
            
            // Update sidebar
            const sidebarList = document.getElementById('savedPromptsList');
            if (sidebarList) {
                sidebarList.innerHTML = data.prompts.slice(0, 10).map(p => `
                    <div class="saved-prompt-item" onclick="app.loadPrompt('${p.id}')">
                        <strong>${p.title}</strong>
                        <div style="font-size: 0.85em; color: #666; margin-top: 4px;">${p.category}</div>
                    </div>
                `).join('');
            }

            // Setup filter event listeners (only once)
            this.setupPromptFilters();
            
            // Render prompts with current filter
            this.renderFilteredPrompts();
        } catch (error) {
            console.error('Error loading library:', error);
        }
    }

    setupPromptFilters() {
        const searchInput = document.getElementById('searchPrompts');
        const categoryFilter = document.getElementById('filterCategory');
        
        if (searchInput && !searchInput.hasAttribute('data-listener-added')) {
            searchInput.setAttribute('data-listener-added', 'true');
            searchInput.addEventListener('input', () => this.renderFilteredPrompts());
        }
        
        if (categoryFilter && !categoryFilter.hasAttribute('data-listener-added')) {
            categoryFilter.setAttribute('data-listener-added', 'true');
            categoryFilter.addEventListener('change', () => this.renderFilteredPrompts());
        }
    }

    renderFilteredPrompts() {
        const searchInput = document.getElementById('searchPrompts');
        const categoryFilter = document.getElementById('filterCategory');
        const libraryGrid = document.getElementById('promptLibraryGrid');
        
        if (!libraryGrid || !this.allPrompts) return;
        
        const searchTerm = (searchInput?.value || '').toLowerCase().trim();
        const selectedCategory = categoryFilter?.value || '';
        
        // Filter prompts
        let filteredPrompts = this.allPrompts.filter(p => {
            // Category filter
            if (selectedCategory && p.category !== selectedCategory) {
                return false;
            }
            
            // Search filter
            if (searchTerm) {
                const titleMatch = (p.title || '').toLowerCase().includes(searchTerm);
                const descMatch = (p.description || '').toLowerCase().includes(searchTerm);
                const contentMatch = (p.content || '').toLowerCase().includes(searchTerm);
                if (!titleMatch && !descMatch && !contentMatch) {
                    return false;
                }
            }
            
            return true;
        });
        
        // Render filtered prompts
        if (filteredPrompts.length === 0) {
            libraryGrid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #666;">
                    <i class="fas fa-search" style="font-size: 48px; margin-bottom: 15px; opacity: 0.5;"></i>
                    <p>No prompts found matching your criteria</p>
                </div>
            `;
        } else {
            libraryGrid.innerHTML = filteredPrompts.map(p => `
                <div class="prompt-card" onclick="app.loadPrompt('${p.id}')" data-testid="card-prompt-${p.id}">
                    <h3>${p.title}</h3>
                    <p style="color: #666; margin: 10px 0;">${p.description || 'No description'}</p>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px;">
                        <span style="background: #667eea; color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.85em;">
                            ${p.category}
                        </span>
                        <span style="font-size: 0.85em; color: #999;">
                            <i class="fas fa-eye"></i> ${p.use_count || 0} uses
                        </span>
                    </div>
                </div>
            `).join('');
        }
    }

    async loadPrompt(promptId) {
        try {
            const response = await fetch('/api/prompts/library');
            const data = await response.json();
            const prompt = data.prompts.find(p => p.id === promptId);
            
            if (prompt) {
                // Store the current prompt ID for tracking
                this.currentPromptId = promptId;
                
                // Populate the modal with prompt details
                document.getElementById('promptDetailTitle').textContent = prompt.title || 'Prompt Details';
                document.getElementById('promptDetailCategory').textContent = prompt.category || 'General';
                document.getElementById('promptUseCount').textContent = prompt.use_count || 0;
                document.getElementById('promptDetailDescription').textContent = prompt.description || 'No description available';
                document.getElementById('promptDetailContent').value = prompt.content || '';
                
                // Show the modal
                document.getElementById('promptDetailsModal').classList.add('show');
            }
        } catch (error) {
            console.error('Error loading prompt:', error);
        }
    }

    closePromptDetailsModal() {
        document.getElementById('promptDetailsModal').classList.remove('show');
        this.currentPromptId = null;
    }

    async copyPromptToClipboard() {
        const content = document.getElementById('promptDetailContent').value;
        try {
            await navigator.clipboard.writeText(content);
            this.showNotification('✅ Prompt copied to clipboard!', 'success');
        } catch (error) {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = content;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            this.showNotification('✅ Prompt copied to clipboard!', 'success');
        }
    }

    async usePromptFromModal() {
        const content = document.getElementById('promptDetailContent').value;
        
        // Put the (possibly modified) content into the message input
        document.getElementById('messageInput').value = content;
        
        // Increment use count if we have a prompt ID
        if (this.currentPromptId) {
            try {
                await fetch(`/api/prompts/library/${this.currentPromptId}/use`, { method: 'POST' });
            } catch (error) {
                console.error('Error incrementing use count:', error);
            }
        }
        
        // Close the modal
        this.closePromptDetailsModal();
        
        // Switch to chat tab
        this.switchTab('chat');
        
        // Focus on the message input
        document.getElementById('messageInput').focus();
        
        this.showNotification('✅ Prompt loaded to chat. Ready to send!', 'success');
    }

    updateCostTracking(data) {
        // Approximate cost calculation
        const inputTokens = data.tokens?.input || 50;
        const outputTokens = data.tokens?.output || 100;
        const cost = this.calculateCost(this.selectedVersion, inputTokens, outputTokens);
        
        this.totalCost += cost;
        this.totalTokens += (inputTokens + outputTokens);

        const totalCostElement = document.getElementById('totalCost');
        const totalTokensElement = document.getElementById('totalTokens');
        
        if (totalCostElement) {
            totalCostElement.textContent = '$' + this.totalCost.toFixed(4);
        }
        if (totalTokensElement) {
            totalTokensElement.textContent = this.totalTokens.toLocaleString();
        }
    }

    calculateCost(model, inputTokens, outputTokens) {
        // Rough per-1K blended estimate for the live counter only. The rates
        // it used before named models that were retired in 2025-2026, and it
        // charged input and output at the same rate. Authoritative costing
        // lives server-side in app/routes/analytics.py, which reads the model
        // registry and prices input and output separately.
        const rates = {
            'gpt-6-astra': 0.020,
            'gpt-5.6-sol': 0.008,
            'gpt-5.6-terra': 0.005,
            'gpt-5.6-luna': 0.0005,
            'claude-opus-5': 0.010,
            'claude-sonnet-5': 0.004,
            'claude-haiku-4-5-20251001': 0.002,
            'gemini-3.1-pro-preview': 0.005,
            'gemini-3.8-flash': 0.0015,
            'grok-4.6': 0.003,
            'deepseek-v4-flash': 0.0007,
            'sonar-pro': 0.006
        };
        const rate = rates[model] || 0.002;
        return ((inputTokens + outputTokens) / 1000) * rate;
    }

    updateMessageCount() {
        const messageCountElement = document.getElementById('messageCount');
        if (messageCountElement) {
            messageCountElement.textContent = this.conversationMessages.length;
        }
    }

    clearChat() {
        if (confirm('Clear all messages?')) {
            document.getElementById('messagesContainer').innerHTML = `
                <div class="welcome-message">
                    <i class="fas fa-robot fa-4x"></i>
                    <h2>Welcome to SkillPilot</h2>
                    <p>Your advanced prompt engineering training platform</p>
                </div>
            `;
            this.conversationMessages = [];
            this.conversationMemory = []; // Clear conversation context for fresh start
            this.updateMessageCount();
            console.log('Chat and conversation memory cleared');
        }
    }

    exportChat() {
        // jsPDF is loaded from a CDN. If the server has no route to it the
        // library is simply absent, and destructuring it threw an uncaught
        // TypeError -- the button did nothing and said nothing.
        if (!window.jspdf || !window.jspdf.jsPDF) {
            alert('The PDF export library could not be loaded, so the chat '
                + 'cannot be saved as a PDF. This usually means the server '
                + 'cannot reach cdnjs.cloudflare.com. Ask your administrator '
                + 'to allow it, then reload the page.');
            return;
        }

        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        
        const pageWidth = doc.internal.pageSize.getWidth();
        const pageHeight = doc.internal.pageSize.getHeight();
        const margin = 20;
        const maxWidth = pageWidth - (margin * 2);
        let yPos = margin;
        
        doc.setFontSize(18);
        doc.setFont(undefined, 'bold');
        doc.text('Chat Conversation Export', margin, yPos);
        yPos += 10;
        
        doc.setFontSize(10);
        doc.setFont(undefined, 'normal');
        doc.text(`Model: ${this.selectedModel} (${this.selectedVersion})`, margin, yPos);
        yPos += 6;
        doc.text(`Total Cost: $${this.totalCost.toFixed(4)}`, margin, yPos);
        yPos += 6;
        doc.text(`Total Tokens: ${this.totalTokens}`, margin, yPos);
        yPos += 6;
        doc.text(`Exported: ${new Date().toLocaleString()}`, margin, yPos);
        yPos += 12;
        
        doc.setLineWidth(0.5);
        doc.line(margin, yPos, pageWidth - margin, yPos);
        yPos += 8;
        
        this.conversationMessages.forEach((msg, index) => {
            if (yPos > pageHeight - 30) {
                doc.addPage();
                yPos = margin;
            }
            
            doc.setFont(undefined, 'bold');
            doc.setFontSize(11);
            const role = msg.role === 'user' ? 'User' : 'AI';
            doc.text(`${role}:`, margin, yPos);
            yPos += 6;
            
            doc.setFont(undefined, 'normal');
            doc.setFontSize(10);
            
            const cleanText = msg.content.replace(/[*#`\n]/g, ' ').substring(0, 500);
            const lines = doc.splitTextToSize(cleanText, maxWidth);
            
            lines.forEach(line => {
                if (yPos > pageHeight - 20) {
                    doc.addPage();
                    yPos = margin;
                }
                doc.text(line, margin, yPos);
                yPos += 5;
            });
            
            yPos += 4;
            
            if (index < this.conversationMessages.length - 1) {
                doc.setDrawColor(200);
                doc.line(margin, yPos, pageWidth - margin, yPos);
                yPos += 6;
            }
        });
        
        doc.save(`chat-export-${Date.now()}.pdf`);
        this.showNotification('✅ Chat exported as PDF', 'success');
    }

    async startNewSession() {
        try {
            const title = prompt('Enter session title:', `Training ${new Date().toLocaleDateString()}`);
            if (!title) return;

            const response = await fetch('/api/sessions/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ title, user: 'trainer' })
            });

            const data = await response.json();
            if (data.success) {
                this.currentSession = data.session;
                this.showNotification('✅ Session started', 'success');
            }
        } catch (error) {
            console.error('Error starting session:', error);
        }
    }

    async endCurrentSession() {
        if (!this.currentSession) {
            this.showNotification('No active session', 'warning');
            return;
        }

        try {
            await fetch(`/api/sessions/${this.currentSession.id}/end`, { method: 'POST' });
            this.showNotification('✅ Session ended', 'success');
            this.currentSession = null;
        } catch (error) {
            console.error('Error ending session:', error);
        }
    }

    async addMessageToSession(data) {
        if (!this.currentSession) return;

        try {
            await fetch(`/api/sessions/${this.currentSession.id}/message`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    role: 'assistant',
                    content: data.text,
                    model: this.selectedVersion,
                    tokens: data.tokens?.total || 0,
                    cost: this.calculateCost(this.selectedVersion, data.tokens?.input || 0, data.tokens?.output || 0)
                })
            });
        } catch (error) {
            console.error('Error adding to session:', error);
        }
    }

    async loadSessions() {
        try {
            const response = await fetch('/api/sessions/list');
            const data = await response.json();
            
            const container = document.getElementById('sessionsList');
            if (container) {
                container.innerHTML = data.sessions.map(s => `
                    <div class="session-item">
                        <h4>${s.title}</h4>
                        <div style="font-size: 0.9em; color: #666; margin-top: 8px;">
                            <i class="fas fa-calendar"></i> ${new Date(s.started_at).toLocaleString()}<br>
                            <i class="fas fa-message"></i> ${s.messages.length} messages | 
                            <i class="fas fa-dollar-sign"></i> $${s.total_cost.toFixed(4)}
                        </div>
                    </div>
                `).join('');
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
        }
    }

    async loadAnalytics() {
        try {
            const response = await fetch('/api/analytics/dashboard?days=30');
            const data = await response.json();
            
            document.getElementById('statSessions').textContent = data.total_sessions;
            document.getElementById('statMessages').textContent = data.total_messages;
            document.getElementById('statCost').textContent = data.total_cost + '%';
            document.getElementById('statModels').textContent = data.total_tokens;
            
            if (data.lms_stats) {
                const lms = data.lms_stats;
                
                const enrollmentsList = document.getElementById('courseEnrollmentsList');
                if (enrollmentsList && lms.enrollments_by_course) {
                    enrollmentsList.innerHTML = lms.enrollments_by_course.length > 0 
                        ? lms.enrollments_by_course.map(item => `
                            <div style="display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #eee;">
                                <span><i class="fas fa-book"></i> ${item.course}</span>
                                <span class="badge">${item.count} students</span>
                            </div>
                        `).join('')
                        : '<p style="color: #666;">No course enrollments yet.</p>';
                }
                
                const activityList = document.getElementById('recentActivityList');
                if (activityList && lms.recent_activity) {
                    activityList.innerHTML = lms.recent_activity.length > 0
                        ? lms.recent_activity.map(item => `
                            <div style="display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #eee;">
                                <span><i class="fas fa-user"></i> ${item.student} enrolled in <strong>${item.course}</strong></span>
                                <span style="color: #666; font-size: 0.9em;">${item.date ? new Date(item.date).toLocaleDateString() : 'N/A'}</span>
                            </div>
                        `).join('')
                        : '<p style="color: #666;">No recent activity.</p>';
                }
            }
        } catch (error) {
            console.error('Error loading analytics:', error);
        }
    }

    async loadAdminPanel() {
        // The model catalogue panel owns its own rendering and talks to
        // /api/ai-models, which reads and writes the config.yaml catalogue.
        // It replaced a read-only list of providers built from a JSON file.
        if (window.SkpAIModels) {
            window.SkpAIModels.mount('adminAIModelsPanel');
        }

        // Load current prompt suggestion model setting
        try {
            const response = await fetch('/api/admin/models');
            const data = await response.json();
            const currentModel = data.prompt_suggestion_model || 'openai';
            const select = document.getElementById('promptSuggestionModel');
            if (select) {
                select.value = currentModel;
            }
        } catch (error) {
            console.error('Error loading prompt suggestion model:', error);
        }
    }

    async loadMyCertificates() {
        const container = document.getElementById('myCertificatesList');
        if (!container) return;

        try {
            const response = await fetch('/api/survey/my-certificates');
            if (!response.ok) {
                throw new Error('Failed to load certificates');
            }

            const data = await response.json();
            const certificates = data.certificates || [];

            if (certificates.length === 0) {
                container.innerHTML = `
                    <div class="empty-state" style="text-align: center; padding: 40px; color: #666;">
                        <i class="fas fa-certificate" style="font-size: 48px; margin-bottom: 20px; color: #ddd;"></i>
                        <h3>No Certificates Yet</h3>
                        <p>Complete assessments to earn certificates</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = certificates.map(cert => `
                <div class="certificate-card" style="background: white; border-radius: 12px; padding: 24px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #4CAF50;">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div>
                            <div style="color: #666; margin-bottom: 12px;">
                                <div><strong>Certificate Number:</strong> ${cert.certificate_number || 'N/A'}</div>
                                <div><strong>Date:</strong> ${new Date(cert.timestamp).toLocaleDateString()}</div>
                                ${cert.admin_override ? '<div style="color: #ff9800;"><i class="fas fa-shield-alt"></i> Admin Approved</div>' : ''}
                            </div>
                        </div>
                        <div>
                            <a href="/api/survey/${cert.type === 'Entry Survey' ? 'certificate' : 'exit-exam/certificate'}/${cert.id}" 
                               class="btn btn-primary" 
                               target="_blank"
                               style="display: inline-flex; align-items: center; gap: 8px; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 8px; transition: all 0.3s;">
                                <i class="fas fa-download"></i>
                                Download
                            </a>
                        </div>
                    </div>
                </div>
            `).join('');

        } catch (error) {
            console.error('Error loading certificates:', error);
            container.innerHTML = `
                <div class="error-state" style="text-align: center; padding: 40px; color: #dc3545;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 48px; margin-bottom: 20px;"></i>
                    <h3>Error Loading Certificates</h3>
                    <p>${error.message}</p>
                </div>
            `;
        }
    }

async updatePromptSuggestionModel(model) {
        try {
            const response = await fetch('/api/admin/prompt-suggestion-model', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ model: model })
            });

            if (response.status === 401) {
                this.showNotification('Admin authentication required', 'error');
                return;
            }

            const data = await response.json();
            
            if (data.success) {
                this.showNotification(
                    `Prompt suggestions will now use ${model.toUpperCase()}`, 
                    'success'
                );
            } else {
                this.showNotification('Failed to update suggestion model', 'error');
            }
        } catch (error) {
            console.error('Error updating suggestion model:', error);
            this.showNotification('Error updating suggestion model', 'error');
        }
    }

    async runComparison() {
        const prompt = document.getElementById('comparisonPrompt').value;
        if (!prompt) {
            this.showNotification('Please enter a prompt', 'warning');
            return;
        }

        const selectedModels = Array.from(document.querySelectorAll('.comparison-model-checkbox:checked'))
            .map(cb => cb.value);

        if (selectedModels.length === 0) {
            this.showNotification('Please select at least one model', 'warning');
            return;
        }

        const resultsContainer = document.getElementById('comparisonResults');
        resultsContainer.innerHTML = '<div style="text-align:center; padding:20px;"><div class="loading"></div> Running comparison across all selected models...</div>';

        // Run comparison for each model
        const results = [];
        for (const model of selectedModels) {
            try {
                const formData = new FormData();
                formData.append('message', prompt);
                formData.append('api_key', '');

                const response = await fetch(`/api/chat/${model}`, {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();
                results.push({ model, data });

            } catch (error) {
                console.error(`Error with ${model}:`, error);
                results.push({ model, data: { error: error.message } });
            }
        }

        // Display all results with formatted output
        resultsContainer.innerHTML = '';
        results.forEach(({ model, data }) => {
            const resultCard = document.createElement('div');
            resultCard.className = 'comparison-result-card';
            
            const responseContent = data.error 
                ? `<span style="color: #dc3545;">❌ ${data.error}</span>`
                : (typeof marked !== 'undefined' ? marked.parse(data.text || '') : data.text || '');
            
            resultCard.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 2px solid ${data.error ? '#dc3545' : '#667eea'};">
                    <h3 style="margin: 0; display: flex; align-items: center; gap: 10px;">
                        <i class="fas fa-brain" style="color: ${data.error ? '#dc3545' : '#667eea'};"></i> 
                        ${model.toUpperCase()}
                    </h3>
                    ${data.text ? `<span style="font-size: 0.85em; color: #28a745;"><i class="fas fa-check-circle"></i> Success</span>` : ''}
                </div>
                <div class="model-response-content" style="margin: 15px 0; padding: 20px; background: ${data.error ? '#ffe5e5' : '#f8f9fa'}; border-radius: 12px; border-left: 4px solid ${data.error ? '#dc3545' : '#667eea'}; max-height: 400px; overflow-y: auto; line-height: 1.6;">
                    ${responseContent}
                </div>
                <div style="font-size: 0.85em; color: #666; display: flex; justify-content: space-between; margin-top: 10px;">
                    <span><i class="fas fa-microchip"></i> Model: ${data.model || model}</span>
                    ${data.tokens ? `<span><i class="fas fa-coins"></i> Tokens: ${data.tokens}</span>` : ''}
                    ${data.cost ? `<span><i class="fas fa-dollar-sign"></i> Cost: $${data.cost.toFixed(4)}</span>` : ''}
                </div>
            `;
            resultsContainer.appendChild(resultCard);
        });

        this.showNotification(`Comparison completed for ${results.length} models`, 'success');
    }

    // Admin login/logout functions removed - admin authentication handled via /admin-login page

    showNotification(message, type = 'info') {
        // Simple notification (can be enhanced with a proper toast library)
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#4CAF50' : type === 'warning' ? '#ff9800' : '#f44336'};
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    // Admin Settings Handlers
    updateTimeout(value) {
        document.getElementById("timeoutValue").textContent = value + "s";
        this.settings = this.settings || {};
        this.settings.responseTimeout = parseInt(value);
        localStorage.setItem("aiacmate_timeout", value);
        this.showToast(`Response timeout set to ${value} seconds`, "success");
    }

    updateMaxHistory(value) {
        document.getElementById("historyValue").textContent = value;
        this.settings = this.settings || {};
        this.settings.maxHistory = parseInt(value);
        localStorage.setItem("aiacmate_max_history", value);
        this.showToast(`Max conversation history set to ${value}`, "success");
    }

    togglePromptSuggestions(enabled) {
        this.settings = this.settings || {};
        this.settings.promptSuggestionsEnabled = enabled;
        localStorage.setItem("aiacmate_prompt_suggestions", enabled);
        const lightbulb = document.querySelector(".prompt-helper-btn");
        if (lightbulb) {
            lightbulb.style.display = enabled ? "flex" : "none";
        }
        this.showToast(`Prompt suggestions ${enabled ? "enabled" : "disabled"}`, "success");
    }

    toggleAutoSave(enabled) {
        this.settings = this.settings || {};
        this.settings.autoSave = enabled;
        localStorage.setItem("aiacmate_auto_save", enabled);
        this.showToast(`Auto-save ${enabled ? "enabled" : "disabled"}`, "success");
    }

    toggleCostTracking(enabled) {
        this.settings = this.settings || {};
        this.settings.costTracking = enabled;
        localStorage.setItem("aiacmate_cost_tracking", enabled);
        const costDisplay = document.querySelector(".cost-display");
        if (costDisplay) {
            costDisplay.style.display = enabled ? "block" : "none";
        }
        this.showToast(`Cost tracking ${enabled ? "enabled" : "disabled"}`, "success");
    }

    toggleFileUploads(enabled) {
        this.settings = this.settings || {};
        this.settings.fileUploadsEnabled = enabled;
        localStorage.setItem("aiacmate_file_uploads", enabled);
        const fileInput = document.querySelector(".file-upload-btn");
        if (fileInput) {
            fileInput.style.display = enabled ? "flex" : "none";
        }
        this.showToast(`File uploads ${enabled ? "enabled" : "disabled"}`, "success");
    }

    toggleDarkMode(enabled) {
        document.body.classList.toggle("dark-mode", enabled);
        localStorage.setItem("aiacmate_dark_mode", enabled);
        this.showToast(`Dark mode ${enabled ? "enabled" : "disabled"}`, "success");
    }

    updateMaxFileSize(value) {
        document.getElementById("fileSizeValue").textContent = value + "MB";
        this.settings = this.settings || {};
        this.settings.maxFileSize = parseInt(value);
        localStorage.setItem("aiacmate_max_file_size", value);
        this.showToast(`Max file size set to ${value}MB`, "success");
    }

    loadSettings() {
        this.settings = {
            responseTimeout: parseInt(localStorage.getItem("aiacmate_timeout")) || 30,
            maxHistory: parseInt(localStorage.getItem("aiacmate_max_history")) || 50,
            promptSuggestionsEnabled: localStorage.getItem("aiacmate_prompt_suggestions") !== "false",
            autoSave: localStorage.getItem("aiacmate_auto_save") !== "false",
            costTracking: localStorage.getItem("aiacmate_cost_tracking") !== "false",
            fileUploadsEnabled: localStorage.getItem("aiacmate_file_uploads") !== "false",
            darkMode: localStorage.getItem("aiacmate_dark_mode") === "true",
            maxFileSize: parseInt(localStorage.getItem("aiacmate_max_file_size")) || 50
        };

        setTimeout(() => {
            if (document.getElementById("responseTimeout")) {
                document.getElementById("responseTimeout").value = this.settings.responseTimeout;
                document.getElementById("timeoutValue").textContent = this.settings.responseTimeout + "s";
            }
            if (document.getElementById("maxHistory")) {
                document.getElementById("maxHistory").value = this.settings.maxHistory;
                document.getElementById("historyValue").textContent = this.settings.maxHistory;
            }
            if (document.getElementById("enablePromptSuggestions")) {
                document.getElementById("enablePromptSuggestions").checked = this.settings.promptSuggestionsEnabled;
            }
            if (document.getElementById("autoSaveConversations")) {
                document.getElementById("autoSaveConversations").checked = this.settings.autoSave;
            }
            if (document.getElementById("showCostTracking")) {
                document.getElementById("showCostTracking").checked = this.settings.costTracking;
            }
            if (document.getElementById("enableFileUploads")) {
                document.getElementById("enableFileUploads").checked = this.settings.fileUploadsEnabled;
            }
            if (document.getElementById("darkModeToggle")) {
                document.getElementById("darkModeToggle").checked = this.settings.darkMode;
                if (this.settings.darkMode) {
                    document.body.classList.add("dark-mode");
                }
            }
            if (document.getElementById("maxFileSize")) {
                document.getElementById("maxFileSize").value = this.settings.maxFileSize;
                document.getElementById("fileSizeValue").textContent = this.settings.maxFileSize + "MB";
            }
        }, 300);
    }

    // ============================================
    // SURVEY FUNCTIONALITY
    // ============================================
    
    async loadSurveyQuestions() {
        try {
            const response = await fetch('/api/survey/questions');
            const data = await response.json();
            this.surveyData = data;
            return data;
        } catch (error) {
            console.error('Error loading survey questions:', error);
            return null;
        }
    }
    
    setupSurveyEventListeners() {
        const nextBtn = document.getElementById('nextQuestionBtn');
        const prevBtn = document.getElementById('prevQuestionBtn');
        const submitBtn = document.getElementById('submitSurveyBtn');
        
        if (nextBtn && !nextBtn.dataset.listenerAdded) {
            nextBtn.addEventListener('click', () => this.nextQuestion());
            nextBtn.dataset.listenerAdded = 'true';
        }
        if (prevBtn && !prevBtn.dataset.listenerAdded) {
            prevBtn.addEventListener('click', () => this.prevQuestion());
            prevBtn.dataset.listenerAdded = 'true';
        }
        if (submitBtn && !submitBtn.dataset.listenerAdded) {
            submitBtn.addEventListener('click', () => this.submitSurvey());
            submitBtn.dataset.listenerAdded = 'true';
        }
        
        // Auto-load survey when tab is opened
        const surveyTab = document.querySelector('[data-tab="survey"]');
        if (surveyTab && !surveyTab.dataset.surveyListenerAdded) {
            surveyTab.addEventListener('click', () => {
                // Check if UI is already rendered
                const questionsSection = document.getElementById('questionsSection');
                if (questionsSection && questionsSection.style.display === 'none') {
                    this.loadSurvey();
                }
            });
            surveyTab.dataset.surveyListenerAdded = 'true';
        }
    }
    
    async loadSurvey() {
        // Use preloaded data if available, otherwise fetch
        if (!this.surveyQuestions || this.surveyQuestions.length === 0) {
            const surveyData = await this.loadSurveyQuestions();
            if (!surveyData || !surveyData.questions) {
                alert('Failed to load survey questions');
                return;
            }
            this.surveyQuestions = surveyData.questions;
        }
        
        this.surveyAnswers = new Array(this.surveyQuestions.length).fill(null);
        this.currentQuestionIndex = 0;
        
        document.getElementById('questionsSection').style.display = 'block';
        
        this.displayCurrentQuestion();
    }
    
    displayCurrentQuestion() {
        const container = document.getElementById('surveyQuestions');
        const currentQ = this.surveyQuestions[this.currentQuestionIndex];
        const lang = window.i18n ? window.i18n.getCurrentLanguage() : 'en';
        
        console.log('[Survey] Current language:', lang, '| i18n available:', !!window.i18n);
        console.log('[Survey] Question structure:', typeof currentQ.question, '| Options structure:', Array.isArray(currentQ.options) ? 'array' : 'object');
        
        // Get question text and options based on current language
        const questionText = typeof currentQ.question === 'object' ? currentQ.question[lang] : currentQ.question;
        const questionType = currentQ.type || currentQ.question_type || 'rating';
        
        // Handle options - with fallback for true_false questions
        let options = currentQ.options ? (Array.isArray(currentQ.options) ? currentQ.options : currentQ.options[lang]) : [];
        if ((questionType === 'true_false') && (!options || options.length === 0)) {
            options = lang === 'ar' ? ['صحيح', 'خطأ'] : ['True', 'False'];
        }
        
        document.getElementById('currentQuestion').textContent = this.currentQuestionIndex + 1;
        document.getElementById('totalQuestions').textContent = this.surveyQuestions.length;
        const progress = ((this.currentQuestionIndex + 1) / this.surveyQuestions.length) * 100;
        document.getElementById('surveyProgress').style.width = progress + '%';
        
        let inputHtml = '';
        if (questionType === 'text' || questionType === 'long_text') {
            // Text question - show textarea for comments
            const savedValue = this.surveyAnswers[this.currentQuestionIndex] || '';
            inputHtml = `
                <div class="question-options">
                    <textarea 
                        id="textQuestion_${this.currentQuestionIndex}"
                        class="form-control"
                        rows="${questionType === 'long_text' ? 5 : 3}"
                        placeholder="${lang === 'ar' ? 'أدخل إجابتك هنا...' : 'Enter your response here...'}"
                        style="width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; resize: vertical;"
                        data-testid="textarea-question-${this.currentQuestionIndex}"
                    >${savedValue}</textarea>
                </div>
            `;
        } else {
            // Rating/choice question - show radio buttons
            inputHtml = `
                <div class="question-options">
                    ${options.map((option, index) => {
                        const escapedOption = option.replace(/'/g, "\\'").replace(/"/g, '&quot;');
                        return `
                        <div class="option-item">
                            <input 
                                type="radio" 
                                name="question_${this.currentQuestionIndex}" 
                                id="option_${index}" 
                                value="${escapedOption}"
                                ${this.surveyAnswers[this.currentQuestionIndex] === option ? 'checked' : ''}
                            >
                            <label for="option_${index}">${option}</label>
                        </div>
                    `}).join('')}
                </div>
            `;
        }
        
        container.innerHTML = `
            <div class="question-item">
                <div class="question-text">
                    ${this.currentQuestionIndex + 1}. ${questionText}
                    ${questionType === 'text' || questionType === 'long_text' ? '<span style="font-size: 12px; color: #6b7280; margin-left: 8px;">(Optional)</span>' : ''}
                </div>
                ${inputHtml}
            </div>
        `;
        
        // Add event listeners
        if (questionType === 'text' || questionType === 'long_text') {
            const textarea = container.querySelector('textarea');
            if (textarea) {
                textarea.addEventListener('input', (e) => {
                    this.surveyAnswers[this.currentQuestionIndex] = e.target.value;
                });
            }
        } else {
            container.querySelectorAll('input[type="radio"]').forEach(radio => {
                radio.addEventListener('change', (e) => {
                    this.surveyAnswers[this.currentQuestionIndex] = e.target.value;
                });
            });
        }
        
        document.getElementById('prevQuestionBtn').style.display = 
            this.currentQuestionIndex > 0 ? 'inline-flex' : 'none';
        
        const isLastQuestion = this.currentQuestionIndex === this.surveyQuestions.length - 1;
        document.getElementById('nextQuestionBtn').style.display = isLastQuestion ? 'none' : 'inline-flex';
        document.getElementById('submitSurveyBtn').style.display = isLastQuestion ? 'inline-flex' : 'none';
    }
    
    nextQuestion() {
        const currentQ = this.surveyQuestions[this.currentQuestionIndex];
        const questionType = currentQ.type || 'rating';
        
        // Text questions are optional, other types require an answer
        if ((questionType !== 'text' && questionType !== 'long_text') && !this.surveyAnswers[this.currentQuestionIndex]) {
            alert('Please select an answer before proceeding');
            return;
        }
        
        if (this.currentQuestionIndex < this.surveyQuestions.length - 1) {
            this.currentQuestionIndex++;
            this.displayCurrentQuestion();
        }
    }
    
    prevQuestion() {
        if (this.currentQuestionIndex > 0) {
            this.currentQuestionIndex--;
            this.displayCurrentQuestion();
        }
    }
    
    async submitSurvey() {
        // Check for unanswered required questions (text questions are optional)
        const unanswered = this.surveyAnswers.findIndex((a, idx) => {
            const q = this.surveyQuestions[idx];
            const qType = q.type || 'rating';
            // Text questions are optional
            if (qType === 'text' || qType === 'long_text') return false;
            return a === null;
        });
        if (unanswered !== -1) {
            alert(`Please answer question ${unanswered + 1} before submitting`);
            this.currentQuestionIndex = unanswered;
            this.displayCurrentQuestion();
            return;
        }
        
        document.getElementById('questionsSection').style.display = 'none';
        document.getElementById('resultsSection').style.display = 'block';
        
        try {
            const response = await fetch('/api/survey/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    answers: this.surveyAnswers
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.currentUserId = result.user_id;
                this.displaySurveyResults(result);
            } else {
                throw new Error(result.error || 'Failed to submit survey');
            }
        } catch (error) {
            console.error('Error submitting survey:', error);
            document.getElementById('surveyResults').innerHTML = `
                <div class="result-card">
                    <h4><i class="fas fa-exclamation-triangle"></i> Error</h4>
                    <p>Failed to analyze your survey results. Please try again later.</p>
                </div>
            `;
        }
    }
    
    displaySurveyResults(result) {
        const container = document.getElementById('surveyResults');
        const analysis = result.analysis || {};
        
        container.innerHTML = `
            <div class="results-content">
                <div class="result-card">
                    <h4><i class="fas fa-trophy"></i> Your Score</h4>
                    <div class="score-display">${result.score}/10</div>
                    <div class="score-label">${result.correct_count} out of ${result.total_questions} questions correct</div>
                </div>
                
                <div class="result-card">
                    <h4><i class="fas fa-chart-line"></i> Performance Evaluation</h4>
                    <p>${analysis.evaluation || 'Analysis completed successfully.'}</p>
                </div>
                
                <div class="result-card">
                    <h4><i class="fas fa-lightbulb"></i> Recommendations</h4>
                    <ul class="recommendations-list">
                        ${(analysis.recommendations || []).map(rec => `
                            <li><i class="fas fa-check-circle"></i> ${rec}</li>
                        `).join('')}
                    </ul>
                </div>
                
                <div class="result-card">
                    <h4><i class="fas fa-target"></i> Focus Areas</h4>
                    <ul class="recommendations-list">
                        ${(analysis.focus_areas || []).map(area => `
                            <li><i class="fas fa-bullseye"></i> ${area}</li>
                        `).join('')}
                    </ul>
                </div>
                
                <button class="btn-primary download-btn" onclick="app.downloadResultsPDF('${result.user_id}')">
                    <i class="fas fa-download"></i> Download Results PDF
                </button>
                
                <button class="btn-secondary download-btn" onclick="app.resetSurvey()">
                    <i class="fas fa-redo"></i> Take Survey Again
                </button>
            </div>
        `;
    }
    
    downloadResultsPDF(userId) {
        window.location.href = `/api/survey/results/${userId}/pdf`;
    }
    
    resetSurvey() {
        this.surveyQuestions = [];
        this.surveyAnswers = [];
        this.currentQuestionIndex = 0;
        
        document.getElementById('questionsSection').style.display = 'none';
        document.getElementById('resultsSection').style.display = 'none';
        
        // Reload survey questions
        this.loadSurvey();
    }
    
    // ============================================
    // CERTIFICATE MANAGEMENT (ADMIN)
    // ============================================
    
    async refreshSurveyUsers() {
        try {
            const response = await fetch('/api/survey/users');
            const data = await response.json();
            
            const tbody = document.getElementById('certificateUsersTable');
            
            if (!data.users || data.users.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="6" style="text-align: center; padding: 20px;">
                            <i class="fas fa-users"></i> No users have completed the survey yet
                        </td>
                    </tr>
                `;
                return;
            }
            
            tbody.innerHTML = data.users.map(user => {
                const percentage = user.percentage || 0;
                const passStatus = user.pass_status || (percentage >= 60 ? 'passed' : 'failed');
                const certStatus = user.certificate_status || 'pending';
                const adminOverride = user.admin_override || false;
                const canRetake = user.can_retake || false;
                
                return `
                    <tr>
                        <td>${user.user_info.name}</td>
                        <td>${user.user_info.college}</td>
                        <td>${user.user_info.email}</td>
                        <td>${user.score}/10 (${percentage.toFixed(1)}%)</td>
                        <td>
                            <span class="status-badge ${passStatus === 'passed' ? 'pass' : 'fail'}">
                                <i class="fas fa-${passStatus === 'passed' ? 'check-circle' : 'times-circle'}"></i>
                                ${passStatus.toUpperCase()}
                            </span>
                            ${(certStatus === 'pass' || certStatus === 'passed') ? `
                                <span class="status-badge pass">
                                    <i class="fas fa-certificate"></i> CERT ISSUED
                                </span>
                            ` : ''}
                            ${adminOverride ? `
                                <span class="status-badge" style="background: #ff9800;">
                                    <i class="fas fa-shield-alt"></i> ADMIN
                                </span>
                            ` : ''}
                        </td>
                        <td>
                            ${(certStatus === 'pass' || certStatus === 'passed') ? `
                                <button class="generate-cert-btn" onclick="app.generateCertificate('${user.id}')" style="margin: 2px;">
                                    <i class="fas fa-download"></i> Download
                                </button>
                            ` : ''}
                            ${passStatus === 'failed' && (certStatus !== 'pass' && certStatus !== 'passed') ? `
                                <button class="btn-success" onclick="app.forceSurveyCertificate('${user.id}')" style="margin: 2px;">
                                    <i class="fas fa-award"></i> Force Certificate
                                </button>
                            ` : ''}
                            ${!canRetake && (certStatus !== 'pass' && certStatus !== 'passed') ? `
                                <button class="btn-primary" onclick="app.allowSurveyRetake('${user.id}')" style="margin: 2px;">
                                    <i class="fas fa-redo"></i> Allow Retake
                                </button>
                            ` : ''}
                        </td>
                    </tr>
                `;
            }).join('');
            
        } catch (error) {
            console.error('Error loading survey users:', error);
        }
    }
    
    async issueSurveyCertificate(userId) {
        if (!confirm('Issue certificate for this user?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/survey/user/${userId}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status: 'pass' })
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert('Certificate issued successfully!');
                await this.refreshSurveyUsers();
            } else {
                alert('Failed to issue certificate: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error issuing certificate:', error);
            alert('Failed to issue certificate');
        }
    }
    
    generateCertificate(userId) {
        window.location.href = `/api/survey/certificate/${userId}`;
    }
    
    async forceSurveyCertificate(userId) {
        if (!confirm('Force certificate generation for this user? This will override the failing grade.')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/survey/user/${userId}/force-certificate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert('Certificate generation forced successfully!');
                await this.refreshSurveyUsers();
            } else {
                alert('Failed to force certificate: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error forcing certificate:', error);
            alert('Failed to force certificate');
        }
    }
    
    async allowSurveyRetake(userId) {
        if (!confirm('Allow this user to retake the survey?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/survey/user/${userId}/allow-retake`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert('Retake enabled successfully!');
                await this.refreshSurveyUsers();
            } else {
                alert('Failed to enable retake: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error enabling retake:', error);
            alert('Failed to enable retake');
        }
    }
    
    // ===================================
    // SETTINGS FUNCTIONS
    // ===================================
    
    async loadSettings() {
        try {
            const response = await fetch('/api/survey/settings');
            const settings = await response.json();
            
            // Update admin controls
            const surveyToggle = document.getElementById('enableSurvey');
            const exitExamToggle = document.getElementById('enableExitExam');
            
            if (surveyToggle) {
                surveyToggle.checked = settings.survey_enabled !== false;
            }
            if (exitExamToggle) {
                exitExamToggle.checked = settings.exit_exam_enabled !== false;
            }
            
            // Show/hide tabs based on settings
            const surveyTab = document.getElementById('surveyTab');
            const exitExamTab = document.getElementById('exitExamTab');
            
            if (surveyTab) {
                surveyTab.style.display = settings.survey_enabled !== false ? 'inline-block' : 'none';
            }
            if (exitExamTab) {
                exitExamTab.style.display = settings.exit_exam_enabled !== false ? 'inline-block' : 'none';
            }
            
            this.settings = settings;
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }
    
    async toggleSurveyEnabled(enabled) {
        try {
            const response = await fetch('/api/survey/settings', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ survey_enabled: enabled })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Update UI
                const surveyTab = document.getElementById('surveyTab');
                if (surveyTab) {
                    surveyTab.style.display = enabled ? 'inline-block' : 'none';
                }
                this.showNotification(`Survey ${enabled ? 'enabled' : 'disabled'} successfully`, 'success');
            } else {
                alert('Failed to update settings');
            }
        } catch (error) {
            console.error('Error updating settings:', error);
            alert('Failed to update settings');
        }
    }
    
    async toggleExitExamEnabled(enabled) {
        try {
            const response = await fetch('/api/survey/settings', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ exit_exam_enabled: enabled })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Update UI
                const exitExamTab = document.getElementById('exitExamTab');
                if (exitExamTab) {
                    exitExamTab.style.display = enabled ? 'inline-block' : 'none';
                }
                this.showNotification(`Training Evaluation ${enabled ? 'enabled' : 'disabled'} successfully`, 'success');
            } else {
                alert('Failed to update settings');
            }
        } catch (error) {
            console.error('Error updating settings:', error);
            alert('Failed to update settings');
        }
    }
    
    // ===================================
    // EXIT EXAM FUNCTIONS
    // ===================================
    
    async loadExitExamQuestions() {
        try {
            const response = await fetch('/api/survey/exit-exam/questions');
            const data = await response.json();
            this.exitExamData = data;
            return data;
        } catch (error) {
            console.error('Error loading exit exam questions:', error);
            return null;
        }
    }
    
    setupExitExamEventListeners() {
        const nextBtn = document.getElementById('nextExamQuestionBtn');
        const prevBtn = document.getElementById('prevExamQuestionBtn');
        const submitBtn = document.getElementById('submitExamBtn');
        
        if (nextBtn && !nextBtn.hasAttribute('data-listener')) {
            nextBtn.addEventListener('click', () => this.nextExamQuestion());
            nextBtn.setAttribute('data-listener', 'true');
        }
        
        if (prevBtn && !prevBtn.hasAttribute('data-listener')) {
            prevBtn.addEventListener('click', () => this.prevExamQuestion());
            prevBtn.setAttribute('data-listener', 'true');
        }
        
        if (submitBtn && !submitBtn.hasAttribute('data-listener')) {
            submitBtn.addEventListener('click', () => this.submitExitExam());
            submitBtn.setAttribute('data-listener', 'true');
        }
        
        // Auto-load exit exam when tab is opened
        const examTab = document.querySelector('[data-tab="exit-exam"]');
        if (examTab && !examTab.hasAttribute('data-exam-listener')) {
            examTab.addEventListener('click', () => {
                // Check if UI is already rendered
                const examContainer = document.getElementById('examQuestions');
                const examSection = document.getElementById('examQuestionsSection');
                if (examContainer && examContainer.innerHTML.trim() === '') {
                    this.loadExitExam();
                } else if (examSection && examSection.style.display === 'none') {
                    // Questions loaded but hidden, show it
                    examSection.style.display = 'block';
                }
            });
            examTab.setAttribute('data-exam-listener', 'true');
        }
        
        // Auto-load exit survey when tab is opened
        const surveyTab = document.querySelector('[data-tab="exit-survey"]');
        if (surveyTab && !surveyTab.hasAttribute('data-survey-listener')) {
            surveyTab.addEventListener('click', () => {
                // Check if UI is already rendered
                const surveyContainer = document.getElementById('exitSurveyQuestionsContainer');
                if (surveyContainer && surveyContainer.innerHTML.trim() === '') {
                    this.loadExitSurvey();
                }
            });
            surveyTab.setAttribute('data-survey-listener', 'true');
        }
    }
    
    async loadExitExam() {
        // Use preloaded data if available, otherwise fetch
        if (!this.exitExamQuestions || this.exitExamQuestions.length === 0) {
            const examData = await this.loadExitExamQuestions();
            if (!examData || !examData.questions) {
                alert('Failed to load exit exam questions');
                return;
            }
            this.exitExamQuestions = examData.questions;
        }
        
        this.exitExamAnswers = new Array(this.exitExamQuestions.length).fill(null);
        this.currentExamQuestionIndex = 0;
        
        // Show questions section
        document.getElementById('examQuestionsSection').style.display = 'block';
        
        this.renderExamQuestion();
    }
    
    renderExamQuestion() {
        const container = document.getElementById('examQuestions');
        const currentQ = this.exitExamQuestions[this.currentExamQuestionIndex];
        const lang = window.i18n ? window.i18n.getCurrentLanguage() : 'en';
        
        console.log('[Exit Exam] Current language:', lang, '| i18n available:', !!window.i18n);
        console.log('[Exit Exam] Question structure:', typeof currentQ.question, '| Options structure:', Array.isArray(currentQ.options) ? 'array' : 'object');
        
        // Get question text and options based on current language
        const questionText = typeof currentQ.question === 'object' ? currentQ.question[lang] : currentQ.question;
        const options = Array.isArray(currentQ.options) ? currentQ.options : currentQ.options[lang];
        
        document.getElementById('currentExamQuestion').textContent = this.currentExamQuestionIndex + 1;
        document.getElementById('totalExamQuestions').textContent = this.exitExamQuestions.length;
        const progress = ((this.currentExamQuestionIndex + 1) / this.exitExamQuestions.length) * 100;
        document.getElementById('examProgress').style.width = progress + '%';
        
        container.innerHTML = `
            <div class="question-card">
                <h4>Question ${this.currentExamQuestionIndex + 1}</h4>
                <p class="question-text">${questionText}</p>
                <div class="options-container">
                    ${options.map((option, index) => `
                        <label class="option-label">
                            <input 
                                type="radio" 
                                name="exam_question_${this.currentExamQuestionIndex}" 
                                value="${option}"
                                ${this.exitExamAnswers[this.currentExamQuestionIndex] === option ? 'checked' : ''}
                            >
                            <span>${option}</span>
                        </label>
                    `).join('')}
                </div>
            </div>
        `;
        
        // Add event listeners to options
        const radios = container.querySelectorAll('input[type="radio"]');
        radios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.exitExamAnswers[this.currentExamQuestionIndex] = e.target.value;
            });
        });
        
        // Update navigation buttons
        const isLastQuestion = this.currentExamQuestionIndex === this.exitExamQuestions.length - 1;
        document.getElementById('nextExamQuestionBtn').style.display = isLastQuestion ? 'none' : 'inline-flex';
        document.getElementById('submitExamBtn').style.display = isLastQuestion ? 'inline-flex' : 'none';
        document.getElementById('prevExamQuestionBtn').style.display = this.currentExamQuestionIndex > 0 ? 'inline-flex' : 'none';
    }
    
    nextExamQuestion() {
        if (!this.exitExamAnswers[this.currentExamQuestionIndex]) {
            alert('Please select an answer before proceeding');
            return;
        }
        
        if (this.currentExamQuestionIndex < this.exitExamQuestions.length - 1) {
            this.currentExamQuestionIndex++;
            this.renderExamQuestion();
        }
    }
    
    prevExamQuestion() {
        if (this.currentExamQuestionIndex > 0) {
            this.currentExamQuestionIndex--;
            this.renderExamQuestion();
        }
    }
    
    async submitExitExam() {
        // Check if all questions are answered
        const unanswered = this.exitExamAnswers.findIndex(answer => answer === null);
        if (unanswered !== -1) {
            alert(`Please answer question ${unanswered + 1} before submitting`);
            return;
        }
        
        // Show results section with loading
        document.getElementById('examQuestionsSection').style.display = 'none';
        document.getElementById('examResultsSection').style.display = 'block';
        
        try {
            const response = await fetch('/api/survey/exit-exam/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    answers: this.exitExamAnswers
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.displayExitExamResults(result);
            } else {
                alert('Failed to submit exit exam: ' + (result.error || 'Unknown error'));
                document.getElementById('examResultsSection').style.display = 'none';
                document.getElementById('examQuestionsSection').style.display = 'block';
            }
        } catch (error) {
            console.error('Error submitting exit exam:', error);
            alert('Failed to submit exit exam');
            document.getElementById('examResultsSection').style.display = 'none';
            document.getElementById('examQuestionsSection').style.display = 'block';
        }
    }
    
    displayExitExamResults(result) {
        const container = document.getElementById('examResults');
        const percentage = Math.round((result.correct_count / result.total_questions) * 100);
        
        // Determine status based on certificate_status from backend
        // "pending" = passed exam (>=60%), awaiting admin approval
        // "pass" = admin approved, certificate downloadable
        // "fail" = failed exam (<60%)
        const isPending = result.certificate_status === 'pending';
        const isApproved = result.certificate_status === 'pass';
        const isFailed = result.certificate_status === 'fail';
        const passedExam = isPending || isApproved; // Either pending or approved means they passed the exam
        
        // Determine display elements
        let statusIcon, statusText, statusBadge, statusClass, noticeIcon, noticeText, actionButtons;
        
        if (isApproved) {
            statusIcon = 'fa-trophy';
            statusText = 'Congratulations!';
            statusBadge = 'APPROVED';
            statusClass = 'badge-pass';
            noticeIcon = 'fa-certificate';
            noticeText = 'Your certificate has been approved! Click below to download your certificate.';
            actionButtons = `
                <button class="btn-primary" onclick="app.downloadExitExamCertificate('${result.user_id}')">
                    <i class="fas fa-certificate"></i> Download Certificate
                </button>
            `;
        } else if (isPending) {
            statusIcon = 'fa-clock';
            statusText = 'Excellent Work!';
            statusBadge = 'PENDING APPROVAL';
            statusClass = 'badge-pending';
            noticeIcon = 'fa-hourglass-half';
            noticeText = 'You have successfully passed the exam! Your certificate is pending approval from your instructor or administrator. You will be notified once approved.';
            actionButtons = '';
        } else {
            statusIcon = 'fa-times-circle';
            statusText = 'Keep Learning!';
            statusBadge = 'NOT PASSED';
            statusClass = 'badge-fail';
            noticeIcon = 'fa-info-circle';
            noticeText = 'Unfortunately, you did not pass the exit exam. Please contact your instructor or administrator for guidance.';
            actionButtons = '';
        }
        
        container.innerHTML = `
            <div class="results-summary ${passedExam ? 'pass' : 'fail'}">
                <div class="score-display">
                    <i class="fas ${statusIcon} fa-4x"></i>
                    <h2>${statusText}</h2>
                    <h3>Your Score: ${result.score}/10</h3>
                    <p>${result.correct_count} out of ${result.total_questions} correct (${percentage}%)</p>
                    <div class="status-badge ${statusClass}">
                        ${statusBadge}
                    </div>
                </div>
                
                <div class="ai-analysis">
                    <h3><i class="fas fa-robot"></i> AI Analysis</h3>
                    <div class="analysis-content">
                        <h4>Final Evaluation</h4>
                        <p>${result.analysis?.evaluation || 'Analysis not available'}</p>
                        
                        <h4>Recommendations</h4>
                        <ul>
                            ${(result.analysis?.recommendations || []).map(rec => `<li>${rec}</li>`).join('')}
                        </ul>
                        
                        <h4>Focus Areas</h4>
                        <ul>
                            ${(result.analysis?.focus_areas || []).map(area => `<li>${area}</li>`).join('')}
                        </ul>
                    </div>
                </div>
                
                <div class="certificate-notice">
                    <i class="fas ${noticeIcon}"></i>
                    <p>${noticeText}</p>
                </div>
                
                <div class="results-actions">
                    ${actionButtons}
                    <button class="btn-secondary" onclick="location.reload()">
                        <i class="fas fa-home"></i> Return to Home
                    </button>
                </div>
            </div>
        `;
    }
    
    downloadExitExamCertificate(userId) {
        window.location.href = `/api/survey/exit-exam/certificate/${userId}`;
    }
    
    async refreshExitExamUsers() {
        try {
            const response = await fetch('/api/survey/exit-exam/users');
            const data = await response.json();
            
            const tbody = document.getElementById('exitExamUsersTable');
            
            if (!data.users || data.users.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="6" style="text-align: center; padding: 20px;">
                            <i class="fas fa-users"></i> No users have completed the exit exam yet
                        </td>
                    </tr>
                `;
                return;
            }
            
            tbody.innerHTML = data.users.map(user => {
                const percentage = user.percentage || 0;
                const passStatus = user.pass_status || (percentage >= 60 ? 'passed' : 'failed');
                const certStatus = user.certificate_status || 'pending';
                const adminOverride = user.admin_override || false;
                const canRetake = user.can_retake || false;
                const correctCount = user.correct_count || 0;
                const totalQuestions = user.total_questions || 15;
                
                return `
                    <tr>
                        <td>${user.user_info.name}</td>
                        <td>${user.user_info.college}</td>
                        <td>${user.user_info.email}</td>
                        <td>${correctCount}/${totalQuestions} (${percentage.toFixed(1)}%)</td>
                        <td>
                            <span class="status-badge ${passStatus === 'passed' ? 'pass' : 'fail'}">
                                <i class="fas fa-${passStatus === 'passed' ? 'check-circle' : 'times-circle'}"></i>
                                ${passStatus.toUpperCase()}
                            </span>
                            ${(certStatus === 'pass' || certStatus === 'passed') ? `
                                <span class="status-badge pass">
                                    <i class="fas fa-certificate"></i> CERT ISSUED
                                </span>
                            ` : ''}
                            ${adminOverride ? `
                                <span class="status-badge" style="background: #ff9800;">
                                    <i class="fas fa-shield-alt"></i> ADMIN
                                </span>
                            ` : ''}
                        </td>
                        <td>
                            ${(certStatus === 'pass' || certStatus === 'passed') ? `
                                <button class="generate-cert-btn" onclick="app.downloadExitExamCertificate('${user.id}')" data-testid="button-download-certificate-${user.id}" style="margin: 2px; background: #4caf50;">
                                    <i class="fas fa-download"></i> Download Cert
                                </button>
                            ` : ''}
                            ${certStatus === 'pending' && passStatus === 'passed' ? `
                                <button class="generate-cert-btn" onclick="app.approveAndDownloadCertificate('${user.id}')" data-testid="button-approve-download-${user.id}" style="margin: 2px; background: #ff9800;">
                                    <i class="fas fa-check-circle"></i> Approve and Download
                                </button>
                            ` : ''}
                            ${passStatus === 'failed' && (certStatus !== 'pass' && certStatus !== 'passed') ? `
                                <button class="btn-success" onclick="app.forceExitExamCertificate('${user.id}')" data-testid="button-force-certificate-${user.id}" style="margin: 2px;">
                                    <i class="fas fa-award"></i> Force Pass
                                </button>
                            ` : ''}
                            ${canRetake || (certStatus !== 'pass' && certStatus !== 'passed') ? `
                                <button class="btn-primary" onclick="app.allowExitExamRetake('${user.id}')" data-testid="button-allow-retake-${user.id}" style="margin: 2px;">
                                    <i class="fas fa-redo"></i> ${canRetake ? 'Retake Enabled' : 'Allow Retake'}
                                </button>
                            ` : ''}
                        </td>
                    </tr>
                `;
            }).join('');
            
        } catch (error) {
            console.error('Error loading exit exam users:', error);
        }
    }
    
    // ============================================
    // BULK CERTIFICATE CSV GENERATION
    // ============================================
    
    async loadBulkCertCourses() {
        try {
            const response = await fetch('/api/classes/list', {
                credentials: 'include'
            });
            const data = await response.json();
            
            const select = document.getElementById('bulkCertCourseSelect');
            if (!select) return;
            
            const courses = data.courses || data.classes || [];
            
            select.innerHTML = '<option value="">-- Select a Course --</option>' + 
                courses.map(course => `
                    <option value="${course.id}">${course.title || course.name} (${course.code || 'N/A'})</option>
                `).join('');
                
        } catch (error) {
            console.error('Error loading courses for bulk certificates:', error);
            alert('Failed to load courses. Please try again.');
        }
    }
    
    async processBulkCertificateCSV() {
        const courseSelect = document.getElementById('bulkCertCourseSelect');
        const fileInput = document.getElementById('bulkCertCsvFile');
        const resultsDiv = document.getElementById('bulkCertResults');
        const resultsContent = document.getElementById('bulkCertResultsContent');
        const btn = document.getElementById('processBulkCertBtn');
        
        if (!courseSelect.value) {
            alert('Please select a course first');
            return;
        }
        
        if (!fileInput.files || !fileInput.files[0]) {
            alert('Please select a CSV file');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('course_id', courseSelect.value);
        
        // Show loading state
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        
        try {
            const response = await fetch('/admin/api/certificates/csv-generate', {
                method: 'POST',
                credentials: 'include',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Show results
            resultsDiv.style.display = 'block';
            resultsContent.innerHTML = `
                <div style="padding: 15px; background: #e8f5e9; border-radius: 8px; margin-bottom: 15px;">
                    <strong style="color: #2e7d32;">
                        <i class="fas fa-check-circle"></i> ${data.message}
                    </strong>
                    <div style="margin-top: 10px; display: flex; gap: 20px;">
                        <span style="color: #4caf50;"><i class="fas fa-certificate"></i> Generated: ${data.success_count}</span>
                        <span style="color: #ff9800;"><i class="fas fa-exclamation-triangle"></i> Not Found: ${data.not_found_count}</span>
                        <span style="color: #9e9e9e;"><i class="fas fa-minus-circle"></i> Already Issued: ${data.already_issued_count}</span>
                    </div>
                </div>
                <div style="max-height: 300px; overflow-y: auto;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f5f5f5;">
                                <th style="padding: 8px; text-align: left; border-bottom: 1px solid #ddd;">Student Name</th>
                                <th style="padding: 8px; text-align: left; border-bottom: 1px solid #ddd;">Status</th>
                                <th style="padding: 8px; text-align: left; border-bottom: 1px solid #ddd;">Details</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.results.map(r => `
                                <tr>
                                    <td style="padding: 8px; border-bottom: 1px solid #eee;">${r.name}</td>
                                    <td style="padding: 8px; border-bottom: 1px solid #eee;">
                                        <span style="color: ${r.status === 'success' ? '#4caf50' : r.status === 'skipped' ? '#9e9e9e' : '#f44336'};">
                                            <i class="fas fa-${r.status === 'success' ? 'check' : r.status === 'skipped' ? 'minus' : 'times'}"></i>
                                            ${r.status}
                                        </span>
                                    </td>
                                    <td style="padding: 8px; border-bottom: 1px solid #eee; color: #666;">${r.reason || '-'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
            
            // Reset file input
            fileInput.value = '';
            
        } catch (error) {
            console.error('Error processing CSV:', error);
            resultsDiv.style.display = 'block';
            resultsContent.innerHTML = `
                <div style="padding: 15px; background: #ffebee; border-radius: 8px; color: #c62828;">
                    <i class="fas fa-exclamation-circle"></i> Error: ${error.message}
                </div>
            `;
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-cogs"></i> Process CSV & Generate Certificates';
        }
    }
    
    async issueExitExamCertificate(userId) {
        if (!confirm('Issue certificate for this user?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/survey/exit-exam/issue-certificate/${userId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert('Certificate issued successfully!');
                this.refreshExitExamUsers();
            } else {
                alert('Failed to issue certificate: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error issuing certificate:', error);
            alert('Failed to issue certificate');
        }
    }
    
    async forceExitExamCertificate(userId) {
        if (!confirm('Force certificate generation for this user? This will override the failing grade.')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/survey/exit-exam/user/${userId}/force-certificate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert('Certificate generation forced successfully!');
                await this.refreshExitExamUsers();
            } else {
                alert('Failed to force certificate: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error forcing certificate:', error);
            alert('Failed to force certificate');
        }
    }
    
    async allowExitExamRetake(userId) {
        if (!confirm('Allow this user to retake the exit exam?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/survey/exit-exam/user/${userId}/allow-retake`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert('Retake enabled successfully!');
                await this.refreshExitExamUsers();
            } else {
                alert('Failed to allow retake: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error allowing retake:', error);
            alert('Failed to allow retake');
        }
    }
    
    async approveAndDownloadCertificate(userId) {
        if (!confirm('Approve this certificate and download it?')) {
            return;
        }
        
        try {
            // First approve the certificate by changing status to "pass"
            const approveResponse = await fetch(`/api/survey/certificate-status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: userId,
                    exam_type: 'exit_exam',
                    status: 'pass'
                })
            });
            
            const approveResult = await approveResponse.json();
            
            if (approveResult.success) {
                // Refresh the table to show updated status
                await this.refreshExitExamUsers();
                
                // Download the certificate
                window.location.href = `/api/survey/exit-exam/certificate/${userId}`;
                
                alert('Certificate approved and download started!');
            } else {
                alert('Failed to approve certificate: ' + (approveResult.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error approving certificate:', error);
            alert('Failed to approve certificate');
        }
    }
    
    // ============================================
    // EXIT SURVEY FUNCTIONS (FEEDBACK COLLECTION)
    // ============================================
    
    async loadExitSurvey() {
        try {
            // Use preloaded data if available, otherwise fetch
            if (!this.exitSurveyQuestions || this.exitSurveyQuestions.length === 0) {
                const response = await fetch('/api/survey/exit-survey/questions');
                const data = await response.json();
                
                if (!data || !data.questions) {
                    alert('Failed to load exit survey questions');
                    return;
                }
                
                this.exitSurveyQuestions = data.questions;
            }
            
            this.renderExitSurvey();
        } catch (error) {
            console.error('Error loading exit survey:', error);
            alert('Failed to load exit survey');
        }
    }
    
    renderExitSurvey() {
        const container = document.getElementById('exitSurveyQuestionsContainer');
        if (!container) return;
        
        const lang = window.i18n ? window.i18n.getCurrentLanguage() : 'en';
        let currentSection = '';
        let html = '';
        
        this.exitSurveyQuestions.forEach((q, index) => {
            // Get section text based on current language
            const sectionText = typeof q.section === 'object' ? q.section[lang] : q.section;
            
            if (sectionText !== currentSection) {
                if (currentSection !== '') {
                    html += '</div>';
                }
                currentSection = sectionText;
                html += `
                    <div class="survey-section">
                        <h4 class="section-title"><i class="fas fa-folder-open"></i> ${currentSection}</h4>
                `;
            }
            
            // Get question text based on current language
            const questionText = typeof q.question === 'object' ? q.question[lang] : q.question;
            
            html += `<div class="form-group survey-question">`;
            html += `<label class="question-label">${index + 1}. ${questionText}</label>`;
            
            if (q.type === 'rating' || q.type === 'likert') {
                // Get options based on current language
                const options = Array.isArray(q.options) ? q.options : q.options[lang];
                
                html += `<div class="radio-group">`;
                options.forEach(option => {
                    html += `
                        <label class="radio-option">
                            <input type="radio" name="question_${q.id}" value="${option}" data-testid="radio-${q.id}-${option.replace(/\s+/g, '-').toLowerCase()}">
                            <span>${option}</span>
                        </label>
                    `;
                });
                html += `</div>`;
            } else if (q.type === 'text') {
                // Get placeholder based on current language
                const placeholder = typeof q.placeholder === 'object' ? q.placeholder[lang] : (q.placeholder || '');
                
                html += `
                    <textarea 
                        name="question_${q.id}" 
                        class="form-control" 
                        rows="4" 
                        placeholder="${placeholder}"
                        data-testid="textarea-${q.id}">
                    </textarea>
                `;
            }
            
            html += `</div>`;
        });
        
        if (currentSection !== '') {
            html += '</div>';
        }
        
        container.innerHTML = html;
        
        // Show submit button after questions are loaded
        const submitSection = document.getElementById('exitSurveySubmitSection');
        if (submitSection) {
            submitSection.style.display = 'block';
        }
        
        const form = document.getElementById('exitSurveyQuestionsForm');
        if (form && !form.hasAttribute('data-listener')) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitExitSurvey();
            });
            form.setAttribute('data-listener', 'true');
        }
    }
    
    async submitExitSurvey() {
        const formData = new FormData(document.getElementById('exitSurveyQuestionsForm'));
        const responses = {};
        
        this.exitSurveyQuestions.forEach(q => {
            const value = formData.get(`question_${q.id}`);
            responses[q.id] = value || '';
        });
        
        const requiredQuestions = this.exitSurveyQuestions.filter(q => q.type !== 'text');
        const unanswered = requiredQuestions.find(q => !responses[q.id]);
        
        if (unanswered) {
            alert(`Please answer question ${unanswered.id}: ${unanswered.question}`);
            return;
        }
        
        try {
            const response = await fetch('/api/survey/exit-survey/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ responses })
            });
            
            const result = await response.json();
            
            if (result.success) {
                document.getElementById('exitSurveyForm').style.display = 'none';
                document.getElementById('exitSurveyThankYou').style.display = 'block';
            } else {
                alert('Failed to submit survey: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error submitting exit survey:', error);
            alert('Failed to submit survey');
        }
    }
    
    // ============================================
    // Enrollment Management Functions
    // ============================================
    
    async loadEnrollmentManagementDropdowns() {
        try {
            // Load instructors
            const instResponse = await fetch('/api/classes/instructors');
            if (instResponse.ok) {
                const instData = await instResponse.json();
                const instSelect = document.getElementById('enrollInstructorSelect');
                if (instSelect) {
                    instSelect.innerHTML = '<option value="">-- Select Instructor --</option>' +
                        instData.instructors.map(inst => 
                            `<option value="${inst.instructor_id}">${inst.full_name}</option>`
                        ).join('');
                }
            }
            
            // Load classes
            const classResponse = await fetch('/api/classes/list');
            if (classResponse.ok) {
                const classData = await classResponse.json();
                const instructorClassSelect = document.getElementById('enrollInstructorClassSelect');
                const studentClassSelect = document.getElementById('enrollStudentClassSelect');
                const classOptions = '<option value="">-- Select Class --</option>' +
                    classData.classes.map(cls => 
                        `<option value="${cls.class_id}">${cls.title} (${cls.semester})</option>`
                    ).join('');
                
                if (instructorClassSelect) instructorClassSelect.innerHTML = classOptions;
                if (studentClassSelect) studentClassSelect.innerHTML = classOptions;
            }
            
            // Load students (case-insensitive role check)
            const userResponse = await fetch('/api/auth/users');
            if (userResponse.ok) {
                const userData = await userResponse.json();
                const students = userData.users.filter(u => u.role && u.role.toLowerCase() === 'student');
                const studentSelect = document.getElementById('enrollStudentSelect');
                if (studentSelect) {
                    studentSelect.innerHTML = '<option value="">-- Select Student --</option>' +
                        students.map(student => 
                            `<option value="${student.user_id || student.id}">${student.full_name} (${student.email || 'No email'})</option>`
                        ).join('');
                }
            }
        } catch (error) {
            console.error('Error loading enrollment management dropdowns:', error);
        }
    }
    
    async addInstructorToClass() {
        const instructorId = document.getElementById('enrollInstructorSelect').value;
        const classId = document.getElementById('enrollInstructorClassSelect').value;
        const errorDiv = document.getElementById('instructorEnrollError');
        const successDiv = document.getElementById('instructorEnrollSuccess');
        
        errorDiv.style.display = 'none';
        successDiv.style.display = 'none';
        
        if (!instructorId || !classId) {
            errorDiv.textContent = 'Please select both an instructor and a class';
            errorDiv.style.display = 'block';
            return;
        }
        
        try {
            const response = await fetch(`/api/classes/${classId}/add-instructor`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ instructor_id: instructorId })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                successDiv.textContent = 'Instructor added to class successfully';
                successDiv.style.display = 'block';
                if (window.classManager) await window.classManager.loadAllClasses();
            } else {
                errorDiv.textContent = data.error || 'Failed to add instructor to class';
                errorDiv.style.display = 'block';
            }
        } catch (error) {
            errorDiv.textContent = 'Error adding instructor to class';
            errorDiv.style.display = 'block';
        }
    }
    
    async removeInstructorFromClass() {
        const instructorId = document.getElementById('enrollInstructorSelect').value;
        const classId = document.getElementById('enrollInstructorClassSelect').value;
        const errorDiv = document.getElementById('instructorEnrollError');
        const successDiv = document.getElementById('instructorEnrollSuccess');
        
        errorDiv.style.display = 'none';
        successDiv.style.display = 'none';
        
        if (!instructorId || !classId) {
            errorDiv.textContent = 'Please select both an instructor and a class';
            errorDiv.style.display = 'block';
            return;
        }
        
        try {
            const response = await fetch(`/api/classes/${classId}/remove-instructor`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ instructor_id: instructorId })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                successDiv.textContent = 'Instructor removed from class successfully';
                successDiv.style.display = 'block';
                if (window.classManager) await window.classManager.loadAllClasses();
            } else {
                errorDiv.textContent = data.error || 'Failed to remove instructor from class';
                errorDiv.style.display = 'block';
            }
        } catch (error) {
            errorDiv.textContent = 'Error removing instructor from class';
            errorDiv.style.display = 'block';
        }
    }
    
    async addStudentToClass() {
        const studentId = document.getElementById('enrollStudentSelect').value;
        const classId = document.getElementById('enrollStudentClassSelect').value;
        const errorDiv = document.getElementById('studentEnrollError');
        const successDiv = document.getElementById('studentEnrollSuccess');
        
        errorDiv.style.display = 'none';
        successDiv.style.display = 'none';
        
        if (!studentId || !classId) {
            errorDiv.textContent = 'Please select both a student and a class';
            errorDiv.style.display = 'block';
            return;
        }
        
        try {
            const response = await fetch(`/api/classes/${classId}/enroll`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: studentId, status: 'approved' })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                successDiv.textContent = 'Student added to class successfully. Refreshing class details...';
                successDiv.style.display = 'block';
                
                // Refresh class details to show updated student list
                if (window.app.classManager) {
                    await window.app.classManager.viewClassDetails(classId);
                }
                
                // Also refresh the class list if viewing all classes
                if (window.classManager) {
                    await window.classManager.loadAllClasses();
                }
            } else {
                errorDiv.textContent = data.error || 'Failed to add student to class';
                errorDiv.style.display = 'block';
            }
        } catch (error) {
            errorDiv.textContent = 'Error adding student to class';
            errorDiv.style.display = 'block';
        }
    }
    
    async removeStudentFromClass() {
        const studentId = document.getElementById('enrollStudentSelect').value;
        const classId = document.getElementById('enrollStudentClassSelect').value;
        const errorDiv = document.getElementById('studentEnrollError');
        const successDiv = document.getElementById('studentEnrollSuccess');
        
        errorDiv.style.display = 'none';
        successDiv.style.display = 'none';
        
        if (!studentId || !classId) {
            errorDiv.textContent = 'Please select both a student and a class';
            errorDiv.style.display = 'block';
            return;
        }
        
        try {
            // Find the enrollment record
            const enrollmentsResponse = await fetch(`/api/classes/${classId}/enrollments`);
            if (!enrollmentsResponse.ok) {
                throw new Error('Failed to fetch enrollments');
            }
            
            const enrollmentsData = await enrollmentsResponse.json();
            const enrollment = enrollmentsData.enrollments.find(e => e.user_id === studentId);
            
            if (!enrollment) {
                errorDiv.textContent = 'Student is not enrolled in this class';
                errorDiv.style.display = 'block';
                return;
            }
            
            const response = await fetch(`/api/classes/enrollments/${enrollment.enrollment_id}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (response.ok) {
                successDiv.textContent = 'Student removed from class successfully. Refreshing class details...';
                successDiv.style.display = 'block';
                
                // Refresh class details to show updated student list
                if (window.app.classManager) {
                    await window.app.classManager.viewClassDetails(classId);
                }
                
                // Also refresh the class list if viewing all classes
                if (window.classManager) {
                    await window.classManager.loadAllClasses();
                }
            } else {
                errorDiv.textContent = data.error || 'Failed to remove student from class';
                errorDiv.style.display = 'block';
            }
        } catch (error) {
            errorDiv.textContent = 'Error removing student from class';
            errorDiv.style.display = 'block';
        }
    }
}

// Initialize app
const app = new SkillPilot();

// Expose app globally for inline onclick handlers
window.app = app;

// Deep-link to a specific tab via ?tab=<id> in the URL
document.addEventListener('DOMContentLoaded', () => {
    try {
        const params = new URLSearchParams(window.location.search);
        let targetTab = params.get('tab');
        if (!targetTab && window.location.hash) {
            targetTab = window.location.hash.replace(/^#/, '').trim() || null;
        }
        if (targetTab && app && typeof app.switchTab === 'function') {
            setTimeout(() => app.switchTab(targetTab), 400);
        }
    } catch (_) { /* ignore */ }
});

// Expose class manager to app when it's ready
if (window.classManager) {
    app.classManager = window.classManager;
} else {
    // Wait for class manager to initialize
    document.addEventListener('DOMContentLoaded', () => {
        if (window.classManager) {
            app.classManager = window.classManager;
        }
    });
}

// Methods to expose for modal control
app.showCreateInstructorModal = function() {
    if (this.classManager) this.classManager.showCreateInstructorModal();
};

app.closeCreateInstructorModal = function() {
    if (this.classManager) this.classManager.closeCreateInstructorModal();
};

app.showCreateClassModal = function() {
    if (this.classManager) this.classManager.showCreateClassModal();
};

app.closeCreateClassModal = function() {
    if (this.classManager) this.classManager.closeCreateClassModal();
};

app.togglePriceField = function() {
    const pricingTypePaid = document.getElementById('pricingTypePaid');
    const priceFieldGroup = document.getElementById('priceFieldGroup');
    const paymentUrlFieldGroup = document.getElementById('paymentUrlFieldGroup');
    
    if (pricingTypePaid && pricingTypePaid.checked) {
        priceFieldGroup.style.display = 'block';
        if (paymentUrlFieldGroup) paymentUrlFieldGroup.style.display = 'block';
    } else {
        priceFieldGroup.style.display = 'none';
        if (paymentUrlFieldGroup) paymentUrlFieldGroup.style.display = 'none';
    }
};

app.closeClassDetailsModal = function() {
    if (this.classManager) this.classManager.closeClassDetailsModal();
};

// Course context management
app.setCourseContext = function(classId, className) {
    const header = document.getElementById('courseNameHeader');
    const nameSpan = document.getElementById('currentCourseName');
    
    if (header && nameSpan) {
        nameSpan.textContent = className;
        header.style.display = 'block';
        this.currentCourseId = classId;
        this.currentCourseName = className;
    }
};

app.clearCourseContext = function() {
    const header = document.getElementById('courseNameHeader');
    
    if (header) {
        header.style.display = 'none';
        this.currentCourseId = null;
        this.currentCourseName = null;
    }
};

// Load admin settings on startup
app.loadSettings();

// Initialize translations
if (window.i18n) {
    // Translate page on load
    setTimeout(() => {
        window.i18n.translatePage();
    }, 100);
    
    // Re-translate when language changes
    window.addEventListener('languageChanged', () => {
        window.i18n.translatePage();
        
        // Reload current survey/exam to show translated questions
        const activeTab = document.querySelector('.tab-btn.active');
        if (activeTab) {
            const tabName = activeTab.getAttribute('data-tab');
            
            // Reload entry survey if active
            if (tabName === 'entry-survey' && app.surveyQuestions && app.surveyQuestions.length > 0) {
                app.displayCurrentQuestion();
            }
            
            // Reload exit exam if active
            if (tabName === 'exit-exam' && app.exitExamQuestions && app.exitExamQuestions.length > 0) {
                app.renderExamQuestion();
            }
            
            // Reload exit survey if active  
            if (tabName === 'exit-survey' && app.exitSurveyQuestions && app.exitSurveyQuestions.length > 0) {
                app.renderExitSurvey();
            }
        }
    });
}

// File Types Info Button
const showFileTypesBtn = document.getElementById('showFileTypes');
if (showFileTypesBtn) {
    showFileTypesBtn.addEventListener('click', () => {
        document.getElementById('fileTypesModal').style.display = 'flex';
    });
}
