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

## Limitaciones del Prototipo y Seguridad

### Advertencia de Seguridad (Almacenamiento de Contraseñas)
El prototipo **no** almacena contraseñas en texto plano (usa SHA-256), pero se advierten los siguientes riesgos de seguridad críticos para un entorno de producción:
* **Riesgo de almacenamiento en texto plano:** Almacenar contraseñas en texto plano expone todas las cuentas si la base de datos o el disco del servidor se ven comprometidos.
* **Falta de Salt:** Al no salar el hash de las contraseñas, los atacantes pueden averiguar fácilmente contraseñas simples mediante tablas de arcoiris (rainbow tables) o fuerza bruta.
* **Sin cifrado de red (TLS/SSL):** Todos los datos (incluyendo credenciales en el login, chats, video y audio) viajan en texto plano sobre TCP, siendo totalmente vulnerables a ataques de tipo Man-in-the-Middle (MitM).

### Limitaciones del Prototipo
1. **TCP para Streaming:** Se utiliza TCP para enviar frames de cámara y audio. En videoconferencias reales se usa UDP para priorizar la baja latencia sobre la retransmisión de paquetes.
2. **Persistencia de Chat y Archivos:** Aunque existen las tablas en la base de datos, los mensajes y el registro de archivos compartidos no se guardan persistentemente en el servidor.
3. **Escalabilidad:** SQLite no está diseñado para alta concurrencia de escrituras simultáneas en entornos masivos de producción.
4. **Renderizado de Video:** Tkinter no está optimizado para reproducir flujos de video de alta definición a tasas de refresco elevadas en la CPU.

