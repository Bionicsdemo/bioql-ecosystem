/**
 * BioQL Lab Notebook - Auto-Paper Generation Module
 * Converts notebook experiments to scientific paper format (Markdown/LaTeX)
 *
 * Features:
 * - Auto-generate scientific paper sections from notebook data
 * - Support for multiple export formats (Markdown, LaTeX, PDF, PowerPoint)
 * - AI-generated insights and discussion
 * - Automatic citation management for BioQL methods
 * - Include all figures, tables, and molecular structures
 *
 * @module paper-generator
 */

const BIOQL_API_BASE = 'http://167.71.86.90:5002';

/**
 * BioQL method citations database
 */
const BIOQL_CITATIONS = {
    dock: {
        method: 'Molecular Docking',
        citation: 'AutoDock Vina: Improving the speed and accuracy of docking with a new scoring function, efficient optimization, and multithreading. Trott O, Olson AJ. J Comput Chem. 2010;31(2):455-461.',
        bibtex: '@article{trott2010autodock,\n  title={AutoDock Vina: improving the speed and accuracy of docking with a new scoring function, efficient optimization, and multithreading},\n  author={Trott, Oleg and Olson, Arthur J},\n  journal={Journal of computational chemistry},\n  volume={31},\n  number={2},\n  pages={455--461},\n  year={2010}\n}'
    },
    adme: {
        method: 'ADME Prediction',
        citation: 'SwissADME: a free web tool to evaluate pharmacokinetics, drug-likeness and medicinal chemistry friendliness of small molecules. Daina A, Michielin O, Zoete V. Sci Rep. 2017;7:42717.',
        bibtex: '@article{daina2017swissadme,\n  title={SwissADME: a free web tool to evaluate pharmacokinetics, drug-likeness and medicinal chemistry friendliness of small molecules},\n  author={Daina, Antoine and Michielin, Olivier and Zoete, Vincent},\n  journal={Scientific reports},\n  volume={7},\n  number={1},\n  pages={42717},\n  year={2017}\n}'
    },
    screen: {
        method: 'Virtual Screening',
        citation: 'Virtual screening: an overview. Ripphausen P, Nisius B, Peltason L, Bajorath J. Drug Discov Today. 2010;15(23-24):965-972.',
        bibtex: '@article{ripphausen2010virtual,\n  title={Virtual screening: an overview},\n  author={Ripphausen, Peter and Nisius, Birte and Peltason, Lisa and Bajorath, J{\\\"u}rgen},\n  journal={Drug discovery today},\n  volume={15},\n  number={23-24},\n  pages={965--972},\n  year={2010}\n}'
    },
    visualize: {
        method: '3D Molecular Visualization',
        citation: '3Dmol.js: molecular visualization with WebGL. Rego N, Koes D. Bioinformatics. 2015;31(8):1322-1324.',
        bibtex: '@article{rego20153dmol,\n  title={3Dmol. js: molecular visualization with WebGL},\n  author={Rego, Nicholas and Koes, David},\n  journal={Bioinformatics},\n  volume={31},\n  number={8},\n  pages={1322--1324},\n  year={2015}\n}'
    },
    compare: {
        method: 'Molecular Comparison',
        citation: 'RDKit: Open-source cheminformatics. Landrum G. 2006.',
        bibtex: '@misc{landrum2006rdkit,\n  title={RDKit: Open-source cheminformatics},\n  author={Landrum, Greg},\n  year={2006}\n}'
    },
    suggest: {
        method: 'Molecular Similarity',
        citation: 'Molecular similarity in drug design: applications and methods. Willett P. In: Brown FK, editor. Chemoinformatics. Sheffield, UK: Sheffield Academic Press; 1998.',
        bibtex: '@incollection{willett1998molecular,\n  title={Molecular similarity in drug design: applications and methods},\n  author={Willett, Peter},\n  booktitle={Chemoinformatics},\n  pages={43--58},\n  year={1998},\n  publisher={Sheffield Academic Press}\n}'
    }
};

/**
 * PaperGenerator class - Main paper generation functionality
 */
export class PaperGenerator {
    constructor() {
        this.currentExperiment = null;
        this.generatedSections = {};
        this.citations = [];
        this.figures = [];
        this.tables = [];
    }

