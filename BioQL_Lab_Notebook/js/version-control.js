/**
 * BioQL Lab Notebook - Version Control Module
 * Git-style version control for notebooks with auto-save, checkpoints, and diff viewer
 */

class VersionControl {
    constructor() {
        this.storagePrefix = 'bioql_versions_';
        this.configKey = 'bioql_version_config';
        this.autoSaveInterval = 5 * 60 * 1000; // 5 minutes
        this.autoSaveTimers = new Map();
        this.currentUser = this.getCurrentUser();
        this.init();
    }

    init() {
        // Initialize version control system
        this.loadConfig();
        this.setupAutoSave();
    }

    loadConfig() {
        const config = localStorage.getItem(this.configKey);
        this.config = config ? JSON.parse(config) : {
            autoSaveEnabled: true,
            maxVersionsPerNotebook: 50,
            compressionEnabled: true
        };
    }

    saveConfig() {
        localStorage.setItem(this.configKey, JSON.stringify(this.config));
    }

    getCurrentUser() {
        // Get current user from localStorage or create anonymous user
        const user = localStorage.getItem('bioql_current_user');
        if (user) {
            return JSON.parse(user);
        }
        return {
            id: 'user_' + Date.now(),
            name: 'Anonymous User',
            email: 'user@bioql.local'
        };
    }

