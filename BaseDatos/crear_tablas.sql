-- ============================================================================
-- ADVERTENCIA DE SEGURIDAD:
-- 1. Nunca almacene contraseñas en texto plano. Hacerlo comprometería la totalidad
--    de las cuentas en caso de que la base de datos sea robada o leída.
-- 2. Este prototipo utiliza SHA-256 para el campo 'PasswordHash'. En un entorno
--    de producción real, se debe utilizar un algoritmo de derivación de claves
--    robusto (como bcrypt, Argon2 o PBKDF2) e incorporar un valor de sal (salt)
--    único por usuario para mitigar ataques de diccionario y tablas de arcoiris.
-- 3. La transmisión de credenciales debe protegerse mediante TLS/SSL (HTTPS).
-- ============================================================================

CREATE TABLE IF NOT EXISTS Usuarios (
    IdUsuario INTEGER PRIMARY KEY AUTOINCREMENT,
    Nombres TEXT NOT NULL,
    Correo TEXT NOT NULL UNIQUE,
    PasswordHash TEXT NOT NULL,
    Rol TEXT NOT NULL DEFAULT 'Usuario',
    Activo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS Salas (
    IdSala INTEGER PRIMARY KEY AUTOINCREMENT,
    CodigoSala TEXT NOT NULL UNIQUE,
    Nombre TEXT NOT NULL,
    IdHost INTEGER NOT NULL,
    Estado TEXT NOT NULL DEFAULT 'Activa',
    FechaCreacion TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (IdHost) REFERENCES Usuarios(IdUsuario)
);

CREATE TABLE IF NOT EXISTS ParticipantesSala (
    IdParticipante INTEGER PRIMARY KEY AUTOINCREMENT,
    IdSala INTEGER NOT NULL,
    IdUsuario INTEGER NOT NULL,
    Estado TEXT NOT NULL,
    FechaIngreso TEXT,
    FOREIGN KEY (IdSala) REFERENCES Salas(IdSala),
    FOREIGN KEY (IdUsuario) REFERENCES Usuarios(IdUsuario)
);

CREATE TABLE IF NOT EXISTS SolicitudesSala (
    IdSolicitud INTEGER PRIMARY KEY AUTOINCREMENT,
    IdSala INTEGER NOT NULL,
    IdUsuario INTEGER NOT NULL,
    Estado TEXT NOT NULL DEFAULT 'Pendiente',
    FechaSolicitud TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (IdSala) REFERENCES Salas(IdSala),
    FOREIGN KEY (IdUsuario) REFERENCES Usuarios(IdUsuario)
);

CREATE TABLE IF NOT EXISTS Mensajes (
    IdMensaje INTEGER PRIMARY KEY AUTOINCREMENT,
    IdSala INTEGER NOT NULL,
    IdUsuario INTEGER NOT NULL,
    Contenido TEXT NOT NULL,
    FechaEnvio TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (IdSala) REFERENCES Salas(IdSala),
    FOREIGN KEY (IdUsuario) REFERENCES Usuarios(IdUsuario)
);

CREATE TABLE IF NOT EXISTS ArchivosCompartidos (
    IdArchivo INTEGER PRIMARY KEY AUTOINCREMENT,
    IdSala INTEGER NOT NULL,
    IdUsuario INTEGER NOT NULL,
    NombreArchivo TEXT NOT NULL,
    RutaArchivo TEXT NOT NULL,
    Tamano INTEGER NOT NULL,
    FechaSubida TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (IdSala) REFERENCES Salas(IdSala),
    FOREIGN KEY (IdUsuario) REFERENCES Usuarios(IdUsuario)
);