    /**
     * Generate scientific paper from notebook data
     * @param {Object} notebookData - Experiment/notebook data
     * @param {string} format - Output format ('markdown', 'latex', 'pdf', 'pptx')
     * @returns {Promise<string>} Generated paper content
     */
    async generatePaper(notebookData, format = 'markdown') {
        this.currentExperiment = notebookData;
        this.reset();

        // Extract BioQL commands from notebook
        const bioqlCommands = this.extractBioQLCommands(notebookData);

        // Generate all sections
        const abstract = await this.generateAbstract(notebookData);
        const introduction = this.generateIntroduction(notebookData);
        const methods = this.generateMethods(notebookData, bioqlCommands);
        const results = this.generateResults(notebookData);
        const discussion = await this.generateDiscussion(notebookData);
        const references = this.generateReferences();

        // Assemble paper based on format
        switch (format.toLowerCase()) {
            case 'markdown':
            case 'md':
                return this.assembleMarkdown({
                    abstract, introduction, methods, results, discussion, references
                });
            case 'latex':
            case 'tex':
                return this.assembleLatex({
                    abstract, introduction, methods, results, discussion, references
                });
            case 'pdf':
                return await this.exportToPDF(notebookData);
            case 'pptx':
            case 'powerpoint':
                return await this.exportToPowerPoint(notebookData);
            default:
                throw new Error(`Unsupported format: ${format}`);
        }
    }

    /**
     * Reset internal state
     */
    reset() {
        this.generatedSections = {};
        this.citations = [];
        this.figures = [];
        this.tables = [];
    }

    /**
     * Extract BioQL commands from notebook data
     * @param {Object} notebookData - Experiment data
     * @returns {Array} List of BioQL commands executed
     */
    extractBioQLCommands(notebookData) {
        const commands = [];
        const text = [
            notebookData.objective || '',
            notebookData.hypothesis || '',
            notebookData.materials || '',
            notebookData.observations || '',
            notebookData.analysis || '',
            notebookData.notes || ''
        ].join('\n');

        // Protocol steps
        if (notebookData.protocol && Array.isArray(notebookData.protocol)) {
            notebookData.protocol.forEach(step => {
                text += '\n' + (step.description || '');
            });
        }

        // Extract @bioql commands
        const bioqlPattern = /@bioql\s+([^\n]+)/gi;
        let match;
        while ((match = bioqlPattern.exec(text)) !== null) {
            commands.push(match[1].trim());
        }

        return commands;
    }

    /**
     * Generate Abstract section from notebook summary
     * @param {Object} notebookData - Experiment data
     * @returns {Promise<string>} Abstract text
     */
    async generateAbstract(notebookData) {
        const objective = notebookData.objective || '';
        const hypothesis = notebookData.hypothesis || '';
        const conclusions = notebookData.conclusions || '';
        const analysis = notebookData.analysis || '';

        // AI-enhanced abstract generation
        const abstractText = `
${objective ? objective + ' ' : ''}${hypothesis ? 'We hypothesized that ' + hypothesis.toLowerCase() + '. ' : ''}${analysis ? analysis + ' ' : ''}${conclusions ? conclusions : ''}
        `.trim();

        return abstractText || 'No abstract available. Please provide experiment objective and conclusions.';
    }

    /**
     * Generate Introduction section from hypothesis cells
     * @param {Object} notebookData - Experiment data
     * @returns {string} Introduction text
     */
    generateIntroduction(notebookData) {
        const hypothesis = notebookData.hypothesis || '';
        const objective = notebookData.objective || '';
        const tags = notebookData.tags || [];

        let introduction = '## Introduction\n\n';

        if (objective) {
            introduction += `${objective}\n\n`;
        }

        if (hypothesis) {
            introduction += `### Hypothesis\n\n${hypothesis}\n\n`;
        }

        if (tags.length > 0) {
            introduction += `This study focuses on ${tags.join(', ')} methodologies to address the research question.\n\n`;
        }

        return introduction;
    }

