import tkinter as tk
import base64
import io
from PIL import Image, ImageTk


class PanelVideo(tk.Frame):
    def __init__(self, master, usuario_nombre="", width=240, height=180, bg="#222"):
        super().__init__(master, bg=bg, width=width, height=height)
        self.pack_propagate(False)
        self._usuario_nombre = usuario_nombre
        self._width = width
        self._height = height

        self._label_nombre = tk.Label(self, text=usuario_nombre, fg="white",
                                       bg="#333", font=("Arial", 8))
        self._label_nombre.pack(fill=tk.X)

        self._label_video = tk.Label(self, bg=bg, text="Sin video",
                                      fg="#666", font=("Arial", 9))
        self._label_video.pack(fill=tk.BOTH, expand=True)

        self._imagen_tk = None

    def actualizar_frame(self, datos_b64):
        try:
            img_data = base64.b64decode(datos_b64)
            img = Image.open(io.BytesIO(img_data))
            img = img.resize((self._width, self._height), Image.LANCZOS)
            self._imagen_tk = ImageTk.PhotoImage(img)
            self._label_video.config(image=self._imagen_tk, text="")
        except Exception as e:
            print(f"[ERROR PanelVideo] {e}")

    def mostrar_placeholder(self, texto="Sin señal"):
        self._imagen_tk = None
        self._label_video.config(image="", text=texto, fg="#666")
