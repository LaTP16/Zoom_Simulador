from Servidor.protocolo import Protocolo


class FabricaMensajes:
    @staticmethod
    def obtener_handler(manejador, tipo):
        handlers = {
            Protocolo.LOGIN_REQUEST: manejador._manejar_login,
            Protocolo.CREATE_ROOM: manejador._manejar_crear_sala,
            Protocolo.JOIN_ROOM_REQUEST: manejador._manejar_unirse_sala,
            Protocolo.ADMIT_USER: manejador._manejar_admitir,
            Protocolo.REJECT_USER: manejador._manejar_rechazar,
            Protocolo.CHAT_MESSAGE: manejador._manejar_chat,
            Protocolo.GET_ROOM_PARTICIPANTS: manejador._manejar_participantes,
            Protocolo.LEAVE_ROOM: manejador._manejar_salir_sala,
            Protocolo.KICK_USER: manejador._manejar_expulsar,
        }

        if tipo in (Protocolo.FILE_START, Protocolo.FILE_CHUNK, Protocolo.FILE_END,
                    Protocolo.CAMERA_FRAME, Protocolo.VIDEO_START, Protocolo.VIDEO_STOP,
                    Protocolo.AUDIO_FRAME):
            return manejador._manejar_reenvio_sala

        return handlers.get(tipo)