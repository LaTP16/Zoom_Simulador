import base64
import platform
import shutil
import subprocess
import threading
import time
import tkinter as tk
from Cliente.pantallas.pantalla_video import PanelVideo


class GestorVideo:
    """
    Gestor de cámara y video.
    Encapsula la captura local (OpenCV o FFmpeg), el envío de frames
    al servidor y la visualización de los paneles de video remotos.
    """

    def __init__(self, master, cliente_socket, codigo_sala, usuario,
                 frame_video_panels, btn_camara, label_cam_status, on_mensaje):
        self._master = master
        self._cliente_socket = cliente_socket
        self._codigo_sala = codigo_sala
        self._usuario = usuario
        self._frame_video_panels = frame_video_panels
        self._btn_camara = btn_camara
        self._label_cam_status = label_cam_status
        self._on_mensaje = on_mensaje  # callback para mostrar mensajes en el chat

        self._camara_activa = False
        self._capturando = False
        self._video_panel_local = None
        self._video_proc = None
        self._backend_video = None
        self._paneles_video = {}  # { userName: PanelVideo }

    # ------------------------------------------------------------------
    # Interfaz pública
    # ------------------------------------------------------------------

    @property
    def camara_activa(self):
        return self._camara_activa

    def toggle_camara(self):
        """Alterna el estado de la cámara (encender/apagar)."""
        backend = self._detectar_backend()
        if not backend:
            self._on_mensaje(
                "❌ No hay backend de cámara. "
                "En Windows instala 'opencv-python'; en Linux instala ffmpeg."
            )
            return
        self._backend_video = backend
        if self._camara_activa:
            self.detener_captura()
        else:
            self._iniciar_captura()

    def detener_captura(self):
        """Detiene la captura de video y notifica al servidor."""
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

    # ------------------------------------------------------------------
    # Callbacks de red (Observer)
    # ------------------------------------------------------------------

    def on_video_start(self, msg):
        """Recibe notificación de que un usuario remoto activó su cámara."""
        user = msg.get("userName", "")
        if user == self._usuario.nombres:
            return
        self._master.after(0, self._agregar_panel_remoto, user)

    def on_video_stop(self, msg):
        """Recibe notificación de que un usuario remoto desactivó su cámara."""
        user = msg.get("userName", "")
        if user == self._usuario.nombres:
            return
        self._master.after(0, self._remover_panel_remoto, user)

    def on_camera_frame(self, msg):
        """Recibe un frame JPEG en base64 de un usuario remoto."""
        user = msg.get("userName", "")
        if user == self._usuario.nombres:
            return
        datos = msg.get("data", "")
        self._master.after(0, self._actualizar_frame_remoto, user, datos)

    # ------------------------------------------------------------------
    # Lógica interna de captura
    # ------------------------------------------------------------------

    @staticmethod
    def _detectar_backend():
        """Devuelve 'opencv', 'ffmpeg' o None según lo disponible."""
        try:
            import cv2  # noqa: F401
            return "opencv"
        except ImportError:
            return "ffmpeg" if shutil.which("ffmpeg") else None

    def _iniciar_captura(self):
        if self._capturando:
            return
        self._capturando = True
        self._camara_activa = True
        self._btn_camara.config(text="📷 Detener Cámara", bg="#f44336")
        self._label_cam_status.config(text="Iniciando cámara...")

        self._video_panel_local = PanelVideo(
            self._frame_video_panels,
            usuario_nombre=f"{self._usuario.nombres} (Tú)",
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
            self._master.after(0, self._on_mensaje, f"❌ Error de cámara: {e}")
            self._master.after(0, self.detener_captura)

    def _capturar_con_opencv(self):
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self._master.after(0, self._on_mensaje, "❌ No se pudo abrir la cámara.")
            self._master.after(0, self.detener_captura)
            return

        self._master.after(0, lambda: self._label_cam_status.config(text="Cámara activa"))
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

            self._master.after(
                0,
                lambda b=datos_b64: self._video_panel_local.actualizar_frame(b)
                if self._video_panel_local else None
            )

            time.sleep(0.1)  # Intervalo de 100 ms para limitar la tasa de envío
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

        self._master.after(0, lambda: self._label_cam_status.config(text="Cámara activa"))
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

                self._master.after(
                    0,
                    lambda b=datos_b64: self._video_panel_local.actualizar_frame(b)
                    if self._video_panel_local else None
                )
        try:
            proc.terminate()
        except ProcessLookupError:
            pass

    # ------------------------------------------------------------------
    # Gestión de paneles remotos
    # ------------------------------------------------------------------

    def _agregar_panel_remoto(self, user):
        if user in self._paneles_video:
            return
        panel = PanelVideo(
            self._frame_video_panels,
            usuario_nombre=user,
            width=240, height=180
        )
        panel.pack(side=tk.LEFT, padx=2)
        self._paneles_video[user] = panel

    def _remover_panel_remoto(self, user):
        panel = self._paneles_video.pop(user, None)
        if panel:
            panel.destroy()

    def _actualizar_frame_remoto(self, user, datos_b64):
        panel = self._paneles_video.get(user)
        if panel:
            panel.actualizar_frame(datos_b64)
