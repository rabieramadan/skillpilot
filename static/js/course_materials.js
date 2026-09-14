// Course Materials Management Module
class CourseMaterialsManager {
    constructor(app) {
        this.app = app;
        this.currentClass = null;
        this.materials = [];
    }

    async loadClasses() {
        try {
            const response = await fetch('/api/classes/list', {
                credentials: 'include'
            });
            
            if (!response.ok) {
                throw new Error('Failed to load classes');
            }
            
            const data = await response.json();
            this.renderClassSelector(data.classes || []);
        } catch (error) {
            console.error('Error loading classes:', error);
            this.showMessage('Failed to load classes', 'error');
        }
    }

    renderClassSelector(classes) {
        const select = document.getElementById('materialClassSelect');
        if (!select) return;

        select.innerHTML = '<option value="">Select a class...</option>' +
            classes.map(cls => `
                <option value="${cls.class_id}">
                    ${this.escapeHtml(cls.class_code)} - ${this.escapeHtml(cls.title)}
                </option>
            `).join('');
    }

    async selectClass(classId) {
        this.currentClass = classId;
        if (classId) {
            await this.loadMaterials(classId);
        } else {
            document.getElementById('materialsListContainer').innerHTML = '';
        }
    }

    async loadMaterials(classId) {
        try {
            const response = await fetch(`/api/materials/class/${classId}`, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                throw new Error('Failed to load materials');
            }
            
            const data = await response.json();
            this.materials = data.files || [];
            this.renderMaterialsList();
        } catch (error) {
            console.error('Error loading materials:', error);
            this.showMessage('Failed to load materials', 'error');
        }
    }

    renderMaterialsList() {
        const container = document.getElementById('materialsListContainer');
        if (!container) return;

        if (this.materials.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #666;">
                    <i class="fas fa-folder-open" style="font-size: 48px; opacity: 0.3;"></i>
                    <p style="margin-top: 16px;">No materials uploaded yet</p>
                </div>
            `;
            return;
        }

        const materialsHTML = `
            <div class="materials-grid">
                ${this.materials.map(material => `
                    <div class="material-card" data-testid="card-material-${material.file_id}">
                        <div class="material-icon">
                            <i class="fas fa-${this.getFileIcon(material.file_type)}"></i>
                        </div>
                        <div class="material-info">
                            <h4>${this.escapeHtml(material.original_filename)}</h4>
                            <p class="material-meta">
                                <span><i class="fas fa-user"></i> ${this.escapeHtml(material.uploaded_by_name)}</span>
                                <span><i class="fas fa-calendar"></i> ${this.formatDate(material.uploaded_at)}</span>
                                <span><i class="fas fa-file"></i> ${material.file_size_mb} MB</span>
                            </p>
                            ${material.description ? `<p class="material-description">${this.escapeHtml(material.description)}</p>` : ''}
                        </div>
                        <div class="material-actions">
                            <button class="btn-icon" onclick="courseMaterialsManager.downloadMaterial('${material.file_id}')" title="Download" data-testid="button-download-${material.file_id}">
                                <i class="fas fa-download"></i>
                            </button>
                            <button class="btn-icon instructor-or-admin-only" onclick="courseMaterialsManager.deleteMaterial('${material.file_id}')" title="Delete" data-testid="button-delete-${material.file_id}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        container.innerHTML = materialsHTML;
        
        // Update role visibility
        if (this.app) {
            this.app.updateRoleUI();
        }
    }

    showUploadForm() {
        if (!this.currentClass) {
            this.showMessage('Please select a class first', 'error');
            return;
        }
        document.getElementById('uploadMaterialModal').classList.add('show');
    }

    async uploadMaterial() {
        const fileInput = document.getElementById('materialFileInput');
        const description = document.getElementById('materialDescription').value.trim();
        
        if (!fileInput.files || fileInput.files.length === 0) {
            this.showMessage('Please select a file', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('class_id', this.currentClass);
        formData.append('description', description);

        try {
            const response = await fetch('/api/materials/upload', {
                method: 'POST',
                credentials: 'include',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to upload file');
            }

            this.showMessage('File uploaded successfully', 'success');
            document.getElementById('uploadMaterialModal').classList.remove('show');
            
            // Reset form
            fileInput.value = '';
            document.getElementById('materialDescription').value = '';
            
            // Reload materials
            await this.loadMaterials(this.currentClass);
        } catch (error) {
            console.error('Error uploading file:', error);
            this.showMessage(error.message, 'error');
        }
    }

    async downloadMaterial(fileId) {
        try {
            window.open(`/api/materials/download/${fileId}`, '_blank');
        } catch (error) {
            console.error('Error downloading file:', error);
            this.showMessage('Failed to download file', 'error');
        }
    }

    async deleteMaterial(fileId) {
        if (!confirm('Are you sure you want to delete this material?')) {
            return;
        }

        try {
            const response = await fetch(`/api/materials/${fileId}`, {
                method: 'DELETE',
                credentials: 'include'
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to delete file');
            }

            this.showMessage('File deleted successfully', 'success');
            await this.loadMaterials(this.currentClass);
        } catch (error) {
            console.error('Error deleting file:', error);
            this.showMessage(error.message, 'error');
        }
    }

    getFileIcon(fileType) {
        const icons = {
            'pdf': 'file-pdf',
            'doc': 'file-word',
            'docx': 'file-word',
            'ppt': 'file-powerpoint',
            'pptx': 'file-powerpoint',
            'xls': 'file-excel',
            'xlsx': 'file-excel',
            'jpg': 'file-image',
            'jpeg': 'file-image',
            'png': 'file-image',
            'gif': 'file-image',
            'mp4': 'file-video',
            'mov': 'file-video',
            'mp3': 'file-audio',
            'zip': 'file-archive',
            'rar': 'file-archive'
        };
        return icons[fileType.toLowerCase()] || 'file';
    }

    formatDate(isoString) {
        const date = new Date(isoString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    showMessage(message, type = 'info') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `flash-message flash-${type}`;
        messageDiv.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;
        document.body.appendChild(messageDiv);

        setTimeout(() => messageDiv.classList.add('show'), 10);
        setTimeout(() => {
            messageDiv.classList.remove('show');
            setTimeout(() => messageDiv.remove(), 300);
        }, 3000);
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return String(text || '').replace(/[&<>"']/g, m => map[m]);
    }
}

// Initialize course materials manager
let courseMaterialsManager;
document.addEventListener('DOMContentLoaded', () => {
    if (window.app) {
        courseMaterialsManager = new CourseMaterialsManager(window.app);
    }
});
