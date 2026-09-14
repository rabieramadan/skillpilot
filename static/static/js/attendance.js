/**
 * Attendance Management Module
 * Daily attendance tracking per class for teachers and admins
 */

class AttendanceManager {
    constructor() {
        this.currentCourseId = null;
        this.currentDate = new Date().toISOString().split('T')[0];
        this.students = [];
    }

    /**
     * Show attendance modal for a course
     */
    async showAttendanceModal(courseId, courseTitle, courseCode) {
        this.currentCourseId = courseId;
        
        const modal = document.createElement('div');
        modal.id = 'attendance-modal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content attendance-modal-content">
                <div class="modal-header">
                    <h2><i class="fas fa-clipboard-list"></i> Daily Attendance / الحضور اليومي</h2>
                    <button class="modal-close" onclick="attendanceManager.closeModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="attendance-header">
                        <div class="course-info">
                            <strong>${courseCode || ''}</strong> - ${courseTitle}
                        </div>
                        <div class="date-selector">
                            <label>Select Date / اختر التاريخ:</label>
                            <input type="date" id="attendance-date" value="${this.currentDate}" 
                                onchange="attendanceManager.loadAttendance()">
                        </div>
                    </div>
                    
                    <div class="attendance-actions">
                        <button class="btn btn-success" onclick="attendanceManager.markAllPresent()">
                            <i class="fas fa-check-double"></i> Mark All Present / تحديد الجميع حاضر
                        </button>
                        <button class="btn btn-primary" onclick="attendanceManager.saveAttendance()">
                            <i class="fas fa-save"></i> Save / حفظ
                        </button>
                        <button class="btn btn-secondary" onclick="attendanceManager.printAttendance()">
                            <i class="fas fa-print"></i> Print / طباعة
                        </button>
                    </div>
                    
                    <div class="attendance-summary" id="attendance-summary">
                        <!-- Summary will be loaded here -->
                    </div>
                    
                    <div class="attendance-table-container">
                        <table class="attendance-table" id="attendance-table">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Student Name / اسم الطالب</th>
                                    <th>Status / الحالة</th>
                                    <th>Notes / ملاحظات</th>
                                </tr>
                            </thead>
                            <tbody id="attendance-tbody">
                                <tr><td colspan="4" class="loading-cell">Loading... / جاري التحميل...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        this.loadAttendance();
    }

    /**
     * Load attendance for the selected date
     */
    async loadAttendance() {
        const dateInput = document.getElementById('attendance-date');
        if (dateInput) {
            this.currentDate = dateInput.value;
        }
        
        const tbody = document.getElementById('attendance-tbody');
        const summaryDiv = document.getElementById('attendance-summary');
        
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading-cell">Loading... / جاري التحميل...</td></tr>';
        }
        
        try {
            const response = await fetch(`/api/attendance/class/${this.currentCourseId}/date/${this.currentDate}`);
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to load attendance');
            }
            
            this.students = data.students;
            
            // Update summary
            if (summaryDiv) {
                const s = data.summary;
                summaryDiv.innerHTML = `
                    <div class="summary-item">
                        <span class="summary-label">Total / الإجمالي:</span>
                        <span class="summary-value">${s.total}</span>
                    </div>
                    <div class="summary-item present">
                        <span class="summary-label">Present / حاضر:</span>
                        <span class="summary-value">${s.present}</span>
                    </div>
                    <div class="summary-item absent">
                        <span class="summary-label">Absent / غائب:</span>
                        <span class="summary-value">${s.absent}</span>
                    </div>
                    <div class="summary-item late">
                        <span class="summary-label">Late / متأخر:</span>
                        <span class="summary-value">${s.late}</span>
                    </div>
                    <div class="summary-item excused">
                        <span class="summary-label">Excused / معذور:</span>
                        <span class="summary-value">${s.excused}</span>
                    </div>
                `;
            }
            
