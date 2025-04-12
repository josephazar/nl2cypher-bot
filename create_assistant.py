import os
import asyncio
from openai import AsyncAzureOpenAI
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Azure OpenAI client
client = AsyncAzureOpenAI(
    azure_endpoint=os.getenv("OPENAI_API_BASE"),
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION"),
)

async def create_assistant():
    """Create an OpenAI Assistant with Neo4j integration capabilities"""
    
    instructions = """
    You are the Badevel Living Lab Assistant, a smart expert supporting users in exploring the smart village project in Badevel, France. The project uses a Neo4j graph database to store data about IoT devices, infrastructure, and digital systems in the village.

    ---

    🧠 Your responsibilities:
    - Help users explore and understand the structure and data within the Neo4j database
    - Retrieve live data by using function calls
    - Present data using tables or visuals when helpful
    - Always respond in the user's language (English or French)
    - Explain technical topics clearly and simply

    ---

    📌 IMPORTANT: When starting a conversation with a new user, **always begin by calling `neo4j_get_schema()`** to understand the graph's structure: node labels, relationships, and properties. This allows you to generate meaningful and context-aware answers.

    ---

    🗂️ The database includes these node types (labels):
    - `Application`
    - `Department`
    - `Manufacturer`
    - `Module`
    - `Network`
    - `Power`
    - `Sensor`
    - `Thing`
    - `ThingType`
    - `Vendor`
    - `Location`

    Each node has an `id` and a `name`, and many have extra properties like `entType`, `unit`, `lat`, `lon`, `latest_value`, or `description`.

    Relationships between nodes are dynamically created using data from a CSV, and may include custom properties.

    ---

    🛠️ You have access to these tools (functions):

    1. `neo4j_get_schema()` – Get the full graph schema (labels, relationships, and properties)
    2. `neo4j_run_query(query)` – Run a Cypher query and return the results
    3. `neo4j_get_node_info(node_id)` – Retrieve all details about a specific node
    4. `neo4j_find_relationships(node_id)` – Return all relationships for a node
    5. `neo4j_find_sensor_readings()` – Get all sensors and their latest readings
    6. `neo4j_count_nodes_by_type()` – Count how many nodes exist for each type
    7. `neo4j_get_node_properties(node_label)` – Show the property keys used by nodes of a specific label
    8. `neo4j_find_nodes_by_type(node_type)` – List all nodes that match a given type
    9. `neo4j_find_path_between_nodes(start_id, end_id)` – Find the shortest path between two nodes
    10. `code_interpreter` – Analyze, summarize, or visualize data using Python code

    ---

    📊 Example Cypher queries you can use:
    - `MATCH (t:Thing) WHERE t.latest_value IS NOT NULL RETURN t.id, t.name, t.latest_value`
    - `MATCH (s:Sensor) RETURN s`
    - `MATCH (n {id: 'Sensor01'})-[r]-(m) RETURN n, type(r) AS rel_type, r, m`
    - `MATCH (a:Application)-[r]->(m:Module) RETURN a.name, type(r), m.name`

    Be helpful, thoughtful, and always base your answers on real-time data from the graph.
    Your output should always be in French or English, depending on the user's language. If the question is in French, respond in French.
    """

    
    # Create the assistant with tools for Neo4j integration
    assistant = await client.beta.assistants.create(
        name="Badevel Living Lab Assistant",
        instructions=instructions,
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "neo4j_get_schema",
                    "description": "Get the complete schema of the Neo4j database (node labels, relationship types, and properties)",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "neo4j_run_query",
                    "description": "Run a Cypher query against the Neo4j database",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The Cypher query to execute"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "neo4j_get_node_info",
                    "description": "Get information about a specific node",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "node_id": {
                                "type": "string",
                                "description": "The ID of the node to look up"
                            }
                        },
                        "required": ["node_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "neo4j_find_relationships",
                    "description": "Find all relationships for a specific node",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "node_id": {
                                "type": "string",
                                "description": "The ID of the node to find relationships for"
                            }
                        },
                        "required": ["node_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "neo4j_find_sensor_readings",
                    "description": "Find all sensor readings",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "neo4j_count_nodes_by_type",
                    "description": "Count the number of nodes for each node label/type",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "neo4j_get_node_properties",
                    "description": "Get all property keys used by nodes with a specific label",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "node_label": {
                                "type": "string",
                                "description": "The label of the nodes to get properties for"
                            }
                        },
                        "required": ["node_label"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "neo4j_find_nodes_by_type",
                    "description": "Find all nodes of a specific type",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "node_type": {
                                "type": "string",
                                "description": "The type of nodes to find"
                            }
                        },
                        "required": ["node_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "neo4j_find_path_between_nodes",
                    "description": "Find a path between two nodes",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_id": {
                                "type": "string",
                                "description": "The ID of the starting node"
                            },
                            "end_id": {
                                "type": "string",
                                "description": "The ID of the ending node"
                            }
                        },
                        "required": ["start_id", "end_id"]
                    }
                }
            },
            {"type": "code_interpreter"}
        ],
        model=os.getenv("OPENAI_ASSISTANT_MODEL"),
    )
    
    return assistant

if __name__ == "__main__":
    try:
        # Create the assistant
        loop = asyncio.get_event_loop()
        assistant = loop.run_until_complete(create_assistant())
        
        # Print the success message and assistant ID
        print(f"✅ Assistant created successfully with ID: {assistant.id}")
        print(f"📝 Name: {assistant.name}")
        print(f"ℹ️ Please add this ID to your .env file as OPENAI_ASSISTANT_ID")
        
        # If an output file was provided, save the ID to it
        if len(sys.argv) > 1:
            output_file = sys.argv[1]
            with open(output_file, "w") as f:
                f.write(assistant.id)
            print(f"📄 Assistant ID saved to {output_file}")
    
    except Exception as e:
        print(f"❌ Error creating assistant: {str(e)}")
        sys.exit(1)