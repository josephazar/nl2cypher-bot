import os
from typing import List, Dict, Any
import json
import networkx as nx
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import pandas as pd
from pathlib import Path
import asyncio
from py2neo import Graph

import chainlit as cl
from chainlit.element import Element
from openai import AsyncAssistantEventHandler, AsyncAzureOpenAI, AzureOpenAI

# Initialize Azure OpenAI clients
async_openai_client = AsyncAzureOpenAI(
    azure_endpoint=os.getenv("OPENAI_API_BASE"),
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION"),
)

sync_openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("OPENAI_API_BASE"),
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION"),
)

# Connect to Neo4j
def get_neo4j_connection():
    return Graph(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(
            os.getenv("NEO4J_USERNAME", "neo4j"),
            os.getenv("NEO4J_PASSWORD", "password")
        )
    )

# Load the assistant
ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID")
assistant = sync_openai_client.beta.assistants.retrieve(ASSISTANT_ID)

# Set the UI name to the assistant's name
cl.config.ui.name = "Badevel Living Lab Assistant"
cl.config.ui.description = "Interrogez votre village intelligent avec du texte ou de la voix."

class Neo4jTools:
    """Tools for working with Neo4j graph database"""
    
    @staticmethod
    def run_query(query: str) -> Dict[str, Any]:
        """Run a Cypher query against Neo4j and return the results"""
        try:
            graph = get_neo4j_connection()
            results = graph.run(query).data()
            return {"status": "success", "results": results}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    def get_schema() -> Dict[str, Any]:
        """Get the complete schema of the Neo4j database (node labels and relationship types)"""
        # Get all node labels
        labels_query = """
        CALL db.labels() YIELD label
        RETURN label ORDER BY label
        """
        labels_result = Neo4jTools.run_query(labels_query)
        
        # Get all relationship types
        rel_types_query = """
        CALL db.relationshipTypes() YIELD relationshipType
        RETURN relationshipType ORDER BY relationshipType
        """
        rel_types_result = Neo4jTools.run_query(rel_types_query)
        
        # Get property keys for each node label
        labels_with_properties = []
        if labels_result["status"] == "success":
            for label_item in labels_result["results"]:
                label = label_item["label"]
                props_query = f"""
                MATCH (n:{label})
                UNWIND keys(n) AS key
                RETURN DISTINCT key AS property
                ORDER BY key
                """
                props_result = Neo4jTools.run_query(props_query)
                
                if props_result["status"] == "success":
                    properties = [item["property"] for item in props_result["results"]]
                    labels_with_properties.append({
                        "label": label,
                        "properties": properties
                    })
        
        # Get property keys for each relationship type
        rel_types_with_properties = []
        if rel_types_result["status"] == "success":
            for rel_item in rel_types_result["results"]:
                rel_type = rel_item["relationshipType"]
                rel_props_query = f"""
                MATCH ()-[r:{rel_type}]->()
                WHERE size(keys(r)) > 0
                UNWIND keys(r) AS key
                RETURN DISTINCT key AS property
                ORDER BY key
                """
                rel_props_result = Neo4jTools.run_query(rel_props_query)
                
                if rel_props_result["status"] == "success":
                    properties = [item["property"] for item in rel_props_result["results"]]
                    rel_types_with_properties.append({
                        "relationshipType": rel_type,
                        "properties": properties
                    })
        
        # Get common relationships patterns (which types connect to which)
        patterns_query = """
        MATCH (a)-[r]->(b)
        RETURN DISTINCT labels(a)[0] as sourceLabel, type(r) as relationshipType, labels(b)[0] as targetLabel
        ORDER BY sourceLabel, relationshipType, targetLabel
        """
        patterns_result = Neo4jTools.run_query(patterns_query)
        
        return {
            "status": "success",
            "nodeLabels": labels_with_properties,
            "relationshipTypes": rel_types_with_properties,
            "patterns": patterns_result["results"] if patterns_result["status"] == "success" else []
        }
    
    @staticmethod
    def get_node_info(node_id: str) -> Dict[str, Any]:
        """Get information about a specific node"""
        query = f"""
        MATCH (n {{id: '{node_id}'}})
        RETURN n
        """
        return Neo4jTools.run_query(query)
    
    @staticmethod
    def find_relationships(node_id: str) -> Dict[str, Any]:
        """Find all relationships for a specific node"""
        query = f"""
        MATCH (n {{id: '{node_id}'}})-[r]-(m)
        RETURN n, type(r) as relationship, r, m
        """
        return Neo4jTools.run_query(query)
    
    @staticmethod
    def find_sensor_readings() -> Dict[str, Any]:
        """Find all sensor readings"""
        query = """
        MATCH (t:Thing)
        WHERE t.latest_value IS NOT NULL
        RETURN t.id as id, t.name as name, t.latest_value as value
        """
        return Neo4jTools.run_query(query)
    
    @staticmethod
    def find_nodes_by_type(node_type: str) -> Dict[str, Any]:
        """Find all nodes of a specific type"""
        query = f"""
        MATCH (n:{node_type})
        RETURN n
        """
        return Neo4jTools.run_query(query)
    
    @staticmethod
    def count_nodes_by_type() -> Dict[str, Any]:
        """Count the number of nodes for each node label/type"""
        query = """
        CALL db.labels() YIELD label
        CALL apoc.cypher.run('MATCH (n:' + $label + ') RETURN count(n) as count', {label: label}) YIELD value
        RETURN label, value.count AS count
        ORDER BY count DESC
        """
        return Neo4jTools.run_query(query)
    
    @staticmethod
    def get_node_properties(node_label: str) -> Dict[str, Any]:
        """Get all property keys used by nodes with a specific label"""
        query = f"""
        MATCH (n:{node_label})
        UNWIND keys(n) AS property
        RETURN DISTINCT property
        ORDER BY property
        """
        return Neo4jTools.run_query(query)
    
    @staticmethod
    def find_path_between_nodes(start_id: str, end_id: str) -> Dict[str, Any]:
        """Find a path between two nodes"""
        query = f"""
        MATCH path = shortestPath((a {{id: '{start_id}'}})-[*]-(b {{id: '{end_id}'}}))
        RETURN path
        """
        return Neo4jTools.run_query(query)

