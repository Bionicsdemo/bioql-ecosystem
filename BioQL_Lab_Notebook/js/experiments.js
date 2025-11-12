// Experiment Management Module

export class ExperimentManager {
    constructor(api) {
        this.api = api;
        this.experiments = [];
        this.filteredExperiments = [];
    }

    async loadExperiments() {
        try {
            this.experiments = await this.api.getExperiments();
            this.filteredExperiments = [...this.experiments];
            this.renderExperiments();
        } catch (error) {
            console.error('Error loading experiments:', error);
            this.renderError();
        }
    }

    renderExperiments() {
        const container = document.getElementById('experimentsList');

        if (!container) return;

        if (this.filteredExperiments.length === 0) {
            container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 2rem;">No experiments found</p>';
            return;
        }

        container.innerHTML = this.filteredExperiments.map(exp => this.createExperimentCard(exp)).join('');

        // Add click handlers
        container.querySelectorAll('.experiment-card').forEach((card, index) => {
            card.addEventListener('click', () => {
                window.location.href = `experiment.html?id=${this.filteredExperiments[index].id}`;
            });
        });
    }

    createExperimentCard(experiment) {
        const tags = experiment.tags || [];
        const statusClass = experiment.status.toLowerCase().replace(' ', '-');

        return `
            <div class="experiment-card" data-id="${experiment.id}">
                <div class="experiment-card-header">
                    <div>
                        <h3>${experiment.title}</h3>
                        <div class="experiment-tags">
                            ${tags.map(tag => `<span class="experiment-tag">${tag}</span>`).join('')}
                        </div>
                    </div>
                    <span class="experiment-status ${statusClass}">${experiment.status}</span>
                </div>
                <div class="experiment-card-body">
                    <p class="experiment-description">${experiment.description || 'No description'}</p>
                </div>
                <div class="experiment-card-footer">
                    <span class="experiment-date">${this.formatDate(experiment.date)}</span>
                </div>
            </div>
        `;
    }

    filterExperiments(searchTerm, status) {
        this.filteredExperiments = this.experiments.filter(exp => {
            const matchesSearch = !searchTerm ||
                exp.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                (exp.description && exp.description.toLowerCase().includes(searchTerm.toLowerCase()));

            const matchesStatus = status === 'all' || exp.status.toLowerCase() === status.toLowerCase();

            return matchesSearch && matchesStatus;
        });

        this.renderExperiments();
    }

    filterByTag(tagName) {
        this.filteredExperiments = this.experiments.filter(exp => {
            return exp.tags && exp.tags.includes(tagName);
        });

        this.renderExperiments();
    }

    renderError() {
        const container = document.getElementById('experimentsList');
        if (container) {
            container.innerHTML = '<p style="color: var(--error-color); text-align: center; padding: 2rem;">Error loading experiments</p>';
        }
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }
}

// Experiment Detail Page
export class ExperimentDetail {
    constructor(api) {
        this.api = api;
        this.experimentId = this.getExperimentId();
        this.experiment = null;
        this.init();
    }

    getExperimentId() {
        const params = new URLSearchParams(window.location.search);
        return params.get('id');
    }

    async init() {
        if (!this.experimentId) {
            // New experiment
            this.setupNewExperiment();
        } else {
            // Load existing experiment
            await this.loadExperiment();
        }

        this.setupTabs();
        this.setupProtocolSteps();
        this.setupSaveHandler();
        this.setupAttachments();
    }

    async loadExperiment() {
        try {
            this.experiment = await this.api.getExperiment(this.experimentId);
            this.populateForm();
        } catch (error) {
            console.error('Error loading experiment:', error);
            alert('Error loading experiment');
        }
    }

    setupNewExperiment() {
        this.experiment = {
            title: '',
            date: new Date().toISOString().split('T')[0],
            status: 'planning',
            tags: [],
            objective: '',
            hypothesis: '',
            materials: '',
            protocol: [{ description: '' }],
            observations: '',
            analysis: '',
            conclusions: '',
            notes: ''
        };
        this.populateForm();
    }

    populateForm() {
        if (!this.experiment) return;

        document.getElementById('experimentTitle').value = this.experiment.title || '';
        document.getElementById('experimentDate').value = this.experiment.date || new Date().toISOString().split('T')[0];
        document.getElementById('experimentStatus').value = this.experiment.status || 'planning';
        document.getElementById('experimentTags').value = (this.experiment.tags || []).join(', ');
        document.getElementById('objective').value = this.experiment.objective || '';
        document.getElementById('hypothesis').value = this.experiment.hypothesis || '';
        document.getElementById('materials').value = this.experiment.materials || '';
        document.getElementById('observations').value = this.experiment.observations || '';
        document.getElementById('analysis').value = this.experiment.analysis || '';
        document.getElementById('conclusions').value = this.experiment.conclusions || '';
        document.getElementById('additionalNotes').value = this.experiment.notes || '';
    }

