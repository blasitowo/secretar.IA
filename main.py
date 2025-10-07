# Importa módulos necesarios para ejecución en segundo plano, tiempo, ejecución de scripts, logging y entorno
import threading
import time
import subprocess
import logging
import os

# Importa la instancia Flask desde el archivo 'interfazBasicaWhatsapp.py'
from interfazBasicaWhatsapp import app

# Configura el sistema de logging a nivel INFO
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Función que ejecuta un script externo (interfazBasicaGmail.py) periódicamente
def tarea_respuesta_email():
    """Ejecuta el bot de Gmail y Google Drive cada 1 minuto"""
    while True:
        try:
            logger.info(" Ejecutando integración con Gmail y Google Drive...")

            # Ejecuta el script de Gmail y captura su salida
            resultado = subprocess.run(["python", "interfazBasicaGmail.py"], capture_output=True, text=True)

            # Verifica si el script terminó correctamente
            if resultado.returncode == 0:
                logger.info(" Proceso completado exitosamente.")
            else:
                # Si hubo error, muestra la salida de error y estándar
                logger.error(f" Error durante la ejecución:\n{resultado.stderr}")
                logger.info(f" Salida estándar:\n{resultado.stdout}")
        except Exception as e:
            # Captura cualquier excepción inesperada
            logger.error(f"Error ejecutando el bot de correos: {e}")

        # Espera 1 minuto antes de volver a ejecutar
        time.sleep(1 * 60)


# Bloque principal que se ejecuta si el script es llamado directamente
if __name__ == "__main__":
    # Crea un hilo en segundo plano para ejecutar el bot de Gmail sin bloquear la app principal
    hilo_correo = threading.Thread(target=tarea_respuesta_email, daemon=True)
    hilo_correo.start()

    # Inicia la aplicación Flask normalmente
    port = int(os.environ.get('PORT', 10000))  # Toma el puerto de la variable de entorno o usa 10000 por defecto
    logger.info("=" * 50)
    logger.info(" BOT WHATSAPP INICIADO + CRON EMAIL & DRIVE")
    logger.info("=" * 50)
    app.run(host='0.0.0.0', port=port)  # Ejecuta la app Flask en todas las interface