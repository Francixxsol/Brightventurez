
import requests

VTU_API_URL = "https://vtu.com.ng/API.php"
VTU_API_KEY = "3e1aafc7efe00b49a0f640049b7ac7"

def send_vtu_request(payload):
    payload["api_key"] = VTU_API_KEY
    try:
        res = requests.post(VTU_API_URL, data=payload, timeout=20)
        return res.json()
    except Exception as e:
        return {"status": "failed", "error": str(e)}
