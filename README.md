# Badevel Living Lab Assistant - Streamlit Version

A Streamlit-based chatbot interface for exploring the smart village data of Badevel through a Neo4j graph database.

## Features

- 🔍 Explore data from the digital twin of the village
- 💬 Ask questions in French or English about the village infrastructure
- 📊 Visualize relationships between different elements
- 📱 View real-time sensor measurements
- 🏢 Learn about buildings and their equipment

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file with the following variables:

```
# Azure OpenAI Configuration
OPENAI_API_BASE=https://your-azure-openai-endpoint
OPENAI_API_KEY=your-api-key
OPENAI_API_VERSION=2023-12-01-preview
OPENAI_ASSISTANT_ID=your-assistant-id
OPENAI_ASSISTANT_MODEL=gpt-4
OPENAI_WHISPER_MODEL=whisper-1

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

### 3. Create the Assistant

Run the following script to create the Azure OpenAI Assistant:

```bash
python create_assistant.py
```

Make sure to copy the generated Assistant ID to your `.env` file.

### 4. Import Data (if needed)

If you need to import data into Neo4j:

```bash
python data_import.py
```

### 5. Run the Application

```bash
streamlit run app.py
```

The application will be available at `http://localhost:8501`.

## Usage

1. Type your questions about the Badevel smart village in the text input field.
2. Click "Send" to submit your question.
3. View the assistant's response, which may include text, tables, or visualizations.
4. Use the example questions in the sidebar for ideas on what to ask.

## Architecture

This application uses:
- **Streamlit**: For the user interface
- **Azure OpenAI**: For natural language processing and reasoning
- **Neo4j**: For graph database storage and querying of the digital twin data
- **Matplotlib/NetworkX**: For data visualization

## Project Structure

- `app.py`: Main Streamlit application
- `neo4j_service.py`: Service for Neo4j database operations
- `models.py`: Neomodel schema definitions
- `create_assistant.py`: Script to create the Azure OpenAI Assistant
- `data_import.py`: Script to import data into Neo4j