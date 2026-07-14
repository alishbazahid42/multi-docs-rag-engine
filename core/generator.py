import os
import re
import google.generativeai as genai
from typing import List, Dict, Any
from dotenv import load_dotenv

class GroundedGenerator:
    """
    Generates citation-backed answers based on retrieved context chunks
    using the Gemini API, with a robust local fallback for demo purposes.
    """
    def __init__(self):
        self.api_key_set = False
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-flash-lite-latest")
            self.api_key_set = True
            print("Generator initialized with Gemini API.")
        else:
            print("Generator initialized with Local Demo Fallback (No GEMINI_API_KEY).")

    def mock_generation_fallback(self, query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generates a readable demo response when no GEMINI_API_KEY is present,
        synthesizing the retrieved passages with dummy text to show citations in the UI.
        """
        if not context_chunks:
            return {
                "answer": "Welcome to the Adaptive RAG System Demo! Please set the **GEMINI_API_KEY** environment variable in your terminal to enable real AI generation.\n\nCurrently running in offline/demo mode. No document context was found for your query.",
                "citations": []
            }
            
        # Synthesize a response from retrieved chunks for demo
        sources_used = []
        answer_parts = [
            f"**[Demo Mode - Set GEMINI_API_KEY for live answers]**\nBased on your retrieved documents, here is the synthesized information:\n"
        ]
        
        for i, chunk in enumerate(context_chunks):
            source = chunk["metadata"]["source"]
            page = chunk["metadata"]["page"]
            text_snippet = chunk["text"][:150].strip() + "..."
            
            answer_parts.append(
                f"- A relevant point is mentioned: \"*{text_snippet}*\" which is sourced from the document **{source}** on **Page {page}** [{source}: Page {page}]."
            )
            sources_used.append({
                "source": source,
                "page": page,
                "text": chunk["text"]
            })
            
        answer_parts.append("\nTo activate full reasoning and conversational memory, configure your API key.")
        return {
            "answer": "\n".join(answer_parts),
            "citations": sources_used
        }

    def generate_answer(self, query: str, context_chunks: List[Dict[str, Any]], history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Generates an answer from Gemini, enforcing formatting that includes citations,
        and parses out the citations for UI highlighting.
        """
        # Reload API key if set dynamically
        if not self.api_key_set or not os.getenv("GEMINI_API_KEY"):
            load_dotenv(override=True)
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel("gemini-flash-lite-latest")
                self.api_key_set = True
            else:
                return self.mock_generation_fallback(query, context_chunks)

        if not context_chunks:
            prompt = f"Answer the following user query directly: {query}"
            try:
                response = self.model.generate_content(prompt)
                return {
                    "answer": response.text,
                    "citations": []
                }
            except Exception as e:
                return {"answer": f"Error generating direct response: {e}", "citations": []}

        # 1. Format the context for prompt grounding
        context_str = ""
        for i, chunk in enumerate(context_chunks):
            source = chunk["metadata"]["source"]
            page = chunk["metadata"]["page"]
            context_str += f"--- CONTEXT CHUNK {i+1} ---\n"
            context_str += f"Source Document: {source}\n"
            context_str += f"Page Number: {page}\n"
            context_str += f"Content:\n{chunk['text']}\n\n"

        # 2. Format history if present
        history_str = ""
        if history:
            history_str = "\n--- CONVERSATION HISTORY ---\n"
            for msg in history:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_str += f"{role}: {msg['text']}\n"
            history_str += "\n"

        # 3. Create the grounding prompt
        system_instruction = """
        You are a highly capable AI Assistant running an Adaptive Retrieval-Augmented Generation (RAG) system.
        Your goal is to answer the user query accurately by using the provided Context Chunks.
        
        Strict Guidelines:
        1. Base your answer ONLY on the provided Context Chunks. Do not make up facts.
        2. You must cite your sources. For every statement you make that is backed by a chunk, append a citation in this exact format: `[DocumentName: Page PageNum]` at the end of the sentence. Example: "...resulting in a 25% year-over-year growth [report.pdf: Page 12]."
        3. If different chunks contain conflicting information, state the conflict clearly, referencing the pages.
        4. If the context does not contain enough information to answer, state that clearly, but try to provide any helpful adjacent information found in the context.
        """

        full_prompt = f"""
        {system_instruction}
        
        {history_str}
        --- RETRIEVED CONTEXT CHUNKS ---
        {context_str}
        
        User Query: {query}
        
        Generate your citation-backed response:
        """

        try:
            response = self.model.generate_content(full_prompt)
            answer = response.text
            
            # 4. Parse citations from generated answer text
            # Looking for patterns like [file.pdf: Page 3]
            citation_pattern = r"\[([^\]]+?):\s*Page\s*(\d+)\]"
            found_citations = re.findall(citation_pattern, answer)
            
            citations_metadata = []
            seen_citations = set()
            
            for doc_name, page_num in found_citations:
                page_val = int(page_num)
                citation_key = (doc_name, page_val)
                
                if citation_key not in seen_citations:
                    seen_citations.add(citation_key)
                    # Find matching chunk to pull the full text snippet
                    matching_text = ""
                    for chunk in context_chunks:
                        if chunk["metadata"]["source"] == doc_name and chunk["metadata"]["page"] == page_val:
                            matching_text = chunk["text"]
                            break
                    
                    citations_metadata.append({
                        "source": doc_name,
                        "page": page_val,
                        "text": matching_text or "Context reference"
                    })

            return {
                "answer": answer,
                "citations": citations_metadata
            }

        except Exception as e:
            print(f"Error calling Gemini in Generator: {e}")
            return self.mock_generation_fallback(query, context_chunks)

if __name__ == "__main__":
    generator = GroundedGenerator()
    print("Generator ready.")
