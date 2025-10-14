# ---- Etapa base ----
FROM python:3.13-alpine

# Establecer el directorio de trabajo en el contenedor
WORKDIR /app

# Copiar el archivo de dependencias primero (para aprovechar la cache de Docker)
COPY requirements.txt .

# Instalar herramientas de compilación
RUN apk add --no-cache build-base gcc musl-dev libffi-dev

# Instalar setuptools primero (requerido para compilar paquetes desde fuente)
RUN pip install --no-cache-dir setuptools wheel

# Instalar dependencias
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt

# Copiar el resto del proyecto al contenedor
COPY . .

# Exponer el puerto donde corre Flask
EXPOSE 5050

# Comando para ejecutar la app
CMD ["python", "main.py"]