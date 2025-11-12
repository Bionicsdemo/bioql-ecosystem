/**
 * BioQL AI Assistant Module
 *
 * Provides AI-powered insights, hypothesis generation, pattern recognition,
 * and natural language to BioQL command conversion using GPT-4 API.
 *
 * Features:
 * - Chat interface with streaming responses
 * - Hypothesis generation from notebook data
 * - Pattern detection in experimental results
 * - Experiment suggestions
 * - Natural language to @bioql command conversion
 * - Smart completions for @bioql commands
 * - Conversation history management
 */

class BioQLAIAssistant {
    constructor(apiKey = null) {
        this.apiKey = apiKey || this.loadApiKey();
        this.conversationHistory = [];
        this.maxHistoryLength = 50;
        this.apiEndpoint = 'https://api.openai.com/v1/chat/completions';
        this.model = 'gpt-4';
        this.streaming = true;

        // System prompts for different modes
        this.systemPrompts = {
            chat: `You are BioQL AI, an expert assistant for computational drug discovery and molecular modeling.
You help scientists analyze experiments, suggest hypotheses, detect patterns in data, and work with BioQL commands.
Always respond in English. Be concise, scientific, and actionable. Focus on molecular biology, drug discovery,
and computational chemistry insights.`,

            hypothesis: `You are a scientific hypothesis generator specializing in drug discovery and molecular modeling.
Analyze experimental data and suggest novel, testable hypotheses based on observed patterns.
Consider structure-activity relationships (SAR), binding affinities, molecular interactions, and chemical modifications.
Always respond in English with clear, numbered hypotheses and rationale.`,

            pattern: `You are a pattern recognition expert for scientific data analysis.
Detect statistically significant trends, correlations, and structure-activity relationships in experimental results.
Identify molecular features that correlate with desired properties (binding affinity, selectivity, ADME properties).
Always respond in English with specific, quantified insights and confidence levels.`,

            command: `You are a BioQL command converter. Convert natural language queries into valid BioQL commands.
BioQL syntax examples:
- @bioql similarity_search SMILES: CC(C)Cc1ccc(cc1)[C@@H](C)C(=O)O, threshold: 0.7
- @bioql predict_binding protein: "1ABC", ligand_smiles: "CCO"
- @bioql optimize_molecule smiles: "c1ccccc1", target_property: "solubility"
- @bioql dock ligand: "aspirin", protein: "COX2"
- @bioql analyze_adme smiles: "CC(=O)Oc1ccccc1C(=O)O"

Always respond with valid @bioql commands in English. Explain parameters briefly.`
        };

        // BioQL command templates for smart completions
        this.commandTemplates = [
            {
                command: '@bioql similarity_search',
                params: ['SMILES', 'threshold'],
                description: 'Find similar molecules in database',
                example: '@bioql similarity_search SMILES: CC(C)Cc1ccc(cc1)[C@@H](C)C(=O)O, threshold: 0.7'
            },
            {
                command: '@bioql predict_binding',
                params: ['protein', 'ligand_smiles'],
                description: 'Predict protein-ligand binding affinity',
                example: '@bioql predict_binding protein: "1ABC", ligand_smiles: "CCO"'
            },
            {
                command: '@bioql optimize_molecule',
                params: ['smiles', 'target_property'],
                description: 'Optimize molecular properties',
                example: '@bioql optimize_molecule smiles: "c1ccccc1", target_property: "solubility"'
            },
            {
                command: '@bioql dock',
                params: ['ligand', 'protein'],
                description: 'Perform molecular docking',
                example: '@bioql dock ligand: "aspirin", protein: "COX2"'
            },
            {
                command: '@bioql analyze_adme',
                params: ['smiles'],
                description: 'Analyze ADME properties',
                example: '@bioql analyze_adme smiles: "CC(=O)Oc1ccccc1C(=O)O"'
            },
            {
                command: '@bioql generate_analogues',
                params: ['smiles', 'count'],
                description: 'Generate molecular analogues',
                example: '@bioql generate_analogues smiles: "CCO", count: 10'
            },
            {
                command: '@bioql fragment_analysis',
                params: ['smiles'],
                description: 'Analyze molecular fragments',
                example: '@bioql fragment_analysis smiles: "CC(=O)Oc1ccccc1C(=O)O"'
            }
        ];

        this.initializeEventHandlers();
    }

