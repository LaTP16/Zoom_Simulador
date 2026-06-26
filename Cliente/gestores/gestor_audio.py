import base64
import queue
import threading
import sounddevice as sd


class GestorAudio:
    """
    Gestor de audio (micrófono y reproducción).
    Encapsula la captura desde el micrófono, el envío de frames de audio
    al servidor y la reproducción del audio recibido de otros participantes.
    """

    def __init__(self, master, cliente_socket, codigo_sala, usuario, btn_mic, on_mensaje):
        self._master = master
        self._cliente_socket = cliente_socket
        self._codigo_sala = codigo_sala
        self._usuario = usuario
        self._btn_mic = btn_mic
        self._on_mensaje = on_mensaje  # callback para mostrar mensajes en el chat

        self._mic_activo = False
        self._capturando_mic = False
        self._audio_activo = True
        self._audio_queue = queue.Queue()

        # El hilo de reproducción arranca inmediatamente en segundo plano
        threading.Thread(target=self._audio_playback_loop, daemon=True).start()

    # ------------------------------------------------------------------
    # Interfaz pública
    # ------------------------------------------------------------------

    @property
    def mic_activo(self):
        return self._mic_activo

    def toggle_mic(self):
        """Alterna el estado del micrófono (encender/silenciar)."""
        if self._mic_activo:
            self._capturando_mic = False
            self._mic_activo = False
            self._btn_mic.configure(text="🎤 Iniciar Micrófono", fg_color="#4CAF50")
        else:
            try:
                devices = sd.query_devices()
                tiene_mic = any(d['max_input_channels'] > 0 for d in devices)
            except Exception:
                tiene_mic = False

            if not tiene_mic:
                self._on_mensaje("❌ No se detectó ningún micrófono en el sistema.")
                return

            self._mic_activo = True
            self._capturando_mic = True
            self._btn_mic.configure(text="🎤 Silenciar Micrófono", fg_color="#f44336")
            threading.Thread(target=self._capturar_y_enviar_audio, daemon=True).start()

    def detener(self):
        """Detiene la captura y la reproducción de audio."""
        self._capturando_mic = False
        self._mic_activo = False
        self._audio_activo = False

    # ------------------------------------------------------------------
    # Callback de red (Observer)
    # ------------------------------------------------------------------

    def on_audio_frame(self, msg):
        """Recibe un frame de audio en base64 de otro participante."""
        if msg.get("userName") == self._usuario.nombres:
            return
        datos_b64 = msg.get("data", "")
        if datos_b64:
            try:
                datos = base64.b64decode(datos_b64)
                self._audio_queue.put(datos)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Lógica interna
    # ------------------------------------------------------------------

    def _capturar_y_enviar_audio(self):
        samplerate = 16000
        channels = 1
        blocksize = 1024
        dtype = 'int16'
        try:
            with sd.RawInputStream(
                samplerate=samplerate, channels=channels,
                dtype=dtype, blocksize=blocksize
            ) as stream:
                while self._capturando_mic and self._cliente_socket._conectado:
                    data, _ = stream.read(blocksize)
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
            self._master.after(0, self._on_mensaje, f"❌ Error en el micrófono: {e}")
            self._master.after(
                0,
                lambda: self._btn_mic.configure(text="🎤 Iniciar Micrófono", fg_color="#4CAF50")
            )
            self._mic_activo = False
            self._capturando_mic = False

    def _audio_playback_loop(self):
        """Hilo daemon que reproduce el audio recibido de otros participantes."""
        samplerate = 16000
        channels = 1
        blocksize = 1024
        dtype = 'int16'
        try:
            try:
                devices = sd.query_devices()
                tiene_salida = any(d['max_output_channels'] > 0 for d in devices)
            except Exception:
                tiene_salida = False

            if not tiene_salida:
                return

            with sd.RawOutputStream(
                samplerate=samplerate, channels=channels,
                dtype=dtype, blocksize=blocksize
            ) as stream:
                while self._audio_activo:
                    try:
                        data = self._audio_queue.get(timeout=0.5)
                        stream.write(data)
                    except queue.Empty:
                        continue
        except Exception as e:
            print(f"Error en reproducción de audio: {e}")
