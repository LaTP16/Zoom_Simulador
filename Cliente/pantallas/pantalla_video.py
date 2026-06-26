import customtkinter as ctk
import tkinter as tk
import base64
import io
from PIL import Image

class PanelVideo(ctk.CTkFrame):
    def __init__(self, master, usuario_nombre="", width=240, height=180, bg="#222"):
        super().__init__(master, width=width, height=height, fg_color=bg)
        self.pack_propagate(False)
        self._usuario_nombre = usuario_nombre
        self._width = width
        self._height = height

        self._label_nombre = ctk.CTkLabel(
            self, text=usuario_nombre, text_color="white",
            fg_color="#333", font=("Arial", 8, "bold")
        )
        self._label_nombre.pack(fill=tk.X)

        self._label_video = ctk.CTkLabel(
            self, text="Sin video", text_color="#666", font=("Arial", 9)
        )
        self._label_video.pack(fill=tk.BOTH, expand=True)

        self._imagen_ctk = None

    def actualizar_frame(self, datos_b64):
        try:
            img_data = base64.b64decode(datos_b64)
            img = Image.open(io.BytesIO(img_data))
            self._imagen_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(self._width, self._height))
            self._label_video.configure(image=self._imagen_ctk, text="")
        except Exception as e:
            print(f"[ERROR PanelVideo] {e}")

    def mostrar_placeholder(self, texto="Sin señal"):
        self._imagen_ctk = None
        self._label_video.configure(image=None, text=texto)

