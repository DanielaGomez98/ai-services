import time
import json
import boto3
from app.utils.logger.logger_util import get_logger
from app.utils.s3.s3_util import read_document_from_s3
from app.utils.prompt.prompt_star import DEFAULT_PROMPT_STAR
from app.utils.prompt.prompt_prms import DEFAULT_PROMPT_PRMS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.utils.config.config_util import AWS, STAR_BUCKET_KEY_NAME, PRMS_BUCKET_KEY_NAME
from app.llm.vectorize_supabase import (get_embedding,
                               store_reference_embeddings,
                               store_temp_embeddings,
                               get_all_reference_data,
                               get_relevant_chunk,
                               initialize_supabase_tables,
                               get_connection
                               )


logger = get_logger()

bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    aws_access_key_id=AWS['aws_access_key'],
    aws_secret_access_key=AWS['aws_secret_key'],
    region_name='us-east-1'
)


def split_text(text):
    logger.info("✂️  Dividing the text into fragments...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=8000, chunk_overlap=1500)
    return text_splitter.split_text(text)


def invoke_model(prompt):
    try:
        logger.info("🚀 Invoking the model...")
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 3000,
            "temperature": 0.1,
            "top_k": 250,
            "top_p": 0.999,
            "stop_sequences": [],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{prompt}"}
                    ]
                }
            ]
        }
        response = bedrock_runtime.invoke_model(
            modelId="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        return json.loads(response['body'].read())['content'][0]['text']

    except Exception as e:
        logger.error(f"❌ Error invoking the model: {str(e)}")
        raise


def is_valid_json(text):
    """Check if the text is a valid JSON string"""
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


def initialize_reference_data(bucket_name, file_key_regions, file_key_countries):
    """Initialize reference data if it doesn't exist"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM reference_embeddings")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()

        if count == 2:
            logger.info("✅ Reference data already exists in the database. Skipping initialization.")
            return True
        
        logger.info("🔄 Initializing reference data...")

        document_content_regions = read_document_from_s3(
            bucket_name, file_key_regions)
        regions_embeddings = get_embedding(document_content_regions)

        document_content_countries = read_document_from_s3(
            bucket_name, file_key_countries)
        countries_embeddings = get_embedding(document_content_countries)

        store_reference_embeddings(document_content_regions, regions_embeddings)
        store_reference_embeddings(document_content_countries, countries_embeddings)

        logger.info("✅ Reference data initialized successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Error initializing reference data: {str(e)}")
        raise


def process_document(bucket_name, file_key, prompt=DEFAULT_PROMPT_STAR):
    start_time = time.time()

    try:
        reference_file_regions = f"{STAR_BUCKET_KEY_NAME}/clarisa_regions.xlsx"
        reference_file_countries = f"{STAR_BUCKET_KEY_NAME}/clarisa_countries.xlsx"
        initialize_supabase_tables()
        initialize_reference_data(
            bucket_name, reference_file_regions, reference_file_countries)

        document_content = read_document_from_s3(bucket_name, file_key)
        chunks = split_text(document_content)

        logger.info("#️⃣ Generating embeddings...")
        embeddings = [get_embedding(chunk) for chunk in chunks]

        document_name = store_temp_embeddings(chunks, embeddings, file_key)

        all_reference_data = get_all_reference_data()

        relevant_chunks = get_relevant_chunk(prompt, document_name)

        context = all_reference_data + relevant_chunks

        query = f"""
        Based on this context:\n{context}\n\n
        Answer the question:\n{prompt}
        """

        response_text = invoke_model(query)

        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"✅ Successfully generated response:\n{response_text}")
        logger.info(f"⏱️ Response time: {elapsed_time:.2f} seconds")

        return {
            "content": response_text,
            "time_taken": f"{elapsed_time:.2f}",
            "json_content": json.loads(response_text) if is_valid_json(response_text) else {"text": response_text}
        }

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise


def process_document_prms(bucket_name, file_key, prompt=DEFAULT_PROMPT_PRMS):
    """Process document for PRMS project using Supabase - identical functionality to process_document"""
    start_time = time.time()
    logger.info(f"PRMS Supabase Processing: {prompt}")

    try:
        reference_file_regions = f"{PRMS_BUCKET_KEY_NAME}/clarisa_regions.xlsx"
        reference_file_countries = f"{PRMS_BUCKET_KEY_NAME}/clarisa_countries.xlsx"
        initialize_supabase_tables()
        initialize_reference_data(
            bucket_name, reference_file_regions, reference_file_countries)

        document_content = read_document_from_s3(bucket_name, file_key)
        chunks = split_text(document_content)

        logger.info("#️⃣ Generating embeddings for PRMS...")
        embeddings = [get_embedding(chunk) for chunk in chunks]

        document_name = store_temp_embeddings(chunks, embeddings, file_key)

        all_reference_data = get_all_reference_data()

        relevant_chunks = get_relevant_chunk(prompt, document_name)

        context = all_reference_data + relevant_chunks

        query = f"""
        Based on this context:\n{context}\n\n
        Answer the question:\n{prompt}
        """

        response_text = invoke_model(query)

        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"✅ Successfully generated PRMS response:\n{response_text}")
        logger.info(f"⏱️ PRMS Response time: {elapsed_time:.2f} seconds")

        return {
            "content": response_text,
            "time_taken": f"{elapsed_time:.2f}",
            "json_content": json.loads(response_text) if is_valid_json(response_text) else {"text": response_text},
            "project": "PRMS"
        }

    except Exception as e:
        logger.error(f"❌ PRMS Error: {str(e)}")
        raise