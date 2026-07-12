import requests

URL = "http://127.0.0.1:8000/chat"

for i in range(1, 51):
    response = requests.post(
        URL,
        json={
            "message": f"Dummy message {i}"
        }
    )

    print(i, response.status_code)

print("Done")