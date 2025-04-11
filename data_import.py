"""
Module for importing data from CSV files into the Neo4j database using neomodel.
This replaces the Cypher script approach with a Python-based import process.
"""
import os
import csv
import json
import requests
from io import StringIO
from typing import Dict, List, Any, Optional
from neomodel import db, config

from models import (
    Application, Department, Manufacturer, Module, Network,
    Power, Sensor, Thing, ThingType, Vendor, Location,
    clear_database, find_node_by_id
)
import dotenv
# Load environment variables from .env file
dotenv.load_dotenv()

# CSV URLs
BASE_URL = "https://raw.githubusercontent.com/josephazar/graph_of_things/main/Neo4jThings/"
CSV_FILES = {
    "applications": "applications.csv",
    "departments": "departments.csv",
    "manufacturers": "manufacturers.csv",
    "modules": "module.csv",
    "networks": "network.csv",
    "power": "power.csv",
    "sensors": "sensors.csv",
    "things": "things.csv",
    "thingtypes": "thingtype.csv",
    "vendors": "vendors.csv",
    "locations": "locations.csv",
    "relations": "relation.csv"
}


def fetch_csv(csv_name: str) -> List[Dict[str, str]]:
    """
    Fetch a CSV file from the GitHub repository and parse it
    
    Args:
        csv_name: Name of the CSV file (without .csv extension)
        
    Returns:
        List of dictionaries, each representing a row in the CSV
    """
    if csv_name not in CSV_FILES:
        raise ValueError(f"Unknown CSV file: {csv_name}")
    
    url = BASE_URL + CSV_FILES[csv_name]
    print(f"Fetching {url}...")
    
    response = requests.get(url)
    response.raise_for_status()  # Raise exception for 4XX/5XX responses
    
    # Handle BOM in CSV - strip the BOM character from the text
    csv_text = response.text
    if csv_text.startswith('\ufeff'):
        csv_text = csv_text[1:]
    
    csv_content = StringIO(csv_text)
    reader = csv.DictReader(csv_content)
    data = list(reader)
    
    # Print first row for debugging
    if data:
        print(f"First row of {csv_name}: {data[0]}")
    else:
        print(f"Warning: No data found in {csv_name}")
        
    return data
def create_node(model_class, data: Dict[str, str]) -> Any:
    """
    Create a node of the specified model class with the given data
    
    Args:
        model_class: neomodel StructuredNode class
        data: Dictionary of node properties
        
    Returns:
        Created node instance
    """
    print(f"Creating {model_class.__name__} with data: {data}")
    
    # Copy data to avoid modifying the original
    processed_data = {}
    
    # Process keys to handle BOM character
    for key, value in data.items():
        # Remove BOM character if present
        if key.startswith('\ufeff'):
            clean_key = key.replace('\ufeff', '')
            processed_data[clean_key] = value
        else:
            processed_data[key] = value
    
    # Filter out empty values
    filtered_data = {k: v for k, v in processed_data.items() if v}
    
    # Special handling for numeric fields
    if "lat" in filtered_data and filtered_data["lat"]:
        filtered_data["lat"] = float(filtered_data["lat"])
    if "lon" in filtered_data and filtered_data["lon"]:
        filtered_data["lon"] = float(filtered_data["lon"])
    
    # Handle id/identifier mapping
    if 'id' in filtered_data:
        filtered_data['identifier'] = filtered_data.pop('id')
    elif 'identifier' not in filtered_data:
        print(f"ERROR: No 'id' or 'identifier' field found in data: {filtered_data}")
        return None  # Skip this node
        
    print(f"Processed data: {filtered_data}")
    
    try:
        # Create and save the node
        node = model_class(**filtered_data)
        node.save()
        print(f"Successfully created {model_class.__name__}: {filtered_data.get('identifier')}")
        return node
    except Exception as e:
        print(f"ERROR creating {model_class.__name__}: {str(e)}")
        print(f"Data: {filtered_data}")
        return None

def create_relationship(source_id: str, target_id: str, rel_name: str, props_json: Optional[str] = None):
    """
    Create a relationship between two nodes
    
    Args:
        source_id: ID of the source node
        target_id: ID of the target node
        rel_name: Name of the relationship
        props_json: JSON string of relationship properties
    """
    # Find the source and target nodes
    source_node = find_node_by_id(source_id)
    target_node = find_node_by_id(target_id)
    
    if not source_node or not target_node:
        print(f"Could not find nodes for relationship: {source_id} -> {target_id}")
        return
    
    # Parse properties if provided
    props = {}
    if props_json and props_json.strip():
        try:
            props = json.loads(props_json)
        except json.JSONDecodeError:
            print(f"Invalid JSON in relationship properties: {props_json}")
    
    # Use Cypher to create the relationship with properties
    # This approach ensures we can create any relationship type dynamically
    query = """
    MATCH (source), (target)
    WHERE source.identifier = $source_id AND target.identifier = $target_id
    CREATE (source)-[r:`{}`]->(target)
    SET r += $props
    RETURN r
    """.format(rel_name)
    
    db.cypher_query(
        query, 
        {"source_id": source_id, "target_id": target_id, "props": props}
    )


def import_all_data():
    """Import all data from CSVs into the Neo4j database"""
    # Clear the database first
    clear_database()
    print("Database cleared. Starting import...")
    
    # Create nodes
    print("Creating Application nodes...")
    applications_data = fetch_csv("applications")
    print(applications_data)
    for row in applications_data:
        create_node(Application, row)
    
    print("Creating Department nodes...")
    departments_data = fetch_csv("departments")
    for row in departments_data:
        create_node(Department, row)
    
    print("Creating Manufacturer nodes...")
    manufacturers_data = fetch_csv("manufacturers")
    for row in manufacturers_data:
        create_node(Manufacturer, row)
    
    print("Creating Module nodes...")
    modules_data = fetch_csv("modules")
    for row in modules_data:
        create_node(Module, row)
    
    print("Creating Network nodes...")
    networks_data = fetch_csv("networks")
    for row in networks_data:
        create_node(Network, row)
    
    print("Creating Power nodes...")
    power_data = fetch_csv("power")
    for row in power_data:
        create_node(Power, row)
    
    print("Creating Sensor nodes...")
    sensors_data = fetch_csv("sensors")
    for row in sensors_data:
        create_node(Sensor, row)
    
    print("Creating Thing nodes...")
    things_data = fetch_csv("things")
    for row in things_data:
        create_node(Thing, row)
    
    print("Creating ThingType nodes...")
    thingtypes_data = fetch_csv("thingtypes")
    for row in thingtypes_data:
        create_node(ThingType, row)
    
    print("Creating Vendor nodes...")
    vendors_data = fetch_csv("vendors")
    for row in vendors_data:
        create_node(Vendor, row)
    
    print("Creating Location nodes...")
    locations_data = fetch_csv("locations")
    for row in locations_data:
        create_node(Location, row)
    
    # Create relationships
    print("Creating relationships...")
    relations_data = fetch_csv("relations")
    for row in relations_data:
        create_relationship(
            row["thingId"],
            row["entityid"],
            row["relationshipname"],
            row.get("prop", "{}")
        )
    
    print("Data import completed successfully!")


if __name__ == "__main__":
    # Set up neomodel configuration
    config.DATABASE_URL = os.getenv(
        "NEO4J_URI", 
        f"bolt://{os.getenv('NEO4J_USERNAME', 'neo4j')}:{os.getenv('NEO4J_PASSWORD', 'password')}@localhost:7687"
    )
    
    # Import all data
    import_all_data()