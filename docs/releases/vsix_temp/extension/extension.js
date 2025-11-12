const vscode = require('vscode');
const { spawn } = require('child_process');
const axios = require('axios');

let outputChannel;

// Global conversation state storage (persists across chat messages)
const conversationStates = new Map();

/**
 * Activate BioQL VS Code Extension
 */
function activate(context) {
    outputChannel = vscode.window.createOutputChannel('BioQL Assistant');
    outputChannel.appendLine('🚀 BioQL Code Assistant activated!');

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('bioql.generateCode', generateCode),
        vscode.commands.registerCommand('bioql.fixCode', fixCode),
        vscode.commands.registerCommand('bioql.explainCode', explainCode),
        vscode.commands.registerCommand('bioql.optimizeCircuit', optimizeCircuit),
        vscode.commands.registerCommand('bioql.runOnQuantumComputer', runOnQuantumComputer),
        vscode.commands.registerCommand('bioql.insertCode', insertCode),
        vscode.commands.registerCommand('bioql.applyFixes', applyFixes),
        // CRISPR-QAI commands (NEW in v4.4.0)
        vscode.commands.registerCommand('bioql.designCRISPRGuide', designCRISPRGuide),
        vscode.commands.registerCommand('bioql.designCRISPRTherapy', designCRISPRTherapy),
        vscode.commands.registerCommand('bioql.rankCRISPRGuides', rankCRISPRGuides),
        vscode.commands.registerCommand('bioql.analyzeCRISPROfftargets', analyzeCRISPROfftargets),
        // BioQL 5.6.0+ Drug Discovery commands (NEW in v4.11.0)
        vscode.commands.registerCommand('bioql.predictADMETox', predictADMETox),
        vscode.commands.registerCommand('bioql.suggestBioisosteres', suggestBioisosteres),
        vscode.commands.registerCommand('bioql.runCompletePipeline', runCompletePipeline),
        vscode.commands.registerCommand('bioql.screenOffTargets', screenOffTargets),
        vscode.commands.registerCommand('bioql.searchSimilarCompounds', searchSimilarCompounds),
        vscode.commands.registerCommand('bioql.profileResistance', profileResistance),
        // Bio-HNET commands (NEW in v4.11.0)
        vscode.commands.registerCommand('bioql.designBioHNET', designBioHNET),
        vscode.commands.registerCommand('bioql.optimizeBioHNET', optimizeBioHNET),
        // Multi-Omics commands (NEW in v6.0.0)
        vscode.commands.registerCommand('bioql.analyzeProteinSequence', analyzeProteinSequence),
        vscode.commands.registerCommand('bioql.predictPTM', predictPTM),
        vscode.commands.registerCommand('bioql.predictPPI', predictPPI),
        vscode.commands.registerCommand('bioql.identifyMetabolite', identifyMetabolite),
        vscode.commands.registerCommand('bioql.analyzePathway', analyzePathway),
        vscode.commands.registerCommand('bioql.fluxAnalysis', fluxAnalysis),
        vscode.commands.registerCommand('bioql.integrateOmics', integrateOmics),
        vscode.commands.registerCommand('bioql.buildNetwork', buildNetwork),
        vscode.commands.registerCommand('bioql.callVariants', callVariants),
        vscode.commands.registerCommand('bioql.analyzeMethylation', analyzeMethylation),
        vscode.commands.registerCommand('bioql.analyzeRNASeq', analyzeRNASeq)
    );

    // Inline completion provider
    const provider = vscode.languages.registerInlineCompletionItemProvider(
        { pattern: '**/*.py' },
        {
            async provideInlineCompletionItems(document, position, context, token) {
                const config = vscode.workspace.getConfiguration('bioql');
                const mode = config.get('mode');

                // Get current line text
                const line = document.lineAt(position.line);
                const prefix = line.text.substring(0, position.character);

                // Only trigger on BioQL-related code
                if (!prefix.includes('bioql') && !prefix.includes('quantum')) {
                    return;
                }

                try {
                    const completion = await callBioQLAssistant(prefix, mode);

                    if (completion) {
                        return [{
                            insertText: completion,
                            range: new vscode.Range(position, position)
                        }];
                    }
                } catch (error) {
                    console.error('BioQL completion error:', error);
                }
            }
        }
    );

    context.subscriptions.push(provider);

    // Register chat participant if API available (VS Code 1.90+)
    if (vscode.chat && vscode.chat.createChatParticipant) {
        try {
            const chatParticipant = vscode.chat.createChatParticipant('bioql.assistant', async (request, context, stream, token) => {
                return handleChatRequest(request, context, stream, token);
            });

            // Don't set icon for now (avoid file loading issues)
            // chatParticipant.iconPath = vscode.Uri.file(__dirname + '/icon.png');

            context.subscriptions.push(chatParticipant);

            outputChannel.appendLine('✅ BioQL Chat enabled! Use @bioql in chat');
            outputChannel.appendLine('✅ Chat participant registered: bioql.assistant');
        } catch (error) {
            outputChannel.appendLine(`❌ Failed to register chat participant: ${error.message}`);
            console.error('Chat registration error:', error);
        }
    } else {
        outputChannel.appendLine('⚠️  Chat API not available (requires VS Code 1.90+)');
    }

    outputChannel.appendLine('✅ BioQL Assistant ready!');
    outputChannel.appendLine('Commands:');
    outputChannel.appendLine('  - Cmd/Ctrl+Shift+G: Generate Code');
    outputChannel.appendLine('  - Cmd/Ctrl+Shift+F: Fix Code');
    outputChannel.appendLine('  - @bioql in Chat: Interactive assistance');
}

/**
 * Generate code from natural language
 */
async function generateCode() {
    const prompt = await vscode.window.showInputBox({
        prompt: 'Describe what you want to do in BioQL',
        placeHolder: 'e.g., Create a Bell state and measure it'
    });

    if (!prompt) return;

    const editor = vscode.window.activeTextEditor;
    if (!editor) return;

    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Generating BioQL code...',
        cancellable: false
    }, async (progress) => {
        try {
            const config = vscode.workspace.getConfiguration('bioql');
            const mode = config.get('mode');

            const code = await callBioQLAssistant(prompt, mode);

            if (code) {
                // Insert generated code at cursor
                editor.edit(editBuilder => {
                    editBuilder.insert(editor.selection.active, '\n' + code + '\n');
                });

                vscode.window.showInformationMessage('✅ Code generated successfully!');
            }
        } catch (error) {
            vscode.window.showErrorMessage(`Error: ${error.message}`);
        }
    });
}

/**
 * Fix current code
 */
async function fixCode() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;

    const selection = editor.selection;
    const code = editor.document.getText(selection);

    if (!code) {
        vscode.window.showWarningMessage('Please select code to fix');
        return;
    }

    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Fixing BioQL code...',
        cancellable: false
    }, async (progress) => {
        try {
            const config = vscode.workspace.getConfiguration('bioql');
            const mode = config.get('mode');

            const prompt = `Fix this BioQL code:\n\n${code}`;
            const fixed = await callBioQLAssistant(prompt, mode);

            if (fixed) {
                editor.edit(editBuilder => {
                    editBuilder.replace(selection, fixed);
                });

                vscode.window.showInformationMessage('✅ Code fixed!');
            }
        } catch (error) {
            vscode.window.showErrorMessage(`Error: ${error.message}`);
        }
    });
}

/**
 * Explain current code
 */
