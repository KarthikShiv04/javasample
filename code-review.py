import os

import requests
import openai
from github import Github

# GitHub Keys
GH_TOKEN = os.getenv('GH_TOKEN') # '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' 
GITHUB_PR_ID = os.getenv('GITHUB_PR_ID') #6
GITHUB_REPOSITORY = os.getenv('GITHUB_REPOSITORY') #interactivedevops/codereview

# Define your SonarQube server URL and authentication token
SONARQUBE_URL = os.getenv('SONARQUBE_URL') # 'http://3.6.87.81:9000'
SONARQUBE_TOKEN = os.getenv('SONARQUBE_TOKEN') #'sqa_3b1cb7e9555bcd73a97f9c8b16a52fe6849c5aa9'
SONARQUBE_PROJECT_KEY = os.getenv('SONARQUBE_PROJECT_KEY') #'chatgpt-CodeReview' 

# Define your ChatGPT API endpoint and API key
CHATGPT_API_URL = os.getenv('CHATGPT_API_URL') # 'https://htcazureopenai.openai.azure.com/'
CHATGPT_API_KEY = os.getenv('CHATGPT_API_KEY') #'1ab8fed99fe74bf7b922d020a6ec1b98'
CHATGPT_DEPLOYMENT_ID = os.getenv('CHATGPT_DEPLOYMENT_ID') # 'gpt-35-turbo'

# Function to fetch SonarQube issues
g = Github(login_or_token=GH_TOKEN)


def fetch_sonarqube_issues():
    issues_url = f'{SONARQUBE_URL}/api/issues/search'
    params = {
        'componentKeys': SONARQUBE_PROJECT_KEY,
        'severities': 'BLOCKER, CRITICAL, MAJOR, MINOR',
        'resolved': 'false',  # Get unresolved issues
        'ps': 100,  # Number of issues to retrieve (adjust as needed)
    }

    headers = {
        'Authorization': f'Bearer {SONARQUBE_TOKEN}',
    }

    try:
        response = requests.get(issues_url, params=params, headers=headers)
        response.raise_for_status()  # Raise an exception for bad responses (e.g., 404, 500)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching SonarQube issues: {e}")
        return None


# Function to generate code review comments using ChatGPT
def generate_code_review_comments(sonarqube_issues):
    if sonarqube_issues is None:
        return []  # Return an empty list if there was an issue with fetching SonarQube issues
    comments = []
    print("no. of issues {}".format(len(sonarqube_issues['issues'])))

    for issue in sonarqube_issues['issues']:
        # Extract relevant information from SonarQube issue
        issue_key = issue['key']
        issue_message = issue['message']

        # Prepare a message to send to ChatGPT
        chatgpt_input = f"SonarQube issue {issue_key}: {issue_message}"

        # Send the message to ChatGPT for review
        print(chatgpt_input)
        chatgpt_response = send_message_to_chatgpt(chatgpt_input)

        # Extract ChatGPT's response with suggested fixes
        suggested_fixes = chatgpt_response.get('choices', [{'message': 'No suggested fixes available.'}])[0]['message']

        file_name = issue['component']
        severity = issue['severity']
        line = issue['line']
        type = issue['type']
        add_pr_comment(file_name, severity, line, type, suggested_fixes)

    return comments


# add comment in PR
def add_pr_comment(file_name, severity, line, type, message):
    print(file_name)
    print(message)
    # repo = g.get_repo(os.getenv('GITHUB_REPOSITORY'))
    repo = g.get_repo(GITHUB_REPOSITORY)
    pull_request = repo.get_pull(int(GITHUB_PR_ID))

    if check_fileexist_in_commit(pull_request, file_name):
        pr_comment = f"<b> File name: </b> {file_name} \n<b> Severity: </b> {severity} \n<b> Line no: </b> {line} \n<b> " \
                     f"Type: </b> {type} \n\n <b>Review comment by ChatGPT about `{file_name}`</b>:\n {message['content']}"
        pull_request.create_issue_comment(pr_comment)


def check_fileexist_in_commit(pull_request, file_name):
    commits = pull_request.get_commits()
    actual_filename = file_name.split(':')[1]
    print(f"actual_filename : {actual_filename}")
    for commit in commits:
        files = commit.files
        print(files)
        for file in files:
            filename = file.filename
            if filename.__contains__(actual_filename):
                print(f"commit file {file} and actual file {actual_filename}")
                return True
    return False


# Function to send a message to ChatGPT for review
def send_message_to_chatgpt(message):
    headers = {
        'Authorization': f'Bearer {CHATGPT_API_KEY}',
        'Content-Type': 'application/json',
    }
    analysis_input = f"Please review the following application code technically: {message}"
    data = [{"role": "system",
             "content": "You are a Senior Developer/Engineer, provide the fix for below SonarQube findings for "
                        "developers to fixed it in their code"},
            {"role": "system", "content": analysis_input}]

    try:
        openai.api_key = CHATGPT_API_KEY
        openai.api_base = CHATGPT_API_URL
        openai.api_type = "azure"
        openai.api_version = "2023-05-15"

        analysis_response = openai.ChatCompletion.create(
            engine=CHATGPT_DEPLOYMENT_ID,
            deployment_id=CHATGPT_DEPLOYMENT_ID,
            messages=data,
            temperature=0
        )
        return analysis_response.to_dict()
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to ChatGPT: {e}")
        return {'choices': [{'text': 'Error communicating with ChatGPT.'}]}


if __name__ == "__main__":
    sonarqube_issues = fetch_sonarqube_issues()
    code_review_comments = generate_code_review_comments(sonarqube_issues)
    # code_review_comments = []
    # Print or process the code review comments as needed
    for comment in code_review_comments:
        print(comment)
