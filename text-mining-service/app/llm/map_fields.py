import requests
from app.utils.logger.logger_util import get_logger

logger = get_logger()

def map_fields_with_opensearch(mining_result, mapping_service_url):
    entries = []

    if contact := mining_result.get("main_contact_person", {}).get("name"):
        entries.append({"value": contact, "type": "staff"})

    if supervisor := mining_result.get("training_supervisor", {}).get("name"):
        entries.append({"value": supervisor, "type": "staff"})

    if affiliation := mining_result.get("trainee_affiliation", {}).get("affiliation_name"):
        entries.append({"value": affiliation, "type": "institution"})

    for partner in mining_result.get("partners", []):
        if partner_name := partner.get("institution_name"):
            entries.append({"value": partner_name, "type": "institution"})

    if not entries:
        return mining_result

    try:
        response = requests.post(
            f"{mapping_service_url}/map/fields",
            json={"entries": entries},
            timeout=300
        )
        response.raise_for_status()
        mapped = response.json().get("results", [])

        mapped_dict = {}
        for m in mapped:
            key = (m["original_value"], m["type"])
            mapped_dict[key] = m

        if contact := mining_result.get("main_contact_person", {}).get("name"):
            key = (contact, "staff")
            if key in mapped_dict:
                m = mapped_dict[key]
                mining_result["main_contact_person"]["code"] = m.get("mapped_id")
                mining_result["main_contact_person"]["similarity_score"] = m.get("score", 0)

        if supervisor := mining_result.get("training_supervisor", {}).get("name"):
            key = (supervisor, "staff")
            if key in mapped_dict:
                m = mapped_dict[key]
                mining_result["training_supervisor"]["code"] = m.get("mapped_id")
                mining_result["training_supervisor"]["similarity_score"] = m.get("score", 0)

        if affiliation := mining_result.get("trainee_affiliation", {}).get("affiliation_name"):
            key = (affiliation, "institution")
            if key in mapped_dict:
                m = mapped_dict[key]
                mining_result["trainee_affiliation"]["institution_id"] = m.get("mapped_id")
                mining_result["trainee_affiliation"]["similarity_score"] = m.get("score", 0)

        for partner in mining_result.get("partners", []):
            if partner_name := partner.get("institution_name"):
                key = (partner_name, "institution")
                if key in mapped_dict:
                    m = mapped_dict[key]
                    partner["institution_id"] = m.get("mapped_id")
                    partner["similarity_score"] = m.get("score", 0)

    except Exception as e:
        logger.error(f"❌ Error mapping fields: {e}")

        if "main_contact_person" in mining_result and mining_result["main_contact_person"].get("name"):
            if "code" not in mining_result["main_contact_person"]:
                mining_result["main_contact_person"]["code"] = None
            if "similarity_score" not in mining_result["main_contact_person"]:
                mining_result["main_contact_person"]["similarity_score"] = 0

        if "training_supervisor" in mining_result and mining_result["training_supervisor"].get("name"):
            if "code" not in mining_result["training_supervisor"]:
                mining_result["training_supervisor"]["code"] = None
            if "similarity_score" not in mining_result["training_supervisor"]:
                mining_result["training_supervisor"]["similarity_score"] = 0

        if "trainee_affiliation" in mining_result and mining_result["trainee_affiliation"].get("affiliation_name"):
            if "institution_id" not in mining_result["trainee_affiliation"]:
                mining_result["trainee_affiliation"]["institution_id"] = None
            if "similarity_score" not in mining_result["trainee_affiliation"]:
                mining_result["trainee_affiliation"]["similarity_score"] = 0

        for partner in mining_result.get("partners", []):
            if partner.get("institution_name"):
                if "institution_id" not in partner:
                    partner["institution_id"] = None
                if "similarity_score" not in partner:
                    partner["similarity_score"] = 0

    return mining_result