    /**
     * Load API key from localStorage or environment
     */
    loadApiKey() {
        const stored = localStorage.getItem('bioql_openai_api_key');
        if (stored) {
            return stored;
        }
        console.warn('OpenAI API key not found. Use setApiKey() to configure.');
        return null;
    }

    /**
     * Set OpenAI API key
     */
    setApiKey(apiKey) {
        this.apiKey = apiKey;
        localStorage.setItem('bioql_openai_api_key', apiKey);
    }

    /**
     * Initialize event handlers for UI integration
     */
    initializeEventHandlers() {
        this.eventHandlers = {
            onMessageStart: null,
            onMessageChunk: null,
            onMessageComplete: null,
            onError: null
        };
    }

    /**
     * Add event listener
     */
    on(event, handler) {
        if (this.eventHandlers.hasOwnProperty(`on${event.charAt(0).toUpperCase()}${event.slice(1)}`)) {
            this.eventHandlers[`on${event.charAt(0).toUpperCase()}${event.slice(1)}`] = handler;
        }
    }

    /**
     * Send message to AI and get response
     * @param {string} message - User message
     * @param {string} mode - Mode: 'chat', 'hypothesis', 'pattern', 'command'
     * @param {boolean} stream - Enable streaming response
     * @returns {Promise<string>} AI response
     */
    async sendMessage(message, mode = 'chat', stream = true) {
        if (!this.apiKey) {
            throw new Error('OpenAI API key not configured. Use setApiKey() first.');
        }

        // Add user message to history
        this.addToHistory('user', message);

        // Prepare messages for API
        const messages = [
            { role: 'system', content: this.systemPrompts[mode] || this.systemPrompts.chat },
            ...this.conversationHistory.slice(-10) // Last 10 messages for context
        ];

        try {
            if (stream && this.streaming) {
                return await this.streamResponse(messages);
            } else {
                return await this.getResponse(messages);
            }
        } catch (error) {
            console.error('AI Assistant Error:', error);
            if (this.eventHandlers.onError) {
                this.eventHandlers.onError(error);
            }
            throw error;
        }
    }

