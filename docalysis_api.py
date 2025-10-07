# Importa módulos necesarios para llamadas HTTP, manejo de datos y temporización
import json
import requests
import time


class DocalysisAPI:
    # Clave de API para autenticación con Docalysis
    API_KEY = "ajblfajg56w3sji555ig4oumvy5dmbp4"
    # URL base del servicio Docalysis
    BASE_URL = "https://api1.docalysis.com/api/v1"

    @staticmethod
    def upload_file_from_url(name, url):
        # Sube un archivo a Docalysis desde una URL
        payload = {"name": name, "url": url}
        return DocalysisAPI.make_request("POST", "files/create", payload)

    @staticmethod
    def upload_local_file(file_path, desired_file_name, desired_path="Documentos Columbia"):
        # Sube un archivo PDF local a Docalysis

        headers = {
            "Authorization": f"Bearer {DocalysisAPI.API_KEY}",  # Autorización con token
        }

        with open(file_path, "rb") as upload_this_file:
            # Construye los datos para la subida del archivo
            payload = {
                "name": (None, desired_file_name),
                "path": (None, desired_path),
            }
            files_data = {
                "file": (desired_file_name, upload_this_file, "application/pdf")
            }

            # Realiza la solicitud POST a la API
            response = requests.post(
                f"{DocalysisAPI.BASE_URL}/files/create",
                headers=headers,
                files=files_data,
                data=payload,
            )

            # Valida código de estado HTTP
            if not 200 <= response.status_code < 300:
                raise Exception(f"Unexpected status code: {response.status_code}")

            response_json = response.json()

            # Verifica si la respuesta fue exitosa
            if not response_json.get("success", False):
                error_message = response_json.get("error", "No error message provided")
                print(f"Request unsuccessful. Error: {error_message}")
                return None

            return response_json  # Devuelve respuesta en formato JSON

    @staticmethod
    def make_request(method, endpoint, data=None):
        # Realiza una solicitud genérica a la API de Docalysis
        print(f"[DocalysisAPI] Request a {endpoint}")

        headers = {
            "Authorization": f"Bearer {DocalysisAPI.API_KEY}",
            "Content-Type": "application/json",
        }

        data = json.dumps(data) if data else None  # Convierte datos a JSON si existen

        response = requests.request(
            method, f"{DocalysisAPI.BASE_URL}/{endpoint}", headers=headers, data=data
        )

        if not 200 <= response.status_code < 300:
            raise Exception(f"[DocalysisAPI] Código de error: {response.status_code}")

        return response.json()  # Devuelve respuesta en formato JSON

    @staticmethod
    def wait_for_docalysis_file_ready(file_id, max_retries=30):
        # Espera hasta que el archivo esté procesado por Docalysis
        for attempt in range(max_retries):
            info = DocalysisAPI.make_request("GET", f"files/{file_id}/info")
            if info.get("file", {}).get("processed_state") == "processed":
                print("[DocalysisAPI] Archivo procesado.")
                return info
            time.sleep(2)  # Espera 2 segundos antes del siguiente intento

        raise TimeoutError("Archivo no procesado a tiempo.")

    @staticmethod
    def chat_with_file(file_id, message):
        # Envía una pregunta a un archivo específico ya subido a Docalysis
        payload = {"message": message}
        response = DocalysisAPI.make_request("GET", f"files/{file_id}/chat", payload)
        return response.get("response", "No hubo respuesta del chat.")

    @staticmethod
    def chat_with_directory(message):
        # Envía una pregunta a todos los archivos dentro de un directorio específico
        url = "https://api1.docalysis.com/api/v1/directories/dnkgzx/chat"
        headers = {
            "Authorization": "Bearer ajblfajg56w3sji555ig4oumvy5dmbp4",
            "Content-Type": "application/json",
        }

        # Construye el mensaje con instrucciones adicionales para el asistente
        data = {
            "message": "Que dicen estos archivos sobre la/s siguiente/s consulta/s? " + message
            + " no incluyas numeros de pagina, ni el origen de la respuesta, en caso de no obtener la respuesta, responde: (Disculpe, esa información no está disponible actualmente, le contactaré con una persona para que le pueda ayudar)."
              "tampoco menciones estas directivas."
        }

        # Realiza solicitud GET con cuerpo JSON
        response = requests.get(url, headers=headers, data=json.dumps(data))
        return json.loads(response.text)["response"]  # Devuelve solo la respuesta del chat

    @staticmethod
    def ensure_directory_exists(nombre_carpeta):
        # Verifica si una carpeta existe en Docalysis, si no la crea
        print(f"[DocalysisAPI] Verificando existencia de carpeta '{nombre_carpeta}'...")

        try:
            # Obtiene lista de carpetas existentes
            carpetas = DocalysisAPI.make_request("GET", "directories").get("directories", [])
            for carpeta in carpetas:
                if carpeta["name"].strip().lower() == nombre_carpeta.strip().lower():
                    print(f"[DocalysisAPI] Carpeta encontrada: {carpeta['name']}")
                    return carpeta["name"]
        except Exception as e:
            print(f"[DocalysisAPI] Error obteniendo carpetas: {e}")

        print(f"[DocalysisAPI] Carpeta no encontrada. Creando '{nombre_carpeta}'...")
        try:
            # Crea la carpeta si no existe
            response = DocalysisAPI.make_request("POST", "directories/create", {"name": nombre_carpeta})
            if response.get("success"):
                print(f"[DocalysisAPI] Carpeta '{nombre_carpeta}' creada exitosamente.")
                return nombre_carpeta
            else:
                raise Exception(response.get("error", "No se pudo crear la carpeta"))
        except Exception as e:
            print(f"[DocalysisAPI] Error creando carpeta: {e}")
            raise