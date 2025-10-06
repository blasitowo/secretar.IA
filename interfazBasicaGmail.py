import os
import os.path
import base64
import re
from email import message_from_bytes
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from docalysis_api import DocalysisAPI

SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.send']


def limpiar_mensaje(texto):
    """Limpia el cuerpo del correo: elimina HTML, firmas y espacios innecesarios."""
    texto = re.sub(r'<[^>]+>', '', texto)  # elimina etiquetas HTML
    texto = re.split(r'\n--+\s*\n', texto)[0]  # elimina firmas comunes
    texto = re.sub(r'\n{2,}', '\n\n', texto)  # elimina saltos de línea dobles
    return texto.strip()


def conectar_gmail():
    creds = None

    #  Crear archivos desde variables de entorno si no existen
    if not os.path.exists("credentials.json"):
        credentials_env = os.getenv("GMAIL_CREDENTIALS_JSON")
        if credentials_env:
            with open("credentials.json", "w") as f:
                f.write(credentials_env)
        else:
            raise Exception(" GMAIL_CREDENTIALS_JSON no está definido en el entorno.")

    if not os.path.exists("token.json"):
        token_env = os.getenv("GMAIL_TOKEN_JSON")
        if token_env:
            with open("token.json", "w") as f:
                f.write(token_env)
        # Si no hay token, se generará abajo con el flujo OAuth

    #  Antes se cargaban directamente los archivos desde disco:
    # creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

            # Guardar el nuevo token en token.json y en la variable de entorno (si querés persistencia)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def es_correo_personal(mime_msg):
    from email.utils import parseaddr

    # Evita correos con cabeceras de marketing/newsletter
    headers = mime_msg.items()
    cabeceras_sospechosas = ["List-Unsubscribe", "Precedence", "Auto-Submitted"]
    for clave, valor in headers:
        if clave in cabeceras_sospechosas:
            return False
        if clave == "Return-Path" and any(x in valor.lower() for x in ["mailer", "bounce", "noreply", "no-reply"]):
            return False

    # Filtra por dirección de correo
    remitente = mime_msg["From"]
    _, email = parseaddr(remitente)
    if any(x in email.lower() for x in ["no-reply", "noreply", "mailer", "notifications", "updates"]):
        return False

    # Opcional: evita dominios de empresas grandes
    dominios_no_deseados = ["@amazon.", "@google.", "@facebook.", "@linkedin.", "@mailchimp.", "@salesforce."]
    if any(dominio in email.lower() for dominio in dominios_no_deseados):
        return False

    return True


def obtener_mensaje_no_leido(service):
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

        # Obtener mensaje completo (raw) y metadatos
        raw_msg = service.users().messages().get(userId='me', id=mensaje_id, format='raw').execute()
        meta_msg = service.users().messages().get(userId='me', id=mensaje_id, format='metadata', metadataHeaders=['Message-ID', 'Subject']).execute()

        payload = base64.urlsafe_b64decode(raw_msg['raw'])
        mime_msg = message_from_bytes(payload)

        if not es_correo_personal(mime_msg):
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

        body = ""
        if mime_msg.is_multipart():
            for part in mime_msg.walk():
                if part.get_content_type() == 'text/plain':
                    body = part.get_payload(decode=True).decode(errors='ignore')
                    break
        else:
            body = mime_msg.get_payload(decode=True).decode(errors='ignore')

        body = limpiar_mensaje(body)

        return {
            "id": mensaje_id,
            "remitente": remitente,
            "asunto": asunto,
            "mensaje": body,
            "thread_id": thread_id,
            "message_id": msg_id_header
        }

    return None


def responder_mensaje(service, destinatario, cuerpo_original, respuesta, thread_id, message_id, subject):
    from email.mime.text import MIMEText
    from email.utils import parseaddr, formatdate
    import base64

    to_email = parseaddr(destinatario)[1]
    cuerpo_respuesta = f"""Hola,\n\n{respuesta}\n\nAtentamente,\nAsistente automático"""

    message = MIMEText(cuerpo_respuesta)
    message['To'] = to_email
    message['Subject'] = f"Re: {subject}" if not subject.lower().startswith("re:") else subject
    message['In-Reply-To'] = message_id
    message['References'] = message_id
    message['Date'] = formatdate(localtime=True)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    body = {
        'raw': raw_message,
        'threadId': thread_id  # Para mantener el hilo
    }

    service.users().messages().send(userId='me', body=body).execute()
    print(f"Respuesta enviada a: {to_email} en el mismo hilo.")


def marcar_como_leido(service, mensaje_id):
    service.users().messages().modify(
        userId='me',
        id=mensaje_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()


def main():
    service = conectar_gmail()

    mensaje = obtener_mensaje_no_leido(service)
    if not mensaje:
        print("No hay mensajes nuevos.")
        return

    print(f"Procesando mensaje de {mensaje['remitente']}")

    respuesta = DocalysisAPI.chat_with_directory(mensaje['mensaje'])

    responder_mensaje(
        service,
        destinatario=mensaje['remitente'],
        cuerpo_original=mensaje['mensaje'],
        respuesta=respuesta,
        thread_id=mensaje['thread_id'],
        message_id=mensaje['message_id'],
        subject=mensaje['asunto']
    )

    marcar_como_leido(service, mensaje['id'])


if __name__ == '__main__':
    main()
