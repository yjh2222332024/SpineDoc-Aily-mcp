
import httpx
import json

def test_ark():
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer ark-d61ab9da-a6f4-4a5e-94b3-c1ca9c4874eb-0f8ce"
    }
    payload = {
        "model": "ep-20260423223132-gxqgd",
        "messages": [{"role": "user", "content": "ping"}]
    }

    print(f" [Test] Sending request to {url}...")
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=20.0)
        print(f" [Test] Status Code: {resp.status_code}")
        print(f" [Test] Response: {resp.text}")
    except Exception as e:
        print(f" [Test] Request failed: {e}")

if __name__ == "__main__":
    test_ark()
