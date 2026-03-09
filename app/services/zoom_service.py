
import requests
import os
from base64 import b64encode

def get_zoom_access_token():
    client_id = os.getenv("ZOOM_CLIENT_ID")
    client_secret = os.getenv("ZOOM_CLIENT_SECRET")
    account_id = os.getenv("ZOOM_ACCOUNT_ID")
    
    url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={account_id}"
    
    # Base64 encoding for headers
    auth_header = b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    response = requests.post(url, headers=headers)
    return response.json().get("access_token")

def create_zoom_meeting(topic, start_time_str, duration=60):
    token = get_zoom_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "topic": topic,
        "type": 2,  # Scheduled meeting
        "start_time": start_time_str,  # Format: "2026-02-11T10:30:00Z"
        "duration": duration,
        "timezone": "Asia/Kolkata",
        "settings": {
            "host_video": True,
            "participant_video": True,
            "join_before_host": False,
            "mute_upon_entry": True,
            "waiting_room": True
        }
    }
    
    response = requests.post("https://api.zoom.us/v2/users/me/meetings", json=payload, headers=headers)
    return response.json()