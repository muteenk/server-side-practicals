from re import L
from fastapi._compat.v2 import Url
import requests
from datetime import datetime
import threading

CAP = 200
BASE_URL = "http://127.0.0.1:9000"
user_ids: list[str] = []


def _request_server(url: str, method: str, payload: dict):
    try:
        res = requests.request(method=method, url=url, json=payload, timeout=10)
        data = res.json()
        data = data['data']
        user_ids.append(data['user_id'])
    except Exception as e:
        print("[ ERR ] >>> Request failed: ", str(e))    


def add_users():
    print("# --- ADDING USERS --- #\n")
    # success, fail = 0, 0
    local_threads: list[threading.Thread] = []
    for i in range(CAP):
        username = f"temp-{i+100}-{datetime.now()}"
        email = f"{username}@email.com"
        payload = {'username': username, 'email': email}
        t = threading.Thread(target=_request_server, args=(f"{BASE_URL}/users/add", 'post', payload))
        local_threads.append(t)
    
    for t in local_threads:
        t.start()

    for t in local_threads:
        t.join()

def get_users():
    print("# --- GETTING USERS --- #\n")
    success, fail = 0, 0
    for user_id in user_ids:
        res = requests.get(f"{BASE_URL}/users/profile", timeout=10, headers={'x-user-id': user_id})
        if res.status_code == 200:
            print(res.json())
            success+=1
        else:
            print(res.text)
            fail += 1

    print("SUCCESS: ", success)
    print("FAIL: ", fail)

if __name__ == "__main__":
    add_users()
    print(user_ids)
    get_users()