            // Render students
            if (tbody) {
                if (this.students.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" class="empty-cell">No enrolled students / لا يوجد طلاب مسجلين</td></tr>';
                    return;
                }
                
                tbody.innerHTML = this.students.map((student, index) => `
                    <tr data-student-id="${student.id}">
                        <td>${index + 1}</td>
                        <td>
                            <div class="student-name">${student.full_name}</div>
                            <div class="student-name-ar">${student.full_name_ar || ''}</div>
                        </td>
                        <td>
                            <select class="attendance-status" data-student-id="${student.id}" onchange="attendanceManager.updateSummary()">
                                <option value="present" ${student.status === 'present' ? 'selected' : ''}>✓ Present / حاضر</option>
                                <option value="absent" ${student.status === 'absent' ? 'selected' : ''}>✗ Absent / غائب</option>
                                <option value="late" ${student.status === 'late' ? 'selected' : ''}>⏰ Late / متأخر</option>
                                <option value="excused" ${student.status === 'excused' ? 'selected' : ''}>📋 Excused / معذور</option>
                            </select>
                        </td>
                        <td>
                            <input type="text" class="attendance-notes" data-student-id="${student.id}" 
                                value="${student.notes || ''}" placeholder="Notes / ملاحظات">
                        </td>
                    </tr>
                `).join('');
            }
            
        } catch (error) {
            console.error('Load attendance error:', error);
            if (tbody) {
                tbody.innerHTML = `<tr><td colspan="4" class="error-cell">Error: ${error.message}</td></tr>`;
            }
        }
    }

    /**
     * Mark all students as present
     */
    markAllPresent() {
        const selects = document.querySelectorAll('.attendance-status');
        selects.forEach(select => {
            select.value = 'present';
        });
        this.updateSummary();
    }

    /**
     * Update the summary based on current selections
     */
    updateSummary() {
        const selects = document.querySelectorAll('.attendance-status');
        const counts = { present: 0, absent: 0, late: 0, excused: 0, total: selects.length };
        
        selects.forEach(select => {
            counts[select.value] = (counts[select.value] || 0) + 1;
        });
        
        const summaryDiv = document.getElementById('attendance-summary');
        if (summaryDiv) {
            summaryDiv.innerHTML = `
                <div class="summary-item">
                    <span class="summary-label">Total / الإجمالي:</span>
                    <span class="summary-value">${counts.total}</span>
                </div>
                <div class="summary-item present">
                    <span class="summary-label">Present / حاضر:</span>
                    <span class="summary-value">${counts.present}</span>
                </div>
                <div class="summary-item absent">
                    <span class="summary-label">Absent / غائب:</span>
                    <span class="summary-value">${counts.absent}</span>
                </div>
                <div class="summary-item late">
                    <span class="summary-label">Late / متأخر:</span>
                    <span class="summary-value">${counts.late}</span>
                </div>
                <div class="summary-item excused">
                    <span class="summary-label">Excused / معذور:</span>
                    <span class="summary-value">${counts.excused}</span>
                </div>
            `;
        }
    }

    /**
     * Save attendance records
     */
    async saveAttendance() {
        const records = [];
        const rows = document.querySelectorAll('#attendance-tbody tr[data-student-id]');
        
        rows.forEach(row => {
            const studentId = row.dataset.studentId;
            const statusSelect = row.querySelector('.attendance-status');
            const notesInput = row.querySelector('.attendance-notes');
            
            records.push({
                student_id: studentId,
                status: statusSelect ? statusSelect.value : 'present',
                notes: notesInput ? notesInput.value : ''
            });
        });
        
        if (records.length === 0) {
            alert('No attendance records to save');
            return;
        }
        
        try {
            const response = await fetch(`/api/attendance/class/${this.currentCourseId}/date/${this.currentDate}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ records })
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to save attendance');
            }
            
            alert(`Attendance saved successfully!\n${data.created} new records, ${data.updated} updated`);
            this.loadAttendance();
            
        } catch (error) {
            console.error('Save attendance error:', error);
            alert('Error saving attendance: ' + error.message);
        }
    }

    /**
     * Print attendance list
     */
    async printAttendance() {
        try {
            const response = await fetch(`/api/attendance/class/${this.currentCourseId}/print/${this.currentDate}`);
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to get print data');
            }
            
            const printData = data.print_data;
            
            // Create print window
            const printWindow = window.open('', '_blank', 'width=800,height=600');
            
            printWindow.document.write(`
<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">
    <title>Attendance List - ${printData.course.title}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Arial', 'Segoe UI', sans-serif; 
            padding: 20px; 
            color: #333;
            line-height: 1.4;
        }
        .header { 
            text-align: center; 
            margin-bottom: 30px; 
            border-bottom: 2px solid #1B5E20;
            padding-bottom: 15px;
        }
        .logos {
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-bottom: 15px;
        }
        .logos img { height: 60px; }
        .app-name {
            font-size: 18px;
            font-weight: bold;
            color: #1B5E20;
            margin-bottom: 5px;
        }
        .doc-title { 
            font-size: 22px; 
            font-weight: bold; 
            margin: 10px 0;
            color: #333;
        }
        .doc-title-ar {
            font-size: 20px;
            font-weight: bold;
            direction: rtl;
        }
        .course-info { 
            margin: 15px 0; 
            font-size: 14px;
        }
        .course-info strong { color: #1B5E20; }
        .date-info {
            font-size: 14px;
            color: #555;
            margin: 10px 0;
        }
        table { 
            width: 100%; 
            border-collapse: collapse; 
            margin: 20px 0;
            font-size: 12px;
        }
        th, td { 
            border: 1px solid #ddd; 
            padding: 10px 8px; 
            text-align: left;
        }
        th { 
            background-color: #1B5E20; 
            color: white; 
            font-weight: bold;
        }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .status-present { color: #2e7d32; font-weight: bold; }
        .status-absent { color: #c62828; font-weight: bold; }
        .status-late { color: #f57c00; font-weight: bold; }
        .status-excused { color: #1565c0; font-weight: bold; }
        .summary {
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 5px;
        }
        .summary-item {
            text-align: center;
        }
        .summary-label { font-size: 12px; color: #666; }
        .summary-value { font-size: 20px; font-weight: bold; display: block; }
        .summary-item.present .summary-value { color: #2e7d32; }
        .summary-item.absent .summary-value { color: #c62828; }
        .summary-item.late .summary-value { color: #f57c00; }
        .summary-item.excused .summary-value { color: #1565c0; }
        .footer {
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #ddd;
            font-size: 11px;
            color: #666;
            display: flex;
            justify-content: space-between;
        }
        .signature-area {
            margin-top: 40px;
            display: flex;
            justify-content: space-between;
        }
        .signature-box {
            width: 200px;
            text-align: center;
        }
        .signature-line {
            border-top: 1px solid #333;
            margin-top: 40px;
            padding-top: 5px;
            font-size: 12px;
        }
        @media print {
            body { padding: 10px; }
            .no-print { display: none; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="app-name">SkillPilot</div>
        <div class="doc-title">Daily Attendance List</div>
        <div class="doc-title-ar">قائمة الحضور اليومي</div>
    </div>
    
    <div class="course-info">
        <strong>Course / المقرر:</strong> ${printData.course.code ? `[${printData.course.code}]` : ''} ${printData.course.title}
        ${printData.course.title_ar ? ` / ${printData.course.title_ar}` : ''}
    </div>
    
    <div class="date-info">
        <strong>Date / التاريخ:</strong> ${printData.date_formatted}
    </div>
    
    <div class="summary">
        <div class="summary-item">
            <span class="summary-label">Total / الإجمالي</span>
            <span class="summary-value">${printData.summary.total}</span>
        </div>
        <div class="summary-item present">
            <span class="summary-label">Present / حاضر</span>
            <span class="summary-value">${printData.summary.present}</span>
        </div>
        <div class="summary-item absent">
            <span class="summary-label">Absent / غائب</span>
            <span class="summary-value">${printData.summary.absent}</span>
        </div>
        <div class="summary-item late">
            <span class="summary-label">Late / متأخر</span>
            <span class="summary-value">${printData.summary.late}</span>
        </div>
        <div class="summary-item excused">
            <span class="summary-label">Excused / معذور</span>
            <span class="summary-value">${printData.summary.excused}</span>
        </div>
    </div>
    
    <table>
        <thead>
            <tr>
                <th style="width: 40px;">#</th>
                <th>Student Name / اسم الطالب</th>
                <th style="width: 120px;">Status / الحالة</th>
                <th>Notes / ملاحظات</th>
            </tr>
        </thead>
        <tbody>
            ${printData.students.map(s => `
            <tr>
                <td>${s.seq}</td>
                <td>
                    ${s.full_name}${s.full_name_ar ? ` / ${s.full_name_ar}` : ''}
                </td>
                <td class="status-${s.status}">${s.status_display}</td>
                <td>${s.notes || ''}</td>
            </tr>
            `).join('')}
        </tbody>
    </table>
    
    <div class="signature-area">
        <div class="signature-box">
            <div class="signature-line">Instructor Signature / توقيع المدرب</div>
        </div>
        <div class="signature-box">
            <div class="signature-line">Admin Signature / توقيع المسؤول</div>
        </div>
    </div>
    
    <div class="footer">
        <span>Generated: ${printData.generated_at}</span>
        <span>SkillPilot Learning Platform</span>
    </div>
    
    <script>
        window.onload = function() { window.print(); };
    </script>
</body>
</html>
            `);
            
            printWindow.document.close();
            
        } catch (error) {
            console.error('Print attendance error:', error);
            alert('Error printing attendance: ' + error.message);
        }
    }

    /**
     * Close the modal
     */
    closeModal() {
        const modal = document.getElementById('attendance-modal');
        if (modal) {
            modal.remove();
        }
    }
}

// Global instance
const attendanceManager = new AttendanceManager();
