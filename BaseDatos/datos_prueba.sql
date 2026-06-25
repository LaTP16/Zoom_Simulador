INSERT OR IGNORE INTO Usuarios (Nombres, Correo, PasswordHash, Rol)
VALUES
    ('Luis Tasayco', 'luis@email.com',  '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'Host'),
    ('Ana Torres',   'ana@email.com',   '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'Usuario'),
    ('Carlos Ruiz',  'carlos@email.com','8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'Usuario');
-- PasswordHash = SHA256 de "123456"
