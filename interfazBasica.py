import tkinter as tk
from tkinter import messagebox
import conexionApi


def on_send():
    # Obtiene el texto del campo, lo limpia y lo envía a la API.
    # Luego muestra la respuesta en un cuadro de diálogo emergente.
    mensaje = text_input.get("1.0", tk.END).strip()
    if mensaje:
        text_input.delete("1.0", tk.END)
        # messagebox.showinfo("Enviando...", "Procesando mensaje, por favor espera...")

        resultado = conexionApi.enviar_mensaje_completo(mensaje)

        messagebox.showinfo("Resultado", resultado)
    else:
        messagebox.showwarning("Campo vacío", "Escribe un mensaje antes de enviar.")


# Crea la ventana principal de la interfaz gráfica, define
# título, tamaño y disposición general de los elementos visuales.
ventana = tk.Tk()
ventana.title("Enviar mensaje a Docalysis")
ventana.geometry("400x300")

# Agrega una etiqueta descriptiva sobre el área de texto para
# guiar al usuario en la introducción del mensaje.
label = tk.Label(ventana, text="Escribe tu mensaje:")
label.pack(pady=10)

# Área de texto donde el usuario redacta el mensaje que será
# enviado posteriormente a la API para procesar la respuesta.
text_input = tk.Text(ventana, height=10, width=40)
text_input.pack(pady=10)

# Botón que activa la función de envío, captura el texto y
# gestiona la comunicación con la API cuando el usuario hace clic.
btn_enviar = tk.Button(ventana, text="Enviar", command=on_send)
btn_enviar.pack(pady=10)

# Inicia el bucle principal de Tkinter, manteniendo activa la
# interfaz gráfica y respondiendo a las acciones del usuario.
ventana.mainloop()
