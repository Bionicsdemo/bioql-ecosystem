# BioQL Lab Notebook - Quick Start Guide

Get up and running with BioQL Lab Notebook in 5 minutes!

---

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Optional: Node.js 14+ (for development tools)

---

## Installation Steps

### 1. Navigate to Project Directory
```bash
cd /Users/heinzjungbluth/Desktop/BioQL_Lab_Notebook
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize the Database
```bash
cd backend
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database created!')"
```

### 4. (Optional) Seed with Sample Data
```bash
# While in backend directory
python << EOF
from app import app, db
from models import Experiment, Protocol, Sample, Tag
from datetime import datetime

with app.app_context():
    # Create sample experiment
    tag = Tag(name='PCR')
    db.session.add(tag)

    exp = Experiment(
        title='Sample PCR Experiment',
        description='A sample experiment to get started',
        status='completed',
        created_at=datetime.now()
    )
    exp.tags.append(tag)
    db.session.add(exp)
    db.session.commit()
    print('Sample data added!')
EOF
```

### 5. Start the Server
```bash
# Make sure you're in the backend directory
python app.py
```

You should see:
```
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

### 6. Open Your Browser
Navigate to: **http://localhost:5000**

---

## Using Mock Data (No Backend Required)

If you want to explore the frontend without setting up the backend:

1. Open `/Users/heinzjungbluth/Desktop/BioQL_Lab_Notebook/js/api.js`
2. Ensure line 6 reads: `this.mockMode = true;`
3. Open `/Users/heinzjungbluth/Desktop/BioQL_Lab_Notebook/frontend/index.html` directly in your browser

The app will use realistic mock data for demonstration.

---

## First Steps

### Create Your First Experiment

1. Click the **"+ New Experiment"** button in the sidebar
2. Fill in:
   - Title: "My First Experiment"
   - Template: Select "PCR" or leave blank
   - Description: Brief description of your experiment
3. Click **"Create Experiment"**
4. You'll be taken to the experiment detail page

### Fill in Experiment Details

The experiment detail page has 5 tabs:

1. **Overview**: Objective, hypothesis, materials
2. **Protocol**: Step-by-step procedure
3. **Data**: Tables and uploaded data
4. **Results**: Observations, analysis, conclusions
5. **Notes**: Additional notes

### Save Your Work

Click the **"Save"** button in the header anytime to save changes.

---

## Keyboard Shortcuts

- **Ctrl/Cmd + S**: Save experiment (when on experiment page)
- **Esc**: Close modals

---

## Troubleshooting

### Port 5000 Already in Use
```bash
# Use a different port
python app.py
# Then edit line in app.py: app.run(debug=True, port=5001)
```

### Database Errors
```bash
# Reset database
cd backend
rm bioql_lab_notebook.db
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### Module Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### CSS/JS Not Loading
- Make sure you're accessing via http://localhost:5000 (not opening HTML directly)
- Check browser console for errors (F12)
- Verify all files are in correct directories

---

## Project Structure Quick Reference

```
BioQL_Lab_Notebook/
├── frontend/          # HTML pages - open in browser via Flask
├── backend/           # Flask app - run python app.py here
├── static/css/        # Stylesheets - automatically served
├── js/                # JavaScript - automatically served
├── templates/         # Experiment templates
└── requirements.txt   # Install with pip
```

---

## Common Tasks

### Add a New Tag
Tags are created automatically when you create/edit experiments.

### View All Experiments
Click **"Experiments"** in the top navigation.

### Search Experiments
Use the search box in the Experiments view or try the **BioQL Search** tab.

### Use Protocol Templates
When creating a new experiment, select a template from the dropdown:
- **PCR**: PCR amplification protocol
- **Western Blot**: Immunoblotting protocol
- **Cell Culture**: Cell culture maintenance

---

## Development Mode

### Enable Debug Mode
Already enabled by default! Check `backend/app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5000)
```

### Watch for Changes
Flask's debug mode automatically reloads when you change Python files.

For frontend changes (HTML/CSS/JS), just refresh your browser.

---

## Next Steps

1. **Explore the Templates**: Check out the experiment templates in `/templates/`
2. **Customize Styles**: Edit CSS files in `/static/css/`
3. **Add Features**: Extend the API in `/backend/routes.py`
4. **Read Documentation**: See README.md for detailed information

---

## Getting Help

- **Documentation**: See README.md and PROJECT_SUMMARY.md
- **API Reference**: Check `/backend/routes.py` for all endpoints
- **Sample Data**: Look at `/js/api.js` for data structure examples

---

## What's Working

✅ Dashboard with statistics
✅ Experiment creation and editing
✅ Protocol templates (PCR, Western Blot, Cell Culture)
✅ Tag system for organization
✅ Search and filtering
✅ BioQL query interface
✅ Responsive design
✅ Mock data mode for testing

---

## What's Coming Soon

🚧 User authentication
🚧 File attachments/uploads
🚧 Data visualization charts
🚧 PDF export
🚧 Advanced BioQL queries
🚧 Real-time collaboration

---

Happy experimenting! 🧬🔬