def generate_graph_visualization(graph_data, title="Badevel Living Lab Graph"):
    """Generate a NetworkX graph visualization from Neo4j results"""
    G = nx.Graph()
    
    # Add nodes with labels
    node_colors = []
    node_labels = {}
    
    for item in graph_data:
        # Handle different result formats
        if 'n' in item and 'm' in item:  # Relationship query
            source_node = item['n']
            target_node = item['m']
            
            # Add nodes
            if source_node['id'] not in G:
                G.add_node(source_node['id'])
                node_labels[source_node['id']] = source_node.get('name', source_node['id'])
                node_colors.append('skyblue')
                
            if target_node['id'] not in G:
                G.add_node(target_node['id'])
                node_labels[target_node['id']] = target_node.get('name', target_node['id'])
                node_colors.append('lightgreen')
            
            # Add edge with relationship type as label
            rel_type = item.get('relationship', 'RELATED_TO')
            G.add_edge(source_node['id'], target_node['id'], label=rel_type)
            
        elif 'n' in item:  # Single node query
            node = item['n']
            G.add_node(node['id'])
            node_labels[node['id']] = node.get('name', node['id'])
            node_colors.append('skyblue')
            
        elif 'path' in item:  # Path query
            path = item['path']
            nodes = path.nodes
            relationships = path.relationships
            
            for node in nodes:
                G.add_node(node['id'])
                node_labels[node['id']] = node.get('name', node['id'])
                node_colors.append('lightblue')
                
            for rel in relationships:
                start_node = rel.start_node['id']
                end_node = rel.end_node['id']
                G.add_edge(start_node, end_node, label=rel.type)
    
    # Create the plot
    plt.figure(figsize=(12, 10))
    pos = nx.spring_layout(G, seed=42)
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, alpha=0.8, node_size=700)
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.7)
    
    # Draw node labels
    nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=10)
    
    # Draw edge labels
    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
    
    plt.title(title, fontsize=16)
    plt.axis('off')
    
    # Convert plot to base64 for embedding in HTML
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    plt.close()
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    
    return base64.b64encode(image_png).decode('utf-8')

