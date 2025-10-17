import io
import json
import time
import boto3
import base64
import requests
import pandas as pd
import streamlit as st
from typing import Optional, List, Dict
from botocore.exceptions import BotoCoreError, ClientError
from app.utils.config.config_util import AWS, CLIENT_ID, CLIENT_SECRET


# =========================
# Auth token generation
# =========================
def generate_auth_token(client_id: str, client_secret: str) -> str:
    """Generate base64 encoded auth token from client credentials"""
    credentials = {
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    json_string = json.dumps(credentials)
    
    encoded_bytes = base64.b64encode(json_string.encode('utf-8'))
    
    return encoded_bytes.decode('utf-8')

AUTH_TOKEN = generate_auth_token(CLIENT_ID, CLIENT_SECRET)

# =========================
# Page config & styles
# =========================
st.set_page_config(
    page_title="Bulk Upload",
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
            try:
                return json.dumps(val, ensure_ascii=False)
            except Exception:
                return json.dumps(val, ensure_ascii=False)
        return val

    for col in df.columns:
        df[col] = df[col].apply(list_to_str)
    
    if "batch_number" in df.columns:
        df = df.drop("batch_number", axis=1)
    
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
                    if isinstance(parsed, dict) and "results" in parsed:
                        return parsed
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


def post_to_star_formalize(
    token: str,
    selected_results: List[Dict]
) -> Dict:
    """
    Send selected results to STAR formalize bulk endpoint.
    """
    url =  "https://main-allianceindicatorstest.ciat.cgiar.org/api/results/ai/formalize/bulk"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "results": selected_results
    }
    
    st.write(f"🔍 **Debug Info:**")
    st.write(f"- Number of selected results: {len(selected_results)}")
    
    if selected_results:
        st.write(f"- Sample of first result:")
        with st.expander("First result preview", expanded=False):
            st.json(selected_results[0])
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=300)
        st.write(f"- Response status: {resp.status_code}")
        
        if resp.status_code not in [200, 201]:
            st.write(f"- Response text: {resp.text}")
            raise RuntimeError(f"STAR API error {resp.status_code}: {resp.text}")
        
        return resp.json()
        
    except requests.exceptions.RequestException as e:
        st.write(f"- Request exception: {str(e)}")
        raise RuntimeError(f"Network error: {str(e)}")


def build_result_from_edited_row(edited_row: pd.Series, original_result: Dict) -> Dict:
    """Build JSON result from edited DataFrame row"""
    result = original_result.copy()

    if "batch_number" in result:
        del result["batch_number"]
    
    simple_fields = [
        "indicator", "title", "description", "contract_code", "training_category", 
        "training_type", "training_purpose", "delivery_modality", 
        "length_of_training", "degree", "trainee_name", "trainee_gender", 
        "geoscope_level", "start_date", "end_date", "year"
    ]
    
    for field in simple_fields:
        if field in edited_row.index and pd.notna(edited_row[field]):
            result[field] = str(edited_row[field]).strip()
    
    numeric_fields = [
        "total_participants", "male_participants", 
        "female_participants", "non_binary_participants"
    ]
    
    for field in numeric_fields:
        if field in edited_row.index and pd.notna(edited_row[field]):
            try:
                result[field] = int(edited_row[field])
            except (ValueError, TypeError):
                result[field] = original_result.get(field, 0)
    
    nested_fields = {
        "main_contact_person.name": ("main_contact_person", "name"),
        "main_contact_person.code": ("main_contact_person", "code"),
        "main_contact_person.similarity_score": ("main_contact_person", "similarity_score"),
        "training_supervisor.name": ("training_supervisor", "name"),
        "training_supervisor.code": ("training_supervisor", "code"),
        "training_supervisor.similarity_score": ("training_supervisor", "similarity_score"),
        "trainee_affiliation.affiliation_name": ("trainee_affiliation", "affiliation_name"),
        "trainee_affiliation.institution_id": ("trainee_affiliation", "institution_id"),
        "trainee_affiliation.similarity_score": ("trainee_affiliation", "similarity_score"),
        "language.name": ("language", "name"),
        "language.code": ("language", "code")
    }
    
    for field_key, (parent, child) in nested_fields.items():
        if field_key in edited_row.index and pd.notna(edited_row[field_key]):
            if parent not in result:
                result[parent] = {}
            result[parent][child] = edited_row[field_key]
    
    array_fields = ["sdg_targets", "keywords", "partners", "countries", "regions", "evidences"]
    
    for field in array_fields:
        if field in edited_row.index and pd.notna(edited_row[field]):
            edited_value = str(edited_row[field]).strip()
            
            if not edited_value:
                result[field] = original_result.get(field, [])
                continue
            
            try:
                parsed_value = json.loads(edited_value)
                if isinstance(parsed_value, list):
                    result[field] = parsed_value
                elif isinstance(parsed_value, dict):
                    result[field] = [parsed_value]
                else:
                    result[field] = original_result.get(field, [])
            except (json.JSONDecodeError, TypeError):
                result[field] = original_result.get(field, [])
        else:
            result[field] = original_result.get(field, [])
    
    return result


