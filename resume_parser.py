import PyPDF2
from io import BytesIO

def extract_text_from_pdf(uploaded_file) -> str:
    """
    Extracts text from a PDF file.
    
    Args:
        uploaded_file: A file-like object (e.g., from Streamlit file uploader).
        
    Returns:
        str: extracted text from the PDF.
    """
    try:
        # Check if the input is bytes or a file-like object
        if isinstance(uploaded_file, bytes):
            file_stream = BytesIO(uploaded_file)
        else:
            file_stream = uploaded_file

        pdf_reader = PyPDF2.PdfReader(file_stream)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return ""
