"""
Neomodel schema definitions for Badevel Living Lab nodes and relationships.
This file defines the data model structure for the Neo4j database.
"""
from neomodel import (
    StructuredNode, StringProperty, FloatProperty, 
    RelationshipTo, RelationshipFrom, StructuredRel,
    config, db, UniqueIdProperty, JSONProperty
)
import os
from dotenv import load_dotenv

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


# Define node models
class Application(StructuredNode):
    """Application node model for software applications"""
    uid = UniqueIdProperty()
    identifier = StringProperty(unique_index=True, required=True)  # Renamed from 'id'
    name = StringProperty(required=True)
    
    # Relationships
    modules = RelationshipTo('Module', 'USES', model=BaseRelationship)


class Department(StructuredNode):
    """Department node model for organizational units"""
    uid = UniqueIdProperty()
    identifier = StringProperty(unique_index=True, required=True)  # Renamed from 'id'
    name = StringProperty(required=True)
    
    # Relationships
    locations = RelationshipTo('Location', 'MANAGES', model=BaseRelationship)


class Manufacturer(StructuredNode):
    """Manufacturer node model for companies making IoT devices"""
    uid = UniqueIdProperty()
    identifier = StringProperty(unique_index=True, required=True)  # Renamed from 'id'
    name = StringProperty(required=True)
    
    # Relationships
    things = RelationshipTo('Thing', 'MAKES', model=BaseRelationship)


class Module(StructuredNode):
    """Module node model for software components"""
    uid = UniqueIdProperty()
    identifier = StringProperty(unique_index=True, required=True)  # Renamed from 'id'
    name = StringProperty(required=True)
    
    # Relationships
    applications = RelationshipFrom('Application', 'USES', model=BaseRelationship)
    things = RelationshipTo('Thing', 'PROCESSES_DATA_FROM', model=BaseRelationship)


class Network(StructuredNode):
    """Network node model for communication networks"""
    uid = UniqueIdProperty()
    identifier = StringProperty(unique_index=True, required=True)  # Renamed from 'id'
    entType = StringProperty()
    name = StringProperty(required=True)
    
    # Relationships
    things = RelationshipTo('Thing', 'CONNECTS', model=BaseRelationship)


class Power(StructuredNode):
    """Power node model for energy sources"""
    uid = UniqueIdProperty()
    identifier = StringProperty(unique_index=True, required=True)  # Renamed from 'id'
    name = StringProperty(required=True)
    
    # Relationships
    things = RelationshipTo('Thing', 'POWERS', model=BaseRelationship)


class Sensor(StructuredNode):
    """Sensor node model for measurement devices"""
    uid = UniqueIdProperty()
    identifier = StringProperty(unique_index=True, required=True)  # Renamed from 'id'
    entType = StringProperty()
    name = StringProperty(required=True)
    unit = StringProperty()
    description = StringProperty()
    
    # Relationships
    things = RelationshipFrom('Thing', 'HAS_SENSOR', model=BaseRelationship)


class Thing(StructuredNode):
    """Thing node model for IoT devices"""
    uid = UniqueIdProperty()
    identifier = StringProperty(unique_index=True, required=True)  # Renamed from 'id'
    name = StringProperty(required=True)
    lat = FloatProperty()
    lon = FloatProperty()
    latest_value = StringProperty()
    
    # Relationships
    location = RelationshipTo('Location', 'LOCATED_AT', model=BaseRelationship)
    type = RelationshipTo('ThingType', 'IS_TYPE', model=BaseRelationship)
    sensors = RelationshipTo('Sensor', 'HAS_SENSOR', model=BaseRelationship)
    power_source = RelationshipTo('Power', 'POWERED_BY', model=BaseRelationship)
    network = RelationshipTo('Network', 'CONNECTED_VIA', model=BaseRelationship)
    manufactured_by = RelationshipTo('Manufacturer', 'MANUFACTURED_BY', model=BaseRelationship)
    vendor = RelationshipTo('Vendor', 'SOLD_BY', model=BaseRelationship)
    modules = RelationshipFrom('Module', 'PROCESSES_DATA_FROM', model=BaseRelationship)


class ThingType(StructuredNode):
    """ThingType node model for categories of IoT devices"""
    uid = UniqueIdProperty()
    identifier = StringProperty(unique_index=True, required=True)  # Renamed from 'id'
    name = StringProperty(required=True)
    
    # Relationships
    things = RelationshipFrom('Thing', 'IS_TYPE', model=BaseRelationship)


class Vendor(StructuredNode):
    """Vendor node model for suppliers of IoT devices"""
    uid = UniqueIdProperty()
    identifier = StringProperty(unique_index=True, required=True)  # Renamed from 'id'
    entType = StringProperty()
    name = StringProperty(required=True)
    
    # Relationships
    things = RelationshipFrom('Thing', 'SOLD_BY', model=BaseRelationship)


class Location(StructuredNode):
    """Location node model for physical places"""
    uid = UniqueIdProperty()
    identifier = StringProperty(unique_index=True, required=True)  # Renamed from 'id'
    name = StringProperty(required=True)
    
    # Relationships
    things = RelationshipFrom('Thing', 'LOCATED_AT', model=BaseRelationship)
    department = RelationshipFrom('Department', 'MANAGES', model=BaseRelationship)


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