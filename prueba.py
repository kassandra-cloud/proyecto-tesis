import smtplib
from email.mime.text import MIMEText
import ssl

# --- REEMPLAZA ESTOS VALORES CON TU INFORMACIÓN ---
HOST = "smtp.gmail.com"
PORT = 465
USERNAME = "kassramosveg@gmail.com" # Tu correo de Gmail
PASSWORD = "sszesapgnhjtseuh"     # ¡Tu Contraseña de Aplicación de 16 caracteres!
TO_EMAIL = "kassramosveg@gmail.com"
FROM_EMAIL = USERNAME

try:
    # Crea un contexto SSL/TLS para el cifrado
    context = ssl.create_default_context()

    # Inicia la conexión SSL implícita
    server = smtplib.SMTP_SSL(HOST, PORT, context=context) 

    # Intenta la autenticación
    server.login(USERNAME, PASSWORD)

    # Prepara y envía un mensaje de prueba
    msg = MIMEText('Prueba de conexión SMTP_SSL exitosa desde script Python.')
    msg['Subject'] = 'Prueba SMTP Exitosa'
    server.sendmail(FROM_EMAIL, TO_EMAIL, msg.as_string())

    server.quit()
    print(" Correo enviado exitosamente con script puro de Python.")
except Exception as e:
    print(f" Fallo al enviar correo o conectar: {e}")