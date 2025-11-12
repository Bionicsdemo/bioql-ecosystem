// Main Application JavaScript

import { API } from './api.js';
import { ExperimentManager } from './experiments.js';

class BioQLApp {
    constructor() {
        this.currentView = 'dashboard';
        this.api = new API();
        this.experimentManager = new ExperimentManager(this.api);
        this.init();
    }

    init() {
        this.setupNavigation();
        this.setupModals();
        this.setupQuickActions();
        this.loadDashboardData();
        this.loadRecentExperiments();
        this.loadTags();
    }

    setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const view = link.getAttribute('href').substring(1);
                this.switchView(view);

                // Update active nav link
                navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');
            });
        });
    }

    switchView(viewName) {
        // Hide all views
        document.querySelectorAll('.view').forEach(view => {
            view.classList.remove('active');
        });

        // Show selected view
        const targetView = document.getElementById(`${viewName}View`);
        if (targetView) {
            targetView.classList.add('active');
            this.currentView = viewName;

            // Load view-specific data
            this.loadViewData(viewName);
        }
    }

    loadViewData(viewName) {
        switch(viewName) {
            case 'experiments':
                this.experimentManager.loadExperiments();
                break;
            case 'protocols':
                this.loadProtocols();
                break;
            case 'samples':
                this.loadSamples();
                break;
            case 'search':
                // Search view is ready
                break;
        }
    }

    setupModals() {
        const modal = document.getElementById('experimentModal');
        const closeBtn = modal.querySelector('.close');
        const cancelBtn = document.getElementById('cancelBtn');
        const form = document.getElementById('experimentForm');

        closeBtn.addEventListener('click', () => {
            modal.classList.remove('active');
        });

        cancelBtn.addEventListener('click', () => {
            modal.classList.remove('active');
        });

        window.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.createExperiment();
        });
    }

    setupQuickActions() {
        const newExperimentBtn = document.getElementById('newExperimentBtn');
        const newProtocolBtn = document.getElementById('newProtocolBtn');

        newExperimentBtn.addEventListener('click', () => {
            this.showNewExperimentModal();
        });

        newProtocolBtn.addEventListener('click', () => {
            this.showNewProtocolModal();
        });

        // Search functionality
        const experimentSearch = document.getElementById('experimentSearch');
        const experimentFilter = document.getElementById('experimentFilter');

        if (experimentSearch) {
            experimentSearch.addEventListener('input', (e) => {
                this.experimentManager.filterExperiments(e.target.value, experimentFilter.value);
            });
        }

        if (experimentFilter) {
            experimentFilter.addEventListener('change', (e) => {
                this.experimentManager.filterExperiments(experimentSearch.value, e.target.value);
            });
        }

        // BioQL Query
        const executeQueryBtn = document.getElementById('executeQuery');
        if (executeQueryBtn) {
            executeQueryBtn.addEventListener('click', () => {
                this.executeBioQLQuery();
            });
        }
    }

    showNewExperimentModal() {
        const modal = document.getElementById('experimentModal');
        modal.classList.add('active');
        document.getElementById('experimentForm').reset();
    }

    showNewProtocolModal() {
        alert('Protocol creation coming soon!');
    }

    async createExperiment() {
        const form = document.getElementById('experimentForm');
        const formData = new FormData(form);

        const experimentData = {
            title: formData.get('title'),
            template: formData.get('template'),
            description: formData.get('description'),
            date: new Date().toISOString(),
            status: 'planning'
        };

        try {
            const result = await this.api.createExperiment(experimentData);

            // Close modal
            document.getElementById('experimentModal').classList.remove('active');

            // Redirect to experiment detail page
            window.location.href = `experiment.html?id=${result.id}`;
        } catch (error) {
            console.error('Error creating experiment:', error);
            alert('Failed to create experiment. Please try again.');
        }
    }

    async loadDashboardData() {
        try {
            const stats = await this.api.getDashboardStats();

            document.getElementById('totalExperiments').textContent = stats.totalExperiments || 0;
            document.getElementById('totalProtocols').textContent = stats.totalProtocols || 0;
            document.getElementById('totalSamples').textContent = stats.totalSamples || 0;
            document.getElementById('recentActivity').textContent = stats.recentActivity || 0;

            this.loadActivityFeed(stats.recentActivities || []);
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            // Set default values
            document.getElementById('totalExperiments').textContent = '0';
            document.getElementById('totalProtocols').textContent = '0';
            document.getElementById('totalSamples').textContent = '0';
            document.getElementById('recentActivity').textContent = '0';
        }
    }

    loadActivityFeed(activities) {
        const feed = document.getElementById('activityFeed');

        if (activities.length === 0) {
            feed.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 2rem;">No recent activity</p>';
            return;
        }

        feed.innerHTML = activities.map(activity => `
            <div class="activity-item">
                <strong>${activity.action}</strong> - ${activity.description}
                <span class="activity-date">${this.formatDate(activity.date)}</span>
            </div>
        `).join('');
    }

    async loadRecentExperiments() {
        try {
            const experiments = await this.api.getRecentExperiments();
            const list = document.getElementById('recentExperiments');

            if (experiments.length === 0) {
                list.innerHTML = '<li style="color: var(--text-secondary); font-size: 0.875rem;">No experiments yet</li>';
                return;
            }

            list.innerHTML = experiments.map(exp => `
                <li><a href="experiment.html?id=${exp.id}">${exp.title}</a></li>
            `).join('');
        } catch (error) {
            console.error('Error loading recent experiments:', error);
        }
    }

    async loadTags() {
        try {
            const tags = await this.api.getTags();
            const tagCloud = document.getElementById('tagCloud');

            if (tags.length === 0) {
                tagCloud.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.875rem;">No tags yet</p>';
                return;
            }

            tagCloud.innerHTML = tags.map(tag => `
                <span class="tag" data-tag="${tag.name}">${tag.name} (${tag.count})</span>
            `).join('');

            // Add tag click handlers
            tagCloud.querySelectorAll('.tag').forEach(tagEl => {
                tagEl.addEventListener('click', (e) => {
                    const tagName = e.target.dataset.tag;
                    this.filterByTag(tagName);
                });
            });
        } catch (error) {
            console.error('Error loading tags:', error);
        }
    }

    filterByTag(tagName) {
        this.switchView('experiments');
        this.experimentManager.filterByTag(tagName);
    }

    async loadProtocols() {
        try {
            const protocols = await this.api.getProtocols();
            const list = document.getElementById('protocolsList');

            if (protocols.length === 0) {
                list.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 2rem;">No protocols yet</p>';
                return;
            }

            list.innerHTML = protocols.map(protocol => `
                <div class="protocol-card">
                    <h3>${protocol.title}</h3>
                    <p>${protocol.description}</p>
                    <div class="protocol-meta">
                        <span>Steps: ${protocol.steps}</span>
                        <span>Used: ${protocol.usageCount} times</span>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            console.error('Error loading protocols:', error);
        }
    }

    async loadSamples() {
        try {
            const samples = await this.api.getSamples();
            const list = document.getElementById('samplesList');

            if (samples.length === 0) {
                list.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 2rem;">No samples tracked yet</p>';
                return;
            }

            list.innerHTML = `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Sample ID</th>
                            <th>Name</th>
                            <th>Type</th>
                            <th>Location</th>
                            <th>Date Added</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${samples.map(sample => `
                            <tr>
                                <td>${sample.id}</td>
                                <td>${sample.name}</td>
                                <td>${sample.type}</td>
                                <td>${sample.location}</td>
                                <td>${this.formatDate(sample.dateAdded)}</td>
                                <td><span class="status-badge">${sample.status}</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } catch (error) {
            console.error('Error loading samples:', error);
        }
    }

    async executeBioQLQuery() {
        const query = document.getElementById('bioqlQuery').value;
        const resultsContainer = document.getElementById('queryResults');

        if (!query.trim()) {
            resultsContainer.innerHTML = '<p style="color: var(--text-secondary);">Please enter a query</p>';
            return;
        }

        try {
            resultsContainer.innerHTML = '<p style="color: var(--text-secondary);">Executing query...</p>';
            const results = await this.api.executeBioQLQuery(query);

            if (results.length === 0) {
                resultsContainer.innerHTML = '<p style="color: var(--text-secondary);">No results found</p>';
                return;
            }

            resultsContainer.innerHTML = results.map(result => `
                <div class="result-item" onclick="window.location.href='experiment.html?id=${result.id}'">
                    <h4>${result.title}</h4>
                    <p>${result.description}</p>
                    <div style="display: flex; gap: 1rem; margin-top: 0.5rem; font-size: 0.875rem; color: var(--text-secondary);">
                        <span>Date: ${this.formatDate(result.date)}</span>
                        <span>Status: ${result.status}</span>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            console.error('Error executing query:', error);
            resultsContainer.innerHTML = '<p style="color: var(--error-color);">Error executing query. Please check your syntax.</p>';
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

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.bioqlApp = new BioQLApp();
});
