# ---- Etapa base ----
FROM python:3.11-slim

# Establecer el directorio de trabajo en el contenedor
WORKDIR /app

# Copiar el archivo de dependencias primero (para aprovechar la cache de Docker)
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del proyecto al contenedor
COPY . .

# Exponer el puerto donde corre Flask (por defecto 5000)
EXPOSE 5000

# Establecer variables de entorno (puedes modificarlas según tu app)
ENV FLASK_APP=app/main.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_ENV=production

# Comando para ejecutar la app
CMD ["flask", "run"]