    /**
     * Get non-streaming response
     */
    async getResponse(messages) {
        const response = await fetch(this.apiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.apiKey}`
            },
            body: JSON.stringify({
                model: this.model,
                messages: messages,
                temperature: 0.7,
                max_tokens: 1000
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(`OpenAI API Error: ${error.error?.message || 'Unknown error'}`);
        }

        const data = await response.json();
        const assistantMessage = data.choices[0].message.content;

        // Add to history
        this.addToHistory('assistant', assistantMessage);

        if (this.eventHandlers.onMessageComplete) {
            this.eventHandlers.onMessageComplete(assistantMessage);
        }

        return assistantMessage;
    }

    /**
     * Get streaming response
     */
    async streamResponse(messages) {
        const response = await fetch(this.apiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.apiKey}`
            },
            body: JSON.stringify({
                model: this.model,
                messages: messages,
                temperature: 0.7,
                max_tokens: 1000,
                stream: true
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(`OpenAI API Error: ${error.error?.message || 'Unknown error'}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';

        if (this.eventHandlers.onMessageStart) {
            this.eventHandlers.onMessageStart();
        }

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n').filter(line => line.trim() !== '');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') continue;

                    try {
                        const parsed = JSON.parse(data);
                        const content = parsed.choices[0]?.delta?.content;

                        if (content) {
                            fullResponse += content;
                            if (this.eventHandlers.onMessageChunk) {
                                this.eventHandlers.onMessageChunk(content);
                            }
                        }
                    } catch (e) {
                        console.warn('Failed to parse chunk:', e);
                    }
                }
            }
        }

        // Add to history
        this.addToHistory('assistant', fullResponse);

        if (this.eventHandlers.onMessageComplete) {
            this.eventHandlers.onMessageComplete(fullResponse);
        }

        return fullResponse;
    }

    /**
     * Generate hypotheses based on notebook data
     * @param {Object} notebookData - Notebook cells and experiment data
     * @returns {Promise<Object>} Generated hypotheses
     */
    async generateHypothesis(notebookData) {
        const prompt = this.buildHypothesisPrompt(notebookData);
        const response = await this.sendMessage(prompt, 'hypothesis', false);

        return this.parseHypothesesResponse(response);
    }

    /**
     * Build hypothesis generation prompt
     */
    buildHypothesisPrompt(notebookData) {
        let prompt = 'Analyze the following experimental data and generate 3-5 testable hypotheses:\n\n';

        // Extract experiment summaries
        if (notebookData.cells && notebookData.cells.length > 0) {
            prompt += '## Experiment History:\n';
            notebookData.cells.slice(-5).forEach((cell, idx) => {
                prompt += `\n### Experiment ${idx + 1}:\n`;
                if (cell.content) {
                    prompt += `Description: ${cell.content}\n`;
                }
                if (cell.results) {
                    prompt += `Results: ${JSON.stringify(cell.results, null, 2)}\n`;
                }
            });
        }

        // Add current focus if available
        if (notebookData.currentFocus) {
            prompt += `\n## Current Research Focus:\n${notebookData.currentFocus}\n`;
        }

        // Add patterns if available
        if (notebookData.observedPatterns) {
            prompt += `\n## Observed Patterns:\n${notebookData.observedPatterns.join('\n')}\n`;
        }

        prompt += '\n\nFor each hypothesis, provide:\n';
        prompt += '1. Clear statement of the hypothesis\n';
        prompt += '2. Rationale based on the data\n';
        prompt += '3. Suggested experiment to test it\n';
        prompt += '4. Expected outcome if hypothesis is correct\n';

