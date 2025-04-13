import csv
import json
import requests
from io import StringIO

# Base GitHub raw URL
base_url = "https://raw.githubusercontent.com/josephazar/graph_of_things/main/Neo4jThings/"

# Files and their corresponding node types
files_with_types = {
    'applications.csv': 'Application',
    'departments.csv': 'Department',
    'manufacturers.csv': 'Manufacturer',
    'module.csv': 'Module',
    'network.csv': 'Network',
    'power.csv': 'Power',
    'sensors.csv': 'Sensor',
    'things.csv': 'Thing',
    'thingtype.csv': 'ThingType',
    'vendors.csv': 'Vendor',
    'locations.csv': 'Location'
}

# Step 1: Build identifier -> type mapping
id_to_type = {}

for filename, nodetype in files_with_types.items():
    url = base_url + filename
    response = requests.get(url)
    if response.status_code == 200:
        f = StringIO(response.text)
        reader = csv.DictReader(f)
        for row in reader:
            key = row.get('identifier') or row.get('name') or row.get('id')
            if key:
                id_to_type[key] = nodetype
    else:
        print(f"Failed to fetch {filename}")

# Step 2: Download and parse relation.csv
relations_url = base_url + "relation.csv"
response = requests.get(relations_url)
relations = []

if response.status_code == 200:
    f = StringIO(response.text)
    reader = csv.DictReader(f)
    for row in reader:
        src = row['thingId']
        rel = row['relationshipname']
        tgt = row['entityid']
        prop = row['prop']

        src_type = id_to_type.get(src, 'Thing')
        tgt_type = id_to_type.get(tgt, 'Unknown')

        # Create the base description
        desc = f"{src} is a {src_type} that has a relationship {rel} with {tgt}, which is a {tgt_type}."

        # Add semantic meaning based on relation type
        if rel == "IS_INSTALLED_IN":
            desc += " This indicates the physical location where the sensor or device is installed. The relationship includes metadata like installation and maintenance info."
        elif rel == "IS_POWERED_BY":
            desc += " This defines the power source or energy supply. The relationship may describe consumption, installation, or power characteristics."
        elif rel == "IS_USING":
            desc += " This specifies the network technology the device uses to communicate, including fields such as app ID or device ID."
        elif rel == "IS_COMPONENT_OF":
            desc += " This links the device to a specific sensor component and can include data ranges and current values."
        elif rel == "IS_FEEDING_DATA_TO":
            desc += " This relationship shows the application that receives data from the device."
        elif rel == "IS_CONTROLLING":
            desc += " This implies the source has control capabilities over the target, such as actuators or automated commands."
        elif rel == "IS_EQUIPPED_WITH":
            desc += " This specifies that the thing includes hardware components like modules or secondary sensors."
        elif rel == "IS_MANUFACTURED_BY":
            desc += " This shows who built the device or sensor."
        elif rel == "IS_FROM_VENDOR":
            desc += " This defines the vendor or supplier associated with the device."
        elif rel == "IS_OF_TYPE":
            desc += " This classifies the device under a certain functional type (e.g., energy monitoring, lighting, etc.)."
        elif rel == "IS_USED_BY":
            desc += " This shows the department or entity using or benefiting from the application."

        relations.append({
            "relation": f"{src},{rel},{tgt},\"{prop}\"",
            "description": desc
        })

    # Write the JSON file
    with open('relations.json', 'w', encoding='utf-8') as f_out:
        json.dump(relations, f_out, indent=2, ensure_ascii=False)

    print("✅ relations.json generated successfully with", len(relations), "entries.")
else:
    print("❌ Failed to fetch relation.csv")
