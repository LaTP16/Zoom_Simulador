import os
import sys
import socket
import threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Servidor.manejador_cliente import ManejadorCliente
from Servidor.base_datos import BaseDatos

class Servidor:
    def __init__(self, host="0.0.0.0", puerto=5000):
        self._host = host
        self._puerto = puerto
        self._socket = None
        self._activo = False
        self._clientes = []
        self._salas = {}
        self._lock = threading.Lock()

    def iniciar(self):
        bd = BaseDatos()
        bd.inicializar()

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self._host, self._puerto))
        self._socket.listen()
        self._activo = True
        print(f"[INICIANDO] Servidor activo en {self._host}:{self._puerto}")

        while self._activo:
            try:
                conexion, direccion = self._socket.accept()
                manejador = ManejadorCliente(self, conexion, direccion)
                with self._lock:
                    self._clientes.append(manejador)
                hilo = threading.Thread(target=manejador.iniciar, daemon=True)
                hilo.start()
                print(f"[HILOS ACTIVOS] {threading.active_count() - 1}")
            except OSError:
                break

    def detener(self):
        self._activo = False
        if self._socket:
            self._socket.close()

    def remover_cliente(self, cliente):
        with self._lock:
            if cliente in self._clientes:
                self._clientes.remove(cliente)

    def reenviar_a_sala(self, codigo_sala, mensaje, emisor=None):
        with self._lock:
            for cliente in self._clientes:
                if cliente._sala_actual == codigo_sala and cliente != emisor:
                    cliente._enviar(mensaje)

    def obtener_participantes_sala(self, codigo_sala):
        with self._lock:
            participantes = []
            for cliente in self._clientes:
                if cliente._sala_actual == codigo_sala and cliente._usuario_actual:
                    participantes.append({
                        "idUsuario": cliente._usuario_actual["idUsuario"],
                        "nombres": cliente._usuario_actual["nombres"]
                    })
            return participantes

    def broadcast_participantes(self, codigo_sala):
        participantes = self.obtener_participantes_sala(codigo_sala)
        mensaje = {"type": "ROOM_PARTICIPANTS", "roomCode": codigo_sala, "participants": participantes}
        with self._lock:
            for cliente in self._clientes:
                if cliente._sala_actual == codigo_sala:
                    cliente._enviar(mensaje)

    def buscar_cliente_por_usuario(self, id_usuario):
        with self._lock:
            for cliente in self._clientes:
                if cliente._usuario_actual and cliente._usuario_actual.get("idUsuario") == id_usuario:
                    return cliente
        return None

if __name__ == "__main__":
    servidor = Servidor()
    try:
        servidor.iniciar()
    except KeyboardInterrupt:
        print("\n[DETENIENDO] Servidor detenido por el usuario")
        servidor.detener()
