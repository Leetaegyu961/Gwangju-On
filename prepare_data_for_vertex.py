import json
import glob
import os
import time
from typing import List
from vertexai.language_models import TextEmbeddingModel

# Configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "jnu-rise-edu-134") # Replace with your project ID
LOCATION = "us-central1" # TextEmbeddingModel is available here
MODEL_NAME = "text-multilingual-embedding-002"

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Generates embeddings for a list of texts."""
    model = TextEmbeddingModel.from_pretrained(MODEL_NAME)
    embeddings = []
    
    # Vertex AI has a quota (e.g. 1500 requests/min). Batching helps.
    batch_size = 5
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        try:
            vectors = model.get_embeddings(batch)
            embeddings.extend([v.values for v in vectors])
            # Rate limiting
            time.sleep(0.5) 
        except Exception as e:
            print(f"Error embedding batch {i}: {e}")
            # Fill with zeros or handle error
            embeddings.extend([[0.0]*768] * len(batch))
            
    return embeddings

def process_files(input_files: List[str], output_file: str):
    all_records = []
    
    # 1. Collect all texts
    for filepath in input_files:
        if not os.path.exists(filepath):
            print(f"Skipping {filepath} (not found)")
            continue
            
        print(f"Reading {filepath}...")
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        places = data.get('places', []) if isinstance(data, dict) else data
        
        for idx, place in enumerate(places):
            place_name = place.get('place_name', 'Unknown')
            keywords = place.get('keywords', {})
            
            # Construct rich text for embedding
            text_parts = [f"장소명: {place_name}"]
            
            if keywords.get('menu_type'):
                text_parts.append(f"메뉴: {', '.join(keywords['menu_type'])}")
            if keywords.get('signature_menu'):
                text_parts.append(f"대표메뉴: {', '.join(keywords['signature_menu'])}")
            if keywords.get('ambiance'):
                text_parts.append(f"분위기: {', '.join(keywords['ambiance'])}")
            if keywords.get('special_features'):
                text_parts.append(f"특징: {', '.join(keywords['special_features'])}")
                
            text_content = " ".join(text_parts)
            
            # Safe ID (ASCII only)
            import hashlib
            file_key = os.path.basename(filepath).split('.')[0]
            safe_id = hashlib.md5(f"{file_key}_{idx}".encode('utf-8')).hexdigest()
            
            all_records.append({
                "id": safe_id,
                "text": text_content,
                "metadata": {
                    "place_name": place_name,
                    "region": data.get('region', 'Unknown'),
                    # Store original keywords for display
                    "keywords": json.dumps(keywords, ensure_ascii=False)
                }
            })
    
    print(f"Total records to embed: {len(all_records)}")
    
    # 2. Generate Embeddings
    texts = [r['text'] for r in all_records]
    # Note: This requires Vertex AI API enabled and credentials set
    print("Generating embeddings (this may take a while)...")
    try:
        embeddings = get_embeddings(texts)
    except Exception as e:
        print(f"Failed to generate embeddings: {e}")
        print("Please ensure 'gcloud auth application-default login' is run and API is enabled.")
        return

    # 3. Write to JSONL
    print(f"Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for record, vector in zip(all_records, embeddings):
            # Vertex AI Vector Search format
            vector_record = {
                "id": record['id'],
                "embedding": vector,
                # Optional: restricts for filtering
                "restricts": [
                    {"namespace": "region", "allow": [record['metadata']['region']]}
                ]
            }
            out_f.write(json.dumps(vector_record) + '\n')
            
    # Also save metadata mapping for backend retrieval
    meta_file = output_file.replace('.jsonl', '_metadata.json')
    with open(meta_file, 'w', encoding='utf-8') as meta_f:
        meta_map = {r['id']: r['metadata'] for r in all_records}
        json.dump(meta_map, meta_f, ensure_ascii=False, indent=2)
        
    print(f"Done! Vectors saved to {output_file}, Metadata to {meta_file}")

if __name__ == "__main__":
    files = [
        'extracted_keywords_cleaned_동명동.json',
        'extracted_keywords_시내권.json',
        'extracted_keywords_조대권.json'
    ]
    process_files(files, 'vertex_vectors.jsonl')
