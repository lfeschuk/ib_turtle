import sys

try:
    import pypdf
    print("pypdf installed")
except ImportError:
    print("pypdf NOT installed")

try:
    import pdfplumber
    print("pdfplumber installed")
except ImportError:
    print("pdfplumber NOT installed")

try:
    import fitz # PyMuPDF
    print("fitz installed")
except ImportError:
    print("fitz NOT installed")