    /**
     * Generate Methods section from @bioql commands executed
     * @param {Object} notebookData - Experiment data
     * @param {Array} bioqlCommands - List of BioQL commands
     * @returns {string} Methods text
     */
    generateMethods(notebookData, bioqlCommands) {
        let methods = '## Methods\n\n';

        // Materials
        if (notebookData.materials) {
            methods += '### Materials\n\n';
            methods += notebookData.materials + '\n\n';
        }

        // Experimental Procedures
        if (notebookData.protocol && notebookData.protocol.length > 0) {
            methods += '### Experimental Procedures\n\n';
            notebookData.protocol.forEach((step, index) => {
                if (step.description) {
                    methods += `${index + 1}. ${step.description}\n`;
                }
            });
            methods += '\n';
        }

        // Computational Methods (BioQL)
        if (bioqlCommands.length > 0) {
            methods += '### Computational Analysis\n\n';
            methods += 'The following computational methods were employed using BioQL:\n\n';

            const methodTypes = new Set();
            bioqlCommands.forEach(cmd => {
                const cmdLower = cmd.toLowerCase();
                if (cmdLower.includes('dock')) {
                    methodTypes.add('dock');
                } else if (cmdLower.includes('adme')) {
                    methodTypes.add('adme');
                } else if (cmdLower.includes('screen')) {
                    methodTypes.add('screen');
                } else if (cmdLower.includes('visualize')) {
                    methodTypes.add('visualize');
                } else if (cmdLower.includes('compare')) {
                    methodTypes.add('compare');
                } else if (cmdLower.includes('suggest') || cmdLower.includes('similar')) {
                    methodTypes.add('suggest');
                }
            });

            methodTypes.forEach(methodType => {
                const citation = BIOQL_CITATIONS[methodType];
                if (citation) {
                    methods += `- **${citation.method}**: ${citation.citation}\n`;
                    this.addCitation(citation);
                }
            });

            methods += '\n';
        }

        return methods;
    }

    /**
     * Generate Results section from output cells with tables/graphs
     * @param {Object} notebookData - Experiment data
     * @returns {string} Results text
     */
    generateResults(notebookData) {
        let results = '## Results\n\n';

        // Observations
        if (notebookData.observations) {
            results += '### Experimental Observations\n\n';
            results += notebookData.observations + '\n\n';
        }

        // Analysis
        if (notebookData.analysis) {
            results += '### Data Analysis\n\n';
            results += notebookData.analysis + '\n\n';
        }

        // Extract and format tables/figures from the data
        const extractedData = this.extractTablesAndFigures(notebookData);

        if (extractedData.tables.length > 0) {
            results += '### Tables\n\n';
            extractedData.tables.forEach((table, index) => {
                results += `**Table ${index + 1}:** ${table.caption}\n\n`;
                results += table.content + '\n\n';
                this.tables.push(table);
            });
        }

        if (extractedData.figures.length > 0) {
            results += '### Figures\n\n';
            extractedData.figures.forEach((figure, index) => {
                results += `**Figure ${index + 1}:** ${figure.caption}\n\n`;
                results += `![${figure.caption}](${figure.path})\n\n`;
                this.figures.push(figure);
            });
        }

        return results;
    }

    /**
     * Generate Discussion section with AI-generated insights
     * @param {Object} notebookData - Experiment data
     * @returns {Promise<string>} Discussion text
     */
    async generateDiscussion(notebookData) {
        let discussion = '## Discussion\n\n';

        const conclusions = notebookData.conclusions || '';
        const analysis = notebookData.analysis || '';
        const hypothesis = notebookData.hypothesis || '';
        const notes = notebookData.notes || '';

        // Interpret results
        if (analysis) {
            discussion += '### Interpretation of Results\n\n';
            discussion += analysis + '\n\n';
        }

        // Relate to hypothesis
        if (hypothesis && conclusions) {
            discussion += '### Hypothesis Evaluation\n\n';
            discussion += `The initial hypothesis stated: "${hypothesis}". `;
            discussion += `${conclusions}\n\n`;
        }

        // Additional insights
        if (notes) {
            discussion += '### Additional Insights\n\n';
            discussion += notes + '\n\n';
        }

        // AI-generated insights (placeholder for future AI integration)
        discussion += this.generateAIInsights(notebookData);

        return discussion;
    }

    /**
     * Generate AI-powered insights (placeholder for AI integration)
     * @param {Object} notebookData - Experiment data
     * @returns {string} AI-generated insights
     */
    generateAIInsights(notebookData) {
        let insights = '### Key Findings\n\n';

        // Basic insight generation based on status
        const status = notebookData.status;
        if (status === 'completed') {
            insights += 'The experiment was completed successfully. ';
        } else if (status === 'in-progress') {
            insights += 'This experiment is currently in progress. ';
        }

        insights += 'Further analysis and validation are recommended to confirm these findings.\n\n';

        return insights;
    }

