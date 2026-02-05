from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel
import json
import os
from typing import List, Dict, Any

# Initialize Vertex AI
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "jnu-rise-edu-134")
LOCATION = "us-central1"
aiplatform.init(project=PROJECT_ID, location=LOCATION)

# Load Metadata into Memory (Hackathon Optimization)
# In production, use Firestore or Redis
METADATA_FILE = "vertex_vectors_metadata.json"
metadata_store = {}

def load_metadata():
    global metadata_store
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                metadata_store = json.load(f)
            print(f"✅ Loaded metadata for {len(metadata_store)} items.")
        except Exception as e:
            print(f"❌ Failed to load metadata: {e}")
    else:
        print(f"⚠️ Metadata file {METADATA_FILE} not found. Search results will be empty.")

# Load on module import
load_metadata()

def search_vector_db(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Embeds the query and searches the Vertex AI Vector Search Index.
    """
    INDEX_ENDPOINT_ID = os.getenv("VERTEX_INDEX_ENDPOINT_ID")
    DEPLOYED_INDEX_ID = os.getenv("VERTEX_DEPLOYED_INDEX_ID", "gwangju_places_index")
    
    if not INDEX_ENDPOINT_ID:
        print("❌ VERTEX_INDEX_ENDPOINT_ID not set.")
        return []

    try:
        # 1. Generate Query Embedding
        model = TextEmbeddingModel.from_pretrained("text-multilingual-embedding-002")
        embeddings = model.get_embeddings([query])
        query_vector = embeddings[0].values

        # 2. Search Index Endpoint
        # Note: This assumes the Endpoint is already created and Index is deployed.
        # This operation connects to the remote GCP service.
        index_endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=INDEX_ENDPOINT_ID,
            project=PROJECT_ID,
            location=LOCATION
        )
        
        response = index_endpoint.find_neighbors(
            deployed_index_id=DEPLOYED_INDEX_ID,
            queries=[query_vector],
            num_neighbors=limit
        )
        
        # 3. Map Results to Metadata
        results = []
        if response:
            for neighbor in response[0]: # response[0] corresponds to the first query
                place_id = neighbor.id
                if place_id in metadata_store:
                    item = metadata_store[place_id].copy()
                    item['similarity_score'] = neighbor.distance
                    results.append(item)
                else:
                    # Fallback if metadata missing
                    results.append({"id": place_id, "score": neighbor.distance})
                    
        return results

    except Exception as e:
        print(f"❌ Vector Search Error: {e}")
        return []
