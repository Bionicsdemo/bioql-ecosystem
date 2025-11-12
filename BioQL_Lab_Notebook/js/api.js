// API Client Module

export class API {
    constructor() {
        this.baseURL = 'http://localhost:5000/api';
        this.mockMode = true; // Set to false when backend is ready
    }

    async request(endpoint, options = {}) {
        if (this.mockMode) {
            return this.mockRequest(endpoint, options);
        }

        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    // Mock API for development
    mockRequest(endpoint, options) {
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve(this.getMockData(endpoint, options));
            }, 300);
        });
    }

    getMockData(endpoint, options) {
        const mockData = {
            '/experiments': this.getMockExperiments(),
            '/experiments/recent': this.getMockRecentExperiments(),
            '/dashboard/stats': this.getMockDashboardStats(),
            '/tags': this.getMockTags(),
            '/protocols': this.getMockProtocols(),
            '/samples': this.getMockSamples()
        };

        // Handle specific experiment by ID
        if (endpoint.startsWith('/experiments/') && endpoint.length > 13) {
            return this.getMockExperiment(endpoint.split('/')[2]);
        }

        // Handle POST requests
        if (options.method === 'POST') {
            if (endpoint === '/experiments') {
                const data = JSON.parse(options.body);
                return { id: Date.now().toString(), ...data };
            }
            if (endpoint === '/bioql/query') {
                return this.getMockQueryResults();
            }
        }

        return mockData[endpoint] || [];
    }

    getMockExperiments() {
        return [
            {
                id: '1',
                title: 'PCR Amplification of Gene X',
                description: 'Amplifying the target gene region for sequencing analysis',
                date: '2024-01-15',
                status: 'completed',
                tags: ['PCR', 'molecular-biology', 'genetics']
            },
            {
                id: '2',
                title: 'Western Blot Analysis - Protein Expression',
                description: 'Analyzing protein expression levels in treated vs control samples',
                date: '2024-01-18',
                status: 'in-progress',
                tags: ['western-blot', 'protein', 'analysis']
            },
            {
                id: '3',
                title: 'Cell Culture Optimization',
                description: 'Testing different media conditions for optimal cell growth',
                date: '2024-01-20',
                status: 'planning',
                tags: ['cell-culture', 'optimization']
            },
            {
                id: '4',
                title: 'ELISA Assay for Cytokine Detection',
                description: 'Quantifying cytokine levels in cell culture supernatants',
                date: '2024-01-22',
                status: 'in-progress',
                tags: ['ELISA', 'immunology', 'cytokines']
            },
            {
                id: '5',
                title: 'DNA Extraction from Tissue Samples',
                description: 'Extracting genomic DNA from frozen tissue specimens',
                date: '2024-01-10',
                status: 'completed',
                tags: ['DNA-extraction', 'molecular-biology']
            },
            {
                id: '6',
                title: 'Flow Cytometry Analysis',
                description: 'Characterizing cell populations using fluorescent markers',
                date: '2024-01-25',
                status: 'planning',
                tags: ['flow-cytometry', 'cell-analysis']
            }
        ];
    }

    getMockRecentExperiments() {
        return this.getMockExperiments().slice(0, 5);
    }

    getMockExperiment(id) {
        return {
            id,
            title: 'PCR Amplification of Gene X',
            date: '2024-01-15',
            status: 'completed',
            tags: ['PCR', 'molecular-biology'],
            objective: 'Amplify the target gene region for downstream sequencing',
            hypothesis: 'The PCR will successfully amplify a 500bp fragment',
            materials: 'DNA template, primers, Taq polymerase, dNTPs, PCR buffer',
            protocol: [
                { description: 'Prepare PCR master mix' },
                { description: 'Add template DNA' },
                { description: 'Run PCR cycle: 95C 3min, then 30 cycles of 95C 30s, 55C 30s, 72C 1min' },
                { description: 'Final extension at 72C for 5 min' },
                { description: 'Run gel electrophoresis to verify product' }
            ],
            observations: 'Clear band observed at expected size',
            analysis: 'PCR successfully amplified the target region',
            conclusions: 'The optimized PCR protocol works reliably for this target',
            notes: 'Consider increasing annealing temperature for better specificity'
        };
    }

    getMockDashboardStats() {
        return {
            totalExperiments: 42,
            totalProtocols: 15,
            totalSamples: 128,
            recentActivity: 8,
            recentActivities: [
                {
                    action: 'Experiment Created',
                    description: 'Western Blot Analysis',
                    date: '2024-01-25'
                },
                {
                    action: 'Experiment Completed',
                    description: 'PCR Amplification',
                    date: '2024-01-24'
                },
                {
                    action: 'Protocol Added',
                    description: 'ELISA Standard Protocol',
                    date: '2024-01-23'
                }
            ]
        };
    }

    getMockTags() {
        return [
            { name: 'PCR', count: 12 },
            { name: 'western-blot', count: 8 },
            { name: 'cell-culture', count: 15 },
            { name: 'molecular-biology', count: 20 },
            { name: 'protein', count: 10 },
            { name: 'DNA-extraction', count: 7 },
            { name: 'ELISA', count: 5 },
            { name: 'immunology', count: 9 }
        ];
    }

    getMockProtocols() {
        return [
            {
                id: '1',
                title: 'Standard PCR Protocol',
                description: 'General purpose PCR amplification',
                steps: 8,
                usageCount: 25
            },
            {
                id: '2',
                title: 'Western Blot Protocol',
                description: 'Protein detection via immunoblotting',
                steps: 12,
                usageCount: 15
            },
            {
                id: '3',
                title: 'Cell Culture Maintenance',
                description: 'Routine cell culture procedures',
                steps: 6,
                usageCount: 50
            }
        ];
    }

    getMockSamples() {
        return [
            {
                id: 'S001',
                name: 'Tissue Sample A',
                type: 'Tissue',
                location: 'Freezer -80C, Box 3',
                dateAdded: '2024-01-10',
                status: 'Available'
            },
            {
                id: 'S002',
                name: 'DNA Extract B',
                type: 'DNA',
                location: 'Fridge 4C, Rack 2',
                dateAdded: '2024-01-15',
                status: 'Available'
            },
            {
                id: 'S003',
                name: 'Cell Line HEK293',
                type: 'Cells',
                location: 'Liquid Nitrogen',
                dateAdded: '2024-01-05',
                status: 'In Use'
            }
        ];
    }

    getMockQueryResults() {
        return [
            {
                id: '1',
                title: 'PCR Amplification of Gene X',
                description: 'Amplifying the target gene region',
                date: '2024-01-15',
                status: 'completed'
            },
            {
                id: '2',
                title: 'Western Blot Analysis',
                description: 'Protein expression analysis',
                date: '2024-01-18',
                status: 'in-progress'
            }
        ];
    }

    // Public API methods
    async getExperiments() {
        return this.request('/experiments');
    }

    async getExperiment(id) {
        return this.request(`/experiments/${id}`);
    }

    async createExperiment(data) {
        return this.request('/experiments', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async updateExperiment(id, data) {
        return this.request(`/experiments/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteExperiment(id) {
        return this.request(`/experiments/${id}`, {
            method: 'DELETE'
        });
    }

    async getRecentExperiments() {
        return this.request('/experiments/recent');
    }

    async getDashboardStats() {
        return this.request('/dashboard/stats');
    }

    async getTags() {
        return this.request('/tags');
    }

    async getProtocols() {
        return this.request('/protocols');
    }

    async getSamples() {
        return this.request('/samples');
    }

    async executeBioQLQuery(query) {
        return this.request('/bioql/query', {
            method: 'POST',
            body: JSON.stringify({ query })
        });
    }
}
