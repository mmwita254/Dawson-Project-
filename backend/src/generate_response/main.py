import os
import json
import boto3
from aws_lambda_powertools import Logger
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_community.chat_message_histories import DynamoDBChatMessageHistory
from langchain_community.vectorstores import FAISS
from langchain_openai.chat_models import ChatOpenAI  # Import ChatOpenAI
from langchain_openai.embeddings import OpenAIEmbeddings  # Import OpenAIEmbeddings

MEMORY_TABLE = os.environ["MEMORY_TABLE"]
BUCKET = os.environ["BUCKET"]
OPENAI_MODEL_ID = os.environ["OPENAI_MODEL_ID"]  # Change this variable for OpenAI model
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]  # Ensure you set your OpenAI API key

s3 = boto3.client("s3")
logger = Logger()


def get_embeddings():
    # Initialize OpenAI embeddings
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    return embeddings

def get_faiss_index(embeddings, user, file_name):
    s3.download_file(BUCKET, f"{user}/{file_name}/index.faiss", "/tmp/index.faiss")
    s3.download_file(BUCKET, f"{user}/{file_name}/index.pkl", "/tmp/index.pkl")
    faiss_index = FAISS.load_local("/tmp", embeddings, allow_dangerous_deserialization=True)
    return faiss_index

def create_memory(conversation_id):
    message_history = DynamoDBChatMessageHistory(
        table_name=MEMORY_TABLE, session_id=conversation_id
    )

    memory = ConversationBufferMemory(
        memory_key="chat_history",
        chat_memory=message_history,
        input_key="question",
        output_key="answer",
        return_messages=True,
    )
    return memory

def openai_chain(faiss_index, memory, human_input):
    chat = ChatOpenAI(
        model_name=OPENAI_MODEL_ID,  # Use OpenAI model ID
        model_kwargs={'temperature': 0.0},
    )

    chain = ConversationalRetrievalChain.from_llm(
        llm=chat,
        chain_type="stuff",
        retriever=faiss_index.as_retriever(),
        memory=memory,
        return_source_documents=True,
    )

    response = chain.invoke({"question": human_input})

    return response

@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    event_body = json.loads(event["body"])
    file_name = event_body["fileName"]
    human_input = event_body["prompt"]
    conversation_id = event["pathParameters"]["conversationid"]
    user = event["requestContext"]["authorizer"]["claims"]["sub"]

    embeddings = get_embeddings()
    faiss_index = get_faiss_index(embeddings, user, file_name)
    memory = create_memory(conversation_id)

    response = openai_chain(faiss_index, memory, human_input)
    if response:
        print(f"{OPENAI_MODEL_ID} -\nPrompt: {human_input}\n\nResponse: {response['answer']}")
    else:
        raise ValueError(f"Unsupported model ID: {OPENAI_MODEL_ID}")

    logger.info(str(response['answer']))

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
        },
        "body": json.dumps(response['answer']),
    }