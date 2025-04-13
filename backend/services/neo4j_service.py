"""
Service for Neo4j database operations.
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from neo4j import GraphDatabase
from dotenv import load_dotenv
import chromadb
from openai import AzureOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables if not already loaded
load_dotenv()

class Neo4jService:
    """Service class for Neo4j database operations using direct driver"""
    
    _driver = None
    
    @classmethod
    def get_driver(cls):
        """Get or create Neo4j driver"""
        if cls._driver is None:
            # Get connection details from environment variables
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            username = os.getenv("NEO4J_USERNAME", "neo4j")
            password = os.getenv("NEO4J_PASSWORD", "password")
            
            cls._driver = GraphDatabase.driver(uri, auth=(username, password))
        return cls._driver
    
    @classmethod
    def close_driver(cls):
        """Close the Neo4j driver if it exists"""
        if cls._driver is not None:
            cls._driver.close()
            cls._driver = None
    
    @staticmethod
    def run_cypher_query(query: str, params: Dict = None) -> Dict[str, Any]:
        """
        Run a raw Cypher query against Neo4j and return the results.
        """
        driver = Neo4jService.get_driver()
        try:
            if params is None:
                params = {}
            
            with driver.session() as session:
                result = session.run(query, params)
                columns = result.keys()
                records = list(result)
                
                # Format results as dictionaries with column names as keys
                formatted_results = []
                for record in records:
                    formatted_row = {}
                    for i, col in enumerate(columns):
                        # Handle Neo4j nodes
                        value = record[col]
                        if hasattr(value, 'items') and callable(getattr(value, 'items')):
                            # Convert dictionaries
                            formatted_row[col] = dict(value)
                        elif hasattr(value, 'labels') and callable(getattr(value, 'labels')):
                            # Convert Neo4j node to dictionary
                            node_dict = dict(value)
                            node_dict['labels'] = list(value.labels)
                            formatted_row[col] = node_dict
                        else:
                            formatted_row[col] = value
                    formatted_results.append(formatted_row)
                
                return {"status": "success", "results": formatted_results}
        except Exception as e:
            logger.error(f"Error running Cypher query: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    def get_schema(query: str = "") -> Dict[str, Any]:
        """
        Get the complete schema of the Neo4j database (node labels and relationship types),
        and find relevant relations and example queries using the vector store.
        
        Args:
            query: The user's query to find relevant relations and examples
        
        Returns:
            Dictionary with schema information, relevant relations and example queries
        """
        # Get all node labels
        labels_query = """
        CALL db.labels() YIELD label
        RETURN label ORDER BY label
        """
        labels_result = Neo4jService.run_cypher_query(labels_query)
        
        # Get all relationship types
        rel_types_query = """
        CALL db.relationshipTypes() YIELD relationshipType
        RETURN relationshipType ORDER BY relationshipType
        """
        rel_types_result = Neo4jService.run_cypher_query(rel_types_query)
        
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
                props_result = Neo4jService.run_cypher_query(props_query)
                
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
                rel_props_result = Neo4jService.run_cypher_query(rel_props_query)
                
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
        patterns_result = Neo4jService.run_cypher_query(patterns_query)
        
        # If a query is provided, use vector search to find relevant relations and example queries
        relations_info = ""
        queries_info = ""
        
        if query:
            try:
                output = "Relevant relations:\n"
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
                chroma_db_path = os.path.join(base_dir, "chromadb")
                
                # Check if the ChromaDB directory exists
                if not os.path.exists(chroma_db_path):
                    os.makedirs(chroma_db_path, exist_ok=True)
                    
                chroma_client = chromadb.PersistentClient(path=chroma_db_path)
                
                # Get embeddings from Azure OpenAI
                client = AzureOpenAI(
                    api_key=os.getenv("OPENAI_API_KEY"),
                    api_version=os.getenv("OPENAI_API_VERSION"),
                    azure_endpoint=os.getenv("OPENAI_API_BASE"),
                )
                
                # Get embedding for the query
                embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-ada-002")
                logger.info(f"Getting embedding for query: '{query}' using model: {embedding_model}")
                query_embedding = client.embeddings.create(input=query, model=embedding_model).data[0].embedding
                
                # Query the collections
                try:
                    # Query relations collection
                    collection = chroma_client.get_or_create_collection(name="nl2cypher-relations")
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=15,
                        include=["documents", "metadatas"]
                    )
                    
                    # Format relations info
                    relations_info = []
                    if results["documents"] and results["documents"][0]:
                        for metadata, document in zip(results["metadatas"][0], results["documents"][0]):
                            relations_info.append(f"Relation: {metadata['relation']}\nDescription: {document}\n")
                    
                    output += "\n\n".join(relations_info)
                    
                    # Query example queries collection
                    collection = chroma_client.get_or_create_collection(name="nl2cypher-queries")
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=15,
                        include=["documents", "metadatas"]
                    )
                    
                    # Format queries info
                    queries_info = []
                    if results["documents"] and results["documents"][0]:
                        for metadata, document in zip(results["metadatas"][0], results["documents"][0]):
                            queries_info.append(f"Question: {document}\nQuery: {metadata['query']}\n")
                    
                    output += "\nQueries Examples:\n"
                    output += "\n\n".join(queries_info)
                
                except Exception as e:
                    logger.error(f"Error querying vector store: {str(e)}")
                    output += f"\nError querying vector store: {str(e)}"
            
            except Exception as e:
                logger.error(f"Error with vector store: {str(e)}")
                output = f"Error with vector store: {str(e)}"
        else:
            output = "No query provided for vector search."
        
        return {
            "status": "success",
            "nodeLabels": labels_with_properties,
            "relationshipTypes": rel_types_with_properties,
            "patterns": patterns_result["results"] if patterns_result["status"] == "success" else [],
            "relations_info": output,
        }
    
    @staticmethod
    def get_node_info(node_id: str) -> Dict[str, Any]:
        """Get information about a specific node"""
        query = """
        MATCH (n {identifier: $node_id})
        RETURN n
        """
        return Neo4jService.run_cypher_query(query, {"node_id": node_id})
    
    @staticmethod
    def find_relationships(node_id: str) -> Dict[str, Any]:
        """Find all relationships for a specific node"""
        query = """
        MATCH (n {identifier: $node_id})-[r]-(m)
        RETURN n, type(r) as relationship, r, m
        """
        return Neo4jService.run_cypher_query(query, {"node_id": node_id})
    
    @staticmethod
    def find_sensor_readings() -> Dict[str, Any]:
        """Find all sensor readings"""
        query = """
        MATCH (t:Thing)
        WHERE t.latest_value IS NOT NULL
        RETURN t.identifier as id, t.name as name, t.latest_value as value
        """
        return Neo4jService.run_cypher_query(query)
    
    @staticmethod
    def find_nodes_by_type(node_type: str) -> Dict[str, Any]:
        """Find all nodes of a specific type"""
        query = f"""
        MATCH (n:{node_type})
        RETURN n
        """
        return Neo4jService.run_cypher_query(query)
    
    @staticmethod
    def count_nodes_by_type() -> Dict[str, Any]:
        """Count the number of nodes for each node label/type"""
        query = """
        CALL db.labels() YIELD label
        CALL apoc.cypher.run('MATCH (n:' + $label + ') RETURN count(n) as count', {}) YIELD value
        RETURN $label as label, value.count as count
        """
        
        # If APOC is not available, fall back to a more basic query
        try:
            result = Neo4jService.run_cypher_query(query, {"label": "Test"})
            if result["status"] == "error" and "APOC" in result["message"]:
                # Fall back to basic query
                return Neo4jService._count_nodes_basic()
            else:
                return Neo4jService.run_cypher_query(query)
        except:
            return Neo4jService._count_nodes_basic()
    
    @staticmethod
    def _count_nodes_basic() -> Dict[str, Any]:
        """Count nodes without using APOC"""
        # First get all labels
        labels_query = """
        CALL db.labels() YIELD label
        RETURN label
        """
        labels_result = Neo4jService.run_cypher_query(labels_query)
        
        if labels_result["status"] != "success":
            return labels_result
        
        # Count nodes for each label
        counts = []
        for label_item in labels_result["results"]:
            label = label_item["label"]
            count_query = f"""
            MATCH (n:{label})
            RETURN count(n) as count
            """
            count_result = Neo4jService.run_cypher_query(count_query)
            
            if count_result["status"] == "success" and count_result["results"]:
                counts.append({
                    "label": label,
                    "count": count_result["results"][0]["count"]
                })
        
        return {"status": "success", "results": counts}
    
    @staticmethod
    def get_node_properties(node_label: str) -> Dict[str, Any]:
        """Get all property keys used by nodes with a specific label"""
        query = f"""
        MATCH (n:{node_label})
        UNWIND keys(n) AS property
        RETURN DISTINCT property
        ORDER BY property
        """
        return Neo4jService.run_cypher_query(query)
    
    @staticmethod
    def find_path_between_nodes(start_id: str, end_id: str) -> Dict[str, Any]:
        """Find a path between two nodes"""
        query = """
        MATCH path = shortestPath((a {identifier: $start_id})-[*]-(b {identifier: $end_id}))
        RETURN path
        """
        return Neo4jService.run_cypher_query(query, {"start_id": start_id, "end_id": end_id})