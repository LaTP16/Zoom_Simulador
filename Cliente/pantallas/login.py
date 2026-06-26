import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from Cliente.cliente_socket import ClienteSocket
from Cliente.modelos.usuario import Usuario

class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, on_login_exitoso, host="127.0.0.1", puerto=5000):
        super().__init__(master)
        self._on_login_exitoso = on_login_exitoso
        self._cliente_socket = ClienteSocket(host, puerto)
        self._crear_widgets()

    def _crear_widgets(self):
        ctk.CTkLabel(self, text="Correo electrónico:", font=("Arial", 11, "bold")).pack(pady=(30, 5))
        self._entrada_correo = ctk.CTkEntry(self, width=250, font=("Arial", 11))
        self._entrada_correo.pack()

        ctk.CTkLabel(self, text="Contraseña:", font=("Arial", 11, "bold")).pack(pady=(15, 5))
        self._entrada_clave = ctk.CTkEntry(self, width=250, show="*", font=("Arial", 11))
        self._entrada_clave.pack()
        self._entrada_clave.bind("<Return>", lambda e: self._procesar_login())

        self._btn_ingresar = ctk.CTkButton(
            self, text="Ingresar", command=self._procesar_login,
            width=150, font=("Arial", 11, "bold"), fg_color="#4CAF50", text_color="white"
        )
        self._btn_ingresar.pack(pady=25)

        self._mensaje_error = ctk.CTkLabel(self, text="", text_color="#f44336", font=("Arial", 10))
        self._mensaje_error.pack()

    def _procesar_login(self):
        correo = self._entrada_correo.get().strip()
        clave = self._entrada_clave.get().strip()

        if not correo or not clave:
            messagebox.showwarning("Atención", "Por favor, completa todos los campos.")
            return

        self._btn_ingresar.configure(state="disabled", text="Conectando...")
        self.update()

        try:
            respuesta = self._cliente_socket.enviar_y_recibir({
                "type": "LOGIN_REQUEST",
                "correo": correo,
                "clave": clave
            }, response_type="LOGIN_RESPONSE")

            if respuesta.get("status") == "success":
                usuario = Usuario(
                    respuesta["idUsuario"],
                    respuesta["nombres"],
                    correo,
                    respuesta["rol"]
                )
                messagebox.showinfo("Éxito", f"Bienvenido, {usuario.nombres}")
                self.after(0, self._on_login_exitoso, usuario, self._cliente_socket)
            else:
                self._mensaje_error.configure(text=respuesta.get("message", "Error desconocido"))
        except ConnectionError as e:
            self._mensaje_error.configure(text=str(e))
        finally:
            self._btn_ingresar.configure(state="normal", text="Ingresar")

