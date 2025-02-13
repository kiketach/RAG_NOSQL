from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
import os

def analyze_local_document(file_path):
    """Procesa un archivo local con Azure Document Intelligence."""
    document_intelligence_client = DocumentIntelligenceClient(
        endpoint=os.getenv("AZURE_ENDPOINT"),
        credential=AzureKeyCredential(os.getenv("AZURE_KEY"))
    )
    with open(file_path, "rb") as file:
        file_bytes = file.read()
    poller = document_intelligence_client.begin_analyze_document("prebuilt-layout", file_bytes)
    result = poller.result()
    return result