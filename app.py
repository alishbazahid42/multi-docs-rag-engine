import os
import shutil
import json
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environmental variables (.env file)
load_dotenv()

# Import core RAG components
from core.indexer import VectorIndexer
from core.router import AdaptiveQueryRouter
from core.reranker import CrossEncoderReranker
from core.generator import GroundedGenerator

# Initialize FastAPI App
app = FastAPI(
    title="Adaptive Retrieval-Augmented Generation (Adaptive RAG) API",
    description="Backend API powering structured, layout-aware multi-document QA systems.",
    version="1.0.0"
)

# Enable CORS for local web testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
UPLOADS_DIR = "uploads"
STATIC_DIR = "static"
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Instantiate core components
# Using global instances so they keep in-memory state (FAISS and models)
print("Initializing core AI pipelines...")
indexer = VectorIndexer()
router = AdaptiveQueryRouter()
reranker = CrossEncoderReranker()
generator = GroundedGenerator()
print("All core pipelines successfully initialized.")

# Pydantic schemas
class QueryRequest(BaseModel):
    query: str
    history: Optional[List[Dict[str, str]]] = []

class QueryResponse(BaseModel):
    intent: str
    retrieve: bool
    reasoning: str
    answer: str
    citations: List[Dict[str, Any]]
    retrieved_chunks: List[Dict[str, Any]]

