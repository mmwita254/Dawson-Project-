import os
import json
import boto3
from aws_lambda_powertools import Logger
from langchain.indexes import VectorstoreIndexCreator
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai.embeddings import OpenAIEmbeddings  # Import OpenAIEmbeddings

DOCUMENT_TABLE = os.environ["DOCUMENT_TABLE"]
BUCKET = os.environ["BUCKET"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]  # Ensure you set your OpenAI API key

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


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    event_body = json.loads(event["Records"][0]["body"])
    document_id = event_body["documentid"]
    user_id = event_body["user"]
    key = event_body["key"]
    file_name_full = key.split("/")[-1]

    set_doc_status(user_id, document_id, "PROCESSING")

    s3.download_file(BUCKET, key, f"/tmp/{file_name_full}")

    loader = PyPDFLoader(f"/tmp/{file_name_full}")

    # Initialize OpenAI embeddings
    embeddings = OpenAIEmbeddings(
        openai_api_key=OPENAI_API_KEY  # Pass the OpenAI API key
    )

    index_creator = VectorstoreIndexCreator(
        vectorstore_cls=FAISS,
        embedding=embeddings,
    )

    index_from_loader = index_creator.from_loaders([loader])

    index_from_loader.vectorstore.save_local("/tmp")

    s3.upload_file(
        "/tmp/index.faiss", BUCKET, f"{user_id}/{file_name_full}/index.faiss"
    )
    s3.upload_file("/tmp/index.pkl", BUCKET, f"{user_id}/{file_name_full}/index.pkl")

    set_doc_status(user_id, document_id, "READY")