import threading
import time
import subprocess
import logging
import os

# Asegúrate de importar la app Flask desde tu archivo actual
from interfazBasicaWhatsapp import app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def tarea_respuesta_email():
    """Ejecuta el bot de Gmail cada 15 minutos"""
    while True:
        try:
            logger.info("⏳ Ejecutando verificación de correos...")
            subprocess.run(["python", "interfazBasicaGmail.py"])
            logger.info(" Verificación de correos terminada.")
        except Exception as e:
            logger.error(f" Error ejecutando el bot de correos: {e}")

        time.sleep(1 * 60)  # Espera 15 minutos


if __name__ == "__main__":
    # Iniciar el hilo en segundo plano
    hilo_correo = threading.Thread(target=tarea_respuesta_email, daemon=True)
    hilo_correo.start()

    # Iniciar la app Flask normalmente
    port = int(os.environ.get('PORT', 10000))
    logger.info("=" * 50)
    logger.info(" BOT WHATSAPP INICIADO + CRON EMAIL")
    logger.info("=" * 50)
    app.run(host='0.0.0.0', port=port)
