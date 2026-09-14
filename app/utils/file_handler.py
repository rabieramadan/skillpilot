import os
import mimetypes
from PIL import Image
import openpyxl
from typing import Dict, Any

# PDF text extraction, best library first. pypdf is the maintained successor
# to PyPDF2, which was abandoned in 2022; the old name is still accepted so an
# existing virtualenv keeps working without a reinstall.
try:
    import pypdf as _pypdf

    PYPDF2_AVAILABLE = True
except ImportError:
    try:
        import PyPDF2 as _pypdf

        PYPDF2_AVAILABLE = True
    except ImportError:
        PYPDF2_AVAILABLE = False
        _pypdf = None

#: A lecture PDF is routinely 40+ pages. The previous 10-page / 15,000-char
#: limits threw most of one away before a model ever saw it, and context
#: windows are now large enough that they bought nothing.
MAX_PDF_PAGES = 200
MAX_EXTRACTED_CHARS = 120_000

try:
    import pdfplumber

    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from docx import Document

    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class FileHandler:
    @staticmethod
    def extract_text(file_path: str) -> str:
        """Extract text content from various file types"""
        try:
            file_type, _ = mimetypes.guess_type(file_path)
            if not file_type:
                ext = os.path.splitext(file_path)[1].lower()
                file_type = FileHandler._get_mime_from_extension(ext)

            print(f"DEBUG: Extracting text from {file_path}, type: {file_type}")

            if file_type == 'text/plain':
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"DEBUG: Extracted {len(content)} characters from text file")
                    return content[:10000]  # Limit size

            elif file_type == 'application/pdf':
                return FileHandler._extract_pdf_text(file_path)

            elif file_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                return FileHandler._extract_docx_text(file_path)

            elif file_type == 'text/csv':
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"DEBUG: Extracted {len(content)} characters from CSV")
                    return content[:5000]

            else:
                return f"File type {file_type} is not supported for text extraction. File: {os.path.basename(file_path)}"

        except Exception as e:
            error_msg = f"Error extracting text from {os.path.basename(file_path)}: {str(e)}"
            print(f"DEBUG: {error_msg}")
            return error_msg

    @staticmethod
    def _extract_pdf_text(file_path: str) -> str:
        """Extract text from PDF using multiple methods"""
        print(f"DEBUG: Attempting to extract PDF text from {file_path}")

        # Method 1: Try pdfplumber first (better for complex PDFs)
        if PDFPLUMBER_AVAILABLE:
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    text = ""
                    for page_num, page in enumerate(pdf.pages[:MAX_PDF_PAGES]):
                        page_text = page.extract_text()
                        if page_text:
                            text += f"\n--- Page {page_num + 1} ---\n"
                            text += page_text

                    if text.strip():
                        print(f"DEBUG: PDFPlumber extracted {len(text)} characters")
                        return text[:MAX_EXTRACTED_CHARS]
            except Exception as e:
                print(f"DEBUG: PDFPlumber failed: {e}")

        # Method 2: Try PyPDF2
        if PYPDF2_AVAILABLE:
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = _pypdf.PdfReader(file)
                    text = ""

                    for page_num, page in enumerate(pdf_reader.pages[:MAX_PDF_PAGES]):
                        try:
                            page_text = page.extract_text()
                            if page_text.strip():
                                text += f"\n--- Page {page_num + 1} ---\n"
                                text += page_text
                        except Exception as page_error:
                            print(f"DEBUG: Error extracting page {page_num}: {page_error}")
                            continue

                    if text.strip():
                        print(f"DEBUG: PyPDF2 extracted {len(text)} characters")
                        return text[:MAX_EXTRACTED_CHARS]
                    else:
                        return "PDF appears to be image-based or encrypted. No text could be extracted."

            except Exception as e:
                print(f"DEBUG: PyPDF2 failed: {e}")

        # Method 3: Basic file info if extraction fails
        try:
            file_size = os.path.getsize(file_path)
            return f"PDF file '{os.path.basename(file_path)}' ({file_size} bytes) - Text extraction failed. This might be an image-based PDF or encrypted document."
        except Exception as e:
            return f"Could not process PDF file: {str(e)}"

    @staticmethod
    def _extract_docx_text(file_path: str) -> str:
        """Extract text from Word document"""
        if not DOCX_AVAILABLE:
            return "Word document support not available. Install python-docx."

        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"

            print(f"DEBUG: Extracted {len(text)} characters from DOCX")
            return text[:10000] if text.strip() else "Document appears to be empty or contains only images/tables."
        except Exception as e:
            return f"DOCX text extraction error: {str(e)}"

    @staticmethod
    def _get_mime_from_extension(ext: str) -> str:
        """Get MIME type from file extension"""
        extension_map = {
            '.txt': 'text/plain',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.csv': 'text/csv',
            '.json': 'application/json'
        }
        return extension_map.get(ext, 'application/octet-stream')