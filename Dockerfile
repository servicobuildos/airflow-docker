FROM apache/airflow:2.4.3-python3.9 AS  airflow

ENV IMAGE_BUILD_VERSION 2.4.3.0

USER root

# usa o snapshot fixo do Debian (já referenciado no sources.list da imagem) em vez do
# mirror "live", que remove pacotes antigos do bullseye e causa 404 em apt install.
# remove o repo do PostgreSQL (pgdg), que não publica mais bullseye e quebra o apt update
RUN sed -i \
        -e 's|^# deb http://snapshot.debian.org|deb http://snapshot.debian.org|g' \
        -e '/^deb http:\/\/deb.debian.org/d' \
        /etc/apt/sources.list && \
    rm -f /etc/apt/sources.list.d/pgdg.list && \
    # Retries/Timeout: o snapshot.debian.org é instável e derrubava o build com exit code 100
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