def extract_unmapped_institutions(results: List[Dict]) -> List[Dict]:
    """
    Extract institutions that were not properly mapped (institution_id = null and similarity_score = 0)
    from partners and trainee_affiliation fields.
    
    Only checks fields that actually exist in the JSON results.
    Avoids duplicates based on institution name.
    
    Returns a list of unmapped institutions with their source information.
    """
    unmapped_institutions = []
    seen_institutions = set()
    
    for idx, result in enumerate(results):
        record_id = f"Record_{idx + 1}"
        title = result.get("title", "Unknown Title")
        
        if "partners" in result:
            partners = result.get("partners", [])
            if isinstance(partners, list):
                for partner_idx, partner in enumerate(partners):
                    if isinstance(partner, dict):
                        institution_id = partner.get("institution_id")
                        similarity_score = partner.get("similarity_score", 0)
                        institution_name = partner.get("institution_name", "Unknown Institution")
                        
                        if institution_id is None and similarity_score == 0:
                            institution_key = institution_name.lower().strip()
                            
                            if institution_key not in seen_institutions:
                                seen_institutions.add(institution_key)
                                unmapped_institutions.append({
                                    "record_id": record_id,
                                    "record_title": title,
                                    "source_field": "partners",
                                    "partner_index": partner_idx + 1,
                                    "institution_name": institution_name,
                                    "institution_id": institution_id,
                                    "similarity_score": similarity_score
                                })
        
        if "trainee_affiliation" in result:
            trainee_affiliation = result.get("trainee_affiliation", {})
            if isinstance(trainee_affiliation, dict):
                institution_id = trainee_affiliation.get("institution_id")
                similarity_score = trainee_affiliation.get("similarity_score", 0)
                affiliation_name = trainee_affiliation.get("affiliation_name", "Unknown Affiliation")
                
                if institution_id is None and similarity_score == 0:
                    institution_key = affiliation_name.lower().strip()
                    
                    if institution_key not in seen_institutions:
                        seen_institutions.add(institution_key)
                        unmapped_institutions.append({
                            "record_id": record_id,
                            "record_title": title,
                            "source_field": "trainee_affiliation",
                            "partner_index": None,
                            "institution_name": affiliation_name,
                            "institution_id": institution_id,
                            "similarity_score": similarity_score
                        })
    
    return unmapped_institutions


def create_unmapped_report_csv(unmapped_institutions: List[Dict]) -> str:
    """Convert unmapped institutions list to CSV format"""
    if not unmapped_institutions:
        return "No unmapped institutions found."
    
    import pandas as pd
    
    df = pd.DataFrame(unmapped_institutions)
    
    column_order = [
        "record_id", 
        "record_title", 
        "source_field", 
        "institution_name", 
        "institution_id", 
        "similarity_score",
        "partner_index"
    ]
    
    df = df[column_order]
    
    return df.to_csv(index=False)


