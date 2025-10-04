import tkinter as tk
from tkinter import messagebox
import conexionApi


def on_send():
    mensaje = text_input.get("1.0", tk.END).strip()
    if mensaje:
        text_input.delete("1.0", tk.END)
        messagebox.showinfo("Enviando...", "Procesando mensaje, por favor espera...")

        resultado = conexionApi.enviar_mensaje_completo(mensaje)

        messagebox.showinfo("Resultado", resultado)
    else:
        messagebox.showwarning("Campo vacío", "Escribe un mensaje antes de enviar.")


ventana = tk.Tk()
ventana.title("Enviar mensaje a Docalysis")
ventana.geometry("400x300")

label = tk.Label(ventana, text="Escribe tu mensaje:")
label.pack(pady=10)

text_input = tk.Text(ventana, height=10, width=40)
text_input.pack(pady=10)

btn_enviar = tk.Button(ventana, text="Enviar", command=on_send)
btn_enviar.pack(pady=10)

ventana.mainloop()
