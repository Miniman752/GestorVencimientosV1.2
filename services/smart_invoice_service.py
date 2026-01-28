import re
from datetime import datetime

class SmartInvoiceService:
    """
    Intelligent Invoice Parser (OCR-Lite).
    Extracts dates and amounts from text/pdf files using heuristics.
    """
    
    @staticmethod
    def parse_file(file_path: str) -> dict:
        """
        Attempts to read file and extract 'amount' and 'date'.
        Returns: {'amount': float, 'date': datetime.date, 'period': str, 'text': str}
        """
        text = ""
        try:
            # 1. Try PDF
            if file_path.lower().endswith(".pdf"):
                try:
                    import pypdf
                    reader = pypdf.PdfReader(file_path)
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                except ImportError:
                    # Fallback or error
                    pass # We will try basic text open next if pdftotext fails or library missing
                except Exception as e:
                    pass

            # 2. Try Text (if PDF failed or not PDF)
            if not text:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
        except:
            return None

        if not text: return None

        # Clean text
        text = text.replace("$", " ")
        
        return {
            "amount": SmartInvoiceService._extract_amount(text),
            "date": SmartInvoiceService._extract_date(text),
            "text": text[:500] # Snippet for debugging
        }

    @staticmethod
    def _extract_amount(text: str) -> float:
        # Regex for amounts: 1.234,56 or 1234.56
        # Focus on "Total" lines
        lines = text.split('\n')
        candidates = []
        
        for line in lines:
            line_lower = line.lower()
            if "total" in line_lower or "importe" in line_lower or "pagar" in line_lower:
                # Find numbers
                # Match 1.234,56
                matches = re.findall(r'(\d{1,3}(?:\.\d{3})*(?:,\d{2}))', line)
                if matches:
                    # Parse ARS format (dot=thousand, comma=decimal)
                    val = float(matches[0].replace('.','').replace(',','.'))
                    candidates.append(val)
                else:
                    # Match 1234.56
                    matches_us = re.findall(r'(\d+(?:\.\d{2}))', line)
                    if matches_us:
                        candidates.append(float(matches_us[0]))
        
        # Heuristic: Return the largest amount found (Total is usually the biggest number)
        if candidates:
            return max(candidates)
        return None

    @staticmethod
    def _extract_date(text: str) -> str:
        # Regex dd/mm/yyyy
        matches = re.findall(r'(\d{2}[/-]\d{2}[/-]\d{4})', text)
        if matches:
            # Take first one, usually issue date.
            try:
                d_str = matches[0].replace('-', '/')
                dt = datetime.strptime(d_str, "%d/%m/%Y").date()
                return dt
            except:
                pass
        return None


