# Importa la clase DocalysisAPI desde el módulo docalysis_api
from docalysis_api import DocalysisAPI


# Función principal para enviar un mensaje a Docalysis y obtener una respuesta
def enviar_mensaje_completo(mensaje):
    try:
        print("[conexionApi] Enviando mensaje a Docalysis...")

        # Sección comentada para subir un archivo local a Docalysis:
        # response_data = DocalysisAPI.upload_local_file(
        #     r"C:\Users\Desarrollo 2\Downloads\ID610-F1-20170516-codigo.pdf",
        #     "codigo_etica.pdf"
        # )
        #
        # if not response_data:
        #     return "Error: No se pudo subir el archivo."
        #
        # file_id = response_data['file']['id']
        #
        # DocalysisAPI.wait_for_docalysis_file_ready(file_id)

        # Sección comentada para interactuar con un archivo específico:
        # respuesta = DocalysisAPI.chat_with_file(file_id, mensaje)

        # Chatea con un directorio de archivos en Docalysis usando el mensaje recibido
        respuesta = DocalysisAPI.chat_with_directory(mensaje)

        # Devuelve la respuesta generada por Docalysis
        return f"Respuesta de Docalysis:\n{respuesta}"

    except Exception as e:
        # Captura y devuelve cualquier error ocurrido durante la ejecución
        return f" Error: {str(e)}"