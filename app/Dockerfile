#  Imagen base estable con soporte completo para OpenCV
FROM python:3.12-slim

#  Establecer directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias del sistema necesarias para OpenCV
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copiar archivo de dependencias
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente del proyecto
COPY . .

# Exponer el puerto (ajústalo según tu app)
EXPOSE 5050

#  Comando por defecto para ejecutar la aplicación
CMD ["python", "main.py"]
