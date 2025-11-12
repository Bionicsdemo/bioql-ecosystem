/**
 * BioQL Lab Notebook Manager
 * Handles notebook creation, loading, saving, and cell management
 */

class NotebookManager {
    constructor() {
        this.apiKey = localStorage.getItem('bioql_api_key');
        this.apiBaseUrl = window.location.origin; // Same server
        this.currentNotebook = null;
        this.cells = [];
        this.editors = new Map(); // Map of cell IDs to Monaco editors
        this.autosaveInterval = null;

        if (!this.apiKey) {
            console.warn('No API key found, redirecting to login...');
            window.location.href = '/login.html';
            return;
        }

        this.init();
    }

    async init() {
        console.log('🚀 Initializing BioQL Lab Notebook Manager');

        // Load existing notebooks or create new one
        const urlParams = new URLSearchParams(window.location.search);
        const notebookId = urlParams.get('id');

        if (notebookId) {
            await this.loadNotebook(notebookId);
        } else {
            await this.createNewNotebook();
        }

        this.setupEventListeners();
        this.startAutosave();
    }

    async createNewNotebook(title = 'Untitled Notebook') {
        console.log(`📝 Creating new notebook: ${title}`);

        const initialCells = [{
            id: this.generateCellId(),
            type: 'code',
            content: '# Welcome to BioQL Lab Notebook\n# Start writing your code here\n',
            outputs: []
        }];

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/notebook/create`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': this.apiKey
                },
                body: JSON.stringify({
                    title: title,
                    content: JSON.stringify(initialCells),
                    metadata: {
                        created: new Date().toISOString(),
                        language: 'python',
                        kernel: 'bioql'
                    }
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to create notebook');
            }

            const data = await response.json();
            console.log('✅ Notebook created:', data);

            this.currentNotebook = {
                id: data.id || data.notebook_id,
                title: data.title || title,
                cells: initialCells,
                metadata: data.metadata || {
                    created: new Date().toISOString(),
                    language: 'python',
                    kernel: 'bioql'
                }
            };

            // Update URL with notebook ID
            window.history.pushState({}, '', `?id=${this.currentNotebook.id}`);

            // Render the notebook
            this.renderNotebook();

            return data.notebook_id;
        } catch (error) {
            console.error('❌ Error creating notebook:', error);
            alert(`Failed to create notebook: ${error.message}`);
            return null;
        }
    }

    async loadNotebook(notebookId) {
        console.log(`📂 Loading notebook: ${notebookId}`);

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/notebook/${notebookId}`, {
                method: 'GET',
                headers: {
                    'X-API-Key': this.apiKey
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load notebook');
            }

            const data = await response.json();
            console.log('✅ Notebook loaded:', data);

            // Parse content if it's a string
            let cells = [];
            if (typeof data.content === 'string' && data.content) {
                try {
                    cells = JSON.parse(data.content);
                } catch (e) {
                    // If content is not JSON, create a default cell
                    cells = [{
                        id: this.generateCellId(),
                        type: 'code',
                        content: data.content || '',
                        outputs: []
                    }];
                }
            } else if (Array.isArray(data.content)) {
                cells = data.content;
            } else {
                // Create a default cell if no content
                cells = [{
                    id: this.generateCellId(),
                    type: 'code',
                    content: '# Welcome to BioQL Lab Notebook\n',
                    outputs: []
                }];
            }

            this.currentNotebook = {
                id: data.id,
                title: data.title,
                cells: cells,
                metadata: data.metadata || {},
                created_at: data.created_at,
                updated_at: data.updated_at
            };

            this.renderNotebook();
        } catch (error) {
            console.error('❌ Error loading notebook:', error);
            alert(`Failed to load notebook: ${error.message}`);
            // Create new notebook as fallback
            await this.createNewNotebook();
        }
    }