async function explainCode() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;

    const selection = editor.selection;
    const code = editor.document.getText(selection);

    if (!code) {
        vscode.window.showWarningMessage('Please select code to explain');
        return;
    }

    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Analyzing BioQL code...',
        cancellable: false
    }, async (progress) => {
        try {
            const config = vscode.workspace.getConfiguration('bioql');
            const mode = config.get('mode');

            const prompt = `Explain this BioQL code:\n\n${code}`;
            const explanation = await callBioQLAssistant(prompt, mode);

            if (explanation) {
                // Show in output channel
                outputChannel.clear();
                outputChannel.appendLine('📖 Code Explanation:');
                outputChannel.appendLine('='.repeat(60));
                outputChannel.appendLine(explanation);
                outputChannel.show();
            }
        } catch (error) {
            vscode.window.showErrorMessage(`Error: ${error.message}`);
        }
    });
}

/**
 * Optimize quantum circuit
 */
async function optimizeCircuit() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;

    const selection = editor.selection;
    const code = editor.document.getText(selection);

    if (!code) {
        vscode.window.showWarningMessage('Please select code to optimize');
        return;
    }

    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Optimizing quantum circuit...',
        cancellable: false
    }, async (progress) => {
        try {
            const config = vscode.workspace.getConfiguration('bioql');
            const mode = config.get('mode');

            const prompt = `Optimize this BioQL quantum circuit:\n\n${code}`;
            const optimized = await callBioQLAssistant(prompt, mode);

            if (optimized) {
                editor.edit(editBuilder => {
                    editBuilder.replace(selection, optimized);
                });

                vscode.window.showInformationMessage('✅ Circuit optimized!');
            }
        } catch (error) {
            vscode.window.showErrorMessage(`Error: ${error.message}`);
        }
    });
}

/**
 * Insert code at cursor (from chat)
 */
async function insertCode(code, ...args) {
    // Handle different call signatures
    const actualCode = typeof code === 'string' ? code : (args[0] || '');

    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor to insert code');
        return;
    }

    await editor.edit(editBuilder => {
        editBuilder.insert(editor.selection.active, '\n' + actualCode + '\n');
    });

    vscode.window.showInformationMessage('✅ Code inserted!');
}

/**
 * Apply fixes from autonomous agent
 */
async function applyFixes(fixedCode, filePath, ...args) {
    // Handle different call signatures
    const actualCode = typeof fixedCode === 'string' ? fixedCode : (args[0] || '');
    const actualPath = typeof filePath === 'string' ? filePath : (args[1] || '');

    // Find the document
    let editor = vscode.window.activeTextEditor;

    // If specified path doesn't match current editor, try to open it
    if (actualPath && editor && editor.document.fileName !== actualPath) {
        const doc = await vscode.workspace.openTextDocument(actualPath);
        editor = await vscode.window.showTextDocument(doc);
    }

    if (!editor) {
        vscode.window.showWarningMessage('No active editor to apply fixes');
        return;
    }

    // Confirm before applying
    const confirm = await vscode.window.showWarningMessage(
        'Apply autonomous agent fixes to this file?',
        { modal: true },
        'Apply', 'Cancel'
    );

    if (confirm !== 'Apply') {
        return;
    }

    // Replace entire document
    await editor.edit(editBuilder => {
        const fullRange = new vscode.Range(
            editor.document.positionAt(0),
            editor.document.positionAt(editor.document.getText().length)
        );
        editBuilder.replace(fullRange, actualCode);
    });

    // Save
    await editor.document.save();

    vscode.window.showInformationMessage('✅ Fixes applied! File saved.');
    outputChannel.appendLine('\n✅ Autonomous agent fixes applied to: ' + editor.document.fileName);
}

/**
 * Handle chat requests (@bioql) - Enhanced with agent capabilities
 */
async function handleChatRequest(request, context, stream, token) {
    const config = vscode.workspace.getConfiguration('bioql');
    const mode = config.get('mode');

    try {
        const prompt = request.prompt;

        // Check for autonomous actions first (fix and apply, improve, refactor)
        const autonomousAction = detectAutonomousAction(prompt);

        if (autonomousAction) {
            // Use autonomous agent
            stream.progress(`🤖 Autonomous agent ${autonomousAction}ing...`);

            const autoResult = await executeAutonomousAgent(prompt, autonomousAction, mode, stream);

            // Show changes
            if (autoResult.changesCount > 0) {
                stream.markdown(`\n### 🔧 ${autonomousAction.toUpperCase()} Complete\n\n`);
                stream.markdown(`**Changes:** ${autoResult.changesCount} lines modified\n\n`);

                if (autoResult.issues) {
                    stream.markdown(`**Issues Found:**\n\`\`\`\n${autoResult.issues.substring(0, 300)}\n\`\`\`\n\n`);
                }

                // Show diff
                if (autoResult.diff) {
                    stream.markdown(`**Diff:**\n\`\`\`diff\n${autoResult.diff.substring(0, 500)}\n\`\`\`\n\n`);
                }

                // Show fixed code
                if (autoResult.fixedCode) {
                    stream.markdown(`**Fixed Code:**\n\`\`\`python\n${autoResult.fixedCode.substring(0, 1000)}\n\`\`\`\n\n`);
                }

                // Button to apply changes
                stream.button({
                    command: 'bioql.applyFixes',
                    title: '✅ Apply Changes',
                    arguments: [autoResult.fixedCode, autoResult.filePath]
                });
            } else {
                stream.markdown('\n✅ No changes needed. Code looks good!\n');
            }

            return { metadata: { command: 'bioql.autonomous' } };
        }

        // Otherwise use regular agent
        stream.progress('🤖 BioQL Agent analyzing...');
        const agentResult = await executeWithAgent(prompt, mode, stream, context);

        // CHECK IF AGENT NEEDS PARAMETERS - Show questions prominently!
        if (agentResult.action === 'needs_parameters') {
            stream.markdown('\n## 🤔 I need more information\n\n');

            // Show the questions
            if (agentResult.message) {
                stream.markdown(agentResult.message + '\n\n');
            }

            // Show what we already know
            if (agentResult.conversation_state && Object.keys(agentResult.conversation_state).length > 0) {
                stream.markdown('**What I already know:**\n');
                const state = agentResult.conversation_state;
                if (state.task_type) stream.markdown(`- Task: ${state.task_type}\n`);
                if (state.qubits) stream.markdown(`- Qubits: ${state.qubits}\n`);
                if (state.backend) stream.markdown(`- Backend: ${state.backend}\n`);
                if (state.shots) stream.markdown(`- Shots: ${state.shots}\n`);
                stream.markdown('\n');
            }

            // Show what's still missing
            if (agentResult.missing_parameters && agentResult.missing_parameters.length > 0) {
                stream.markdown('**Still need:**\n');
                agentResult.missing_parameters.forEach(param => {
                    // Handle special optional parameter
                    if (param === 'ligand_or_receptor') {
                        stream.markdown(`- Ligand, receptor, or both (optional - provide at least one)\n`);
                    } else {
                        stream.markdown(`- ${param}\n`);
                    }
                });
                stream.markdown('\n');
            }

            stream.markdown('---\n\n');
            stream.markdown('💬 **Just respond naturally with the missing information!**\n\n');
            stream.markdown('Examples:\n');
            stream.markdown('- For ligand/receptor: *"aspirin to COX-2"* or *"semaglutide to GLP1R"*\n');
            stream.markdown('- For backend: *"Use AWS Braket simulator with 1000 shots"*\n\n');

            return { metadata: { command: 'bioql.needs_parameters' } };
        }

        // Show agent actions if any tools were used
        if (agentResult.actions && agentResult.actions.length > 0) {
            const action = agentResult.actions[0];

            // Only show "Actions Taken" if it's actually a tool execution
            if (action.tool && action.tool !== 'generate_code' && action.tool !== 'answer' && action.tool !== 'needs_parameters') {
                stream.markdown('\n### Action\n\n');
                const status = action.success ? '✅' : '❌';
                stream.markdown(`${status} **${action.tool}**\n\n`);

                if (action.result && action.result.length > 0) {
                    // Truncate very long results
                    const result = action.result.length > 500
                        ? action.result.substring(0, 500) + '...'
                        : action.result;
                    stream.markdown(`\`\`\`\n${result}\n\`\`\`\n\n`);
                }
                if (action.error) {
                    stream.markdown(`Error: ${action.error}\n\n`);
                }
            }
        }

        // Show code if generated
        if (agentResult.code) {
            stream.markdown('### ✅ Generated Code\n\n```python\n' + agentResult.code + '\n```\n\n');

            // Offer to insert code
            stream.button({
                command: 'bioql.insertCode',
                title: '📋 Insert Code',
                arguments: [agentResult.code]
            });
        }

        // Show response/reasoning
        if (agentResult.response && !agentResult.code) {
            stream.markdown(agentResult.response);
        }

        return { metadata: { command: 'bioql.agent' } };

    } catch (error) {
        stream.markdown(`❌ Error: ${error.message}`);
        return { metadata: { command: '' } };
    }
}