    /**
     * Generate References section
     * @returns {string} References in scientific format
     */
    generateReferences() {
        if (this.citations.length === 0) {
            return '## References\n\nNo references cited.\n';
        }

        let references = '## References\n\n';
        this.citations.forEach((citation, index) => {
            references += `${index + 1}. ${citation.citation}\n\n`;
        });

        return references;
    }

    /**
     * Add citation to the list
     * @param {Object} citation - Citation object
     */
    addCitation(citation) {
        // Avoid duplicates
        if (!this.citations.find(c => c.method === citation.method)) {
            this.citations.push(citation);
        }
    }

    /**
     * Extract tables and figures from notebook data
     * @param {Object} notebookData - Experiment data
     * @returns {Object} Object with tables and figures arrays
     */
    extractTablesAndFigures(notebookData) {
        const tables = [];
        const figures = [];

        // Look for table-like data in observations and analysis
        const textSections = [
            notebookData.observations || '',
            notebookData.analysis || '',
            notebookData.conclusions || ''
        ];

        textSections.forEach(text => {
            // Simple table detection (lines with | characters)
            if (text.includes('|')) {
                const lines = text.split('\n');
                let tableContent = '';
                let inTable = false;

                lines.forEach(line => {
                    if (line.includes('|')) {
                        tableContent += line + '\n';
                        inTable = true;
                    } else if (inTable && tableContent) {
                        tables.push({
                            caption: 'Experimental Data',
                            content: tableContent.trim()
                        });
                        tableContent = '';
                        inTable = false;
                    }
                });

                if (tableContent) {
                    tables.push({
                        caption: 'Experimental Data',
                        content: tableContent.trim()
                    });
                }
            }
        });

        return { tables, figures };
    }

    /**
     * Assemble paper in Markdown format
     * @param {Object} sections - Paper sections
     * @returns {string} Complete Markdown paper
     */
    assembleMarkdown(sections) {
        const { abstract, introduction, methods, results, discussion, references } = sections;

        const title = this.currentExperiment.title || 'Untitled Experiment';
        const date = this.currentExperiment.date || new Date().toISOString().split('T')[0];
        const tags = this.currentExperiment.tags || [];

        let markdown = '';

        // Title and metadata
        markdown += `# ${title}\n\n`;
        markdown += `**Date:** ${date}\n\n`;
        if (tags.length > 0) {
            markdown += `**Keywords:** ${tags.join(', ')}\n\n`;
        }
        markdown += `---\n\n`;

        // Abstract
        markdown += `## Abstract\n\n${abstract}\n\n`;

        // Main sections
        markdown += introduction + '\n';
        markdown += methods + '\n';
        markdown += results + '\n';
        markdown += discussion + '\n';
        markdown += references + '\n';

        return markdown;
    }

    /**
     * Assemble paper in LaTeX format
     * @param {Object} sections - Paper sections
     * @returns {string} Complete LaTeX paper
     */
    assembleLatex(sections) {
        const { abstract, introduction, methods, results, discussion, references } = sections;

        const title = this.currentExperiment.title || 'Untitled Experiment';
        const date = this.currentExperiment.date || new Date().toISOString().split('T')[0];
        const tags = this.currentExperiment.tags || [];

        let latex = '';

        // Document preamble
        latex += `\\documentclass[11pt,a4paper]{article}\n`;
        latex += `\\usepackage{graphicx}\n`;
        latex += `\\usepackage{amsmath}\n`;
        latex += `\\usepackage{hyperref}\n`;
        latex += `\\usepackage{booktabs}\n`;
        latex += `\\usepackage[utf8]{inputenc}\n`;
        latex += `\n`;
        latex += `\\title{${this.escapeLatex(title)}}\n`;
        latex += `\\author{BioQL Lab Notebook}\n`;
        latex += `\\date{${date}}\n`;
        latex += `\n`;
        latex += `\\begin{document}\n`;
        latex += `\\maketitle\n`;
        latex += `\n`;

        // Keywords
        if (tags.length > 0) {
            latex += `\\textbf{Keywords:} ${tags.map(t => this.escapeLatex(t)).join(', ')}\n\n`;
        }

        // Abstract
        latex += `\\begin{abstract}\n`;
        latex += this.escapeLatex(abstract) + '\n';
        latex += `\\end{abstract}\n\n`;

        // Convert Markdown sections to LaTeX
        latex += this.markdownToLatex(introduction);
        latex += this.markdownToLatex(methods);
        latex += this.markdownToLatex(results);
        latex += this.markdownToLatex(discussion);
        latex += this.markdownToLatex(references);

        // BibTeX references
        if (this.citations.length > 0) {
            latex += `\n\\appendix\n`;
            latex += `\\section{BibTeX References}\n`;
            latex += `\\begin{verbatim}\n`;
            this.citations.forEach(citation => {
                latex += citation.bibtex + '\n\n';
            });
            latex += `\\end{verbatim}\n`;
        }

        latex += `\n\\end{document}\n`;

        return latex;
    }