    async saveNotebook() {
        if (!this.currentNotebook || !this.currentNotebook.id) {
            console.warn('No notebook to save');
            return;
        }

        console.log('💾 Saving notebook...');

        // Update cell contents from editors
        this.updateCellContents();

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/notebook/${this.currentNotebook.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': this.apiKey
                },
                body: JSON.stringify({
                    title: this.currentNotebook.title,
                    content: JSON.stringify(this.currentNotebook.cells),
                    metadata: this.currentNotebook.metadata
                })
            });

            if (!response.ok) {
                throw new Error('Failed to save notebook');
            }

            console.log('✅ Notebook saved successfully');
            this.showNotification('Notebook saved', 'success');
        } catch (error) {
            console.error('❌ Error saving notebook:', error);
            this.showNotification(`Failed to save: ${error.message}`, 'error');
        }
    }

    renderNotebook() {
        if (!this.currentNotebook) return;

        console.log('🎨 Rendering notebook');

        // Update title
        document.getElementById('notebook-title').textContent = this.currentNotebook.title;

        // Clear existing cells
        const container = document.getElementById('cells-container');
        container.innerHTML = '';

        // Render each cell
        this.currentNotebook.cells.forEach((cell, index) => {
            this.renderCell(cell, index);
        });

        // Initialize Monaco editors after rendering
        setTimeout(() => {
            this.initializeEditors();
        }, 100);
    }

    renderCell(cell, index) {
        const container = document.getElementById('cells-container');

        const cellElement = document.createElement('div');
        cellElement.className = `notebook-cell ${cell.type}-cell`;
        cellElement.id = `cell-${cell.id}`;
        cellElement.dataset.cellId = cell.id;

        cellElement.innerHTML = `
            <div class="cell-header">
                <div class="cell-info">
                    <span class="cell-type-badge">${cell.type}</span>
                    <span class="cell-index">[${index + 1}]</span>
                </div>
                <div class="cell-actions">
                    <button class="cell-action-btn run-cell" onclick="window.notebookManager.runCell('${cell.id}')">
                        ▶ Run
                    </button>
                    <button class="cell-action-btn" onclick="window.notebookManager.moveCellUp('${cell.id}')">
                        ↑
                    </button>
                    <button class="cell-action-btn" onclick="window.notebookManager.moveCellDown('${cell.id}')">
                        ↓
                    </button>
                    <button class="cell-action-btn delete-cell" onclick="window.notebookManager.deleteCell('${cell.id}')">
                        🗑
                    </button>
                </div>
            </div>
            <div class="cell-editor" id="editor-${cell.id}"></div>
            <div class="cell-output" id="output-${cell.id}">
                ${cell.outputs && cell.outputs.length > 0 ? this.renderOutput(cell.outputs) : ''}
            </div>
            <div class="cell-add-buttons">
                <button class="add-cell-btn" onclick="window.notebookManager.addCell('code', '${cell.id}')">+ Code</button>
                <button class="add-cell-btn" onclick="window.notebookManager.addCell('markdown', '${cell.id}')">+ Markdown</button>
                <button class="add-cell-btn" onclick="window.notebookManager.addCell('bioql', '${cell.id}')">+ BioQL</button>
            </div>
        `;

        container.appendChild(cellElement);
    }

    initializeEditors() {
        if (typeof monaco === 'undefined') {
            console.error('Monaco editor not loaded');
            return;
        }

        this.currentNotebook.cells.forEach(cell => {
            const editorElement = document.getElementById(`editor-${cell.id}`);
            if (!editorElement) return;

            const language = cell.type === 'markdown' ? 'markdown' :
                            cell.type === 'bioql' ? 'sql' : 'python';

            const editor = monaco.editor.create(editorElement, {
                value: cell.content || '',
                language: language,
                theme: 'vs-dark',
                minimap: { enabled: false },
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                automaticLayout: true,
                fontSize: 13,
                tabSize: 4,
                wordWrap: 'on'
            });

            this.editors.set(cell.id, editor);

            // Auto-save on content change
            editor.onDidChangeModelContent(() => {
                this.markAsModified();
            });
        });
    }

    async runCell(cellId) {
        const cell = this.currentNotebook.cells.find(c => c.id === cellId);
        if (!cell) return;

        const editor = this.editors.get(cellId);
        if (!editor) return;

        const content = editor.getValue();
        const outputElement = document.getElementById(`output-${cellId}`);

        console.log(`▶️ Running cell ${cellId}:`, content);

        // Show loading
        outputElement.innerHTML = '<div class="cell-output-loading">⚙️ Executing...</div>';

        try {
            if (cell.type === 'bioql' || content.trim().startsWith('@bioql')) {
                // Execute BioQL command
                await this.executeBioQLCommand(content, cellId);
            } else if (cell.type === 'code') {
                // Execute Python code
                await this.executePythonCode(content, cellId);
            } else if (cell.type === 'markdown') {
                // Render markdown
                this.renderMarkdown(content, cellId);
            }
        } catch (error) {
            console.error('Error executing cell:', error);
            outputElement.innerHTML = `<div class="cell-output-error">❌ Error: ${error.message}</div>`;
        }
    }

    async executeBioQLCommand(content, cellId) {
        const outputElement = document.getElementById(`output-${cellId}`);

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/execute`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': this.apiKey
                },
                body: JSON.stringify({
                    code: content,
                    language: 'bioql',
                    notebook_id: this.currentNotebook.id,
                    cell_id: cellId
                })
            });

            const data = await response.json();

            if (data.success) {
                outputElement.innerHTML = `
                    <div class="cell-output-success">
                        <pre>${JSON.stringify(data.result, null, 2)}</pre>
                    </div>
                `;

                // Store output in cell
                const cell = this.currentNotebook.cells.find(c => c.id === cellId);
                if (cell) {
                    cell.outputs = [{ type: 'result', data: data.result }];
                }
            } else {
                throw new Error(data.error || 'Execution failed');
            }
        } catch (error) {
            outputElement.innerHTML = `<div class="cell-output-error">❌ Error: ${error.message}</div>`;
        }
    }

    async executePythonCode(content, cellId) {
        const outputElement = document.getElementById(`output-${cellId}`);
        outputElement.innerHTML = `
            <div class="cell-output-info">
                ℹ️ Python execution requires BioQL backend.
                Use @bioql commands for quantum computing tasks.
            </div>
        `;
    }

    renderMarkdown(content, cellId) {
        const outputElement = document.getElementById(`output-${cellId}`);
        // Simple markdown rendering (you can use a library like marked.js for better rendering)
        const html = content
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
            .replace(/\*(.*)\*/gim, '<em>$1</em>')
            .replace(/\n/gim, '<br>');

        outputElement.innerHTML = `<div class="cell-output-markdown">${html}</div>`;
    }

    addCell(type, afterCellId = null) {
        const newCell = {
            id: this.generateCellId(),
            type: type,
            content: type === 'markdown' ? '# New Markdown Cell' :
                     type === 'bioql' ? '@bioql\n# Write your BioQL command here' :
                     '# New code cell',
            outputs: []
        };

        if (afterCellId) {
            const index = this.currentNotebook.cells.findIndex(c => c.id === afterCellId);
            this.currentNotebook.cells.splice(index + 1, 0, newCell);
        } else {
            this.currentNotebook.cells.push(newCell);
        }

        this.renderNotebook();
        this.saveNotebook();
    }

    deleteCell(cellId) {
        if (this.currentNotebook.cells.length === 1) {
            alert('Cannot delete the last cell');
            return;
        }

        this.currentNotebook.cells = this.currentNotebook.cells.filter(c => c.id !== cellId);
        this.editors.delete(cellId);
        this.renderNotebook();
        this.saveNotebook();
    }

    moveCellUp(cellId) {
        const index = this.currentNotebook.cells.findIndex(c => c.id === cellId);
        if (index > 0) {
            [this.currentNotebook.cells[index], this.currentNotebook.cells[index - 1]] =
            [this.currentNotebook.cells[index - 1], this.currentNotebook.cells[index]];
            this.renderNotebook();
        }
    }

    moveCellDown(cellId) {
        const index = this.currentNotebook.cells.findIndex(c => c.id === cellId);
        if (index < this.currentNotebook.cells.length - 1) {
            [this.currentNotebook.cells[index], this.currentNotebook.cells[index + 1]] =
            [this.currentNotebook.cells[index + 1], this.currentNotebook.cells[index]];
            this.renderNotebook();
        }
    }

    updateCellContents() {
        this.editors.forEach((editor, cellId) => {
            const cell = this.currentNotebook.cells.find(c => c.id === cellId);
            if (cell) {
                cell.content = editor.getValue();
            }
        });
    }

    generateCellId() {
        return `cell_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    markAsModified() {
        this.currentNotebook.modified = true;
    }

    startAutosave() {
        this.autosaveInterval = setInterval(() => {
            if (this.currentNotebook && this.currentNotebook.modified) {
                this.saveNotebook();
                this.currentNotebook.modified = false;
            }
        }, 30000); // Autosave every 30 seconds
    }

    showNotification(message, type = 'info') {
        console.log(`📢 ${type.toUpperCase()}: ${message}`);
        // You can implement a toast notification here
    }

    renderOutput(outputs) {
        if (!outputs || outputs.length === 0) return '';

        return outputs.map(output => {
            if (output.type === 'result') {
                return `<pre>${JSON.stringify(output.data, null, 2)}</pre>`;
            } else if (output.type === 'error') {
                return `<div class="cell-output-error">${output.message}</div>`;
            }
            return '';
        }).join('');
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.notebookManager = new NotebookManager();
});
