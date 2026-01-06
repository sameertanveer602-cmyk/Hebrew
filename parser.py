import pdfplumber
import re
from typing import List, Dict, Any

class HebrewPDFParser:
    def __init__(self):
        # Hebrew character range
        self.hebrew_pattern = re.compile(r'[\u0590-\u05FF]')

    def is_hebrew(self, text: str) -> bool:
        if not text:
            return False
        return bool(self.hebrew_pattern.search(text))

    def fix_hebrew_text(self, text: str) -> str:
        """
        Processes text to be logical Hebrew.
        1. Joins fragmented lines.
        2. Reverses visual order to logical order.
        """
        if not text:
            return ""
        
        # Split into lines and process each
        lines = text.split('\n')
        fixed_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if majority is Hebrew or contains Hebrew
            if self.is_hebrew(line):
                # Reverse the whole line (Visual -> Logical)
                fixed_lines.append(line[::-1])
            else:
                fixed_lines.append(line)
        
        return "\n".join(fixed_lines)

    def table_to_markdown(self, table: List[List[str]]) -> str:
        if not table:
            return ""
        
        rows = []
        for row in table:
            # Clean and fix cells
            clean_cells = []
            for cell in row:
                if cell:
                    c = cell.strip().replace('\n', ' ')
                    clean_cells.append(self.fix_hebrew_text(c))
                else:
                    clean_cells.append("")
            rows.append("| " + " | ".join(clean_cells) + " |")
        
        if not rows:
            return ""
            
        # Add header separator
        num_cols = len(table[0]) if table else 0
        header_sep = "| " + " | ".join(["---"] * num_cols) + " |"
        rows.insert(1, header_sep)
        
        return "\n".join(rows)

    def extract_content(self, pdf_path: str) -> List[Dict[str, Any]]:
        results = []
        print(f"Loading {pdf_path}...")
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # We do NOT use layout=True as it fragments text too much
                # Instead, we extract directly and handle the reversal
                text = page.extract_text()
                
                if text:
                    fixed_text = self.fix_hebrew_text(text)
                    results.append({
                        "page": page_num + 1,
                        "type": "text",
                        "content": fixed_text
                    })
                
                # Extract tables
                tables = page.extract_tables()
                for i, table in enumerate(tables):
                    md_table = self.table_to_markdown(table)
                    results.append({
                        "page": page_num + 1,
                        "type": "table",
                        "content": md_table
                    })
                    
        return results

if __name__ == "__main__":
    parser = HebrewPDFParser()
    test_file = "1169_2011_food_information_HE.pdf"
    content = parser.extract_content(test_file)
    # Print Page 11 or 12 specifically to check "Name of Food"
    for item in content:
        if 10 <= item['page'] <= 15 and item['type'] == 'text':
            print(f"--- Page {item['page']} ---")
            print(item['content'][:500])
            print("-" * 50)
