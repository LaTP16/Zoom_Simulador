import base64, os, threading, queue, random, string
from nicegui import ui
from Cliente.modelos.mensaje import Mensaje
from web_cliente.estado import estado

_sala_ui = None

REMOTE_FRAMES = {}
LOCAL_FRAME = queue.Queue(maxsize=1)
AUDIO_OUT = queue.Queue()
MENSAJES = queue.Queue()
SOLICITANTES = {}
PARTICIPANTES = []

MEDIA_JS = """
<script>
let localStream = null;
let captureInterval = null;
let mediaRecorder = null;
let audioChunks = [];
let audioCtx = null;

window.startCamera = function(quality) {
    if (localStream) return;
    const q = quality || 50;
    navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        .then(function(stream) {
            localStream = stream;
            const video = document.getElementById('localVideo');
            if (video) video.srcObject = stream;
            const canvas = document.getElementById('captureCanvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            captureInterval = setInterval(function() {
                canvas.width = 320;
                canvas.height = 240;
                ctx.drawImage(video, 0, 0, 320, 240);
                window._lastFrame = canvas.toDataURL('image/jpeg', q/100);
            }, 100);
        }).catch(function(e) {
            console.error('Camera error:', e);
            window._cameraError = e.message;
        });
};

window.stopCamera = function() {
    if (captureInterval) clearInterval(captureInterval);
    captureInterval = null;
    if (localStream) {
        localStream.getTracks().forEach(function(t) { t.stop(); });
        localStream = null;
    }
    window._lastFrame = null;
};

window.getLocalFrame = function() {
    const f = window._lastFrame;
    if (f) return f.split(',')[1] || '';
    return '';
};

window.startMic = function() {
    if (mediaRecorder) return;
    navigator.mediaDevices.getUserMedia({ audio: true, video: false })
        .then(function(stream) {
            mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
            mediaRecorder.ondataavailable = function(e) {
                if (e.data.size > 0) {
                    audioChunks.push(e.data);
                }
            };
            mediaRecorder.start(100);
        }).catch(function(e) {
            window._micError = e.message;
        });
};

window.stopMic = function() {
    if (mediaRecorder) {
        mediaRecorder.stream.getTracks().forEach(function(t) { t.stop(); });
        mediaRecorder = null;
    }
};

window.getAudioChunk = function() {
    if (audioChunks.length === 0) return '';
    const blob = audioChunks.shift();
    return new Promise(function(resolve) {
        const reader = new FileReader();
        reader.onloadend = function() {
            const data = reader.result.split(',')[1] || '';
            resolve(data);
        };
        reader.readAsDataURL(blob);
    });
};

window.playAudio = function(base64Data, mimeType) {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const binary = atob(base64Data);
    const array = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) array[i] = binary.charCodeAt(i);
    audioCtx.decodeAudioData(array.buffer).then(function(buf) {
        const src = audioCtx.createBufferSource();
        src.buffer = buf;
        src.connect(audioCtx.destination);
        src.start();
    }).catch(function(e) {});
};

window.updateRemoteFrame = function(user, b64) {
    const img = document.getElementById('remote_' + user);
    if (img) img.src = 'data:image/jpeg;base64,' + b64;
};

window.addRemoteVideo = function(user) {
    const container = document.getElementById('remoteVideoContainer');
    if (!container || document.getElementById('remote_' + user)) return;
    const div = document.createElement('div');
    div.className = 'remote-video-item';
    div.innerHTML = '<div class="text-xs text-center bg-gray-800 text-white py-1">' + user + '</div>'
        + '<img id="remote_' + user + '" class="w-[240px] h-[180px] bg-black" src="" style="object-fit:cover">';
    container.appendChild(div);
};

window.removeRemoteVideo = function(user) {
    const img = document.getElementById('remote_' + user);
    if (img) {
        const div = img.parentElement;
        if (div) div.remove();
    }
};
</script>
"""

def inyectar_media_js():
    ui.add_body_html(MEDIA_JS)

