# Badevel Living Lab Assistant - Flask Version

## Project Structure
```
badevel-assistant/
├── app.py                  # Main Flask application
├── templates/              # Jinja templates
│   ├── index.html          # Main page
│   ├── layout.html         # Base layout template
│   └── components/         # Reusable components
│       └── chat.html       # Chat component
├── static/                 # Static files
│   ├── css/                # CSS files
│   │   └── style.css       # Main stylesheet
│   ├── js/                 # JavaScript files
│   │   ├── chat.js         # Chat functionality
│   │   ├── speech.js       # Speech recognition
│   │   └── graph.js        # neovis.js visualization
├── services/               # Backend services
│   ├── neo4j_service.py    # Neo4j service  
│   ├── assistant_service.py # OpenAI Assistant service
│   └── speech_service.py   # Azure Speech service
└── requirements.txt        # Dependencies
```

## Implementation Steps:
1. Set up Flask application with routes
2. Create beautiful UI with Jinja templates
3. Implement backend services for Assistant, Neo4j, and Azure Speech
4. Add frontend JavaScript for chat, speech recognition, and graph visualization
5. Connect everything through API endpoints
