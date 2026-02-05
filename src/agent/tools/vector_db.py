import os
import json
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

# Load env
load_dotenv()

class LocalVectorDB:
    def __init__(self, index_path="faiss_index"):
        self.index_path = index_path
        self.vectorstore = None
        self._load_index()

    def _get_embeddings(self):
        # 1. Try Vertex AI
        try:
            from langchain_google_vertexai import VertexAIEmbeddings
            return VertexAIEmbeddings(model_name="text-multilingual-embedding-002")
        except: pass

        # 2. Try OpenAI
        try:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings()
        except: pass
        
        # 3. Try Gemini
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            api_key = os.getenv("GOOGLE_CLOUD_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if api_key:
                return GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
        except: pass

        raise ValueError("No suitable embedding provider found.")

    def _load_index(self):
        if not os.path.exists(self.index_path):
            print(f"[VectorDB] Index path {self.index_path} not found.")
            return

        try:
            embeddings = self._get_embeddings()
            self.vectorstore = FAISS.load_local(
                self.index_path, 
                embeddings, 
                allow_dangerous_deserialization=True
            )
            print(f"[VectorDB] Loaded index from {self.index_path}")
        except Exception as e:
            print(f"[VectorDB] Error loading index: {e}")

    async def search(self, query: str, k: int = 5):
        if not self.vectorstore:
            return []

        try:
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            parsed_results = []
            for doc, score in results:
                try:
                    info = json.loads(doc.metadata.get("info_json", "{}"))
                except:
                    info = {}
                
                parsed_results.append({
                    "place_name": doc.metadata.get("place_name"),
                    "score": float(score),
                    "data": info,
                    "content": doc.page_content
                })
            return parsed_results
        except Exception as e:
            print(f"[VectorDB] Search error: {e}")
            return []

vector_db = LocalVectorDB()
