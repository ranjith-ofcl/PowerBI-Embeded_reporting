from models.reportconfig import ReportConfig
from models.embedtoken import EmbedToken
from models.embedconfig import EmbedConfig
from models.embedtokenrequestbody import EmbedTokenRequestBody
from flask import Flask, render_template, send_from_directory, abort, request, jsonify
import json
import requests
import msal
import os

app = Flask(__name__)
# Load configuration
app.config.from_object('config.BaseConfig')

def get_access_token():
    '''Generates and returns Access token'''
    response = None
    try:
        # Service Principal auth is to achieve App Owns Data Power BI embedding
        authority = app.config['AUTHORITY_URL'].replace('organizations', app.config['TENANT_ID'])
        clientapp = msal.ConfidentialClientApplication(app.config['CLIENT_ID'], client_credential=app.config['CLIENT_SECRET'], authority=authority)
        response = clientapp.acquire_token_for_client(scopes=app.config['SCOPE_BASE'])
        try:
            return response['access_token']
        except KeyError:
            raise Exception(response['error_description'])
    except Exception as ex:
        raise Exception('Error retrieving Access token\n' + str(ex))

def get_embed_params_for_single_report(workspace_id, report_id, additional_dataset_id=None):
    '''Returns: EmbedConfig: Embed token and Embed URL'''
    report_url = f'https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}'    
    access_tok = get_access_token()
    header = {
        'Content-Type': 'application/json', 
        'Authorization': 'Bearer ' + access_tok
    }
    api_response = requests.get(report_url, headers=header)
    if api_response.status_code != 200:
        abort(api_response.status_code, description=f'Error while retrieving Embed URL\n{api_response.reason}:\t{api_response.text}\nRequestId:\t{api_response.headers.get("RequestId")}')

    api_response = json.loads(api_response.text)
    report = ReportConfig(api_response['id'], api_response['name'], api_response['embedUrl'])
    dataset_ids = [api_response['datasetId']]

    # Appending additional dataset to the list to achieve dynamic binding later if required
    if additional_dataset_id is not None:
        dataset_ids.append(additional_dataset_id)
        
    embed_token = get_embed_token_for_single_report_single_workspace(report_id, dataset_ids, workspace_id)
    embed_config = EmbedConfig(embed_token.tokenId, embed_token.token, embed_token.tokenExpiry, [report.__dict__])
    return json.dumps(embed_config.__dict__)

def get_embed_token_for_single_report_single_workspace(report_id, dataset_ids, target_workspace_id=None):
    '''Returns: EmbedToken: Embed token'''
    request_body = EmbedTokenRequestBody()

    for dataset_id in dataset_ids:
        request_body.datasets.append({'id': dataset_id})

    request_body.reports.append({'id': report_id})

    if target_workspace_id is not None:
        request_body.targetWorkspaces.append({'id': target_workspace_id})

    # Generating Embed Token
    embed_token_api = 'https://api.powerbi.com/v1.0/myorg/GenerateToken'
    api_response = requests.post(embed_token_api, data=json.dumps(request_body.__dict__), headers=get_request_header())

    if api_response.status_code != 200:
        abort(api_response.status_code, description=f'Error while retrieving Embed token\n{api_response.reason}:\t{api_response.text}\nRequestId:\t{api_response.headers.get("RequestId")}')

    api_response = json.loads(api_response.text)
    embed_token = EmbedToken(api_response['tokenId'], api_response['token'], api_response['expiration'])
    return embed_token

def get_request_header():
    '''Returns: Dict: Request header'''
    return {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + get_access_token()}

def get_all_reports_in_workspace(workspace_id):
    '''Fetches all reports in the specified Power BI workspace'''
    report_url = f'https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports'
    header = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + get_access_token()}
    api_response = requests.get(report_url, headers=header)

    if api_response.status_code != 200:
        abort(api_response.status_code, description=f'Error while fetching reports\n{api_response.reason}:\t{api_response.text}\nRequestId:\t{api_response.headers.get("RequestId")}')

    return json.loads(api_response.text)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/getreports')
def getreports():
    workspace_id = app.config['WORKSPACE_ID']
    reports = get_all_reports_in_workspace(workspace_id)
    all_reports = {}
    for idx, report in enumerate(reports['value'], start=1):
        report_name = f"report{idx}"
        all_reports[report_name] = {
            'name': report['name'],
            'id': report['id'],
        }
    return all_reports

@app.route('/get_embed_info', methods=['POST'])
def get_embed_info():
    data = request.get_json()
    report_id = data.get('id')
    report_name = data.get('name')
    workspace_id = app.config['WORKSPACE_ID']
    report_configs = []
    embed_info = get_embed_params_for_single_report(workspace_id, report_id)
    report_config = {'reportId': report_id, 'reportName': report_name, 'embedInfo': embed_info}
    report_configs.append(report_config)

    return report_configs

if __name__ == '__main__':
    app.run()