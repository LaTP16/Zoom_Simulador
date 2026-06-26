import os
import customtkinter as ctk
import tkinter as tk
from tkinter import scrolledtext, messagebox
from Cliente.modelos.mensaje import Mensaje
from Cliente.gestores.gestor_video import GestorVideo
from Cliente.gestores.gestor_audio import GestorAudio
from Cliente.gestores.gestor_archivos import GestorArchivos



class PantallaSala(ctk.CTkFrame):
    """
    Pantalla principal de la sala de reunión.
    Se encarga únicamente de la UI y la coordinación entre los gestores;
    toda la lógica de video, audio y archivos está delegada en sus respectivos gestores.
    """

    def __init__(self, master, usuario, cliente_socket, codigo_sala, es_host, id_sala, on_salir):
        super().__init__(master)
        self._usuario = usuario
        self._cliente_socket = cliente_socket
        self._codigo_sala = codigo_sala
        self._es_host = es_host
        self._id_sala = id_sala
        self._on_salir = on_salir
        self._link_counter = 0
        self._solicitantes = {}  # { idUsuario: { nombre } }
        self._participantes_actuales = []
        self._download_dir = os.path.join(os.path.dirname(__file__), "..", "descargas")
        os.makedirs(self._download_dir, exist_ok=True)


        self._crear_widgets()
        self._inicializar_gestores()
        self._registrar_callbacks()
        self._cliente_socket.enviar({"type": "GET_ROOM_PARTICIPANTS", "roomCode": self._codigo_sala})

    # ------------------------------------------------------------------
    # Construcción de la UI
    # ------------------------------------------------------------------

    def _crear_widgets(self):
        ctk.CTkLabel(self, text=f"Sala: {self._codigo_sala}",
                  font=("Arial", 14, "bold")).pack(pady=(10, 5))

        # Área de video
        self._frame_video_container = ctk.CTkFrame(self, fg_color="#1a1a1a", height=200)
        self._frame_video_container.pack(fill=tk.X, padx=10, pady=(0, 5))
        self._frame_video_container.pack_propagate(False)

        self._frame_video_panels = ctk.CTkFrame(self._frame_video_container, fg_color="transparent")
        self._frame_video_panels.pack(fill=tk.BOTH, expand=True)

        # Controles de cámara y micrófono
        frame_controles = ctk.CTkFrame(self, fg_color="transparent")
        frame_controles.pack(fill=tk.X, padx=10, pady=(0, 5))

        self._btn_camara = ctk.CTkButton(
            frame_controles, text="📷 Iniciar Cámara",
            command=self._toggle_camara, fg_color="#4CAF50", text_color="white", width=140, font=("Arial", 11, "bold")
        )
        self._btn_camara.pack(side=tk.LEFT, padx=5)

        self._btn_mic = ctk.CTkButton(
            frame_controles, text="🎤 Iniciar Micrófono",
            command=self._toggle_mic, fg_color="#4CAF50", text_color="white", width=150, font=("Arial", 11, "bold")
        )
        self._btn_mic.pack(side=tk.LEFT, padx=5)

        self._label_cam_status = ctk.CTkLabel(
            frame_controles, text="", text_color="#888", font=("Arial", 9)
        )
        self._label_cam_status.pack(side=tk.LEFT, padx=(5, 0))

        # Layout principal: panel izquierdo + chat
        frame_principal = ctk.CTkFrame(self, fg_color="transparent")
        frame_principal.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self._crear_panel_izquierdo(frame_principal)
        self._crear_panel_chat(frame_principal)

        ctk.CTkButton(self, text="Salir de la Sala", command=self._salir,
                  fg_color="#f44336", text_color="white", font=("Arial", 11, "bold")).pack(pady=10)

    def _crear_panel_izquierdo(self, padre):
        frame_izq = ctk.CTkFrame(padre, width=200, fg_color="transparent")
        frame_izq.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        frame_izq.pack_propagate(False)

        if self._es_host:
            ctk.CTkLabel(frame_izq, text="Sala de Espera",
                     font=("Arial", 11, "bold")).pack(pady=(0, 5))
            self._lista_espera = tk.Listbox(
                frame_izq, height=8, bg="#2b2b2b", fg="white",
                selectbackground="#1f538d", borderwidth=0, highlightthickness=0
            )
            self._lista_espera.pack(fill=tk.BOTH, expand=True)

            frame_botones = ctk.CTkFrame(frame_izq, fg_color="transparent")
            frame_botones.pack(fill=tk.X, pady=(0, 10))
            ctk.CTkButton(
                frame_botones, text="Admitir", command=self._admitir,
                fg_color="#4CAF50", text_color="white", width=80, font=("Arial", 11, "bold")
            ).pack(side=tk.LEFT, padx=2)
            ctk.CTkButton(
                frame_botones, text="Rechazar", command=self._rechazar,
                fg_color="#f44336", text_color="white", width=80, font=("Arial", 11, "bold")
            ).pack(side=tk.LEFT, padx=2)

        ctk.CTkLabel(frame_izq, text="Conectados",
                 font=("Arial", 11, "bold")).pack(pady=(0, 5))
        self._lista_conectados = tk.Listbox(
            frame_izq, height=8, bg="#2b2b2b", fg="white",
            selectbackground="#1f538d", borderwidth=0, highlightthickness=0
        )
        self._lista_conectados.pack(fill=tk.BOTH, expand=True)

        if self._es_host:
            ctk.CTkButton(
                frame_izq, text="Expulsar", command=self._expulsar,
                fg_color="#f44336", text_color="white", font=("Arial", 11, "bold")
            ).pack(fill=tk.X, pady=(5, 0))

    def _crear_panel_chat(self, padre):
        frame_chat = ctk.CTkFrame(padre, fg_color="transparent")
        frame_chat.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ctk.CTkLabel(frame_chat, text="Chat", font=("Arial", 11, "bold")).pack()
        self._chat_text = scrolledtext.ScrolledText(
            frame_chat, height=15, state=tk.DISABLED, bg="#2b2b2b", fg="white",
            insertbackground="white", borderwidth=0, highlightthickness=0
        )
        self._chat_text.pack(fill=tk.BOTH, expand=True)

        frame_input = ctk.CTkFrame(frame_chat, fg_color="transparent")
        frame_input.pack(fill=tk.X, pady=5)

        self._entrada_msg = ctk.CTkEntry(frame_input, font=("Arial", 11))
        self._entrada_msg.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._entrada_msg.bind("<Return>", lambda e: self._enviar_mensaje())

        ctk.CTkButton(
            frame_input, text="Enviar", command=self._enviar_mensaje,
            fg_color="#2196F3", text_color="white", width=70, font=("Arial", 11, "bold")
        ).pack(side=tk.RIGHT, padx=(2, 0))
        ctk.CTkButton(
            frame_input, text="Archivo", command=self._enviar_archivo,
            fg_color="#9C27B0", text_color="white", width=70, font=("Arial", 11, "bold")
        ).pack(side=tk.RIGHT, padx=(0, 2))
        ctk.CTkButton(
            frame_input, text="Abrir descargas",
            command=self._abrir_carpeta_descargas,
            fg_color="#607D8B", text_color="white", width=120, font=("Arial", 11, "bold")
        ).pack(side=tk.RIGHT, padx=(0, 2))

    # ------------------------------------------------------------------
    # Inicialización de gestores
    # ------------------------------------------------------------------

    def _inicializar_gestores(self):
        self._gestor_video = GestorVideo(
            master=self,
            cliente_socket=self._cliente_socket,
            codigo_sala=self._codigo_sala,
            usuario=self._usuario,
            frame_video_panels=self._frame_video_panels,
            btn_camara=self._btn_camara,
            label_cam_status=self._label_cam_status,
            on_mensaje=self._agregar_mensaje
        )
        self._gestor_audio = GestorAudio(
            master=self,
            cliente_socket=self._cliente_socket,
            codigo_sala=self._codigo_sala,
            usuario=self._usuario,
            btn_mic=self._btn_mic,
            on_mensaje=self._agregar_mensaje
        )
        self._gestor_archivos = GestorArchivos(
            master=self,
            cliente_socket=self._cliente_socket,
            codigo_sala=self._codigo_sala,
            usuario=self._usuario,
            download_dir=self._download_dir,
            on_mensaje=self._agregar_mensaje,
            on_mensaje_link=self._agregar_mensaje_con_link
        )

    # ------------------------------------------------------------------
    # Registro de callbacks (patrón Observer)
    # ------------------------------------------------------------------

    def _registrar_callbacks(self):
        self._cliente_socket.registrar_callback("CHAT_MESSAGE", self._recibir_mensaje)
        self._cliente_socket.registrar_callback("ROOM_PARTICIPANTS", self._actualizar_conectados)

        # Video — delegado al GestorVideo
        self._cliente_socket.registrar_callback("VIDEO_START", self._gestor_video.on_video_start)
        self._cliente_socket.registrar_callback("VIDEO_STOP", self._gestor_video.on_video_stop)
        self._cliente_socket.registrar_callback("CAMERA_FRAME", self._gestor_video.on_camera_frame)

        # Audio — delegado al GestorAudio
        self._cliente_socket.registrar_callback("AUDIO_FRAME", self._gestor_audio.on_audio_frame)

        # Archivos — delegado al GestorArchivos
        self._cliente_socket.registrar_callback("FILE_START", self._gestor_archivos.on_file_start)
        self._cliente_socket.registrar_callback("FILE_CHUNK", self._gestor_archivos.on_file_chunk)
        self._cliente_socket.registrar_callback("FILE_END", self._gestor_archivos.on_file_end)

        if self._es_host:
            self._cliente_socket.registrar_callback("WAITING_ROOM_UPDATE", self._nuevo_solicitante)
        self._cliente_socket.registrar_callback("KICKED", self._ser_expulsado)
        self._cliente_socket.registrar_callback("ROOM_CLOSED", self._sala_cerrada)


    def _limpiar_callbacks(self):
        for tipo in ("CHAT_MESSAGE", "ROOM_PARTICIPANTS",
                     "VIDEO_START", "VIDEO_STOP", "CAMERA_FRAME",
                     "AUDIO_FRAME",
                     "FILE_START", "FILE_CHUNK", "FILE_END",
                     "WAITING_ROOM_UPDATE", "KICKED", "ROOM_CLOSED"):
            self._cliente_socket.remover_callback(tipo)

    # ------------------------------------------------------------------
    # Sala de espera (solo host)
    # ------------------------------------------------------------------

    def _nuevo_solicitante(self, msg):
        self.after(0, self._agregar_solicitante, msg["solicitanteId"], msg["solicitanteNombre"])

    def _agregar_solicitante(self, uid, nombre):
        self._solicitantes[uid] = {"nombre": nombre}
        self._lista_espera.insert(tk.END, f"{nombre} (ID: {uid})")

    def _admitir(self):
        sel = self._lista_espera.curselection()
        if not sel:
            return
        uid = int(self._lista_espera.get(sel[0]).split("ID: ")[1].rstrip(")"))
        self._cliente_socket.enviar({
            "type": "ADMIT_USER",
            "idSala": self._id_sala,
            "idUsuario": uid
        })
        self._lista_espera.delete(sel[0])
        self._solicitantes.pop(uid, None)

    def _rechazar(self):
        sel = self._lista_espera.curselection()
        if not sel:
            return
        uid = int(self._lista_espera.get(sel[0]).split("ID: ")[1].rstrip(")"))
        self._cliente_socket.enviar({
            "type": "REJECT_USER",
            "idSala": self._id_sala,
            "idUsuario": uid
        })
        self._lista_espera.delete(sel[0])
        self._solicitantes.pop(uid, None)

    def _actualizar_conectados(self, msg):
        participantes = msg.get("participants", [])
        self.after(0, self._refrescar_lista_conectados, participantes)

    def _refrescar_lista_conectados(self, participantes):
        self._participantes_actuales = participantes
        self._lista_conectados.delete(0, tk.END)
        for p in participantes:
            texto = p.get("nombres", "Desconocido")
            if p.get("idUsuario") == self._usuario.id_usuario:
                texto += " (Tú)"
            self._lista_conectados.insert(tk.END, texto)

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    def _enviar_mensaje(self):
        texto = self._entrada_msg.get().strip()
        if not texto:
            return
        msg = Mensaje(self._usuario.id_usuario, self._usuario.nombres, texto, self._codigo_sala)
        self._cliente_socket.enviar(msg.a_dict())
        self._agregar_mensaje(f"Tú: {texto}")
        self._entrada_msg.delete(0, tk.END)

    def _recibir_mensaje(self, msg):
        if msg.get("userName") != self._usuario.nombres:
            self.after(0, self._agregar_mensaje, f"{msg['userName']}: {msg['message']}")

    def _agregar_mensaje(self, texto):
        self._chat_text.config(state=tk.NORMAL)
        self._chat_text.insert(tk.END, texto + "\n")
        self._chat_text.see(tk.END)
        self._chat_text.config(state=tk.DISABLED)

    def _agregar_mensaje_con_link(self, pre_texto, link_texto, post_texto, ruta_archivo):
        self._chat_text.config(state=tk.NORMAL)
        self._chat_text.insert(tk.END, pre_texto)

        self._link_counter += 1
        tag_name = f"link_{self._link_counter}"
        self._chat_text.insert(tk.END, link_texto, tag_name)
        self._chat_text.tag_config(tag_name, foreground="#2196F3", underline=True)
        self._chat_text.tag_bind(
            tag_name, "<Button-1>",
            lambda event, r=ruta_archivo: GestorArchivos.abrir_archivo(r, self._agregar_mensaje)
        )
        self._chat_text.tag_bind(tag_name, "<Enter>", lambda e: self._chat_text.config(cursor="hand2"))
        self._chat_text.tag_bind(tag_name, "<Leave>", lambda e: self._chat_text.config(cursor=""))

        self._chat_text.insert(tk.END, post_texto + "\n")
        self._chat_text.see(tk.END)
        self._chat_text.config(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Delegación a gestores (mantiene el botón conectado al gestor)
    # ------------------------------------------------------------------

    def _toggle_camara(self):
        self._gestor_video.toggle_camara()

    def _toggle_mic(self):
        self._gestor_audio.toggle_mic()

    def _enviar_archivo(self):
        self._gestor_archivos.enviar_archivo()

    def _abrir_carpeta_descargas(self):
        self._gestor_archivos.abrir_carpeta_descargas()

    def _expulsar(self):
        sel = self._lista_conectados.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._participantes_actuales):
            return
        participante = self._participantes_actuales[idx]
        if participante["idUsuario"] == self._usuario.id_usuario:
            messagebox.showwarning("Advertencia", "No puedes expulsarte a ti mismo.")
            return

        self._cliente_socket.enviar({
            "type": "KICK_USER",
            "roomCode": self._codigo_sala,
            "idSala": self._id_sala,
            "targetId": participante["idUsuario"]
        })

    def _ser_expulsado(self, msg):
        self.after(0, self._on_expulsado_ui)

    def _on_expulsado_ui(self):
        messagebox.showinfo("Información", "Has sido expulsado de la sala por el anfitrión.")
        self._salir()

    def _sala_cerrada(self, msg):
        self.after(0, self._on_sala_cerrada_ui)

    def _on_sala_cerrada_ui(self):
        messagebox.showinfo("Información", "La sala ha sido finalizada por el anfitrión.")
        if self._gestor_video.camara_activa:
            self._gestor_video.detener_captura()
        self._gestor_audio.detener()
        self._limpiar_callbacks()
        self._on_salir()

    # ------------------------------------------------------------------
    # Salir de la sala
    # ------------------------------------------------------------------

    def _salir(self):
        if self._gestor_video.camara_activa:
            self._gestor_video.detener_captura()
        self._gestor_audio.detener()
        self._cliente_socket.enviar({"type": "LEAVE_ROOM", "roomCode": self._codigo_sala})
        self._limpiar_callbacks()
        self._on_salir()