    /**
     * Generate unique version ID
     */
    generateVersionId() {
        return 'v_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Save a new version of the notebook
     * @param {Object} notebookData - The notebook data to save
     * @param {string} message - Commit message describing the changes
     * @param {boolean} isAutoSave - Whether this is an auto-save
     * @returns {Object} The created version object
     */
    saveVersion(notebookData, message = '', isAutoSave = false) {
        const notebookId = notebookData.id || 'default_notebook';
        const versionId = this.generateVersionId();

        const version = {
            id: versionId,
            notebookId: notebookId,
            timestamp: new Date().toISOString(),
            message: message || (isAutoSave ? 'Auto-save' : 'Manual checkpoint'),
            author: this.currentUser,
            isAutoSave: isAutoSave,
            data: this.compressData(notebookData),
            dataHash: this.hashData(notebookData),
            parent: this.getLatestVersion(notebookId)?.id || null,
            tags: []
        };

        // Get existing versions
        const versions = this.getVersionHistory(notebookId);

        // Check if data has actually changed
        if (versions.length > 0) {
            const latestVersion = versions[0];
            if (latestVersion.dataHash === version.dataHash) {
                console.log('No changes detected, skipping version save');
                return latestVersion;
            }
        }

        // Add new version
        versions.unshift(version);

        // Enforce max versions limit
        if (versions.length > this.config.maxVersionsPerNotebook) {
            // Keep manual checkpoints, remove oldest auto-saves first
            const manual = versions.filter(v => !v.isAutoSave);
            const auto = versions.filter(v => v.isAutoSave);
            const keepAuto = Math.max(0, this.config.maxVersionsPerNotebook - manual.length);
            const trimmedVersions = [...manual, ...auto.slice(0, keepAuto)];
            this.saveVersionHistory(notebookId, trimmedVersions);
        } else {
            this.saveVersionHistory(notebookId, versions);
        }

        console.log(`Version saved: ${versionId} - ${message}`);
        return version;
    }

    /**
     * Get version history for a notebook
     * @param {string} notebookId - The notebook ID
     * @returns {Array} Array of version objects, sorted by timestamp (newest first)
     */
    getVersionHistory(notebookId) {
        const key = this.storagePrefix + notebookId;
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : [];
    }

    /**
     * Save version history to localStorage
     */
    saveVersionHistory(notebookId, versions) {
        const key = this.storagePrefix + notebookId;
        localStorage.setItem(key, JSON.stringify(versions));
    }

    /**
     * Get the latest version of a notebook
     */
    getLatestVersion(notebookId) {
        const versions = this.getVersionHistory(notebookId);
        return versions.length > 0 ? versions[0] : null;
    }

    /**
     * Get a specific version by ID
     */
    getVersion(notebookId, versionId) {
        const versions = this.getVersionHistory(notebookId);
        return versions.find(v => v.id === versionId);
    }

    /**
     * Restore a notebook to a previous version
     * @param {string} notebookId - The notebook ID
     * @param {string} versionId - The version ID to restore
     * @returns {Object} The restored notebook data
     */
    restoreVersion(notebookId, versionId) {
        const version = this.getVersion(notebookId, versionId);
        if (!version) {
            throw new Error('Version not found: ' + versionId);
        }

        // Save current state before restoring
        const currentNotebook = this.getLatestVersion(notebookId);
        if (currentNotebook) {
            this.saveVersion(
                this.decompressData(currentNotebook.data),
                `Before restore to ${versionId}`,
                false
            );
        }

        // Restore the version
        const restoredData = this.decompressData(version.data);

        // Create a new version marking this as a restore
        this.saveVersion(
            restoredData,
            `Restored from version: ${version.message} (${new Date(version.timestamp).toLocaleString()})`,
            false
        );

        return restoredData;
    }

    /**
     * Compare two versions and generate diff
     * @param {string} notebookId - The notebook ID
     * @param {string} versionId1 - First version ID
     * @param {string} versionId2 - Second version ID
     * @returns {Object} Diff object with changes
     */
    compareVersions(notebookId, versionId1, versionId2) {
        const v1 = this.getVersion(notebookId, versionId1);
        const v2 = this.getVersion(notebookId, versionId2);

        if (!v1 || !v2) {
            throw new Error('One or both versions not found');
        }

        const data1 = this.decompressData(v1.data);
        const data2 = this.decompressData(v2.data);

        return {
            version1: {
                id: v1.id,
                timestamp: v1.timestamp,
                message: v1.message,
                author: v1.author
            },
            version2: {
                id: v2.id,
                timestamp: v2.timestamp,
                message: v2.message,
                author: v2.author
            },
            diff: this.generateDiff(data1, data2),
            summary: this.generateDiffSummary(data1, data2)
        };
    }

    /**
     * Generate detailed diff between two data objects
     */
    generateDiff(data1, data2) {
        const diff = {
            metadata: this.diffObjects(data1.metadata || {}, data2.metadata || {}),
            cells: this.diffArrays(data1.cells || [], data2.cells || []),
            settings: this.diffObjects(data1.settings || {}, data2.settings || {})
        };

        return diff;
    }

    /**
     * Generate human-readable diff summary
     */
    generateDiffSummary(data1, data2) {
        const summary = {
            cellsAdded: 0,
            cellsRemoved: 0,
            cellsModified: 0,
            metadataChanged: false,
            settingsChanged: false
        };

        const cells1 = data1.cells || [];
        const cells2 = data2.cells || [];

        // Count cell changes
        const cells1Ids = new Set(cells1.map(c => c.id));
        const cells2Ids = new Set(cells2.map(c => c.id));

        summary.cellsAdded = cells2.filter(c => !cells1Ids.has(c.id)).length;
        summary.cellsRemoved = cells1.filter(c => !cells2Ids.has(c.id)).length;

        // Check for modified cells
        cells1.forEach(c1 => {
            const c2 = cells2.find(c => c.id === c1.id);
            if (c2 && JSON.stringify(c1) !== JSON.stringify(c2)) {
                summary.cellsModified++;
            }
        });

        summary.metadataChanged = JSON.stringify(data1.metadata) !== JSON.stringify(data2.metadata);
        summary.settingsChanged = JSON.stringify(data1.settings) !== JSON.stringify(data2.settings);

        return summary;
    }

    /**
     * Diff two objects
     */
    diffObjects(obj1, obj2) {
        const changes = {
            added: {},
            removed: {},
            modified: {}
        };

        const keys1 = Object.keys(obj1);
        const keys2 = Object.keys(obj2);

        // Find added and modified
        keys2.forEach(key => {
            if (!keys1.includes(key)) {
                changes.added[key] = obj2[key];
            } else if (JSON.stringify(obj1[key]) !== JSON.stringify(obj2[key])) {
                changes.modified[key] = {
                    old: obj1[key],
                    new: obj2[key]
                };
            }
        });

        // Find removed
        keys1.forEach(key => {
            if (!keys2.includes(key)) {
                changes.removed[key] = obj1[key];
            }
        });

        return changes;
    }

    /**
     * Diff two arrays
     */
    diffArrays(arr1, arr2) {
        return {
            added: arr2.filter(item2 =>
                !arr1.some(item1 => JSON.stringify(item1) === JSON.stringify(item2))
            ),
            removed: arr1.filter(item1 =>
                !arr2.some(item2 => JSON.stringify(item1) === JSON.stringify(item2))
            ),
            lengthChange: arr2.length - arr1.length
        };
    }

    /**
     * Fork a notebook to create a new branch
     * @param {string} notebookId - The notebook ID to fork
     * @param {string} newNotebookId - The new notebook ID
     * @param {string} message - Fork message
     * @returns {Object} The forked notebook data
     */
    forkNotebook(notebookId, newNotebookId, message = '') {
        const latestVersion = this.getLatestVersion(notebookId);
        if (!latestVersion) {
            throw new Error('No versions found for notebook: ' + notebookId);
        }

        const forkedData = this.decompressData(latestVersion.data);
        forkedData.id = newNotebookId;
        forkedData.metadata = forkedData.metadata || {};
        forkedData.metadata.forkedFrom = {
            notebookId: notebookId,
            versionId: latestVersion.id,
            timestamp: new Date().toISOString()
        };

        // Save initial version for the new notebook
        this.saveVersion(
            forkedData,
            message || `Forked from ${notebookId} at ${new Date(latestVersion.timestamp).toLocaleString()}`,
            false
        );

        return forkedData;
    }

    /**
     * Merge two versions
     * @param {string} targetNotebookId - Target notebook ID
     * @param {string} targetVersionId - Target version ID
     * @param {string} sourceNotebookId - Source notebook ID
     * @param {string} sourceVersionId - Source version ID
     * @param {Object} mergeOptions - Merge strategy options
     * @returns {Object} Merged notebook data
     */
    mergeVersions(targetNotebookId, targetVersionId, sourceNotebookId, sourceVersionId, mergeOptions = {}) {
        const targetVersion = this.getVersion(targetNotebookId, targetVersionId);
        const sourceVersion = this.getVersion(sourceNotebookId, sourceVersionId);

        if (!targetVersion || !sourceVersion) {
            throw new Error('One or both versions not found');
        }

        const targetData = this.decompressData(targetVersion.data);
        const sourceData = this.decompressData(sourceVersion.data);

        const mergeStrategy = mergeOptions.strategy || 'auto';
        let mergedData;

        switch (mergeStrategy) {
            case 'ours':
                // Keep target, ignore source
                mergedData = targetData;
                break;
            case 'theirs':
                // Take source, ignore target
                mergedData = sourceData;
                break;
            case 'auto':
            default:
                // Smart merge
                mergedData = this.smartMerge(targetData, sourceData, mergeOptions);
                break;
        }

        // Save merged version
        this.saveVersion(
            mergedData,
            `Merged ${sourceNotebookId}@${sourceVersionId.substr(0, 8)} into ${targetNotebookId}@${targetVersionId.substr(0, 8)}`,
            false
        );

        return {
            data: mergedData,
            conflicts: mergeOptions.conflicts || []
        };
    }

    /**
     * Smart merge algorithm
     */
    smartMerge(targetData, sourceData, options) {
        const merged = JSON.parse(JSON.stringify(targetData)); // Deep clone

        // Merge metadata
        merged.metadata = {
            ...targetData.metadata,
            ...sourceData.metadata,
            mergedAt: new Date().toISOString()
        };

        // Merge cells - append source cells not in target
        const targetCellIds = new Set((targetData.cells || []).map(c => c.id));
        const sourceCells = sourceData.cells || [];

        sourceCells.forEach(sourceCell => {
            if (!targetCellIds.has(sourceCell.id)) {
                merged.cells.push(sourceCell);
            } else if (options.overwriteConflicts) {
                // Replace conflicting cells
                const index = merged.cells.findIndex(c => c.id === sourceCell.id);
                merged.cells[index] = sourceCell;
            }
        });

        // Merge settings
        merged.settings = {
            ...targetData.settings,
            ...sourceData.settings
        };

        return merged;
    }

    /**
     * Setup auto-save for a notebook
     */
    setupAutoSave(notebookId, getNotebookDataFn) {
        if (!this.config.autoSaveEnabled) return;

        // Clear existing timer
        if (this.autoSaveTimers.has(notebookId)) {
            clearInterval(this.autoSaveTimers.get(notebookId));
        }

        // Setup new timer
        const timer = setInterval(() => {
            try {
                const data = getNotebookDataFn();
                this.saveVersion(data, 'Auto-save', true);
            } catch (error) {
                console.error('Auto-save failed:', error);
            }
        }, this.autoSaveInterval);

        this.autoSaveTimers.set(notebookId, timer);
    }

    /**
     * Stop auto-save for a notebook
     */
    stopAutoSave(notebookId) {
        if (this.autoSaveTimers.has(notebookId)) {
            clearInterval(this.autoSaveTimers.get(notebookId));
            this.autoSaveTimers.delete(notebookId);
        }
    }

    /**
     * Delete a specific version
     */
    deleteVersion(notebookId, versionId) {
        const versions = this.getVersionHistory(notebookId);
        const filtered = versions.filter(v => v.id !== versionId);
        this.saveVersionHistory(notebookId, filtered);
    }

    /**
     * Delete all versions for a notebook
     */
    deleteAllVersions(notebookId) {
        const key = this.storagePrefix + notebookId;
        localStorage.removeItem(key);
        this.stopAutoSave(notebookId);
    }

    /**
     * Tag a version
     */
    tagVersion(notebookId, versionId, tag) {
        const versions = this.getVersionHistory(notebookId);
        const version = versions.find(v => v.id === versionId);
        if (version) {
            version.tags = version.tags || [];
            if (!version.tags.includes(tag)) {
                version.tags.push(tag);
                this.saveVersionHistory(notebookId, versions);
            }
        }
    }

    /**
     * Compress data for storage
     */
    compressData(data) {
        // Simple compression - in production, use LZ-string or similar
        if (this.config.compressionEnabled) {
            return JSON.stringify(data);
        }
        return data;
    }

    /**
     * Decompress data from storage
     */
    decompressData(data) {
        if (typeof data === 'string') {
            return JSON.parse(data);
        }
        return data;
    }

    /**
     * Generate hash of data for change detection
     */
    hashData(data) {
        const str = JSON.stringify(data);
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return hash.toString(36);
    }

    /**
     * Get storage statistics
     */
    getStorageStats() {
        const stats = {
            totalVersions: 0,
            totalSize: 0,
            notebooks: {}
        };

        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key.startsWith(this.storagePrefix)) {
                const notebookId = key.replace(this.storagePrefix, '');
                const versions = this.getVersionHistory(notebookId);
                const size = new Blob([localStorage.getItem(key)]).size;

                stats.notebooks[notebookId] = {
                    versionCount: versions.length,
                    size: size,
                    oldestVersion: versions[versions.length - 1]?.timestamp,
                    newestVersion: versions[0]?.timestamp
                };

                stats.totalVersions += versions.length;
                stats.totalSize += size;
            }
        }