/**
 * Detect if request needs agent tool execution
 */
function detectToolRequirement(prompt) {
    const toolKeywords = [
        'read file', 'write file', 'edit file', 'create file',
        'run', 'execute', 'test',
        'search', 'find in', 'grep',
        'list files', 'show files',
        'fix code in', 'update file'
    ];

    const lowerPrompt = prompt.toLowerCase();
    return toolKeywords.some(keyword => lowerPrompt.includes(keyword));
}

/**
 * Detect if request needs autonomous agent (fix, improve, refactor)
 */
function detectAutonomousAction(prompt) {
    const lowerPrompt = prompt.toLowerCase();

    // Autonomous actions that modify code
    if (lowerPrompt.includes('fix') && (lowerPrompt.includes('apply') || lowerPrompt.includes('automatically'))) {
        return 'fix_and_apply';
    }
    if (lowerPrompt.includes('improve') && lowerPrompt.includes('code')) {
        return 'improve';
    }
    if (lowerPrompt.includes('refactor')) {
        return 'refactor';
    }

    return null;
}

/**
 * Execute autonomous agent action (fix, improve, refactor)
 */
async function executeAutonomousAgent(prompt, action, mode, stream) {
    const config = vscode.workspace.getConfiguration('bioql');
    const apiKey = config.get('apiKey');

    if (!apiKey) {
        throw new Error('API key required for autonomous agent');
    }

    // Get current file
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        throw new Error('No file open. Please open a file to fix/improve/refactor');
    }

    const fileContent = editor.document.getText();
    const filePath = editor.document.fileName;

    outputChannel.appendLine('\n🤖 Calling Autonomous Agent...');
    outputChannel.appendLine(`   Action: ${action}`);
    outputChannel.appendLine(`   File: ${filePath}`);

    stream.progress(`Autonomous agent ${action}ing code...`);

    try {
        const autonomousUrl = 'https://spectrix--bioql-agent-autonomous-agent-act.modal.run';

        const response = await axios.post(autonomousUrl, {
            api_key: apiKey,
            action: action,
            file_content: fileContent,
            file_path: filePath,
            instruction: prompt
        }, { timeout: 180000 });  // 3 minute timeout for autonomous actions

        const result = response.data;

        if (result.error) {
            throw new Error(result.error);
        }

        // Log cost
        if (result.cost && outputChannel) {
            outputChannel.appendLine('\n💰 Autonomous Agent Cost:');
            // Handle both object format (result.cost.user_cost_usd) and number format (result.cost)
            const cost = typeof result.cost === 'object' ? result.cost.user_cost_usd : result.cost;
            outputChannel.appendLine(`   User Cost: $${cost.toFixed(6)}`);
            if (result.timing) {
                outputChannel.appendLine(`   Time: ${result.timing.total_seconds}s`);
            }
            outputChannel.appendLine(`   Changes: ${result.changes_count || 0} lines`);
        }

        return {
            success: result.success,
            action: action,
            fixedCode: result.fixed_code || result.improved_code || result.refactored_code,
            originalCode: result.original_code,
            diff: result.diff,
            changesCount: result.changes_count || 0,
            issues: result.issues_found,
            filePath: filePath
        };

    } catch (error) {
        if (error.response) {
            outputChannel.appendLine(`\n❌ Autonomous Agent Error: ${JSON.stringify(error.response.data)}`);
            throw new Error(error.response.data.error || 'Autonomous agent failed');
        } else if (error.request) {
            outputChannel.appendLine(`\n❌ Network Error: No response from autonomous agent`);
            throw new Error('Network error: Could not reach autonomous agent');
        } else {
            throw error;
        }
    }
}

/**
 * Execute request with agent tools (calls Modal agent endpoint)
 */
async function executeWithAgent(prompt, mode, stream, chatContext) {
    const config = vscode.workspace.getConfiguration('bioql');
    const apiKey = config.get('apiKey');

    if (!apiKey) {
        throw new Error('API key required for agent mode');
    }

    // Get workspace context
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd();
    const editor = vscode.window.activeTextEditor;
    const currentFile = editor?.document.fileName;
    const selectedText = editor ? editor.document.getText(editor.selection) : '';

    // Get full file content if reviewing/fixing code
    let currentFileContent = '';
    let fileToReview = currentFile;

    // Check if user specified a file path in the prompt
    const filePathMatch = prompt.match(/([\/~][\w\/\-_.]+\.py)/);

    if (prompt.toLowerCase().includes('review') ||
        prompt.toLowerCase().includes('fix') ||
        prompt.toLowerCase().includes('analyze')) {

        if (filePathMatch) {
            // User specified a file path - try to read it
            const fs = require('fs');
            const specifiedPath = filePathMatch[1];

            try {
                currentFileContent = fs.readFileSync(specifiedPath, 'utf-8');
                fileToReview = specifiedPath;
                outputChannel.appendLine(`📄 Reading file from path: ${specifiedPath}`);
            } catch (error) {
                outputChannel.appendLine(`⚠️  Could not read ${specifiedPath}: ${error.message}`);
                outputChannel.appendLine(`   Falling back to current editor...`);

                // Fallback to current editor
                if (editor) {
                    currentFileContent = editor.document.getText();
                    fileToReview = currentFile;
                }
            }
        } else if (editor) {
            // Use current editor
            currentFileContent = editor.document.getText();
            fileToReview = currentFile;
        }
    }

    // Build workspace context for agent
    const workspaceContext = {
        workspace: workspaceFolder,
        current_file: fileToReview,  // Use detected file path
        selected_text: selectedText,
        file_content: currentFileContent  // Send full file content
    };

    try {
        // Call Modal billing agent endpoint (connected to ngrok billing server)
        const agentUrl = 'https://spectrix--bioql-agent-create-fastapi-app.modal.run';

        outputChannel.appendLine('\n🤖 Calling BioQL Agent...');
        outputChannel.appendLine(`   Endpoint: ${agentUrl}`);
        outputChannel.appendLine(`   Request: ${prompt}`);
        outputChannel.appendLine(`   API Key: ${apiKey ? apiKey.substring(0, 15) + '...' : 'NOT SET'}`);

        // Include conversation_state if available (from previous interaction)
        // Get conversation state from global storage using chat session ID
        const sessionId = chatContext?.session?.id || 'default';
        const conversationState = conversationStates.get(sessionId) || {};

        const response = await axios.post(agentUrl, {
            api_key: apiKey,
            request: prompt,
            conversation_state: conversationState  // Pass conversation state to maintain context
        }, { timeout: 120000 });

        const result = response.data;

        outputChannel.appendLine(`\n✅ Agent Response Received`);
        outputChannel.appendLine(`   Success: ${result.success}`);
        outputChannel.appendLine(`   Action: ${result.action || 'N/A'}`);

        if (result.error) {
            throw new Error(result.error);
        }

        // Log cost
        if (result.cost && outputChannel) {
            outputChannel.appendLine('\n💰 Agent Cost:');
            // Handle both object format (result.cost.user_cost_usd) and number format (result.cost)
            const cost = typeof result.cost === 'object' ? result.cost.user_cost_usd : result.cost;
            outputChannel.appendLine(`   User Cost: $${cost.toFixed(6)}`);
            if (result.timing) {
                outputChannel.appendLine(`   Time: ${result.timing.total_seconds}s`);
            }
            outputChannel.appendLine(`   Action: ${result.action}`);
            if (result.user && result.user.balance !== undefined) {
                outputChannel.appendLine(`   Balance: $${result.user.balance.toFixed(6)}`);
            }
        }

        // Convert single action to array format for compatibility
        const actions = [{
            tool: result.action,
            success: result.success,
            result: result.result || result.code || result.response,
            error: result.error
        }];

        // Update conversation state in global storage if returned
        if (result.conversation_state) {
            conversationStates.set(sessionId, result.conversation_state);
        }

        return {
            actions: actions,
            response: result.reasoning || result.code || result.response || result.message || 'Agent completed',
            success: result.success,
            code: result.code,
            action: result.action,  // Include action type
            message: result.message,  // Include message (for needs_parameters)
            conversation_state: result.conversation_state,  // Include conversation state
            missing_parameters: result.missing_parameters  // Include missing parameters
        };

    } catch (error) {
        if (error.response) {
            outputChannel.appendLine(`\n❌ Agent Error: ${JSON.stringify(error.response.data)}`);
            throw new Error(error.response.data.error || 'Agent request failed');
        } else if (error.request) {
            outputChannel.appendLine(`\n❌ Network Error: No response from agent`);
            throw new Error('Network error: Could not reach agent server');
        } else {
            throw error;
        }
    }
}

