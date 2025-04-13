"""
Service for handling interactions with the Azure OpenAI Assistant.
"""
import os
import time
import json
import logging
from typing import Dict, Any, Tuple, Optional, List
from openai import AzureOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field
# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AssistantService:
    """Service for interacting with Azure OpenAI Assistant"""
    
    def __init__(self, client: AzureOpenAI = None):
        """Initialize the AssistantService with an OpenAI client"""
        if client:
            self.client = client
        else:
            self.client = AzureOpenAI(
                azure_endpoint=os.getenv("OPENAI_API_BASE"),
                api_key=os.getenv("OPENAI_API_KEY"),
                api_version=os.getenv("OPENAI_API_VERSION"),
            )
        
        self.assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
        self.assistant = self._load_assistant()
        
    def _load_assistant(self):
        """Load the OpenAI Assistant"""
        try:
            logger.info(f"Loading assistant with ID: {self.assistant_id}")
            assistant = self.client.beta.assistants.retrieve(self.assistant_id)
            logger.info(f"Assistant loaded successfully: {assistant.name} (model: {assistant.model})")
            
            # Log available tools for debugging
            tools = [tool.type if isinstance(tool, dict) else tool.type for tool in assistant.tools]
            logger.info(f"Assistant tools: {', '.join(tools)}")
            
            return assistant
        except Exception as e:
            logger.error(f"Error loading assistant: {str(e)}")
            raise
            
    def create_thread(self) -> str:
        """Create a new thread for the conversation"""
        try:
            logger.info("Creating new conversation thread")
            thread = self.client.beta.threads.create()
            logger.info(f"Created thread with ID: {thread.id}")
            return thread.id
        except Exception as e:
            logger.error(f"Error creating thread: {str(e)}")
            raise
            
    def send_message(self, thread_id: str, message: str, schema: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Send a message to the assistant and get a response
        
        Args:
            thread_id: The ID of the thread
            message: The user's message
            schema: Optional schema context with relevant relations for the query
            
        Returns:
            Tuple containing the assistant's response text and the run object
        """
        try:
            logger.info(f"Processing user message on thread: {thread_id}")
            logger.info(f"User message: {message[:50]}{'...' if len(message) > 50 else ''}")
            
            # Add the user message to the thread
            logger.info("Adding user message to thread")
            message_obj = self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )
            logger.info(f"Added message with ID: {message_obj.id}")
            
            # Prepare run parameters
            run_params = {
                "thread_id": thread_id,
                "assistant_id": self.assistant_id
            }
            
            # If schema with relevant relations is provided, add it as additional instructions
            if schema and 'relations_info' in schema:
                additional_instructions = f"""
                The user is asking about the Neo4j graph database. Here is some context that may help you answer their query:
                
                {schema['relations_info']}
                
                Please use this information to help answer their question and formulate Cypher queries if needed.
                """
                run_params["additional_instructions"] = additional_instructions
                logger.info("Added schema context to run with additional instructions")
            
            # Create a run to process the thread
            logger.info(f"Creating run with assistant ID: {self.assistant_id}")
            run = self.client.beta.threads.runs.create(**run_params)
            logger.info(f"Created run with ID: {run.id}, initial status: {run.status}")
            
            # Poll the run status until it's complete
            logger.info("Polling run status until complete")
            while run.status in ["queued", "in_progress"]:
                time.sleep(0.5)
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
                logger.info(f"Run status: {run.status}")
                
            # Handle tool calls if needed
            if run.status == "requires_action":
                logger.info("Run requires action - processing tool calls")
                run = self._process_tool_calls(thread_id, run)
                logger.info(f"After tool calls, run status: {run.status}")
            elif run.status == "completed":
                logger.info("Run completed without requiring tool calls")
            else:
                logger.warning(f"Run ended with unexpected status: {run.status}")
                
            # Get the assistant's response
            logger.info("Retrieving assistant's responses")
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id
            )
            logger.info(f"Retrieved {len(messages.data)} messages")
            
            # Find the most recent assistant message
            assistant_message = None
            for message in messages.data:
                if message.role == "assistant" and message.created_at > run.created_at:
                    logger.info(f"Found assistant message with ID: {message.id}")
                    # Extract the text content
                    content = "".join(part.text.value for part in message.content if part.type == "text")
                    assistant_message = content
                    logger.info(f"Assistant response: {content[:50]}{'...' if len(content) > 50 else ''}")
                    return content, run
            
            # If no message found, return an error
            logger.warning("No assistant message found after run completion")
            return "Sorry, I couldn't process your request.", run
            
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return f"Error: {str(e)}", {}

    def _process_tool_calls(self, thread_id: str, run: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process tool calls requested by the assistant
        
        Args:
            thread_id: The ID of the thread
            run: The run object
            
        Returns:
            Updated run object
        """
        logger.info("=== PROCESSING TOOL CALLS ===")
        
        # Get the tool calls
        tool_calls = run.required_action.submit_tool_outputs.tool_calls
        logger.info(f"Found {len(tool_calls)} tool calls to process")
        tool_outputs = []
        
        for i, tool_call in enumerate(tool_calls):
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            logger.info(f"Processing tool call {i+1}/{len(tool_calls)}: {function_name}")
            logger.info(f"Arguments: {json.dumps(function_args)}")
            
            # Process based on function name
            # This is where you'd integrate with the Neo4j service
            if function_name == "neo4j_get_schema":
                logger.info("Calling Neo4j service: get_schema()")
                from services.neo4j_service import Neo4jService
                neo4j_service = Neo4jService()
                result = neo4j_service.get_schema()
                logger.info(f"Schema retrieved with {len(result.get('nodeLabels', []))} node labels and {len(result.get('relationshipTypes', []))} relationship types")
                output = json.dumps(result)
                
            elif function_name == "neo4j_run_query":
                query = function_args.get("query")
                logger.info(f"Calling Neo4j service: run_cypher_query()")
                logger.info(f"Query: {query}")
                from services.neo4j_service import Neo4jService
                neo4j_service = Neo4jService()
                result = neo4j_service.run_cypher_query(query)
                result_count = len(result.get("results", [])) if result.get("status") == "success" else 0
                logger.info(f"Query execution status: {result.get('status')}, returned {result_count} results")
                output = json.dumps(result)
                
            elif function_name == "neo4j_get_node_info":
                node_id = function_args.get("node_id")
                logger.info(f"Calling Neo4j service: get_node_info(node_id={node_id})")
                from services.neo4j_service import Neo4jService
                neo4j_service = Neo4jService()
                result = neo4j_service.get_node_info(node_id)
                logger.info(f"Node info status: {result.get('status')}")
                output = json.dumps(result)
                
            elif function_name == "neo4j_find_relationships":
                node_id = function_args.get("node_id")
                logger.info(f"Calling Neo4j service: find_relationships(node_id={node_id})")
                from services.neo4j_service import Neo4jService
                neo4j_service = Neo4jService()
                result = neo4j_service.find_relationships(node_id)
                logger.info(f"Relationships status: {result.get('status')}, found {len(result.get('results', []))} relationships")
                output = json.dumps(result)
                
            elif function_name == "neo4j_find_sensor_readings":
                logger.info("Calling Neo4j service: find_sensor_readings()")
                from services.neo4j_service import Neo4jService
                neo4j_service = Neo4jService()
                result = neo4j_service.find_sensor_readings()
                logger.info(f"Sensor readings status: {result.get('status')}, found {len(result.get('results', []))} readings")
                output = json.dumps(result)
                
            elif function_name == "neo4j_count_nodes_by_type":
                logger.info("Calling Neo4j service: count_nodes_by_type()")
                from services.neo4j_service import Neo4jService
                neo4j_service = Neo4jService()
                result = neo4j_service.count_nodes_by_type()
                logger.info(f"Node count status: {result.get('status')}")
                output = json.dumps(result)
                
            elif function_name == "neo4j_get_node_properties":
                node_label = function_args.get("node_label")
                logger.info(f"Calling Neo4j service: get_node_properties(node_label={node_label})")
                from services.neo4j_service import Neo4jService
                neo4j_service = Neo4jService()
                result = neo4j_service.get_node_properties(node_label)
                logger.info(f"Node properties status: {result.get('status')}")
                output = json.dumps(result)
                
            elif function_name == "neo4j_find_nodes_by_type":
                node_type = function_args.get("node_type")
                logger.info(f"Calling Neo4j service: find_nodes_by_type(node_type={node_type})")
                from services.neo4j_service import Neo4jService
                neo4j_service = Neo4jService()
                result = neo4j_service.find_nodes_by_type(node_type)
                logger.info(f"Find nodes status: {result.get('status')}, found {len(result.get('results', []))} nodes")
                output = json.dumps(result)
                
            elif function_name == "neo4j_find_path_between_nodes":
                start_id = function_args.get("start_id")
                end_id = function_args.get("end_id")
                logger.info(f"Calling Neo4j service: find_path_between_nodes(start_id={start_id}, end_id={end_id})")
                from services.neo4j_service import Neo4jService
                neo4j_service = Neo4jService()
                result = neo4j_service.find_path_between_nodes(start_id, end_id)
                logger.info(f"Path finding status: {result.get('status')}")
                output = json.dumps(result)
                
            # Add more function handlers as needed
            else:
                logger.warning(f"Function not implemented: {function_name}")
                output = json.dumps({"status": "error", "message": f"Function {function_name} not implemented"})
                
            logger.info(f"Adding tool output for call {i+1}, output length: {len(output)} chars")
            tool_outputs.append({
                "tool_call_id": tool_call.id,
                "output": output
            })
        
        # Submit the tool outputs
        logger.info(f"Submitting {len(tool_outputs)} tool outputs")
        run = self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run.id,
            tool_outputs=tool_outputs
        )
        logger.info(f"Tool outputs submitted, new run status: {run.status}")
        
        # Poll until the run is complete
        logger.info("Polling run status until complete")
        poll_count = 0
        while run.status in ["queued", "in_progress"]:
            time.sleep(0.5)
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            poll_count += 1
            if poll_count % 10 == 0:  # Log every 5 seconds
                logger.info(f"Still polling run status: {run.status}")
            
        logger.info(f"Run status after tool processing: {run.status}")
            
        # Handle nested tool calls if needed
        if run.status == "requires_action":
            logger.info("Found nested tool calls, processing recursively")
            run = self._process_tool_calls(thread_id, run)
            
        logger.info("=== TOOL CALL PROCESSING COMPLETE ===")
        return run