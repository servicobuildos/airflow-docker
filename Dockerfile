FROM apache/airflow:2.4.3-python3.9 AS  airflow

ENV IMAGE_BUILD_VERSION 2.4.3.0

USER root

# usa o archive.debian.org (arquivo permanente do Debian) para o bullseye: o mirror "live"
# remove pacotes antigos (404 no apt install) e o snapshot.debian.org é lento/instável
# (derrubava o build com exit code 100).
# remove o repo do PostgreSQL (pgdg), que não publica mais bullseye e quebra o apt update
RUN printf '%s\n' \
        'deb http://archive.debian.org/debian bullseye main' \
        'deb http://archive.debian.org/debian bullseye-updates main' \
        'deb http://archive.debian.org/debian-security bullseye-security main' \
        > /etc/apt/sources.list && \
    rm -f /etc/apt/sources.list.d/pgdg.list && \
    apt -o Acquire::Check-Valid-Until=false \
        -o Acquire::Retries=5 \
        -o Acquire::http::Timeout=60 \
        -y update && \
    apt -o Acquire::Retries=5 install -y --no-install-recommends \
        # dependência para o ambiente de desenvolvimento
        git && \
    # clean
    apt clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -r /tmp/*

USER airflow

WORKDIR /opt

COPY --chown=airflow:root ./requirements.txt /opt
COPY --chown=airflow:root ./plugins/framework-dataflow /opt/framework-dataflow

RUN pip install --no-cache-dir --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -e /opt/framework-dataflow