/**
 * Run on quantum computer
 */
async function runOnQuantumComputer() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;

    const code = editor.document.getText();

    // Save file first
    await editor.document.save();

    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Running on quantum computer...',
        cancellable: false
    }, async (progress) => {
        try {
            const config = vscode.workspace.getConfiguration('bioql');
            const apiKey = config.get('apiKey');
            const backend = config.get('defaultBackend');

            if (!apiKey) {
                vscode.window.showWarningMessage('Please set your BioQL API key in settings');
                return;
            }

            // Execute the Python file
            const pythonPath = vscode.workspace.getConfiguration('python').get('pythonPath') || 'python3';

            const result = await executePython(pythonPath, editor.document.fileName);

            outputChannel.clear();
            outputChannel.appendLine('⚛️  Quantum Execution Results:');
            outputChannel.appendLine('='.repeat(60));
            outputChannel.appendLine(result);
            outputChannel.show();

            vscode.window.showInformationMessage('✅ Quantum execution complete!');

        } catch (error) {
            vscode.window.showErrorMessage(`Error: ${error.message}`);
        }
    });
}

/**
 * Call BioQL Assistant - Full response with reasoning
 */
async function callBioQLAssistantFull(prompt, mode) {
    const config = vscode.workspace.getConfiguration('bioql');

    if (mode === 'modal') {
        // Call Modal API with authentication
        const modalUrl = config.get('modalUrl');
        const apiKey = config.get('apiKey');

        if (!modalUrl) {
            throw new Error('Modal URL not configured. Set bioql.modalUrl in settings.');
        }

        if (!apiKey) {
            throw new Error('API key required. Set bioql.apiKey in settings to use Modal inference.');
        }

        outputChannel.appendLine(`\n🔄 Calling BioQL inference API...`);
        outputChannel.appendLine(`   Endpoint: ${modalUrl}`);

        try {
            const response = await axios.post(modalUrl, {
                api_key: apiKey,
                prompt: prompt,
                max_length: 300,
                temperature: 0.7,
                include_reasoning: true  // Request reasoning
            }, {
                timeout: 120000  // 2 minute timeout
            });

            const result = response.data;

            // Check for errors
            if (result.error) {
                throw new Error(result.error);
            }

            // Log cost information
            if (result.cost && outputChannel) {
                outputChannel.appendLine('\n💰 Cost Information:');
                outputChannel.appendLine(`   Model: ${result.model || 'unknown'}`);
                // Handle both object format (result.cost.user_cost_usd) and number format (result.cost)
                const cost = typeof result.cost === 'object' ? result.cost.user_cost_usd : result.cost;
                outputChannel.appendLine(`   User Cost: $${cost.toFixed(6)}`);
                if (result.timing) {
                    outputChannel.appendLine(`   Generation Time: ${result.timing.generation_seconds}s`);
                }
                if (result.cost && typeof result.cost === 'object' && result.cost.profit_margin_percent !== undefined) {
                    outputChannel.appendLine(`   Profit Margin: ${result.cost.profit_margin_percent}%`);
                }
                if (result.user && result.user.balance !== undefined) {
                    outputChannel.appendLine(`   Balance: $${result.user.balance.toFixed(6)}`);
                }
            }

            return {
                code: result.code || '',
                reasoning: result.reasoning || ''
            };

        } catch (error) {
            if (error.response) {
                // Server responded with error
                outputChannel.appendLine(`\n❌ API Error: ${JSON.stringify(error.response.data)}`);
                throw new Error(error.response.data.error || 'API request failed');
            } else if (error.request) {
                // Request made but no response
                outputChannel.appendLine(`\n❌ Network Error: No response from server`);
                throw new Error('Network error: Could not reach inference server');
            } else {
                // Other error
                throw error;
            }
        }

    } else {
        // Call Python assistant script
        const pythonPath = await findPythonWithBioQL();

        const code = await executePython(pythonPath, '-c', `
from bioql.llm.vscode_assistant import quick_complete
code = quick_complete("${prompt.replace(/"/g, '\\"')}", mode="${mode}")
print(code)
        `);

        return {
            code: code.trim(),
            reasoning: ''
        };
    }
}

/**
 * Call BioQL Assistant (Python backend) - Returns code only
 */
async function callBioQLAssistant(prompt, mode) {
    const result = await callBioQLAssistantFull(prompt, mode);
    return result.code;
}

/**
 * Find Python executable with BioQL installed
 */
async function findPythonWithBioQL() {
    // Try multiple Python executables
    const candidates = [
        vscode.workspace.getConfiguration('python').get('defaultInterpreterPath'),
        vscode.workspace.getConfiguration('python').get('pythonPath'),
        'python3',
        '/opt/homebrew/bin/python3',
        '/usr/local/bin/python3',
        '/usr/bin/python3'
    ].filter(Boolean);

    for (const pythonPath of candidates) {
        try {
            const result = await executePython(pythonPath, '-c', 'import bioql; print("OK")');
            if (result.trim() === 'OK') {
                outputChannel.appendLine(`✅ Found Python with BioQL: ${pythonPath}`);
                return pythonPath;
            }
        } catch (e) {
            // Try next candidate
        }
    }

    outputChannel.appendLine('⚠️  No Python with BioQL found, using python3');
    return 'python3';
}

/**
 * Execute Python script
 */
function executePython(pythonPath, ...args) {
    return new Promise((resolve, reject) => {
        // Debug logging
        if (outputChannel) {
            outputChannel.appendLine(`Executing: ${pythonPath} ${args.join(' ')}`);
        }
        const python = spawn(pythonPath, args);

        let stdout = '';
        let stderr = '';

        python.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        python.stderr.on('data', (data) => {
            stderr += data.toString();
        });

        python.on('close', (code) => {
            if (code !== 0) {
                reject(new Error(stderr || 'Python execution failed'));
            } else {
                resolve(stdout);
            }
        });
    });
}

// ==============================================================================
// CRISPR-QAI COMMANDS (NEW in v4.4.0)
// ==============================================================================

