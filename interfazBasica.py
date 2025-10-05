from flask import Flask, request, jsonify
import requests
import logging
import os
from datetime import datetime

import conexionApi

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

WHATSAPP_CONFIG = {
    'access_token': os.environ.get('WHATSAPP_ACCESS_TOKEN', 'EAAXm78sPnEgBPgDAnFZBqdPtM7hx1mPekZAxanSi6YaZBKBpBJ7CiALfIP0YdX2JoEjFG3CK1FsJs9rdtEZB5uZA5HeKywthJAiuMZBJZAkNED8uqziM7OAtahKtPmML2AO4EzpGljWZB8P7EEXRpI8nF0se8dPiTKTXzfAq1wPE9lpNgSEtG0aC5veKeyWLnZAydpk87A28aTdFZBxOkZCNHMkXpKkLPlmqIm3a1tYolZBzAMR5qAZDZD'),
    'phone_number_id': os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '736137046259055'),
    'api_version': os.environ.get('WHATSAPP_API_VERSION', 'v23.0'),
    'verify_token': os.environ.get('WHATSAPP_VERIFY_TOKEN', 'secretaria')
}


def procesar_mensaje_whatsapp(mensaje, numero_whatsapp):
    """Procesa el mensaje y lo envía a Docalysis"""
    try:
        if mensaje and mensaje.strip():
            logger.info(f"Procesando mensaje de {numero_whatsapp}: {mensaje}")

            resultado = conexionApi.enviar_mensaje_completo(mensaje.strip())

            # resultado = f"Recibí: '{mensaje}'. Pronto tendré Docalysis integrado."
            logger.info(f"Respuesta: {resultado}")

            return resultado
        else:
            return "Hola! Recibí tu mensaje vacío. ¿En qué puedo ayudarte?"

    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")
        return "Error procesando tu mensaje. Intenta nuevamente."


def enviar_respuesta_whatsapp(numero_destino, mensaje):
    """Envía mensajes a través de WhatsApp Business API"""
    try:
        numero_limpio = ''.join(filter(str.isdigit, numero_destino))

        url = f"https://graph.facebook.com/{WHATSAPP_CONFIG['api_version']}/{WHATSAPP_CONFIG['phone_number_id']}/messages"

        headers = {
            "Authorization": f"Bearer {WHATSAPP_CONFIG['access_token']}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": numero_limpio,
            "text": {"body": mensaje}
        }

        logger.info(f"Enviando a {numero_limpio}")

        response = requests.post(url, headers=headers, json=payload, timeout=30)

        logger.info(f"Status: {response.status_code}")

        if response.status_code == 200:
            logger.info("Mensaje enviado")
            return True
        else:
            logger.error(f"Error: {response.text}")
            return False

    except Exception as e:
        logger.error(f"Error enviando mensaje: {e}")
        return False


@app.route('/webhook/whatsapp', methods=['GET', 'POST'])
def webhook_whatsapp():
    """Webhook para WhatsApp Business API"""

    if request.method == 'GET':
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        logger.info(f"Verificando: {verify_token}")

        if verify_token == WHATSAPP_CONFIG['verify_token']:
            logger.info("Webhook verificado")
            return challenge
        else:
            logger.warning("Token incorrecto")
            return 'Error de verificación', 403

    elif request.method == 'POST':
        data = request.get_json()
        logger.info(f"Mensaje recibido: {data}")

        try:
            if 'entry' in data:
                for entry in data['entry']:
                    if 'changes' in entry:
                        for change in entry['changes']:
                            if 'value' in change and 'messages' in change['value']:
                                for message in change['value']['messages']:
                                    if message['type'] == 'text':
                                        mensaje_texto = message['text']['body']
                                        numero_whatsapp = message['from']

                                        logger.info(f"De {numero_whatsapp}: {mensaje_texto}")

                                        respuesta = procesar_mensaje_whatsapp(mensaje_texto, numero_whatsapp)

                                        if enviar_respuesta_whatsapp(numero_whatsapp, respuesta):
                                            logger.info("Respuesta enviada")
                                        else:
                                            logger.error("Error enviando")

                                        return jsonify({'status': 'success'})

            return jsonify({'status': 'success', 'message': 'Mensaje recibido'})

        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/', methods=['GET', 'POST'])
def home():
    """Página principal - ahora acepta POST también"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        logger.info(f"POST recibido en /: {data}")

        return jsonify({
            'message': 'POST recibido correctamente en WhatsApp Bot',
            'data_received': data,
            'status': 'success',
            'timestamp': datetime.now().isoformat()
        })
    else:
        return jsonify({
            'message': 'WhatsApp Docalysis Bot está funcionando',
            'status': 'active',
            'webhook_url': 'https://secretar-ia.onrender.com/webhook/whatsapp',
            'timestamp': datetime.now().isoformat(),
            'instructions': 'Usa POST en /webhook/whatsapp para mensajes de WhatsApp'
        })


@app.route('/health', methods=['GET', 'POST'])
def health_check():
    """Health check - acepta ambos métodos"""
    if request.method == 'POST':
        return jsonify({
            'status': 'healthy',
            'method': 'POST',
            'timestamp': datetime.now().isoformat()
        })
    return jsonify({
        'status': 'healthy',
        'method': 'GET',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/test', methods=['GET', 'POST'])
def test_endpoint():
    """Endpoint para pruebas - acepta ambos métodos"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        return jsonify({
            'status': 'success',
            'message': 'POST recibido correctamente',
            'data_received': data,
            'method': 'POST',
            'timestamp': datetime.now().isoformat()
        })
    else:
        return jsonify({
            'status': 'success',
            'message': 'GET funcionando correctamente',
            'method': 'GET',
            'timestamp': datetime.now().isoformat()
        })


@app.route('/send-message', methods=['POST'])
def send_message():
    """Endpoint específico para enviar mensajes de prueba"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Se requiere JSON'}), 400

        numero = data.get('numero')
        mensaje = data.get('mensaje', 'Mensaje de prueba desde Render')

        if not numero:
            return jsonify({'error': 'Número requerido'}), 400

        logger.info(f"Enviando mensaje a {numero}")

        success = enviar_respuesta_whatsapp(numero, mensaje)

        if success:
            return jsonify({
                'status': 'success',
                'message': 'Mensaje enviado',
                'numero': numero
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Error enviando mensaje'
            }), 500

    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))

    logger.info("=" * 50)
    logger.info("BOT INICIADO - LISTO PARA POST Y GET")
    logger.info("=" * 50)
    logger.info(f"URL: https://secretar-ia.onrender.com")
    logger.info(f"Webhook: /webhook/whatsapp")
    logger.info(f"Puerto: {port}")
    logger.info("=" * 50)

    app.run(host='0.0.0.0', port=port, debug=False)