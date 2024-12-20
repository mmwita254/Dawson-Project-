import os
import json
from datetime import datetime
import boto3
import PyPDF2
import shortuuid
import urllib
from aws_lambda_powertools import Logger
from zipfile import ZipFile

DOCUMENT_TABLE = os.environ["DOCUMENT_TABLE"]
MEMORY_TABLE = os.environ["MEMORY_TABLE"]
QUEUE = os.environ["QUEUE"]
BUCKET = os.environ["BUCKET"]

EXTRACTION_PATH = "/tmp/extracted_files"

ddb = boto3.resource("dynamodb")
document_table = ddb.Table(DOCUMENT_TABLE)
memory_table = ddb.Table(MEMORY_TABLE)
sqs = boto3.client("sqs")
s3 = boto3.client("s3")
logger = Logger()

def extract_zip_file(zip_file_path, extraction_path=EXTRACTION_PATH):
    """Extract PDF files from a ZIP and return their paths"""
    with ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(extraction_path)
    pdf_files = [os.path.join(extraction_path, f) for f in os.listdir(extraction_path) if f.endswith('.pdf')]
    return pdf_files

@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    for record in event["Records"]:
        try:
            key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
            split = key.split("/")
            user_id = split[0]
            file_name = split[1]

            document_id = shortuuid.uuid()
            temp_file_path = f"/tmp/{document_id}_{file_name}"

            s3.download_file(BUCKET, key, temp_file_path)

            """ with open(temp_file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                pages = str(len(reader.pages)) """

            if file_name.endswith('.zip'):
                # Handle ZIP file by extracting PDFs
                extracted_files = extract_zip_file(temp_file_path)
                pages = 0
                for pdf_path in extracted_files:
                    with open(pdf_path, "rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        pages += len(reader.pages)
            else:
                # Handle single PDF
                with open(temp_file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    pages = str(len(reader.pages))

            conversation_id = shortuuid.uuid()
            timestamp = datetime.utcnow()
            timestamp_str = timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            document = {
                "userid": user_id,
                "documentid": document_id,
                "filename": file_name,
                "created": timestamp_str,
                "pages": pages,
                "filesize": str(record["s3"]["object"]["size"]),
                "docstatus": "UPLOADED",
                "conversations": [],
            }

            conversation = {"conversationid": conversation_id, "created": timestamp_str}
            document["conversations"].append(conversation)

            document_table.put_item(Item=document)

            conversation_entry = {"SessionId": conversation_id, "History": []}
            memory_table.put_item(Item=conversation_entry)

            message = {
                "documentid": document_id,
                "key": key,
                "user": user_id,
            }
            sqs.send_message(QueueUrl=QUEUE, MessageBody=json.dumps(message))

        except Exception as e:
            logger.error(f"Error processing file {key}: {e}")
            continue
