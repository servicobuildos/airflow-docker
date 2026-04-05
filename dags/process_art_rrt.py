"""DAG para processar ART/CREA via `DockerOperator`.

Configuração esperada em `dag_run.conf`:

- `dados_os_json`
- `user`
- `password`
- `cnpj_cliente`
- `cod_contrato`
- `data_contrato`
- `conselho`
- `crea_uf`
- `execution_id`
- `considerar_deslocamento_doc_rt` (opcional)

O diretório do aplicativo montado no container é resolvido pela variável de
ambiente `HOST_APP_PATH`. Quando ela não estiver definida, a DAG usa um caminho
fallback compatível com a configuração atual do ambiente Docker.

Exemplo de acionamento:

```bash
curl -X POST "http://localhost:8080/api/v1/dags/process_art_crea/dagRuns" \
  -H "Content-Type: application/json" \
  -u "airflow:airflow" \
  -d '{
    "conf": {
      "dados_os_json": "<json-da-os>",
      "user": "<usuario>",
      "password": "<senha>",
      "cnpj_cliente": "00.000.000/0000-00",
      "cod_contrato": "12345/2025",
      "data_contrato": "17/01/2025",
      "conselho": "CREA",
      "crea_uf": "RN",
      "execution_id": "exec-123"
    }
  }'
```
"""

import os
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

DAG_ID = 'process_art_rrt'
DEFAULT_HOST_APP_PATH = '/home/djyllier/gonz.ai/buildos/airflow-docker/app'
DOCKER_IMAGE = 'art_boot-app:latest'
DOCKER_NETWORK = 'containers-network'
APP_MOUNT_TARGET = '/app'


def get_host_app_path() -> str:
    """Resolve o caminho do diretório da aplicação no host.

    A DAG prioriza `HOST_APP_PATH`, permitindo ajustar o bind mount sem mudar o
    código. Quando a variável não existe, usa um fallback conhecido para o
    ambiente atual.
    """
    env_path = os.getenv('HOST_APP_PATH')
    if env_path:
        return env_path

    project_root = Path(__file__).resolve().parents[1]
    local_app_path = project_root / 'app'
    if local_app_path.exists():
        return str(local_app_path)

    return DEFAULT_HOST_APP_PATH


def build_process_command() -> list[str]:
    """Monta a linha de comando do container com templates do Airflow."""
    return [
        'python',
        'main.py',
        '--os-json',
        '{{ dag_run.conf.get("dados_os_json") }}',
        '--user',
        '{{ dag_run.conf.get("user") }}',
        '--password',
        '{{ dag_run.conf.get("password") }}',
        '--cnpj-cliente',
        '{{ dag_run.conf.get("cnpj_cliente") }}',
        '--cod-contrato',
        '{{ dag_run.conf.get("cod_contrato") }}',
        '--data-contrato',
        '{{ dag_run.conf.get("data_contrato") }}',
        '--conselho',
        '{{ dag_run.conf.get("conselho") }}',
        '--crea-uf',
        '{{ dag_run.conf.get("crea_uf") }}',
        '--execution-id',
        '{{ dag_run.conf.get("execution_id") }}',
        '--dag-run-id',
        '{{ dag_run.conf.get("dag_run_id") }}',
        '--considerar-deslocamento-doc-rt',
        '{{ dag_run.conf.get("considerar_deslocamento_doc_rt", "false") }}',
        '--headless',
    ]


HOST_APP_PATH = get_host_app_path()

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
}

dag = DAG(
    DAG_ID,
    default_args=default_args,
    description='Processa ordens de serviço ART/CREA através de DockerOperator',
    doc_md=__doc__,
    schedule_interval=None,
    start_date=datetime(2025, 11, 7),
    catchup=False,
    tags=['Documento de RT', 'ART/RRT'],
)

process_contract_task = DockerOperator(
    task_id=DAG_ID,
    image=DOCKER_IMAGE,
    container_name='container_art_crea_{{ dag_run.conf.get("crea_uf") }}_{{ dag_run.conf.get("cnpj_cliente").replace(".", "_").replace("/", "_").replace("-", "_") }}',
    api_version='auto',
    auto_remove=True,
    tty=True,
    command=build_process_command(),
    mounts=[
        Mount(
            source=HOST_APP_PATH,
            target=APP_MOUNT_TARGET,
            type='bind',
        )
    ],
    working_dir=APP_MOUNT_TARGET,
    docker_url='unix://var/run/docker.sock',
    network_mode=DOCKER_NETWORK,
    mount_tmp_dir=False,
    dag=dag,
)

process_contract_task
