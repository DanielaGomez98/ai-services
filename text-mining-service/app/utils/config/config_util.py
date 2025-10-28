import os
from dotenv import load_dotenv

load_dotenv()

AWS = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "aws_region": os.getenv("AWS_REGION", "us-east-1")
}

MS_NAME = os.getenv("MS_NAME", "Mining Microservice")

STAR_BUCKET_KEY_NAME = os.getenv("STAR_BUCKET_KEY_NAME")
PRMS_BUCKET_KEY_NAME = os.getenv("PRMS_BUCKET_KEY_NAME")
AICCRA_BUCKET_KEY_NAME = os.getenv("AICCRA_BUCKET_KEY_NAME")

MAPPING_URL = os.getenv("MAPPING_URL")

AUTH_TOKEN_STAR = os.getenv("AUTH_TOKEN_STAR", None)

CLIENT_ID = os.getenv("CLIENT_ID", None)
CLIENT_SECRET = os.getenv("CLIENT_SECRET", None)