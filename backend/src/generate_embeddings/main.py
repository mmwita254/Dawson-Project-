import os
import json
import boto3
import io

from aws_lambda_powertools import Logger
from langchain_community.document_loaders import PyPDFLoader, PyPDFDirectoryLoader
from langchain_community.vectorstores import FAISS
from langchain_openai.embeddings import OpenAIEmbeddings
from zipfile import ZipFile

DOCUMENT_TABLE = os.environ["DOCUMENT_TABLE"]
BUCKET = os.environ["BUCKET"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# Initialize AWS services
s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb")
document_table = ddb.Table(DOCUMENT_TABLE)
logger = Logger()

def set_doc_status(user_id, document_id, status):
    """Update the document status in DynamoDB."""
    document_table.update_item(
        Key={"userid": user_id, "documentid": document_id},
        UpdateExpression="SET docstatus = :docstatus",
        ExpressionAttributeValues={":docstatus": status},
    )


def load_document_with_page_numbers(local_file_path):
    """Load PDF and add accurate page numbers."""
    loader = PyPDFLoader(local_file_path)
    docs = loader.load()

    # Add page number metadata
    for i, doc in enumerate(docs):
        doc.metadata["page"] = i + 1  # Ensure this accurately reflects PDF pages

    return docs

@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    """Lambda function handler to process PDF documents."""
    try:
        # Extracting information from the SQS event
        event_body = json.loads(event["Records"][0]["body"])
        document_id = event_body["documentid"]
        user_id = event_body["user"]
        key = event_body["key"]
        file_name_full = key.split("/")[-1]

        # Set document status to "PROCESSING"
        set_doc_status(user_id, document_id, "PROCESSING")

        # Download the file from S3
        local_file_path = f"/tmp/{file_name_full}"
        s3.download_file(BUCKET, key, local_file_path)

        # Load the document text using PyPDFLoader or PyPDFDirectoryLoader
        # docs = load_document_with_page_numbers(local_file_path)
        docs = []
        if file_name_full.endswith('.zip'):
            # Handle ZIP files containing multiple PDFs
            pdf_paths = extract_zip_file(local_file_path)
            for pdf_path in pdf_paths:
                docs += load_document_with_page_numbers(pdf_path)
        else:
            # Handle single PDF files
            docs = load_document_with_page_numbers(local_file_path)  

        # Extract text content from each Document object
        text_contents = [doc.page_content for doc in docs]

        # Initialize OpenAI embeddings
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, model="text-embedding-ada-002")

        # Create FAISS vectorstore from the extracted text contents
        vectorstore = FAISS.from_texts(text_contents, embeddings)

        # Save the FAISS index locally
        vectorstore.save_local("/tmp/index")

        # Upload the FAISS index to S3
        s3.upload_file("/tmp/index/index.faiss", BUCKET, f"{user_id}/{file_name_full}/index.faiss")
        s3.upload_file("/tmp/index/index.pkl", BUCKET, f"{user_id}/{file_name_full}/index.pkl")

        # Update the document status to "READY"
        set_doc_status(user_id, document_id, "READY")

    except Exception as e:
        logger.exception("Error processing document")
        set_doc_status(user_id, document_id, "FAILED")
        raise e