/**
 * Design CRISPR Guide - Generate code for quantum-enhanced guide design
 */
async function designCRISPRGuide() {
    const guideSeq = await vscode.window.showInputBox({
        prompt: 'Enter guide RNA sequence (e.g., ATCGAAGTCGCTAGCTA)',
        placeHolder: 'ATCGAAGTCGCTAGCTA',
        validateInput: (text) => {
            if (!/^[ATCG]+$/.test(text)) {
                return 'Guide sequence must contain only A, T, C, G';
            }
            if (text.length < 15 || text.length > 25) {
                return 'Guide sequence should be 15-25 nucleotides';
            }
            return null;
        }
    });

    if (!guideSeq) return;

    // Select quantum backend
    const backend = await vscode.window.showQuickPick([
        { label: '🖥️  Local Simulator', value: 'simulator', description: 'Free - Fast - Only BioQL API key needed' },
        { label: '⚛️  IBM Qiskit', value: 'qiskit', description: 'Real IBM quantum hardware (BioQL handles credentials)' },
        { label: '☁️  AWS Braket', value: 'braket', description: 'AWS quantum hardware (BioQL handles credentials)' }
    ], {
        placeHolder: 'Select quantum backend (BioQL API key only!)',
        title: 'Quantum Backend - BioQL handles all credentials'
    });

    if (!backend) return;

    let request = `score crispr guide ${guideSeq} with 1000 shots`;

    // Add backend-specific parameters
    if (backend.value === 'qiskit') {
        const device = await vscode.window.showQuickPick([
            { label: 'aer_simulator', description: 'Local Qiskit simulator' },
            { label: 'ibm_torino', description: 'IBM Torino 133-qubit (real hardware)' },
            { label: 'ibm_kyoto', description: 'IBM Kyoto 127-qubit' },
            { label: 'ibm_osaka', description: 'IBM Osaka 127-qubit' }
        ], { placeHolder: 'Select IBM Qiskit device' });

        if (!device) return;
        request = `score crispr guide ${guideSeq} with ibm qiskit ${device.label} 1000 shots`;

    } else if (backend.value === 'braket') {
        const device = await vscode.window.showQuickPick([
            { label: 'SV1', description: 'AWS State Vector Simulator' },
            { label: 'DM1', description: 'AWS Density Matrix Simulator' },
            { label: 'Aspen-M-3', description: 'Rigetti Aspen-M-3 (real hardware)' },
            { label: 'Harmony', description: 'IonQ Harmony (real hardware)' }
        ], { placeHolder: 'Select AWS Braket device' });

        if (!device) return;
        request = `score crispr guide ${guideSeq} with aws braket ${device.label} 1000 shots`;
    }

    await processRequest(request, 'CRISPR Guide Design');
}

/**
 * Rank CRISPR Guides - Generate code for ranking multiple guides
 */
async function rankCRISPRGuides() {
    const input = await vscode.window.showQuickPick(
        ['Enter guides manually', 'Load from file'],
        { placeHolder: 'How do you want to provide guide sequences?' }
    );

    if (!input) return;

    let baseRequest;
    if (input === 'Enter guides manually') {
        const guides = await vscode.window.showInputBox({
            prompt: 'Enter guide sequences (comma-separated)',
            placeHolder: 'ATCGAAGTCGCTAGCTA, GCTAGCTACGATCCGA, TTAACCGGTTAACCGG'
        });

        if (!guides) return;
        baseRequest = `rank crispr guides: ${guides}`;
    } else {
        const file = await vscode.window.showInputBox({
            prompt: 'Enter file path (CSV or FASTA)',
            placeHolder: 'guides.csv'
        });

        if (!file) return;
        baseRequest = `rank crispr guides from file ${file}`;
    }

    // Select quantum backend
    const backend = await vscode.window.showQuickPick([
        { label: '🖥️  Local Simulator', value: 'simulator', description: 'Free - Fast - Only BioQL API key needed' },
        { label: '⚛️  IBM Qiskit', value: 'qiskit', description: 'Real IBM quantum hardware (BioQL handles credentials)' },
        { label: '☁️  AWS Braket', value: 'braket', description: 'AWS quantum hardware (BioQL handles credentials)' }
    ], {
        placeHolder: 'Select quantum backend (BioQL API key only!)',
        title: 'Quantum Backend - BioQL handles all credentials'
    });

    if (!backend) return;

    let request = baseRequest;

    // Add backend-specific parameters
    if (backend.value === 'qiskit') {
        const device = await vscode.window.showQuickPick([
            { label: 'aer_simulator', description: 'Local Qiskit simulator' },
            { label: 'ibm_torino', description: 'IBM Torino 133-qubit' },
            { label: 'ibm_kyoto', description: 'IBM Kyoto 127-qubit' }
        ], { placeHolder: 'Select IBM Qiskit device' });

        if (!device) return;
        request += ` using ibm ${device.label}`;

    } else if (backend.value === 'braket') {
        const device = await vscode.window.showQuickPick([
            { label: 'SV1', description: 'AWS State Vector Simulator' },
            { label: 'DM1', description: 'AWS Density Matrix Simulator' }
        ], { placeHolder: 'Select AWS Braket device' });

        if (!device) return;
        request += ` using aws ${device.label}`;
    }

    await processRequest(request, 'CRISPR Guide Ranking');
}

/**
 * Analyze CRISPR Off-Targets - Generate code for off-target prediction
 */
async function analyzeCRISPROfftargets() {
    const guideSeq = await vscode.window.showInputBox({
        prompt: 'Enter guide RNA sequence to analyze',
        placeHolder: 'ATCGAAGTCGCTAGCTA',
        validateInput: (text) => {
            if (!/^[ATCG]+$/.test(text)) {
                return 'Guide sequence must contain only A, T, C, G';
            }
            return null;
        }
    });

    if (!guideSeq) return;

    const genomeFile = await vscode.window.showInputBox({
        prompt: 'Enter genome regions file (optional - leave empty for heuristic mode)',
        placeHolder: 'genome_regions.fasta'
    });

    const request = genomeFile
        ? `analyze off-targets for crispr guide ${guideSeq} using genome ${genomeFile}`
        : `analyze off-targets for crispr guide ${guideSeq}`;

    await processRequest(request, 'CRISPR Off-Target Analysis');
}

/**
 * Design Clinical CRISPR Therapy - NEW in v4.6.0
 * Complete end-to-end therapy design with real gene sequences
 */
