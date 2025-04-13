# Badevel Living Lab Assistant - Flask Version

A beautiful Flask-based chatbot interface for exploring the smart village data of Badevel through a Neo4j graph database. This application includes speech recognition capabilities and interactive graph visualization using neovis.js.

## Features

- 🔍 Explore data from the digital twin of the village
- 💬 Ask questions in French or English about the village infrastructure
- 🎙️ Speech recognition powered by Azure Speech Services
- 📊 Interactive graph visualization with neovis.js
- 📱 View real-time sensor measurements
- 🏢 Learn about buildings and their equipment

## Project Structure

```
badevel-assistant/
├── app.py                  # Main Flask application
├── templates/              # Jinja templates
│   ├── index.html          # Main page
│   └── layout.html         # Base layout template
├── static/                 # Static files
│   ├── css/                # CSS files
│   │   └── style.css       # Main stylesheet
│   └── js/                 # JavaScript files
│       ├── chat.js         # Chat functionality
│       ├── speech.js       # Speech recognition
│       └── graph.js        # neovis.js visualization
├── services/               # Backend services
│   ├── neo4j_service.py    # Neo4j service
│   ├── assistant_service.py # OpenAI Assistant service
│   └── speech_service.py   # Azure Speech service
└── requirements.txt        # Dependencies
```

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/badevel-assistant.git
cd badevel-assistant
```

### 2. Set Up Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Variables

Create a `.env` file based on the `.env.example` template:

```bash
cp .env.example .env
```

Then edit the `.env` file to add your API keys and configuration.

### 4. Create the Azure OpenAI Assistant

If you haven't already created the assistant, follow the instructions in the original repository to create it:

```bash
python create_assistant.py
```

Make sure to copy the generated Assistant ID to your `.env` file.

### 5. Run the Application

```bash
flask run
```

The application will be available at `http://localhost:5000`.

For production deployment, use a WSGI server like Gunicorn:

```bash
gunicorn app:app
```

## Usage

1. Visit the web interface at `http://localhost:5000`.
2. Type your questions about the Badevel smart village in the text input field or click the microphone button to use speech recognition.
3. Click "Send" to submit your question.
4. View the assistant's response in the chat area.
5. If the response includes data that can be visualized as a graph, it will automatically appear in the visualization area.
6. Use the example questions in the suggestion area for ideas on what to ask.

## API Endpoints

The Flask application provides several API endpoints:

- `POST /api/chat`: Send a message to the assistant
- `GET /api/speech-token`: Get an Azure Speech token for frontend use
- `GET /api/neo4j/schema`: Get the Neo4j database schema
- `POST /api/neo4j/query`: Run a Cypher query against the Neo4j database

## Technologies Used

- **Flask**: Web framework for the backend
- **Azure OpenAI**: For the conversational AI assistant
- **Neo4j**: Graph database for storing the digital twin data
- **neovis.js**: JavaScript library for Neo4j visualization
- **Azure Speech Services**: For speech recognition
- **Bootstrap**: For responsive frontend design

## Notes for Developers

- The assistant automatically extracts Cypher queries from responses to visualize them using neovis.js.
- If the automatic extraction fails, the application uses instructor to attempt a second extraction.
- All communication with the Neo4j database is handled via the backend for security.
- The speech recognition uses Azure Speech Services for high accuracy in both French and English.

## Troubleshooting

- If you encounter CORS issues during development, make sure you're running both the frontend and backend on the same origin.
- If the visualization doesn't appear, check the browser console for errors and ensure your Neo4j credentials are correct.
- For speech recognition issues, verify that your microphone is properly connected and that you've granted the necessary browser permissions.
