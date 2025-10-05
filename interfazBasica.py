from flask import Flask, request, jsonify
import requests
import logging
from datetime import datetime
import conexionApi

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

WHATSAPP_CONFIG = {
    'access_token': 'EAAXm78sPnEgBPgDAnFZBqdPtM7hx1mPekZAxanSi6YaZBKBpBJ7CiALfIP0YdX2JoEjFG3CK1FsJs9rdtEZB5uZA5HeKywthJAiuMZBJZAkNED8uqziM7OAtahKtPmML2AO4EzpGljWZB8P7EEXRpI8nF0se8dPiTKTXzfAq1wPE9lpNgSEtG0aC5veKeyWLnZAydpk87A28aTdFZBxOkZCNHMkXpKkLPlmqIm3a1tYolZBzAMR5qAZDZD',  #  Token de acceso de Meta
    'phone_number_id': '595982364250',  #  Phone Number ID
    'api_version': 'v23.0',  #  Versión de la API
    'verify_token': 'secretaria'  #  Token para verificar webhook
}


# =============================================

def procesar_mensaje_whatsapp(mensaje, numero_whatsapp):
    """Procesa el mensaje y lo envía a Docalysis"""
    try:
        if mensaje and mensaje.strip():
            logger.info(f" Procesando mensaje de {numero_whatsapp}: {mensaje}")

            # Enviar el mensaje a Docalysis
            resultado = conexionApi.enviar_mensaje_completo(mensaje.strip())
            logger.info(f" Respuesta de Docalysis: {resultado}")

            return resultado
        else:
            return " ¡Hola! Recibí tu mensaje pero está vacío. ¿En qué puedo ayudarte?"

    except Exception as e:
        logger.error(f" Error procesando mensaje: {e}")
        return " Lo siento, hubo un error procesando tu mensaje. Por favor, intenta nuevamente."


def enviar_respuesta_whatsapp(numero_destino, mensaje):
    """Envía mensajes a través de WhatsApp Business API"""
    try:
        # Limpiar el número (solo dígitos)
        numero_limpio = ''.join(filter(str.isdigit, numero_destino))

        # URL de la API de Meta WhatsApp
        url = f"https://graph.facebook.com/{WHATSAPP_CONFIG['api_version']}/{WHATSAPP_CONFIG['phone_number_id']}/messages"

        # Headers con autenticación
        headers = {
            "Authorization": f"Bearer {WHATSAPP_CONFIG['access_token']}",
            "Content-Type": "application/json"
        }

        # Cuerpo del mensaje
        payload = {
            "messaging_product": "whatsapp",
            "to": numero_limpio,
            "text": {"body": mensaje}
        }

        logger.info(f" Enviando mensaje a {numero_limpio}")

        # Realizar petición POST a la API de Meta
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        logger.info(f" Status Code: {response.status_code}")

        if response.status_code == 200:
            response_data = response.json()
            message_id = response_data.get('messages', [{}])[0].get('id', 'N/A')
            logger.info(f" Mensaje enviado exitosamente. ID: {message_id}")
            return True
        else:
            logger.error(f" Error {response.status_code}: {response.text}")
            return False

    except requests.exceptions.Timeout:
        logger.error(" Timeout al enviar mensaje a WhatsApp API")
        return False
    except requests.exceptions.ConnectionError:
        logger.error(" Error de conexión con WhatsApp API")
        return False
    except Exception as e:
        logger.error(f" Error inesperado enviando mensaje: {e}")
        return False


