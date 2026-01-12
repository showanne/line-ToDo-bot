# GEMINI.md

## Project Overview

This project is a LINE To-Do Bot, a chatbot for the LINE messaging platform that helps users manage their to-do lists. It is built with Python and the Flask web framework. The bot allows users to add, list, edit, and delete to-do items through chat commands. Each user's to-do list is kept separate. The application uses an SQLite database to store the data. For development, it uses `ngrok` to expose the local Flask server to the internet to receive webhooks from the LINE platform.

### Main Technologies

- **Backend:** Python, Flask
- **Database:** SQLite
- **LINE Integration:** line-bot-sdk-python
- **Development Tunneling:** pyngrok

## Building and Running

### 1. Set up the Environment

First, create a virtual environment and install the required dependencies.

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows
venv\\Scripts\\activate
# On macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the `.env.sample` file to a new file named `.env` and fill in the required credentials.

```bash
cp .env.sample .env
```

You will need to add your LINE Channel Access Token, LINE Channel Secret, and your ngrok Authtoken to the `.env` file.

```
LINE_CHANNEL_ACCESS_TOKEN="YOUR_LINE_CHANNEL_ACCESS_TOKEN"
LINE_CHANNEL_SECRET="YOUR_LINE_CHANNEL_SECRET"
NGROK_AUTHTOKEN="YOUR_NGROK_AUTHTOKEN"
```

### 3. Run the Application

Start the Flask application with the following command:

```bash
python app.py
```

The application will start, and `ngrok` will create a public URL for your local server. You need to configure this URL in your LINE Developer Console's webhook settings. The URL will be printed in the console when you start the application.

## Development Conventions

- **State Management:** The application uses a simple in-memory dictionary (`user_states`) to manage the conversation state for multi-step commands like "add" or "edit".
- **Database:** The database is initialized and managed directly within `app.py`. The schema is created if the database file does not exist. All database operations are handled by helper functions within the same file.
- **Commands:** User commands are handled in the main `/callback` webhook endpoint. The code checks for specific keywords and command patterns to trigger different actions. Simple commands are handled directly, while more complex, multi-step commands use the state management dictionary.
- **Dependencies:** Project dependencies are listed in `requirements.txt`.

## AI Behavior Guidelines

To ensure efficiency and system safety, GEMINI must follow these rules:

### 1. File Operations

- **Allow File Creation**: When the project needs new modules, extensions, or test scripts, you are encouraged to generate the content and suggest creating new files.
- **Code Updates**: You may provide modification suggestions or full code snippets for existing files.

### 2. Installation & System Changes

- **Prompt Only**: When new Python packages need to be installed (e.g., `pip install`) or system-level changes are required, **DO NOT** attempt to execute them. Instead, clearly prompt the user with the necessary commands.
- **Dependency Management**: Remind the user to manually update `requirements.txt` if new packages are introduced.

### 3. Security

- **Credential Protection**: Never include real API keys or secrets in generated files. Always direct the user to use the `.env` file.
