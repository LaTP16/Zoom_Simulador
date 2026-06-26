import json, os
from nicegui import ui
from Cliente.cliente_socket import ClienteSocket
from Cliente.modelos.usuario import Usuario
from web_cliente.estado import estado

def cargar_config():
    config = {"servidor_host": "127.0.0.1", "servidor_puerto": 5000}
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Cliente", "config.json")
    if os.path.exists(ruta):
        with open(ruta) as f:
            config.update(json.load(f))
    return config

def mostrar_login(on_exito, on_ir_principal):
    config = cargar_config()

    with ui.column().classes("items-center justify-center w-full h-full gap-4"):
        ui.label("Prototipo Zoom").classes("text-2xl font-bold")
        ui.label("Iniciar Sesión").classes("text-lg text-gray-500")

        correo = ui.input("Correo electrónico").props('type="email"').classes("w-80")
        clave = ui.input("Contraseña").props('type="password"').classes("w-80")
        error = ui.label("").classes("text-red-500 text-sm")

        btn = ui.button("Ingresar", on_click=lambda: None).props("flat").classes("w-80")

        async def procesar_login():
            if not correo.value or not clave.value:
                error.text = "Completa todos los campos"
                return
            btn.text = "Conectando..."
            btn.disable()
            error.text = ""
            try:
                socket = ClienteSocket(config["servidor_host"], config["servidor_puerto"])
                socket.conectar()
                respuesta = socket.enviar_y_recibir({
                    "type": "LOGIN_REQUEST",
                    "correo": correo.value,
                    "clave": clave.value
                }, response_type="LOGIN_RESPONSE")

                if respuesta.get("status") == "success":
                    usuario = Usuario(
                        respuesta["idUsuario"],
                        respuesta["nombres"],
                        correo.value,
                        respuesta["rol"]
                    )
                    estado.login(usuario, socket)
                    on_exito(usuario.nombres)
                    ui.open("/principal")
                else:
                    error.text = respuesta.get("message", "Error desconocido")
                    btn.text = "Ingresar"
                    btn.enable()
            except ConnectionError as e:
                error.text = str(e)
                btn.text = "Ingresar"
                btn.enable()

        btn.on_click(procesar_login)
        clave.on("keydown.enter", procesar_login)
        correo.on("keydown.enter", lambda: clave.focus())
