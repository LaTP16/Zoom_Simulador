# Prototipo Zoom - PC3 POO

Prototipo académico de videoconferencia tipo Zoom usando sockets,
base de datos, login, sala de espera, chat, documentos y cámaras.

## Integrantes

- 

## Tecnologías

- **Cliente:** Python + Tkinter
- **Servidor:** Python + Sockets TCP + threading
- **Base de datos:** SQLite

## Estructura del proyecto

```
Cliente/       # Aplicación cliente (Tkinter)
Servidor/      # Servidor de sockets
BaseDatos/     # Scripts SQL
Documentacion/ # Informe, diagramas, capturas
```

## Instalación y ejecución

1. Instalar Python 3.10+
2. Ejecutar el servidor:
   ```
   python -m Servidor.servidor
   ```
3. Ejecutar el cliente (una o más instancias):
   ```
   python -m Cliente.main
   ```
