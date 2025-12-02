"""
File parser for project descriptions.
Supports PDF, Word (.docx), and plain text files.
"""

import os
from pathlib import Path
from typing import Optional


class FileParser:
    """Parse project description files in various formats."""
    
    def __init__(self):
        self.supported_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md'}
    
    def parse(self, file_path: str) -> Optional[str]:
        """
        Parse a project description file.
        
        Args:
            file_path: Path to the file (PDF, Word, or text)
            
        Returns:
            Extracted text content or None if parsing fails
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        extension = path.suffix.lower()
        
        if extension not in self.supported_extensions:
            raise ValueError(
                f"Unsupported file type: {extension}. "
                f"Supported types: {', '.join(self.supported_extensions)}"
            )
        
        try:
            if extension == '.pdf':
                return self._parse_pdf(path)
            elif extension in {'.docx', '.doc'}:
                return self._parse_word(path)
            else:  # .txt, .md
                return self._parse_text(path)
        except Exception as e:
            raise Exception(f"Error parsing file {file_path}: {str(e)}")
    
    def _parse_pdf(self, path: Path) -> str:
        """Parse PDF file using PyPDF2 or pdfplumber."""
        try:
            import pdfplumber
            text = ""
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text.strip()
        except ImportError:
            try:
                import PyPDF2
                text = ""
                with open(path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                return text.strip()
            except ImportError:
                raise ImportError(
                    "PDF parsing requires either 'pdfplumber' or 'PyPDF2'. "
                    "Install with: pip install pdfplumber"
                )
    
    def _parse_word(self, path: Path) -> str:
        """Parse Word document using python-docx."""
        try:
            from docx import Document
            doc = Document(path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
        except ImportError:
            raise ImportError(
                "Word document parsing requires 'python-docx'. "
                "Install with: pip install python-docx"
            )
    
    def _parse_text(self, path: Path) -> str:
        """Parse plain text file."""
        with open(path, 'r', encoding='utf-8') as file:
            return file.read().strip()