def create_markdown_table(data):
    """Convert a list of dictionaries to a markdown table"""
    if not data:
        return "No data to display"
    
    # Extract column names from the first item
    columns = list(data[0].keys())
    
    # Create header row
    table = "| " + " | ".join(columns) + " |\n"
    table += "| " + " | ".join(["---"] * len(columns)) + " |\n"
    
    # Add data rows
    for item in data:
        # Format each value and handle nested objects
        row_values = []
        for col in columns:
            value = item.get(col, "")
            if isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False)
            row_values.append(str(value))
        
        table += "| " + " | ".join(row_values) + " |\n"
    
    return table

def process_neo4j_results(results):
    """Process Neo4j results and return formatted data for display"""
    processed_data = []
    
    for item in results:
        processed_item = {}
        
        for key, value in item.items():
            # If it's a Neo4j Node object, extract the properties
            if hasattr(value, 'items') and callable(getattr(value, 'items')):
                processed_item[key] = dict(value)
            else:
                processed_item[key] = value
                
        processed_data.append(processed_item)
    
    return processed_data

class EventHandler(AsyncAssistantEventHandler):
    def __init__(self, assistant_name: str) -> None:
        super().__init__()
        self.current_message: cl.Message = None
        self.current_step: cl.Step = None
        self.current_tool_call = None
        self.assistant_name = assistant_name

    async def on_text_created(self, text) -> None:
        self.current_message = await cl.Message(author=self.assistant_name, content="").send()

    async def on_text_delta(self, delta, snapshot):
        await self.current_message.stream_token(delta.value)

    async def on_text_done(self, text):
        await self.current_message.update()

    async def on_tool_call_created(self, tool_call):
        self.current_tool_call = tool_call.id
        self.current_step = cl.Step(name=tool_call.type, type="tool")
        self.current_step.language = "python"
        await self.current_step.send()


    async def on_tool_call_delta(self, delta, snapshot):
        if snapshot.id != self.current_tool_call:
            self.current_tool_call = snapshot.id
            self.current_step = cl.Step(name=delta.type, type="tool")
            self.current_step.language = "python"
            await self.current_step.send()
                
        if delta.type == "code_interpreter":
            if delta.code_interpreter.outputs:
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        # Handle code interpreter logs
                        self.current_step.output = output.logs
                        await self.current_step.update()
                    elif output.type == "image":
                        # Handle image output
                        image_element = cl.Image(
                            name=output.image.file_id,
                            display="inline",
                            size="large"
                        )
                        if not self.current_message.elements:
                            self.current_message.elements = []
                        self.current_message.elements.append(image_element)
                        await self.current_message.update()
            else:
                if delta.code_interpreter.input:
                    await self.current_step.stream_token(delta.code_interpreter.input)
                    
        # Handle Neo4j function calls - this should be at same level as if delta.type == "code_interpreter"
        elif delta.type == "function" and delta.function.name.startswith("neo4j_"):
            function_name = delta.function.name.replace("neo4j_", "")
            
            # Parse function arguments if available
            args = {}
            if hasattr(delta.function, 'arguments') and delta.function.arguments:
                try:
                    args = json.loads(delta.function.arguments)
                except json.JSONDecodeError:
                    print(f"Error parsing arguments for function {function_name}")
                    args = {}
            
            # Now process the function calls with proper arguments
            if function_name == "get_node_info" and "node_id" in args:
                result = Neo4jTools.get_node_info(args["node_id"])
                
                if result["status"] == "success" and result["results"]:
                    processed_data = process_neo4j_results(result["results"])
                    table = create_markdown_table(processed_data)
                    
                    if not hasattr(self, "function_results"):
                        self.function_results = ""
                    self.function_results += f"\n\n{table}\n\n"
            
            elif function_name == "find_relationships" and "node_id" in args:
                result = Neo4jTools.find_relationships(args["node_id"])
                
                if result["status"] == "success" and result["results"]:
                    processed_data = process_neo4j_results(result["results"])
                    table = create_markdown_table(processed_data)
                    graph_image = generate_graph_visualization(result["results"], f"Relationships for {args['node_id']}")
                    
                    if not hasattr(self, "function_results"):
                        self.function_results = ""
                    self.function_results += f"\n\n{table}\n\n"
                    
                    image_element = cl.Image(
                        content=base64.b64decode(graph_image),
                        name="relationships.png",
                        display="inline",
                        size="large"
                    )
                    if not self.current_message.elements:
                        self.current_message.elements = []
                    self.current_message.elements.append(image_element)
                        
            elif function_name == "find_sensor_readings":
                result = Neo4jTools.find_sensor_readings()
                
                if result["status"] == "success" and result["results"]:
                    processed_data = process_neo4j_results(result["results"])
                    table = create_markdown_table(processed_data)
                    
                    # Create a DataFrame for visualization
                    df = pd.DataFrame(processed_data)
                    
                    if not hasattr(self, "function_results"):
                        self.function_results = ""
                    self.function_results += f"\n\n{table}\n\n"
            
            elif function_name == "count_nodes_by_type":
                result = Neo4jTools.count_nodes_by_type()
                
                if result["status"] == "success" and result["results"]:
                    processed_data = process_neo4j_results(result["results"])
                    table = create_markdown_table(processed_data)
                    
                    if not hasattr(self, "function_results"):
                        self.function_results = ""
                    self.function_results += f"\n\n{table}\n\n"
                    
                    # Create a bar chart of node counts
                    plt.figure(figsize=(10, 6))
                    df = pd.DataFrame(processed_data)
                    if 'count' in df.columns and 'label' in df.columns:
                        df = df.sort_values('count', ascending=False)
                        plt.bar(df['label'], df['count'], color='skyblue')
                        plt.title('Node Counts by Type')
                        plt.xlabel('Node Type')
                        plt.ylabel('Count')
                        plt.xticks(rotation=45, ha='right')
                        plt.tight_layout()
                        
                        # Convert plot to base64 for embedding
                        buffer = BytesIO()
                        plt.savefig(buffer, format='png')
                        buffer.seek(0)
                        chart_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        plt.close()
                        
                        image_element = cl.Image(
                            content=base64.b64decode(chart_image),
                            name="node_counts.png",
                            display="inline",
                            size="large"
                        )
                        if not self.current_message.elements:
                            self.current_message.elements = []
                        self.current_message.elements.append(image_element)
            
            elif function_name == "get_node_properties" and "node_label" in args:
                result = Neo4jTools.get_node_properties(args["node_label"])
                
                if result["status"] == "success" and result["results"]:
                    processed_data = process_neo4j_results(result["results"])
                    table = create_markdown_table(processed_data)
                    
                    if not hasattr(self, "function_results"):
                        self.function_results = ""
                    self.function_results += f"\n\n{table}\n\n"
                    
            elif function_name == "find_nodes_by_type" and "node_type" in args:
                result = Neo4jTools.find_nodes_by_type(args["node_type"])
                
                if result["status"] == "success" and result["results"]:
                    processed_data = process_neo4j_results(result["results"])
                    table = create_markdown_table(processed_data)
                    
                    if not hasattr(self, "function_results"):
                        self.function_results = ""
                    self.function_results += f"\n\n{table}\n\n"
                    
            elif function_name == "find_path_between_nodes" and "start_id" in args and "end_id" in args:
                result = Neo4jTools.find_path_between_nodes(args["start_id"], args["end_id"])
                
                if result["status"] == "success" and result["results"]:
                    graph_image = generate_graph_visualization(
                        result["results"], 
                        f"Path from {args['start_id']} to {args['end_id']}"
                    )
                    
                    image_element = cl.Image(
                        content=base64.b64decode(graph_image),
                        name="path.png",
                        display="inline",
                        size="large"
                    )
                    if not self.current_message.elements:
                        self.current_message.elements = []
                    self.current_message.elements.append(image_element)
                    
            elif function_name == "get_schema":
                result = Neo4jTools.get_schema()
                
                if result["status"] == "success":
                    # Process node labels
                    node_labels_table = "### Node Labels\n\n"
                    node_labels_table += "| Label | Properties |\n"
                    node_labels_table += "|-------|------------|\n"
                    
                    for label_info in result["nodeLabels"]:
                        label = label_info["label"]
                        properties = label_info["properties"]
                        props_str = ", ".join(properties[:5])
                        if len(properties) > 5:
                            props_str += ", ..."
                        node_labels_table += f"| {label} | {props_str} |\n"
                    
                    # Process relationship types
                    rel_types_table = "\n\n### Relationship Types\n\n"
                    rel_types_table += "| Type | Properties |\n"
                    rel_types_table += "|------|------------|\n"
                    
                    for rel_info in result["relationshipTypes"]:
                        rel_type = rel_info["relationshipType"]
                        properties = rel_info["properties"]
                        props_str = ", ".join(properties[:5])
                        if len(properties) > 5:
                            props_str += ", ..."
                        rel_types_table += f"| {rel_type} | {props_str} |\n"
                    
                    # Process connection patterns
                    patterns_table = "\n\n### Connection Patterns\n\n"
                    patterns_table += "| Source | Relationship | Target |\n"
                    patterns_table += "|--------|--------------|--------|\n"
                    
                    for pattern in result["patterns"][:15]:  # Limit to 15 patterns
                        source = pattern.get("sourceLabel", "")
                        rel = pattern.get("relationshipType", "")
                        target = pattern.get("targetLabel", "")
                        patterns_table += f"| {source} | {rel} | {target} |\n"
                    
                    if len(result["patterns"]) > 15:
                        patterns_table += "| ... | ... | ... |\n"
                    
                    # Add tables to the message
                    if not hasattr(self, "function_results"):
                        self.function_results = ""
                    self.function_results += f"\n\n{node_labels_table}\n\n{rel_types_table}\n\n{patterns_table}\n\n"

    async def on_tool_call_done(self, tool_call):
        # Add function results to the message if available
        if hasattr(self, "function_results"):
            await self.current_message.stream_token(self.function_results)
            delattr(self, "function_results")
        
        await self.current_message.update()

