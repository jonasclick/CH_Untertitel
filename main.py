import requests
import json
import time
from dotenv import load_dotenv
import os
import datetime

load_dotenv()

# Load the environment variable for API key
subscription_key = os.getenv('OCP_APIM_SUBSCRIPTION_KEY')

def request_transcription():
    # The URL for the API endpoint
    endpoint_url = "https://switzerlandnorth.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions"

    # The headers including the Ocp-Apim-Subscription-Key and Content-Type
    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key,
        "Content-Type": "application/json"
    }

    # The data payload as a Python dictionary
    data = {
        "displayName": "My Transcription",
        "description": "Speech Studio Batch speech to text",
        "locale": "en-us",
        "contentUrls": [
            "https://crbn.us/whatstheweatherlike.wav"
        ],
        "properties": {
            "wordLevelTimestampsEnabled": False,
            "displayFormWordLevelTimestampsEnabled": True,
            "diarizationEnabled": False,
            "punctuationMode": "DictatedAndAutomatic",
            "profanityFilterMode": "Masked"
        },
        "customProperties": {}
    }

    # Convert the data dictionary to a JSON string
    data_json = json.dumps(data)

    # Make the POST request
    response = requests.post(endpoint_url, headers=headers, data=data_json)

    # Check if the request was successful
    if response.status_code == 200 or response.status_code == 202 or response.status_code == 201:
        # Save the response to a file
        with open('initial-response.json', 'w') as file:
            json.dump(response.json(), file, indent=4)
        print("Request sent. Initial response saved to 'initial-response.json'.")
    else:
        print(f"Request failed with status code: {response.status_code}")
        print(f"Response: {response.text}")


def get_transcription_results():
    # Load the initial response from the JSON file
    with open('initial-response.json', 'r') as file:
        data = json.load(file)
    
    # Your subscription key and URLs from the initial response
    transcription_status_url = data.get('self')
    transcription_files_url = data.get('links', {}).get('files')

    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key
    }

    # Check the transcription job's status
    status_response = requests.get(transcription_status_url, headers=headers)
    if status_response.status_code == 200:
        status = status_response.json()['status']
        print("Transcription Status:", status)
        if status == "Succeeded":
            # Fetch the transcription result files
            files_response = requests.get(transcription_files_url, headers=headers)
            if files_response.status_code == 200:
                # Store JSON list of files in dictionary --> in davinci it would be only one file!
                files = files_response.json()['values']
                for file in files:
                    # Get the contentUrl for each transcription result file
                    if file['kind'] == 'Transcription':
                        transcription_file_url = file['links']['contentUrl']
                        # Download the transcription file content
                        transcription_content_response = requests.get(transcription_file_url)
                        if transcription_content_response.status_code == 200:
                            # adjust as necessary based on actual file format
                            transcription_content = transcription_content_response.json()

                            # Save the response to a file
                            with open('transcription-content.json', 'w') as file:
                                json.dump(transcription_content, file, indent=4)
                            print("Response saved to 'transcription-content.json'.")
                        else:
                            print("Failed to download transcription content.")
            else:
                print("Failed to fetch transcription result files.")
        else:
            print(f"Transcription is not yet completed. Status: {status}. Sleeping for 5 seconds...")
            time.sleep(5)
            get_transcription_results()
    else:
        print("Failed to check transcription status.")


# Convert an ISO 8601 duration to an SRT timestamp ––> This can only handle seconds. No minutes, hours yet.
def convert_to_srt_timestamp(iso_duration):
    # Remove the 'PT' prefix and the 'S' suffix
    seconds = float(iso_duration[2:-1])
    # Convert seconds to a time object
    time = datetime.timedelta(seconds=seconds)
    # Format the time object as an SRT timestamp
    return str(time)


def transcription_to_srt():
    # Import the JSON data from the transcription-content.json file
    with open('transcription-content.json', 'r') as file:
        data = json.load(file)
    
    # Strip the JSON to get only the displayWords
    display_words = data['recognizedPhrases'][0]['nBest'][0]['displayWords']

    with open('output.srt', 'w') as f:
        for i, word in enumerate(display_words, start=1):
            # Write the index
            f.write(str(i) + '\n')
            # Write the start and end timestamps
            start = convert_to_srt_timestamp(word['offset'])
            end = convert_to_srt_timestamp(word['duration'])
            f.write(start + ' --> ' + end + '\n')
            # Write the display text
            f.write(word['displayText'] + '\n\n')
    
    print("SRT file created.")


request_transcription()
get_transcription_results()
transcription_to_srt()