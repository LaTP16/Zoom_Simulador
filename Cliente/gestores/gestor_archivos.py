import base64
import os
import platform
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox


class GestorArchivos:
    """
    Gestor de transferencia de archivos.
    Encapsula el envío (chunked en base64) y la recepción de archivos
    entre participantes de una sala.
    """

    def __init__(self, master, cliente_socket, codigo_sala, usuario,
                 download_dir, on_mensaje, on_mensaje_link):
        self._master = master
        self._cliente_socket = cliente_socket
        self._codigo_sala = codigo_sala
        self._usuario = usuario
        self._download_dir = download_dir
        self._on_mensaje = on_mensaje           # muestra texto simple en el chat
        self._on_mensaje_link = on_mensaje_link  # muestra un hipervínculo en el chat

        self._file_recv = {}  # { fileName: { name, size, data, user } }

    # ------------------------------------------------------------------
    # Interfaz pública
    # ------------------------------------------------------------------

    def enviar_archivo(self):
        """Abre el diálogo de selección y envía el archivo elegido."""
        ruta = filedialog.askopenfilename(title="Seleccionar archivo")
        if not ruta:
            return
        nombre = os.path.basename(ruta)
        tamano = os.path.getsize(ruta)
        self._on_mensaje(f"📤 Enviando: {nombre} ({tamano} bytes)...")
        threading.Thread(
            target=self._enviar_archivo_thread,
            args=(ruta, nombre, tamano),
            daemon=True
        ).start()

    def abrir_carpeta_descargas(self):
        """Abre la carpeta de descargas en el explorador del SO."""
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
            self._on_mensaje(f"❌ No se pudo abrir la carpeta de descargas: {e}")

    @staticmethod
    def abrir_archivo(ruta, on_mensaje):
        """Abre un archivo con la aplicación predeterminada del SO."""
        ruta = os.path.abspath(ruta)
        if not os.path.exists(ruta):
            on_mensaje(f"❌ El archivo no existe: {ruta}")
            return
        try:
            if platform.system() == "Windows":
                os.startfile(ruta)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", ruta])
            else:
                subprocess.Popen(["xdg-open", ruta])
        except Exception as e:
            on_mensaje(f"❌ No se pudo abrir el archivo: {e}")

    # ------------------------------------------------------------------
    # Callbacks de red (Observer)
    # ------------------------------------------------------------------

    def on_file_start(self, msg):
        """Recibe la notificación de inicio de transferencia de un archivo."""
        if msg.get("userName") == self._usuario.nombres:
            return
        rid = msg["fileName"]

        # Preguntamos al usuario si desea aceptar el archivo (hilo seguro)
        result_queue = queue.Queue()
        self._master.after(
            0,
            lambda q=result_queue: q.put(
                messagebox.askyesno(
                    "Archivo entrante",
                    f"{msg['userName']} te envía:\n"
                    f"{rid} ({msg['fileSize']} bytes)\n\n¿Descargar?"
                )
            )
        )
        if not result_queue.get():
            return

        self._file_recv[rid] = {
            "name": rid,
            "size": msg["fileSize"],
            "data": "",
            "user": msg["userName"]
        }
        self._master.after(
            0, self._on_mensaje,
            f"📥 Recibiendo: {rid} ({msg['fileSize']} bytes) de {msg['userName']}..."
        )

    def on_file_chunk(self, msg):
        """Acumula un fragmento del archivo que se está recibiendo."""
        nombre = msg.get("fileName")
        if nombre and nombre in self._file_recv:
            self._file_recv[nombre]["data"] += msg["data"]

    def on_file_end(self, msg):
        """Finaliza la recepción, decodifica y guarda el archivo en disco."""
        rid = msg["fileName"]
        info = self._file_recv.pop(rid, None)
        if not info:
            return
        try:
            datos = base64.b64decode(info["data"])
            ruta = os.path.join(self._download_dir, rid)
            with open(ruta, "wb") as f:
                f.write(datos)
            self._master.after(
                0,
                lambda: self._on_mensaje_link(
                    "✅ Archivo recibido: ", rid, " (guardado en descargas/)", ruta
                )
            )
        except Exception as e:
            self._master.after(0, self._on_mensaje, f"❌ Error al guardar {rid}: {e}")

    # ------------------------------------------------------------------
    # Lógica interna de envío
    # ------------------------------------------------------------------

    def _enviar_archivo_thread(self, ruta, nombre, tamano):
        CHUNK_SIZE = 1500
        try:
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

            self._master.after(
                0,
                lambda: self._on_mensaje_link("✅ Archivo enviado: ", nombre, "", ruta)
            )
        except Exception as e:
            self._master.after(0, self._on_mensaje, f"❌ Error al enviar {nombre}: {e}")