@cl.step(type="tool")
async def speech_to_text(audio_file):
    """Transcribe audio to text using Azure OpenAI Whisper model"""
    response = await async_openai_client.audio.transcriptions.create(
        model=os.getenv("OPENAI_WHISPER_MODEL"), file=audio_file
    )
    return response.text

async def upload_files(files: List[Element]):
    """Upload files to Azure OpenAI for processing"""
    file_ids = []
    for file in files:
        uploaded_file = await async_openai_client.files.create(
            file=Path(file.path), purpose="assistants"
        )
        file_ids.append(uploaded_file.id)
    return file_ids

async def process_files(files: List[Element]):
    """Process uploaded files and prepare them for the assistant"""
    # Upload files if any and get file_ids
    file_ids = []
    if len(files) > 0:
        file_ids = await upload_files(files)

    return [
        {
            "file_id": file_id,
            "tools": [{"type": "code_interpreter"}],
        }
        for file_id in file_ids
    ]

@cl.on_chat_start
async def start_chat():
    """Initialize the chat session"""
    # Create an OpenAI Thread
    thread = await async_openai_client.beta.threads.create()
    # Store thread ID in user session
    cl.user_session.set("thread_id", thread.id)
    
    # Send welcome message
    await cl.Avatar(name="Badevel", url="https://img.icons8.com/color/96/smart-city.png").send()
    
    welcome_message = """# 🌟 Bienvenue au Badevel Living Lab Assistant! 🌟

Je peux vous aider à explorer les données du village intelligent de Badevel. Posez-moi des questions sur:

- 🌡️ Les capteurs et leurs mesures actuelles
- 🏢 Les bâtiments et leurs équipements
- 🔌 La consommation et production d'énergie
- 📊 Les relations entre différents éléments

Vous pouvez me parler ou écrire vos questions!"""

    await cl.Message(content=welcome_message).send()
    
    # Automatically fetch schema information
    try:
        schema_msg = cl.Message(content="📊 *Analyse de la structure de la base de données...*")
        await schema_msg.send()
        
        # Get database schema
        schema_result = Neo4jTools.get_schema()
        if schema_result["status"] == "success":
            schema_info = "## Structure de la base de données\n\n"
            
            # Node labels with counts
            count_result = Neo4jTools.count_nodes_by_type()
            if count_result["status"] == "success":
                schema_info += "### Types de nœuds\n\n"
                schema_info += "| Type | Nombre | Propriétés |\n|------|--------|------------|\n"
                
                for item in count_result["results"]:
                    label = item["label"]
                    count = item["count"]
                    
                    # Find properties for this label
                    properties = []
                    for label_info in schema_result["nodeLabels"]:
                        if label_info["label"] == label:
                            properties = label_info["properties"]
                            break
                    
                    props_str = ", ".join(properties[:5])
                    if len(properties) > 5:
                        props_str += ", ..."
                    
                    schema_info += f"| {label} | {count} | {props_str} |\n"
                
                schema_info += "\n"
            
            # Relationship types
            if schema_result["relationshipTypes"]:
                schema_info += "### Types de relations\n\n"
                schema_info += "| Type | Propriétés |\n|------|------------|\n"
                
                for rel_info in schema_result["relationshipTypes"]:
                    rel_type = rel_info["relationshipType"]
                    properties = rel_info["properties"]
                    
                    props_str = ", ".join(properties[:5])
                    if len(properties) > 5:
                        props_str += ", ..."
                    
                    schema_info += f"| {rel_type} | {props_str} |\n"
                
                schema_info += "\n"
            
            # Common patterns
            if schema_result["patterns"]:
                schema_info += "### Modèles de connexion\n\n"
                schema_info += "| Source | Relation | Destination |\n|--------|----------|-------------|\n"
                
                # Limit to first 10 patterns
                for pattern in schema_result["patterns"][:10]:
                    source = pattern.get("sourceLabel", "")
                    rel = pattern.get("relationshipType", "")
                    target = pattern.get("targetLabel", "")
                    schema_info += f"| {source} | {rel} | {target} |\n"
                
                if len(schema_result["patterns"]) > 10:
                    schema_info += "| ... | ... | ... |\n"
            
            # Update the message with schema information
            await schema_msg.update(content=schema_info)
            
            # Store schema info in user session for future reference
            cl.user_session.set("db_schema", schema_result)
        else:
            await schema_msg.update(content="❌ Erreur lors de l'analyse de la structure de la base de données.")
    except Exception as e:
        print(f"Error fetching schema: {str(e)}")
    
    # Update the assistant with Neo4j tools
    await async_openai_client.beta.assistants.update(
        assistant_id=ASSISTANT_ID,
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
        ]
    )