def _render_results(result: Dict, df: pd.DataFrame, elapsed: float) -> None:
    st.success(f"Processed successfully! ⏱️ {elapsed:.2f}s")

    with st.expander("🔎 **Raw JSON output**", expanded=False):
        st.json(result)

    if not df.empty:
        payload = extract_inner_results_json(result)
        original_results = payload.get("results", [])
        
        if original_results:
            st.subheader("🏢 Institution Mapping Report")
            
            unmapped_institutions = extract_unmapped_institutions(original_results)
            
            if unmapped_institutions:
                st.warning(f"⚠️ Found {len(unmapped_institutions)} unmapped institutions")
                
                with st.expander("🔍 View unmapped institutions", expanded=False):
                    unmapped_df = pd.DataFrame(unmapped_institutions)
                    st.dataframe(unmapped_df, use_container_width=True)
                
                csv_content = create_unmapped_report_csv(unmapped_institutions)
                
                st.download_button(
                    label="📥 Download Unmapped Institutions Report",
                    data=csv_content,
                    file_name=f"unmapped_institutions_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    help="Download CSV report of institutions that could not be mapped",
                    use_container_width=True
                )
            else:
                st.success("✅ All institutions were successfully mapped!")

            st.markdown("---")

            st.subheader("📊 Results")
            st.markdown("**Select records to submit to STAR platform:**")
            
            col1, col2, col3 = st.columns([1, 2, 2])
            
            # with col1:
            #     select_all = st.checkbox("Select All", key="select_all_records")
            
            with col2:
                st.info(f"📊 Found {len(original_results)} records")
            
            with col3:
                submit_to_star = st.button(
                    "🚀 Submit to STAR", 
                    type="primary",
                    disabled=len(original_results) == 0,
                    help="Submit selected records to STAR platform",
                    use_container_width=True
                )
            
            df_display = df.copy()
            
            selection_column = []
            for idx in range(len(df_display)):
                checkbox_key = f"record_select_{idx}"
                
                # if select_all:
                #     st.session_state[checkbox_key] = True
                
                current_value = st.session_state.get(checkbox_key, False)
                selection_column.append(current_value)
            
            df_display.insert(0, "Select", selection_column)

            column_config = {
                "Select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Select records to submit to STAR",
                    default=False,
                ),
                "indicator": st.column_config.TextColumn(
                    "Indicator",
                    help="Edit the indicator",
                    max_chars=500,
                ),
                "title": st.column_config.TextColumn(
                    "Title",
                    help="Edit the title of the record",
                    max_chars=500,
                    required=True,
                ),
                "description": st.column_config.TextColumn(
                    "Description",
                    help="Edit the description",
                    max_chars=1000,
                ),
                "year": st.column_config.TextColumn(
                    "Year",
                    help="Edit the year (e.g., 2024, 2025)",
                    max_chars=20,
                ),
                "contract_code": st.column_config.TextColumn(
                    "Contract Code",
                    help="Edit the contract code",
                    max_chars=50,
                ),
                "sdg_targets": st.column_config.TextColumn(
                    "SDG Targets",
                    help="Edit SDG targets (comma-separated)",
                    max_chars=500,
                ),
                "training_category": st.column_config.SelectboxColumn(
                    "Training Category",
                    help="Select training category",
                    options=["Training", "Engagement"],
                ),
                "training_type": st.column_config.SelectboxColumn(
                    "Training Type",
                    help="Select training type", 
                    options=["Individual training", "Group training"],
                ),
                "training_purpose": st.column_config.TextColumn(
                    "Training Purpose",
                    help="Edit training purpose",
                    max_chars=100,
                ),
                "start_date": st.column_config.TextColumn(
                    "Start Date",
                    help="Edit start date (format: YYYY-MM-DD, e.g., 2025-04-30)",
                    max_chars=10,
                ),
                "end_date": st.column_config.TextColumn(
                    "End Date", 
                    help="Edit end date (format: YYYY-MM-DD, e.g., 2025-04-30)",
                    max_chars=10,
                ),
                "delivery_modality": st.column_config.SelectboxColumn(
                    "Delivery Modality",
                    help="Select delivery modality",
                    options=["in-person", "virtual", "hybrid"],
                ),
                "length_of_training": st.column_config.SelectboxColumn(
                    "Length of Training",
                    help="Select length of training",
                    options=["Short-term", "Long-term"],
                ),
                "total_participants": st.column_config.NumberColumn(
                    "Total Participants",
                    help="Edit total participants",
                    min_value=0,
                    step=1,
                    format="%d"
                ),
                "male_participants": st.column_config.NumberColumn(
                    "Male Participants",
                    help="Edit male participants",
                    min_value=0, 
                    step=1,
                    format="%d"
                ),
                "female_participants": st.column_config.NumberColumn(
                    "Female Participants",
                    help="Edit female participants", 
                    min_value=0,
                    step=1,
                    format="%d"
                ),
                "non_binary_participants": st.column_config.NumberColumn(
                    "Non-binary Participants",
                    help="Edit non-binary participants",
                    min_value=0,
                    step=1, 
                    format="%d"
                ),
                "degree": st.column_config.SelectboxColumn(
                    "Degree",
                    help="Select degree level",
                    options=["PhD", "MSc", "BSc", "Other"],
                ),
                "trainee_name": st.column_config.TextColumn(
                    "Trainee Name",
                    help="Edit trainee name",
                    max_chars=200,
                ),
                "trainee_gender": st.column_config.SelectboxColumn(
                    "Trainee Gender", 
                    help="Select trainee gender",
                    options=["male", "female", "non-binary"],
                ),
                "geoscope_level": st.column_config.SelectboxColumn(
                    "Geoscope Level",
                    help="Select geographic scope",
                    options=["Global", "Regional", "National", "Sub-national", "This is yet to be determined"],
                ),
                "keywords": st.column_config.TextColumn(
                    "Keywords",
                    help="Edit keywords (comma-separated)",
                    max_chars=500,
                ),
                "main_contact_person.name": st.column_config.TextColumn(
                    "Main Contact Name",
                    help="Edit main contact person name",
                    max_chars=200,
                ),
                "main_contact_person.code": st.column_config.TextColumn(
                    "Main Contact Code",
                    help="Edit main contact person code",
                    max_chars=100,
                ),
                "main_contact_person.similarity_score": st.column_config.NumberColumn(
                    "Main Contact Similarity",
                    help="Edit main contact similarity score",
                    min_value=0.0,
                    max_value=100.0,
                ),
                "training_supervisor.name": st.column_config.TextColumn(
                    "Training Supervisor",
                    help="Edit training supervisor name", 
                    max_chars=200,
                ),
                "training_supervisor.code": st.column_config.TextColumn(
                    "Training Supervisor Code",
                    help="Edit training supervisor code",
                    max_chars=100,
                ),
                "training_supervisor.similarity_score": st.column_config.NumberColumn(
                    "Supervisor Similarity",
                    help="Edit training supervisor similarity score",
                    min_value=0.0,
                    max_value=100.0,
                ),
                "trainee_affiliation.affiliation_name": st.column_config.TextColumn(
                    "Trainee Affiliation",
                    help="Edit trainee affiliation",
                    max_chars=300,
                ),
                "trainee_affiliation.institution_id": st.column_config.TextColumn(
                    "Trainee affiliation ID",
                    help="Edit institution ID",
                    max_chars=100,
                ),
                "trainee_affiliation.similarity_score": st.column_config.NumberColumn(
                    "Affiliation Similarity",
                    help="Edit trainee affiliation similarity score",
                    min_value=0.0,
                    max_value=100.0,
                ),
                "language.name": st.column_config.TextColumn(
                    "Language",
                    help="Edit language name",
                    max_chars=100,
                ),
                "language.code": st.column_config.TextColumn(
                    "Language Code",
                    help="Edit language code",
                    max_chars=10,
                ),
                "partners": st.column_config.TextColumn(
                    "Partners",
                    help="Edit partners (JSON format)",
                    max_chars=1000,
                ),
                "countries": st.column_config.TextColumn(
                    "Countries", 
                    help="Edit countries (JSON format)",
                    max_chars=500,
                ),
                "regions": st.column_config.TextColumn(
                    "Regions",
                    help="Edit regions (JSON format)", 
                    max_chars=500,
                ),
                "evidences": st.column_config.TextColumn(
                    "Evidences",
                    help="Edit evidences (JSON format)",
                    max_chars=2000,
                ),
                "trainee_nationality.code": st.column_config.TextColumn(
                    "Trainee Nationality Code",
                    help="Edit trainee nationality code",
                    max_chars=10,
                ),
            }
            
            edited_df = st.data_editor(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config=column_config,
                key="data_editor"
            )
            
            selection_data = edited_df["Select"].tolist()
            selected_count = sum(selection_data)
            
            if selected_count > 0:
                st.info(f"📋 Selected: {selected_count} of {len(original_results)} records")
            
            if submit_to_star:
                selected_indices = [idx for idx, selected in enumerate(selection_data) if selected]
                
                if not selected_indices:
                    st.warning("⚠️ Please select at least one record to submit to STAR.")
                else:
                    selected_results = []
                    for idx in selected_indices:
                        result = build_result_from_edited_row(edited_df.iloc[idx], original_results[idx])
                        selected_results.append(result)
                    
                    try:
                        with st.spinner(f"Submitting {len(selected_results)} records to STAR platform..."):
                            star_response = post_to_star_formalize(
                                token=st.session_state.get("token", ""),
                                selected_results=selected_results
                            )
                        
                        st.success(f"✅ Successfully submitted {len(selected_results)} records to STAR!")
                        
                        with st.expander("📋 STAR Submission Details", expanded=True):
                            st.json(star_response)
                            
                        if st.button("🔄 Clear Selections", key="clear_selections"):
                            if "data_editor" in st.session_state:
                                del st.session_state["data_editor"]
                            if "select_all_records" in st.session_state:
                                del st.session_state["select_all_records"]
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"❌ Error submitting to STAR: {str(e)}")
                        with st.expander("🔍 Error Details", expanded=False):
                            st.code(str(e))
        
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.session_state["has_rendered_this_run"] = True


