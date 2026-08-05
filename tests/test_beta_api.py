import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_search():
    print("Testing /api/search...")
    try:
        res = requests.get(f"{BASE_URL}/api/search?query=react")
        if res.status_code == 200:
            data = res.json()
            print(f"  SUCCESS: Found {len(data)} results.")
        else:
            print(f"  FAILED: Status {res.status_code}")
    except Exception as e:
        print(f"  FAILED: {e}")

def test_chat():
    print("Testing /api/chat...")
    try:
        res = requests.post(f"{BASE_URL}/api/chat", json={"query": "What do I know about React?"})
        if res.status_code == 200:
            data = res.json()
            print(f"  SUCCESS: Got answer: {data['answer'][:50]}...")
            print(f"  Citations: {len(data['citations'])}")
        else:
            print(f"  FAILED: Status {res.status_code}")
    except Exception as e:
        print(f"  FAILED: {e}")

def test_attachments():
    print("Testing /api/attachments...")
    try:
        res = requests.get(f"{BASE_URL}/api/attachments")
        if res.status_code == 200:
            data = res.json()
            print(f"  SUCCESS: Found {len(data['data'])} attachments.")
        else:
            print(f"  FAILED: Status {res.status_code}")
    except Exception as e:
        print(f"  FAILED: {e}")

if __name__ == "__main__":
    test_search()
    test_chat()
    test_attachments()
