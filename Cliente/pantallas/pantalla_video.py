import customtkinter as ctk
import tkinter as tk
import base64
import io
from PIL import Image

class PanelVideo(ctk.CTkFrame):
    def __init__(self, master, usuario_nombre="", width=240, height=180, bg="#111111"):
        super().__init__(
            master, 
            width=width, 
            height=height, 
            fg_color=bg, 
            corner_radius=8, 
            border_width=1, 
            border_color="#2d2d2d"
        )
        self.pack_propagate(False)
        self._usuario_nombre = usuario_nombre
        self._width = width
        self._height = height

        # Etiqueta de video que ocupa toda la superficie
        self._label_video = ctk.CTkLabel(
            self, 
            text="📷  Sin video", 
            text_color="#555555", 
            font=("Helvetica Neue", 11, "bold")
        )
        self._label_video.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Nombre superpuesto en la esquina inferior izquierda
        self._label_nombre = ctk.CTkLabel(
            self, 
            text=f"  {usuario_nombre}  ", 
            text_color="white",
            fg_color="#1c1c1e", 
            corner_radius=4,
            font=("Helvetica Neue", 9, "bold")
        )
        self._label_nombre.place(relx=0.04, rely=0.96, anchor="sw")
        self._label_nombre.lift()

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

