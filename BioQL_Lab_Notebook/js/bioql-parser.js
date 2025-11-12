/**
 * BioQL Parser Module
 * Parses @bioql commands from text cells and executes them via BioQL backend API
 * @module bioql-parser
 */

const BIOQL_API_BASE = 'http://167.71.86.90:5002';
const POLL_INTERVAL = 2000; // Poll every 2 seconds for job status

/**
 * Command patterns for different BioQL operations
 */
const COMMAND_PATTERNS = {
    dock: /^@bioql\s+dock\s+(.+?)\s+to\s+(.+?)$/i,
    adme: /^@bioql\s+predict\s+ADME\s+for\s+(.+?)$/i,
    screen: /^@bioql\s+screen\s+(.+?)\s+against\s+(.+?)$/i,
    visualize: /^@bioql\s+visualize\s+(.+?)\s+in\s+3D$/i,
    compare: /^@bioql\s+compare\s+(.+?)\s+vs\s+(.+?)$/i,
    suggest: /^@bioql\s+suggest\s+molecules\s+similar\s+to\s+(.+?)$/i,
    export: /^@bioql\s+export\s+experiment\s+to\s+paper$/i
};

/**
 * Parse BioQL command from text
 * @param {string} text - Text containing BioQL command
 * @returns {Object|null} Parsed command object or null if no command found
 */
function parseBioQLCommand(text) {
    const trimmedText = text.trim();

    for (const [commandType, pattern] of Object.entries(COMMAND_PATTERNS)) {
        const match = trimmedText.match(pattern);
        if (match) {
            return {
                type: commandType,
                raw: trimmedText,
                params: match.slice(1)
            };
        }
    }

    return null;
}

/**
 * Execute BioQL command and return results
 * @param {Object} command - Parsed command object
 * @param {HTMLElement} outputElement - DOM element to render results
 * @returns {Promise<Object>} Command execution results
 */
async function executeBioQLCommand(command, outputElement) {
    try {
        showProgress(outputElement, `Executing: ${command.raw}`);

        switch (command.type) {
            case 'dock':
                return await executeDocking(command.params[0], command.params[1], outputElement);
            case 'adme':
                return await executePredictADME(command.params[0], outputElement);
            case 'screen':
                return await executeScreening(command.params[0], command.params[1], outputElement);
            case 'visualize':
                return await executeVisualization(command.params[0], outputElement);
            case 'compare':
                return await executeComparison(command.params[0], command.params[1], outputElement);
            case 'suggest':
                return await executeSuggestion(command.params[0], outputElement);
            case 'export':
                return await executeExport(outputElement);
            default:
                throw new Error(`Unknown command type: ${command.type}`);
        }
    } catch (error) {
        handleError(error, outputElement);
        throw error;
    }
}

/**
 * Execute molecular docking
 * @param {string} molecule - Molecule identifier or SMILES
 * @param {string} protein - Protein identifier or PDB ID
 * @param {HTMLElement} outputElement - Output container
 * @returns {Promise<Object>} Docking results
 */
async function executeDocking(molecule, protein, outputElement) {
    const jobId = await submitJob('/api/dock', {
        molecule: molecule.trim(),
        protein: protein.trim()
    });

    updateProgress(outputElement, `Job submitted: ${jobId}`, 10);

    const result = await pollJobStatus(jobId, outputElement, 'Docking');

    renderDockingResults(result, outputElement);
    return result;
}

/**
 * Execute ADME prediction
 * @param {string} molecule - Molecule identifier or SMILES
 * @param {HTMLElement} outputElement - Output container
 * @returns {Promise<Object>} ADME prediction results
 */
async function executePredictADME(molecule, outputElement) {
    const jobId = await submitJob('/api/predict/adme', {
        molecule: molecule.trim()
    });

    updateProgress(outputElement, `Job submitted: ${jobId}`, 10);

    const result = await pollJobStatus(jobId, outputElement, 'ADME Prediction');

    renderADMEResults(result, outputElement);
    return result;
}

/**
 * Execute library screening
 * @param {string} library - Library identifier
 * @param {string} target - Target protein identifier
 * @param {HTMLElement} outputElement - Output container
 * @returns {Promise<Object>} Screening results
 */
async function executeScreening(library, target, outputElement) {
    const jobId = await submitJob('/api/screen', {
        library: library.trim(),
        target: target.trim()
    });

    updateProgress(outputElement, `Job submitted: ${jobId}`, 10);

    const result = await pollJobStatus(jobId, outputElement, 'Virtual Screening');

    renderScreeningResults(result, outputElement);
    return result;
}

