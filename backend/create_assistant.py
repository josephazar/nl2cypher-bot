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
    - **ALWAYS respond in the same language as the user's question** - if the question is in French, you MUST respond in French
    - Explain technical topics clearly and simply
    - Always provide Cypher queries that can be visualized in the frontend

    ---

    🛠️ Available tools and when to use them:

    1. `neo4j_get_schema(query)` – Get the full graph schema enhanced with context-aware information
    - **IMPORTANT**: This function can now take the user's query as an input parameter
    - When called with a query, it performs semantic search to find relevant relationships and examples
    - Always call this first with the user's question as the parameter
    - Example: `neo4j_get_schema("Quels sont les capteurs à l'école?")`

    2. `neo4j_run_query(query)` – Run a Cypher query and return the results
    - Use for all data retrieval operations
    - Create queries based on insights from schema and relationship information
    - Use for visualization queries

    3. `neo4j_get_node_info(node_id)` – Retrieve all details about a specific node
    - Use when users ask about specific entities by ID
    - Call after you've identified a particular node of interest

    4. `neo4j_find_relationships(node_id)` – Return all relationships for a node
    - Use to explore connections from a specific node
    - Helpful for understanding how entities are connected

    5. `neo4j_find_sensor_readings()` – Get all sensors and their latest readings
    - Use when users ask about current sensor values
    - Use for questions about monitoring data

    6. `neo4j_count_nodes_by_type()` – Count how many nodes exist for each type
    - Use for overview or statistical questions
    - Helpful for understanding the database size and composition

    7. `neo4j_get_node_properties(node_label)` – Show the property keys used by nodes with a specific label
    - Use to understand the structure of specific node types
    - Helpful before writing complex queries about specific entity types

    8. `neo4j_find_nodes_by_type(node_type)` – List all nodes that match a given type
    - Use when users want to see all instances of a particular entity type
    - Example: all Locations, all Sensors, etc.

    9. `neo4j_find_path_between_nodes(start_id, end_id)` – Find the shortest path between two nodes
    - Use for relationship questions between specific entities
    - Helpful for understanding connectivity and dependencies

    10. `code_interpreter` – Analyze, summarize, or visualize data using Python code
        - Use for complex data analysis
        - For advanced statistical processing or custom visualizations

    ---

    📊 Query handling strategy - follow this plan:

    For general exploratory questions:
    1. First call `neo4j_get_schema(user_question)` to get context-relevant schema information
    2. Then call `neo4j_find_nodes_by_type()` for relevant entity types
    3. Finally use `neo4j_run_query()` to execute visualization-friendly queries

    For specific entity questions:
    1. First call `neo4j_get_schema(user_question)` to get context-relevant schema information
    2. Then call `neo4j_find_nodes_by_type()` to locate entities
    3. Use `neo4j_get_node_info()` or `neo4j_find_relationships()` for specific details
    4. Finally use `neo4j_run_query()` to create visualization-friendly output

    For relationship questions:
    1. First call `neo4j_get_schema(user_question)` to get context-relevant schema information
    2. Identify the relationship types of interest from the schema response
    3. Use `neo4j_run_query()` with a relationship-focused query that includes both nodes and the relationships

    For sensor data questions:
    1. First call `neo4j_get_schema(user_question)` to get context-relevant schema information
    2. Then call `neo4j_find_sensor_readings()` to get current values
    3. Use `neo4j_run_query()` to create visualization-friendly queries showing sensors and their locations

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

    Each node has an `identifier` property (not "id") and a `name`, and many have extra properties like `entType`, `unit`, `lat`, `lon`, `latest_value`, or `description`.

    Relationships between nodes are dynamically created and may include custom properties.

    ---

    📊 For visualization in the UI:
    To ensure your responses can be visualized in the UI, follow these guidelines:
    1. Always include a clear Cypher query in your response when answering data questions
    2. Use queries that show relationships between nodes (using the MATCH pattern)
    3. Format your Cypher queries with proper indentation and line breaks
    4. Ensure queries have a RETURN clause that includes both nodes and relationships when appropriate

    Example of a good visualization query:
    ```
    MATCH (t:Thing)-[r:IS_INSTALLED_IN]->(l:Location)
    WHERE l.name = 'École Maternelle'
    RETURN t, r, l
    ```

    ---

    🔍 Your responses should be:
    - Always in the SAME LANGUAGE as the user's question (French for French questions)
    - Data-driven and backed by actual database content
    - Visually oriented when possible (using well-structured Cypher queries)
    - Concise yet informative

    Remember that users may explore the data visually after your response, so provide both textual answers and visualizable queries.
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