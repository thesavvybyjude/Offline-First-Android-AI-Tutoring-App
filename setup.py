"""
Setup script for AI Tutor
"""

from setuptools import setup, find_packages

setup(
    name="ai-tutor",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "llama-cpp-python==0.2.57",
        "sentence-transformers==2.2.2",
        "faiss-cpu==1.7.4",
        "numpy==1.24.3",
        "Flask==3.0.0",
        "Flask-CORS==4.0.0",
        "Jinja2==3.1.2",
        "PyMuPDF==1.23.8",
        "pdfplumber==0.10.3",
        "kivy==2.3.0",
        "kivymd==1.2.0",
    ],
    python_requires=">=3.11",
)
