# Importa módulos estándar y de Google necesarios para autenticación, acceso a Gmail/Drive y manipulación de archivos
import os
import os.path
import base64
import re
import io
import hashlib
from email import message_from_bytes
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from docalysis_api import DocalysisAPI  # API externa para subir y procesar archivos

# Define los permisos necesarios para acceder a Gmail y Google Drive
SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/drive.readonly']


def limpiar_mensaje(texto):
    """Limpia el cuerpo del correo: elimina HTML, firmas y espacios innecesarios."""
    texto = re.sub(r'<[^>]+>', '', texto)  # Elimina etiquetas HTML
    texto = re.split(r'\n--+\s*\n', texto)[0]  # Elimina firmas comunes separadas por guiones
    texto = re.sub(r'\n{2,}', '\n\n', texto)  # Normaliza saltos de línea dobles
    return texto.strip()  # Elimina espacios en blanco al inicio y final


def conectar_gmail():
    creds = None

    # Crea el archivo credentials.json desde la variable de entorno si no existe
    if not os.path.exists("credentials.json"):
        credentials_env = os.getenv("GMAIL_CREDENTIALS_JSON")
        if credentials_env:
            with open("credentials.json", "w") as f:
                f.write(credentials_env)
        else:
            raise Exception("GMAIL_CREDENTIALS_JSON no está definido en el entorno.")

    # Crea el archivo token.json desde la variable de entorno si no existe
    if not os.path.exists("token.json"):
        token_env = os.getenv("GMAIL_TOKEN_JSON")
        if token_env:
            with open("token.json", "w") as f:
                f.write(token_env)

    # Carga las credenciales desde token.json si existe
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # Refresca o solicita nuevas credenciales si son inválidas
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())  # Refresca token expirado
        else:
            # Inicia flujo de autorización OAuth
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

            # Guarda el nuevo token en token.json
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)  # Retorna el servicio de Gmail


def conectar_drive():
    creds = None
    # Carga las credenciales desde token.json
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    return build('drive', 'v3', credentials=creds)  # Retorna el servicio de Drive


def obtener_archivos_en_drive(drive_service, folder_id):
    archivos = []
    # Consulta archivos PDF no eliminados en una carpeta específica
    query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed = false"
    response = drive_service.files().list(q=query, fields="files(id, name, modifiedTime)").execute()
    archivos = response.get('files', [])  # Obtiene la lista de archivos
    return archivos


def calcular_hash_archivo(file_path):
    # Calcula el hash SHA256 del archivo para detectar duplicados
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def descargar_y_subir_nuevos(drive_service, folder_id, carpeta_local="descargados_drive", carpeta_docalysis=None):
    # Crea carpeta local si no existe
    if not os.path.exists(carpeta_local):
        os.makedirs(carpeta_local)

    archivos = obtener_archivos_en_drive(drive_service, folder_id)
    hash_existentes = set()

    for archivo in archivos:
        file_id = archivo["id"]
        nombre = archivo["name"]
        destino = os.path.join(carpeta_local, nombre)

        # Omite descarga si el archivo ya existe localmente
        if os.path.exists(destino):
            hash_existentes.add(calcular_hash_archivo(destino))
            print(f"[SKIP] Ya existe localmente: {nombre}")
            continue

        print(f"[DESCARGANDO] {nombre}")
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.FileIO(destino, "wb")
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()  # Descarga por partes

        hash_archivo = calcular_hash_archivo(destino)

        # Elimina archivo si ya fue descargado previamente (duplicado por hash)
        if hash_archivo in hash_existentes:
            print(f"[SKIP] Archivo duplicado por hash: {nombre}")
            os.remove(destino)
            continue

        # Sube el archivo a Docalysis
        print(f"[UPLOAD] Subiendo {nombre} a Docalysis...")
        respuesta = DocalysisAPI.upload_local_file(destino, desired_file_name=nombre, desired_path=carpeta_docalysis)
        if respuesta:
            print(f"[OK] Subido {nombre} a Docalysis.")
        else:
            print(f"[ERROR] Fallo al subir {nombre}")

        hash_existentes.add(hash_archivo)


def es_correo_personal(mime_msg):
    from email.utils import parseaddr

    # Revisa cabeceras sospechosas de ser correos automáticos o de marketing
    headers = mime_msg.items()
    cabeceras_sospechosas = ["List-Unsubscribe", "Precedence", "Auto-Submitted"]
    for clave, valor in headers:
        if clave in cabeceras_sospechosas:
            return False
        if clave == "Return-Path" and any(x in valor.lower() for x in ["mailer", "bounce", "noreply", "no-reply"]):
            return False

    # Revisa el remitente por palabras clave típicas de correos automáticos
    remitente = mime_msg["From"]
    _, email = parseaddr(remitente)
    if any(x in email.lower() for x in ["no-reply", "noreply", "mailer", "notifications", "updates"]):
        return False

    # Rechaza dominios de empresas conocidas por enviar correos automatizados
    dominios_no_deseados = ["@amazon.", "@google.", "@facebook.", "@linkedin.", "@mailchimp.", "@salesforce."]
    if any(dominio in email.lower() for dominio in dominios_no_deseados):
        return False

    return True  # Considera el correo como personal


