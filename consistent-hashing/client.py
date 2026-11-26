import requests
from datetime import datetime
import threading
import time

CAP = 200
BASE_URL = "http://127.0.0.1:9000"
user_ids: list[str] = []


def _request_server(url: str, method: str, payload: dict | None, headers: dict | None):
    try:
        res = requests.request(method=method, url=url, json=payload, timeout=10, headers=headers)
        res.raise_for_status()
        body = res.json()
        data = body.get("data") or {}
        # POST /users/add returns user_id; GET /users/profile returns uuid
        if method.lower() == "post" and "user_id" in data:
            user_ids.append(data["user_id"])
        print("[ SUC ] >>> Request Success: ", res.text)
    except Exception as e:
        print("[ ERR ] >>> Request failed: ", str(e))


def add_users():
    print("# --- ADDING USERS --- #\n")
    local_threads: list[threading.Thread] = []
    for i in range(CAP):
        username = f"temp-{i+100}-{datetime.now()}"
        email = f"{username}@email.com"
        payload = {'username': username, 'email': email}
        t = threading.Thread(target=_request_server, args=(f"{BASE_URL}/users/add", 'post', payload, None))
        local_threads.append(t)
    
    for t in local_threads:
        t.start()

    for t in local_threads:
        t.join()

def get_users():
    print("# --- GETTING USERS --- #\n")
    local_threads: list[threading.Thread] = []
    for user_id in user_ids:
        t = threading.Thread(
            target=_request_server, 
            args=(
                f"{BASE_URL}/users/profile", 
                'get', 
                None, 
                {'x-user-id': user_id}
            )
        )
        local_threads.append(t)

    for t in local_threads:
        t.start()

    for t in local_threads:
        t.join()

if __name__ == "__main__":
    while True:
        inp = input(">>> ")
        if inp == 'a':
            add_users()
        elif inp == 'f':
            get_users()