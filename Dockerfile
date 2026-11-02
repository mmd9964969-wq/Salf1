FROM node:22-bookworm-slim

ENV NODE_ENV=production \
    PORT=4173 \
    SALF1_PORT=8080 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       python3 \
       python3-pip \
       python3-venv \
       build-essential \
       libffi-dev \
       libssl-dev \
       tini \
    && rm -rf /var/lib/apt/lists/*

COPY package.json ./
RUN npm install --omit=dev

COPY . .
RUN npm run build

RUN python3 -m venv /opt/salf1-venv \
    && /opt/salf1-venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/salf1-venv/bin/pip install --no-cache-dir -r telegram-worker/requirements.txt

EXPOSE 4173 8080

ENTRYPOINT ["tini", "--", "sh", "/app/start.sh"]