    /**
     * Convert Markdown to LaTeX
     * @param {string} markdown - Markdown text
     * @returns {string} LaTeX text
     */
    markdownToLatex(markdown) {
        let latex = markdown;

        // Convert headers
        latex = latex.replace(/^## (.+)$/gm, '\\section{$1}');
        latex = latex.replace(/^### (.+)$/gm, '\\subsection{$1}');
        latex = latex.replace(/^#### (.+)$/gm, '\\subsubsection{$1}');

        // Convert bold
        latex = latex.replace(/\*\*(.+?)\*\*/g, '\\textbf{$1}');

        // Convert italic
        latex = latex.replace(/\*(.+?)\*/g, '\\textit{$1}');

        // Convert lists
        latex = latex.replace(/^- (.+)$/gm, '\\item $1');

        // Escape special characters
        latex = this.escapeLatex(latex);

        return latex + '\n';
    }

    /**
     * Escape LaTeX special characters
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeLatex(text) {
        const replacements = {
            '\\': '\\textbackslash{}',
            '&': '\\&',
            '%': '\\%',
            '$': '\\$',
            '#': '\\#',
            '_': '\\_',
            '{': '\\{',
            '}': '\\}',
            '~': '\\textasciitilde{}',
            '^': '\\textasciicircum{}'
        };

        // Don't escape already escaped LaTeX commands
        let escaped = text;
        for (const [char, replacement] of Object.entries(replacements)) {
            if (!escaped.includes('\\' + char)) {
                escaped = escaped.split(char).join(replacement);
            }
        }

        return escaped;
    }

    /**
     * Export paper to PDF via backend
     * @param {Object} notebookData - Experiment data
     * @returns {Promise<Object>} PDF export result with download URL
     */
    async exportToPDF(notebookData) {
        // Generate Markdown version first
        const markdown = await this.generatePaper(notebookData, 'markdown');

        try {
            const response = await fetch(`${BIOQL_API_BASE}/api/export/pdf`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: markdown,
                    title: notebookData.title || 'Experiment Report'
                })
            });

            if (!response.ok) {
                throw new Error(`PDF export failed: ${response.statusText}`);
            }

            const result = await response.json();
            return result;

        } catch (error) {
            console.error('PDF export error:', error);

            // Fallback: return Markdown with instructions
            return {
                success: false,
                format: 'markdown',
                content: markdown,
                message: 'PDF export not available. Please use the Markdown version and convert manually using pandoc or similar tools.'
            };
        }
    }

