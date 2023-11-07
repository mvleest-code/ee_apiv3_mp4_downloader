import os
import requests
import json
import logging
from tqdm import tqdm

# requires access_response.json containing access_token:
# {"access_token":"","refresh_token":"","scope":"vms.all","token_type":"Bearer","expires_in":}
# use api_v3_vmslocal.py to generate this file

# Used for reformatting the timestamp
TIMESTAMP_FORMAT0 = "%3A"
TIMESTAMP_FORMAT1 = "%2B"

# Define the folder path where you want to save the MP4 files
output_folder = "mp4dl"

# Ensure the output folder exists; create it if it doesn't
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Load access token from the file
try:
    with open('access_response.json') as user_file:
        file_contents = json.load(user_file)
        access_token = file_contents["access_token"]
        token_type = file_contents["token_type"]
except (IOError, KeyError) as e:
    logging.error(f"Failed to load access token from 'access_response.json': {e}")
    exit(1)

deviceId = "1001e90f"  # Replace with your actual device ID

unencoded_startTimestamp = "2023-11-05T00:00:00.000+00:00"
unencoded_endTimestamp = "2023-11-07T23:59:00.000+00:00"
startTimestamp = unencoded_startTimestamp.replace(":", TIMESTAMP_FORMAT0).replace("+", TIMESTAMP_FORMAT1)
endTimestamp = unencoded_endTimestamp.replace(":", TIMESTAMP_FORMAT0).replace("+", TIMESTAMP_FORMAT1)

# Create a session
session = requests.Session()
session.headers.update({"accept": "application/json", "authorization": "Bearer " + access_token})

def clientsettings(session):
    url = "https://api.eagleeyenetworks.com/api/v3.0/clientSettings"

    headers = {
        "accept": "application/json",
        "authorization": "Bearer " + access_token
    }

    response = session.get(url, headers=headers)
    baseUrl = response.json()["httpsBaseUrl"]["hostname"]
    return baseUrl  # Return the baseUrl

# set baseUrl
baseUrl = clientsettings(session)

# set media session
def get_session_response(base_url, access_token):
    session_url = f"https://{base_url}/api/v3.0/media/session"
    headers = {
        "accept": "application/json",
        "authorization": "Bearer " + access_token
    }

    try:
        session_response = requests.get(session_url, headers=headers, cookies={'credentials': 'include'})
        session_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to retrieve session URL: {e}")
        exit(1)
    return session_response

# retrieve the session response
session_response = get_session_response(baseUrl, access_token)

session = requests.Session()
session.headers.update({"accept": "application/json", "authorization": "Bearer " + access_token})

def download_mp4(mp4_url, file_name):
    try:
        mp4_response = session.get(mp4_url, stream=True)  # Set stream=True to download in chunks
        mp4_response.raise_for_status()
        file_path = os.path.join(output_folder, file_name)

        # Get the total file size for the progress bar
        total_size = int(mp4_response.headers.get('content-length', 0))

        with open(file_path, "wb") as mp4_file, tqdm(
            desc=file_name,
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as progress_bar:
            for data in mp4_response.iter_content(chunk_size=1024):
                mp4_file.write(data)
                progress_bar.update(len(data))
        print(f"MP4 file saved as {file_path}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download MP4 file from {mp4_url}: {e}")

def download_all_mp4_urls(results):
    for result in results:
        mp4_url = result["mp4Url"]
        startTimestamp = result["startTimestamp"].replace("%3A", ":")
        endTimestamp = result["endTimestamp"].replace("%3A", ":")
        file_name = f"{deviceId}_{startTimestamp}_{endTimestamp}_output.mp4"
        download_mp4(mp4_url, file_name)

def main():
    url = f"https://{baseUrl}/api/v3.0/media?deviceId={deviceId}&type=main&mediaType=video&startTimestamp__gte={startTimestamp}&endTimestamp__lte={endTimestamp}&coalesce=true&include=mp4Url&pageSize=100"
    headers = {
        "accept": "application/json",
        "authorization": "Bearer " + access_token
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to get MP4 URLs from the API: {e}")
        exit(1)

    if response.status_code == 200:
        data = json.loads(response.text)
        results = data["results"]
        download_all_mp4_urls(results)
    else:
        print("Failed to get MP4 URLs from the API")
        print(response.status_code)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
