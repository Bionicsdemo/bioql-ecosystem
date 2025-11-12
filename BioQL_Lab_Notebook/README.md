# BioQL Lab Notebook

## Project Description

BioQL Lab Notebook is a modern, web-based electronic lab notebook (ELN) designed specifically for biological research. It provides researchers with an intuitive interface to document experiments, manage protocols, track samples, and analyze results in a structured, queryable format.

## Features

- **Experiment Management**: Create, edit, and organize experiments with rich text formatting
- **Protocol Templates**: Reusable templates for common experimental procedures
- **Sample Tracking**: Keep track of biological samples, reagents, and materials
- **Data Visualization**: Built-in charts and graphs for experimental data
- **Search & Query**: Powerful search capabilities using BioQL query language
- **Collaboration**: Share experiments and protocols with team members
- **Version Control**: Track changes and maintain experiment history
- **Export Options**: Export experiments to PDF, CSV, or other formats

## Technology Stack

### Frontend
- HTML5, CSS3, JavaScript (ES6+)
- Modern responsive design
- Interactive data visualizations

### Backend
- Python Flask API
- RESTful architecture
- SQLite/PostgreSQL database support

## Project Structure

```
BioQL_Lab_Notebook/
├── frontend/           # Frontend HTML files
├── backend/           # Flask API backend
├── static/            # Static assets
│   ├── css/          # Stylesheets
│   └── images/       # Images and icons
├── js/               # JavaScript modules
├── templates/        # Experiment templates
├── package.json      # Node.js dependencies
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

## Installation

### Prerequisites
- Python 3.8+
- Node.js 14+ (optional, for development tools)

### Setup

1. Clone or download the project

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install Node.js dependencies (optional):
```bash
npm install
```

4. Run the Flask backend:
```bash
cd backend
python app.py
```

5. Open the frontend in your browser:
```
http://localhost:5000
```

## Usage

1. **Create New Experiment**: Click "New Experiment" to start documenting your research
2. **Use Templates**: Select from pre-built templates for common experiment types
3. **Add Data**: Enter observations, measurements, and attach files
4. **Query Data**: Use BioQL syntax to search and filter experiments
5. **Export Results**: Download your experiments in various formats

## Development

### Running Tests
```bash
python -m pytest
```

### Development Server
```bash
export FLASK_ENV=development
python backend/app.py
```

## Contributing

Contributions are welcome! Please follow these guidelines:
- Write clear commit messages
- Add tests for new features
- Update documentation as needed
- Follow PEP 8 style guidelines for Python code

## License

MIT License - See LICENSE file for details

## Contact

For questions or support, please open an issue on the project repository.

## Roadmap

- [ ] User authentication and authorization
- [ ] Cloud storage integration
- [ ] Advanced data analytics
- [ ] Mobile app support
- [ ] Integration with laboratory instruments
- [ ] Multi-language support
