# Browser Use API

A robust, self-healing browser automation service built with FastAPI, featuring CDP-based Chrome management, automatic restart capabilities, and pre-authenticated profiles.

## Features

- **FastAPI-based REST API** - Modern async web framework
- **Chrome DevTools Protocol (CDP)** - Direct browser control
- **Pre-Authenticated Profiles** - No Google verification prompts
- **Automatic Restart** - Self-healing browser instances
- **Task Queue Management** - Async task processing
- **Firestore Integration** - Persistent task storage
- **Multi-Agent Support** - Concurrent browser operations
- **Chrome Profile Manager** - Pre-launched Chrome instances with authentication
- **Headless Mode Support** - Production-ready deployment
- **Authentication Persistence** - Maintains Google login sessions

## Prerequisites

- Python 3.8+
- Google Chrome browser
- Firebase project with Firestore enabled
- Google account for authentication

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd browser-use-api
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
```

5. Fill in your actual values in the `.env` file (see Environment Variables section below)

## Environment Variables

Copy `.env.example` to `.env` and fill in the following variables:

### Browser Configuration
- `NUM_BROWSER_WORKERS` - Number of concurrent browser workers (default: 2)
- `CLONED_PROFILES_BASE_DIR` - Base directory for Chrome profiles (default: ~/.config/browseruse/profiles)
- `HEADLESS_MODE` - Run browsers in headless mode (default: true)

### Chrome Configuration
- `BROWSER_PROFILES_DIR` - Directory for browser profiles
- `CHROME_EXECUTABLE` - Path to Chrome executable (default: /usr/bin/google-chrome)
- `CHROME_START_PORT` - Starting port for Chrome instances
- `CHROME_NUM_PROFILES` - Number of Chrome profiles to create
- `CHROME_HEADLESS` - Run Chrome in headless mode

### Firebase Configuration
- `FIREBASE_SERVICE_ACCOUNT_PATH` - Path to Firebase service account JSON file
- `FIREBASE_PROJECT_ID` - Your Firebase project ID

### API Configuration
- `API_BASE_URL` - Base URL for the API (default: http://localhost:8000)

### Test Configuration
- `SUCCESS_TEST_CASES_PATH` - Path to success test cases
- `FAILURE_TEST_CASES_PATH` - Path to failure test cases
- `RAW_SUCCESS_TEST_RESULTS_PATH` - Path for raw success results
- `RAW_FAILURE_TEST_RESULTS_PATH` - Path for raw failure results
- `EVALUATED_SUCCESS_TEST_RESULTS_PATH` - Path for evaluated success results
- `EVALUATED_FAILURE_TEST_RESULTS_PATH` - Path for evaluated failure results

### Display Configuration
- `DISPLAY` - Display for headless mode (default: :99)

## Setup

### 1. Firebase Setup

1. Create a Firebase project at [Firebase Console](https://console.firebase.google.com/)
2. Enable Firestore Database
3. Generate a service account key:
   - Go to Project Settings > Service Accounts
   - Click "Generate new private key"
   - Save the JSON file as `firebase-service-account.json`
4. Set the `FIREBASE_SERVICE_ACCOUNT_PATH` environment variable to point to this file

### 2. Chrome Profile Setup

1. Create and authenticate Chrome profiles:
```bash
python create_profiles.py
```

2. Launch Chrome profiles:
```bash
python launch_chrome_profiles.py
```

### 3. Start the API Server

```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Task Management

- `POST /api/v1/tasks` - Create a new browser automation task
- `GET /api/v1/tasks/{task_id}` - Get task status and results
- `GET /api/v1/tasks` - List all tasks

### Health Check

- `GET /health` - Check API health status

## Usage Example

```python
import requests

# Create a new task
task_data = {
    "instruction": "Navigate to Google and search for 'browser automation'",
    "url": "https://www.google.com"
}

response = requests.post("http://localhost:8000/api/v1/tasks", json=task_data)
task_id = response.json()["task_id"]

# Check task status
status_response = requests.get(f"http://localhost:8000/api/v1/tasks/{task_id}")
print(status_response.json())
```

## Project Structure

```
browser-use-api/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── services/             # Core services
│   ├── task_service.py   # Task management service
│   ├── browser_agent.py  # Browser automation agent
│   └── firestore_service.py # Firestore integration
├── models/               # Data models
│   └── task.py          # Task data models
├── routes/               # API routes
│   └── task_routes.py   # Task-related endpoints
├── test/                 # Test files and data
└── scripts/              # Utility scripts
    ├── create_profiles.py
    └── launch_chrome_profiles.py
```

## Development

### Running Tests

```bash
python -m pytest test/
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## Deployment

### Docker

```bash
docker build -t browser-use-api .
docker run -p 8000:8000 --env-file .env browser-use-api
```

### Production Considerations

1. **Authentication issues:**
   - Ensure Chrome profiles are properly authenticated
   - Monitor for Google verification prompts

2. **Profile management:**
   - Regularly clean up old profiles
   - Monitor disk usage for profile storage

3. **Resource management:**
   - Adjust `NUM_BROWSER_WORKERS` based on server capacity
   - Monitor memory usage for Chrome instances

## Troubleshooting

### Common Issues

1. **Chrome not starting:**
   - Check Chrome executable path
   - Ensure display is available for headless mode
   - Verify Chrome version compatibility

2. **Authentication failures:**
   - Recreate profiles with fresh authentication
   - Check Google account permissions

3. **Firestore connection issues:**
   - Verify service account file path
   - Check Firebase project configuration
   - Ensure Firestore is enabled

### Logs

Check application logs for detailed error information:
```bash
tail -f logs/app.log
```

## Security Notes

- Never commit your `.env` file to version control
- Keep your Firebase service account file secure
- Use environment variables for all sensitive configuration
- The `.gitignore` file is configured to exclude sensitive files

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]