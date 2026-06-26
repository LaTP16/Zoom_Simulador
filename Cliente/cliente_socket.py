import socket
import json
import threading

class ClienteSocket:
    def __init__(self, host="127.0.0.1", puerto=5000):
        self._host = host
        self._puerto = puerto
        self._socket = None
        self._conectado = False
        self._callbacks = {}
        self._lock = threading.Lock()

    def conectar(self):
        if not self._conectado:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(None)
            self._socket.connect((self._host, self._puerto))
            self._conectado = True
            self._listener = threading.Thread(target=self._escuchar, daemon=True)
            self._listener.start()

    def desconectar(self):
        self._conectado = False
        if self._socket:
            try: self._socket.close()
            except: pass

    def _escuchar(self):
        buffer = ""
        while self._conectado:
            try:
                datos = self._socket.recv(4096).decode("utf-8")
                if not datos:
                    break
                buffer += datos
                while "\n" in buffer:
                    linea, buffer = buffer.split("\n", 1)
                    mensaje = json.loads(linea)
                    tipo = mensaje.get("type")
                    with self._lock:
                        cb = self._callbacks.get(tipo) or self._callbacks.get("any")
                    if cb:
                        cb(mensaje)
            except:
                break
        self._conectado = False

    def registrar_callback(self, tipo, callback):
        with self._lock:
            self._callbacks[tipo] = callback

    def remover_callback(self, tipo):
        with self._lock:
            self._callbacks.pop(tipo, None)

    def enviar(self, datos):
        try:
            if not self._conectado:
                self.conectar()
            self._socket.send((json.dumps(datos) + "\n").encode("utf-8"))
        except (socket.error, ConnectionRefusedError) as e:
            raise ConnectionError(f"No se pudo conectar al servidor: {e}")

    def enviar_y_recibir(self, datos, response_type=None):
        if not self._conectado:
            self.conectar()
        respuesta = [None]
        evento = threading.Event()

        def cb(msg):
            respuesta[0] = msg
            evento.set()

        tipo = response_type or "any"
        self.registrar_callback(tipo, cb)
        self.enviar(datos)
        evento.wait(timeout=10)
        self.remover_callback(tipo)
        if not evento.is_set():
            raise ConnectionError("Tiempo de espera agotado")
        return respuesta[0]
