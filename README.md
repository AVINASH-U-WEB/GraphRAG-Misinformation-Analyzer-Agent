# 📈 GraphRAG Misinformation Analyzer API

This repository contains the backend service for the GraphRAG Misinformation Analyzer, a powerful API designed to combat misinformation. It leverages a GraphRAG (Retrieval-Augmented Generation) architecture to build a dynamic knowledge graph of claims, sources, and entities from unstructured text.

The system uses the high-speed **Groq LLM API** for real-time information extraction and a **Neo4j AuraDB** instance for robust graph storage, enabling complex analysis of how information originates and spreads.

---

---

### ✨ Key Features

*   **Knowledge Graph Construction:** Automatically processes text and converts it into a rich, interconnected knowledge graph.
*   **AI-Powered Information Extraction:** Uses the high-speed Groq LLM API to extract key claims, named entities, and summaries.
*   **Graph-Based Analysis:** Stores all data in Neo4j AuraDB, enabling complex queries to trace information origin and spread.
*   **Batch Dataset Ingestion:** Can load and process entire datasets from Hugging Face for large-scale analysis and graph population.
*   **RESTful API-Driven:** A well-defined API for processing posts, loading datasets, and retrieving graph data.

---

### 🛠️ Technology Stack

*   **Framework:** Python 3.11+, Flask
*   **Data Validation:** Pydantic
*   **LLM Provider:** Groq API (interfacing with Llama 3)
*   **Database:** Neo4j AuraDB (Cloud Graph Database)
*   **AI/ML Libraries:** `langchain`, `langchain-groq`
*   **Graph Processing:** `neo4j` Python Driver
*   **Dataset Hub:** 🤗 Hugging Face `datasets` library

---

### 🚀 Getting Started

Follow these instructions to get a local copy of the backend up and running.

#### Prerequisites

*   Python 3.11+ and `pip`
*   Git
*   An active **Neo4j AuraDB** instance (free tier is sufficient)
*   A **Groq API Key**
*   A **Hugging Face User Access Token** (for accessing datasets)

#### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/<YOUR_GITHUB_USERNAME>/graphrag-misinformation-analyzer.git
    cd graphrag-misinformation-analyzer/backend
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    *   Create your environment file from the example:
        ```bash
        cp .env.example .env
        ```
    *   Open the newly created `.env` file and fill in your credentials:
        ```dotenv
        # Neo4j AuraDB Configuration
        NEO4J_URI="bolt://<your-aura-db-instance-id>.databases.neo4j.io"
        NEO4J_USERNAME="neo4j"
        NEO4J_PASSWORD="<your-aura-db-password>"

        # Groq API Configuration
        GROQ_API_KEY="<your-groq-api-key>"

        # Hugging Face Configuration
        HUGGINGFACE_TOKEN="<your-huggingface-token>"
        ```

#### Running the Application

1.  **Start the Backend Server:**
    ```bash
    # Ensure your virtual environment is activated
    flask run --host=0.0.0.0 --port=5000
    ```
    The backend API will be available at `http://localhost:5000`. For development with auto-reloading, you can use `flask run --debug`.

---

### 📋 API Endpoints

The API is structured to handle graph operations, analysis, and administrative tasks.

#### Core Graph Operations
| Endpoint | Method | Description | Body Example |
|---|---|---|---|
| `/api/graph/process-post` | `POST` | Processes a single text post and adds it to the knowledge graph. | `{"id": "...", "text": "...", "author": "..."}` |
| `/api/graph/load-dataset` | `POST` | Loads and processes a dataset from Hugging Face. | `{"dataset_name": "liar", "split": "train"}` |
| `/api/graph/post-graph/{id}`| `GET` | Retrieves graph data (nodes & links) for a specific post ID. | N/A |
| `/api/graph/post-summary/{id}`| `GET` | Retrieves the AI-generated summary and verdict for a post. | N/A |

