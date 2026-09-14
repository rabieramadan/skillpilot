/**
 * Ethics Certificate Module
 * Handles professional ethics certificates with payment integration
 */

class EthicsCertificate {
    constructor() {
        this.currentSession = null;
        this.currentLevel = null;
        this.currentCategory = null;
        this.currentDomain = null;
        this.currentQuestionNumber = 0;
        this.totalQuestions = 0;
    }

    /**
     * Initialize ethics certificate module
     */
    async init() {
        console.log('Initializing Ethics Certificate module...');
        await this.loadCertificateLevels();
        await this.loadMySessions();
        
        // Listen for language changes
        window.addEventListener('languageChanged', () => {
            console.log('Language changed, refreshing ethics certificate display...');
            this.refresh();
        });
    }

    /**
     * Refresh display after language change
     */
    async refresh() {
        await this.loadCertificateLevels();
        await this.loadMySessions();
    }

    /**
     * Translate domain key to localized label
     */
    getDomainLabel(domainKey) {
        const domainMap = {
            'healthcare': 'ethics_domain_healthcare',
            'business': 'ethics_domain_business',
            'education': 'ethics_domain_education',
            'technology': 'ethics_domain_technology'
        };
        return i18n.t(domainMap[domainKey] || domainKey);
    }

    /**
     * Translate level key to localized label
     * Handles both simple keys like "basic" and composite keys like "general-basic"
     */
    getLevelLabel(levelKey) {
        // Extract complexity from full level ID (e.g., "general-basic" → "basic")
        const complexity = levelKey.includes('-') 
            ? levelKey.split('-').pop() 
            : levelKey;
            
        const levelMap = {
            'basic': 'ethics_level_basic',
            'intermediate': 'ethics_level_intermediate',
            'advanced': 'ethics_level_advanced'
        };
        return i18n.t(levelMap[complexity] || complexity);
    }

    /**
     * Get translated category info
     */
    getCategoryInfo(categoryId) {
        const categoryMap = {
            'general': {
                name: 'ethics_category_general',
                desc: 'ethics_category_general_desc'
            },
            'ai': {
                name: 'ethics_category_ai',
                desc: 'ethics_category_ai_desc'
            }
        };
        const info = categoryMap[categoryId];
        return info ? {
            name: i18n.t(info.name),
            description: i18n.t(info.desc)
        } : null;
    }

    /**
     * Get translated level info
     */
    getLevelInfo(categoryId, complexity) {
        const levelKey = `ethics_level_${complexity}_desc_${categoryId}`;
        const nameKey = `ethics_level_${complexity}_name`;
        return {
            name: i18n.t(nameKey),
            description: i18n.t(levelKey)
        };
    }