class SalaUI:
    def __init__(self, on_salir):
        self._on_salir = on_salir
        self._camara_activa = False
        self._mic_activa = False
        self._solicitantes = {}
        self._participantes = []
        self._link_counter = 0
        self._download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "descargas")
        os.makedirs(self._download_dir, exist_ok=True)

    def build(self):
        inyectar_media_js()

        with ui.column().classes("w-full h-full gap-0"):
            # Header
            with ui.row().classes("w-full items-center justify-between bg-gray-900 text-white p-3"):
                ui.label(f"Sala: {estado.codigo_sala}").classes("text-lg font-bold")

            # Video area
            video_container = ui.element("div").classes("bg-gray-900 flex flex-wrap gap-1 p-2 min-h-[200px]")
            with video_container:
                ui.html('<video id="localVideo" autoplay muted class="hidden"></video>')
                ui.html('<canvas id="captureCanvas" class="hidden"></canvas>')
                ui.html('<div id="remoteVideoContainer" class="flex flex-wrap gap-1"></div>')

            # Media controls
            with ui.row().classes("gap-2 p-2 items-center"):
                self._btn_cam = ui.button("Iniciar Cámara", on_click=self._toggle_camara)\
                    .classes("bg-green-500 text-white")
                self._btn_mic = ui.button("Iniciar Micrófono", on_click=self._toggle_mic)\
                    .classes("bg-green-500 text-white")
                self._cam_status = ui.label("").classes("text-gray-400 text-xs")

            # Main content: left panel + chat
            with ui.row().classes("flex-1 gap-2 p-2 overflow-hidden"):
                # Left panel
                with ui.column().classes("w-64 gap-2"):
                    # Waiting room (host only)
                    if estado.es_host:
                        ui.label("Sala de Espera").classes("font-bold")
                        self._lista_espera = ui.list().classes("w-full h-32 overflow-y-auto border rounded")
                        with ui.row().classes("gap-1"):
                            ui.button("Admitir", on_click=self._admitir).classes("bg-green-500 text-white text-sm")
                            ui.button("Rechazar", on_click=self._rechazar).classes("bg-red-500 text-white text-sm")

                    # Participants
                    ui.label("Conectados").classes("font-bold")
                    self._lista_conectados = ui.list().classes("w-full h-32 overflow-y-auto border rounded")

                    if estado.es_host:
                        ui.button("Expulsar", on_click=self._expulsar).classes("bg-red-500 text-white w-full")

                # Chat
                with ui.column().classes("flex-1 gap-1"):
                    ui.label("Chat").classes("font-bold")
                    self._chat_area = ui.scroll_area().classes("flex-1 border rounded p-2 overflow-y-auto")
                    with self._chat_area:
                        self._chat_log = ui.column().classes("gap-0")

                    with ui.row().classes("w-full gap-1 items-center"):
                        self._entrada_msg = ui.input(placeholder="Escribe un mensaje...")\
                            .classes("flex-1").on("keydown.enter", self._enviar_mensaje)
                        ui.button("Enviar", on_click=self._enviar_mensaje)\
                            .classes("bg-blue-500 text-white")
                        ui.button("Archivo", on_click=self._enviar_archivo)\
                            .classes("bg-purple-500 text-white")
                        ui.button("Descargas", on_click=self._abrir_descargas)\
                            .classes("bg-gray-500 text-white")

            # Exit button
            ui.button("Salir de la Sala", on_click=self._salir)\
                .classes("bg-red-500 text-white w-full")

        self._registrar_callbacks()
        estado.socket.enviar({"type": "GET_ROOM_PARTICIPANTS", "roomCode": estado.codigo_sala})

        # Timers for video/audio polling
        self._timer_cam = ui.timer(0.1, self._poll_camera, once=False)
        self._timer_audio = ui.timer(0.2, self._poll_audio, once=False)

    def _registrar_callbacks(self):
        s = estado.socket
        s.registrar_callback("CHAT_MESSAGE", self._recibir_mensaje)
        s.registrar_callback("ROOM_PARTICIPANTS", self._actualizar_conectados)
        s.registrar_callback("CAMERA_FRAME", self._on_camera_frame)
        s.registrar_callback("VIDEO_START", self._on_video_start)
        s.registrar_callback("VIDEO_STOP", self._on_video_stop)
        s.registrar_callback("AUDIO_FRAME", self._on_audio_frame)
        if estado.es_host:
            s.registrar_callback("WAITING_ROOM_UPDATE", self._nuevo_solicitante)
        s.registrar_callback("KICKED", self._ser_expulsado)
        s.registrar_callback("ROOM_CLOSED", self._sala_cerrada)
        s.registrar_callback("FILE_START", self._on_file_start)
        s.registrar_callback("FILE_CHUNK", self._on_file_chunk)
        s.registrar_callback("FILE_END", self._on_file_end)

    def _limpiar_callbacks(self):
        s = estado.socket
        for t in ("CHAT_MESSAGE", "ROOM_PARTICIPANTS", "VIDEO_START", "VIDEO_STOP",
                  "CAMERA_FRAME", "AUDIO_FRAME", "WAITING_ROOM_UPDATE", "KICKED",
                  "ROOM_CLOSED", "FILE_START", "FILE_CHUNK", "FILE_END"):
            s.remover_callback(t)

    # --- Camera ---
    async def _toggle_camara(self):
        if self._camara_activa:
            await ui.run_javascript("stopCamera()")
            self._camara_activa = False
            self._btn_cam.text = "Iniciar Cámara"
            self._btn_cam.classes("bg-green-500 text-white", replace=False)
            self._cam_status.text = ""
            estado.socket.enviar({
                "type": "VIDEO_STOP", "roomCode": estado.codigo_sala,
                "userName": estado.usuario.nombres
            })
        else:
            q = 50
            await ui.run_javascript(f"startCamera({q})")
            self._camara_activa = True
            self._btn_cam.text = "Detener Cámara"
            self._btn_cam.classes("bg-red-500 text-white", replace=False)
            self._cam_status.text = "Cámara activa"
            estado.socket.enviar({
                "type": "VIDEO_START", "roomCode": estado.codigo_sala,
                "userName": estado.usuario.nombres
            })

    async def _poll_camera(self):
        if not self._camara_activa:
            return
        try:
            b64 = await ui.run_javascript("getLocalFrame()", respond=True)
            if b64:
                estado.socket.enviar({
                    "type": "CAMERA_FRAME",
                    "roomCode": estado.codigo_sala,
                    "userName": estado.usuario.nombres,
                    "data": b64
                })
        except Exception:
            pass

    def _on_video_start(self, msg):
        user = msg.get("userName", "")
        if user == estado.usuario.nombres:
            return
        ui.run_javascript(f"addRemoteVideo('{user}')")

    def _on_video_stop(self, msg):
        user = msg.get("userName", "")
        if user == estado.usuario.nombres:
            return
        ui.run_javascript(f"removeRemoteVideo('{user}')")

    def _on_camera_frame(self, msg):
        user = msg.get("userName", "")
        if user == estado.usuario.nombres:
            return
        b64 = msg.get("data", "")
        if b64:
            ui.run_javascript(f"updateRemoteFrame('{user}', '{b64}')")

    # --- Mic ---
    async def _toggle_mic(self):
        if self._mic_activa:
            await ui.run_javascript("stopMic()")
            self._mic_activa = False
            self._btn_mic.text = "Iniciar Micrófono"
            self._btn_mic.classes("bg-green-500 text-white", replace=False)
        else:
            await ui.run_javascript("startMic()")
            self._mic_activa = True
            self._btn_mic.text = "Silenciar Micrófono"
            self._btn_mic.classes("bg-red-500 text-white", replace=False)

    async def _poll_audio(self):
        if not self._mic_activa:
            return
        try:
            b64 = await ui.run_javascript("getAudioChunk()", respond=True)
            if b64:
                estado.socket.enviar({
                    "type": "AUDIO_FRAME",
                    "roomCode": estado.codigo_sala,
                    "userName": estado.usuario.nombres,
                    "data": b64
                })
        except Exception:
            pass

    def _on_audio_frame(self, msg):
        if msg.get("userName") == estado.usuario.nombres:
            return
        b64 = msg.get("data", "")
        if b64:
            ui.run_javascript(f"playAudio('{b64}', 'audio/webm;codecs=opus')")

    # --- Chat ---
    def _enviar_mensaje(self):
        texto = self._entrada_msg.value.strip()
        if not texto:
            return
        msg = Mensaje(estado.usuario.id_usuario, estado.usuario.nombres, texto, estado.codigo_sala)
        estado.socket.enviar(msg.a_dict())
        self._agregar_mensaje(f"Tú: {texto}")
        self._entrada_msg.value = ""

    def _recibir_mensaje(self, msg):
        if msg.get("userName") != estado.usuario.nombres:
            self._agregar_mensaje(f"{msg['userName']}: {msg['message']}")

    def _agregar_mensaje(self, texto):
        with self._chat_log:
            ui.label(texto).classes("text-sm py-0.5")
        self._chat_area.scroll_to(percent=1)

    # --- Waiting room ---
    def _nuevo_solicitante(self, msg):
        uid = msg["solicitanteId"]
        nombre = msg["solicitanteNombre"]
        self._solicitantes[uid] = nombre
        with self._lista_espera:
            ui.item(f"{nombre} (ID: {uid})").props(f"id=sol_{uid}")

    def _admitir(self):
        if not self._solicitantes:
            return
        uid = next(iter(self._solicitantes))
        estado.socket.enviar({
            "type": "ADMIT_USER", "idSala": estado.id_sala, "idUsuario": uid
        })
        self._solicitantes.pop(uid, None)
        self._refrescar_lista(self._lista_espera, self._solicitantes)

    def _rechazar(self):
        if not self._solicitantes:
            return
        uid = next(iter(self._solicitantes))
        estado.socket.enviar({
            "type": "REJECT_USER", "idSala": estado.id_sala, "idUsuario": uid
        })
        self._solicitantes.pop(uid, None)
        self._refrescar_lista(self._lista_espera, self._solicitantes)

    def _actualizar_conectados(self, msg):
        self._participantes = msg.get("participants", [])
        self._lista_conectados.clear()
        with self._lista_conectados:
            for p in self._participantes:
                texto = p.get("nombres", "Desconocido")
                if p.get("idUsuario") == estado.usuario.id_usuario:
                    texto += " (Tú)"
                ui.item(texto)

    def _refrescar_lista(self, lista, datos):
        lista.clear()
        with lista:
            for uid, nombre in datos.items():
                ui.item(f"{nombre} (ID: {uid})")

    def _expulsar(self):
        if not self._participantes:
            return
        p = self._participantes[0]
        if p["idUsuario"] == estado.usuario.id_usuario:
            ui.notify("No puedes expulsarte a ti mismo", type="warning")
            return
        estado.socket.enviar({
            "type": "KICK_USER", "roomCode": estado.codigo_sala,
            "idSala": estado.id_sala, "targetId": p["idUsuario"]
        })

    def _ser_expulsado(self, msg):
        ui.notify("Has sido expulsado de la sala.", type="info")
        self._salir()

    def _sala_cerrada(self, msg):
        ui.notify("La sala ha sido finalizada por el anfitrión.", type="info")
        self._salir()

    # --- File transfer ---
    def _enviar_archivo(self):
        ui.upload(
            label="Seleccionar archivo",
            on_upload=lambda e: self._procesar_archivo(e),
        ).classes("hidden").trigger()

    def _procesar_archivo(self, e):
        nombre = e.name
        datos = e.content.read()
        tamano = len(datos)
        b64 = base64.b64encode(datos).decode()
        self._agregar_mensaje(f"📤 Enviando: {nombre} ({tamano} bytes)...")
        threading.Thread(target=self._enviar_archivo_thread, args=(nombre, b64, tamano), daemon=True).start()

    def _enviar_archivo_thread(self, nombre, b64, tamano):
        CHUNK = 1500
        estado.socket.enviar({
            "type": "FILE_START", "roomCode": estado.codigo_sala,
            "fileName": nombre, "fileSize": tamano,
            "userName": estado.usuario.nombres
        })
        for i in range(0, len(b64), CHUNK):
            estado.socket.enviar({
                "type": "FILE_CHUNK", "roomCode": estado.codigo_sala,
                "fileName": nombre, "data": b64[i:i+CHUNK]
            })
        estado.socket.enviar({
            "type": "FILE_END", "roomCode": estado.codigo_sala, "fileName": nombre
        })
        self._agregar_mensaje(f"✅ Archivo enviado: {nombre}")

    def _on_file_start(self, msg):
        if msg.get("userName") == estado.usuario.nombres:
            return
        if not hasattr(self, "_file_recv"):
            self._file_recv = {}
        rid = msg["fileName"]
        self._file_recv[rid] = {
            "name": rid, "size": msg["fileSize"],
            "data": "", "user": msg["userName"]
        }
        self._agregar_mensaje(f"📥 Recibiendo: {rid} ({msg['fileSize']} bytes) de {msg['userName']}...")

    def _on_file_chunk(self, msg):
        nombre = msg.get("fileName")
        if nombre and hasattr(self, "_file_recv") and nombre in self._file_recv:
            self._file_recv[nombre]["data"] += msg["data"]

    def _on_file_end(self, msg):
        rid = msg["fileName"]
        info = getattr(self, "_file_recv", {}).pop(rid, None)
        if not info:
            return
        try:
            datos = base64.b64decode(info["data"])
            ruta = os.path.join(self._download_dir, rid)
            with open(ruta, "wb") as f:
                f.write(datos)
            self._agregar_mensaje(f"✅ Archivo recibido: {rid} (guardado en descargas/)")
        except Exception as e:
            self._agregar_mensaje(f"❌ Error al guardar {rid}: {e}")

    def _abrir_descargas(self):
        ruta = os.path.abspath(self._download_dir)
        import subprocess, platform
        try:
            if platform.system() == "Windows":
                os.startfile(ruta)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", ruta])
            else:
                subprocess.Popen(["xdg-open", ruta])
        except Exception as e:
            self._agregar_mensaje(f"❌ Error al abrir descargas: {e}")

    # --- Exit ---
    def _salir(self):
        if self._camara_activa:
            ui.run_javascript("stopCamera()")
        if self._mic_activa:
            ui.run_javascript("stopMic()")
        if hasattr(self, "_timer_cam"):
            self._timer_cam.deactivate()
        if hasattr(self, "_timer_audio"):
            self._timer_audio.deactivate()
        estado.socket.enviar({"type": "LEAVE_ROOM", "roomCode": estado.codigo_sala})
        self._limpiar_callbacks()
        estado.codigo_sala = ""
        estado.es_host = False
        estado.id_sala = 0
        self._on_salir()
        ui.open("/principal")


def mostrar_sala(on_salir):
    global _sala_ui
    ui.query("body").classes("m-0 p-0")
    _sala_ui = SalaUI(on_salir)
    _sala_ui.build()
