import os
import fitz  # PyMuPDF
from typing import List, Dict, Any

class LayoutAwarePDFParser:
    """
    Extracts text and tables from PDFs page-by-page while preserving structural integrity
    and maintaining page and coordinate metadata.
    """
    def __init__(self):
        pass

    def extract_tables_from_page(self, page) -> List[Dict[str, Any]]:
        """
        Detects and extracts tables on a page, formatting them as Markdown tables.
        """
        extracted_tables = []
        try:
            tables = page.find_tables()
            for i, table in enumerate(tables):
                bbox = table.bbox  # Bounding box [x0, y0, x1, y1]
                data = table.extract()
                
                if not data or len(data) == 0:
                    continue
                
                # Format table data into Markdown
                headers = [str(h) if h is not None else "" for h in data[0]]
                markdown_lines = []
                
                # Header row
                markdown_lines.append("| " + " | ".join(headers) + " |")
                # Separator row
                markdown_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
                
                # Data rows
                for row in data[1:]:
                    cleaned_row = [str(cell).replace("\n", " ").strip() if cell is not None else "" for cell in row]
                    # Ensure row has same column count as header
                    if len(cleaned_row) < len(headers):
                        cleaned_row += [""] * (len(headers) - len(cleaned_row))
                    elif len(cleaned_row) > len(headers):
                        cleaned_row = cleaned_row[:len(headers)]
                    markdown_lines.append("| " + " | ".join(cleaned_row) + " |")
                
                markdown_table = "\n".join(markdown_lines)
                extracted_tables.append({
                    "text": f"Table structure found on page {page.number + 1}:\n\n{markdown_table}",
                    "type": "table",
                    "bbox": list(bbox)
                })
        except Exception as e:
            print(f"Error extracting tables on page {page.number}: {e}")
            
        return extracted_tables

    def parse_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parses a PDF file and returns a list of chunks, preserving page numbers,
        structural layouts (paragraphs vs. tables), and coordinate information.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        doc = fitz.open(file_path)
        filename = os.path.basename(file_path)
        chunks = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # 1. Extract and format tables on this page
            tables = self.extract_tables_from_page(page)
            table_bboxes = [t["bbox"] for t in tables]
            
            # Add table chunks
            for table in tables:
                chunks.append({
                    "text": table["text"],
                    "metadata": {
                        "source": filename,
                        "page": page_num + 1,
                        "type": "table",
                        "bbox": table["bbox"]
                    }
                })
                
            # 2. Extract layout-aware blocks of text (excluding table areas if possible)
            blocks = page.get_text("blocks")
            # blocks format: (x0, y0, x1, y1, "text", block_no, block_type)
            
            for block in blocks:
                x0, y0, x1, y1, text, block_no, block_type = block
                text = text.strip()
                
                if not text or len(text) < 15:
                    continue  # Skip header/footer snippets, page numbers, or empty blocks
                
                # Check if this text block overlaps significantly with a table
                is_inside_table = False
                for t_bbox in table_bboxes:
                    # Simple overlap detection (overlap if bounds intersect)
                    tx0, ty0, tx1, ty1 = t_bbox
                    # Check if bounding box centers overlap or if text block is fully inside table
                    overlap_x = max(0, min(x1, tx1) - max(x0, tx0))
                    overlap_y = max(0, min(y1, ty1) - max(y0, ty0))
                    if (overlap_x * overlap_y) > 0.5 * (x1 - x0) * (y1 - y0):
                        is_inside_table = True
                        break
                        
                if is_inside_table:
                    continue  # Table content is already captured cleanly in the markdown table representation
                
                chunks.append({
                    "text": text,
                    "metadata": {
                        "source": filename,
                        "page": page_num + 1,
                        "type": "text",
                        "bbox": [x0, y0, x1, y1]
                    }
                })
                
        doc.close()
        return chunks

# Test parser script
if __name__ == "__main__":
    # Example execution if run directly
    parser = LayoutAwarePDFParser()
    print("Parser initialized.")
