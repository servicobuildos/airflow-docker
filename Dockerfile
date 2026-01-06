FROM apache/airflow:2.4.3-python3.9 AS  airflow

ENV IMAGE_BUILD_VERSION 2.4.3.0

USER root

RUN apt -y update && \
    apt install -y --no-install-recommends \
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