/**
 * Execute 3D visualization
 * @param {string} resultId - Result identifier to visualize
 * @param {HTMLElement} outputElement - Output container
 * @returns {Promise<Object>} Visualization data
 */
async function executeVisualization(resultId, outputElement) {
    updateProgress(outputElement, 'Loading visualization...', 30);

    const response = await apiRequest('/api/visualize', {
        result_id: resultId.trim()
    });

    updateProgress(outputElement, 'Rendering 3D structure...', 70);

    render3DVisualization(response.data, outputElement);

    updateProgress(outputElement, 'Complete', 100);
    return response.data;
}

/**
 * Execute molecule comparison
 * @param {string} mol1 - First molecule identifier
 * @param {string} mol2 - Second molecule identifier
 * @param {HTMLElement} outputElement - Output container
 * @returns {Promise<Object>} Comparison results
 */
async function executeComparison(mol1, mol2, outputElement) {
    updateProgress(outputElement, 'Comparing molecules...', 30);

    const response = await apiRequest('/api/compare', {
        molecule1: mol1.trim(),
        molecule2: mol2.trim()
    });

    updateProgress(outputElement, 'Analyzing differences...', 70);

    renderComparisonResults(response.data, outputElement);

    updateProgress(outputElement, 'Complete', 100);
    return response.data;
}

/**
 * Execute molecule suggestion
 * @param {string} scaffold - Scaffold molecule identifier
 * @param {HTMLElement} outputElement - Output container
 * @returns {Promise<Object>} Suggested molecules
 */
async function executeSuggestion(scaffold, outputElement) {
    const jobId = await submitJob('/api/suggest', {
        scaffold: scaffold.trim()
    });

    updateProgress(outputElement, `Job submitted: ${jobId}`, 10);

    const result = await pollJobStatus(jobId, outputElement, 'Molecule Suggestion');

    renderSuggestionResults(result, outputElement);
    return result;
}

/**
 * Execute experiment export to paper format
 * @param {HTMLElement} outputElement - Output container
 * @returns {Promise<Object>} Export results
 */
async function executeExport(outputElement) {
    updateProgress(outputElement, 'Gathering experiment data...', 20);

    const response = await apiRequest('/api/export/paper', {
        format: 'latex'
    });

    updateProgress(outputElement, 'Generating paper format...', 70);

    renderExportResults(response.data, outputElement);

    updateProgress(outputElement, 'Complete', 100);
    return response.data;
}

/**
 * Submit job to BioQL API
 * @param {string} endpoint - API endpoint
 * @param {Object} data - Request payload
 * @returns {Promise<string>} Job ID
 */
async function submitJob(endpoint, data) {
    const response = await apiRequest(endpoint, data);

    if (!response.job_id) {
        throw new Error('No job ID returned from API');
    }

    return response.job_id;
}

/**
 * Poll job status until completion
 * @param {string} jobId - Job identifier
 * @param {HTMLElement} outputElement - Output container for progress
 * @param {string} taskName - Human-readable task name
 * @returns {Promise<Object>} Job results
 */
async function pollJobStatus(jobId, outputElement, taskName) {
    let attempts = 0;
    const maxAttempts = 300; // 10 minutes max

    while (attempts < maxAttempts) {
        const status = await apiRequest(`/api/job/${jobId}`);

        if (status.status === 'completed') {
            updateProgress(outputElement, `${taskName} complete`, 100);
            return status.result;
        } else if (status.status === 'failed') {
            throw new Error(`Job failed: ${status.error || 'Unknown error'}`);
        } else if (status.status === 'running') {
            const progress = status.progress || (30 + (attempts * 2));
            updateProgress(
                outputElement,
                `${taskName} in progress... ${status.message || ''}`,
                Math.min(progress, 90)
            );
        }

        await sleep(POLL_INTERVAL);
        attempts++;
    }

    throw new Error('Job timeout: exceeded maximum wait time');
}

/**
 * Make API request to BioQL backend
 * @param {string} endpoint - API endpoint path
 * @param {Object} data - Request payload
 * @param {string} method - HTTP method (default: POST)
 * @returns {Promise<Object>} Response data
 */
async function apiRequest(endpoint, data = null, method = 'POST') {
    const url = `${BIOQL_API_BASE}${endpoint}`;

    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    };

    if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
    }

    const response = await fetch(url, options);

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
            errorData.error ||
            errorData.message ||
            `API request failed: ${response.status} ${response.statusText}`
        );
    }

    return await response.json();
}

/**
 * Show initial progress indicator
 * @param {HTMLElement} element - Container element
 * @param {string} message - Progress message
 */
