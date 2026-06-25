import tkinter as tk
from tkinter import messagebox, ttk
from Cliente.cliente_socket import ClienteSocket
from Cliente.modelos.usuario import Usuario

class LoginFrame(tk.Frame):
    def __init__(self, master, on_login_exitoso, host="127.0.0.1", puerto=5000):
        super().__init__(master)
        self._on_login_exitoso = on_login_exitoso
        self._cliente_socket = ClienteSocket(host, puerto)
        self._crear_widgets()

    def _crear_widgets(self):
        tk.Label(self, text="Correo electrónico:", font=("Arial", 10)).pack(pady=(20, 5))
        self._entrada_correo = tk.Entry(self, width=30, font=("Arial", 10))
        self._entrada_correo.pack()

        tk.Label(self, text="Contraseña:", font=("Arial", 10)).pack(pady=(10, 5))
        self._entrada_clave = tk.Entry(self, width=30, show="*", font=("Arial", 10))
        self._entrada_clave.pack()
        self._entrada_clave.bind("<Return>", lambda e: self._procesar_login())

        self._btn_ingresar = tk.Button(
            self, text="Ingresar", command=self._procesar_login,
            width=15, font=("Arial", 10), bg="#4CAF50", fg="white"
        )
        self._btn_ingresar.pack(pady=20)

        self._mensaje_error = tk.Label(self, text="", fg="red", font=("Arial", 9))
        self._mensaje_error.pack()

    def _procesar_login(self):
        correo = self._entrada_correo.get().strip()
        clave = self._entrada_clave.get().strip()

        if not correo or not clave:
            messagebox.showwarning("Atención", "Por favor, completa todos los campos.")
            return

        self._btn_ingresar.config(state=tk.DISABLED, text="Conectando...")
        self.update()

        try:
            respuesta = self._cliente_socket.enviar_y_recibir({
                "type": "LOGIN_REQUEST",
                "correo": correo,
                "clave": clave
            })

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
                self._mensaje_error.config(text=respuesta.get("message", "Error desconocido"))
        except ConnectionError as e:
            self._mensaje_error.config(text=str(e))
        finally:
            self._btn_ingresar.config(state=tk.NORMAL, text="Ingresar")
