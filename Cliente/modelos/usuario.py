class Usuario:
    def __init__(self, id_usuario, nombres, correo, rol):
        self._id_usuario = id_usuario
        self._nombres = nombres
        self._correo = correo
        self._rol = rol

    @property
    def id_usuario(self):
        return self._id_usuario

    @property
    def nombres(self):
        return self._nombres

    @property
    def correo(self):
        return self._correo

    @property
    def rol(self):
        return self._rol

    def es_host(self):
        return self._rol.lower() == "host"

    def __str__(self):
        return f"{self._nombres} ({self._rol})"