async function designCRISPRTherapy() {
    // Step 1: Select target gene (20+ genes with clinical relevance)
    const geneChoice = await vscode.window.showQuickPick([
        { label: 'PCSK9', description: 'Hypercholesterolemia - Liver targeting', value: 'PCSK9' },
        { label: 'APOE', description: 'Alzheimer\'s disease - CNS targeting', value: 'APOE' },
        { label: 'TP53', description: 'Cancer - Tumor suppressor', value: 'TP53' },
        { label: 'BRCA1', description: 'Breast/ovarian cancer', value: 'BRCA1' },
        { label: 'BRCA2', description: 'Breast/ovarian cancer', value: 'BRCA2' },
        { label: 'KRAS', description: 'Pancreatic/lung cancer', value: 'KRAS' },
        { label: 'EGFR', description: 'Lung cancer - receptor tyrosine kinase', value: 'EGFR' },
        { label: 'BRAF', description: 'Melanoma - kinase', value: 'BRAF' },
        { label: 'PIK3CA', description: 'Breast cancer - kinase', value: 'PIK3CA' },
        { label: 'LEP', description: 'Obesity - leptin', value: 'LEP' },
        { label: 'INS', description: 'Diabetes - insulin', value: 'INS' },
        { label: 'APP', description: 'Alzheimer\'s - amyloid precursor', value: 'APP' },
        { label: 'PSEN1', description: 'Early-onset Alzheimer\'s', value: 'PSEN1' },
        { label: 'IL6', description: 'Inflammation - interleukin-6', value: 'IL6' },
        { label: 'TNF', description: 'Inflammation - tumor necrosis factor', value: 'TNF' }
    ], {
        placeHolder: 'Select target gene (real NCBI sequences)',
        title: 'Step 1/5: Target Gene Selection'
    });

    if (!geneChoice) return;

    // Step 2: Enter disease/condition
    const disease = await vscode.window.showInputBox({
        prompt: 'Enter disease or condition to treat',
        placeHolder: 'e.g., hypercholesterolemia, cancer, Alzheimer\'s disease',
        value: geneChoice.description.split(' - ')[0] // Pre-fill with suggested disease
    });

    if (!disease) return;

    // Step 3: Select target tissue
    const tissueChoice = await vscode.window.showQuickPick([
        { label: 'Liver', description: 'AAV8/LNP - metabolic diseases', value: 'Liver' },
        { label: 'CNS', description: 'AAV9/AAVrh10 - crosses BBB', value: 'CNS' },
        { label: 'Retina', description: 'AAV2/AAV5 - subretinal injection', value: 'Retina' },
        { label: 'Muscle', description: 'AAV1/AAV9/LNP - intramuscular', value: 'Muscle' },
        { label: 'Lung', description: 'AAV5/LNP - inhalation', value: 'Lung' }
    ], {
        placeHolder: 'Select target tissue',
        title: 'Step 2/5: Target Tissue'
    });

    if (!tissueChoice) return;

    // Step 4: Select delivery system
    const deliveryChoice = await vscode.window.showQuickPick([
        {
            label: 'AAV Vector',
            description: 'Adeno-Associated Virus - FDA approved (Luxturna, Zolgensma)',
            value: 'AAV'
        },
        {
            label: 'LNP (Lipid Nanoparticle)',
            description: 'mRNA delivery - FDA approved (Patisiran, COVID vaccines)',
            value: 'LNP'
        }
    ], {
        placeHolder: 'Select delivery system',
        title: 'Step 3/5: Delivery System'
    });

    if (!deliveryChoice) return;

    // Step 5: Select quantum backend
    const backendChoice = await vscode.window.showQuickPick([
        {
            label: '🖥️  Local Simulator',
            value: 'simulator',
            description: 'Fast - Free - Only BioQL API key needed'
        },
        {
            label: '⚛️  IBM Torino',
            value: 'ibm_torino',
            description: 'Real 133-qubit IBM quantum hardware'
        },
        {
            label: '☁️  AWS Braket SV1',
            value: 'aws_sv1',
            description: 'AWS State Vector Simulator'
        }
    ], {
        placeHolder: 'Select quantum backend (BioQL handles all credentials)',
        title: 'Step 4/5: Quantum Backend'
    });

    if (!backendChoice) return;

    // Step 6: Confirm and generate
    const confirm = await vscode.window.showQuickPick(['Yes', 'No'], {
        placeHolder: `Generate therapy design for ${geneChoice.value} (${disease}) targeting ${tissueChoice.value} with ${deliveryChoice.value}?`,
        title: 'Step 5/5: Confirm Therapy Design'
    });

    if (confirm !== 'Yes') return;

    // Build request for agent
    let request = `create a CRISPR therapy for ${disease} that targets ${geneChoice.value} gene using ${deliveryChoice.value} delivery to ${tissueChoice.value} tissue`;

    if (backendChoice.value !== 'simulator') {
        request += ` with ${backendChoice.value} quantum backend`;
    }

    // Process request
    await processRequest(request, 'Clinical CRISPR Therapy Design');
}

/**
 * Helper function to process CRISPR requests via agent
 */
async function processRequest(request, title) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('Please open a Python file first');
        return;
    }

    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: title,
        cancellable: false
    }, async (progress) => {
        try {
            const config = vscode.workspace.getConfiguration('bioql');
            const mode = config.get('mode');

            progress.report({ message: 'Calling BioQL Agent...' });
            outputChannel.appendLine(`\n🧬 ${title}`);
            outputChannel.appendLine(`   Request: ${request}`);

            // Call agent via chat interface (reuse existing agent infrastructure)
            const result = await executeWithAgent(request, mode, {
                progress: (msg) => progress.report({ message: msg }),
                markdown: (msg) => outputChannel.appendLine(msg)
            }, {});

            if (result.code) {
                // Insert generated code
                await editor.edit(editBuilder => {
                    editBuilder.insert(editor.selection.active, '\n' + result.code + '\n');
                });

                vscode.window.showInformationMessage(`✅ ${title} complete!`);
                outputChannel.appendLine(`\n✅ Code generated (${result.code.length} characters)`);
                outputChannel.show();
            } else if (result.response) {
                // Show response in output
                outputChannel.appendLine('\n' + result.response);
                outputChannel.show();
                vscode.window.showInformationMessage(`✅ ${title} complete!`);
            } else {
                throw new Error('No code or response generated');
            }

        } catch (error) {
            vscode.window.showErrorMessage(`Error: ${error.message}`);
            outputChannel.appendLine(`\n❌ Error: ${error.message}`);
            outputChannel.show();
        }
    });
}

// ==============================================================================
// BIOQL 5.6.0+ DRUG DISCOVERY COMMANDS (NEW in v4.11.0)
// ==============================================================================

/**
 * Predict ADME/Toxicity - Generate code for ADME/Tox prediction
 */
async function predictADMETox() {
    const molecule = await vscode.window.showInputBox({
        prompt: 'Enter molecule (SMILES or name)',
        placeHolder: 'e.g., aspirin or CC(=O)Oc1ccccc1C(=O)O'
    });

    if (!molecule) return;

    // Select prediction properties
    const properties = await vscode.window.showQuickPick([
        { label: 'All ADME/Tox Properties', value: 'all', picked: true },
        { label: 'Absorption (Caco-2, HIA)', value: 'absorption' },
        { label: 'Distribution (PPB, VDss, BBB)', value: 'distribution' },
        { label: 'Metabolism (CYP inhibition)', value: 'metabolism' },
        { label: 'Excretion (Clearance, Half-life)', value: 'excretion' },
        { label: 'Toxicity (hERG, AMES, LD50)', value: 'toxicity' }
    ], {
        placeHolder: 'Select properties to predict',
        title: 'ADME/Tox Properties'
    });

    if (!properties) return;

    const request = properties.value === 'all'
        ? `predict ADME and toxicity for ${molecule}`
        : `predict ${properties.value} for ${molecule}`;

    await processRequest(request, 'ADME/Toxicity Prediction');
}

/**
 * Suggest Bioisosteric Replacements - Generate code for bioisosteric analysis
 */
async function suggestBioisosteres() {
    const molecule = await vscode.window.showInputBox({
        prompt: 'Enter molecule (SMILES or name)',
        placeHolder: 'e.g., aspirin or CC(=O)Oc1ccccc1C(=O)O'
    });

    if (!molecule) return;

    // Select replacement type
    const replacementType = await vscode.window.showQuickPick([
        { label: 'All Bioisosteric Replacements', value: 'all', description: '12+ replacement types' },
        { label: 'Classical Isosteres', value: 'classical', description: 'Atom/group replacements' },
        { label: 'Non-classical Isosteres', value: 'nonclassical', description: 'Ring/scaffold replacements' },
        { label: 'Scaffold Hopping', value: 'scaffold', description: 'Major structural changes' }
    ], {
        placeHolder: 'Select replacement strategy',
        title: 'Bioisosteric Replacement Type'
    });

    if (!replacementType) return;

    const request = replacementType.value === 'all'
        ? `suggest bioisosteric replacements for ${molecule}`
        : `suggest ${replacementType.value} bioisosteres for ${molecule}`;

    await processRequest(request, 'Bioisosteric Replacement');
}

