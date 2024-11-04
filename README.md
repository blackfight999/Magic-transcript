# Flask Web Application

This is a Flask-based web application that integrates with Google's AI services and YouTube transcript functionality.

## Project Structure
```
├── app.py              # Main Flask application
├── requirements.txt    # Project dependencies
├── static/            # Static files
│   ├── css/          # CSS stylesheets
│   └── js/           # JavaScript files
└── templates/         # HTML templates
```

## Setup Instructions

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

## Dependencies

Major dependencies include:
- Flask 3.0.3
- Google AI Generation Language 0.6.10
- Google Generative AI 0.8.3
- YouTube Transcript API 0.6.2

For a complete list of dependencies, see `requirements.txt`.

## Features
- Web interface using Flask
- Integration with Google AI services
- YouTube transcript functionality
- Static file handling (CSS/JS)
- Template-based views using Jinja2
# Magic-transcript
