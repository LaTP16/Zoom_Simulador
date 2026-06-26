import json
import threading
from Servidor.protocolo import Protocolo
from Servidor.auth_service import AuthService
from Servidor.base_datos import BaseDatos

class ManejadorCliente:
    def __init__(self, servidor, conexion, direccion):
        self._servidor = servidor
        self._conexion = conexion
        self._direccion = direccion
        self._auth_service = AuthService()
        self._usuario_actual = None
        self._sala_actual = None
        self._conectado = True

    def iniciar(self):
        print(f"[NUEVA CONEXIÓN] Cliente conectado desde {self._direccion}")
        buffer = ""
        while self._conectado:
            try:
                datos = self._conexion.recv(4096).decode("utf-8")
                if not datos:
                    break
                buffer += datos
                while "\n" in buffer:
                    linea, buffer = buffer.split("\n", 1)
                    if not linea.strip():
                        continue
                    mensaje = json.loads(linea)
                    self._procesar_mensaje(mensaje)
            except json.JSONDecodeError:
                print("[ERROR] Formato JSON inválido recibido")
            except ConnectionResetError:
                break
            except Exception as e:
                print(f"[ERROR] {e}")
                break
        print(f"[DESCONEXIÓN] Cliente {self._direccion} se ha desconectado")
        if self._sala_actual:
            codigo = self._sala_actual
            self._sala_actual = None
            self._servidor.broadcast_participantes(codigo)
        self._conexion.close()
        self._servidor.remover_cliente(self)

    def _procesar_mensaje(self, mensaje):
        tipo = mensaje.get("type")
        if tipo == Protocolo.LOGIN_REQUEST:
            self._manejar_login(mensaje)
        elif tipo == Protocolo.CREATE_ROOM:
            self._manejar_crear_sala(mensaje)
        elif tipo == Protocolo.JOIN_ROOM_REQUEST:
            self._manejar_unirse_sala(mensaje)
        elif tipo == Protocolo.ADMIT_USER:
            self._manejar_admitir(mensaje)
        elif tipo == Protocolo.REJECT_USER:
            self._manejar_rechazar(mensaje)
        elif tipo == Protocolo.CHAT_MESSAGE:
            self._manejar_chat(mensaje)
        elif tipo in (Protocolo.FILE_START, Protocolo.FILE_CHUNK, Protocolo.FILE_END):
            self._servidor.reenviar_a_sala(mensaje.get("roomCode"), mensaje, self)
        elif tipo in (Protocolo.CAMERA_FRAME, Protocolo.VIDEO_START, Protocolo.VIDEO_STOP):
            self._servidor.reenviar_a_sala(mensaje.get("roomCode"), mensaje, self)
        elif tipo == Protocolo.AUDIO_FRAME:
            self._servidor.reenviar_a_sala(mensaje.get("roomCode"), mensaje, self)
        elif tipo == Protocolo.GET_ROOM_PARTICIPANTS:
            self._servidor.broadcast_participantes(mensaje.get("roomCode"))
        elif tipo == Protocolo.LEAVE_ROOM:
            codigo = self._sala_actual
            self._sala_actual = None
            if codigo:
                self._servidor.broadcast_participantes(codigo)

    def _manejar_login(self, mensaje):
        respuesta = self._auth_service.validar_login(
            mensaje.get("correo", ""),
            mensaje.get("clave", "")
        )
        respuesta["type"] = Protocolo.LOGIN_RESPONSE
        if respuesta["status"] == "success":
            self._usuario_actual = {
                "idUsuario": respuesta["idUsuario"],
                "nombres": respuesta["nombres"],
                "rol": respuesta["rol"]
            }
        self._enviar(respuesta)

    def _manejar_crear_sala(self, mensaje):
        try:
            bd = BaseDatos()
            conexion = bd.conectar()
            cursor = conexion.cursor()
            cursor.execute(
                "INSERT INTO Salas (CodigoSala, Nombre, IdHost) VALUES (?, ?, ?)",
                (mensaje["codigo"], mensaje["nombre"], mensaje["idHost"])
            )
            id_sala = cursor.lastrowid
            cursor.execute(
                "INSERT INTO ParticipantesSala (IdSala, IdUsuario, Estado) VALUES (?, ?, 'Admitido')",
                (id_sala, mensaje["idHost"])
            )
            conexion.commit()
            self._sala_actual = mensaje["codigo"]
            self._enviar({"type": "CREATE_ROOM", "status": "success", "codigo": mensaje["codigo"], "idSala": id_sala})
        except Exception as e:
            self._enviar({"type": "CREATE_ROOM", "status": "error", "message": str(e)})

    def _manejar_unirse_sala(self, mensaje):
        try:
            bd = BaseDatos()
            conexion = bd.conectar()
            cursor = conexion.cursor()
            cursor.execute(
                "SELECT IdSala, IdHost FROM Salas WHERE CodigoSala = ? AND Estado = 'Activa'",
                (mensaje["codigo"],)
            )
            sala = cursor.fetchone()
            if not sala:
                self._enviar({"type": "JOIN_ROOM_REQUEST", "status": "error",
                              "message": "Sala no encontrada o inactiva."})
                return
            if sala["IdHost"] == mensaje["idUsuario"]:
                cursor.execute(
                    "INSERT INTO ParticipantesSala (IdSala, IdUsuario, Estado) VALUES (?, ?, 'Admitido')",
                    (sala["IdSala"], mensaje["idUsuario"])
                )
                conexion.commit()
                self._sala_actual = mensaje["codigo"]
                self._enviar({"type": "JOIN_ROOM_REQUEST", "status": "success",
                              "idSala": sala["IdSala"], "admitido": True})
            else:
                cursor.execute(
                    "SELECT Nombres FROM Usuarios WHERE IdUsuario = ?",
                    (mensaje["idUsuario"],)
                )
                nombre_solicitante = cursor.fetchone()["Nombres"]
                cursor.execute(
                    "INSERT INTO SolicitudesSala (IdSala, IdUsuario) VALUES (?, ?)",
                    (sala["IdSala"], mensaje["idUsuario"])
                )
                conexion.commit()
                self._enviar({"type": "JOIN_ROOM_REQUEST", "status": "success",
                              "idSala": sala["IdSala"], "admitido": False})
                host = self._servidor.buscar_cliente_por_usuario(sala["IdHost"])
                if host:
                    host._enviar({
                        "type": "WAITING_ROOM_UPDATE",
                        "idSala": sala["IdSala"],
                        "solicitanteId": mensaje["idUsuario"],
                        "solicitanteNombre": nombre_solicitante
                    })
        except Exception as e:
            self._enviar({"type": "JOIN_ROOM_REQUEST", "status": "error", "message": str(e)})

    def _manejar_admitir(self, mensaje):
        try:
            bd = BaseDatos()
            conexion = bd.conectar()
            cursor = conexion.cursor()
            cursor.execute(
                "DELETE FROM SolicitudesSala WHERE IdSala = ? AND IdUsuario = ?",
                (mensaje["idSala"], mensaje["idUsuario"])
            )
            cursor.execute(
                "INSERT INTO ParticipantesSala (IdSala, IdUsuario, Estado) VALUES (?, ?, 'Admitido')",
                (mensaje["idSala"], mensaje["idUsuario"])
            )
            cursor.execute("SELECT CodigoSala FROM Salas WHERE IdSala = ?", (mensaje["idSala"],))
            codigo = cursor.fetchone()["CodigoSala"]
            conexion.commit()
            invitado = self._servidor.buscar_cliente_por_usuario(mensaje["idUsuario"])
            if invitado:
                invitado._sala_actual = codigo
                invitado._enviar({
                    "type": "ADMIT_USER",
                    "status": "admitido",
                    "idSala": mensaje["idSala"],
                    "codigo": codigo
                })
            self._servidor.broadcast_participantes(codigo)
        except Exception as e:
            print(f"[ERROR] Admitir usuario: {e}")

    def _manejar_rechazar(self, mensaje):
        try:
            bd = BaseDatos()
            conexion = bd.conectar()
            cursor = conexion.cursor()
            cursor.execute(
                "DELETE FROM SolicitudesSala WHERE IdSala = ? AND IdUsuario = ?",
                (mensaje["idSala"], mensaje["idUsuario"])
            )
            conexion.commit()
            invitado = self._servidor.buscar_cliente_por_usuario(mensaje["idUsuario"])
            if invitado:
                invitado._enviar({
                    "type": "REJECT_USER",
                    "status": "rechazado",
                    "idSala": mensaje["idSala"]
                })
        except Exception as e:
            print(f"[ERROR] Rechazar usuario: {e}")

    def _manejar_chat(self, mensaje):
        print(f"[CHAT] {mensaje.get('userName')}: {mensaje.get('message')}")
        self._servidor.reenviar_a_sala(mensaje.get("roomCode"), mensaje, self)

    def _enviar(self, datos):
        try:
            if "__rid" in datos:
                datos.pop("__rid")
            if "_rid" in datos:
                datos["_rid"] = datos.pop("_rid")
            self._conexion.send((json.dumps(datos) + "\n").encode("utf-8"))
        except Exception as e:
            print(f"[ERROR] No se pudo enviar mensaje: {e}")
            self._conectado = False
