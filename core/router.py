import os
import json
import google.generativeai as genai
from typing import Dict, Any
from dotenv import load_dotenv

class AdaptiveQueryRouter:
    """
    Classifies user query intent and dynamically routes the execution pipeline.
    """
    def __init__(self):
        # Configure Gemini if API key is present
        self.api_key_set = False
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-flash-lite-latest")
            self.api_key_set = True
            print("Router initialized with Gemini API.")
        else:
            print("Router initialized with Local Fallback (No GEMINI_API_KEY found).")

    def route_query_local_fallback(self, query: str) -> Dict[str, Any]:
        """
        Rule-based classifier in case the Gemini API is unavailable.
        """
        query_lower = query.lower()
        
        # Simple greetings or conversation
        greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "who are you", "what can you do"]
        if any(g.startswith(query_lower) or query_lower.startswith(g) for g in greetings):
            return {
                "intent": "chitchat",
                "retrieve": False,
                "reasoning": "Local rule-based fallback detected chitchat/greeting keywords."
            }
            
        # Summarization requests
        summarization_keywords = ["summarize", "summary", "tl;dr", "overview of", "main points", "executive summary"]
        if any(keyword in query_lower for keyword in summarization_keywords):
            return {
                "intent": "summarization",
                "retrieve": True,
                "reasoning": "Local rule-based fallback detected summarization keywords."
            }
            
        # Analytical / Comparison requests
        analytical_keywords = ["compare", "difference", "versus", "vs", "analyze", "math", "total", "average", "increase", "decrease"]
        if any(keyword in query_lower for keyword in analytical_keywords):
            return {
                "intent": "analytical",
                "retrieve": True,
                "reasoning": "Local rule-based fallback detected analytical or comparative keywords."
            }
            
        # Default is factual retrieval
        return {
            "intent": "factual",
            "retrieve": True,
            "reasoning": "Local rule-based fallback defaulted to factual retrieval query."
        }

    def route_query(self, query: str) -> Dict[str, Any]:
        """
        Routes the query using LLM intent classification, fallback to local rules if needed.
        """
        # If API key is not configured, use local fallback
        if not self.api_key_set or not os.getenv("GEMINI_API_KEY"):
            # Try reloading key dynamically in case it was set later
            load_dotenv(override=True)
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel("gemini-flash-lite-latest")
                self.api_key_set = True
            else:
                return self.route_query_local_fallback(query)

        prompt = f"""
        You are an intelligent query routing agent for a Retrieval-Augmented Generation (RAG) system.
        Analyze the following query and classify it into one of these intents:
        - "factual": Specific requests for detailed facts, figures, or statements in the documents.
        - "analytical": Comparison between points, mathematical calculations, trends analysis, or multi-document aggregation.
        - "summarization": High-level requests asking for an overview of the entire document or entire pages.
        - "chitchat": Greetings, jokes, user feelings, or questions completely unrelated to document contents.

        Also decide if the system needs to retrieve documents to answer (retrieve is true for factual, analytical, and summarization; false for chitchat).

        Respond ONLY with a raw JSON object containing these keys: "intent" (string), "retrieve" (boolean), "reasoning" (string).

        Query: "{query}"
        JSON:
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            data = json.loads(response.text.strip())
            return {
                "intent": data.get("intent", "factual"),
                "retrieve": data.get("retrieve", True),
                "reasoning": data.get("reasoning", "LLM classified query.")
            }
        except Exception as e:
            print(f"Error calling Gemini in Router: {e}")
            return self.route_query_local_fallback(query)

if __name__ == "__main__":
    router = AdaptiveQueryRouter()
    print(router.route_query("Hello there!"))
    print(router.route_query("Compare the revenue reports for Q1 and Q3."))
