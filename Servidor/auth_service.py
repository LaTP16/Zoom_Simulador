from Servidor.base_datos import BaseDatos

class AuthService:
    def __init__(self):
        self._bd = BaseDatos()

    def validar_login(self, correo, clave):
        try:
            conexion = self._bd.conectar()
            cursor = conexion.cursor()
            password_hash = BaseDatos.hash_clave(clave)
            cursor.execute(
                "SELECT IdUsuario, Nombres, Rol FROM Usuarios WHERE Correo = ? AND PasswordHash = ? AND Activo = 1",
                (correo, password_hash)
            )
            resultado = cursor.fetchone()
            if resultado:
                return {
                    "status": "success",
                    "idUsuario": resultado["IdUsuario"],
                    "nombres": resultado["Nombres"],
                    "rol": resultado["Rol"]
                }
            return {"status": "error", "message": "Credenciales incorrectas o usuario no existe."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
