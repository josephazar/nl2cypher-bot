"""
Modified version of the models module that prevents relationship redefinition
when used with Streamlit's hot-reloading feature.
"""
from neomodel import (
    StructuredNode, StringProperty, FloatProperty, 
    RelationshipTo, RelationshipFrom, StructuredRel,
    config, db, UniqueIdProperty, JSONProperty
)
import os
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# Configure neomodel
config.DATABASE_URL = os.getenv(
    "NEO4J_URI", 
    f"bolt://{os.getenv('NEO4J_USERNAME', 'neo4j')}:{os.getenv('NEO4J_PASSWORD', 'password')}@localhost:7687"
)

# Define relationship classes to include properties
class BaseRelationship(StructuredRel):
    """Base relationship that can hold dynamic properties"""
    # This will store any additional properties defined in the CSV
    properties = JSONProperty(default={})

# Track already defined model classes to prevent redefinition
_DEFINED_MODELS = {}

# Function to get or create a model class
def get_or_create_model(class_name, base_class=StructuredNode, **attrs):
    """Get an existing model class or create a new one if it doesn't exist"""
    if class_name in _DEFINED_MODELS:
        return _DEFINED_MODELS[class_name]
    
    # Create new class
    model_class = type(class_name, (base_class,), attrs)
    _DEFINED_MODELS[class_name] = model_class
    return model_class

# Create model classes only if they haven't been defined already
Application = get_or_create_model('Application', 
    uid=UniqueIdProperty(),
    identifier=StringProperty(unique_index=True, required=True),
    name=StringProperty(required=True)
)

Department = get_or_create_model('Department',
    uid=UniqueIdProperty(),
    identifier=StringProperty(unique_index=True, required=True),
    name=StringProperty(required=True)
)

Manufacturer = get_or_create_model('Manufacturer',
    uid=UniqueIdProperty(),
    identifier=StringProperty(unique_index=True, required=True),
    name=StringProperty(required=True)
)

Module = get_or_create_model('Module',
    uid=UniqueIdProperty(),
    identifier=StringProperty(unique_index=True, required=True),
    name=StringProperty(required=True)
)

Network = get_or_create_model('Network',
    uid=UniqueIdProperty(),
    identifier=StringProperty(unique_index=True, required=True),
    entType=StringProperty(),
    name=StringProperty(required=True)
)

Power = get_or_create_model('Power',
    uid=UniqueIdProperty(),
    identifier=StringProperty(unique_index=True, required=True),
    name=StringProperty(required=True)
)

Sensor = get_or_create_model('Sensor',
    uid=UniqueIdProperty(),
    identifier=StringProperty(unique_index=True, required=True),
    entType=StringProperty(),
    name=StringProperty(required=True),
    unit=StringProperty(),
    description=StringProperty()
)

ThingType = get_or_create_model('ThingType',
    uid=UniqueIdProperty(),
    identifier=StringProperty(unique_index=True, required=True),
    name=StringProperty(required=True)
)

Vendor = get_or_create_model('Vendor',
    uid=UniqueIdProperty(),
    identifier=StringProperty(unique_index=True, required=True),
    entType=StringProperty(),
    name=StringProperty(required=True)
)

Location = get_or_create_model('Location',
    uid=UniqueIdProperty(),
    identifier=StringProperty(unique_index=True, required=True),
    name=StringProperty(required=True)
)

Thing = get_or_create_model('Thing',
    uid=UniqueIdProperty(),
    identifier=StringProperty(unique_index=True, required=True),
    name=StringProperty(required=True),
    lat=FloatProperty(),
    lon=FloatProperty(),
    latest_value=StringProperty()
)

# Define relationships safely
def setup_relationships():
    """Set up relationships between models only if they haven't been set up before"""
    # Only set up relationships if they don't exist
    if not hasattr(Application, 'modules'):
        try:
            Application.modules = RelationshipTo('Module', 'USES', model=BaseRelationship)
            Department.locations = RelationshipTo('Location', 'MANAGES', model=BaseRelationship)
            Manufacturer.things = RelationshipTo('Thing', 'MAKES', model=BaseRelationship)
            Module.applications = RelationshipFrom('Application', 'USES', model=BaseRelationship)
            Module.things = RelationshipTo('Thing', 'PROCESSES_DATA_FROM', model=BaseRelationship)
            Network.things = RelationshipTo('Thing', 'CONNECTS', model=BaseRelationship)
            Power.things = RelationshipTo('Thing', 'POWERS', model=BaseRelationship)
            Sensor.things = RelationshipFrom('Thing', 'HAS_SENSOR', model=BaseRelationship)
            
            Thing.location = RelationshipTo('Location', 'LOCATED_AT', model=BaseRelationship)
            Thing.type = RelationshipTo('ThingType', 'IS_TYPE', model=BaseRelationship)
            Thing.sensors = RelationshipTo('Sensor', 'HAS_SENSOR', model=BaseRelationship)
            Thing.power_source = RelationshipTo('Power', 'POWERED_BY', model=BaseRelationship)
            Thing.network = RelationshipTo('Network', 'CONNECTED_VIA', model=BaseRelationship)
            Thing.manufactured_by = RelationshipTo('Manufacturer', 'MANUFACTURED_BY', model=BaseRelationship)
            Thing.vendor = RelationshipTo('Vendor', 'SOLD_BY', model=BaseRelationship)
            Thing.modules = RelationshipFrom('Module', 'PROCESSES_DATA_FROM', model=BaseRelationship)
            
            ThingType.things = RelationshipFrom('Thing', 'IS_TYPE', model=BaseRelationship)
            Vendor.things = RelationshipFrom('Thing', 'SOLD_BY', model=BaseRelationship)
            Location.things = RelationshipFrom('Thing', 'LOCATED_AT', model=BaseRelationship)
            Location.department = RelationshipFrom('Department', 'MANAGES', model=BaseRelationship)
            
            print("Relationships set up successfully")
        except Exception as e:
            # Print but don't fail - in most cases this means relationships already exist
            print(f"Note: {str(e)}")

# Try to set up relationships (will be ignored if already defined)
try:
    setup_relationships()
except Exception as e:
    print(f"Warning: Error setting up relationships: {str(e)}")

# Helper functions for common database operations
def clear_database():
    """Remove all nodes and relationships from the database"""
    db.cypher_query("MATCH (n) DETACH DELETE n")

def get_node_counts():
    """Get counts of all node types in the database"""
    node_types = [
        Application, Department, Manufacturer, Module, 
        Network, Power, Sensor, Thing, ThingType, Vendor, Location
    ]
    
    counts = {}
    for node_type in node_types:
        label = node_type.__name__
        count = len(node_type.nodes.all())
        counts[label] = count
    
    return counts

def find_node_by_id(node_id):
    """Find any node by its identifier property"""
    node_types = [
        Application, Department, Manufacturer, Module, 
        Network, Power, Sensor, Thing, ThingType, Vendor, Location
    ]
    
    for node_type in node_types:
        try:
            node = node_type.nodes.get(identifier=node_id)
            return node
        except node_type.DoesNotExist:
            continue
    
    return None