@app.route('/webhook/whatsapp', methods=['GET', 'POST'])
def webhook_whatsapp():
    """Webhook para recibir mensajes de WhatsApp Business API"""

    if request.method == 'GET':
        #  Verificación del webhook (Meta envía este challenge)
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        logger.info(f" Verificando webhook. Token recibido: {verify_token}")
        logger.info(f" Token esperado: {WHATSAPP_CONFIG['verify_token']}")

        if verify_token == WHATSAPP_CONFIG['verify_token']:
            logger.info(" Webhook verificado exitosamente")
            return challenge
        else:
            logger.warning(" Token de verificación incorrecto")
            return 'Error de verificación', 403

    elif request.method == 'POST':
        #  Procesar mensajes entrantes de WhatsApp
        data = request.get_json()
        logger.info(f" Mensaje recibido: {data}")

        try:
            # Estructura de datos de WhatsApp Business API
            if 'entry' in data:
                for entry in data['entry']:
                    if 'changes' in entry:
                        for change in entry['changes']:
                            if 'value' in change and 'messages' in change['value']:
                                for message in change['value']['messages']:
                                    if message['type'] == 'text':
                                        # Extraer información del mensaje
                                        mensaje_texto = message['text']['body']
                                        numero_whatsapp = message['from']
                                        message_id = message['id']

                                        logger.info(f" Mensaje #{message_id} de {numero_whatsapp}: {mensaje_texto}")

                                        # Procesar el mensaje con Docalysis
                                        respuesta = procesar_mensaje_whatsapp(mensaje_texto, numero_whatsapp)

                                        # Enviar respuesta a WhatsApp
                                        if enviar_respuesta_whatsapp(numero_whatsapp, respuesta):
                                            logger.info(" Respuesta enviada exitosamente a WhatsApp")
                                        else:
                                            logger.error(" Error al enviar respuesta a WhatsApp")

                                        return jsonify({'status': 'success', 'message': 'Procesado'})

            # Si no es un mensaje de texto que procesamos
            logger.info("  Tipo de mensaje no procesado")
            return jsonify({'status': 'success', 'message': 'Tipo de mensaje no procesado'})

        except Exception as e:
            logger.error(f" Error procesando mensaje: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/', methods=['GET'])
def home():
    """Página principal"""
    return jsonify({
        'message': ' WhatsApp Docalysis Bot está funcionando',
        'webhook_url': 'https://secretar-ia.onrender.com/webhook/whatsapp',
        'status': 'active',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que el servidor está funcionando"""
    return jsonify({
        'status': 'healthy',
        'service': 'whatsapp-docalysis-bot',
        'webhook': 'https://secretar-ia.onrender.com/webhook/whatsapp',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0'
    })


@app.route('/send-test', methods=['POST'])
def send_test_message():
    """Endpoint para probar el envío de mensajes sin webhook"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Se requiere JSON en el cuerpo'}), 400

        numero = data.get('numero')
        mensaje = data.get('mensaje', 'Este es un mensaje de prueba desde Docalysis ')

        if not numero:
            return jsonify({'error': 'El campo "numero" es requerido'}), 400

        logger.info(f" Enviando mensaje de prueba a {numero}")

        success = enviar_respuesta_whatsapp(numero, mensaje)

        if success:
            return jsonify({
                'status': 'success',
                'message': 'Mensaje de prueba enviado',
                'numero': numero,
                'webhook': 'https://secretar-ia.onrender.com'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Error enviando mensaje de prueba'
            }), 500

    except Exception as e:
        logger.error(f" Error en prueba: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/info', methods=['GET'])
def get_info():
    """Endpoint para obtener información de la configuración (sin mostrar tokens)"""
    return jsonify({
        'status': 'active',
        'service': 'WhatsApp Docalysis Bot',
        'webhook_url': 'https://secretar-ia.onrender.com/webhook/whatsapp',
        'phone_number_id': WHATSAPP_CONFIG['phone_number_id'],
        'api_version': WHATSAPP_CONFIG['api_version'],
        'verify_token_set': bool(WHATSAPP_CONFIG['verify_token'])
    })


if __name__ == '__main__':
    #  Configuración del servidor para Render
    port = int(os.environ.get('PORT', 10000))
    debug = False  # En producción siempre False

    logger.info("=" * 50)
    logger.info(" INICIANDO WHATSAPP DOCALYSIS BOT")
    logger.info("=" * 50)
    logger.info(f" Webhook URL: https://secretar-ia.onrender.com/webhook/whatsapp")
    logger.info(f" Verify Token: {WHATSAPP_CONFIG['verify_token']}")
    logger.info(f" Phone Number ID: {WHATSAPP_CONFIG['phone_number_id']}")
    logger.info(f" API Version: {WHATSAPP_CONFIG['api_version']}")
    logger.info(f" Puerto: {port}")
    logger.info("=" * 50)

    # Iniciar servidor Flask
    app.run(host='0.0.0.0', port=port, debug=debug)