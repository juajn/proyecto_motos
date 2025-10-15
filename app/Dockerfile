# ---- Etapa base ----
FROM python:3.13-alpine

# Establecer el directorio de trabajo en el contenedor
WORKDIR /app

# Copiar el archivo de dependencias primero (para aprovechar la cache de Docker)
COPY requirements.txt .

RUN apk add --no-cache build-base gcc musl-dev libffi-dev
# Instalar dependencias
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt

# Copiar el resto del proyecto al contenedor
COPY . .

# Exponer el puerto donde corre Flask (por defecto 5000)
EXPOSE 5050


# Comando para ejecutar la app
CMD ["python", "main.py"]