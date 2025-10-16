import boto3
from typing import Any
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from app.utils.logger.logger_util import get_logger
from app.middleware.star_auth_middleware import AuthMiddleware as StarAuthMiddleware
from app.middleware.prms_auth_middleware import AuthMiddleware as PrmsAuthMiddleware
from app.llm.mining import process_document as process_with_llm
from app.llm.mining import process_document_prms as process_with_llm_prms
from app.utils.notification.notification_service import NotificationService
from app.llm.bulk_upload.upload_capdev import process_document_capdev as process_bulk_capdev

load_dotenv()
logger = get_logger()

star_auth_middleware = StarAuthMiddleware()
prms_auth_middleware = PrmsAuthMiddleware()
notification_service = NotificationService()

mcp = FastMCP("DocumentProcessor")

s3_client = boto3.client("s3")
bedrock_client = boto3.client("bedrock-runtime", region_name="us-west-2")


async def authenticate_star(key: str, bucket: str, token: str, environmentUrl: str):
    try:
        payload = {
            "token": token,
            "key": key,
            "bucket": bucket,
            "environmentUrl": environmentUrl
        }
        return await star_auth_middleware.authenticate(payload)
    except Exception as e:
        logger.error(f"Auth error (STAR): {str(e)}")
        return None


async def authenticate_prms(key: str, bucket: str, token: str, environmentUrl: str):
    try:
        payload = {
            "token": token,
            "key": key,
            "bucket": bucket,
            "environmentUrl": environmentUrl
        }
        return await prms_auth_middleware.authenticate(payload)
    except Exception as e:
        logger.error(f"Auth error (PRMS): {str(e)}")
        return None


@mcp.tool()
async def process_document(bucket: str, key: str, token: Any, environmentUrl: str, user_id: str = None) -> dict:
    logger.info("✅ process_document invoked via MCP")

    try:
        is_authenticated = await authenticate_star(key, bucket, token, environmentUrl)
        print(f"Authenticated: {is_authenticated}")
        if not is_authenticated:
            raise ValueError("Authentication failed")

        logger.info(f"Processing document: {key} from bucket: {bucket}")
        logger.info(f"👤 User ID for tracking: {user_id}")

        result = process_with_llm(
            bucket_name=bucket, file_key=key, user_id=user_id)

        await notification_service.send_slack_notification(
            emoji=":ai: :pick:",
            app_name="AI-MCP Mining Service (STAR)",
            color="#36a64f",
            title="Document Processed",
            message=f"Successfully processed document: *{key}*\nBucket: *{bucket}*",
            time_taken=f"Time taken: *{result['time_taken']}* seconds",
            priority="Low"
        )

        if "interaction_id" in result:
            response = {
                "json_content": result["json_content"],
                "interaction_id": result["interaction_id"]
            }

            return response
        else:
            return result["json_content"]

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await notification_service.send_slack_notification(
            emoji=":ai: :pick: :alert:",
            app_name="AI-MCP Mining Service (STAR)",
            color="#FF0000",
            title="Document Processing Failed",
            message=f"Error processing document: *{key}*\nError: *{str(e)}*",
            time_taken="Time taken: *N/A*",
            priority="High"
        )
        return {"status": "error", "key": key, "error": str(e)}


@mcp.tool()
async def process_document_prms(bucket: str, key: str, token: Any, environmentUrl: str, user_id: str = None) -> dict:
    logger.info("✅ process_document_prms invoked via MCP")

    try:
        is_authenticated = await authenticate_prms(key, bucket, token, environmentUrl)
        print(f"PRMS Authenticated: {is_authenticated}")
        if not is_authenticated:
            raise ValueError("PRMS Authentication failed")

        logger.info(f"Processing document for PRMS: {key} from bucket: {bucket}")
        logger.info(f"👤 User ID for tracking: {user_id}")

        result = process_with_llm_prms(
            bucket_name=bucket, file_key=key, user_id=user_id)

        await notification_service.send_slack_notification(
            emoji=":ai: :pick:",
            app_name="AI-MCP Mining Service (PRMS)",
            color="#36a64f",
            title="PRMS Document Processed",
            message=f"Successfully processed document for PRMS: *{key}*\nBucket: *{bucket}*",
            time_taken=f"Time taken: *{result['time_taken']}* seconds",
            priority="Low"
        )

        if "interaction_id" in result:
            response = {
                "json_content": result["json_content"],
                "interaction_id": result["interaction_id"]
            }

            return response
        else:
            return result["json_content"]

    except Exception as e:
        logger.error(f"Unexpected error in PRMS processing: {str(e)}")
        await notification_service.send_slack_notification(
            emoji=":ai: :pick: :alert:",
            app_name="AI-MCP Mining Service (PRMS)",
            color="#FF0000",
            title="PRMS Document Processing Failed",
            message=f"Error processing document for PRMS: *{key}*\nError: *{str(e)}*",
            time_taken="Time taken: *N/A*",
            priority="High"
        )
        return {"status": "error", "key": key, "error": str(e), "project": "PRMS"}


@mcp.tool()
async def process_document_capdev(bucket: str, key: str, token: Any, environmentUrl: str) -> dict:
    logger.info("✅ process_document_capdev invoked via MCP")

    try:
        is_authenticated = await authenticate_star(key, bucket, token, environmentUrl)
        print(f"Authenticated: {is_authenticated}")
        if not is_authenticated:
            raise ValueError("Authentication failed")

        logger.info(f"Processing document: {key} from bucket: {bucket}")

        result = process_bulk_capdev(
            bucket_name=bucket, file_key=key)

        await notification_service.send_slack_notification(
            emoji=":ai: :pick:",
            app_name="Bulk upload via Mining Service (STAR)",
            color="#36a64f",
            title="Document Processed",
            message=f"Successfully processed document: *{key}*\nBucket: *{bucket}*",
            time_taken=f"Time taken: *{result['time_taken']}* seconds",
            priority="Low"
        )

        return result["json_content"]

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await notification_service.send_slack_notification(
            emoji=":ai: :pick: :alert:",
            app_name="Bulk upload via Mining Service (STAR)",
            color="#FF0000",
            title="Document Processing Failed",
            message=f"Error processing document: *{key}*\nError: *{str(e)}*",
            time_taken="Time taken: *N/A*",
            priority="High"
        )
        return {"status": "error", "key": key, "error": str(e)}


if __name__ == "__main__":
    mcp.run()