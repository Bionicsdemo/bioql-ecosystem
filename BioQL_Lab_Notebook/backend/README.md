# BioQL Lab Notebook Backend

Flask REST API server for managing lab notebooks and integrating with BioQL workflows.

## Features

- **Notebook Management**: Create, read, update, delete lab notebooks
- **BioQL Integration**: Execute @bioql commands via API
- **Real-time Collaboration**: WebSocket support for collaborative editing
- **Templates**: Pre-built experiment templates
- **Paper Export**: Generate papers/reports from notebooks
- **SQLite Database**: Persistent storage for notebooks and executions
- **API Key Authentication**: Secure access control
- **CORS Enabled**: Cross-origin resource sharing
- **Comprehensive Logging**: Using loguru

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python notebook_server.py
```

The server will start on `http://localhost:5003`

## API Endpoints

### Notebooks

- `POST /api/notebook/create` - Create new notebook
  ```json
  {
    "title": "My Experiment",
    "content": "Notebook content...",
    "metadata": {"tags": ["protein", "analysis"]}
  }
  ```

- `GET /api/notebook/<id>` - Get notebook by ID
- `PUT /api/notebook/<id>` - Update notebook
- `DELETE /api/notebook/<id>` - Delete notebook
- `GET /api/notebooks` - List all user notebooks

### Execution

- `POST /api/execute` - Execute BioQL command
  ```json
  {
    "command": "@bioql get protein P53",
    "notebook_id": "optional-notebook-id"
  }
  ```

### Export

- `POST /api/export/paper` - Generate paper from notebook
  ```json
  {
    "notebook_id": "notebook-id",
    "format": "markdown"
  }
  ```

### Templates

- `GET /api/templates` - Get experiment templates
- `GET /api/templates?category=protein` - Get templates by category

### Collaboration

- `POST /api/collaborate` - Initiate collaboration session

### WebSocket Events

Connect to `ws://localhost:5003` and use these events:

- `join_notebook` - Join a notebook room
  ```json
  {"notebook_id": "...", "user_id": "..."}
  ```

- `leave_notebook` - Leave a notebook room
- `notebook_edit` - Broadcast edits
- `cursor_position` - Share cursor position

## Authentication

All API requests (except `/health` and `/api/templates`) require an API key:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:5003/api/notebooks
```

## Database Schema

### Notebooks Table
- `id` - Unique identifier
- `user_id` - User identifier (from API key)
- `title` - Notebook title
- `content` - Notebook content (text/markdown)
- `metadata` - JSON metadata
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

### Executions Table
- `id` - Unique identifier
- `notebook_id` - Associated notebook
- `command` - BioQL command executed
- `result` - Execution result (JSON)
- `status` - success/error
- `created_at` - Execution timestamp

### Templates Table
- `id` - Unique identifier
- `name` - Template name
- `description` - Template description
- `content` - Template content (JSON)
- `category` - Template category
- `created_at` - Creation timestamp

## Environment Variables

- `SECRET_KEY` - Flask secret key (optional, defaults to development key)

## Production Deployment

For production, use gunicorn with eventlet:

```bash
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5003 notebook_server:app
```

## Logging

Logs are written to:
- Console (stdout)
- `notebook_server.log` (rotated at 10 MB, kept for 10 days)

## BioQL Integration

The server integrates with the BioQL Workflow API at `http://167.71.86.90:5002`. All `@bioql` commands are forwarded to this API for execution.

## Development

```bash
# Install development dependencies
pip install -r requirements.txt

# Run in debug mode
python notebook_server.py

# Run tests (if available)
pytest

# Format code
black notebook_server.py

# Lint code
flake8 notebook_server.py
```

## License

MIT License
