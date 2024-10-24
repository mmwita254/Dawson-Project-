import os
import json
import boto3
import fitz  # PyMuPDF for image extraction
from PIL import Image
import io
import pytesseract  # For OCR on images
import tesseract
from aws_lambda_powertools import Logger
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai.embeddings import OpenAIEmbeddings

DOCUMENT_TABLE = os.environ["DOCUMENT_TABLE"]
BUCKET = os.environ["BUCKET"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb")
document_table = ddb.Table(DOCUMENT_TABLE)
logger = Logger()

def set_doc_status(user_id, document_id, status):
    document_table.update_item(
        Key={"userid": user_id, "documentid": document_id},
        UpdateExpression="SET docstatus = :docstatus",
        ExpressionAttributeValues={":docstatus": status},
    )

def extract_images_and_ocr_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    ocr_texts = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        images_in_page = page.get_images(full=True)
        
        for img_index, img in enumerate(images_in_page):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image = Image.open(io.BytesIO(image_bytes))
            
            # Perform OCR on the image
            ocr_text = pytesseract.image_to_string(image)
            ocr_texts.append({
                "page": page_num + 1,
                "text": ocr_text
            })
    
    return ocr_texts

@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    event_body = json.loads(event["Records"][0]["body"])
    document_id = event_body["documentid"]
    user_id = event_body["user"]
    key = event_body["key"]
    file_name_full = key.split("/")[-1]

    set_doc_status(user_id, document_id, "PROCESSING")

    # Download the file from S3
    s3.download_file(BUCKET, key, f"/tmp/{file_name_full}")

    # Load the document text using PyPDFLoader
    loader = PyPDFLoader(f"/tmp/{file_name_full}")
    docs = loader.load()

    # Add page number metadata for documents
    for i, doc in enumerate(docs):
        doc.metadata["page"] = i + 1

    # Extract and OCR text from images in the PDF
    ocr_texts = extract_images_and_ocr_from_pdf(f"/tmp/{file_name_full}")

    # Combine OCR text with the original text from PyPDFLoader
    combined_texts = docs + [ocr["text"] for ocr in ocr_texts]

    # Initialize OpenAI embeddings
    embeddings = OpenAIEmbeddings(
        openai_api_key=OPENAI_API_KEY,
        model="text-embedding-ada-002"
    )

    # Create FAISS vectorstore from combined text (original + OCR text)
    vectorstore = FAISS.from_texts(combined_texts, embeddings)

    # Save the FAISS index locally
    vectorstore.save_local("/tmp")

    # Upload the FAISS index to S3
    s3.upload_file(
        "/tmp/index.faiss", BUCKET, f"{user_id}/{file_name_full}/index.faiss"
    )
    s3.upload_file("/tmp/index.pkl", BUCKET, f"{user_id}/{file_name_full}/index.pkl")

    # Update the document status to "READY"
    set_doc_status(user_id, document_id, "READY")
