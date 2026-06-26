# Exposición — Zoom Simulador (10 min, 3 personas)

---

## Persona 1 — Arquitectura y Comunicación (3 min)

**Tema:** Cómo está organizado el proyecto y cómo se comunican cliente y servidor.

**Texto:**

"El proyecto simula un Zoom usando TCP sockets. Hay dos partes: un **servidor** que administra salas y reenvía mensajes, y un **cliente** con interfaz gráfica en Tkinter.

La comunicación es por **TCP**, con mensajes en **formato JSON** separados por saltos de línea. El servidor escucha en el puerto 5000 y por cada cliente que se conecta, crea un hilo dedicado (`ManejadorCliente`).

El archivo `protocolo.py` define todos los tipos de mensaje: `LOGIN_REQUEST`, `CHAT_MESSAGE`, `CAMERA_FRAME`, etc. El servidor es solo un **relay**: cuando un cliente en una sala envía un mensaje, el servidor lo reenvía a todos los demás en esa sala.

Del lado del cliente, `ClienteSocket` maneja la conexión. Tiene un hilo listener que recibe mensajes y los distribuye usando un **sistema de callbacks**: cada tipo de mensaje se registra con una función que se ejecuta cuando llega.

Usa dos modos: `enviar()` para mensajes sin respuesta (chat, video, audio) y `enviar_y_recibir()` para operaciones que esperan respuesta (login, crear sala), con un timeout de 10 segundos."

---

## Persona 2 — Flujo de Usuario y Salas (3:30 min)

**Tema:** Cómo un usuario inicia sesión, crea/entra a una sala, y chatea.

**Texto:**

"Al iniciar el cliente aparece la pantalla de **login**. El usuario ingresa correo y contraseña. El cliente envía un `LOGIN_REQUEST` al servidor, que consulta la base de datos SQLite, valida con SHA-256, y responde con los datos del usuario. Hay 3 usuarios de prueba: Luis (Host), Ana y Carlos, todos con contraseña `123456`.

Una vez dentro, `PantallaPrincipal` ofrece crear o unirse a una sala.

- **Crear sala:** genera un código aleatorio de 6 caracteres y envía `CREATE_ROOM`. El servidor inserta la sala en la BD y respeta con el ID. El creador entra como host.
- **Unirse a sala:** el usuario ingresa un código. Si es el host de esa sala, entra directo. Si no, queda en **sala de espera** y el host decide si admitirlo o rechazarlo.

Cuando el host admite a alguien, el servidor notifica al invitado y ambos entran a `PantallaSala`. Esta pantalla coordina todo: chat, video, audio y archivos.

El **chat** es simple: un mensaje se envía al servidor, que lo reenvía a todos en la sala menos al emisor. Cada mensaje aparece en un `ScrolledText` con el nombre del usuario."

---

## Persona 3 — Video, Audio y Archivos (3:30 min)

**Tema:** Cómo se manejan la cámara, el micrófono y la transferencia de archivos.

**Texto:**

"Las funcionalidades multimedia están organizadas en **gestores**, cada uno en su propio archivo dentro de `Cliente/gestores/`.

**GestorVideo:** Al presionar 'Iniciar Cámara', detecta el backend disponible (OpenCV en Windows, FFmpeg en Linux). Captura frames de 320x240, los comprime como JPEG con calidad 50, los codifica en base64 y los envía como `CAMERA_FRAME` cada 100 ms. Cuando otro usuario enciende su cámara, aparece un `PanelVideo` nuevo. Los frames recibidos se decodifican y muestran con PIL.

**GestorAudio:** Usa la librería `sounddevice`. Captura audio a 16 kHz, mono, 16 bits, en bloques de 1024 muestras, los codifica en base64 y los envía como `AUDIO_FRAME`. La reproducción corre en un hilo separado con una cola (`queue.Queue`) para no bloquear la interfaz.

**GestorArchivos:** Para enviar un archivo, abre un diálogo de selección, lo codifica completo en base64, lo parte en fragmentos de 1500 bytes y envía `FILE_START`, múltiples `FILE_CHUNK` y `FILE_END`. El receptor acumula los fragmentos, los decodifica y guarda el archivo. Aparece un link en el chat para abrirlo.

Los gestores usan **hilos daemon** para que se cierren automáticamente al cerrar la ventana. El servidor nunca interpreta estos datos, solo los reenvía."