        return prompt;
    }

    /**
     * Parse hypotheses from AI response
     */
    parseHypothesesResponse(response) {
        const hypotheses = [];
        const sections = response.split(/\d+\.\s+/).filter(s => s.trim());

        sections.forEach((section, idx) => {
            const lines = section.split('\n').filter(l => l.trim());
            hypotheses.push({
                id: `hyp_${Date.now()}_${idx}`,
                statement: lines[0] || section.substring(0, 100),
                rationale: this.extractSection(section, 'rationale'),
                suggestedExperiment: this.extractSection(section, 'experiment'),
                expectedOutcome: this.extractSection(section, 'outcome'),
                confidence: 'medium',
                timestamp: new Date().toISOString()
            });
        });

        return {
            hypotheses,
            rawResponse: response,
            generatedAt: new Date().toISOString()
        };
    }

    /**
     * Extract section from text
     */
    extractSection(text, keyword) {
        const patterns = {
            rationale: /rationale:?\s*(.+?)(?=\n\n|\n[A-Z]|$)/is,
            experiment: /(?:suggested\s+)?experiment:?\s*(.+?)(?=\n\n|\n[A-Z]|$)/is,
            outcome: /(?:expected\s+)?outcome:?\s*(.+?)(?=\n\n|\n[A-Z]|$)/is
        };

        const match = text.match(patterns[keyword]);
        return match ? match[1].trim() : '';
    }

    /**
     * Detect patterns in experimental results
     * @param {Array} results - Array of experimental results
     * @returns {Promise<Object>} Detected patterns
     */
    async detectPatterns(results) {
        const prompt = this.buildPatternPrompt(results);
        const response = await this.sendMessage(prompt, 'pattern', false);

        return this.parsePatternResponse(response, results);
    }

    /**
     * Build pattern detection prompt
     */
    buildPatternPrompt(results) {
        let prompt = 'Analyze the following experimental results and detect significant patterns:\n\n';

        prompt += '## Experimental Data:\n';
        prompt += JSON.stringify(results, null, 2);

        prompt += '\n\nIdentify:\n';
        prompt += '1. Structure-Activity Relationships (SAR)\n';
        prompt += '2. Correlations between molecular features and properties\n';
        prompt += '3. Trends in binding affinity, selectivity, or other metrics\n';
        prompt += '4. Outliers or unexpected results\n';
        prompt += '5. Quantified improvements (e.g., "fluorine at position 4 improves binding by 15%")\n';
        prompt += '\nFor each pattern, provide:\n';
        prompt += '- Description with specific values\n';
        prompt += '- Statistical significance (if applicable)\n';
        prompt += '- Confidence level (high/medium/low)\n';
        prompt += '- Actionable insights\n';

        return prompt;
    }

    /**
     * Parse pattern detection response
     */
    parsePatternResponse(response, originalData) {
        const patterns = [];
        const lines = response.split('\n').filter(l => l.trim());

        let currentPattern = null;

        lines.forEach(line => {
            // Detect new pattern (numbered or bulleted)
            if (/^[\d\-\*]+[\.\)]\s+/.test(line)) {
                if (currentPattern) {
                    patterns.push(currentPattern);
                }

                currentPattern = {
                    id: `pat_${Date.now()}_${patterns.length}`,
                    description: line.replace(/^[\d\-\*]+[\.\)]\s+/, '').trim(),
                    confidence: this.extractConfidence(line),
                    type: this.classifyPattern(line),
                    insights: [],
                    detectedAt: new Date().toISOString()
                };
            } else if (currentPattern && line.trim()) {
                // Add details to current pattern
                currentPattern.insights.push(line.trim());
            }
        });

        if (currentPattern) {
            patterns.push(currentPattern);
        }

        return {
            patterns,
            rawResponse: response,
            dataAnalyzed: originalData.length,
            detectedAt: new Date().toISOString()
        };
    }

    /**
     * Extract confidence level from text
     */
    extractConfidence(text) {
        const lower = text.toLowerCase();
        if (lower.includes('high confidence') || lower.includes('strong')) return 'high';
        if (lower.includes('low confidence') || lower.includes('weak')) return 'low';
        return 'medium';
    }

    /**
     * Classify pattern type
     */
    classifyPattern(text) {
        const lower = text.toLowerCase();
        if (lower.includes('sar') || lower.includes('structure-activity')) return 'sar';
        if (lower.includes('correlation')) return 'correlation';
        if (lower.includes('trend')) return 'trend';
        if (lower.includes('outlier')) return 'outlier';
        if (lower.includes('improvement') || lower.includes('increase') || lower.includes('decrease')) return 'quantified_change';
        return 'general';
    }

    /**
     * Suggest next experiment based on context
     * @param {Object} context - Current experimental context
     * @returns {Promise<Object>} Experiment suggestions
     */
    async suggestNextExperiment(context) {
        const prompt = this.buildSuggestionPrompt(context);
        const response = await this.sendMessage(prompt, 'chat', false);

        return this.parseExperimentSuggestions(response);
    }

    /**
     * Build experiment suggestion prompt
     */
    buildSuggestionPrompt(context) {
        let prompt = 'Based on the current research context, suggest 3 next experiments:\n\n';

        if (context.recentResults) {
            prompt += '## Recent Results:\n';
            prompt += JSON.stringify(context.recentResults, null, 2);
            prompt += '\n\n';
        }

        if (context.patterns) {
            prompt += '## Detected Patterns:\n';
            context.patterns.forEach(p => {
                prompt += `- ${p.description}\n`;
            });
            prompt += '\n';
        }

        if (context.hypotheses) {
            prompt += '## Active Hypotheses:\n';
            context.hypotheses.forEach(h => {
                prompt += `- ${h.statement}\n`;
            });
            prompt += '\n';
        }

        if (context.goal) {
            prompt += `## Research Goal:\n${context.goal}\n\n`;
        }

        prompt += 'For each suggested experiment, provide:\n';
        prompt += '1. Experiment description\n';
        prompt += '2. Rationale (why this experiment)\n';
        prompt += '3. Required resources/methods\n';
        prompt += '4. Expected insights\n';
        prompt += '5. Priority (high/medium/low)\n';

        return prompt;
    }

    /**
     * Parse experiment suggestions
     */
    parseExperimentSuggestions(response) {
        const suggestions = [];
        const sections = response.split(/(?:Experiment\s+\d+|^\d+\.)/i).filter(s => s.trim());

        sections.forEach((section, idx) => {
            if (idx === 0 && !section.match(/description|rationale/i)) return; // Skip preamble

            suggestions.push({
                id: `exp_${Date.now()}_${idx}`,
                description: this.extractSection(section, 'description') || section.split('\n')[0],
                rationale: this.extractSection(section, 'rationale'),
                resources: this.extractSection(section, 'resources') || this.extractSection(section, 'methods'),
                expectedInsights: this.extractSection(section, 'insights') || this.extractSection(section, 'outcome'),
                priority: this.extractPriority(section),
                suggestedAt: new Date().toISOString()
            });
        });

        return {
            suggestions,
            rawResponse: response,
            suggestedAt: new Date().toISOString()
        };
    }

    /**
     * Extract priority from text
     */
    extractPriority(text) {
        const lower = text.toLowerCase();
        if (lower.includes('high priority') || lower.includes('priority: high')) return 'high';
        if (lower.includes('low priority') || lower.includes('priority: low')) return 'low';
        return 'medium';
    }

    /**
     * Convert natural language to BioQL command
     * @param {string} naturalLanguage - User's natural language query
     * @returns {Promise<Object>} BioQL command and explanation
     */
    async convertToCommand(naturalLanguage) {
        const prompt = this.buildCommandPrompt(naturalLanguage);
        const response = await this.sendMessage(prompt, 'command', false);

        return this.parseCommandResponse(response);
    }

    /**
     * Build command conversion prompt
     */
    buildCommandPrompt(naturalLanguage) {
        let prompt = `Convert this natural language query to a BioQL command:\n\n"${naturalLanguage}"\n\n`;

        prompt += 'Available BioQL commands:\n';
        this.commandTemplates.forEach(template => {
            prompt += `- ${template.command}: ${template.description}\n`;
            prompt += `  Example: ${template.example}\n`;
        });

        prompt += '\nProvide:\n';
        prompt += '1. The exact BioQL command to execute\n';
        prompt += '2. Brief explanation of each parameter\n';
        prompt += '3. Expected output type\n';

        return prompt;
    }

    /**
     * Parse command conversion response
     */
    parseCommandResponse(response) {
        // Extract BioQL command (usually in code blocks or starts with @bioql)
        const commandMatch = response.match(/@bioql\s+[^\n]+/i);
        const command = commandMatch ? commandMatch[0] : '';

        // Extract explanation
        const lines = response.split('\n').filter(l => l.trim() && !l.includes('@bioql'));
        const explanation = lines.join('\n').trim();

        return {
            command,
            explanation,
            rawResponse: response,
            convertedAt: new Date().toISOString()
        };
    }

    /**
     * Get smart completions for partial @bioql commands
     * @param {string} partial - Partial command text
     * @returns {Array} Completion suggestions
     */
    getSmartCompletions(partial) {
        const completions = [];

        // Match command templates
        this.commandTemplates.forEach(template => {
            if (template.command.toLowerCase().includes(partial.toLowerCase())) {
                completions.push({
                    type: 'command',
                    text: template.command,
                    description: template.description,
                    example: template.example,
                    params: template.params
                });
            }
        });

        // If user has typed a command, suggest parameters
        const currentCommand = this.commandTemplates.find(t =>
            partial.toLowerCase().startsWith(t.command.toLowerCase())
        );

        if (currentCommand) {
            const usedParams = this.extractUsedParameters(partial);
            const remainingParams = currentCommand.params.filter(p => !usedParams.includes(p));

            remainingParams.forEach(param => {
                completions.push({
                    type: 'parameter',
                    text: `${param}: `,
                    description: `Add ${param} parameter`,
                    command: currentCommand.command
                });
            });
        }

        return completions;
    }

    /**
     * Extract already used parameters from partial command
     */
    extractUsedParameters(partial) {
        const params = [];
        const matches = partial.matchAll(/(\w+):\s*[^,]+/g);

        for (const match of matches) {
            params.push(match[1]);
        }

        return params;
    }

    /**
     * Add message to conversation history
     */
    addToHistory(role, content) {
        this.conversationHistory.push({ role, content });

        // Trim history if too long
        if (this.conversationHistory.length > this.maxHistoryLength) {
            this.conversationHistory = this.conversationHistory.slice(-this.maxHistoryLength);
        }

        this.saveHistory();
    }

    /**
     * Clear conversation history
     */
    clearHistory() {
        this.conversationHistory = [];
        this.saveHistory();
    }

    /**
     * Get conversation history
     */
    getHistory() {
        return this.conversationHistory;
    }

    /**
     * Save history to localStorage
     */
    saveHistory() {
        try {
            localStorage.setItem('bioql_ai_history', JSON.stringify(this.conversationHistory));
        } catch (e) {
            console.warn('Failed to save conversation history:', e);
        }
    }

    /**
     * Load history from localStorage
     */
    loadHistory() {
        try {
            const stored = localStorage.getItem('bioql_ai_history');
            if (stored) {
                this.conversationHistory = JSON.parse(stored);
            }
        } catch (e) {
            console.warn('Failed to load conversation history:', e);
        }
    }

    /**
     * Export conversation history
     */
    exportHistory() {
        return {
            conversations: this.conversationHistory,
            exportedAt: new Date().toISOString(),
            version: '1.0'
        };
    }

    /**
     * Import conversation history
     */
    importHistory(data) {
        if (data.conversations && Array.isArray(data.conversations)) {
            this.conversationHistory = data.conversations;
            this.saveHistory();
        }
    }
}