@app.post("/upload", response_model=Dict[str, Any])
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Uploads multiple PDF files, parses them layout-aware, and indexes them in the FAISS vector database.
    """
    uploaded_files = []
    total_chunks_indexed = 0
    
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF.")
            
        file_path = os.path.join(UPLOADS_DIR, file.filename)
        
        try:
            # Save PDF file locally
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            # Index document
            chunks_added = indexer.add_document(file_path)
            total_chunks_indexed += chunks_added
            uploaded_files.append({
                "filename": file.filename,
                "chunks_indexed": chunks_added,
                "status": "success"
            })
            
        except Exception as e:
            # Clean up if failed
            if os.path.exists(file_path):
                os.remove(file_path)
            uploaded_files.append({
                "filename": file.filename,
                "status": "failed",
                "error": str(e)
            })
            
    return {
        "message": f"Successfully processed {len(uploaded_files)} file(s).",
        "details": uploaded_files,
        "total_chunks_indexed": total_chunks_indexed
    }

@app.post("/query", response_model=QueryResponse)
async def query_system(payload: QueryRequest):
    """
    Accepts user queries, routes them adaptively, retrieves relevant paragraphs/tables,
    rerank them via Cross-Encoder, and generates grounded answers with citation references.
    """
    query = payload.query
    history = payload.history
    
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
        
    try:
        # Step 1: Query Intent Routing
        routing_decision = router.route_query(query)
        intent = routing_decision["intent"]
        retrieve_flag = routing_decision["retrieve"]
        reasoning = routing_decision["reasoning"]
        
        retrieved_chunks = []
        reranked_chunks = []
        
        # Step 2: Adaptive Retrieval
        if retrieve_flag:
            # Check if vector db is populated
            if len(indexer.chunks) == 0:
                # If no docs uploaded but retrieval is required, notify user
                return QueryResponse(
                    intent=intent,
                    retrieve=retrieve_flag,
                    reasoning=reasoning + " (Warning: No documents uploaded.)",
                    answer="You haven't uploaded any documents yet. Please upload PDF files to build the index before querying.",
                    citations=[],
                    retrieved_chunks=[]
                )
                
            # Perform Bi-Encoder retrieval based on query intent
            if intent == "summarization":
                # Broad retrieval to synthesize a document summary
                retrieved_chunks = indexer.search(query, top_k=25)
                reranked_chunks = reranker.rerank(query, retrieved_chunks, top_n=10)
            elif intent == "analytical":
                # Multi-point comparison queries
                retrieved_chunks = indexer.search(query, top_k=16)
                reranked_chunks = reranker.rerank(query, retrieved_chunks, top_n=6)
            else:
                # Factual / standard queries
                retrieved_chunks = indexer.search(query, top_k=12)
                reranked_chunks = reranker.rerank(query, retrieved_chunks, top_n=4)
            
        # Step 4: Grounded Generation
        # Context will be empty if retrieve_flag is False
        generation_response = generator.generate_answer(query, reranked_chunks, history)
        
        return QueryResponse(
            intent=intent,
            retrieve=retrieve_flag,
            reasoning=reasoning,
            answer=generation_response["answer"],
            citations=generation_response["citations"],
            retrieved_chunks=reranked_chunks
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/documents", response_model=List[str])
async def get_documents():
    """
    Lists all uploaded and indexed documents.
    """
    return indexer.get_all_documents()

@app.post("/clear", response_model=Dict[str, str])
async def clear_system():
    """
    Deletes all uploaded documents and clears the FAISS vector index.
    """
    try:
        # Clear indexer memory and FAISS
        indexer.clear()
        
        # Clear uploads folder
        if os.path.exists(UPLOADS_DIR):
            shutil.rmtree(UPLOADS_DIR)
            os.makedirs(UPLOADS_DIR, exist_ok=True)
            
        return {"status": "success", "message": "System database and uploads successfully cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear system: {str(e)}")

# --- RESEARCH PAPER ASSISTANT ENDPOINTS ---
insights_cache: Dict[str, Dict[str, Any]] = {}

class SetModelRequest(BaseModel):
    model_name: str

class InsightsRequest(BaseModel):
    filename: str

class CompareRequest(BaseModel):
    filenames: List[str]

@app.post("/set-model")
def set_model(payload: SetModelRequest):
    """
    Switches the Bi-Encoder model dynamically and re-indexes the existing corpus.
    Supported engines: 'MiniLM' (all-MiniLM-L6-v2) or 'SciBERT' (gsarti/scibert-nli).
    """
    global indexer
    try:
        model_name = payload.model_name
        allowed_models = {
            "MiniLM": "all-MiniLM-L6-v2",
            "SciBERT": "gsarti/scibert-nli"
        }
        actual_model_name = allowed_models.get(model_name, "all-MiniLM-L6-v2")
        
        print(f"Swapping embedding model to: {actual_model_name}")
        indexer = VectorIndexer(model_name=actual_model_name)
        
        # Re-index existing files automatically so search works immediately
        if os.path.exists(UPLOADS_DIR):
            for file in os.listdir(UPLOADS_DIR):
                if file.lower().endswith(".pdf"):
                    indexer.add_document(os.path.join(UPLOADS_DIR, file))
                    
        return {
            "status": "success",
            "model_name": model_name,
            "actual_model_name": actual_model_name,
            "message": f"Embeddings engine switched to {model_name}. Existing corpus re-indexed."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to switch embeddings model: {str(e)}")

@app.post("/extract-insights")
def extract_insights(payload: InsightsRequest):
    """
    Extracts structured academic research paper insights (problem, methodology, results, contributions)
    using layout-aware parsing and Gemini reasoning.
    """
    filename = payload.filename
    if filename in insights_cache:
        return insights_cache[filename]
        
    file_path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File {filename} not found.")
        
    try:
        # Load layout chunks (top chunks usually cover abstract/intro)
        raw_chunks = indexer.parser.parse_pdf(file_path)
        context_text = "\n".join([chunk["text"] for chunk in raw_chunks[:10]])
        
        prompt = f"""
        Analyze the following academic paper text and extract the key components in a clean, structured JSON format.
        
        Text excerpt:
        {context_text}
        
        Return ONLY a JSON object with these EXACT keys:
        - "title": The title of the research paper (detect from text)
        - "problem_statement": A concise 1-2 sentence description of the problem the paper addresses.
        - "methodology": A concise summary (1-2 sentences) of the proposed method, algorithm, or experimental setup.
        - "results": A concise description (1-2 sentences) of the key results, metrics, or performance outcomes.
        - "key_contributions": A bulleted list of 2-3 key scientific or engineering contributions.
        
        Do not output any markdown formatting like ```json or trailing text. Output ONLY the raw JSON string.
        """
        
        response = generator.model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Handle potential markdown wrapping
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        insights = json.loads(response_text)
        insights_cache[filename] = insights
        return insights
    except Exception as e:
        print(f"Error extracting insights for {filename}: {e}")
        # Return elegant fallback to prevent UI crash
        fallback_insights = {
            "title": filename,
            "problem_statement": "Problem statement extraction pending. Please ensure GEMINI_API_KEY is active.",
            "methodology": "Methodology extraction pending.",
            "results": "Results summary pending.",
            "key_contributions": ["Scientific paper index successfully initialized."]
        }
        return fallback_insights

@app.post("/compare-papers")
def compare_papers(payload: CompareRequest):
    """
    Compares multiple research papers and synthesizes a literature review matrix.
    """
    filenames = payload.filenames
    if not filenames:
        raise HTTPException(status_code=400, detail="Please select at least one paper to compare.")
        
    try:
        papers_insights = []
        for filename in filenames:
            insights = insights_cache.get(filename)
            if not insights:
                insights = extract_insights(InsightsRequest(filename=filename))
            papers_insights.append({
                "filename": filename,
                "insights": insights
            })
            
        formatted_papers = ""
        for i, paper in enumerate(papers_insights):
            formatted_papers += f"""
            Paper {i+1}: {paper['filename']}
            Title: {paper['insights'].get('title', paper['filename'])}
            Problem: {paper['insights'].get('problem_statement', '')}
            Method: {paper['insights'].get('methodology', '')}
            Results: {paper['insights'].get('results', '')}
            Contributions: {", ".join(paper['insights'].get('key_contributions', []))}
            
            """
            
        prompt = f"""
        You are an expert AI Research Assistant. You are given the extracted key metrics for the following papers:
        {formatted_papers}
        
        Please synthesize this information into:
        1. A Markdown comparison table with columns: [Paper Title, Core Methodology, Key Results, Unique Contributions].
        2. A concise 1-paragraph "Literature Review & Synthesis" that highlights how these papers compare, their relationships (e.g. does one build on another, or address a different angle), and which paper is best suited for different scenarios.
        
        Write clean, professional Markdown output.
        """
        
        response = generator.model.generate_content(prompt)
        return {
            "comparison_markdown": response.text,
            "papers": papers_insights
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare papers: {str(e)}")

# Mount static files (Frontend dashboard)
# Make sure this is mounted last to avoid overriding API routes
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
