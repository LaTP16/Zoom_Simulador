import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from Cliente.cliente_socket import ClienteSocket
from Cliente.modelos.usuario import Usuario

class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, on_login_exitoso, host="127.0.0.1", puerto=5000):
        super().__init__(master, fg_color="#1a1a1a")
        self._on_login_exitoso = on_login_exitoso
        self._cliente_socket = ClienteSocket(host, puerto)
        self._crear_widgets()

    def _crear_widgets(self):
        # Tarjeta contenedora centrada (sin altura fija para auto-ajuste dinámico)
        card = ctk.CTkFrame(
            self, 
            width=400,
            fg_color="#242424", 
            corner_radius=16, 
            border_width=1, 
            border_color="#333333"
        )
        card.pack(expand=True, padx=40, pady=40)

        # Título
        ctk.CTkLabel(
            card, 
            text="Zoom Simulador", 
            font=("Helvetica Neue", 24, "bold"), 
            text_color="#ffffff"
        ).pack(pady=(35, 20))

        # Campo correo
        self._entrada_correo = ctk.CTkEntry(
            card, 
            width=300, 
            height=40,
            placeholder_text="Correo electrónico",
            font=("Helvetica Neue", 13),
            corner_radius=8,
            fg_color="#1a1a1a",
            border_color="#444444",
            text_color="#ffffff",
            placeholder_text_color="#888888"
        )
        self._entrada_correo.pack(pady=8, padx=40)

        # Campo contraseña
        self._entrada_clave = ctk.CTkEntry(
            card, 
            width=300, 
            height=40,
            show="*", 
            placeholder_text="Contraseña",
            font=("Helvetica Neue", 13),
            corner_radius=8,
            fg_color="#1a1a1a",
            border_color="#444444",
            text_color="#ffffff",
            placeholder_text_color="#888888"
        )
        self._entrada_clave.pack(pady=8, padx=40)
        self._entrada_clave.bind("<Return>", lambda e: self._procesar_login())

        # Botón de ingresar
        self._btn_ingresar = ctk.CTkButton(
            card, 
            text="Iniciar Sesión", 
            command=self._procesar_login,
            width=300, 
            height=40,
            font=("Helvetica Neue", 13, "bold"), 
            fg_color="#0E71EB", 
            hover_color="#0b5ed7",
            text_color="white",
            corner_radius=8
        )
        self._btn_ingresar.pack(pady=(20, 10), padx=40)

        # Mensaje de error (garantiza espacio al fondo de la tarjeta)
        self._mensaje_error = ctk.CTkLabel(
            card, 
            text="", 
            text_color="#f44336", 
            font=("Helvetica Neue", 10)
        )
        self._mensaje_error.pack(pady=(0, 25))

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