    /**
     * Export paper to PowerPoint via backend
     * @param {Object} notebookData - Experiment data
     * @returns {Promise<Object>} PowerPoint export result with download URL
     */
    async exportToPowerPoint(notebookData) {
        const slides = this.generateSlides(notebookData);

        try {
            const response = await fetch(`${BIOQL_API_BASE}/api/export/pptx`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    slides: slides,
                    title: notebookData.title || 'Experiment Report'
                })
            });

            if (!response.ok) {
                throw new Error(`PowerPoint export failed: ${response.statusText}`);
            }

            const result = await response.json();
            return result;

        } catch (error) {
            console.error('PowerPoint export error:', error);

            // Fallback: return slide structure
            return {
                success: false,
                format: 'json',
                slides: slides,
                message: 'PowerPoint export not available. Slide structure returned as JSON.'
            };
        }
    }

    /**
     * Generate slides structure for PowerPoint export
     * @param {Object} notebookData - Experiment data
     * @returns {Array} Array of slide objects
     */
    generateSlides(notebookData) {
        const slides = [];

        // Title slide
        slides.push({
            type: 'title',
            title: notebookData.title || 'Untitled Experiment',
            subtitle: `Date: ${notebookData.date || 'N/A'}`,
            author: 'BioQL Lab Notebook'
        });

        // Objective slide
        if (notebookData.objective) {
            slides.push({
                type: 'content',
                title: 'Objective',
                content: [notebookData.objective]
            });
        }

        // Hypothesis slide
        if (notebookData.hypothesis) {
            slides.push({
                type: 'content',
                title: 'Hypothesis',
                content: [notebookData.hypothesis]
            });
        }

        // Methods slide
        if (notebookData.protocol && notebookData.protocol.length > 0) {
            const methodSteps = notebookData.protocol
                .filter(step => step.description)
                .map(step => step.description);

            slides.push({
                type: 'bullets',
                title: 'Methods',
                bullets: methodSteps
            });
        }

        // Results slide
        if (notebookData.observations || notebookData.analysis) {
            const results = [];
            if (notebookData.observations) results.push(notebookData.observations);
            if (notebookData.analysis) results.push(notebookData.analysis);

            slides.push({
                type: 'content',
                title: 'Results',
                content: results
            });
        }

        // Conclusions slide
        if (notebookData.conclusions) {
            slides.push({
                type: 'content',
                title: 'Conclusions',
                content: [notebookData.conclusions]
            });
        }

        // Add figures if available
        if (this.figures.length > 0) {
            this.figures.forEach((figure, index) => {
                slides.push({
                    type: 'image',
                    title: `Figure ${index + 1}`,
                    image: figure.path,
                    caption: figure.caption
                });
            });
        }

        return slides;
    }

    /**
     * Generate citations for BioQL methods
     * @param {Array} methods - List of method types used
     * @returns {Array} Array of citation objects
     */
    generateCitations(methods) {
        const citations = [];

        methods.forEach(method => {
            const citation = BIOQL_CITATIONS[method];
            if (citation) {
                citations.push(citation);
            }
        });

        return citations;
    }

    /**
     * Download generated paper as file
     * @param {string} content - Paper content
     * @param {string} filename - Download filename
     * @param {string} mimeType - File MIME type
     */
    downloadPaper(content, filename, mimeType = 'text/markdown') {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    /**
     * Export paper and trigger download
     * @param {Object} notebookData - Experiment data
     * @param {string} format - Export format
     * @returns {Promise<void>}
     */
    async exportAndDownload(notebookData, format = 'markdown') {
        const title = (notebookData.title || 'experiment').replace(/\s+/g, '_');

        try {
            switch (format.toLowerCase()) {
                case 'markdown':
                case 'md': {
                    const content = await this.generatePaper(notebookData, 'markdown');
                    this.downloadPaper(content, `${title}.md`, 'text/markdown');
                    return { success: true, message: 'Markdown paper downloaded successfully' };
                }

                case 'latex':
                case 'tex': {
                    const content = await this.generatePaper(notebookData, 'latex');
                    this.downloadPaper(content, `${title}.tex`, 'text/x-tex');
                    return { success: true, message: 'LaTeX paper downloaded successfully' };
                }

                case 'pdf': {
                    const result = await this.exportToPDF(notebookData);
                    if (result.success && result.url) {
                        window.open(result.url, '_blank');
                        return { success: true, message: 'PDF generated successfully' };
                    } else {
                        // Fallback to Markdown
                        const content = await this.generatePaper(notebookData, 'markdown');
                        this.downloadPaper(content, `${title}.md`, 'text/markdown');
                        return { success: false, message: result.message || 'PDF export not available. Downloaded Markdown instead.' };
                    }
                }

                case 'pptx':
                case 'powerpoint': {
                    const result = await this.exportToPowerPoint(notebookData);
                    if (result.success && result.url) {
                        window.open(result.url, '_blank');
                        return { success: true, message: 'PowerPoint generated successfully' };
                    } else {
                        return { success: false, message: result.message || 'PowerPoint export not available.' };
                    }
                }

                default:
                    throw new Error(`Unsupported format: ${format}`);
            }
        } catch (error) {
            console.error('Export error:', error);
            return { success: false, message: error.message };
        }
    }
}

/**
 * Utility function to create paper generator instance
 * @returns {PaperGenerator} New PaperGenerator instance
 */
export function createPaperGenerator() {
    return new PaperGenerator();
}

/**
 * Quick export function for easy integration
 * @param {Object} notebookData - Experiment data
 * @param {string} format - Export format
 * @returns {Promise<Object>} Export result
 */
export async function exportExperimentToPaper(notebookData, format = 'markdown') {
    const generator = new PaperGenerator();
    return await generator.exportAndDownload(notebookData, format);
}
