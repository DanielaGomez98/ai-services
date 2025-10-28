import json
import time
import boto3
import requests
import pandas as pd
import streamlit as st
from typing import Optional, List, Dict
from app.utils.config.config_util import AWS
from botocore.exceptions import BotoCoreError, ClientError

# =========================
# Page config & styles
# =========================
st.set_page_config(
    page_title="AICCRA Text Mining Service",
    page_icon="🧠",
    layout="wide",
)

# -------------------------
# Session state (persist results across reruns)
# -------------------------
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None
if "last_payload" not in st.session_state:
    st.session_state["last_payload"] = None
if "last_df" not in st.session_state:
    st.session_state["last_df"] = None
if "last_elapsed" not in st.session_state:
    st.session_state["last_elapsed"] = None
if "last_source_id" not in st.session_state:
    st.session_state["last_source_id"] = None

st.session_state["has_rendered_this_run"] = False


# =========================
# Helpers
# =========================
def list_s3_objects(bucket: str, prefix: str = "", max_items: int = 1000) -> List[str]:
    """List objects in S3; returns keys ordered by LastModified (desc)."""
    try:
        s3 = boto3.client(
            "s3", 
            aws_access_key_id=AWS['aws_access_key'],
            aws_secret_access_key=AWS['aws_secret_key'],
            region_name=AWS['aws_region']
        )
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
        items = []
        for page in pages:
            for obj in page.get("Contents", []):
                items.append((obj["Key"], obj["LastModified"]))
                if len(items) >= max_items:
                    break
        items.sort(key=lambda x: x[1], reverse=True)
        return [k for k, _ in items]
    except (BotoCoreError, ClientError) as e:
        st.error(f"❌ _S3 listing error: {e}_")
        return []


def normalize_results_to_df(result_json: Dict) -> pd.DataFrame:
    """
    Normalize the JSON output (with 'results': [...]) to a flat DataFrame.
    - Flattens 'geoscope'
    - Converts arrays/objects to readable strings
    - Keeps a friendly column order
    """
    results = result_json.get("results", [])
    if not isinstance(results, list):
        results = []

    df = pd.json_normalize(results, sep=".")

    def list_to_str(val):
        if isinstance(val, list):
            return json.dumps(val, ensure_ascii=False)
        
        return val

    for col in df.columns:
        df[col] = df[col].apply(list_to_str)
    
    return df


def extract_inner_results_json(raw: Dict) -> Dict:
    """
    Extracts the actual payload with 'results' from wrapper responses.
    Supports backends that return:
      { "content": [ {"type":"text", "text": "{...json...}"} ], ... }
    or direct { "text": "{...json...}" }.
    Returns a dict that ideally contains 'results': [...]
    """
    if isinstance(raw, dict) and "results" in raw:
        return raw

    content = raw.get("content")
    if isinstance(content, list):
        for item in content:
            text = item.get("text")
            if isinstance(text, str):
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        if "results" in parsed:
                            return parsed
                        json_content = parsed.get("json_content")
                        if isinstance(json_content, dict) and "results" in json_content:
                            return json_content
                except Exception:
                    continue

    return {"results": []}


def _set_results(result: Dict, payload: Dict, df: pd.DataFrame, elapsed: float, source_id: str) -> None:
    st.session_state["last_result"] = result
    st.session_state["last_payload"] = payload
    st.session_state["last_df"] = df
    st.session_state["last_elapsed"] = elapsed
    st.session_state["last_source_id"] = source_id
    st.session_state["has_rendered_this_run"] = False


def _clear_results() -> None:
    st.session_state["last_result"] = None
    st.session_state["last_payload"] = None
    st.session_state["last_df"] = None
    st.session_state["last_elapsed"] = None
    st.session_state["last_source_id"] = None


def _render_results(result: Dict, df: pd.DataFrame, elapsed: float) -> None:
    st.success(f"Processed successfully! ⏱️ {elapsed:.2f}s")

    with st.expander("🔎 **Raw JSON output**", expanded=False):
        st.json(result)

    if not df.empty:
        payload = extract_inner_results_json(result)
        original_results = payload.get("results", [])
        
        if original_results:
            st.subheader("📊 Results")
            st.info(f"📊 Found {len(original_results)} records")

            st.dataframe(df, use_container_width=True, hide_index=True)
            
    else:
        st.warning(f"⚠️ No results found.")

    st.session_state["has_rendered_this_run"] = True


def post_to_api(
    base_url: str,
    bucket: str,
    user_id: str,
    project_type: str,
    folder_path: str,
    key: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    file_name: Optional[str] = None,
    file_type: Optional[str] = None,
) -> Dict:
    """
    Call the FastAPI /aiccra/text-mining endpoint.
    - If file_bytes is present, send multipart with 'file'
    - Otherwise, send 'key'
    """
    if project_type == "AICCRA":
        url = base_url.rstrip("/") + "/aiccra/text-mining"
    
    data = {
        "bucketName": bucket,
        "user_id": user_id
    }

    files = None
    if file_bytes is not None and file_name:
        full_key = folder_path + file_name
        files = {"file": (file_name, file_bytes, file_type or "application/octet-stream")}
        data["key"] = full_key
    else:
        data["key"] = key or ""

    resp = requests.post(url, data=data, files=files, timeout=900)
    if resp.status_code != 200:
        raise RuntimeError(f"API error {resp.status_code}: {resp.text}")
    return resp.json()


# =========================
# Sidebar
# =========================
st.sidebar.title("⚙️ Settings")