/**
 * UI Integration Helper
 * Creates and manages AI assistant UI components
 */
class BioQLAIAssistantUI {
    constructor(assistant, containerId) {
        this.assistant = assistant;
        this.container = document.getElementById(containerId);
        this.messageContainer = null;
        this.inputField = null;
        this.sendButton = null;

        this.initialize();
    }

    /**
     * Initialize UI components
     */
    initialize() {
        if (!this.container) {
            console.error('Container not found for AI Assistant UI');
            return;
        }

        this.container.innerHTML = `
            <div class="ai-assistant-panel">
                <div class="ai-assistant-header">
                    <h3>BioQL AI Assistant</h3>
                    <div class="ai-assistant-controls">
                        <button id="ai-clear-history" class="btn-icon" title="Clear History">
                            <i class="fas fa-trash"></i>
                        </button>
                        <button id="ai-export-history" class="btn-icon" title="Export History">
                            <i class="fas fa-download"></i>
                        </button>
                    </div>
                </div>

                <div class="ai-mode-selector">
                    <button class="mode-btn active" data-mode="chat">Chat</button>
                    <button class="mode-btn" data-mode="hypothesis">Hypothesis</button>
                    <button class="mode-btn" data-mode="pattern">Patterns</button>
                    <button class="mode-btn" data-mode="command">Commands</button>
                </div>

                <div class="ai-messages" id="ai-messages"></div>

                <div class="ai-input-container">
                    <textarea
                        id="ai-input"
                        class="ai-input"
                        placeholder="Ask BioQL AI anything..."
                        rows="3"
                    ></textarea>
                    <button id="ai-send" class="btn-primary">
                        <i class="fas fa-paper-plane"></i> Send
                    </button>
                </div>
            </div>
        `;

        this.messageContainer = document.getElementById('ai-messages');
        this.inputField = document.getElementById('ai-input');
        this.sendButton = document.getElementById('ai-send');

        this.attachEventListeners();
        this.loadConversation();
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Send message
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.inputField.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Mode selection
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
            });
        });

        // Clear history
        document.getElementById('ai-clear-history').addEventListener('click', () => {
            if (confirm('Clear conversation history?')) {
                this.assistant.clearHistory();
                this.messageContainer.innerHTML = '';
            }
        });

        // Export history
        document.getElementById('ai-export-history').addEventListener('click', () => {
            this.exportHistory();
        });

        // AI event handlers
        this.assistant.on('messageChunk', (chunk) => this.appendToLastMessage(chunk));
        this.assistant.on('messageComplete', () => this.scrollToBottom());
        this.assistant.on('error', (error) => this.showError(error));
    }

    /**
     * Send message to AI
     */
    async sendMessage() {
        const message = this.inputField.value.trim();
        if (!message) return;

        const mode = document.querySelector('.mode-btn.active').dataset.mode;

        // Add user message to UI
        this.addMessage('user', message);
        this.inputField.value = '';

        // Disable input while processing
        this.setInputEnabled(false);

        try {
            // Create assistant message placeholder
            const assistantMsgId = this.addMessage('assistant', '');

            // Send to AI
            await this.assistant.sendMessage(message, mode, true);

            this.setInputEnabled(true);
            this.inputField.focus();
        } catch (error) {
            this.setInputEnabled(true);
            this.showError(error);
        }
    }

    /**
     * Add message to UI
     */
    addMessage(role, content) {
        const msgId = `msg_${Date.now()}`;
        const msgDiv = document.createElement('div');
        msgDiv.id = msgId;
        msgDiv.className = `ai-message ai-message-${role}`;
        msgDiv.innerHTML = `
            <div class="ai-message-avatar">
                <i class="fas fa-${role === 'user' ? 'user' : 'robot'}"></i>
            </div>
            <div class="ai-message-content">${this.formatMessage(content)}</div>
        `;

        this.messageContainer.appendChild(msgDiv);
        this.scrollToBottom();

        return msgId;
    }

    /**
     * Append content to last message
     */
    appendToLastMessage(content) {
        const lastMsg = this.messageContainer.querySelector('.ai-message-assistant:last-child .ai-message-content');
        if (lastMsg) {
            lastMsg.innerHTML += content;
            this.scrollToBottom();
        }
    }

    /**
     * Format message with markdown-like syntax
     */
    formatMessage(content) {
        if (!content) return '<span class="typing-indicator">...</span>';

        return content
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }

    /**
     * Show error message
     */
    showError(error) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'ai-error';
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <span>${error.message}</span>
        `;
        this.messageContainer.appendChild(errorDiv);
        this.scrollToBottom();
    }

    /**
     * Enable/disable input
     */
    setInputEnabled(enabled) {
        this.inputField.disabled = !enabled;
        this.sendButton.disabled = !enabled;
    }

    /**
     * Scroll to bottom of messages
     */
    scrollToBottom() {
        this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
    }

    /**
     * Load conversation from history
     */
    loadConversation() {
        this.assistant.loadHistory();
        const history = this.assistant.getHistory();

        history.forEach(msg => {
            this.addMessage(msg.role, msg.content);
        });
    }

    /**
     * Export conversation history
     */
    exportHistory() {
        const data = this.assistant.exportHistory();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `bioql-ai-history-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { BioQLAIAssistant, BioQLAIAssistantUI };
}
