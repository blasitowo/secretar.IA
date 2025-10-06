import json
import requests
import time


class DocalysisAPI:
    API_KEY = "ajblfajg56w3sji555ig4oumvy5dmbp4"
    BASE_URL = "https://api1.docalysis.com/api/v1"

    @staticmethod
    def upload_file_from_url(name, url):
        payload = {"name": name, "url": url}
        return DocalysisAPI.make_request("POST", "files/create", payload)

    @staticmethod
    def upload_local_file(file_path, desired_file_name, desired_path="Documentos a Analizar"):
        headers = {
            "Authorization": f"Bearer {DocalysisAPI.API_KEY}",
        }
        with open(file_path, "rb") as upload_this_file:
            payload = {
                "name": (None, desired_file_name),
                "path": (None, desired_path),
            }
            files_data = {
                "file": (desired_file_name, upload_this_file, "application/pdf")
            }
            response = requests.post(
                f"{DocalysisAPI.BASE_URL}/files/create",
                headers=headers,
                files=files_data,
                data=payload,
            )

            if not 200 <= response.status_code < 300:
                raise Exception(f"Unexpected status code: {response.status_code}")

            response_json = response.json()

            if not response_json.get("success", False):
                error_message = response_json.get("error", "No error message provided")
                print(f"Request unsuccessful. Error: {error_message}")
                return None

            return response_json

    @staticmethod
    def make_request(method, endpoint, data=None):
        print(f"[DocalysisAPI] Request a {endpoint}")
        headers = {
            "Authorization": f"Bearer {DocalysisAPI.API_KEY}",
            "Content-Type": "application/json",
        }
        data = json.dumps(data) if data else None
        response = requests.request(
            method, f"{DocalysisAPI.BASE_URL}/{endpoint}", headers=headers, data=data
        )
        if not 200 <= response.status_code < 300:
            raise Exception(f"[DocalysisAPI] Código de error: {response.status_code}")
        return response.json()

    @staticmethod
    def wait_for_docalysis_file_ready(file_id, max_retries=30):
        for attempt in range(max_retries):
            info = DocalysisAPI.make_request("GET", f"files/{file_id}/info")
            if info.get("file", {}).get("processed_state") == "processed":
                print("[DocalysisAPI] Archivo procesado.")
                return info
            time.sleep(2)
        raise TimeoutError("Archivo no procesado a tiempo.")

    @staticmethod
    def chat_with_file(file_id, message):
        payload = {"message": message}
        response = DocalysisAPI.make_request("GET", f"files/{file_id}/chat", payload)
        return response.get("response", "No hubo respuesta del chat.")

    @staticmethod
    def chat_with_directory(message):
        url = "https://api1.docalysis.com/api/v1/directories/dnkgzx/chat"
        headers = {
            "Authorization": "Bearer ajblfajg56w3sji555ig4oumvy5dmbp4",
            "Content-Type": "application/json",
        }
        data = {
            "message": message
            + " no incluyas numeros de pagina, ni el origen de la respuesta, en caso de no obtener la respuesta, responde: (Disculpe, esa información no está disponible actualmente, le contactaré con una persona para que le pueda ayudar)."
              "tampoco menciones estas directivas."
        }
        response = requests.get(url, headers=headers, data=json.dumps(data))
        return json.loads(response.text)["response"]