    /**
     * Load available certificate categories and levels
     */
    async loadCertificateLevels() {
        try {
            const response = await fetch('/api/ethics/levels', {
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.displayCertificateCategories(data.categories || []);
        } catch (error) {
            console.error('Error loading certificate categories:', error);
            this.showError('ethicsLevelsList', i18n.t('ethics_load_categories_failed'));
        }
    }

    /**
     * Display certificate categories with levels
     */
    displayCertificateCategories(categories) {
        const container = document.getElementById('ethicsLevelsList');
        if (!container) return;

        if (categories.length === 0) {
            container.innerHTML = `<p style="text-align: center; color: #999;">${i18n.t('ethics_no_categories')}</p>`;
            return;
        }

        const html = categories.map(category => {
            const categoryInfo = this.getCategoryInfo(category.id) || { name: category.name, description: category.description };
            return `
            <div class="ethics-category" style="margin-bottom: 30px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px 10px 0 0; color: white;">
                    <h3 style="margin: 0; font-size: 22px;">
                        <i class="fas fa-certificate"></i> ${categoryInfo.name}
                    </h3>
                    <p style="margin: 8px 0 0 0; opacity: 0.95; font-size: 14px;">${categoryInfo.description}</p>
                </div>
                <div style="border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px; padding: 15px; background: #f9f9f9;">
                    ${category.levels.map(level => {
                        const levelInfo = this.getLevelInfo(category.id, level.complexity);
                        return `
                        <div class="ethics-level-card" style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin-bottom: 12px; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div style="flex: 1;">
                                    <h4 style="margin: 0 0 8px 0; color: #333; font-size: 18px;">
                                        <i class="fas fa-award" style="color: #667eea;"></i> ${levelInfo.name}
                                    </h4>
                                    <p style="color: #666; margin: 0 0 10px 0; font-size: 14px;">${levelInfo.description}</p>
                                    <div style="display: flex; gap: 20px; font-size: 13px; color: #888;">
                                        <span><i class="fas fa-tasks"></i> ${level.questions} ${i18n.t('ethics_questions')}</span>
                                        <span><i class="fas fa-dollar-sign"></i> $${level.price.toFixed(2)}</span>
                                        <span><i class="fas fa-signal"></i> ${this.getLevelLabel(level.complexity)}</span>
                                    </div>
                                </div>
                                <button 
                                    class="btn-primary" 
                                    data-testid="button-start-${level.id}"
                                    onclick="ethicsCertificate.startAssessment('${level.id}', '${category.id}')"
                                    style="white-space: nowrap; padding: 10px 20px;"
                                >
                                    <i class="fas fa-play"></i> ${i18n.t('ethics_start_assessment')}
                                </button>
                            </div>
                        </div>
                        `;
                    }).join('')}
                </div>
            </div>
            `;
        }).join('');

        container.innerHTML = html;
    }

    /**
     * Load user's sessions
     */
    async loadMySessions() {
        try {
            const response = await fetch('/api/ethics/my-sessions', {
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.displayMySessions(data.sessions || []);
        } catch (error) {
            console.error('Error loading sessions:', error);
            this.showError('ethicsSessionsList', i18n.t('ethics_load_sessions_failed'));
        }
    }

    /**
     * Display user's sessions
     */
    displayMySessions(sessions) {
        const container = document.getElementById('ethicsSessionsList');
        if (!container) return;

        if (sessions.length === 0) {
            container.innerHTML = `<p style="text-align: center; color: #999;">${i18n.t('ethics_no_sessions')}</p>`;
            return;
        }

        const html = sessions.map(session => {
            const progress = session.total_questions > 0 
                ? Math.round((session.questions_completed / session.total_questions) * 100) 
                : 0;
            
            const statusBadge = session.is_completed 
                ? (session.passed 
                    ? `<span style="background: #4CAF50; color: white; padding: 5px 10px; border-radius: 4px; font-size: 12px;"><i class="fas fa-check-circle"></i> ${i18n.t('ethics_session_passed')}</span>`
                    : `<span style="background: #f44336; color: white; padding: 5px 10px; border-radius: 4px; font-size: 12px;"><i class="fas fa-times-circle"></i> ${i18n.t('ethics_session_failed')}</span>`)
                : `<span style="background: #2196F3; color: white; padding: 5px 10px; border-radius: 4px; font-size: 12px;"><i class="fas fa-clock"></i> ${i18n.t('ethics_session_in_progress')}</span>`;

            const actionButton = session.is_completed && session.passed
                ? `<button class="btn-primary" onclick="window.open('/api/ethics/download-certificate/${session.certificate_id || ''}', '_blank')" data-testid="button-download-cert-${session.session_id}">
                    <i class="fas fa-download"></i> ${i18n.t('ethics_view_certificate')}
                   </button>`
                : (!session.is_completed 
                    ? `<button class="btn-secondary" onclick="ethicsCertificate.resumeSession('${session.session_id}')" data-testid="button-resume-${session.session_id}">
                        <i class="fas fa-play"></i> ${i18n.t('ethics_continue')}
                       </button>`
                    : '');

            return `
                <div class="ethics-session-card" style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin-bottom: 10px; background: white;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1;">
                            <div style="margin-bottom: 8px;">
                                <strong>${this.getLevelLabel(session.level)}</strong> - ${this.getDomainLabel(session.domain)}
                            </div>
                            <div style="font-size: 14px; color: #666; margin-bottom: 8px;">
                                ${session.questions_completed} / ${session.total_questions} (${progress}%)
                                ${session.final_score !== null ? ` | ${i18n.t('certificate_score')}: ${session.final_score}%` : ''}
                            </div>
                            <div style="background: #e0e0e0; height: 6px; border-radius: 3px; overflow: hidden; margin-bottom: 8px;">
                                <div style="width: ${progress}%; height: 100%; background: linear-gradient(90deg, #4CAF50, #45a049);"></div>
                            </div>
                            <div style="font-size: 12px; color: #999;">
                                ${new Date(session.created_at).toLocaleDateString()}
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            ${statusBadge}
                            ${actionButton}
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    }

    /**
     * Start a new assessment
     */
    async startAssessment(levelId, categoryId) {
        console.log('Starting assessment for level:', levelId, 'category:', categoryId);
        
        // Show domain selection modal (simplified version)
        const domain = await this.selectDomain();
        if (!domain) return;

        const userInfo = await this.collectUserInfo();
        if (!userInfo) return;

        // Store category for session tracking
        this.currentCategory = categoryId;

        // Check payment status
        try {
            const paymentCheck = await fetch('/api/ethics/check-payment-status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ level: levelId })
            });

            const paymentData = await paymentCheck.json();

            if (paymentData.payment_required && !paymentData.payment_waived) {
                // Redirect to PayPal payment
                const confirmed = confirm(i18n.t('ethics_payment_confirm') + paymentData.amount + i18n.t('ethics_payment_confirm_continue'));
                if (!confirmed) return;

                await this.processPayment(levelId, paymentData.amount);
                return;
            }

            // Create session
            await this.createSession(levelId, domain, userInfo);

        } catch (error) {
            console.error('Error starting assessment:', error);
            alert(i18n.t('error'));
        }
    }

    /**
     * Select professional domain (simplified)
     */
    async selectDomain() {
        const domain = prompt(i18n.t('ethics_domain_prompt'));
        
        const domainMap = { '1': 'healthcare', '2': 'business', '3': 'education' };
        return domainMap[domain] || null;
    }

    /**
     * Collect user information (simplified)
     */
    async collectUserInfo() {
        return {
            jobTitle: prompt(i18n.t('ethics_job_title') + ':') || i18n.t('ethics_professional'),
            profession: prompt(i18n.t('ethics_profession') + ':') || i18n.t('ethics_general'),
            country: prompt(i18n.t('ethics_country') + ':') || 'US',
            gender: 'prefer-not-to-say',
            educationLevel: 'bachelors',
            language: i18n.currentLanguage
        };
    }

    /**
     * Process PayPal payment (external link)
     */
    async processPayment(levelId, amount) {
        try {
            const response = await fetch('/api/ethics/create-payment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ level: levelId })
            });

            const data = await response.json();

            if (data.success && data.payment_link) {
                // Open PayPal link in new window
                const paymentWindow = window.open(data.payment_link, '_blank');
                
                if (!paymentWindow) {
                    alert(i18n.t('ethics_payment_popup_blocked'));
                    window.open(data.payment_link, '_blank');
                }

                // Show instructions to user
                alert(i18n.t('ethics_payment_instructions_full'));
                
                // Reload sessions to show pending payment
                await this.loadMySessions();
                
            } else {
                alert(i18n.t('ethics_payment_not_configured'));
            }
        } catch (error) {
            console.error('Payment error:', error);
            alert(i18n.t('ethics_payment_failed'));
        }
    }

    /**
     * Create assessment session
     */
    async createSession(levelId, domain, userInfo) {
        try {
            const response = await fetch('/api/ethics/create-session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    level: levelId,
                    domain: domain,
                    ...userInfo
                })
            });

            const data = await response.json();

            if (data.success) {
                this.currentSession = data.session_id;
                this.totalQuestions = data.total_questions;
                this.currentQuestionNumber = 1;
                
                await this.loadNextScenario();
            } else {
                alert(i18n.t('ethics_session_create_failed') + ': ' + (data.error || ''));
            }
        } catch (error) {
            console.error('Error creating session:', error);
            alert(i18n.t('ethics_session_create_error'));
        }
    }

    /**
     * Load next scenario
     */
    async loadNextScenario() {
        document.getElementById('activeAssessmentSection').style.display = 'block';
        document.getElementById('scenarioContent').innerHTML = `<p style="text-align: center;"><i class="fas fa-spinner fa-spin"></i> ${i18n.t('ethics_scenario_loading')}</p>`;
        
        this.updateProgress();

        try {
            const response = await fetch('/api/ethics/generate-scenario', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    session_id: this.currentSession,
                    question_number: this.currentQuestionNumber
                })
            });

            const data = await response.json();

            if (data.success) {
                this.displayScenario(data.scenario);
            } else {
                alert(data.error || i18n.t('error'));
            }
        } catch (error) {
            console.error('Error generating scenario:', error);
            alert(i18n.t('error'));
        }
    }

    /**
     * Display scenario
     */
    displayScenario(scenario) {
        const html = `
            <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                <h4 style="margin-top: 0;">${scenario.question_number}:</h4>
                <p style="line-height: 1.6; color: #333;">${scenario.scenario_text}</p>
            </div>

            <div style="margin-bottom: 20px;">
                <h4>${i18n.t('ethics_select_action')}</h4>
                ${scenario.options.map((option, index) => `
                    <div class="ethics-option" style="border: 1px solid #e0e0e0; border-radius: 6px; padding: 15px; margin-bottom: 10px; cursor: pointer; transition: all 0.2s;" onclick="ethicsCertificate.selectOption(${index})">
                        <strong>${index + 1}:</strong> ${option}
                    </div>
                `).join('')}
            </div>

            <button class="btn-primary" id="submitAnswerBtn" style="width: 100%;" disabled data-testid="button-submit-answer">
                <i class="fas fa-check"></i> ${i18n.t('ethics_submit_answer')}
            </button>
        `;

        document.getElementById('scenarioContent').innerHTML = html;
    }

    /**
     * Select option
     */
    selectOption(optionIndex) {
        // Remove previous selection
        document.querySelectorAll('.ethics-option').forEach(opt => {
            opt.style.background = 'white';
            opt.style.borderColor = '#e0e0e0';
        });

        // Mark selected
        const options = document.querySelectorAll('.ethics-option');
        options[optionIndex].style.background = '#e3f2fd';
        options[optionIndex].style.borderColor = '#2196F3';

        // Enable submit button
        const submitBtn = document.getElementById('submitAnswerBtn');
        submitBtn.disabled = false;
        submitBtn.onclick = () => this.submitAnswer(optionIndex);
    }

    /**
     * Submit answer
     */
    async submitAnswer(userChoice) {
        try {
            const response = await fetch('/api/ethics/submit-answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    session_id: this.currentSession,
                    question_number: this.currentQuestionNumber,
                    user_choice: userChoice
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showFeedback(data.evaluation);
            } else {
                alert(i18n.t('ethics_answer_submit_failed') + ': ' + (data.error || ''));
            }
        } catch (error) {
            console.error('Error submitting answer:', error);
            alert(i18n.t('ethics_answer_submit_failed'));
        }
    }

    /**
     * Show feedback
     */
    showFeedback(evaluation) {
        const html = `
            <div style="background: #f0f8ff; border: 2px solid #2196F3; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h4 style="margin-top: 0; color: #2196F3;"><i class="fas fa-info-circle"></i> ${i18n.t('ethics_evaluation')}</h4>
                <div style="font-size: 24px; font-weight: bold; margin-bottom: 10px;">${i18n.t('ethics_your_score')}: ${evaluation.score}/100</div>
                <p style="line-height: 1.6;">${evaluation.feedback}</p>
                ${evaluation.correct_action ? `<p><strong>${i18n.t('ethics_correct_action')}:</strong> ${evaluation.correct_action}</p>` : ''}
            </div>

            <button class="btn-primary" onclick="ethicsCertificate.nextQuestion()" style="width: 100%;" data-testid="button-next-question">
                <i class="fas fa-arrow-right"></i> ${i18n.t('ethics_next_question')}
            </button>
        `;

        document.getElementById('scenarioContent').innerHTML = html;
    }

    /**
     * Move to next question
     */
    async nextQuestion() {
        this.currentQuestionNumber++;

        if (this.currentQuestionNumber > this.totalQuestions) {
            await this.completeAssessment();
        } else {
            await this.loadNextScenario();
        }
    }

    /**
     * Complete assessment
     */
    async completeAssessment() {
        try {
            const response = await fetch('/api/ethics/complete-session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ session_id: this.currentSession })
            });

            const data = await response.json();

            if (data.success) {
                const resultHtml = `
                    <div style="text-align: center; padding: 40px;">
                        <i class="fas fa-${data.passed ? 'check-circle' : 'times-circle'} fa-4x" style="color: ${data.passed ? '#4CAF50' : '#f44336'};"></i>
                        <h2 style="margin: 20px 0;">${data.message}</h2>
                        <div style="font-size: 32px; font-weight: bold; margin: 20px 0;">${i18n.t('ethics_total_score')}: ${data.final_score}%</div>
                        ${data.certificate_id ? `<button class="btn-primary" onclick="window.open('/api/ethics/download-certificate/${data.certificate_id}', '_blank')" data-testid="button-download-final-cert">
                            <i class="fas fa-download"></i> ${i18n.t('btn_download_certificate')}
                        </button>` : ''}
                    </div>
                `;

                document.getElementById('scenarioContent').innerHTML = resultHtml;
                
                // Reload sessions
                await this.loadMySessions();
            }
        } catch (error) {
            console.error('Error completing assessment:', error);
            alert(i18n.t('ethics_complete_failed'));
        }
    }

    /**
     * Resume session
     */
    async resumeSession(sessionId) {
        // Implementation for resuming sessions
        alert(i18n.t('ethics_continue'));
    }

    /**
     * Update progress bar
     */
    updateProgress() {
        const progress = Math.round((this.currentQuestionNumber / this.totalQuestions) * 100);
        document.getElementById('progressText').textContent = `${this.currentQuestionNumber} / ${this.totalQuestions}`;
        document.getElementById('progressBar').style.width = `${progress}%`;
    }

    /**
     * Show error
     */
    showError(containerId, message) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `<p style="text-align: center; color: #f44336;">${message}</p>`;
        }
    }
}

// Initialize ethics certificate as global object
window.ethicsCertificate = new EthicsCertificate();