function showProgress(element, message) {
    element.innerHTML = `
        <div class="bioql-progress-container">
            <div class="bioql-progress-message">${escapeHtml(message)}</div>
            <div class="bioql-progress-bar">
                <div class="bioql-progress-fill" style="width: 0%"></div>
            </div>
            <div class="bioql-progress-percent">0%</div>
        </div>
    `;
}

/**
 * Update progress indicator
 * @param {HTMLElement} element - Container element
 * @param {string} message - Progress message
 * @param {number} percent - Progress percentage (0-100)
 */
function updateProgress(element, message, percent) {
    const container = element.querySelector('.bioql-progress-container');
    if (!container) {
        showProgress(element, message);
        return;
    }

    const messageEl = container.querySelector('.bioql-progress-message');
    const fillEl = container.querySelector('.bioql-progress-fill');
    const percentEl = container.querySelector('.bioql-progress-percent');

    if (messageEl) messageEl.textContent = message;
    if (fillEl) fillEl.style.width = `${percent}%`;
    if (percentEl) percentEl.textContent = `${Math.round(percent)}%`;
}

/**
 * Render docking results
 * @param {Object} result - Docking result data
 * @param {HTMLElement} element - Output container
 */
function renderDockingResults(result, element) {
    const html = `
        <div class="bioql-results">
            <h3>Docking Results</h3>
            <div class="bioql-result-section">
                <h4>Binding Affinity</h4>
                <p class="bioql-score">Score: ${result.binding_affinity || 'N/A'} kcal/mol</p>
            </div>
            <div class="bioql-result-section">
                <h4>Key Interactions</h4>
                <ul>
                    ${(result.interactions || []).map(int =>
                        `<li>${escapeHtml(int.type)}: ${escapeHtml(int.residue)} (${int.distance} Å)</li>`
                    ).join('')}
                </ul>
            </div>
            <div class="bioql-result-section">
                <h4>Pose Information</h4>
                <p>RMSD: ${result.rmsd || 'N/A'} Å</p>
                <p>Conformations analyzed: ${result.num_conformations || 'N/A'}</p>
            </div>
        </div>
    `;

    element.innerHTML = html;
}

/**
 * Render ADME prediction results
 * @param {Object} result - ADME prediction data
 * @param {HTMLElement} element - Output container
 */
function renderADMEResults(result, element) {
    const html = `
        <div class="bioql-results">
            <h3>ADME Predictions</h3>
            <table class="bioql-table">
                <thead>
                    <tr>
                        <th>Property</th>
                        <th>Value</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Absorption (Caco-2)</td>
                        <td>${result.absorption || 'N/A'}</td>
                        <td>${getPropertyStatus(result.absorption_status)}</td>
                    </tr>
                    <tr>
                        <td>BBB Penetration</td>
                        <td>${result.bbb_penetration || 'N/A'}</td>
                        <td>${getPropertyStatus(result.bbb_status)}</td>
                    </tr>
                    <tr>
                        <td>CYP2D6 Inhibition</td>
                        <td>${result.cyp2d6 || 'N/A'}</td>
                        <td>${getPropertyStatus(result.cyp2d6_status)}</td>
                    </tr>
                    <tr>
                        <td>Half-life (t1/2)</td>
                        <td>${result.half_life || 'N/A'}</td>
                        <td>${getPropertyStatus(result.half_life_status)}</td>
                    </tr>
                    <tr>
                        <td>Clearance</td>
                        <td>${result.clearance || 'N/A'}</td>
                        <td>${getPropertyStatus(result.clearance_status)}</td>
                    </tr>
                </tbody>
            </table>
            <div class="bioql-result-section">
                <h4>Lipinski's Rule of Five</h4>
                <p>Violations: ${result.lipinski_violations || 0}</p>
            </div>
        </div>
    `;

    element.innerHTML = html;
}

/**
 * Render screening results
 * @param {Object} result - Screening result data
 * @param {HTMLElement} element - Output container
 */
