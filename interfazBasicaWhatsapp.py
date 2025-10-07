# Importa módulos necesarios de Flask, HTTP, logging, sistema de archivos y fechas
from flask import Flask, request, jsonify
import requests
import logging
import os
from datetime import datetime

# Importa módulo interno para conexión a la API (debe estar definido en otro archivo llamado conexionApi.py)
import conexionApi

# Configura el sistema de logging a nivel INFO
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Función auxiliar para obtener una variable de entorno obligatoria
def get_env_variable(name):
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(f"La variable de entorno '{name}' es obligatoria y no está definida.")
    return value

# Inicializa la aplicación Flask
app = Flask(__name__)

# Carga configuración de WhatsApp desde variables de entorno
WHATSAPP_CONFIG = {
    'access_token': get_env_variable('WHATSAPP_ACCESS_TOKEN'),
    'phone_number_id': get_env_variable('WHATSAPP_PHONE_NUMBER_ID'),
    'api_version': os.environ.get('WHATSAPP_API_VERSION', 'v17.0'),
    'verify_token': get_env_variable('WHATSAPP_VERIFY_TOKEN')
}

# Procesa el mensaje recibido por WhatsApp y llama a la API que da la respuesta
def procesar_mensaje_whatsapp(mensaje, numero_whatsapp):
    try:
        if mensaje and mensaje.strip():
            logger.info(f"Procesando mensaje de {numero_whatsapp}: {mensaje}")
            resultado = conexionApi.enviar_mensaje_completo(mensaje.strip())  # Llama a la función que maneja el mensaje
            logger.info(f"Respuesta: {resultado}")
            return resultado
        else:
            return "Hola! Recibí tu mensaje vacío. ¿En qué puedo ayudarte?"
    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")
        return "Error procesando tu mensaje. Intenta nuevamente."

# Envía una respuesta por WhatsApp usando la API de Meta
def enviar_respuesta_whatsapp(numero_destino, mensaje):
    try:
        numero_limpio = ''.join(filter(str.isdigit, numero_destino))  # Elimina caracteres no numéricos del número
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

# Ruta principal del webhook de WhatsApp
@app.route('/webhook/whatsapp', methods=['GET', 'POST'])
def webhook_whatsapp():
    if request.method == 'GET':
        # Validación del webhook desde Meta
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        logger.info(f"Verificando: {verify_token}")

        if verify_token == WHATSAPP_CONFIG['verify_token']:
            logger.info("Webhook verificado")
            return challenge  # Devuelve challenge si el token es correcto
        else:
            logger.warning("Token incorrecto")
            return 'Error de verificación', 403

    elif request.method == 'POST':
        # Procesa el mensaje entrante
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

                                        return jsonify({'status': 'success'})  # Respuesta HTTP al webhook

            return jsonify({'status': 'success', 'message': 'Mensaje recibido'})

        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

# Ruta base para verificar si el bot está activo
@app.route('/', methods=['GET', 'POST'])
def home():
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
            'webhook_url': '/webhook/whatsapp',
            'timestamp': datetime.now().isoformat(),
            'instructions': 'Usa POST en /webhook/whatsapp para mensajes de WhatsApp'
        })

# Ruta de verificación de salud (health check)
@app.route('/health', methods=['GET', 'POST'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'method': request.method,
        'timestamp': datetime.now().isoformat()
    })

# Ruta de prueba para POST/GET manuales
@app.route('/test', methods=['GET', 'POST'])
def test_endpoint():
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

# Ruta para enviar un mensaje manualmente (útil para testing externo)
@app.route('/send-message', methods=['POST'])
def send_message():
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

# Punto de entrada principal del script
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))  # Usa el puerto definido o el 10000 por defecto
    logger.info("=" * 50)
    logger.info("BOT INICIADO - LISTO PARA POST Y GET")
    logger.info(f"Webhook: /webhook/whatsapp")
    logger.info(f"Puerto: {port}")
    logger.info("=" * 50)

    app.run(host='0.0.0.0', port=port, debug=False)  # Inicia el servidor Flask