import json
import os
import sys
import tkinter as tk
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Cliente.pantallas.login import LoginFrame
from Cliente.pantallas.pantalla_principal import PantallaPrincipal
from Cliente.pantallas.pantalla_sala import PantallaSala

class MainApp(tk.Tk):
    def __init__(self, host="127.0.0.1", puerto=5000):
        super().__init__()
        self._host = host
        self._puerto = puerto
        self.title("Prototipo Zoom - PC3 POO")
        self.geometry("400x350")
        self._cliente_socket = None
        self._usuario = None
        self._frame_actual = None
        self._mostrar_login()

    def _mostrar_login(self):
        if self._frame_actual:
            self._frame_actual.destroy()
        self._frame_actual = LoginFrame(self, self._on_login_exitoso, self._host, self._puerto)
        self._frame_actual.pack(fill=tk.BOTH, expand=True)

    def _mostrar_principal(self):
        if self._frame_actual:
            self._frame_actual.destroy()
        self._frame_actual = PantallaPrincipal(
            self, self._usuario, self._cliente_socket, self._cerrar_sesion, self._mostrar_sala
        )
        self._frame_actual.pack(fill=tk.BOTH, expand=True)

    def _on_login_exitoso(self, usuario, cliente_socket):
        self._usuario = usuario
        self._cliente_socket = cliente_socket
        self._mostrar_principal()

    def _mostrar_sala(self, codigo_sala, es_host, id_sala):
        if self._frame_actual:
            self._frame_actual.destroy()
        self.geometry("900x600")
        self._frame_actual = PantallaSala(
            self, self._usuario, self._cliente_socket, codigo_sala, es_host, id_sala, self._salir_sala
        )
        self._frame_actual.pack(fill=tk.BOTH, expand=True)

    def _salir_sala(self):
        self.geometry("400x350")
        self._mostrar_principal()

    def _cerrar_sesion(self):
        if self._cliente_socket:
            self._cliente_socket.desconectar()
        self._usuario = None
        self._cliente_socket = None
        self._mostrar_login()

if __name__ == "__main__":
    config = {"servidor_host": "127.0.0.1", "servidor_puerto": 5000}
    ruta_config = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(ruta_config):
        with open(ruta_config) as f:
            config.update(json.load(f))
    host = sys.argv[1] if len(sys.argv) > 1 else config["servidor_host"]
    app = MainApp(host, config["servidor_puerto"])
    app.mainloop()
