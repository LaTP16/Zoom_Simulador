import random, string
from nicegui import ui
from web_cliente.estado import estado

def mostrar_principal(on_entrar_sala):
    if not estado.conectado:
        ui.open("/")
        return

    with ui.column().classes("items-center justify-center w-full h-full gap-4"):
        ui.label(f"Bienvenido, {estado.usuario.nombres}").classes("text-2xl font-bold")
        ui.label(f"Rol: {estado.usuario.rol}").classes("text-gray-500")

        codigo_dialog = ui.dialog()
        with codigo_dialog, ui.card().classes("gap-4 p-4"):
            ui.label("Código de la sala:").classes("font-bold")
            codigo_input = ui.input("Ej: ABC123").classes("w-60")
            error_label = ui.label("").classes("text-red-500 text-sm")

            async def unirse():
                codigo = codigo_input.value.strip()
                if not codigo:
                    error_label.text = "Ingresa un código"
                    return
                respuesta = estado.socket.enviar_y_recibir({
                    "type": "JOIN_ROOM_REQUEST",
                    "codigo": codigo,
                    "idUsuario": estado.usuario.id_usuario
                }, response_type="JOIN_ROOM_REQUEST")
                if respuesta.get("status") == "success":
                    if respuesta.get("admitido"):
                        on_entrar_sala(codigo, False, respuesta["idSala"])
                        ui.open("/sala")
                    else:
                        ui.notify("Espera a que el host te admita.", type="info")
                    codigo_dialog.close()
                else:
                    error_label.text = respuesta.get("message", "Error al unirse")

            ui.button("Unirse", on_click=unirse).classes("w-full")
            ui.button("Cancelar", on_click=codigo_dialog.close).props("flat")

        def crear_sala():
            codigo = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            respuesta = estado.socket.enviar_y_recibir({
                "type": "CREATE_ROOM",
                "nombre": f"Sala de {estado.usuario.nombres}",
                "codigo": codigo,
                "idHost": estado.usuario.id_usuario
            }, response_type="CREATE_ROOM")
            if respuesta.get("status") == "success":
                on_entrar_sala(codigo, True, respuesta["idSala"])
                ui.open("/sala")
            else:
                ui.notify(respuesta.get("message", "Error al crear sala"), type="negative")

        ui.button("Crear Sala", on_click=crear_sala).classes("w-80 bg-blue-500 text-white")
        ui.button("Unirse a Sala", on_click=codigo_dialog.open).classes("w-80 bg-orange-500 text-white")

        def cerrar_sesion():
            estado.socket.remover_callback("ADMIT_USER")
            estado.logout()
            ui.open("/")

        ui.button("Cerrar Sesión", on_click=cerrar_sesion).classes("w-80 bg-red-500 text-white")

    def admitido_en_sala(msg):
        estado.codigo_sala = msg["codigo"]
        estado.id_sala = msg["idSala"]
        estado.es_host = False
        ui.open("/sala")

    estado.socket.registrar_callback("ADMIT_USER", admitido_en_sala)