api_base_url = st.sidebar.text_input(
    "FastAPI Base URL",
    value="https://oxnrkcntlheycdgcnilexrwp4i0tucqz.lambda-url.us-east-1.on.aws",
    help="Your FastAPI service URL (defaults to https://oxnrkcntlheycdgcnilexrwp4i0tucqz.lambda-url.us-east-1.on.aws)."
)
bucket = st.sidebar.text_input("S3 Bucket", value="ai-services-ibd")

project_type = st.sidebar.selectbox(
    "Project Type",
    options=["AICCRA"],
    help="Select the project type to determine the correct folder structure"
)

if project_type == "AICCRA":
    base_folders = [
        "aiccra/text-mining/files/test/",
        "aiccra/text-mining/files/prod/"
    ]

folder_path = st.sidebar.selectbox(
    "Base Folder",
    options=base_folders,
    help="Select the base folder for document operations"
)

st.sidebar.markdown("---")

email = st.sidebar.text_input(
    "👤 User Email",
    value="",
    help="User email for tracking interactions"
)


# =========================
# Main
# =========================
st.title("🧠 AICCRA - Text Mining Service")
st.markdown("**Upload a document or select one from S3, send it to the text-mining service, and visualize results.**")

st.markdown("######")
    
mode = st.radio(
    "**📄 Document source:**",
    options=["Upload file", "Select from S3"],
    horizontal=True
)

col_left, col_right = st.columns([2, 1])

selected_key = None
uploaded_file = None

with col_left:
    if mode == "Upload file":
        uploaded_file = st.file_uploader(
            "File type (pdf, docx, txt, xlsx, xls, pptx)",
            type=["pdf", "docx", "txt", "xlsx", "xls", "pptx"],
            accept_multiple_files=False
        )
        if uploaded_file:
            st.info(f"📁 File will be uploaded to: `{bucket}/{folder_path}{uploaded_file.name}`")
    
    else:
        with st.expander("S3 search options", expanded=True):
            additional_prefix = st.text_input(
                "Additional prefix (optional)", 
                value="",
                help=f"Will be appended to base folder: {folder_path}"
            )
            full_prefix = folder_path + additional_prefix
            st.caption(f"Searching in: `{bucket}/{full_prefix}`")
            refresh = st.button("🔄 Refresh list")

        if bucket:
            cache_key = f"s3_keys_{bucket}_{full_prefix}"
            if cache_key not in st.session_state or refresh:
                with st.spinner("Listing S3 objects..."):
                    st.session_state[cache_key] = list_s3_objects(bucket, full_prefix)
            
            keys = st.session_state.get(cache_key, [])
            if keys:
                selected_key = st.selectbox(
                    "Select an object from S3",
                    options=keys,
                    index=0
                )
                st.caption(f"Selected: `{selected_key}`")
            else:
                st.info("_No objects found for this bucket/prefix._")

with col_right:
    st.markdown("####")
    run_btn = st.button("🚀 Process document", type="primary", use_container_width=True)
    st.caption("_Tip: Filter by prefix to quickly find your files._")


# =========================
# Main action
# =========================
if run_btn:
    if not bucket:
        st.error("❌ _Please complete **S3 Bucket**._")
    elif not email:
        st.error("❌ _Please provide a **User Email**._")
    else:
        try:
            with st.spinner("Sending document to the service…"):
                t0 = time.time()

                if mode == "Upload file":
                    if not uploaded_file:
                        st.warning("⚠️ _You need to select a file to upload._")
                        st.stop()
                    file_bytes = uploaded_file.read()
                    result = post_to_api(
                        base_url=api_base_url,
                        bucket=bucket,
                        user_id=email,
                        project_type=project_type,
                        folder_path=folder_path,
                        file_bytes=file_bytes,
                        file_name=uploaded_file.name,
                        file_type=uploaded_file.type
                    )
                else:
                    if not selected_key:
                        st.warning("⚠️ _You need to select an S3 object._")
                        st.stop()
                    result = post_to_api(
                        base_url=api_base_url,
                        bucket=bucket,
                        user_id=email,
                        project_type=project_type,
                        folder_path=folder_path,
                        key=selected_key
                    )

                elapsed = time.time() - t0

            if isinstance(result, dict) and (result.get("status") == "error" or result.get("isError") is True):
                _clear_results()
                st.error(f"❌ _Service returned an error: {result.get('error') or result.get('message') or 'Unknown error'}_")
                st.stop()

            if mode == "Upload file" and uploaded_file is not None:
                source_id = f"upload::{uploaded_file.name}"
            elif mode == "Select from S3" and selected_key:
                source_id = f"s3::{selected_key}"
            else:
                source_id = "unknown"

            try:
                payload = extract_inner_results_json(result)
                df = normalize_results_to_df(payload)
            except Exception as e:
                st.error(f"❌ _Failed to normalize output to table: {e}_")
                df = pd.DataFrame()

            if not df.empty:
                _set_results(result, payload, df, elapsed, source_id)
                _render_results(st.session_state["last_result"], st.session_state["last_df"], st.session_state["last_elapsed"])
            else:
                _clear_results()
                st.warning("⚠️ _No results to display (empty list or unexpected structure)._")

        except requests.exceptions.RequestException as e:
            _clear_results()
            st.error(f"❌ _Could not reach the API: {e}_")
        except Exception as e:
            _clear_results()
            st.exception(e)


# -------------------------
# Persist results across reruns (e.g., after clicking download buttons)
# -------------------------
if not st.session_state.get("has_rendered_this_run") and st.session_state.get("last_df") is not None:
    _render_results(st.session_state["last_result"], st.session_state["last_df"], st.session_state["last_elapsed"])