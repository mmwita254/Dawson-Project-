import os
import json
import boto3
from aws_lambda_powertools import Logger
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_community.chat_message_histories import DynamoDBChatMessageHistory
from langchain_community.vectorstores import FAISS
from langchain_openai.chat_models import ChatOpenAI
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain.prompts import PromptTemplate

MEMORY_TABLE = os.environ["MEMORY_TABLE"]
BUCKET = os.environ["BUCKET"]
OPENAI_MODEL_ID = os.environ["OPENAI_MODEL_ID"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

s3 = boto3.client("s3")
logger = Logger()

def get_embeddings():
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

# Define a prompt template
PROMPT_TEMPLATE = """You are a helpful assistant. 
The user is asking questions related to a document: "{file_name}". 
The user's question is: "{question}".
Please provide a detailed and accurate answer, and include relevant page numbers from the document when possible.
"""

def create_prompt(file_name, user_input):
    return PROMPT_TEMPLATE.format(file_name=file_name, question=user_input)

def openai_chain(faiss_index, memory, human_input, file_name):
    chat = ChatOpenAI(
        model_name=OPENAI_MODEL_ID,
        model_kwargs={'temperature': 0.0},
    )

    chain = ConversationalRetrievalChain.from_llm(
        llm=chat,
        retriever=faiss_index.as_retriever(),
        memory=memory,
        return_source_documents=True,
    )

    # Create the prompt using the template
    prompt = create_prompt(file_name, human_input)

    response = chain.invoke({"question": prompt})

    sources = response.get("source_documents", [])
    source_info = []

    for doc in sources:
        page = doc.metadata.get("page", "unknown")
        source_info.append(f"Page: {page}")

    response["source_info"] = source_info
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

    response = openai_chain(faiss_index, memory, human_input, file_name)

    if response:
        answer = response['answer']
        source_info = response.get("source_info", [])
        print(f"{OPENAI_MODEL_ID} -\nPrompt: {human_input}\n\nResponse: {answer}\nSource Info: {source_info}")
    else:
        raise ValueError(f"Unsupported model ID: {OPENAI_MODEL_ID}")

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
        },
        "body": json.dumps({
            "answer": response['answer'],
            "source_info": response.get("source_info", [])
        }),
    }
