import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import random
import string

class PantallaPrincipal(ctk.CTkFrame):
    def __init__(self, master, usuario, cliente_socket, on_cerrar_sesion, on_entrar_sala):
        super().__init__(master, fg_color="#1a1a1a")
        self._usuario = usuario
        self._cliente_socket = cliente_socket
        self._on_cerrar_sesion = on_cerrar_sesion
        self._on_entrar_sala = on_entrar_sala
        self._registrar_callbacks()
        self._crear_widgets()

    def _registrar_callbacks(self):
        self._cliente_socket.registrar_callback("ADMIT_USER", self._admitido_en_sala)

    def _limpiar_callbacks(self):
        self._cliente_socket.remover_callback("ADMIT_USER")

    def _crear_widgets(self):
        # Tarjeta contenedora principal (sin altura fija para auto-ajuste dinámico)
        card = ctk.CTkFrame(
            self, 
            width=420,
            fg_color="#242424", 
            corner_radius=16, 
            border_width=1, 
            border_color="#333333"
        )
        card.pack(expand=True, padx=40, pady=40)

        # Sección de perfil de usuario
        profile_frame = ctk.CTkFrame(
            card, 
            fg_color="#1a1a1a", 
            corner_radius=10, 
            border_width=1, 
            border_color="#2d2d2d"
        )
        profile_frame.pack(fill=tk.X, padx=25, pady=(25, 15))

        # Avatar basado en rol
        rol_icon = "👔" if "host" in self._usuario.rol.lower() or "anfitrion" in self._usuario.rol.lower() or "docente" in self._usuario.rol.lower() else "🎓"
        avatar_label = ctk.CTkLabel(profile_frame, text=rol_icon, font=("Segoe UI", 32))
        avatar_label.pack(side=tk.LEFT, padx=(15, 12), pady=12)

        info_frame = ctk.CTkFrame(profile_frame, fg_color="transparent")
        info_frame.pack(side=tk.LEFT, fill=tk.Y, pady=12)

        ctk.CTkLabel(
            info_frame, 
            text=self._usuario.nombres,
            font=("Helvetica Neue", 15, "bold"),
            text_color="#ffffff",
            anchor="w"
        ).pack(anchor="w")

        ctk.CTkLabel(
            info_frame, 
            text=f"Rol: {self._usuario.rol}",
            font=("Helvetica Neue", 11),
            text_color="#aaaaaa",
            anchor="w"
        ).pack(anchor="w")

        # Contenedor de botones de acción con margen inferior garantizado de 25px
        frame_botones = ctk.CTkFrame(card, fg_color="transparent")
        frame_botones.pack(fill=tk.X, padx=25, pady=(0, 25))

        # Botón Crear Sala
        self._btn_crear = ctk.CTkButton(
            frame_botones, 
            text="➕  Crear Sala", 
            command=self._crear_sala,
            width=360,
            height=42, 
            font=("Helvetica Neue", 13, "bold"), 
            fg_color="#0E71EB", 
            hover_color="#0b5ed7", 
            text_color="white",
            corner_radius=8
        )
        self._btn_crear.pack(fill=tk.X, pady=5)

        # Botón Unirse a Sala
        self._btn_unirse = ctk.CTkButton(
            frame_botones, 
            text="🚪  Unirse a Sala", 
            command=self._unirse_sala,
            width=360,
            height=42, 
            font=("Helvetica Neue", 13, "bold"), 
            fg_color="#FF9800", 
            hover_color="#e08600", 
            text_color="white",
            corner_radius=8
        )
        self._btn_unirse.pack(fill=tk.X, pady=5)

        # Botón Cerrar Sesión
        self._btn_cerrar = ctk.CTkButton(
            frame_botones, 
            text="🚪 Cerrar Sesión", 
            command=self._cerrar_sesion,
            width=360,
            height=36, 
            font=("Helvetica Neue", 12, "bold"), 
            fg_color="#f44336", 
            hover_color="#d32f2f", 
            text_color="white",
            corner_radius=8
        )
        self._btn_cerrar.pack(fill=tk.X, pady=(15, 0))

    def _crear_sala(self):
        codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        respuesta = self._cliente_socket.enviar_y_recibir({
            "type": "CREATE_ROOM",
            "nombre": f"Sala de {self._usuario.nombres}",
            "codigo": codigo,
            "idHost": self._usuario.id_usuario
        }, response_type="CREATE_ROOM")
        if respuesta.get("status") == "success":
            self._on_entrar_sala(codigo, True, respuesta["idSala"])
        else:
            messagebox.showerror("Error", respuesta.get("message", "Error al crear sala"))

    def _unirse_sala(self):
        ventana = ctk.CTkToplevel(self)
        ventana.title("Unirse a Sala")
        ventana.geometry("320x190")
        ventana.resizable(False, False)
        ventana.transient(self)
        ventana.grab_set()
        ventana.configure(fg_color="#1a1a1a")

        container = ctk.CTkFrame(
            ventana, 
            fg_color="#242424", 
            corner_radius=12, 
            border_width=1, 
            border_color="#333333"
        )
        container.pack(expand=True, fill=tk.BOTH, padx=15, pady=15)

        ctk.CTkLabel(
            container, 
            text="Código de la sala:", 
            font=("Helvetica Neue", 13, "bold"),
            text_color="#ffffff"
        ).pack(pady=(12, 5))

        entrada = ctk.CTkEntry(
            container, 
            width=180, 
            height=34,
            placeholder_text="Código (Ej: AB12CD)",
            font=("Helvetica Neue", 12),
            corner_radius=8,
            fg_color="#1a1a1a",
            border_color="#444444",
            text_color="#ffffff",
            placeholder_text_color="#888888",
            justify="center"
        )
        entrada.pack(pady=5)
        entrada.focus()

        def unirse():
            codigo = entrada.get().strip().upper()
            if not codigo:
                messagebox.showwarning("Atención", "Ingresa un código de sala.")
                return
            
            btn_unirse.configure(state="disabled", text="Uniendo...")
            ventana.update()
            
            try:
                respuesta = self._cliente_socket.enviar_y_recibir({
                    "type": "JOIN_ROOM_REQUEST",
                    "codigo": codigo,
                    "idUsuario": self._usuario.id_usuario
                }, response_type="JOIN_ROOM_REQUEST")
                
                if respuesta.get("status") == "success":
                    if respuesta.get("admitido"):
                        self._on_entrar_sala(codigo, False, respuesta["idSala"])
                    else:
                        messagebox.showinfo("Solicitud Enviada", "Espera a que el host te admita.")
                    ventana.destroy()
                else:
                    messagebox.showerror("Error", respuesta.get("message", "Error al unirse"))
            except Exception as e:
                messagebox.showerror("Error", f"Error de conexión: {e}")
            finally:
                if ventana.winfo_exists():
                    btn_unirse.configure(state="normal", text="Unirse")

        entrada.bind("<Return>", lambda e: unirse())

        btn_unirse = ctk.CTkButton(
            container, 
            text="Unirse", 
            command=unirse,
            width=180, 
            height=34,
            font=("Helvetica Neue", 12, "bold"), 
            fg_color="#4CAF50", 
            hover_color="#3e8e41", 
            text_color="white",
            corner_radius=8
        )
        btn_unirse.pack(pady=15)

    def _admitido_en_sala(self, msg):
        self.after(0, self._on_entrar_sala, msg["codigo"], False, msg["idSala"])

    def _cerrar_sesion(self):
        self._limpiar_callbacks()
        self._on_cerrar_sesion()