function renderScreeningResults(result, element) {
    const hits = result.hits || [];

    const html = `
        <div class="bioql-results">
            <h3>Screening Results</h3>
            <p class="bioql-summary">
                Screened ${result.total_compounds || 0} compounds,
                found ${hits.length} hits (threshold: ${result.threshold || 'N/A'})
            </p>
            <div class="bioql-result-section">
                <h4>Top Hits</h4>
                <table class="bioql-table">
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Compound</th>
                            <th>Score</th>
                            <th>MW</th>
                            <th>LogP</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${hits.slice(0, 10).map((hit, idx) => `
                            <tr>
                                <td>${idx + 1}</td>
                                <td>${escapeHtml(hit.name || hit.id)}</td>
                                <td>${hit.score || 'N/A'}</td>
                                <td>${hit.molecular_weight || 'N/A'}</td>
                                <td>${hit.logp || 'N/A'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;

    element.innerHTML = html;
}

/**
 * Render 3D visualization
 * @param {Object} data - Visualization data
 * @param {HTMLElement} element - Output container
 */
function render3DVisualization(data, element) {
    const html = `
        <div class="bioql-results">
            <h3>3D Visualization</h3>
            <div class="bioql-3d-viewer" id="bioql-viewer-${Date.now()}">
                <div class="bioql-viewer-placeholder">
                    <p>3D viewer loading...</p>
                    <p class="bioql-note">
                        Visualization data: ${data.format || 'PDB'}
                    </p>
                </div>
            </div>
            <div class="bioql-viewer-controls">
                <button onclick="resetView()">Reset View</button>
                <button onclick="toggleRepresentation()">Toggle Style</button>
                <button onclick="downloadStructure()">Download</button>
            </div>
        </div>
    `;

    element.innerHTML = html;

    // Note: Actual 3D rendering would require a library like NGL, 3Dmol.js, or Mol*
    // This is a placeholder for the visualization infrastructure
}

/**
 * Render comparison results
 * @param {Object} data - Comparison data
 * @param {HTMLElement} element - Output container
 */
function renderComparisonResults(data, element) {
    const html = `
        <div class="bioql-results">
            <h3>Molecule Comparison</h3>
            <div class="bioql-comparison-grid">
                <div class="bioql-comparison-col">
                    <h4>${escapeHtml(data.molecule1_name || 'Molecule 1')}</h4>
                    <ul>
                        <li>MW: ${data.mol1_mw || 'N/A'}</li>
                        <li>LogP: ${data.mol1_logp || 'N/A'}</li>
                        <li>HBD: ${data.mol1_hbd || 'N/A'}</li>
                        <li>HBA: ${data.mol1_hba || 'N/A'}</li>
                    </ul>
                </div>
                <div class="bioql-comparison-col">
                    <h4>Similarity</h4>
                    <p class="bioql-similarity-score">
                        ${data.tanimoto_similarity || 'N/A'}
                    </p>
                    <p>Tanimoto Coefficient</p>
                </div>
                <div class="bioql-comparison-col">
                    <h4>${escapeHtml(data.molecule2_name || 'Molecule 2')}</h4>
                    <ul>
                        <li>MW: ${data.mol2_mw || 'N/A'}</li>
                        <li>LogP: ${data.mol2_logp || 'N/A'}</li>
                        <li>HBD: ${data.mol2_hbd || 'N/A'}</li>
                        <li>HBA: ${data.mol2_hba || 'N/A'}</li>
                    </ul>
                </div>
            </div>
            <div class="bioql-result-section">
                <h4>Structural Differences</h4>
                <p>${data.differences || 'No major differences detected'}</p>
            </div>
        </div>
    `;

    element.innerHTML = html;
}

/**
 * Render suggestion results
 * @param {Object} result - Suggestion data
 * @param {HTMLElement} element - Output container
 */
function renderSuggestionResults(result, element) {
    const suggestions = result.suggestions || [];

    const html = `
        <div class="bioql-results">
            <h3>Molecule Suggestions</h3>
            <p class="bioql-summary">
                Generated ${suggestions.length} similar molecules based on scaffold
            </p>
            <div class="bioql-result-section">
                <h4>Suggested Molecules</h4>
                <table class="bioql-table">
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>SMILES</th>
                            <th>Similarity</th>
                            <th>Drug-likeness</th>
                            <th>Synthesizability</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${suggestions.map((sug, idx) => `
                            <tr>
                                <td>${idx + 1}</td>
                                <td><code>${escapeHtml(sug.smiles)}</code></td>
                                <td>${sug.similarity || 'N/A'}</td>
                                <td>${sug.qed || 'N/A'}</td>
                                <td>${sug.sa_score || 'N/A'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;

    element.innerHTML = html;
}

/**
 * Render export results
 * @param {Object} data - Export data
 * @param {HTMLElement} element - Output container
 */
function renderExportResults(data, element) {
    const html = `
        <div class="bioql-results">
            <h3>Experiment Export</h3>
            <div class="bioql-result-section">
                <p class="bioql-success">
                    Experiment exported successfully in ${data.format || 'LaTeX'} format
                </p>
                <div class="bioql-export-actions">
                    <button onclick="downloadExport('${data.file_id}')">
                        Download ${data.format || 'LaTeX'} File
                    </button>
                    <button onclick="copyToClipboard('${data.content_id}')">
                        Copy to Clipboard
                    </button>
                </div>
            </div>
            <div class="bioql-result-section">
                <h4>Export Details</h4>
                <ul>
                    <li>Format: ${data.format || 'LaTeX'}</li>
                    <li>Size: ${data.size || 'N/A'} KB</li>
                    <li>Sections: ${data.sections || 'N/A'}</li>
                    <li>Figures: ${data.figures || 0}</li>
                    <li>Tables: ${data.tables || 0}</li>
                </ul>
            </div>
        </div>
    `;

    element.innerHTML = html;
}

/**
 * Handle errors and display to user
 * @param {Error} error - Error object
 * @param {HTMLElement} element - Output container
 */
function handleError(error, element) {
    console.error('BioQL Error:', error);

    const html = `
        <div class="bioql-error">
            <h3>Error</h3>
            <p class="bioql-error-message">${escapeHtml(error.message)}</p>
            <details>
                <summary>Technical Details</summary>
                <pre>${escapeHtml(error.stack || 'No stack trace available')}</pre>
            </details>
            <div class="bioql-error-actions">
                <button onclick="retryLastCommand()">Retry</button>
                <button onclick="reportBug()">Report Bug</button>
            </div>
        </div>
    `;

    element.innerHTML = html;
}

/**
 * Get status badge for ADME properties
 * @param {string} status - Property status
 * @returns {string} HTML for status badge
 */
function getPropertyStatus(status) {
    const statusMap = {
        good: '<span class="bioql-status bioql-status-good">Good</span>',
        moderate: '<span class="bioql-status bioql-status-moderate">Moderate</span>',
        poor: '<span class="bioql-status bioql-status-poor">Poor</span>'
    };

    return statusMap[status] || '<span class="bioql-status">Unknown</span>';
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    if (text == null) return '';

    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

/**
 * Sleep utility for polling
 * @param {number} ms - Milliseconds to sleep
 * @returns {Promise<void>}
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Process all BioQL commands in a notebook cell
 * @param {HTMLElement} cell - Notebook cell element
 */
async function processCellBioQLCommands(cell) {
    const textContent = cell.querySelector('.cell-content')?.textContent || '';
    const command = parseBioQLCommand(textContent);

    if (command) {
        const outputDiv = cell.querySelector('.cell-output') ||
                         createOutputDiv(cell);

        try {
            await executeBioQLCommand(command, outputDiv);
        } catch (error) {
            console.error('Failed to execute BioQL command:', error);
        }
    }
}

/**
 * Create output div for cell if it doesn't exist
 * @param {HTMLElement} cell - Cell element
 * @returns {HTMLElement} Output div
 */
function createOutputDiv(cell) {
    let outputDiv = cell.querySelector('.cell-output');

    if (!outputDiv) {
        outputDiv = document.createElement('div');
        outputDiv.className = 'cell-output bioql-output';
        cell.appendChild(outputDiv);
    }

    return outputDiv;
}

/**
 * Initialize BioQL parser for notebook
 * Scans all cells and processes BioQL commands
 */
function initializeBioQLParser() {
    console.log('Initializing BioQL Parser...');

    // Find all cells with BioQL commands
    const cells = document.querySelectorAll('.notebook-cell');

    cells.forEach(cell => {
        const textContent = cell.textContent || '';
        if (textContent.includes('@bioql')) {
            // Add button to execute BioQL command
            addExecuteButton(cell);
        }
    });

    console.log(`BioQL Parser initialized. Found ${cells.length} cells.`);
}

/**
 * Add execute button to cell
 * @param {HTMLElement} cell - Cell element
 */
function addExecuteButton(cell) {
    const existingButton = cell.querySelector('.bioql-execute-btn');
    if (existingButton) return;

    const button = document.createElement('button');
    button.className = 'bioql-execute-btn';
    button.textContent = 'Execute BioQL';
    button.onclick = () => processCellBioQLCommands(cell);

    cell.appendChild(button);
}

// Export module functions
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        parseBioQLCommand,
        executeBioQLCommand,
        initializeBioQLParser,
        processCellBioQLCommands,
        BIOQL_API_BASE,
        COMMAND_PATTERNS
    };
}

// Auto-initialize if in browser environment
if (typeof window !== 'undefined') {
    window.BioQLParser = {
        parseBioQLCommand,
        executeBioQLCommand,
        initializeBioQLParser,
        processCellBioQLCommands,
        BIOQL_API_BASE,
        COMMAND_PATTERNS
    };

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeBioQLParser);
    } else {
        initializeBioQLParser();
    }
}
