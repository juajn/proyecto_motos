# ---- Etapa base ----
FROM python:3.13-alpine

# Establecer el directorio de trabajo en el contenedor
WORKDIR /app

# Copiar el archivo de dependencias primero (para aprovechar la cache de Docker)
COPY requirements.txt .

# Instalar dependencias
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt

# Copiar el resto del proyecto al contenedor
COPY . .

# Exponer el puerto donde corre Flask (por defecto 5000)
EXPOSE 5000


# Comando para ejecutar la app
CMD ["python", "app/main.py"]