#### Management Endpoints
| Endpoint | Method | Description |
|---|---|---|
| `/api/admin/health` | `GET` | Health check endpoint to verify the service is running. |
| `/api/admin/clear-data`| `POST`| **(Dev Only)** Clears all data from the Neo4j database. |

---

### 🗃️ Data Model & Schema

The knowledge graph follows a flexible schema designed to capture the relationships between posts, claims, authors, and entities.

*   `(Post)`: Represents the original piece of content (e.g., a tweet, an article snippet).
*   `(Author)`: The person or entity who created the post.
*   `(Claim)`: A verifiable statement extracted from a Post by the LLM.
*   `(Entity)`: A named entity (person, organization, location) mentioned in a Claim.
*   `(FactCheckVerdict)`: The truthfulness label assigned to a Post (e.g., 'True', 'False').
*   `(Timestamp)`: The publication date/time of the Post.

**Core Relationships:**
*   `(Author)-[:CREATED]->(Post)`
*   `(Post)-[:AT_TIME]->(Timestamp)`
*   `(Post)-[:CONTAINS_CLAIM]->(Claim)`
*   `(Post)-[:MENTIONS]->(Entity)`
*   `(Post)-[:HAS_VERDICT]->(FactCheckVerdict)`

---

### 📂 Project Structure

```backend/
├── app.py                 # Flask application entry point
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── services/              # External service integrations
│   ├── neo4j_service.py   # Neo4j database operations
│   └── groq_service.py    # Groq LLM integration
├── agents/                # Core processing logic
│   ├── graph_agent.py     # Main GraphRAG processing agent
│   └── dataset_loader.py  # Hugging Face dataset loading
├── routes/                # API route definitions
│   └── graph_routes.py    # Graph operations endpoints
├── models/                # Pydantic data validation models
│   └── graph_models.py    # API request/response models
└── utils/                 # Utility functions
    └── helpers.py         # General helper functions (text cleaning, etc.)
```

---

### 🧪 API Testing with `curl`

You can test the API endpoints directly from your terminal.

1.  **Test the Health Check:**
    ```bash
    curl http://localhost:5000/
    ```

2.  **Test Single Post Processing:**
    ```bash
    curl -X POST http://localhost:5000/api/graph/process-post \
      -H "Content-Type: application/json" \
      -d '{"id": "test-post-001", "text": "A new study shows coffee is made from solid light.", "author": "Dr. Science"}'
    ```

3.  **Test Graph Retrieval:**
    ```bash
    curl http://localhost:5000/api/graph/post-graph/test-post-001
    ```

4.  **Test Dataset Loading (example with `liar` dataset):**
    ```bash
    curl -X POST http://localhost:5000/api/graph/load-dataset \
      -H "Content-Type: application/json" \
      -d '{"dataset_name": "liar", "split": "test"}'
    ```

---

### 🚢 Deployment

The application is designed to be deployed in a containerized environment.

1.  **Build the Docker Image:**
    ```bash
    docker build -t graphrag-api ./backend
    ```

2.  **Run the Docker Container:**
    *   Make sure to provide the environment variables.
    ```bash
    docker run -p 5000:5000 \
      -e NEO4J_URI="<your-prod-uri>" \
      -e NEO4J_USERNAME="neo4j" \
      -e NEO4J_PASSWORD="<your-prod-password>" \
      -e GROQ_API_KEY="<your-prod-key>" \
      -e HUGGINGFACE_TOKEN="<your-prod-token>" \
      graphrag-api
    ```

---

### 🐛 Troubleshooting

*   **Neo4j Connection Issues:** Verify your AuraDB instance is running and not paused. Double-check all credentials in your `.env` file.
*   **Groq API Errors:** Check your API key and monitor your usage on the GroqCloud dashboard to ensure you have not exceeded your rate limits.
*   **Module Import Errors:** Ensure all dependencies from `requirements.txt` are installed and your Python virtual environment is activated.

---

### 📜 License

This project is licensed under the MIT License - see the `LICENSE` file for details.