def post_to_api(
    base_url: str,
    bucket: str,
    token: str,
    environment_url: str,
    project_type: str,
    folder_path: str,
    prompt: Optional[str] = None,
    key: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    file_name: Optional[str] = None,
    file_type: Optional[str] = None,
) -> Dict:
    """
    Call the FastAPI /star/mining-bulk-upload/capdev endpoint.
    - If file_bytes is present, send multipart with 'file'
    - Otherwise, send 'key'
    """
    if project_type == "STAR":
        url = base_url.rstrip("/") + "/star/mining-bulk-upload/capdev"
    
    data = {
        "bucketName": bucket,
        "token": token,
        "environmentUrl": environment_url
    }

    if prompt is not None and prompt != "":
        data["prompt"] = prompt

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
    options=["STAR"],
    help="Select the project type to determine the correct folder structure"
)

if project_type == "STAR":
    base_folders = [
        "star/text-mining/files/test/",
        "star/text-mining/files/prod/"
    ]

folder_path = st.sidebar.selectbox(
    "Base Folder",
    options=base_folders,
    help="Select the base folder for document operations"
)

token = AUTH_TOKEN
environment_url = st.sidebar.text_input("Environment URL", value="https://management-allianceindicatorstest.ciat.cgiar.org/api/")

st.sidebar.markdown("---")
st.sidebar.caption("*AWS credentials are taken from your environment. Ensure `boto3` is authorized.*")


# =========================
# Main
# =========================
st.title("🧠 Bulk Upload - Text Mining Service")
st.markdown(
    "<div class='muted'>Upload a document or select one from S3, send it to the text-mining service, and visualize results.</div>",
    unsafe_allow_html=True
)

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
    if not bucket or not token or not environment_url:
        st.error("❌ _Please complete **S3 Bucket**, **Auth Token**, and **Environment URL** in the sidebar._")
    else:
        st.session_state["token"] = token
        st.session_state["environment_url"] = environment_url

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
                        token=token,
                        environment_url=environment_url,
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
                        token=token,
                        environment_url=environment_url,
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