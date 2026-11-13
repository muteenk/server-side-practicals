import requests
from datetime import datetime

CAP = 200
BASE_URL = "http://127.0.0.1:9000"
user_ids: list[str] = []

def add_users():
    print("# --- ADDING USERS --- #\n")
    success, fail = 0, 0
    for i in range(CAP):
        username = f"temp-{i+100}-{datetime.now()}"
        email = f"{username}@email.com"
        payload = {'username': username, 'email': email}
        res = requests.post(f"{BASE_URL}/users/add", json=payload, timeout=10)
        if res.status_code in (200, 201):
            data = res.json()
            data = data['data']
            user_ids.append(data['user_id'])
            success += 1
        else:
            print(res.status_code)
            print(res.text)
            fail += 1

    print("SUCCESS: ", success)
    print("FAIL: ", fail)

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
    get_users()