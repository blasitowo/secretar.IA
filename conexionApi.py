from docalysis_api import DocalysisAPI


def enviar_mensaje_completo(mensaje):
    try:
        print("[conexionApi] Enviando mensaje a Docalysis...")

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

        # chatear con archivo
        # respuesta = DocalysisAPI.chat_with_file(file_id, mensaje)

        # chatear con directorio
        respuesta = DocalysisAPI.chat_with_directory(mensaje)

        return f"Respuesta de Docalysis:\n{respuesta}"

    except Exception as e:
        return f" Error: {str(e)}"
