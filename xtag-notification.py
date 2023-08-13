import requests
import json
import time
import os
import logging

API_KEY = ""
URL_DASHBOARD = "https://[company-name].vicarius.cloud/vicarius-external-data-api/endpoint/search"
WEBHOOK_URL = ""
ENDPOINTS_FILE = "notified_endpoints.txt"
RISK_FACTORS = set([
    "#has_exploit",
    "#easy_to_exploit",
    "#exposed_to_RCE_attack",
    "#exposed_to_DOS_Attack",
    "#exposed_to_credentials_stealing",
    "#critical_vulnerability",
    "#end_of_support"
])

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_notified_endpoints():
    if os.path.exists(ENDPOINTS_FILE):
        with open(ENDPOINTS_FILE, 'r') as f:
            return set(f.read().splitlines())
    return set()

def save_endpoints(endpoints):
    try:
        with open(ENDPOINTS_FILE, 'w') as f:
            for endpoint in endpoints:
                f.write(f"{endpoint}\n")
        logging.info("Successfully saved notified events.")
    except Exception as e:
        logging.error(f"Error saving notified events: {e}")

def send_notification_to_teams(endpoint_data):
    payload = {
        "@context": "http://schema.org/extensions",
        "@type": "MessageCard",
        "themeColor": "0078D7",
        "title": "Endpoint Exploitability Risk Factors Summary",
        "text": f"""**Endpoint ID:** {endpoint_data['id']}
**Endpoint Name:** {endpoint_data['name']}
**Risk Factor Term:** {endpoint_data['risk_term']}
**Risk Factor Description:** {endpoint_data['risk_description']}"""
    }
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = session.post(WEBHOOK_URL, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Error sending notification: {str(e)}")

def get_endpoint_scores():
    from_value = 0
    size_value = 100

    while True:
        params = {
            'from': from_value,
            'size': size_value,
            'includeFields': 'endpointId,endpointEndpointScores,endpointName',
        }

        try:
            response = session.get(URL_DASHBOARD, params=params)
            response.raise_for_status()
            
            data = response.json()
            if 'serverResponseObject' not in data or not data['serverResponseObject']:
                break
            
            for entry in data['serverResponseObject']:
                if entry['endpointName'].startswith('cl'):
                    for score in entry['endpointEndpointScores']['endpointScoresExploitabilityRiskFactors']:
                        unique_key = f"{entry['endpointId']}_{score['riskFactorTerm']}_{score['riskFactorDescription']}"
                        if score['riskFactorDescription'] in RISK_FACTORS and unique_key not in notified_endpoints:
                            send_notification_to_teams({
                                'id': entry['endpointId'],
                                'name': entry['endpointName'],
                                'risk_term': score['riskFactorTerm'],
                                'risk_description': score['riskFactorDescription']
                            })
                            notified_endpoints.add(unique_key)

            from_value += size_value
        
        except requests.RequestException as e:
            logging.error(f"Error fetching data: {str(e)}")
            break

if __name__ == "__main__":
    session = requests.Session()
    session.headers.update({
        'Accept': 'application/json',
        'Vicarius-Token': API_KEY,
    })
    
    notified_endpoints = load_notified_endpoints()

    while True:
        try:
            get_endpoint_scores()
        except Exception as e:
            logging.error(f"Error during execution: {e}")
        finally:
            save_endpoints(notified_endpoints)
            time.sleep(30)
