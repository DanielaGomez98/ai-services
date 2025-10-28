import os
import json
import uvicorn
from typing import Optional, Union
from pydantic import BaseModel, Field
from mcp.client.stdio import stdio_client
from fastapi.middleware.cors import CORSMiddleware
from app.utils.s3.s3_util import upload_file_to_s3
from app.utils.logger.logger_util import get_logger
from mcp import ClientSession, StdioServerParameters, types
from fastapi import FastAPI, HTTPException, Body, UploadFile, File, Form
from app.utils.config.config_util import STAR_BUCKET_KEY_NAME, PRMS_BUCKET_KEY_NAME, AICCRA_BUCKET_KEY_NAME


logger = get_logger()

server_params = StdioServerParameters(
    command="python",
    args=[os.path.join(os.path.dirname(__file__), "server.py")],
    cwd=os.path.dirname(os.path.abspath(__file__)),
    env={"PYTHONPATH": os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../.."))}
)


class TextMiningRequest(BaseModel):
    bucketName: str = Field(
        ..., description="Name of the S3 bucket where the document is located", examples=["my-documents-bucket"])
    key: Optional[str] = Field(
        None, description="Object key in the S3 bucket. Optional if file is provided", examples=["reports/annual-report-2024.pdf"])
    token: str = Field(
        ..., description="Authentication token", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    environmentUrl: str = Field(
        ..., description="Environment for the service (e.g., production, test)")
    user_id: Optional[str] = Field(
        None, description="User identifier for interaction tracking", examples=["user@example.com", "researcher@cgiar.org"])

class UploadResponse(BaseModel):
    bucket: str = Field(..., description="S3 bucket where the file was uploaded")
    key: str = Field(..., description="Key (path) of the uploaded file in S3")
    status: str = Field(..., description="Status of the upload operation")
    message: str = Field(..., description="Detailed message about the upload operation")


app = FastAPI(
    title="CGIAR Text Mining Service API",
    description="""
    AI-Powered Document Processing Service:
    
    This service provides intelligent document analysis using Large Language Models (LLMs) 
    for extracting structured information from various document formats.
    
    Supported Projects:
    - STAR
    - PRMS

    Key Features:
    - 📄 Multi-format document support (PDF, DOCX, Excel, PowerPoint, TXT)
    - 🔍 Semantic content extraction with vector embeddings
    - 🤖 AI-powered analysis using AWS Bedrock (Claude 3 Sonnet)
    - 🔐 Authentication integration
    - 📊 Excel row-level processing for structured data
    - 🚀 Real-time processing with MCP protocol
    - 📱 Slack notifications for processing status

    Authentication:
    All requests require a valid token for authentication.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    servers=[
        {"url": "https://oxnrkcntlheycdgcnilexrwp4i0tucqz.lambda-url.us-east-1.on.aws", "description": "Test server"},
        {"url": "http://localhost:8000", "description": "Local server"},
        {"url": "https://d3djd7q7g7v7di.cloudfront.net", "description": "Production server"}
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def handle_sampling_message(message: types.CreateMessageRequestParams) -> types.CreateMessageResult:
    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(
            content="Processed by mock model", type="text"),
        model="mock-model",
        stopReason="endTurn"
    )


@app.post("/star/text-mining",
          summary="Process Document for STAR Project",
          description="""
          Process a document using AI text mining techniques for the STAR project.
          
          Processing Flow:
          1. Document validation and upload (if file provided)
          2. Authentication verification  
          3. Document chunking and vectorization
          4. AI analysis using Claude 3 Sonnet
          5. Structured data extraction
          
          Supported File Types:
          - PDF documents (.pdf)
          - Microsoft Word (.docx, .doc)
          - Excel spreadsheets (.xlsx, .xls)
          - PowerPoint presentations (.pptx, .ppt)
          - Plain text files (.txt)
          
          Note: You must provide either `key` (for existing S3 documents) or `file` (for upload), but not both.
          """,
          responses={
              200: {"description": "Document processed successfully"},
              400: {"description": "Bad Request - Missing or invalid parameters"},
              401: {"description": "Unauthorized - Invalid or missing authentication token"},
              500: {"description": "Internal Server Error - Error processing document"}
          },
          tags=["STAR Project"])
async def process_document_endpoint(
    bucketName: str = Form(
        ..., description="Name of the S3 bucket where the document is/will be located", examples=["cgiar-documents"]),
    token: str = Form(
        ..., description="Authentication token", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]),
    key: Optional[str] = Form(
        None, description="Object key in the S3 bucket. Optional if file is provided", examples=["star/text-mining/files/test/training-report-2024.pdf"]),
    file: Optional[Union[UploadFile, str]] = File(
        default=None, description="Document file to upload and process. Optional if key is provided"),
    environmentUrl: str = Form(
        ..., description="Target environment URL for authentication"
    ),
    user_id: Optional[str] = Form(
        None, description="User identifier for interaction tracking", examples=["user@example.com", "researcher@cgiar.org"]
    )
):
    """
    Process a document stored in S3 using text mining techniques.
    You can either provide a key to an existing document in S3 or upload a new file.

    - bucketName: Name of the S3 bucket where the document is/will be located
    - token: Authentication token
    - key: Object key in the S3 bucket (required if no file is provided)
    - file: File to upload and process (required if no key is provided)
    - environmentUrl: Environment for the service (e.g., production, test)
    - user_id: User identifier for interaction tracking (optional)

    Returns:
        dict: Result of the document processing
    """
    
    if isinstance(file, str) and file == "":
        file = None

    if key is None and file is None:
        raise HTTPException(
            status_code=400,
            detail="Either 'key' or 'file' must be provided"
        )

    if file is not None:
        try:
            file_content = await file.read()

            filename = file.filename
            key = f"{STAR_BUCKET_KEY_NAME}/{filename}"

            content_type = file.content_type

            upload_file_to_s3(
                file_content=file_content,
                bucket_name=bucketName,
                file_key=key,
                content_type=content_type
            )

            logger.info(f"✅ File {filename} uploaded to {bucketName}/{key}")

        except Exception as e:
            logger.error(f"❌ Error uploading file: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error uploading file: {str(e)}")

    logger.info(
        f"Processing document with key: {key} from bucket {bucketName}")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=handle_sampling_message) as session:
                await session.initialize()

                mcp_arguments = {
                    "bucket": bucketName,
                    "key": key,
                    "token": token,
                    "environmentUrl": environmentUrl
                }
                
                if user_id:
                    mcp_arguments["user_id"] = user_id

                result = await session.call_tool(
                    "process_document",
                    arguments=mcp_arguments
                )
                return result

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/prms/text-mining",
          summary="Process document for PRMS Project",
          description="""
          Process a document using AI text mining techniques for the PRMS (Policy Research and Management Systems) project.
          
          PRMS-Specific Features:
          - Policy change analysis and classification
          - Innovation development assessment
          - Capacity sharing evaluation with detailed demographics
          - Stakeholder identification and categorization
          
          Processing Capabilities:
          - Extract policy interventions and their stages
          - Identify innovation readiness levels (0-9 scale)
          - Analyze training programs and participant demographics
          - Classify organization types and roles
          
          Note: You must provide either `key` (for existing S3 documents) or `file` (for upload), but not both.
          """,
          responses={
              200: {"description": "Document processed successfully for PRMS"},
              400: {"description": "Bad Request - Missing or invalid parameters"},
              401: {"description": "Unauthorized - Authentication failed"},
              500: {"description": "Internal Server Error - Error processing document for PRMS"}
          },
          tags=["PRMS Project"])
async def process_document_prms_endpoint(
    bucketName: str = Form(
        ..., description="Name of the S3 bucket where the document is/will be located", examples=["prms-policy-documents"]),
    token: str = Form(
        ..., description="Authentication token for PRMS access", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]),
    key: Optional[str] = Form(
        None, description="Object key in the S3 bucket. Optional if file is provided", examples=["prms/text-mining/files/test/climate-policy-2024.docx"]),
    file: Optional[Union[UploadFile, str]] = File(
        default=None, description="File to upload and process. Optional if key is provided"),
    environmentUrl: str = Form(
        ..., description="Target environment URL for PRMS authentication"
    ),
    user_id: Optional[str] = Form(
        None, description="User identifier for interaction tracking", examples=["user@example.com", "researcher@cgiar.org"]
    )
):
    """
    Process a document stored in S3 using text mining techniques for PRMS project.
    You can either provide a key to an existing document in S3 or upload a new file.

    - bucketName: Name of the S3 bucket where the document is/will be located
    - token: Authentication token
    - key: Object key in the S3 bucket (required if no file is provided)
    - file: File to upload and process (required if no key is provided)
    - environmentUrl: Environment for the service (e.g., production, test)
    - user_id: User identifier for interaction tracking (optional)

    Returns:
        dict: Result of the document processing for PRMS
    """
    if isinstance(file, str) and file == "":
        file = None
    
    if key is None and file is None:
        raise HTTPException(
            status_code=400,
            detail="Either 'key' or 'file' must be provided"
        )
    
    if file is not None:
        try:
            file_content = await file.read()

            filename = file.filename
            key = f"{PRMS_BUCKET_KEY_NAME}/{filename}"

            content_type = file.content_type

            upload_file_to_s3(
                file_content=file_content,
                bucket_name=bucketName,
                file_key=key,
                content_type=content_type
            )

            logger.info(f"✅ File {filename} uploaded to {bucketName}/{key} for PRMS")

        except Exception as e:
            logger.error(f"❌ Error uploading file for PRMS: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error uploading file for PRMS: {str(e)}")

    logger.info(
        f"Processing document for PRMS with key: {key} from bucket {bucketName}")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=handle_sampling_message) as session:
                await session.initialize()

                mcp_arguments = {
                    "bucket": bucketName,
                    "key": key,
                    "token": token,
                    "environmentUrl": environmentUrl
                }

                if user_id:
                    mcp_arguments["user_id"] = user_id

                result = await session.call_tool(
                    "process_document_prms",
                    arguments=mcp_arguments
                )
                return result

    except Exception as e:
        logger.error(f"Error processing document for PRMS: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/star/mining-bulk-upload/capdev",
          summary="Bulk Upload for STAR Project",
          description="""
          This endpoint allows for the bulk upload of documents for the STAR project, specifically for the Capacity Sharing for Development (CapDev) indicator.

          Note: You must provide either `key` (for existing S3 documents) or `file` (for upload), but not both.
          """,
          responses={
              200: {"description": "Document processed successfully"},
              400: {"description": "Bad Request - Missing or invalid parameters"},
              401: {"description": "Unauthorized - Invalid or missing authentication token"},
              500: {"description": "Internal Server Error - Error processing document"}
          },
          tags=["STAR Project"])
async def bulk_upload_capdev_endpoint(
    bucketName: str = Form(
        ..., description="Name of the S3 bucket where the document is/will be located", examples=["cgiar-documents"]),
    token: str = Form(
        ..., description="Authentication token", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]),
    key: Optional[str] = Form(
        None, description="Object key in the S3 bucket. Optional if file is provided", examples=["star/text-mining/files/test/training-report-2024.pdf"]),
    file: Optional[Union[UploadFile, str]] = File(
        default=None, description="Document file to upload and process. Optional if key is provided"),
    environmentUrl: str = Form(
        ..., description="Target environment URL for authentication"
    )
):
    """
    Process a document stored in S3 using text mining techniques.
    You can either provide a key to an existing document in S3 or upload a new file.

    - bucketName: Name of the S3 bucket where the document is/will be located
    - token: Authentication token
    - key: Object key in the S3 bucket (required if no file is provided)
    - file: File to upload and process (required if no key is provided)
    - environmentUrl: Environment for the service (e.g., production, test)

    Returns:
        dict: Result of the document processing
    """
    
    if isinstance(file, str) and file == "":
        file = None

    if key is None and file is None:
        raise HTTPException(
            status_code=400,
            detail="Either 'key' or 'file' must be provided"
        )

    if file is not None:
        try:
            file_content = await file.read()

            filename = file.filename
            key = f"{STAR_BUCKET_KEY_NAME}/{filename}"

            content_type = file.content_type

            upload_file_to_s3(
                file_content=file_content,
                bucket_name=bucketName,
                file_key=key,
                content_type=content_type
            )

            logger.info(f"✅ File {filename} uploaded to {bucketName}/{key}")

        except Exception as e:
            logger.error(f"❌ Error uploading file: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error uploading file: {str(e)}")

    logger.info(
        f"Processing document with key: {key} from bucket {bucketName}")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=handle_sampling_message) as session:
                await session.initialize()

                result = await session.call_tool(
                    "process_document_capdev",
                    arguments={
                        "bucket": bucketName,
                        "key": key,
                        "token": token,
                        "environmentUrl": environmentUrl
                    }
                )
                return result

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/aiccra/text-mining",
          summary="Process Document for AICCRA Project",
          description="""
          Process a document using AI text mining techniques for the AICCRA project.
          
          Processing Flow:
          1. Document validation and upload (if file provided)
          2. Document chunking and vectorization
          3. AI analysis using Claude 4 Sonnet
          4. Structured data extraction
          
          Supported File Types:
          - PDF documents (.pdf)
          - Microsoft Word (.docx, .doc)
          - Excel spreadsheets (.xlsx, .xls)
          - PowerPoint presentations (.pptx, .ppt)
          - Plain text files (.txt)
          
          Note: You must provide either `key` (for existing S3 documents) or `file` (for upload), but not both.
          """,
          responses={
              200: {"description": "Document processed successfully"},
              400: {"description": "Bad Request - Missing or invalid parameters"},
              401: {"description": "Unauthorized - Invalid or missing authentication token"},
              500: {"description": "Internal Server Error - Error processing document"}
          },
          tags=["AICCRA Project"])
async def process_document_aiccra_endpoint(
    bucketName: str = Form(
        ..., description="Name of the S3 bucket where the document is/will be located", examples=["cgiar-documents"]),
    token: Optional[str] = Form(
        None, description="Authentication token", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]),
    key: Optional[str] = Form(
        None, description="Object key in the S3 bucket. Optional if file is provided", examples=["star/text-mining/files/test/training-report-2024.pdf"]),
    file: Optional[Union[UploadFile, str]] = File(
        default=None, description="Document file to upload and process. Optional if key is provided"),
    environmentUrl: Optional[str] = Form(
        None, description="Target environment URL for authentication"
    ),
    user_id: Optional[str] = Form(
        None, description="User identifier for interaction tracking", examples=["user@example.com", "researcher@cgiar.org"]
    )
):
    """
    Process a document stored in S3 using text mining techniques.
    You can either provide a key to an existing document in S3 or upload a new file.

    - bucketName: Name of the S3 bucket where the document is/will be located
    - token: Authentication token
    - key: Object key in the S3 bucket (required if no file is provided)
    - file: File to upload and process (required if no key is provided)
    - environmentUrl: Environment for the service (e.g., production, test)
    - user_id: User identifier for interaction tracking (optional)

    Returns:
        dict: Result of the document processing
    """
    
    if isinstance(file, str) and file == "":
        file = None

    if key is None and file is None:
        raise HTTPException(
            status_code=400,
            detail="Either 'key' or 'file' must be provided"
        )

    if file is not None:
        try:
            file_content = await file.read()

            filename = file.filename
            key = f"{AICCRA_BUCKET_KEY_NAME}/{filename}"

            content_type = file.content_type

            upload_file_to_s3(
                file_content=file_content,
                bucket_name=bucketName,
                file_key=key,
                content_type=content_type
            )

            logger.info(f"✅ File {filename} uploaded to {bucketName}/{key}")

        except Exception as e:
            logger.error(f"❌ Error uploading file: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error uploading file: {str(e)}")

    logger.info(
        f"Processing document with key: {key} from bucket {bucketName}")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=handle_sampling_message) as session:
                await session.initialize()

                mcp_arguments = {
                    "bucket": bucketName,
                    "key": key,
                    "token": token,
                    "environmentUrl": environmentUrl
                }
                
                if user_id:
                    mcp_arguments["user_id"] = user_id

                result = await session.call_tool(
                    "process_document_aiccra",
                    arguments=mcp_arguments
                )
                return result

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)