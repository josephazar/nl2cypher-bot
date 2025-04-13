import json
import logging
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from openai import AzureOpenAI
import instructor
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os


from services.neo4j_service import Neo4jService
from services.assistant_service import AssistantService
from services.speech_service import SpeechService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Pydantic model for Cypher query extraction
class CypherQuery(BaseModel):
    query: str = Field(..., description="The Cypher query to visualize the graph")
    description: Optional[str] = Field(None, description="Description of what this query is showing")
    
    @classmethod
    def extract_from_text(cls, text: str) -> Optional['CypherQuery']:
        try:
            if "MATCH" in text and "RETURN" in text:
                lines = text.split("\n")
                query_lines = []
                in_query = False
                for line in lines:
                    if "MATCH" in line and not in_query:
                        in_query = True
                        query_lines.append(line)
                    elif in_query and any(keyword in line for keyword in ["RETURN", "WHERE", "WITH", "ORDER", "LIMIT"]):
                        query_lines.append(line)
                    elif in_query and not any(keyword in line for keyword in ["MATCH", "RETURN", "WHERE", "WITH", "ORDER", "LIMIT"]):
                        in_query = False
                if query_lines:
                    return cls(query=" ".join(query_lines).strip(), description="Automatically extracted query")
            return None
        except Exception as e:
            logger.error(f"Error extracting query: {str(e)}")
            return None

# Initialize the services
openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("OPENAI_API_BASE"),
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION"),
)
instructor_client = instructor.from_openai(openai_client)
assistant_service = AssistantService(openai_client)
neo4j_service = Neo4jService()
speech_service = SpeechService()

# Routes
@app.route('/')
def index():
    """Render the main page"""
    examples = [
        "Quels sont les capteurs présents à l'école maternelle?",
        "Quelle est la température actuelle dans la mairie?",
        "Montre-moi la consommation d'énergie de tous les bâtiments",
        "Quelles sont les relations entre les capteurs et les bâtiments?",
        "Quelle est la production d'énergie solaire actuelle?"
    ]
    
    # Try to get speech token, but gracefully handle errors
    try:
        speech_token = speech_service.get_token_for_frontend()
    except Exception as e:
        logger.warning(f"Speech services not available: {str(e)}")
        # Provide empty token info which will disable speech features on the frontend
        speech_token = {
            'token': '',
            'region': '',
            'language': 'fr-FR',
            'endpointId': '',
            'error': str(e)
        }
    
    return render_template('index.html', examples=examples, speech_token=speech_token)

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages and interact with the assistant"""
    data = request.json
    user_message = data.get('message', '')
    thread_id = data.get('thread_id')
    
    # If no thread ID provided, create a new thread
    if not thread_id:
        thread_id = assistant_service.create_thread()
    
    # Send message to assistant and get response
    response, run = assistant_service.send_message(thread_id, user_message)
    
    # Extract Cypher query from response
    cypher_query = None
    query_obj = CypherQuery.extract_from_text(response)
    
    if query_obj:
        cypher_query = query_obj.query
    else:
        # Try to extract with instructor if regular extraction failed
        try:
            class ExtractedCypherQuery(BaseModel):
                query: Optional[str] = Field(None, description="The extracted Cypher query if present in the text")
                
            system_prompt = """
            You are a Cypher query extraction expert. Extract any valid Cypher query from the text.
            A valid Cypher query typically contains MATCH and RETURN clauses.
            If there's no valid Cypher query, return null for the query field.
            """
            
            extraction_result = instructor_client.chat.completions.create(
                model=os.getenv("OPENAI_ASSISTANT_MODEL"),
                response_model=ExtractedCypherQuery,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": response}
                ],
                max_tokens=200,
            )
            
            if extraction_result.query:
                cypher_query = extraction_result.query
                
        except Exception as e:
            logger.error(f"Error using instructor to extract query: {str(e)}")
    
    # Return response with thread ID and extracted query
    return jsonify({
        'response': response,
        'thread_id': thread_id,
        'cypher_query': cypher_query
    })

@app.route('/static/speech-sdk-fallback.js')
def speech_sdk_fallback():
    """Provide a fallback method for speech SDK if the CDN fails"""
    return """
    // Fallback object to prevent errors if Microsoft Speech SDK fails to load
    window.Microsoft = window.Microsoft || {};
    Microsoft.CognitiveServices = Microsoft.CognitiveServices || {};
    Microsoft.CognitiveServices.Speech = Microsoft.CognitiveServices.Speech || {
        // Minimal implementation to prevent errors
        SpeechConfig: {
            fromAuthorizationToken: function() {
                console.warn('Using Speech SDK fallback implementation');
                return {};
            }
        },
        AudioConfig: {
            fromDefaultMicrophoneInput: function() {
                return {};
            }
        },
        SpeechRecognizer: function() {
            return {
                startContinuousRecognitionAsync: function(onSuccess, onError) {
                    onError(new Error('Speech SDK not properly loaded'));
                },
                stopContinuousRecognitionAsync: function(onSuccess) {
                    if (onSuccess) onSuccess();
                }
            };
        },
        ResultReason: {
            RecognizedSpeech: 'RecognizedSpeech'
        }
    };
    console.warn('Using Speech SDK fallback - speech recognition will not work.');
    """

@app.route('/api/speech-token', methods=['GET'])
def get_speech_token():
    """Get the Azure Speech service token for the frontend"""
    token_data = speech_service.get_token_for_frontend()
    return jsonify(token_data)

@app.route('/api/neo4j/schema', methods=['GET'])
def get_schema():
    """Get the Neo4j database schema"""
    schema = neo4j_service.get_schema()
    return jsonify(schema)

@app.route('/api/neo4j/query', methods=['POST'])
def run_query():
    """Run a Cypher query against the Neo4j database"""
    data = request.json
    query = data.get('query')
    if not query:
        return jsonify({"status": "error", "message": "No query provided"})
    
    result = neo4j_service.run_cypher_query(query)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)