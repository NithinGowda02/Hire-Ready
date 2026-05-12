import pdfplumber
import docx
import io

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text content from PDF file."""
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text content from DOCX file."""
    doc = docx.Document(io.BytesIO(file_bytes))
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def parse_resume_file(file, filename: str) -> str:
    """Parse resume file and return text content."""
    file_bytes = file.read()

    if filename.lower().endswith('.pdf'):
        return extract_text_from_pdf(file_bytes)
    elif filename.lower().endswith(('.docx', '.doc')):
        return extract_text_from_docx(file_bytes)
    else:
        # Assume plain text
        return file_bytes.decode('utf-8', errors='ignore')