/**
 * Run Complete Pipeline - Execute full drug discovery pipeline
 */
async function runCompletePipeline() {
    const molecule = await vscode.window.showInputBox({
        prompt: 'Enter starting molecule (SMILES or name)',
        placeHolder: 'e.g., aspirin or CC(=O)Oc1ccccc1C(=O)O'
    });

    if (!molecule) return;

    const target = await vscode.window.showInputBox({
        prompt: 'Enter target protein (optional)',
        placeHolder: 'e.g., COX-2, EGFR, or leave empty'
    });

    // Select pipeline steps
    const steps = await vscode.window.showQuickPick([
        { label: 'Complete 9-Step Pipeline', value: 'complete', description: 'All optimization steps', picked: true },
        { label: 'Custom Pipeline Steps', value: 'custom', description: 'Select specific steps' }
    ], {
        placeHolder: 'Select pipeline configuration',
        title: 'Pipeline Configuration'
    });

    if (!steps) return;

    let request = target
        ? `run complete drug discovery pipeline for ${molecule} targeting ${target}`
        : `run complete drug discovery pipeline for ${molecule}`;

    if (steps.value === 'custom') {
        // Show custom steps selection
        const customSteps = await vscode.window.showInputBox({
            prompt: 'Enter pipeline steps (comma-separated)',
            placeHolder: 'e.g., adme, bioisosteric, similarity, offtarget'
        });

        if (customSteps) {
            request += ` with steps: ${customSteps}`;
        }
    }

    await processRequest(request, 'Complete Drug Discovery Pipeline');
}

/**
 * Screen Off-Targets - Generate code for off-target screening
 */
async function screenOffTargets() {
    const molecule = await vscode.window.showInputBox({
        prompt: 'Enter molecule (SMILES or name)',
        placeHolder: 'e.g., aspirin or CC(=O)Oc1ccccc1C(=O)O'
    });

    if (!molecule) return;

    // Select screening panel
    const panel = await vscode.window.showQuickPick([
        { label: 'Complete Panel (30+ proteins)', value: 'complete', description: 'Full off-target screening' },
        { label: 'hERG + CYP Panel', value: 'safety', description: 'Safety-critical targets' },
        { label: 'Kinase Panel', value: 'kinase', description: 'Kinase selectivity' },
        { label: 'GPCR Panel', value: 'gpcr', description: 'GPCR selectivity' },
        { label: 'Custom Targets', value: 'custom', description: 'Specify targets' }
    ], {
        placeHolder: 'Select screening panel',
        title: 'Off-Target Screening Panel'
    });

    if (!panel) return;

    let request;
    if (panel.value === 'custom') {
        const targets = await vscode.window.showInputBox({
            prompt: 'Enter target proteins (comma-separated)',
            placeHolder: 'e.g., hERG, CYP3A4, EGFR'
        });

        if (!targets) return;
        request = `screen ${molecule} against off-targets: ${targets}`;
    } else {
        request = `screen ${molecule} for off-targets using ${panel.label}`;
    }

    await processRequest(request, 'Off-Target Screening');
}

/**
 * Search Similar Compounds - Generate code for similarity search
 */
async function searchSimilarCompounds() {
    const molecule = await vscode.window.showInputBox({
        prompt: 'Enter molecule (SMILES or name)',
        placeHolder: 'e.g., aspirin or CC(=O)Oc1ccccc1C(=O)O'
    });

    if (!molecule) return;

    // Select database
    const database = await vscode.window.showQuickPick([
        { label: 'ChEMBL', value: 'chembl', description: 'Bioactive molecules (2M+ compounds)' },
        { label: 'PubChem', value: 'pubchem', description: 'Chemical structures (110M+ compounds)' },
        { label: 'Both ChEMBL + PubChem', value: 'both', description: 'Combined search' }
    ], {
        placeHolder: 'Select compound database',
        title: 'Similarity Search Database'
    });

    if (!database) return;

    // Similarity threshold
    const threshold = await vscode.window.showInputBox({
        prompt: 'Enter similarity threshold (0.0-1.0)',
        placeHolder: '0.8',
        value: '0.8',
        validateInput: (text) => {
            const val = parseFloat(text);
            if (isNaN(val) || val < 0 || val > 1) {
                return 'Threshold must be between 0.0 and 1.0';
            }
            return null;
        }
    });

    if (!threshold) return;

    const request = `search for compounds similar to ${molecule} in ${database.label} with threshold ${threshold}`;

    await processRequest(request, 'Similarity Search');
}

/**
 * Profile Resistance - Generate code for resistance profiling
 */
async function profileResistance() {
    const molecule = await vscode.window.showInputBox({
        prompt: 'Enter molecule (SMILES or name)',
        placeHolder: 'e.g., imatinib or CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5'
    });

    if (!molecule) return;

    const target = await vscode.window.showInputBox({
        prompt: 'Enter target protein',
        placeHolder: 'e.g., BCR-ABL, EGFR, HIV-1 protease'
    });

    if (!target) return;

    // Select resistance type
    const resistanceType = await vscode.window.showQuickPick([
        { label: 'Known Mutations', value: 'known', description: 'Clinically observed resistance mutations' },
        { label: 'Predicted Mutations', value: 'predicted', description: 'ML-predicted resistance hotspots' },
        { label: 'Complete Profile', value: 'complete', description: 'Known + Predicted mutations', picked: true }
    ], {
        placeHolder: 'Select resistance profiling type',
        title: 'Resistance Profiling'
    });

    if (!resistanceType) return;

    const request = `profile resistance for ${molecule} against ${target} using ${resistanceType.label}`;

    await processRequest(request, 'Resistance Profiling');
}

// ==============================================================================
// BIO-HNET COMMANDS (NEW in v4.11.0)
// ==============================================================================

/**
 * Design Bio-HNET - Generate code for Bio-HNET design
 */
async function designBioHNET() {
    const task = await vscode.window.showQuickPick([
        { label: 'Molecular Docking', value: 'docking', description: 'Ligand-receptor docking with Bio-HNET' },
        { label: 'Property Prediction', value: 'property', description: 'ADME/Tox with Bio-HNET' },
        { label: 'Drug Discovery Pipeline', value: 'pipeline', description: 'Full pipeline with Bio-HNET' }
    ], {
        placeHolder: 'Select Bio-HNET task',
        title: 'Bio-HNET Design'
    });

    if (!task) return;

    let request;
    if (task.value === 'docking') {
        const ligand = await vscode.window.showInputBox({
            prompt: 'Enter ligand (SMILES or name)',
            placeHolder: 'e.g., aspirin'
        });

        if (!ligand) return;

        const receptor = await vscode.window.showInputBox({
            prompt: 'Enter receptor protein',
            placeHolder: 'e.g., COX-2'
        });

        if (!receptor) return;

        request = `design bio-hnet for docking ${ligand} to ${receptor}`;
    } else if (task.value === 'property') {
        const molecule = await vscode.window.showInputBox({
            prompt: 'Enter molecule (SMILES or name)',
            placeHolder: 'e.g., aspirin'
        });

        if (!molecule) return;

        request = `design bio-hnet for property prediction of ${molecule}`;
    } else {
        const molecule = await vscode.window.showInputBox({
            prompt: 'Enter starting molecule',
            placeHolder: 'e.g., aspirin'
        });

        if (!molecule) return;

        request = `design bio-hnet pipeline for ${molecule}`;
    }

    await processRequest(request, 'Bio-HNET Design');
}

/**
 * Optimize Bio-HNET - Generate code for Bio-HNET optimization
 */
