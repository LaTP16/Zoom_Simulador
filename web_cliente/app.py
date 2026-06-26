import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Cliente"))

from nicegui import ui, app
from web_cliente.paginas.login import mostrar_login
from web_cliente.paginas.principal import mostrar_principal
from web_cliente.paginas.sala import mostrar_sala
from web_cliente.estado import estado

@ui.page("/")
def login_page():
    ui.query("body").classes("m-0 p-0")
    ui.add_head_html("""<style>
    body { margin: 0; padding: 0; }
    .q-page { padding: 0; }
    </style>""")
    mostrar_login(
        on_exito=lambda nombre: ui.notify(f"Bienvenido, {nombre}", type="positive"),
        on_ir_principal=lambda: None,
    )

@ui.page("/principal")
def principal_page():
    if not estado.conectado:
        ui.open("/")
        return
    ui.query("body").classes("m-0 p-0")
    def on_entrar_sala(codigo, es_host, id_sala):
        estado.codigo_sala = codigo
        estado.es_host = es_host
        estado.id_sala = id_sala
    mostrar_principal(on_entrar_sala)

@ui.page("/sala")
def sala_page():
    if not estado.conectado or not estado.codigo_sala:
        ui.open("/")
        return
    ui.query("body").classes("m-0 p-0")
    def on_salir():
        pass
    mostrar_sala(on_salir)

def main():
    ui.run(
        title="Prototipo Zoom - Web",
        host="0.0.0.0",
        port=8080,
        storage_secret="zoom_prototipo_secret",
        dark=True,
        favicon="🎥",
    )

if __name__ == "__main__":
    main()
