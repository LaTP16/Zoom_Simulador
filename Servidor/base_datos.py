import sqlite3
import hashlib
import os

class BaseDatos:
    _instancia = None

    def __new__(cls, *args, **kwargs):
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
        return cls._instancia

    def __init__(self, ruta="server.db"):
        if not hasattr(self, "_inicializada"):
            self._ruta = ruta
            self._conexion = None
            self._inicializada = True

    def conectar(self):
        if self._conexion is None:
            self._conexion = sqlite3.connect(self._ruta, check_same_thread=False)
            self._conexion.row_factory = sqlite3.Row
        else:
            try:
                self._conexion.cursor().execute("SELECT 1")
            except sqlite3.ProgrammingError:
                self._conexion = sqlite3.connect(self._ruta, check_same_thread=False)
                self._conexion.row_factory = sqlite3.Row
        return self._conexion

    def desconectar(self):
        if self._conexion:
            self._conexion.close()
            self._conexion = None

    def inicializar(self):
        conexion = self.conectar()
        cursor = conexion.cursor()
        ruta_sql_tablas = os.path.join(os.path.dirname(__file__), "..", "BaseDatos", "crear_tablas.sql")
        with open(ruta_sql_tablas, "r", encoding="utf-8") as f:
            cursor.executescript(f.read())
        cursor.execute("SELECT COUNT(*) FROM Usuarios")
        if cursor.fetchone()[0] == 0:
            ruta_sql = os.path.join(os.path.dirname(__file__), "..", "BaseDatos", "datos_prueba.sql")
            with open(ruta_sql, "r", encoding="utf-8") as f:
                cursor.executescript(f.read())
            print("[BD] Datos de prueba insertados.")
        conexion.commit()

    @staticmethod
    def hash_clave(clave):
        return hashlib.sha256(clave.encode()).hexdigest()
