import json
import logging
from flask import Flask, jsonify, request
from dotenv import load_dotenv
from openai import AzureOpenAI
import instructor
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
from flask_cors import CORS  # Import CORS

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
CORS(app)  # Enable CORS for all routes



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

class CypherVisualizationQuery(BaseModel):
    """Model for extracting and enhancing Cypher queries for visualization"""
    query: str = Field(..., description="The cleaned and corrected Cypher query for visualization")
    is_valid: bool = Field(..., description="Whether this is a valid query for visualization")
    visualization_notes: Optional[str] = Field(None, description="Notes about how this query will be visualized")
    
    @classmethod
    def extract_from_response(cls, response_text: str, schema_context: Optional[dict] = None):
        """
        Extract a visualization-ready Cypher query from an assistant response
        
        Args:
            response_text: The full text response from the assistant
            schema_context: Optional schema information to help with query validation
            
        Returns:
            CypherVisualizationQuery or None if no valid query could be extracted
        """
        try:
            logger.info("Extracting Cypher visualization query using instructor")
            
            # Initialize OpenAI client
            client = AzureOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                api_version=os.getenv("OPENAI_API_VERSION"),
                azure_endpoint=os.getenv("OPENAI_API_BASE"),
            )
            
            # Wrap with instructor
            instructor_client = instructor.from_openai(client)
            
            # Create system prompt
            system_prompt = """
            You are a Cypher query extraction and enhancement expert for Neo4j graph visualizations.
            
            Your task is to:
            1. Extract any Cypher query from the text
            2. Ensure the query is valid and visualization-friendly
            3. Enhance the query if needed to make it suitable for graph visualization
            
            For visualization, the query should:
            - Return complete node objects, not just properties
            - Include relationships when possible
            - Not be too complex (limit large result sets)
            - Use proper Neo4j syntax
            """
            
            # Add schema context if available
            if schema_context:
                # Extract relevant parts from schema
                node_labels = []
                if 'nodeLabels' in schema_context:
                    node_labels = [label_info.get('label') for label_info in schema_context.get('nodeLabels', [])]
                
                relationship_types = []
                if 'relationshipTypes' in schema_context:
                    relationship_types = [rel_info.get('relationshipType') for rel_info in schema_context.get('relationshipTypes', [])]
                
                system_prompt += f"""
                
                Available node labels: {', '.join(node_labels)}
                Available relationship types: {', '.join(relationship_types)}
                
                A good visualization query should include both nodes and relationships, like:
                
                MATCH (n:{node_labels[0] if node_labels else 'SomeLabel'})-[r]->(m)
                RETURN n, r, m LIMIT 25
                """
            
            # Create user prompt
            user_prompt = f"""
            Extract and enhance a Cypher query from the following text for graph visualization:
            
            {response_text}
            
            If no valid Cypher query is present, create a simple MATCH query that will visualize some meaningful part of the graph based on the context.
            """
            
            # Get structured response
            result = instructor_client.chat.completions.create(
                model=os.getenv("OPENAI_ASSISTANT_MODEL"),
                response_model=cls,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
            )
            
            logger.info(f"Extracted visualization query: {result.query}")
            logger.info(f"Query valid for visualization: {result.is_valid}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting Cypher query using instructor: {str(e)}")
            return None

# Routes
@app.route('/api/examples', methods=['GET'])
def get_examples():
    """Get example questions"""
    examples = [
        "Quels sont les capteurs présents à l'école maternelle?",
        "Quelle est la température actuelle dans la mairie?",
        "Montre-moi la consommation d'énergie de tous les bâtiments",
        "Quelles sont les relations entre les capteurs et les bâtiments?",
        "Quelle est la production d'énergie solaire actuelle?"
    ]
    return jsonify(examples)

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages and interact with the assistant"""
    data = request.json
    user_message = data.get('message', '')
    thread_id = data.get('thread_id')
    
    logger.info("=== CHAT REQUEST DEBUG ===")
    logger.info(f"Received message: '{user_message}'")
    logger.info(f"Thread ID: {thread_id}")
    
    # If no thread ID provided, create a new thread
    if not thread_id:
        thread_id = assistant_service.create_thread()
        logger.info(f"Created new thread: {thread_id}")
    
    # Get schema with query context before sending to assistant
    logger.info("Getting schema with query context")
    schema = neo4j_service.get_schema(user_message)
    logger.info(f"Schema retrieved with {len(schema.get('nodeLabels', []))} node labels and {len(schema.get('patterns', []))} patterns")
    
    # Send message to assistant with schema context
    logger.info("Sending message to assistant with schema context")
    response, run = assistant_service.send_message(thread_id, user_message, schema)
    logger.info(f"Received response ({len(response)} chars)")
    
    # Extract Cypher query from response using intelligent extraction
    logger.info("Extracting Cypher query using intelligent extraction")
    cypher_query = None
    
    try:
        # Use the new intelligent extraction
        query_result = CypherVisualizationQuery.extract_from_response(response, schema)
        
        if query_result and query_result.is_valid:
            cypher_query = query_result.query
            logger.info(f"Successfully extracted visualization query: {cypher_query}")
            
            # Add visualization notes to the response if available
            if query_result.visualization_notes:
                logger.info(f"Visualization notes: {query_result.visualization_notes}")
        else:
            logger.warning("No valid visualization query could be extracted using intelligent extraction")
    except Exception as e:
        logger.error(f"Error during intelligent query extraction: {str(e)}")
    
    # Legacy fallback if intelligent extraction fails
    if not cypher_query:
        logger.info("Falling back to legacy extraction methods")
        # Try to extract with instructor if intelligent extraction failed
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
                logger.info(f"Extracted query with fallback instructor: {cypher_query}")
            else:
                logger.info("No query could be extracted with fallback method")
                
        except Exception as e:
            logger.error(f"Error using fallback instructor to extract query: {str(e)}")
    
    # Prepare the response
    result = {
        'response': response,
        'thread_id': thread_id,
        'cypher_query': cypher_query
    }
    
    logger.info(f"Sending response with cypher_query: {cypher_query is not None}")
    logger.info("=== CHAT REQUEST COMPLETE ===")
    
    return jsonify(result)

@app.route('/api/speech-token', methods=['GET'])
def get_speech_token():
    """Get the Azure Speech service token for the frontend"""
    token_data = speech_service.get_token_for_frontend()
    return jsonify(token_data)

@app.route('/api/neo4j/schema', methods=['GET'])
def get_schema():
    """Get the Neo4j database schema with optional query relevance"""
    # Extract query parameter if provided
    query = request.args.get('query', '')
    
    # Log the request
    logger.info(f"Getting schema with query: '{query}'")
    
    # Get schema with the query for relevance
    schema = neo4j_service.get_schema(query)
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
    app.run(debug=True, host='0.0.0.0', port=5000)