        return stats;
    }

    /**
     * Export version history to JSON
     */
    exportHistory(notebookId) {
        const versions = this.getVersionHistory(notebookId);
        const exportData = {
            notebookId: notebookId,
            exportDate: new Date().toISOString(),
            versionCount: versions.length,
            versions: versions
        };
        return JSON.stringify(exportData, null, 2);
    }

    /**
     * Import version history from JSON
     */
    importHistory(jsonData) {
        const importData = JSON.parse(jsonData);
        this.saveVersionHistory(importData.notebookId, importData.versions);
        return importData.notebookId;
    }
}

// UI Components for Version Control

class VersionControlUI {
    constructor(versionControl) {
        this.vc = versionControl;
        this.currentNotebookId = null;
        this.selectedVersions = [];
    }

    /**
     * Show version history modal
     */
    showVersionHistory(notebookId, onRestore) {
        this.currentNotebookId = notebookId;
        const versions = this.vc.getVersionHistory(notebookId);

        const modal = this.createModal('Version History', this.renderVersionHistory(versions, onRestore));
        document.body.appendChild(modal);

        // Animate in
        setTimeout(() => modal.classList.add('active'), 10);
    }

    /**
     * Render version history timeline
     */
    renderVersionHistory(versions, onRestore) {
        if (versions.length === 0) {
            return `
                <div class="vc-empty-state">
                    <div class="vc-empty-icon">📚</div>
                    <h3>No Version History</h3>
                    <p>Versions will appear here as you save checkpoints.</p>
                </div>
            `;
        }

        const versionItems = versions.map((version, index) => {
            const date = new Date(version.timestamp);
            const isFirst = index === 0;
            const isLast = index === versions.length - 1;

            return `
                <div class="vc-timeline-item ${isFirst ? 'latest' : ''}" data-version-id="${version.id}">
                    <div class="vc-timeline-marker">
                        <div class="vc-timeline-dot ${version.isAutoSave ? 'auto' : 'manual'}"></div>
                        ${!isLast ? '<div class="vc-timeline-line"></div>' : ''}
                    </div>
                    <div class="vc-version-card">
                        <div class="vc-version-header">
                            <div class="vc-version-info">
                                <h4 class="vc-version-message">
                                    ${version.isAutoSave ? '🔄' : '📌'} ${this.escapeHtml(version.message)}
                                    ${isFirst ? '<span class="vc-badge latest">Latest</span>' : ''}
                                </h4>
                                <div class="vc-version-meta">
                                    <span class="vc-author">👤 ${this.escapeHtml(version.author.name)}</span>
                                    <span class="vc-timestamp">🕒 ${this.formatTimestamp(date)}</span>
                                    <span class="vc-version-id">ID: ${version.id.substr(0, 8)}</span>
                                </div>
                                ${version.tags && version.tags.length > 0 ? `
                                    <div class="vc-tags">
                                        ${version.tags.map(tag => `<span class="vc-tag">${this.escapeHtml(tag)}</span>`).join('')}
                                    </div>
                                ` : ''}
                            </div>
                            <div class="vc-version-actions">
                                <button class="vc-btn vc-btn-sm vc-btn-compare" data-action="select" data-version-id="${version.id}">
                                    Select
                                </button>
                                ${!isFirst ? `
                                    <button class="vc-btn vc-btn-sm vc-btn-primary" data-action="restore" data-version-id="${version.id}">
                                        Restore
                                    </button>
                                ` : ''}
                                <button class="vc-btn vc-btn-sm" data-action="view" data-version-id="${version.id}">
                                    View
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        return `
            <div class="vc-history-container">
                <div class="vc-history-toolbar">
                    <div class="vc-stats">
                        <span class="vc-stat-item">📊 ${versions.length} versions</span>
                        <span class="vc-stat-item">📌 ${versions.filter(v => !v.isAutoSave).length} manual</span>
                        <span class="vc-stat-item">🔄 ${versions.filter(v => v.isAutoSave).length} auto-save</span>
                    </div>
                    <div class="vc-actions">
                        <button class="vc-btn vc-btn-primary" data-action="create-checkpoint">
                            Create Checkpoint
                        </button>
                        <button class="vc-btn" data-action="compare" ${this.selectedVersions.length !== 2 ? 'disabled' : ''}>
                            Compare Selected (${this.selectedVersions.length}/2)
                        </button>
                    </div>
                </div>
                <div class="vc-timeline">
                    ${versionItems}
                </div>
            </div>
        `;
    }

    /**
     * Show version comparison modal
     */
    showVersionComparison(notebookId, versionId1, versionId2) {
        const comparison = this.vc.compareVersions(notebookId, versionId1, versionId2);
        const modal = this.createModal('Compare Versions', this.renderComparison(comparison), 'large');
        document.body.appendChild(modal);
        setTimeout(() => modal.classList.add('active'), 10);
    }

    /**
     * Render version comparison
     */
    renderComparison(comparison) {
        const { version1, version2, diff, summary } = comparison;

        return `
            <div class="vc-comparison-container">
                <div class="vc-comparison-header">
                    <div class="vc-version-col">
                        <h3>Version A</h3>
                        <div class="vc-version-info">
                            <p><strong>Message:</strong> ${this.escapeHtml(version1.message)}</p>
                            <p><strong>Author:</strong> ${this.escapeHtml(version1.author.name)}</p>
                            <p><strong>Date:</strong> ${this.formatTimestamp(new Date(version1.timestamp))}</p>
                        </div>
                    </div>
                    <div class="vc-comparison-arrow">→</div>
                    <div class="vc-version-col">
                        <h3>Version B</h3>
                        <div class="vc-version-info">
                            <p><strong>Message:</strong> ${this.escapeHtml(version2.message)}</p>
                            <p><strong>Author:</strong> ${this.escapeHtml(version2.author.name)}</p>
                            <p><strong>Date:</strong> ${this.formatTimestamp(new Date(version2.timestamp))}</p>
                        </div>
                    </div>
                </div>

                <div class="vc-summary">
                    <h4>Summary of Changes</h4>
                    <div class="vc-summary-stats">
                        ${summary.cellsAdded > 0 ? `<span class="vc-stat added">+${summary.cellsAdded} cells added</span>` : ''}
                        ${summary.cellsRemoved > 0 ? `<span class="vc-stat removed">-${summary.cellsRemoved} cells removed</span>` : ''}
                        ${summary.cellsModified > 0 ? `<span class="vc-stat modified">~${summary.cellsModified} cells modified</span>` : ''}
                        ${summary.metadataChanged ? `<span class="vc-stat info">Metadata changed</span>` : ''}
                        ${summary.settingsChanged ? `<span class="vc-stat info">Settings changed</span>` : ''}
                    </div>
                </div>

                <div class="vc-diff-sections">
                    ${this.renderDiffSection('Cells', diff.cells)}
                    ${this.renderDiffSection('Metadata', diff.metadata)}
                    ${this.renderDiffSection('Settings', diff.settings)}
                </div>
            </div>
        `;
    }

    /**
     * Render a diff section
     */
    renderDiffSection(title, changes) {
        const hasChanges = (changes.added && Object.keys(changes.added).length > 0) ||
                          (changes.removed && Object.keys(changes.removed).length > 0) ||
                          (changes.modified && Object.keys(changes.modified).length > 0);

        if (!hasChanges) {
            return `
                <div class="vc-diff-section">
                    <h4>${title}</h4>
                    <p class="vc-no-changes">No changes</p>
                </div>
            `;
        }

        return `
            <div class="vc-diff-section">
                <h4>${title}</h4>
                ${this.renderChanges(changes)}
            </div>
        `;
    }

    /**
     * Render changes in a diff
     */
    renderChanges(changes) {
        let html = '';

        if (changes.added && Object.keys(changes.added).length > 0) {
            html += '<div class="vc-changes-group added">';
            html += '<h5>Added</h5>';
            html += '<pre>' + this.escapeHtml(JSON.stringify(changes.added, null, 2)) + '</pre>';
            html += '</div>';
        }

        if (changes.removed && Object.keys(changes.removed).length > 0) {
            html += '<div class="vc-changes-group removed">';
            html += '<h5>Removed</h5>';
            html += '<pre>' + this.escapeHtml(JSON.stringify(changes.removed, null, 2)) + '</pre>';
            html += '</div>';
        }

        if (changes.modified && Object.keys(changes.modified).length > 0) {
            html += '<div class="vc-changes-group modified">';
            html += '<h5>Modified</h5>';
            html += '<pre>' + this.escapeHtml(JSON.stringify(changes.modified, null, 2)) + '</pre>';
            html += '</div>';
        }

        return html || '<p class="vc-no-changes">No changes</p>';
    }

    /**
     * Create modal element
     */
    createModal(title, content, size = 'medium') {
        const modal = document.createElement('div');
        modal.className = 'vc-modal-overlay';
        modal.innerHTML = `
            <div class="vc-modal vc-modal-${size}">
                <div class="vc-modal-header">
                    <h2>${title}</h2>
                    <button class="vc-modal-close" data-action="close">&times;</button>
                </div>
                <div class="vc-modal-body">
                    ${content}
                </div>
            </div>
        `;

        // Event delegation
        modal.addEventListener('click', (e) => {
            if (e.target.classList.contains('vc-modal-overlay') ||
                e.target.closest('[data-action="close"]')) {
                this.closeModal(modal);
            }
        });

        return modal;
    }

    /**
     * Close modal
     */
    closeModal(modal) {
        modal.classList.remove('active');
        setTimeout(() => modal.remove(), 300);
    }

    /**
     * Format timestamp
     */
    formatTimestamp(date) {
        const now = new Date();
        const diff = now - date;
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (seconds < 60) return 'Just now';
        if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        if (days < 7) return `${days} day${days > 1 ? 's' : ''} ago`;

        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Get CSS styles for version control UI
     */
    static getStyles() {
        return `
            /* Version Control Modal Styles */
            .vc-modal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.7);
                backdrop-filter: blur(4px);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
                opacity: 0;
                transition: opacity 0.3s ease;
            }

            .vc-modal-overlay.active {
                opacity: 1;
            }

            .vc-modal {
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                max-height: 90vh;
                display: flex;
                flex-direction: column;
                transform: scale(0.9);
                transition: transform 0.3s ease;
            }

            .vc-modal-overlay.active .vc-modal {
                transform: scale(1);
            }

            .vc-modal-medium {
                width: 90%;
                max-width: 900px;
            }

            .vc-modal-large {
                width: 95%;
                max-width: 1400px;
            }

            .vc-modal-header {
                padding: 24px 32px;
                border-bottom: 1px solid #e0e0e0;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .vc-modal-header h2 {
                margin: 0;
                font-size: 24px;
                color: #1a1a1a;
            }

            .vc-modal-close {
                background: none;
                border: none;
                font-size: 32px;
                color: #666;
                cursor: pointer;
                padding: 0;
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 4px;
                transition: all 0.2s;
            }

            .vc-modal-close:hover {
                background: #f0f0f0;
                color: #000;
            }

            .vc-modal-body {
                padding: 32px;
                overflow-y: auto;
                flex: 1;
            }

            /* History Container */
            .vc-history-container {
                display: flex;
                flex-direction: column;
                gap: 24px;
            }

            .vc-history-toolbar {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 16px;
                background: #f8f9fa;
                border-radius: 8px;
            }

            .vc-stats {
                display: flex;
                gap: 24px;
            }

            .vc-stat-item {
                font-size: 14px;
                color: #666;
            }

            .vc-actions {
                display: flex;
                gap: 12px;
            }

            /* Timeline */
            .vc-timeline {
                position: relative;
            }

            .vc-timeline-item {
                display: flex;
                gap: 16px;
                position: relative;
            }

            .vc-timeline-marker {
                position: relative;
                width: 32px;
                display: flex;
                flex-direction: column;
                align-items: center;
            }

            .vc-timeline-dot {
                width: 16px;
                height: 16px;
                border-radius: 50%;
                background: #4CAF50;
                border: 3px solid white;
                box-shadow: 0 0 0 2px #4CAF50;
                z-index: 2;
                margin-top: 8px;
            }

            .vc-timeline-dot.auto {
                background: #2196F3;
                box-shadow: 0 0 0 2px #2196F3;
            }

            .vc-timeline-dot.manual {
                background: #FF9800;
                box-shadow: 0 0 0 2px #FF9800;
            }

            .vc-timeline-item.latest .vc-timeline-dot {
                width: 20px;
                height: 20px;
                background: #E91E63;
                box-shadow: 0 0 0 3px #E91E63, 0 0 0 6px rgba(233, 30, 99, 0.2);
            }

            .vc-timeline-line {
                width: 2px;
                flex: 1;
                background: linear-gradient(to bottom, #ddd, transparent);
                margin-top: 4px;
            }

            /* Version Card */
            .vc-version-card {
                flex: 1;
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 16px;
                transition: all 0.2s;
            }

            .vc-version-card:hover {
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                border-color: #2196F3;
            }

            .vc-version-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 16px;
            }

            .vc-version-info {
                flex: 1;
            }

            .vc-version-message {
                margin: 0 0 8px 0;
                font-size: 16px;
                font-weight: 600;
                color: #1a1a1a;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .vc-version-meta {
                display: flex;
                flex-wrap: wrap;
                gap: 16px;
                font-size: 13px;
                color: #666;
                margin-bottom: 8px;
            }

            .vc-version-actions {
                display: flex;
                gap: 8px;
            }

            /* Badges and Tags */
            .vc-badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
            }