async function optimizeBioHNET() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('Please open a file with Bio-HNET code first');
        return;
    }

    const selection = editor.selection;
    const code = editor.document.getText(selection);

    if (!code || !code.includes('bio_hnet')) {
        vscode.window.showWarningMessage('Please select Bio-HNET code to optimize');
        return;
    }

    // Select optimization target
    const target = await vscode.window.showQuickPick([
        { label: 'Accuracy', value: 'accuracy', description: 'Maximize prediction accuracy' },
        { label: 'Speed', value: 'speed', description: 'Minimize computation time' },
        { label: 'Balanced', value: 'balanced', description: 'Balance accuracy and speed' }
    ], {
        placeHolder: 'Select optimization target',
        title: 'Bio-HNET Optimization'
    });

    if (!target) return;

    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Optimizing Bio-HNET code...',
        cancellable: false
    }, async (progress) => {
        try {
            const config = vscode.workspace.getConfiguration('bioql');
            const mode = config.get('mode');

            const prompt = `Optimize this Bio-HNET code for ${target.label}:\n\n${code}`;
            const optimized = await callBioQLAssistant(prompt, mode);

            if (optimized) {
                editor.edit(editBuilder => {
                    editBuilder.replace(selection, optimized);
                });

                vscode.window.showInformationMessage('Bio-HNET code optimized!');
            }
        } catch (error) {
            vscode.window.showErrorMessage(`Error: ${error.message}`);
        }
    });
}

// ====================================================================
// MULTI-OMICS COMMANDS (NEW in v6.0.0)
// ====================================================================

/**
 * Analyze Protein Sequence - Generate code for protein analysis
 */
async function analyzeProteinSequence() {
    const sequence = await vscode.window.showInputBox({
        prompt: 'Enter protein sequence (amino acids)',
        placeHolder: 'MKTAYIAKQRQISFVKSHFSRQ'
    });
    if (!sequence) return;

    const request = `Analyze this protein sequence using BioQL proteomics: ${sequence}`;
    await processRequest(request, 'Protein Sequence Analysis');
}

/**
 * Predict PTM Sites - Generate code for PTM prediction
 */
async function predictPTM() {
    const sequence = await vscode.window.showInputBox({
        prompt: 'Enter protein sequence for PTM prediction',
        placeHolder: 'MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGP'
    });
    if (!sequence) return;

    const ptmType = await vscode.window.showQuickPick([
        { label: 'phosphorylation', description: 'Predict phosphorylation sites (Ser, Thr, Tyr)' },
        { label: 'acetylation', description: 'Predict acetylation sites (Lys)' },
        { label: 'methylation', description: 'Predict methylation sites (Lys, Arg)' }
    ], { placeHolder: 'Select PTM type' });
    if (!ptmType) return;

    const request = `Predict ${ptmType.label} sites in this protein: ${sequence}`;
    await processRequest(request, 'PTM Prediction');
}

/**
 * Predict Protein-Protein Interaction
 */
async function predictPPI() {
    const protein1 = await vscode.window.showInputBox({
        prompt: 'Enter first protein sequence',
        placeHolder: 'MKTAYIAKQRQISFVKSHFSRQ'
    });
    if (!protein1) return;

    const protein2 = await vscode.window.showInputBox({
        prompt: 'Enter second protein sequence',
        placeHolder: 'GIVEQCCTSICSLYQLENYCN'
    });
    if (!protein2) return;

    const request = `Predict protein-protein interaction between these sequences: Protein A: ${protein1}, Protein B: ${protein2}`;
    await processRequest(request, 'Protein-Protein Interaction Prediction');
}

/**
 * Identify Metabolite - Generate code for metabolite identification
 */
async function identifyMetabolite() {
    const mass = await vscode.window.showInputBox({
        prompt: 'Enter metabolite mass (Da)',
        placeHolder: '180.156'
    });
    if (!mass) return;

    const request = `Identify metabolite with mass ${mass} Da using BioQL metabolomics`;
    await processRequest(request, 'Metabolite Identification');
}

/**
 * Analyze Metabolic Pathway
 */
async function analyzePathway() {
    const pathway = await vscode.window.showQuickPick([
        { label: 'Glycolysis', description: 'Glucose to pyruvate' },
        { label: 'TCA Cycle', description: 'Citric acid cycle' },
        { label: 'Pentose Phosphate', description: 'PPP pathway' },
        { label: 'Fatty Acid', description: 'Lipid metabolism' }
    ], { placeHolder: 'Select pathway to analyze' });
    if (!pathway) return;

    const request = `Analyze ${pathway.label} pathway using BioQL metabolomics`;
    await processRequest(request, 'Metabolic Pathway Analysis');
}

/**
 * Metabolic Flux Analysis (FBA)
 */
async function fluxAnalysis() {
    const model = await vscode.window.showInputBox({
        prompt: 'Enter metabolic model name',
        placeHolder: 'iJO1366 (E. coli)'
    });
    if (!model) return;

    const request = `Perform flux balance analysis on ${model} using BioQL`;
    await processRequest(request, 'Metabolic Flux Analysis');
}

/**
 * Integrate Multi-Omics Data
 */
async function integrateOmics() {
    const layers = await vscode.window.showQuickPick([
        { label: 'transcriptomics', picked: true },
        { label: 'proteomics', picked: true },
        { label: 'metabolomics', picked: true }
    ], {
        placeHolder: 'Select omics layers to integrate',
        canPickMany: true
    });
    if (!layers || layers.length === 0) return;

    const layerNames = layers.map(l => l.label).join(', ');
    const request = `Integrate ${layerNames} data using BioQL multi-omics quantum fusion`;
    await processRequest(request, 'Multi-Omics Integration');
}

/**
 * Build Regulatory Network
 */
async function buildNetwork() {
    const networkType = await vscode.window.showQuickPick([
        { label: 'gene-regulatory', description: 'Gene regulatory network (GRN)' },
        { label: 'protein-protein', description: 'Protein-protein interaction network' },
        { label: 'metabolic', description: 'Metabolic reaction network' }
    ], { placeHolder: 'Select network type' });
    if (!networkType) return;

    const request = `Build ${networkType.label} network using BioQL multi-omics`;
    await processRequest(request, 'Regulatory Network Analysis');
}

/**
 * Call Genetic Variants
 */
async function callVariants() {
    const inputFile = await vscode.window.showInputBox({
        prompt: 'Enter BAM/VCF file path',
        placeHolder: 'sample.bam'
    });
    if (!inputFile) return;

    const request = `Call genetic variants from ${inputFile} using BioQL genomics`;
    await processRequest(request, 'Variant Calling');
}

/**
 * Analyze DNA Methylation
 */
async function analyzeMethylation() {
    const dataType = await vscode.window.showQuickPick([
        { label: 'bisulfite-seq', description: 'Bisulfite sequencing data' },
        { label: '450k-array', description: 'Illumina 450K array data' },
        { label: 'epic-array', description: 'Illumina EPIC array data' }
    ], { placeHolder: 'Select methylation data type' });
    if (!dataType) return;

    const request = `Analyze DNA methylation from ${dataType.label} using BioQL genomics`;
    await processRequest(request, 'DNA Methylation Analysis');
}

/**
 * Analyze RNA-Seq Data
 */
async function analyzeRNASeq() {
    const analysisType = await vscode.window.showQuickPick([
        { label: 'differential-expression', description: 'Find differentially expressed genes' },
        { label: 'pathway-enrichment', description: 'Pathway enrichment analysis' },
        { label: 'splicing', description: 'Alternative splicing analysis' }
    ], { placeHolder: 'Select RNA-Seq analysis type' });
    if (!analysisType) return;

    const request = `Perform ${analysisType.label} analysis using BioQL RNA-Seq`;
    await processRequest(request, 'RNA-Seq Analysis');
}

// ====================================================================

function deactivate() {
    if (outputChannel) {
        outputChannel.dispose();
    }
}

module.exports = {
    activate,
    deactivate
};
