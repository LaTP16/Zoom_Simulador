from datetime import datetime

class Mensaje:
    def __init__(self, id_usuario, nombre_usuario, contenido, sala_codigo, fecha=None):
        self._id_usuario = id_usuario
        self._nombre_usuario = nombre_usuario
        self._contenido = contenido
        self._sala_codigo = sala_codigo
        self._fecha = fecha or datetime.now().isoformat()

    @property
    def id_usuario(self):
        return self._id_usuario

    @property
    def nombre_usuario(self):
        return self._nombre_usuario

    @property
    def contenido(self):
        return self._contenido

    @property
    def sala_codigo(self):
        return self._sala_codigo

    @property
    def fecha(self):
        return self._fecha

    def a_dict(self):
        return {
            "type": "CHAT_MESSAGE",
            "roomCode": self._sala_codigo,
            "userId": self._id_usuario,
            "userName": self._nombre_usuario,
            "message": self._contenido,
            "sentAt": self._fecha
        }
