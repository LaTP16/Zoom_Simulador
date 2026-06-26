import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Cliente"))

from Cliente.cliente_socket import ClienteSocket
from Cliente.modelos.usuario import Usuario

class Estado:
    def __init__(self):
        self.socket: ClienteSocket | None = None
        self.usuario: Usuario | None = None
        self.codigo_sala: str = ""
        self.es_host: bool = False
        self.id_sala: int = 0
        self.conectado: bool = False

    def login(self, usuario, socket):
        self.usuario = usuario
        self.socket = socket
        self.conectado = True

    def logout(self):
        if self.socket:
            self.socket.desconectar()
        self.socket = None
        self.usuario = None
        self.codigo_sala = ""
        self.es_host = False
        self.id_sala = 0
        self.conectado = False

estado = Estado()