def obtener_mensaje_no_leido(service):
    # Obtiene los últimos 5 correos no leídos en la bandeja de entrada
    response = service.users().messages().list(
        userId='me',
        labelIds=['INBOX', 'UNREAD'],
        maxResults=5
    ).execute()
    mensajes = response.get('messages', [])
    if not mensajes:
        return None

    for mensaje in mensajes:
        mensaje_id = mensaje['id']
        thread_id = mensaje['threadId']

        # Obtiene el contenido completo en formato raw y los metadatos del mensaje
        raw_msg = service.users().messages().get(userId='me', id=mensaje_id, format='raw').execute()
        meta_msg = service.users().messages().get(userId='me', id=mensaje_id, format='metadata', metadataHeaders=['Message-ID', 'Subject']).execute()

        payload = base64.urlsafe_b64decode(raw_msg['raw'])  # Decodifica mensaje raw
        mime_msg = message_from_bytes(payload)  # Convierte a objeto MIME

        if not es_correo_personal(mime_msg):
            # Marca el correo como leído si no es personal
            print(f"Correo ignorado: {mime_msg['From']}")
            service.users().messages().modify(
                userId='me',
                id=mensaje_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            continue

        remitente = mime_msg['From']
        asunto = mime_msg['Subject']

        headers = meta_msg['payload']['headers']
        msg_id_header = next((h['value'] for h in headers if h['name'] == 'Message-ID'), None)

        # Extrae el cuerpo del correo
        body = ""
        if mime_msg.is_multipart():
            for part in mime_msg.walk():
                if part.get_content_type() == 'text/plain':
                    body = part.get_payload(decode=True).decode(errors='ignore')
                    break
        else:
            body = mime_msg.get_payload(decode=True).decode(errors='ignore')

        body = limpiar_mensaje(body)  # Limpia el cuerpo del mensaje

        return {
            "id": mensaje_id,
            "remitente": remitente,
            "asunto": asunto,
            "mensaje": body,
            "thread_id": thread_id,
            "message_id": msg_id_header
        }

    return None  # Si no hay mensajes personales


def responder_mensaje(service, destinatario, cuerpo_original, respuesta, thread_id, message_id, subject, cc_email=None):
    from email.mime.text import MIMEText
    from email.utils import parseaddr, formatdate
    import base64

    to_email = parseaddr(destinatario)[1]  # Extrae dirección de correo del destinatario
    cc_header = f"\nCC: {cc_email}" if cc_email else ""  # Añade CC si se especifica

    # Construye el cuerpo de la respuesta incluyendo el mensaje original
    cuerpo_respuesta = f"""Hola,\n\n{respuesta}\n\n--- Mensaje original ---\n{cuerpo_original}\n\nAtentamente,\nAsistente automático{cc_header}"""

    message = MIMEText(cuerpo_respuesta)
    message['To'] = to_email
    message['Subject'] = f"Re: {subject}" if not subject.lower().startswith("re:") else subject
    message['In-Reply-To'] = message_id  # Mantiene relación con mensaje original
    message['References'] = message_id
    message['Date'] = formatdate(localtime=True)

    if cc_email:
        message['Cc'] = cc_email

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()  # Codifica el mensaje

    body = {
        'raw': raw_message,
        'threadId': thread_id  # Responde en el mismo hilo
    }

    service.users().messages().send(userId='me', body=body).execute()
    print(f"Respuesta enviada a: {to_email} en el mismo hilo.")
    if cc_email:
        print(f"Se copió a: {cc_email}")


def marcar_como_leido(service, mensaje_id):
    # Elimina la etiqueta UNREAD del mensaje especificado
    service.users().messages().modify(
        userId='me',
        id=mensaje_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()


def main():
    service = conectar_gmail()  # Conecta con Gmail

    mensaje = obtener_mensaje_no_leido(service)  # Busca mensaje no leído
    if not mensaje:
        print("No hay mensajes nuevos.")
        return

    print(f"Procesando mensaje de {mensaje['remitente']}")

    # Envía el mensaje a Docalysis para generar una respuesta
    respuesta = DocalysisAPI.chat_with_directory(mensaje['mensaje'])

    frase_clave = "Disculpe, esa información no está disponible actualmente, le contactaré con una persona para que le pueda ayudar"
    cc_email = None

    # Si Docalysis indica que se necesita ayuda humana, copia a otra persona
    if frase_clave.lower() in respuesta.strip().lower():
        cc_email = "ahilinreyes5@gmail.com"

    responder_mensaje(
        service,
        destinatario=mensaje['remitente'],
        cuerpo_original=mensaje['mensaje'],
        respuesta=respuesta,
        thread_id=mensaje['thread_id'],
        message_id=mensaje['message_id'],
        subject=mensaje['asunto'],
        cc_email=cc_email
    )

    marcar_como_leido(service, mensaje['id'])  # Marca el mensaje como leído


if __name__ == '__main__':
    main()  # Ejecuta el flujo principal