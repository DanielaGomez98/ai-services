DEFAULT_PROMPT_AICCRA = """
Analyze the provided document(s) and extract all results related **only** to the indicator:
    • "Innovation Development"

If no relevant information for either indicator is found, do not assume or invent data. Instead, return a JSON object with an empty array of results, like this:

{
    "results": []
}

⸻

Instructions for Each Identified Result:

Your task is to identify and extract **only Innovation Development** results using the definitions, examples, and field structure below.

Indicator Definition:
• Refers to a new, improved, or adapted output or groups of outputs such as technologies, products and services, policies, and other organizational and institutional arrangements with high potential to contribute to positive impacts when used at scale.
• Possible keywords: innovation, new technology, new product, new service, readiness level.

⸻

Output Fields for Each Result:

Result Title
    • title
    • Identify the exact title of the result as stated in the document.
    • If no title is mentioned explicitly, try to infer a concise title that accurately reflects the content of the result.

Short Title:
    • short_title
    • Provide a short name that facilitates clear communication about the innovation for a non-specialist reader and without acronyms. No more than 10 words.

Result Description
    • description
    • Provide a brief description of the result.

Alliance Main Contact Person
    • Extract the contact's name into the following field as an object:
        • main_contact_person: {"name": "..."}
    • Look for any mention or indication of the primary Alliance contact in the document (e.g., "Alliance focal point," "main Alliance contact," "Alliance coordinator," or a named person specifically flagged as responsible).
    • If no specific name or contact is mentioned, do not return the field in the output JSON.

Keywords
    • keywords
    • List relevant keywords in lowercase, as an array of strings.

Geoscope (Geographical Scope)
    • For each result, specify:
        • geoscope_level:
            • "Global": if the document does not specify a region or country.
            • "Regional": if the document mentions ONLY the region, but does not specify countries. If the document specifies countries within the region, it should be classified as "National".
            • "National": if the document mentions one or more countries, but does not specify sub-national areas.
            • "Sub-national": if the document mentions specific locations within a country.
            • "This is yet to be determined"
        • regions and countries:
            • If level = "Regional", return an array with the appropriate UN49 region code(s) as numbers:
                (e.g., regions: [150, 2] (150 for Europe region and 2 for Africa region)).
            • If level = "National", return an array with objects containing the ISO Alpha-2 country code(s):
                (e.g., countries: [{"code": "KE"}, {"code": "UG"}]).
            • If level = "Sub-national", return an array of objects, each containing the country code and an array with the appropriate ISO 3166-2 code(s) for the subnational areas. 
              Use your knowledge of ISO 3166-2 subnational codes to provide the appropriate codes based on the location names mentioned in the document:
                (e.g., countries: [{"code": "CO", "areas": ["CO-CUN", "CO-CAS"]}]).
            • If not applicable, do not return the regions or countries field in the output JSON.

Innovation Nature:
    • innovation_nature
    • Must be one of the following predefined values:
        • "Incremental innovation": Innovations that already exist and undergo constant, steady progress, and improvement.
        • "Radical innovation": Innovations that are new and replace existing products, systems, services and/or policies but do not cause or require major reconfiguration of farming, market and/or policy/ business models.
        • "Disruptive innovation": Innovations that are new and cause or require major reconfiguration of farming, market and/or policy/ business models.
        • "Other": Unknown or the characterization does not work for the innovation.
    • If the document does not specify the nature of the innovation, or it cannot be deduced, return "Other".
    • If the document provides a specific nature, use that value.

Innovation Type:
    • innovation_type
    • Must be one of the following predefined values:
        • "Technological innovation": Innovations of technical/ material nature, including varieties/ breeds; crop and livestock management practices; machines; processing technologies; big data and information systems.
        • "Capacity development innovation": Innovations that strengthen capacity, including farmer, extension or investor decision-support services; accelerator/ incubator programs; manuals, training programs and curricula; online courses.
        • "Policy, organizational or institutional innovation": Innovations that create enabling conditions, including policy, legal and regulatory frameworks; business models; finance mechanisms; partnership models; public/ private delivery strategies.
        • "Other": Unknown or the type does not work for the innovation.
    • If the document does not specify the type of innovation, or it cannot be deduced, return "Other".
    • If the document provides a specific type, use that value.

How would you assess the current readiness of this innovation?
    • assess_readiness
    • At the output level, a single readiness score is given for the innovation, irrespective of the specific geo-location where the innovation is being designed, tested and/or scaled. If you need help, use the Scaling Readiness Calculator for guidance.
    • This is the Scaling Readiness Calculator:
        • Level 0: Idea - The innovation is at idea stage.
        • Level 1: Basic Research - The innovation's basic principles are being researched for their ability to achieve a specific impact.
        • Level 2: Formulation - The innovation's key concepts are being formulated or designed.
        • Level 3: Proof of Concept - The innovation's key concepts have been validated for their ability to achieve a specific impact.
        • Level 4: Controlled Testing - The innovation is being tested for its ability to achieve a specific impact under fully-controlled conditions.
        • Level 5: Model/Early Prototype - The innovation is validated for its ability to achieve a specific impact under fully-controlled conditions.
        • Level 6: Semi-Controlled Testing - The innovation is being tested for its ability to achieve a specific impact under semi-controlled conditions.
        • Level 7: Prototype - The innovation is validated for its ability to achieve a specific impact under semi-controlled conditions.
        • Level 8: Uncontrolled Testing - The innovation is being tested for its ability to achieve a specific impact under uncontrolled conditions.
        • Level 9: Proven Innovation - The innovation is validated for its ability to achieve a specific impact under uncontrolled conditions.
    • Must be defined as a number between 0 and 9. Just use the number, not the description.
    • If the document does not specify the readiness level, or it cannot be deduced, do not return the field in the output JSON.
    • If the document provides a specific readiness level, use that value.
    • If the document provides a description of the readiness level, map it to the corresponding number based on the Scaling Readiness Calculator.
    • If the document provides multiple readiness levels, use the highest level mentioned. For example, if it is level 7 in Kenya, level 3 in Peru and level 5 in India, only the highest score for the generic rank is retained.

Who would be the anticipated user(s) of this innovation?
    • anticipated_users
    • Must be one of the following predefined values:
        • "This is yet to be determined": If the document does not specify the users or it cannot be deduced.
        • "Users have been determined": If the document specifies or implies any direct or potential users of the innovation.
    • ONLY INCLUDE individuals or organizations that are direct or potential users or beneficiaries of the innovation — those who apply, adopt, or benefit from it. 
    • DO NOT INCLUDE funders, donors, implementing partners, or supporting organizations unless they are also users.
    • If at least one actor is mentioned in the document that fits this definition, select "Users have been determined" and extract the relevant actor(s) under innovation_actors.

Actors involved in the innovation:
    • innovation_actors_detailed
    • This field is used ONLY if the anticipated_users is "Users have been determined".
    • Do not include organizations, this field is only for individual actors.
    • Include the names, types, genres and ages of all individuals mentioned in the document that are potential or actual users or beneficiaries of the innovation.
    • Return a list of objects. Each object must include:
        • name: Full name of the actor, or "Not collected" if only the role or type is known.
        • type: Must be one or more of the following predefined values:
            • "Farmers / (agro)pastoralist / herders / fishers"
            • "Researchers"
            • "Extension agents"
            • "Policy actors (public or private)"
            • "Other"
        • other_actor_type: If the type is "Other", this field must contain information about the type of actor involved in the innovation that does not fit into the predefined values. If the type is not "Other", this field should not be included in the output JSON.
        • gender_age: Must be an array with one or more of the following predefined values, which defines the gender and age of the actor:
            • "Women: Youth"
            • "Women: Non-youth"
            • "Men: Youth"
            • "Men: Non-youth"
    • For gender_age, use the following definitions:
        • Youth = 15 to 24 years old
        • Non-youth = older than 24
    • If the document provides gender but not age:
        • Return both youth and non-youth for that gender (e.g., ["Women: Youth", "Women: Non-youth"])
    • If the document provides age but not gender:
        • Return both genders for that age group (e.g., ["Men: Youth", "Women: Youth"])
    • Do NOT create multiple entries for the same actor with different gender/age combinations.
    • If the document does not provide enough information, you may include partial entries (e.g., name and type only).
    • If anticipated_users is "This is yet to be determined", do not include this field in the output JSON.

Organizations involved in the innovation (detailed):
    • organizations_detailed
    • This field is used ONLY if the anticipated_users is "Users have been determined".
    • Return a list of organization objects. Each object must include:
        • name: Full name of the organization that is potential or actual user or beneficiary of the innovation.
        • type: Must be one or more of the following predefined values:
            • "NGO"
            • "Research organizations and universities"
            • "Organization (other than financial or research)"
            • "Government"
            • "Financial institution"
            • "Private company (other than financial)"
            • "Public-Private Partnership"
            • "Foundation"
            • "Other"
        • sub_type: 
            • This field is used ONLY if the organization_type is "NGO" or "Research organizations and universities" or "Organization (other than financial or research)" or "Government" or "Financial Institution".
            • If the organization_type is "Private company (other than financial)", "Public-Private Partnership", "Foundation", or "Other", this field should not be included in the output JSON.
            • If you do not know the sub-type, return "Not collected".
            • If the organization_type is "NGO", it must be one of the following predefined values:
                • NGO International
                • NGO International (General)
                • NGO International (Farmers)
                • NGO Regional
                • NGO Regional (General)
                • NGO Regional (Farmers)
                • NGO National
                • NGO National (General)
                • NGO National (Farmers)
                • NGO Local
                • NGO Local (General)
                • NGO Local (Farmers)
            • If the organization_type is "Research organizations and universities", it must be one of the following predefined values:
                • Research organizations and universities International
                • Research organizations and universities International (General)
                • Research organizations and universities International (Universities)
                • Research organizations and universities International (CGIAR)
                • Research organizations and universities Regional
                • Research organizations and universities Regional (NA)
                • Research organizations and universities Regional (Universities)
                • Research organizations and universities National
                • Research organizations and universities National (NARS)
                • Research organizations and universities National (Universities)
                • Research organizations and universities Local
                • Research organizations and universities Local (NA)
                • Research organizations and universities Local (Universities)
            • If the organization_type is "Organization (other than financial or research)", it must be one of the following predefined values:
                • Organization (other than financial or research) International
                • Organization (other than financial or research) Regional
            • If the organization_type is "Government", it must be one of the following predefined values:
                • Government (National)
                • Government (Subnational)
            • If the organization_type is "Financial institution", it must be one of the following predefined values:
                • Financial Institution
                • Financial Institution International
                • Financial Institution Regional
                • Financial Institution National
                • Financial Institution Local
        • other_type: Include ONLY if type is "Other"; otherwise do not include this field. This field should contain information about the type of organization involved in the innovation that does not fit into the predefined values.
    • Do not include individuals in this field; individuals should be captured under innovation_actors_detailed.
    • If anticipated_users is "This is yet to be determined", do not include this field in the output JSON.

⸻

Output Format:

Return dates in YYYY-MM-DD format when available.
Your output must be a single valid JSON object, and must not include any additional text, comments, footnotes, citations, or explanations.

**IMPORTANT: Only include fields in the JSON when information is found in the document or inferred by you. Do not include fields with null values or missing information - simply omit them entirely from the output.**

Required and mandatory fields:
• indicator
• title
• short_title
• description
• keywords
• geoscope_level

Do not:
• Add text before or after the JSON.
• Add any explanatory sentences, notes, or references (e.g., "This result is extracted from…").
• Include markdown code blocks like ```json or ```.
• Escape quotes unless necessary.
• Wrap the JSON in additional quotes or strings.
• Include fields with null values - omit them completely.
The response must be raw JSON only — nothing else.

⸻

Follow this exact structure:

{
    "results": [
        {
            "indicator": "<'Innovation Development'>",
            "title": "<result title>",
            "short_title": "<short result title>",
            "description": "<result description>",
            "main_contact_person": {
                "name": "<value>"
            },
            "keywords": [
                "<keyword1>",
                "<keyword2>",
                "..."
            ],
            "geoscope_level": "<Global | Regional | National | Sub-national | This is yet to be determined>",
            "regions": [<UN49 region code 1>, <UN49 region code 2>, ...] (only if geoscope_level is Regional),
            "countries": [
                {
                    "code": "<ISO Alpha-2 country code (if geoscope_level is National or Sub-national)>",
                    "areas": ["<ISO 3166-2 subnational area code 1>", "<ISO 3166-2 subnational area code 2>"] (only if geoscope_level is Sub-national)
                }
            ] (only if geoscope_level is National or Sub-national),
            "innovation_nature": "<value or 'Other'>",
            "innovation_type": "<value or 'Other'>",
            "assess_readiness": "<number between 0 and 9>",
            "anticipated_users": "<This is yet to be determined | Users have been determined>",
            "innovation_actors_detailed": [
                {
                    "name": "<actor name or 'Not collected' (only if anticipated_users is 'Users have been determined'>",
                    "type": "<value or 'Other' (only if anticipated_users is 'Users have been determined')>",
                    "other_actor_type": "<value or 'Not collected' (only if type is 'Other')>",
                    "gender_age": "<[array of values] or null>"
                }
            ],
            "organizations_detailed": [
                {
                    "name": "<organization name or 'Not collected' (only if anticipated_users is 'Users have been determined' and indicator is 'Innovation Development')>",
                    "type": "<value(s) or 'Other' (only if anticipated_users is 'Users have been determined' and indicator is 'Innovation Development')>",
                    "sub_type": "<value or 'Not collected' (only if indicator is 'Innovation Development')>",
                    "other_type": "<value or 'Not collected' (only if type is 'Other' and indicator is 'Innovation Development'; omit otherwise)>"
                }
            ]
        }
    ]
}
"""