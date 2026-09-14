/**
 * Admin Ethics Certificate Settings Module
 * Handles Ethics Certificate admin controls
 */

class AdminEthicsSettings {
    constructor() {
        this.settings = null;
        this.classes = [];
    }

    /**
     * Initialize admin Ethics settings
     */
    async init() {
        console.log('Initializing Admin Ethics Settings...');
        await this.loadSettings();
        await this.loadPendingPayments();
    }

    /**
     * Load Ethics Certificate settings
     */
    async loadSettings() {
        try {
            const response = await fetch('/api/ethics/admin/class-settings', {
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.settings = data.settings;
            this.classes = data.classes || [];
            
            // Update UI
            this.renderClassCheckboxes();
            this.updateModuleToggle();
            this.updatePayPalEmail();
            
        } catch (error) {
            console.error('Error loading ethics settings:', error);
        }
    }

    /**
     * Update PayPal link field
     */
    updatePayPalEmail() {
        const linkInput = document.getElementById('paypalPaymentLink');
        if (linkInput && this.settings) {
            linkInput.value = this.settings.paypal_payment_link || '';
        }
    }

    /**
     * Render class checkboxes
     */
    renderClassCheckboxes() {
        const container = document.getElementById('ethicsClassesCheckboxes');
        if (!container) return;

        const enabledClasses = this.settings?.enabled_classes || [];

        if (this.classes.length === 0) {
            container.innerHTML = '<p style="color: #999;">No classes available</p>';
            return;
        }

        const html = this.classes.map(cls => {
            const isChecked = enabledClasses.includes(cls.class_id);
            return `
                <div style="padding: 8px 0;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input 
                            type="checkbox" 
                            value="${cls.class_id}" 
                            ${isChecked ? 'checked' : ''} 
                            data-testid="checkbox-ethics-class-${cls.class_id}"
                            style="margin-right: 10px;"
                        />
                        <span>
                            <strong>${cls.title}</strong>
                            ${cls.course_type ? `<span style="margin-left: 8px; padding: 2px 8px; background: #e0f7fa; color: #006064; border-radius: 4px; font-size: 12px;">${cls.course_type}</span>` : ''}
                        </span>
                    </label>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    }

    /**
     * Update module toggle state
     */
    updateModuleToggle() {
        const toggle = document.getElementById('enableEthicsCertificate');
        if (toggle && this.settings) {
            toggle.checked = this.settings.module_enabled !== false;
        }
    }

    /**
     * Toggle Ethics Certificate module
     */
    async toggleModule(enabled) {
        try {
            const response = await fetch('/api/ethics/admin/class-settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    module_enabled: enabled
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            console.log('Ethics Certificate module', enabled ? 'enabled' : 'disabled');
            this.showMessage('Module ' + (enabled ? 'enabled' : 'disabled') + ' successfully', 'success');
            
        } catch (error) {
            console.error('Error toggling module:', error);
            this.showMessage('Failed to update module status', 'error');
        }
    }

    /**
     * Save class settings
     */
    async saveClassSettings() {
        try {
            const container = document.getElementById('ethicsClassesCheckboxes');
            const checkboxes = container.querySelectorAll('input[type="checkbox"]');
            const enabledClasses = Array.from(checkboxes)
                .filter(cb => cb.checked)
                .map(cb => cb.value);

            const response = await fetch('/api/ethics/admin/class-settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    enabled_classes: enabledClasses,
                    all_for_course_type: true
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            this.showMessage('Class settings saved successfully', 'success');
            
        } catch (error) {
            console.error('Error saving class settings:', error);
            this.showMessage('Failed to save class settings', 'error');
        }
    }

    /**
     * Save PayPal settings
     */
    async savePayPalSettings() {
        try {
            const linkInput = document.getElementById('paypalPaymentLink');
            const paypalLink = linkInput?.value?.trim() || '';

            if (!paypalLink) {
                this.showMessage('Please enter a PayPal payment link', 'error');
                return;
            }

            // Validate URL format
            try {
                new URL(paypalLink);
            } catch (e) {
                this.showMessage('Please enter a valid URL (must start with http:// or https://)', 'error');
                return;
            }

            const response = await fetch('/api/ethics/admin/class-settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    paypal_payment_link: paypalLink
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            this.showMessage('PayPal payment link saved successfully', 'success');
            
        } catch (error) {
            console.error('Error saving PayPal settings:', error);
            this.showMessage('Failed to save PayPal settings', 'error');
        }
    }

    /**
     * Load pending payments (both course enrollments and ethics certificate)
     */
    async loadPendingPayments() {
        try {
            // Load both course enrollments and ethics payments in parallel
            const [enrollmentsResponse, ethicsPaymentsResponse] = await Promise.all([
                fetch('/api/classes/enrollments', { credentials: 'include' }),
                fetch('/api/ethics/admin/pending-payments', { credentials: 'include' })
            ]);

            const enrollmentsData = enrollmentsResponse.ok ? await enrollmentsResponse.json() : { enrollments: [] };
            const ethicsData = ethicsPaymentsResponse.ok ? await ethicsPaymentsResponse.json() : { payments: [] };

            const coursePayments = (enrollmentsData.enrollments || []).filter(e => 
                e.enrollment_status === 'pending_payment' || !e.payment_verified
            );

            const ethicsPayments = ethicsData.payments || [];

            // Store all payments for filtering
            this.allEnrollments = coursePayments;
            this.allEthicsPayments = ethicsPayments;
            
            this.renderPendingPayments(coursePayments, ethicsPayments);
            
        } catch (error) {
            console.error('Error loading pending payments:', error);
            const container = document.getElementById('pendingPaymentsList');
            if (container) {
                container.innerHTML = '<p style="color: #f44336;">Failed to load pending payments</p>';
            }
        }
    }

    /**
     * Render pending payments (both course and ethics)
     */
    renderPendingPayments(coursePayments, ethicsPayments) {
        const container = document.getElementById('pendingPaymentsList');
        if (!container) return;

        const totalPending = coursePayments.length + ethicsPayments.length;

        if (totalPending === 0) {
            container.innerHTML = '<p style="color: #999;">No pending payments</p>';
            return;
        }

        // Render Ethics Certificate Payments Section
        let ethicsHtml = '';
        if (ethicsPayments.length > 0) {
            ethicsHtml = `
                <div style="margin-bottom: 30px;">
                    <h4 style="margin-bottom: 15px;"><i class="fas fa-certificate"></i> Ethics Certificate Payments (${ethicsPayments.length})</h4>
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f5f5f5;">
                                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Student</th>
                                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Certificate Level</th>
                                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Amount</th>
                                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Date</th>
                                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${ethicsPayments.map(payment => `
                                <tr data-testid="row-ethics-payment-${payment.payment_id}">
                                    <td style="padding: 10px; border: 1px solid #ddd;">
                                        ${payment.user_name || 'Unknown'}
                                        ${payment.user_email ? `<br><small style="color: #666;">${payment.user_email}</small>` : ''}
                                    </td>
                                    <td style="padding: 10px; border: 1px solid #ddd;">${payment.description || payment.level}</td>
                                    <td style="padding: 10px; border: 1px solid #ddd;">$${payment.amount.toFixed(2)} ${payment.currency}</td>
                                    <td style="padding: 10px; border: 1px solid #ddd;">${new Date(payment.created_at).toLocaleString()}</td>
                                    <td style="padding: 10px; border: 1px solid #ddd;">
                                        <button 
                                            class="btn-success" 
                                            onclick="window.adminEthicsSettings.verifyEthicsPayment('${payment.payment_id}')"
                                            data-testid="button-verify-payment-${payment.payment_id}"
                                            style="padding: 6px 12px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer;"
                                        >
                                            <i class="fas fa-check"></i> Verify Payment
                                        </button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }

        // Course Enrollments Section
        if (coursePayments.length > 0) {
            const uniqueClasses = [...new Set(coursePayments.map(p => p.course_title))].sort();
            
            courseHtml = `
                <div>
                    <h4 style="margin-bottom: 15px;"><i class="fas fa-graduation-cap"></i> Course Enrollments (${coursePayments.length})</h4>
                    <div style="margin-bottom: 15px; display: flex; gap: 10px; align-items: center;">
                        <input 
                            type="text" 
                            id="studentSearchInput" 
                            placeholder="Search by student name..." 
                            style="padding: 8px; width: 300px; border: 1px solid #ddd; border-radius: 4px;"
                            data-testid="input-student-search"
                            oninput="window.adminEthicsSettings.filterPayments()"
                        />
                        <select 
                            id="classFilterSelect" 
                            style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;"
                            data-testid="select-class-filter"
                            onchange="window.adminEthicsSettings.filterPayments()"
                        >
                            <option value="">All Classes</option>
                            ${uniqueClasses.map(cls => `<option value="${cls}">${cls}</option>`).join('')}
                        </select>
                    </div>
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f5f5f5;">
                                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Student</th>
                                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Class</th>
                                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Price</th>
                                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Enrolled Date</th>
                                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${coursePayments.map(payment => `
                                <tr data-testid="row-enrollment-${payment.user_id}">
                                    <td style="padding: 10px; border: 1px solid #ddd;">
                                        ${payment.student_name || 'Unknown Student'}
                                        ${payment.student_username ? `<br><small style="color: #666;">(${payment.student_username})</small>` : ''}
                                    </td>
                                    <td style="padding: 10px; border: 1px solid #ddd;">
                                        ${payment.course_title || 'Unknown Course'}
                                        ${payment.course_code ? `<br><small style="color: #666;">${payment.course_code}</small>` : ''}
                                    </td>
                                    <td style="padding: 10px; border: 1px solid #ddd;">
                                        ${payment.pricing_type === 'paid' ? `${payment.price} OMR` : 'Free'}
                                    </td>
                                    <td style="padding: 10px; border: 1px solid #ddd;">
                                        ${payment.enrollment_date_formatted || 'N/A'}
                                    </td>
                                    <td style="padding: 10px; border: 1px solid #ddd;">
                                        <button 
                                            class="btn-success" 
                                            onclick="window.adminEthicsSettings.verifyPayment('${payment.user_id}', '${payment.class_id}')"
                                            data-testid="button-verify-payment-${payment.user_id}"
                                            style="padding: 6px 12px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer;"
                                        >
                                            <i class="fas fa-check"></i> Verify Payment
                                        </button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }

        // Combine both sections
        container.innerHTML = ethicsHtml + courseHtml;
    }

    /**
     * Filter course payments based on search and class filter
     */
    filterPayments() {
        const searchInput = document.getElementById('studentSearchInput');
        const classSelect = document.getElementById('classFilterSelect');
        
        if (!searchInput || !classSelect || !this.allEnrollments) return;

        const searchTerm = searchInput.value.toLowerCase();
        const selectedClass = classSelect.value;

        let filtered = this.allEnrollments.filter(payment => {
            const matchesSearch = !searchTerm || 
                (payment.student_name && payment.student_name.toLowerCase().includes(searchTerm)) ||
                (payment.student_username && payment.student_username.toLowerCase().includes(searchTerm));
            
            const matchesClass = !selectedClass || payment.course_title === selectedClass;

            return matchesSearch && matchesClass;
        });

        // Keep ethics payments unchanged
        this.renderPendingPayments(filtered, this.allEthicsPayments || []);
    }

    /**
     * Sort payments by column
     */
    sortPayments(column) {
        if (!this.allEnrollments) return;

        // Toggle sort direction
        if (this.sortColumn === column) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = column;
            this.sortDirection = 'asc';
        }

        const sorted = [...this.allEnrollments].sort((a, b) => {
            let valA = a[column] || '';
            let valB = b[column] || '';

            if (column === 'enrollment_date_formatted') {
                valA = new Date(a.enrolled_at || 0);
                valB = new Date(b.enrolled_at || 0);
            }

            if (valA < valB) return this.sortDirection === 'asc' ? -1 : 1;
            if (valA > valB) return this.sortDirection === 'asc' ? 1 : -1;
            return 0;
        });

        // Keep ethics payments unchanged
        this.renderPendingPayments(sorted, this.allEthicsPayments || []);
    }

    /**
     * Verify ethics certificate payment
     */
    async verifyEthicsPayment(paymentId) {
        try {
            const response = await fetch(`/api/ethics/admin/verify-payment/${paymentId}`, {
                method: 'POST',
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            this.showMessage('Ethics payment verified successfully', 'success');
            await this.loadPendingPayments(); // Refresh the list
            
        } catch (error) {
            console.error('Error verifying ethics payment:', error);
            this.showMessage('Failed to verify ethics payment', 'error');
        }
    }

    /**
     * Verify course enrollment payment
     */
    async verifyPayment(userId, classId) {
        try {
            const response = await fetch('/api/classes/verify-payment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    user_id: userId,
                    class_id: classId
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            this.showMessage('Payment verified successfully', 'success');
            await this.loadPendingPayments(); // Refresh the list
            
        } catch (error) {
            console.error('Error verifying payment:', error);
            this.showMessage('Failed to verify payment', 'error');
        }
    }

    /**
     * Show message to admin
     */
    showMessage(message, type) {
        console.log(`[${type.toUpperCase()}] ${message}`);
        // Could enhance this with a toast notification system
        alert(message);
    }
}

// Initialize global instance
window.adminEthicsSettings = new AdminEthicsSettings();
