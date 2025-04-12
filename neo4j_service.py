"""
Modified Neo4j service module that works with Streamlit's hot-reloading feature.
"""
import os
from typing import Dict, Any, List, Optional
import json
import networkx as nx
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# Import from fixed models module instead of the original one
# from models import (
#     Application, Department, Manufacturer, Module, Network, 
#     Power, Sensor, Thing, ThingType, Vendor, Location,
#     find_node_by_id, get_node_counts
# )

class Neo4jService:
    """Service class for Neo4j database operations using direct driver"""
    
    _driver = None
    
    @classmethod
    def get_driver(cls):
        """Get or create Neo4j driver"""
        if cls._driver is None:
            # Get connection details from environment variables
            uri_env = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            username = os.getenv("NEO4J_USERNAME", "neo4j")
            password = os.getenv("NEO4J_PASSWORD", "password")
            uri = os.getenv("NEO4J_URI_CYPHER", "bolt://localhost:7687")
            
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
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    def get_schema() -> Dict[str, Any]:
        """
        Get the complete schema of the Neo4j database (node labels and relationship types).
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
        
        return {
            "status": "success",
            "nodeLabels": labels_with_properties,
            "relationshipTypes": rel_types_with_properties,
            "patterns": patterns_result["results"] if patterns_result["status"] == "success" else []
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
            
            # Add nodes - Use identifier or fallback to id for compatibility
            source_id = source_node.get('identifier', source_node.get('id', ''))
            target_id = target_node.get('identifier', target_node.get('id', ''))
            
            if source_id and source_id not in G:
                G.add_node(source_id)
                node_labels[source_id] = source_node.get('name', source_id)
                node_colors.append('skyblue')
                
            if target_id and target_id not in G:
                G.add_node(target_id)
                node_labels[target_id] = target_node.get('name', target_id)
                node_colors.append('lightgreen')
            
            # Add edge with relationship type as label
            if source_id and target_id:
                rel_type = item.get('relationship', 'RELATED_TO')
                G.add_edge(source_id, target_id, label=rel_type)
            
        elif 'n' in item:  # Single node query
            node = item['n']
            node_id = node.get('identifier', node.get('id', ''))
            if node_id:
                G.add_node(node_id)
                node_labels[node_id] = node.get('name', node_id)
                node_colors.append('skyblue')
            
        elif 'path' in item:  # Path query
            path = item['path']
            if hasattr(path, 'nodes') and hasattr(path, 'relationships'):
                nodes = path.nodes
                relationships = path.relationships
                
                for node in nodes:
                    node_id = node.get('identifier', node.get('id', ''))
                    if node_id:
                        G.add_node(node_id)
                        node_labels[node_id] = node.get('name', node_id)
                        node_colors.append('lightblue')
                    
                for rel in relationships:
                    start_node = rel.start_node.get('identifier', rel.start_node.get('id', ''))
                    end_node = rel.end_node.get('identifier', rel.end_node.get('id', ''))
                    if start_node and end_node:
                        G.add_edge(start_node, end_node, label=rel.type)
    
    # Create the plot (only if there are nodes)
    if G.number_of_nodes() > 0:
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
    else:
        # Return empty image if no nodes
        plt.figure(figsize=(12, 10))
        plt.text(0.5, 0.5, "No data to visualize", ha="center", va="center", fontsize=16)
        plt.axis('off')
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150)
        plt.close()
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        
        return base64.b64encode(image_png).decode('utf-8')