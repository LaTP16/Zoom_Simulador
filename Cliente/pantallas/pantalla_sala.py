import base64
import os
import platform
import shutil
import subprocess
import threading
import time
import tkinter as tk
from tkinter import filedialog, scrolledtext
import queue
import sounddevice as sd
from Cliente.pantallas.pantalla_video import PanelVideo

class PantallaSala(tk.Frame):
    def __init__(self, master, usuario, cliente_socket, codigo_sala, es_host, id_sala, on_salir):
        super().__init__(master)
        self._usuario = usuario
        self._cliente_socket = cliente_socket
        self._codigo_sala = codigo_sala
        self._es_host = es_host
        self._id_sala = id_sala
        self._on_salir = on_salir
        self._file_recv = {}
        self._link_counter = 0
        self._download_dir = os.path.join(os.path.dirname(__file__), "..", "descargas")
        os.makedirs(self._download_dir, exist_ok=True)
        self._crear_widgets()
        self._registrar_callbacks()
        
        self._mic_activo = False
        self._capturando_mic = False
        self._audio_activo = True
        self._audio_queue = queue.Queue()
        threading.Thread(target=self._audio_playback_loop, daemon=True).start()

    def _crear_widgets(self):
        tk.Label(self, text=f"Sala: {self._codigo_sala}",
                 font=("Arial", 12, "bold")).pack(pady=(10, 5))

        # === VIDEO SECTION ===
        self._frame_video_container = tk.Frame(self, bg="#1a1a1a", height=200)
        self._frame_video_container.pack(fill=tk.X, padx=10, pady=(0, 5))
        self._frame_video_container.pack_propagate(False)

        self._frame_video_panels = tk.Frame(self._frame_video_container, bg="#1a1a1a")
        self._frame_video_panels.pack(fill=tk.BOTH, expand=True)

        self._frame_controles = tk.Frame(self)
        self._frame_controles.pack(fill=tk.X, padx=10, pady=(0, 5))
        self._btn_camara = tk.Button(
            self._frame_controles, text="📷 Iniciar Cámara",
            command=self._toggle_camara, bg="#4CAF50", fg="white", width=16
        )
        self._btn_camara.pack(side=tk.LEFT, padx=5)

        self._btn_mic = tk.Button(
            self._frame_controles, text="🎤 Iniciar Micrófono",
            command=self._toggle_mic, bg="#4CAF50", fg="white", width=18
        )
        self._btn_mic.pack(side=tk.LEFT, padx=5)
        self._label_cam_status = tk.Label(
            self._frame_controles, text="", fg="#888", font=("Arial", 8)
        )
        self._label_cam_status.pack(side=tk.LEFT, padx=(5, 0))

        self._paneles_video = {}
        self._camara_activa = False
        self._capturando = False
        self._video_panel_local = None
        self._video_proc = None
        self._backend_video = None

        frame_principal = tk.Frame(self)
        frame_principal.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        if self._es_host:
            frame_izq = tk.Frame(frame_principal, width=200)
            frame_izq.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
            frame_izq.pack_propagate(False)

            tk.Label(frame_izq, text="Sala de Espera",
                     font=("Arial", 10, "bold")).pack(pady=(0, 5))
            self._lista_espera = tk.Listbox(frame_izq, height=10)
            self._lista_espera.pack(fill=tk.BOTH, expand=True)

            frame_botones = tk.Frame(frame_izq)
            frame_botones.pack(fill=tk.X, pady=5)
            tk.Button(frame_botones, text="Admitir", command=self._admitir,
                      bg="#4CAF50", fg="white", width=8).pack(side=tk.LEFT, padx=2)
            tk.Button(frame_botones, text="Rechazar", command=self._rechazar,
                      bg="#f44336", fg="white", width=8).pack(side=tk.LEFT, padx=2)

            self._solicitantes = {}

            frame_chat = tk.Frame(frame_principal)
            frame_chat.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        else:
            frame_chat = frame_principal

        tk.Label(frame_chat, text="Chat", font=("Arial", 10, "bold")).pack()
        self._chat_text = scrolledtext.ScrolledText(frame_chat, height=15, state=tk.DISABLED)
        self._chat_text.pack(fill=tk.BOTH, expand=True)

        frame_input = tk.Frame(frame_chat)
        frame_input.pack(fill=tk.X, pady=5)
        self._entrada_msg = tk.Entry(frame_input)
        self._entrada_msg.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._entrada_msg.bind("<Return>", lambda e: self._enviar_mensaje())
        tk.Button(frame_input, text="Enviar", command=self._enviar_mensaje,
                  bg="#2196F3", fg="white").pack(side=tk.RIGHT, padx=(2, 0))
        tk.Button(frame_input, text="📎 Archivo", command=self._enviar_archivo,
                  bg="#9C27B0", fg="white").pack(side=tk.RIGHT, padx=(0, 2))
        self._btn_abrir_descargas = tk.Button(
            frame_input,
            text="Abrir carpeta de descargas",
            command=self._abrir_carpeta_descargas,
            bg="#607D8B",
            fg="white",
        )
        self._btn_abrir_descargas.pack(side=tk.RIGHT, padx=(0, 2))

        tk.Button(self, text="Salir de la Sala", command=self._salir,
                  bg="#f44336", fg="white", font=("Arial", 10)).pack(pady=10)

    def _registrar_callbacks(self):
        self._cliente_socket.registrar_callback("CHAT_MESSAGE", self._recibir_mensaje)
        self._cliente_socket.registrar_callback("FILE_START", self._recibir_file_start)
        self._cliente_socket.registrar_callback("FILE_CHUNK", self._recibir_file_chunk)
        self._cliente_socket.registrar_callback("FILE_END", self._recibir_file_end)
        self._cliente_socket.registrar_callback("CAMERA_FRAME", self._on_camera_frame)
        self._cliente_socket.registrar_callback("VIDEO_START", self._on_video_start)
        self._cliente_socket.registrar_callback("VIDEO_STOP", self._on_video_stop)
        self._cliente_socket.registrar_callback("AUDIO_FRAME", self._recibir_audio_frame)
        if self._es_host:
            self._cliente_socket.registrar_callback("WAITING_ROOM_UPDATE", self._nuevo_solicitante)

    def _limpiar_callbacks(self):
        self._cliente_socket.remover_callback("CHAT_MESSAGE")
        self._cliente_socket.remover_callback("FILE_START")
        self._cliente_socket.remover_callback("FILE_CHUNK")
        self._cliente_socket.remover_callback("FILE_END")
        self._cliente_socket.remover_callback("CAMERA_FRAME")
        self._cliente_socket.remover_callback("VIDEO_START")
        self._cliente_socket.remover_callback("VIDEO_STOP")
        self._cliente_socket.remover_callback("AUDIO_FRAME")
        if self._es_host:
            self._cliente_socket.remover_callback("WAITING_ROOM_UPDATE")

    def _nuevo_solicitante(self, msg):
        self.after(0, self._agregar_solicitante, msg["solicitanteId"], msg["solicitanteNombre"])

    def _agregar_solicitante(self, uid, nombre):
        self._solicitantes[uid] = {"nombre": nombre}
        self._lista_espera.insert(tk.END, f"{nombre} (ID: {uid})")

    def _admitir(self):
        sel = self._lista_espera.curselection()
        if not sel:
            return
        texto = self._lista_espera.get(sel[0])
        uid = int(texto.split("ID: ")[1].rstrip(")"))
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
        texto = self._lista_espera.get(sel[0])
        uid = int(texto.split("ID: ")[1].rstrip(")"))
        self._cliente_socket.enviar({
            "type": "REJECT_USER",
            "idSala": self._id_sala,
            "idUsuario": uid
        })
        self._lista_espera.delete(sel[0])
        self._solicitantes.pop(uid, None)

    def _enviar_mensaje(self):
        texto = self._entrada_msg.get().strip()
        if not texto:
            return
        self._cliente_socket.enviar({
            "type": "CHAT_MESSAGE",
            "roomCode": self._codigo_sala,
            "userName": self._usuario.nombres,
            "message": texto
        })
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

    def _agregar_mensaje_descargas(self, texto):
        self._chat_text.config(state=tk.NORMAL)
        self._chat_text.insert(tk.END, texto + "\n")
        self._chat_text.see(tk.END)
        self._chat_text.config(state=tk.DISABLED)

    def _abrir_archivo(self, ruta):
        ruta = os.path.abspath(ruta)
        if not os.path.exists(ruta):
            self._agregar_mensaje(f"❌ El archivo no existe: {ruta}")
            return
        try:
            if platform.system() == "Windows":
                os.startfile(ruta)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", ruta])
            else:
                subprocess.Popen(["xdg-open", ruta])
        except Exception as e:
            self._agregar_mensaje(f"❌ No se pudo abrir el archivo: {e}")

    def _agregar_mensaje_con_link(self, pre_texto, link_texto, post_texto, ruta_archivo):
        self._chat_text.config(state=tk.NORMAL)
        self._chat_text.insert(tk.END, pre_texto)
        
        self._link_counter += 1
        tag_name = f"link_{self._link_counter}"
        self._chat_text.insert(tk.END, link_texto, tag_name)
        
        self._chat_text.tag_config(tag_name, foreground="#2196F3", underline=True)
        self._chat_text.tag_bind(tag_name, "<Button-1>", lambda event, r=ruta_archivo: self._abrir_archivo(r))
        self._chat_text.tag_bind(tag_name, "<Enter>", lambda event: self._chat_text.config(cursor="hand2"))
        self._chat_text.tag_bind(tag_name, "<Leave>", lambda event: self._chat_text.config(cursor=""))
        
        self._chat_text.insert(tk.END, post_texto + "\n")
        self._chat_text.see(tk.END)
        self._chat_text.config(state=tk.DISABLED)

    def _abrir_carpeta_descargas(self, event=None):
        ruta = os.path.abspath(self._download_dir)
        os.makedirs(ruta, exist_ok=True)
        try:
            if platform.system() == "Windows":
                os.startfile(ruta)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", ruta])
            else:
                subprocess.Popen(["xdg-open", ruta])
        except Exception as e:
            self._agregar_mensaje(f"❌ No se pudo abrir la carpeta de descargas: {e}")

    @staticmethod
    def _detectar_backend():
        if platform.system() == "Windows":
            try:
                import cv2
                return "opencv"
            except ImportError:
                return None
        try:
            import cv2
            return "opencv"
        except ImportError:
            return "ffmpeg" if shutil.which("ffmpeg") else None

    def _toggle_camara(self):
        backend = self._detectar_backend()
        if not backend:
            self._agregar_mensaje("❌ No hay backend de cámara. En Windows instala 'opencv-python'; en Linux instala ffmpeg.")
            return
        self._backend_video = backend
        if self._camara_activa:
            self._detener_captura()
        else:
            self._iniciar_captura()

    def _iniciar_captura(self):
        if self._capturando:
            return
        self._capturando = True
        self._camara_activa = True
        self._btn_camara.config(text="📷 Detener Cámara", bg="#f44336")
        self._label_cam_status.config(text="Iniciando cámara...")

        self._video_panel_local = PanelVideo(
            self._frame_video_panels, usuario_nombre=f"{self._usuario.nombres} (Tú)",
            width=240, height=180
        )
        self._video_panel_local.pack(side=tk.LEFT, padx=2)

        self._cliente_socket.enviar({
            "type": "VIDEO_START",
            "roomCode": self._codigo_sala,
            "userName": self._usuario.nombres
        })

        threading.Thread(target=self._capturar_y_enviar, daemon=True).start()

    def _capturar_y_enviar(self):
        try:
            if self._backend_video == "opencv":
                self._capturar_con_opencv()
            else:
                self._capturar_con_ffmpeg()
        except Exception as e:
            self.after(0, self._agregar_mensaje, f"❌ Error de cámara: {e}")
            self.after(0, self._detener_captura)

    def _capturar_con_opencv(self):
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.after(0, self._agregar_mensaje, "❌ No se pudo abrir la cámara.")
            self.after(0, self._detener_captura)
            return

        self.after(0, lambda: self._label_cam_status.config(text="Cámara activa"))
        while self._capturando and self._cliente_socket._conectado:
            ret, frame = cap.read()
            if not ret:
                continue

            frame = cv2.resize(frame, (320, 240))
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            datos_b64 = base64.b64encode(buffer).decode()

            self._cliente_socket.enviar({
                "type": "CAMERA_FRAME",
                "roomCode": self._codigo_sala,
                "userName": self._usuario.nombres,
                "data": datos_b64
            })

            self.after(0, lambda b=datos_b64: self._video_panel_local.actualizar_frame(b)
                       if self._video_panel_local else None)

            time.sleep(0.1) #Intervalo de 100 ms para limitar la tasa de envío
        cap.release()

    def _capturar_con_ffmpeg(self):
        proc = subprocess.Popen(
            ["ffmpeg", "-f", "v4l2", "-video_size", "320x240",
             "-i", "/dev/video0", "-f", "image2pipe",
             "-vcodec", "mjpeg", "-r", "15",
             "-loglevel", "quiet", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        self._video_proc = proc

        self.after(0, lambda: self._label_cam_status.config(text="Cámara activa"))
        buffer = b""
        while self._capturando and self._cliente_socket._conectado:
            try:
                datos = proc.stdout.read(4096)
            except ValueError:
                break
            if not datos:
                break
            buffer += datos

            while True:
                start = buffer.find(b'\xff\xd8')
                if start == -1:
                    break
                end = buffer.find(b'\xff\xd9', start)
                if end == -1:
                    break
                jpeg_data = buffer[start:end + 2]
                buffer = buffer[end + 2:]

                datos_b64 = base64.b64encode(jpeg_data).decode()
                self._cliente_socket.enviar({
                    "type": "CAMERA_FRAME",
                    "roomCode": self._codigo_sala,
                    "userName": self._usuario.nombres,
                    "data": datos_b64
                })

                self.after(0, lambda b=datos_b64: self._video_panel_local.actualizar_frame(b)
                           if self._video_panel_local else None)

        try:
            proc.terminate()
        except ProcessLookupError:
            pass

    def _detener_captura(self):
        self._capturando = False
        self._camara_activa = False
        self._btn_camara.config(text="📷 Iniciar Cámara", bg="#4CAF50")
        self._label_cam_status.config(text="")

        if self._video_proc:
            self._video_proc.terminate()
            self._video_proc = None

        if self._video_panel_local:
            self._video_panel_local.destroy()
            self._video_panel_local = None

        self._cliente_socket.enviar({
            "type": "VIDEO_STOP",
            "roomCode": self._codigo_sala,
            "userName": self._usuario.nombres
        })

    def _on_video_start(self, msg):
        user = msg.get("userName", "")
        if user == self._usuario.nombres:
            return
        self.after(0, self._agregar_panel_remoto, user)

    def _agregar_panel_remoto(self, user):
        if user in self._paneles_video:
            return
        panel = PanelVideo(
            self._frame_video_panels, usuario_nombre=user,
            width=240, height=180
        )
        panel.pack(side=tk.LEFT, padx=2)
        self._paneles_video[user] = panel

    def _on_video_stop(self, msg):
        user = msg.get("userName", "")
        if user == self._usuario.nombres:
            return
        self.after(0, self._remover_panel_remoto, user)

    def _remover_panel_remoto(self, user):
        panel = self._paneles_video.pop(user, None)
        if panel:
            panel.destroy()

    def _on_camera_frame(self, msg):
        user = msg.get("userName", "")
        if user == self._usuario.nombres:
            return
        datos = msg.get("data", "")
        self.after(0, self._actualizar_frame_remoto, user, datos)

    def _actualizar_frame_remoto(self, user, datos_b64):
        panel = self._paneles_video.get(user)
        if panel:
            panel.actualizar_frame(datos_b64)

    def _enviar_archivo(self):
        ruta = filedialog.askopenfilename(title="Seleccionar archivo")
        if not ruta:
            return
        nombre = os.path.basename(ruta)
        tamano = os.path.getsize(ruta)
        self._agregar_mensaje(f"📤 Enviando: {nombre} ({tamano} bytes)...")
        threading.Thread(target=self._enviar_archivo_thread, args=(ruta, nombre, tamano), daemon=True).start()

    def _enviar_archivo_thread(self, ruta, nombre, tamano):
        try:
            CHUNK_SIZE = 1500
            with open(ruta, "rb") as f:
                datos = base64.b64encode(f.read()).decode()
            self._cliente_socket.enviar({
                "type": "FILE_START",
                "roomCode": self._codigo_sala,
                "fileName": nombre,
                "fileSize": tamano,
                "userName": self._usuario.nombres
            })
            for i in range(0, len(datos), CHUNK_SIZE):
                self._cliente_socket.enviar({
                    "type": "FILE_CHUNK",
                    "roomCode": self._codigo_sala,
                    "fileName": nombre,
                    "data": datos[i:i + CHUNK_SIZE]
                })
            self._cliente_socket.enviar({
                "type": "FILE_END",
                "roomCode": self._codigo_sala,
                "fileName": nombre
            })
            self.after(0, lambda: self._agregar_mensaje_con_link("✅ Archivo enviado: ", nombre, "", ruta))
        except Exception as e:
            self.after(0, self._agregar_mensaje, f"❌ Error al enviar {nombre}: {e}")

    def _recibir_file_start(self, msg):
        if msg.get("userName") == self._usuario.nombres:
            return
        rid = msg["fileName"]
        self._file_recv[rid] = {
            "name": rid,
            "size": msg["fileSize"],
            "data": "",
            "user": msg["userName"]
        }
        self.after(0, self._agregar_mensaje, f"📥 Recibiendo: {rid} ({msg['fileSize']} bytes) de {msg['userName']}...")

    def _recibir_file_chunk(self, msg):
        nombre = msg.get("fileName")
        if nombre and nombre in self._file_recv:
            self._file_recv[nombre]["data"] += msg["data"]

    def _recibir_file_end(self, msg):
        rid = msg["fileName"]
        info = self._file_recv.pop(rid, None)
        if not info:
            return
        try:
            datos = base64.b64decode(info["data"])
            ruta = os.path.join(self._download_dir, rid)
            with open(ruta, "wb") as f:
                f.write(datos)
            self.after(0, lambda: self._agregar_mensaje_con_link("✅ Archivo recibido: ", rid, " (guardado en descargas/)", ruta))
        except Exception as e:
            self.after(0, self._agregar_mensaje, f"❌ Error al guardar {rid}: {e}")

    def _salir(self):
        if self._camara_activa:
            self._detener_captura()
        if self._mic_activo:
            self._capturando_mic = False
            self._mic_activo = False
        self._audio_activo = False
        self._cliente_socket.enviar({"type": "LEAVE_ROOM", "roomCode": self._codigo_sala})
        self._limpiar_callbacks()
        self._on_salir()

    def _toggle_mic(self):
        if self._mic_activo:
            self._capturando_mic = False
            self._mic_activo = False
            self._btn_mic.config(text="🎤 Iniciar Micrófono", bg="#4CAF50")
        else:
            # Comprobar si hay micrófonos
            try:
                devices = sd.query_devices()
                tiene_mic = any(d['max_input_channels'] > 0 for d in devices)
            except Exception:
                tiene_mic = False
            
            if not tiene_mic:
                self._agregar_mensaje("❌ No se detectó ningún micrófono en el sistema.")
                return
            
            self._mic_activo = True
            self._capturando_mic = True
            self._btn_mic.config(text="🎤 Silenciar Micrófono", bg="#f44336")
            threading.Thread(target=self._capturar_y_enviar_audio, daemon=True).start()

    def _capturar_y_enviar_audio(self):
        samplerate = 16000
        channels = 1
        blocksize = 1024
        dtype = 'int16'
        try:
            with sd.RawInputStream(samplerate=samplerate, channels=channels, dtype=dtype, blocksize=blocksize) as stream:
                while self._capturando_mic and self._cliente_socket._conectado:
                    data, overflowed = stream.read(blocksize)
                    if not data:
                        continue
                    datos_b64 = base64.b64encode(data).decode()
                    self._cliente_socket.enviar({
                        "type": "AUDIO_FRAME",
                        "roomCode": self._codigo_sala,
                        "userName": self._usuario.nombres,
                        "data": datos_b64
                    })
        except Exception as e:
            self.after(0, self._agregar_mensaje, f"❌ Error en el micrófono: {e}")
            self.after(0, lambda: self._btn_mic.config(text="🎤 Iniciar Micrófono", bg="#4CAF50"))
            self._mic_activo = False
            self._capturando_mic = False

    def _recibir_audio_frame(self, msg):
        if msg.get("userName") == self._usuario.nombres:
            return
        datos_b64 = msg.get("data", "")
        if datos_b64:
            try:
                datos = base64.b64decode(datos_b64)
                self._audio_queue.put(datos)
            except Exception:
                pass

    def _audio_playback_loop(self):
        samplerate = 16000
        channels = 1
        blocksize = 1024
        dtype = 'int16'
        try:
            # Check if there is an output device
            try:
                devices = sd.query_devices()
                tiene_salida = any(d['max_output_channels'] > 0 for d in devices)
            except Exception:
                tiene_salida = False
                
            if not tiene_salida:
                return

            with sd.RawOutputStream(samplerate=samplerate, channels=channels, dtype=dtype, blocksize=blocksize) as stream:
                while self._audio_activo:
                    try:
                        data = self._audio_queue.get(timeout=0.5)
                        stream.write(data)
                    except queue.Empty:
                        continue
        except Exception as e:
            print(f"Error en reproducción de audio: {e}")