            .vc-badge.latest {
                background: #E91E63;
                color: white;
            }

            .vc-tags {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
                margin-top: 8px;
            }

            .vc-tag {
                display: inline-block;
                padding: 3px 10px;
                background: #e3f2fd;
                color: #1976d2;
                border-radius: 4px;
                font-size: 12px;
            }

            /* Buttons */
            .vc-btn {
                padding: 8px 16px;
                border: 1px solid #ddd;
                background: white;
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
                font-weight: 500;
                transition: all 0.2s;
            }

            .vc-btn:hover:not(:disabled) {
                background: #f5f5f5;
                border-color: #999;
            }

            .vc-btn-primary {
                background: #2196F3;
                color: white;
                border-color: #2196F3;
            }

            .vc-btn-primary:hover:not(:disabled) {
                background: #1976D2;
                border-color: #1976D2;
            }

            .vc-btn-sm {
                padding: 6px 12px;
                font-size: 12px;
            }

            .vc-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }

            /* Comparison View */
            .vc-comparison-container {
                display: flex;
                flex-direction: column;
                gap: 24px;
            }

            .vc-comparison-header {
                display: flex;
                gap: 24px;
                align-items: center;
            }

            .vc-version-col {
                flex: 1;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
            }

            .vc-version-col h3 {
                margin: 0 0 12px 0;
                color: #1a1a1a;
            }

            .vc-version-col p {
                margin: 4px 0;
                font-size: 14px;
                color: #666;
            }

            .vc-comparison-arrow {
                font-size: 32px;
                color: #999;
            }

            .vc-summary {
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
            }

            .vc-summary h4 {
                margin: 0 0 12px 0;
            }

            .vc-summary-stats {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
            }

            .vc-stat {
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }

            .vc-stat.added {
                background: #e8f5e9;
                color: #2e7d32;
            }

            .vc-stat.removed {
                background: #ffebee;
                color: #c62828;
            }

            .vc-stat.modified {
                background: #fff3e0;
                color: #ef6c00;
            }

            .vc-stat.info {
                background: #e3f2fd;
                color: #1976d2;
            }

            /* Diff Sections */
            .vc-diff-sections {
                display: flex;
                flex-direction: column;
                gap: 24px;
            }

            .vc-diff-section {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                overflow: hidden;
            }

            .vc-diff-section h4 {
                margin: 0;
                padding: 16px 20px;
                background: #f8f9fa;
                border-bottom: 1px solid #e0e0e0;
            }

            .vc-changes-group {
                padding: 16px 20px;
                border-left: 4px solid #ddd;
            }

            .vc-changes-group.added {
                background: #f1f8f4;
                border-left-color: #4CAF50;
            }

            .vc-changes-group.removed {
                background: #fef5f5;
                border-left-color: #f44336;
            }

            .vc-changes-group.modified {
                background: #fff8f0;
                border-left-color: #FF9800;
            }

            .vc-changes-group h5 {
                margin: 0 0 12px 0;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            .vc-changes-group pre {
                margin: 0;
                padding: 12px;
                background: white;
                border-radius: 4px;
                font-size: 12px;
                overflow-x: auto;
                font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
            }

            .vc-no-changes {
                padding: 20px;
                text-align: center;
                color: #999;
                font-style: italic;
            }

            /* Empty State */
            .vc-empty-state {
                text-align: center;
                padding: 60px 20px;
            }

            .vc-empty-icon {
                font-size: 64px;
                margin-bottom: 16px;
            }

            .vc-empty-state h3 {
                margin: 0 0 8px 0;
                color: #1a1a1a;
            }

            .vc-empty-state p {
                margin: 0;
                color: #666;
            }

            /* Responsive */
            @media (max-width: 768px) {
                .vc-modal {
                    width: 100%;
                    height: 100%;
                    max-height: 100vh;
                    border-radius: 0;
                }

                .vc-history-toolbar {
                    flex-direction: column;
                    gap: 16px;
                }

                .vc-comparison-header {
                    flex-direction: column;
                }

                .vc-comparison-arrow {
                    transform: rotate(90deg);
                }

                .vc-version-actions {
                    flex-direction: column;
                }
            }
        `;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { VersionControl, VersionControlUI };
}
