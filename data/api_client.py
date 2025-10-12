import requests

VTU_API_KEY = "3e1aafc7efe00b49a0f640049b7ac7"
VTU_API_URL = "https://vtu.com.ng/API/data"

def send_data_request(network, data_type, phone, size):
    payload = {
        "apikey": VTU_API_KEY,
        "network": network.lower(),
        "type": data_type.lower().replace(" ", "_"),
        "phone": phone,
        "size": size
    }

    response = requests.post(VTU_API_URL, data=payload)
    try:
        return response.json()
    except:
        return {"status": "error", "raw": response.text}
