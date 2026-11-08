# backend/worker/Dockerfile
# Usamos una imagen base oficial de Python ligera
FROM python:3.11-slim

# Configuramos variables de entorno para evitar crear .pyc y forzar stdout sin buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Directorio de trabajo seguro para los repositorios
    REPOS_DIR=/tmp/scans

# Instalamos Git (requerido por Módulo E) y dependencias de sistema limpiando el caché
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Creamos un usuario no privilegiado (qubitor) y el grupo
RUN groupadd -r qubitor_group && useradd -r -g qubitor_group qubitor

# Solo el directorio de los clones es del usuario no root: el código de la app
# queda de root, así un repo malicioso no puede modificarlo
RUN mkdir -p /app ${REPOS_DIR} \
    && chown -R qubitor:qubitor_group ${REPOS_DIR}

# Cambiamos al directorio de trabajo de la app
WORKDIR /app

# Copiamos el archivo de dependencias e instalamos (como root, pero quedan disponibles globalmente)
# Nota: requirements.txt se agregará en la PR de la API
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código del backend
COPY . /app/

# Cambiamos al usuario no privilegiado
USER qubitor

# Ejecutamos con sh -c para que evalúe la variable de entorno $REDIS_URL.
# La API encola los trabajos en JSON, así que el worker los lee en ese formato.
CMD ["sh", "-c", "exec rq worker scans --url \"$REDIS_URL\" --serializer rq.serializers.JSONSerializer"]