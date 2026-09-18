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
COPY data/ ./data/
COPY config/ ./config/
COPY .streamlit/ ./.streamlit/

# /app/output e /app/logs são preenchidos via volumes (mas garantimos que existam)
RUN mkdir -p /app/output /app/logs \
    && chown -R robo:robo /app

USER robo

ENTRYPOINT ["python", "-m", "src.main"]
