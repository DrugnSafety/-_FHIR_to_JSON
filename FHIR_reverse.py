import json
import pandas as pd
import os
from xlsxwriter import Workbook

# Load the JSON data from a file
#file_path = '서울대_통합조정_20240507.json'
file_path = '충북대_통합조정_20240507.json'
#file_path = '경북대_통합조정_20240507.json'


with open(file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

entries = data.get('entry', [])

def extract_reaction_details(reactions):
    
    all_reactions = {
        "resource.reaction.allergy-reaction-causality": [],
        "resource.reaction.substance_info": [],
        "resource.reaction.manifestation": []
    }
    
    for reaction in reactions:
        # Extract extension valueCodeableConcept.coding.code
        causality_codes = [ext['valueCodeableConcept']['coding'][0]['code']
                           for ext in reaction.get('extension', [])
                           if 'valueCodeableConcept' in ext and 'coding' in ext['valueCodeableConcept']]
        if causality_codes:
            all_reactions["resource.reaction.allergy-reaction-causality"].extend(causality_codes)

        # Extract substance details
        substance_info = [
            "##".join([coding.get('system', ''), coding.get('code', ''), coding.get('display', '')])
            for coding in reaction.get('substance', {}).get('coding', [])
        ]
        all_reactions["resource.reaction.substance_info"].extend(substance_info)

        # Extract manifestation details
        manifestations = [
            "##".join([coding.get('system', ''), coding.get('code', ''), coding.get('display', '')])
            for manifestation in reaction.get('manifestation', [])
            for coding in manifestation.get('coding', [])
        ]
        all_reactions["resource.reaction.manifestation"].extend(manifestations)

    return all_reactions

def extract_risk_codes(extensions):
    known_risk = []
    potentially_crossreactive_risk = []
    no_known_risk = []

    for extension in extensions:
        if extension.get('url') == 'http://hl7.org/fhir/StructureDefinition/allergyintolerance-substanceExposureRisk':
            risk_category = None  # Reset risk category for each substanceExposureRisk extension
            substances = []
            
            # First determine the risk category from exposureRisk
            for sub_ext in extension.get('extension', []):
                if sub_ext.get('url') == 'exposureRisk':
                    risk_code = sub_ext.get('valueCodeableConcept', {}).get('coding', [{}])[0].get('code', '').lower()
                    if risk_code =='known-reaction-risk':
                        risk_category = 'known-reaction-risk'
                    elif risk_code == 'potentially-crossreactive-reaction-risk':
                        risk_category = 'potentially-crossreactive-reaction-risk'
                    elif risk_code == 'no-known-reaction-risk':
                        risk_category = 'no-known-reaction-risk'

            # Now process substances based on the determined risk category
            for sub_ext in extension.get('extension', []):
                if sub_ext.get('url') == 'substance':
                    for coding in sub_ext.get('valueCodeableConcept', {}).get('coding', []):
                        system = coding.get('system', '').replace('http://www.whocc.no/', '')
                        code = coding.get('code', '')
                        display = coding.get('display', '')
                        formatted_code = f"{system}##{code}##{display}"
                        
                        if risk_category == 'known-reaction-risk':
                            known_risk.append(formatted_code)
                        elif risk_category == 'potentially-crossreactive-reaction-risk':
                            potentially_crossreactive_risk.append(formatted_code)
                        elif risk_category == 'no-known-reaction-risk':
                            no_known_risk.append(formatted_code)

    return {
        "known-reaction-risk": known_risk,
        "potentially-crossreactive-reaction-risk": potentially_crossreactive_risk,
        "no-known-reaction-risk": no_known_risk
    }

# Function to extract manifestations
def extract_manifestations(extensions):
    manifestations = []
    for extension in extensions:
        if extension.get('url') == 'https://hins.or.kr/fhir/Allergy-MyHealthWay/StructureDefinition/allergy-manifestation':
            for coding in extension.get('valueCodeableConcept', {}).get('coding', []):
                system = coding.get('system', '')
                code = coding.get('code', '')
                display = coding.get('display', '')
                manifestations.append(f"{system}##{code}##{display}")
    return {"manifestations": manifestations}

# Extracting all required details from the entries
extracted_data = []
for entry in entries:
    resource = entry.get('resource', {})
    reaction_details = extract_reaction_details(resource.get('reaction', []))
    risk_codes = extract_risk_codes(resource.get('extension', []))
    extension_manifestation = extract_manifestations(resource.get('extension', []))

    resource_dict = {
        'resource.id': resource.get('id', ''),
        'resource.meta.lastUpdated': resource.get('meta', {}).get('lastUpdated', ''),
        'resource.meta.source': resource.get('meta', {}).get('source', ''),
        'resource.identifier.system': next((identifier.get('system', '') for identifier in resource.get('identifier', []) if identifier.get('system')), ''),
        'resource.identifier.value': next((identifier.get('value', '') for identifier in resource.get('identifier', []) if identifier.get('value')), ''),
        'resource.clinicalStatus.coding.system': next((coding.get('system', '') for coding in resource.get('clinicalStatus', {}).get('coding', []) if coding.get('system')), ''),
        'resource.clinicalStatus.coding.code': next((coding.get('code', '') for coding in resource.get('clinicalStatus', {}).get('coding', []) if coding.get('code')), ''),
        'resource.category': ', '.join(resource.get('category', [])),
        'resource.criticality': resource.get('criticality', ''),
        'resource.patient.resource': resource.get('patient', {}).get('reference', ''),
        'resource.onsetDateTime': resource.get('onsetDateTime', ''),
        'resource.recordedDate': resource.get('recordedDate', ''),
        'resource.asserter.reference': resource.get('asserter', {}).get('reference', ''),
        'resource.note.text': ' '.join(note.get('text', '') for note in resource.get('note', [])),
        'resource.reaction.description': ' '.join(reaction.get('description', '') for reaction in resource.get('reaction', [])),
        'resource.reaction.onset': ' '.join(reaction.get('onset', '') for reaction in resource.get('reaction', [])),
        'resource.reaction.severity': ' '.join(reaction.get('severity', '') for reaction in resource.get('reaction', [])),
        'resource.extension.risk_codes.known-reaction-risk': risk_codes['known-reaction-risk'],
        'resource.extension.risk_codes.potentially-crossreactive-risk': risk_codes['potentially-crossreactive-reaction-risk'],
        'resource.extension.risk_codes.no-known-reaction-risk': risk_codes['no-known-reaction-risk'],
        #'resource.extension.manifestations': json.dumps(extract_manifestations(resource.get('extension', [])), ensure_ascii=False),
        'resource.extension.manifestations': extension_manifestation['manifestations'],
        'resource.reaction.allergy-reaction-causality': reaction_details['resource.reaction.allergy-reaction-causality'],  
        'resource.reaction.substance_info': reaction_details['resource.reaction.substance_info'],
        'resource.reaction.manifestation': reaction_details['resource.reaction.manifestation'],
    }
    extracted_data.append(resource_dict)

# Assuming 'extracted_data' is a list of dictionaries prepared earlier
df = pd.DataFrame(extracted_data)

# Setup Excel writer to write multiple sheets within a context manager
output_excel_path = file_path.split('_')[0]+"_"+'final_extracted_data_multiple_sheets.xlsx'

with pd.ExcelWriter(output_excel_path, engine='xlsxwriter') as writer:
    # Save the original DataFrame to the 'total' sheet
    df.to_excel(writer, sheet_name='total', index=False)

    # Columns to explode and convert to long format, each in its own sheet
    columns_to_explode = ['resource.extension.risk_codes.known-reaction-risk',
                          'resource.extension.risk_codes.potentially-crossreactive-risk',
                          'resource.extension.risk_codes.no-known-reaction-risk',
                          'resource.extension.manifestations',
                          'resource.reaction.substance_info', 
                          'resource.reaction.manifestation']

    for column in columns_to_explode:
        if column in df:
            df[column] = df[column].apply(lambda x: x if isinstance(x, list) else [])
            exploded_df = df.explode(column)
            split_columns = exploded_df[column].str.split('##', expand=True)
            # Define new column names based on the content of the exploded column
            split_columns.columns = [f'{column}_system', f'{column}_code', f'{column}_display']
            # Prepare the DataFrame to be written to Excel: include all columns not in columns_to_explode except the current one
            columns_to_keep = [col for col in df.columns if col not in columns_to_explode or col == column]
            final_df = pd.concat([exploded_df[columns_to_keep].drop(columns=[column]), split_columns], axis=1)
            # Remove any rows where the new split columns are empty
            final_df = final_df.dropna(subset=[f'{column}_code'])
            short_sheet_name = column.split('.')[-1][:31]  # Ensure the sheet name is within Excel's limits
            final_df.to_excel(writer, sheet_name=short_sheet_name, index=False)

# Print a success message
print(f"Data in long format has been saved to: {output_excel_path}")

# Saving to JSON
output_json_path = file_path.split('_')[0]+"_" + 'final_extracted_data.json'
with open(output_json_path, 'w', encoding='utf-8') as json_file:
    json.dump(extracted_data, json_file, ensure_ascii=False, indent=4)

print(f"Data saved to Excel: {output_excel_path}")
print(f"Data saved to JSON: {output_json_path}")
