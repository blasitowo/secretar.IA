
from docalysis_api import DocalysisAPI

def enviar_mensaje_completo(mensaje):
    try:
        print("[conexionApi] Enviando mensaje a Docalysis...")

        response_data = DocalysisAPI.upload_local_file(
            "E:\Descargas\ID610-F1-20170516-codigo.pdf",
            "codigo_etica.pdf"
        )

        if not response_data:
            return "❌ Error: No se pudo subir el archivo."

        file_id = response_data['file']['id']

        # 2. Esperar que el archivo se procese
        DocalysisAPI.wait_for_docalysis_file_ready(file_id)

        # 3. Enviar el mensaje al chat
        respuesta = DocalysisAPI.chat_with_file(file_id, mensaje)
        return f"✅ Respuesta de Docalysis:\n{respuesta}"

    except Exception as e:
        return f"❌ Error: {str(e)}"