@cl.on_message
async def main(message: cl.Message):
    """Process user messages"""
    thread_id = cl.user_session.get("thread_id")
    
    # Process any file attachments
    attachments = await process_files(message.elements)
    
    # Add user message to the thread
    await async_openai_client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message.content,
        attachments=attachments,
    )
    
    # Create and process a run with the assistant
    async with async_openai_client.beta.threads.runs.stream(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID,
        event_handler=EventHandler(assistant_name="Badevel"),
    ) as stream:
        await stream.until_done()

@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.AudioChunk):
    """Process audio chunks from speech input"""
    if chunk.isStart:
        buffer = BytesIO()
        # Set name with extension for Whisper to recognize file type
        buffer.name = f"input_audio.{chunk.mimeType.split('/')[1]}"
        # Initialize the session for a new audio stream
        cl.user_session.set("audio_buffer", buffer)
        cl.user_session.set("audio_mime_type", chunk.mimeType)

    # Write the chunks to a buffer
    cl.user_session.get("audio_buffer").write(chunk.data)

@cl.on_audio_end
async def on_audio_end(elements: list[Element]):
    """Process complete audio input and transcribe it"""
    # Get the audio buffer from the session
    audio_buffer: BytesIO = cl.user_session.get("audio_buffer")
    audio_buffer.seek(0)  # Move the file pointer to the beginning
    audio_file = audio_buffer.read()
    audio_mime_type: str = cl.user_session.get("audio_mime_type")

    # Create an audio element to display in the UI
    input_audio_el = cl.Audio(
        mime=audio_mime_type, content=audio_file, name=audio_buffer.name
    )
    await cl.Message(
        author="You",
        type="user_message",
        content="",
        elements=[input_audio_el, *elements],
    ).send()

    # Transcribe speech to text
    whisper_input = (audio_buffer.name, audio_file, audio_mime_type)
    transcription = await speech_to_text(whisper_input)

    # Send the transcribed message
    msg = cl.Message(author="You", content=transcription, elements=elements)
    await main(message=msg)

if __name__ == "__main__":
    # Test Neo4j connection on startup
    try:
        graph = get_neo4j_connection()
        print("✅ Successfully connected to Neo4j database!")
    except Exception as e:
        print(f"❌ Failed to connect to Neo4j: {str(e)}")