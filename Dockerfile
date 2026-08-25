FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

# Timezone exigido pela avaliação (América/Manaus)
ENV TZ=America/Manaus
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# Usuário não-root (configuração segura, item 4.2)
RUN groupadd -r robo && useradd -r -g robo -m robo

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# /app/data, /app/output e /app/logs são preenchidos via volumes (docker-compose)
RUN mkdir -p /app/data /app/output /app/logs \
    && chown -R robo:robo /app

USER robo

ENTRYPOINT ["python", "-m", "src.main"]
