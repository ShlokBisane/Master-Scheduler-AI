# Master-Scheduler-AI

An intelligent chatbot application with a Python backend and interactive web frontend, featuring stress tracking, task management, and calendar integration.

## Project Structure

```
Master-Scheduler-AI/
├── backend/
│   ├── ai_engine.py          # Core AI/NLP engine
│   ├── database.py           # Database operations and models
│   ├── main.py               # Backend server entry point
│   ├── prompts.py            # AI prompt templates and management
│   ├── ranking_engine.py     # Response ranking and prioritization
│   ├── scheduler.py          # Task scheduling and reminders
│   └── requirements.txt      # Python dependencies
└── frontend/
    ├── index.html            # Main HTML template
    └── assets/
        ├── css/
        │   └── style.css     # Application styling
        └── js/
            ├── app.js        # Main application logic
            ├── api.js        # API communication layer
            ├── chat.js       # Chat functionality
            ├── calendar.js   # Calendar integration
            ├── profile.js    # User profile management
            ├── stress.js     # Stress tracking
            ├── todo.js       # Todo/Task management
            └── voice.js      # Voice interaction features
```

## Features

- 💬 **Intelligent Chat Interface** - AI-powered conversational engine
- 📅 **Calendar Integration** - Schedule and manage events
- ✅ **Task Management** - Create and track todo items
- 😌 **Stress Tracking** - Monitor and manage stress levels
- 🎤 **Voice Support** - Voice-based interactions
- 👤 **User Profiles** - Personalized user accounts
- 📊 **Ranking Engine** - Intelligent response prioritization

## Installation

### Prerequisites
- Python 3.8+
- Node.js/npm (optional, for local development)
- Git

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables (if needed):
```bash
# Create a .env file with your configuration
```

### Frontend Setup

No build process required - the frontend is static HTML/CSS/JS. Simply open `frontend/index.html` in a web browser or serve it using a local server.

## Running the Application

### Start the Backend Server

```bash
cd backend
python main.py
```

The backend server will typically run on `http://localhost:5000` or `http://localhost:8000` (check main.py for the exact port).

### Serve the Frontend

Option 1 - Simple HTTP Server:
```bash
cd frontend
python -m http.server 8080
```

Then open `http://localhost:8080` in your browser.

Option 2 - Direct File:
Open `frontend/index.html` directly in your web browser (may have CORS limitations).

## API Endpoints

The frontend communicates with the backend through API calls defined in `frontend/assets/js/api.js`. Key endpoints typically include:
- Chat messages
- User profiles
- Tasks/Todos
- Calendar events
- Stress tracking data

## Key Files

| File | Purpose |
|------|---------|
| `ai_engine.py` | Core AI processing and NLP logic |
| `database.py` | Data persistence and models |
| `main.py` | Flask/FastAPI server configuration |
| `prompts.py` | AI prompt engineering templates |
| `ranking_engine.py` | Response quality ranking |
| `scheduler.py` | Scheduled tasks and reminders |
| `app.js` | Frontend application state management |
| `api.js` | Backend communication |

## Development

### Backend Development
- Modify AI logic in `ai_engine.py`
- Update prompts in `prompts.py`
- Adjust server configuration in `main.py`

### Frontend Development
- Edit `frontend/assets/css/style.css` for styling
- Modify individual feature files (chat.js, calendar.js, etc.)
- Update API calls in `api.js` if backend endpoints change

## Dependencies

See `backend/requirements.txt` for Python dependencies. Common packages may include:
- Flask/FastAPI (web framework)
- SQLAlchemy (database ORM)
- NLTK/spaCy (NLP)
- Requests (HTTP client)

## Troubleshooting

- **CORS errors**: Ensure frontend and backend servers are properly configured
- **Database errors**: Check database.py configuration and ensure DB is initialized
- **API not responding**: Verify backend server is running on the correct port

## Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request


## Support

For issues or questions, please open an issue in the repository.