    setupTabs() {
        const tabs = document.querySelectorAll('.tab');
        const tabContents = document.querySelectorAll('.tab-content');

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetTab = tab.dataset.tab;

                // Remove active class from all tabs and contents
                tabs.forEach(t => t.classList.remove('active'));
                tabContents.forEach(c => c.classList.remove('active'));

                // Add active class to clicked tab and corresponding content
                tab.classList.add('active');
                document.getElementById(targetTab).classList.add('active');
            });
        });
    }

    setupProtocolSteps() {
        const addStepBtn = document.getElementById('addStepBtn');

        if (addStepBtn) {
            addStepBtn.addEventListener('click', () => {
                this.addProtocolStep();
            });
        }

        // Setup existing steps
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('add-step')) {
                this.addProtocolStep();
            } else if (e.target.classList.contains('remove-step')) {
                this.removeProtocolStep(e.target);
            }
        });
    }

    addProtocolStep() {
        const stepsContainer = document.getElementById('protocolSteps');
        const stepCount = stepsContainer.querySelectorAll('.protocol-step').length + 1;

        const stepHTML = `
            <div class="protocol-step">
                <div class="step-number">${stepCount}</div>
                <textarea class="step-description" placeholder="Describe this step..."></textarea>
                <button class="btn-icon add-step">+</button>
                <button class="btn-icon remove-step">-</button>
            </div>
        `;

        stepsContainer.insertAdjacentHTML('beforeend', stepHTML);
        this.renumberSteps();
    }

    removeProtocolStep(button) {
        const step = button.closest('.protocol-step');
        const stepsContainer = document.getElementById('protocolSteps');

        if (stepsContainer.querySelectorAll('.protocol-step').length > 1) {
            step.remove();
            this.renumberSteps();
        }
    }

    renumberSteps() {
        const steps = document.querySelectorAll('.protocol-step');
        steps.forEach((step, index) => {
            step.querySelector('.step-number').textContent = index + 1;
        });
    }

    setupSaveHandler() {
        const saveBtn = document.getElementById('saveExperimentBtn');
        const exportBtn = document.getElementById('exportBtn');

        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveExperiment());
        }

        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportExperiment());
        }
    }

    async saveExperiment() {
        const experimentData = this.collectFormData();

        try {
            if (this.experimentId) {
                await this.api.updateExperiment(this.experimentId, experimentData);
            } else {
                const result = await this.api.createExperiment(experimentData);
                this.experimentId = result.id;
                window.history.replaceState({}, '', `experiment.html?id=${this.experimentId}`);
            }

            alert('Experiment saved successfully!');
        } catch (error) {
            console.error('Error saving experiment:', error);
            alert('Error saving experiment. Please try again.');
        }
    }

    collectFormData() {
        const protocolSteps = [];
        document.querySelectorAll('.protocol-step').forEach(step => {
            const description = step.querySelector('.step-description').value;
            if (description.trim()) {
                protocolSteps.push({ description });
            }
        });

        return {
            title: document.getElementById('experimentTitle').value,
            date: document.getElementById('experimentDate').value,
            status: document.getElementById('experimentStatus').value,
            tags: document.getElementById('experimentTags').value.split(',').map(t => t.trim()).filter(t => t),
            objective: document.getElementById('objective').value,
            hypothesis: document.getElementById('hypothesis').value,
            materials: document.getElementById('materials').value,
            protocol: protocolSteps,
            observations: document.getElementById('observations').value,
            analysis: document.getElementById('analysis').value,
            conclusions: document.getElementById('conclusions').value,
            notes: document.getElementById('additionalNotes').value
        };
    }

    exportExperiment() {
        alert('Export functionality coming soon!');
    }

    setupAttachments() {
        const attachBtn = document.getElementById('attachFileBtn');
        const fileInput = document.getElementById('fileInput');

        if (attachBtn && fileInput) {
            attachBtn.addEventListener('click', () => {
                fileInput.click();
            });

            fileInput.addEventListener('change', (e) => {
                this.handleFileUpload(e.target.files);
            });
        }
    }

    async handleFileUpload(files) {
        const attachmentsList = document.getElementById('attachmentsList');

        for (let file of files) {
            const attachmentHTML = `
                <div class="attachment-item">
                    <div class="attachment-icon">${this.getFileIcon(file.name)}</div>
                    <div class="attachment-info">
                        <div class="attachment-name">${file.name}</div>
                        <div class="attachment-size">${this.formatFileSize(file.size)}</div>
                    </div>
                </div>
            `;
            attachmentsList.insertAdjacentHTML('beforeend', attachmentHTML);
        }
    }

    getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const icons = {
            'pdf': 'PDF',
            'doc': 'DOC',
            'docx': 'DOC',
            'xls': 'XLS',
            'xlsx': 'XLS',
            'jpg': 'IMG',
            'jpeg': 'IMG',
            'png': 'IMG',
            'gif': 'IMG',
            'txt': 'TXT'
        };
        return icons[ext] || 'FILE';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }
}

// Initialize experiment detail page if on that page
if (window.location.pathname.includes('experiment.html')) {
    document.addEventListener('DOMContentLoaded', async () => {
        const { API } = await import('./api.js');
        const api = new API();
        window.experimentDetail = new ExperimentDetail(api);
    });
}
