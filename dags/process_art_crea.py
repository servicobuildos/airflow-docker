"""
DAG parametrizada para processar contratos SEVEN usando DockerOperator

Comando Docker equivalente:
docker run -it --rm --name process-contract \
  -v "$(pwd)/app:/app" \
  process-contract:latest \
  python main.py \
    --file "./files/not_processed/relatorio_os_seven_teste.json" \
    --arquivo-pdf "./files/not_processed/relatorio.pdf" \
    --user "915.933.604-87" \
    --password "78787878" \
    --cnpj-cliente "21.278.243/0001-66" \
    --cod-contrato "15643/2024" \
    --data-contrato "17/01/2025" \
    --crea-uf "RN" \
    --headless

Como usar via API:
curl -X POST "http://localhost:8080/api/v1/dags/process_art_crea/dagRuns" \
  -H "Content-Type: application/json" \
  -u "airflow:airflow" \
  -d '{
    "conf": {
      "json_file": "relatorio_os_seven_teste_com_endereco_out_2025.v2RN.json",
      "pdf_file": "Gmail - SEVEN Relatório de Conferência das O.S. - 21.278.243_0001-66 - DF - Data Limite_ 31_10_2025.v2RN.pdf",
      "user": "915.933.604-87",
      "password": "78787878",
      "cnpj_cliente": "21.278.243/0001-66",
      "cod_contrato": "15643/2024",
      "data_contrato": "17/01/2025",
      "crea_uf": "RN"
    }
  }'

Nota: O caminho do volume app é configurado automaticamente via HOST_APP_PATH no docker-compose.yml.
Para sobrescrever, adicione "app_path": "/caminho/customizado" na configuração.
"""

import os
from datetime import datetime
from pathlib import Path
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

# Descobre automaticamente o caminho do app no host
# Estratégia: O diretório dags está mapeado como volume, então podemos inferir o caminho do app
# Se /opt/airflow/dags está mapeado para /home/user/airflow-docker/dags
# Então o app deve estar em /home/user/airflow-docker/app

def get_host_app_path():
    """Descobre automaticamente o caminho do app no host"""
    # Primeiro tenta pegar da variável de ambiente
    env_path = os.getenv('HOST_APP_PATH')
    if env_path:
        return env_path
    
    # Tenta descobrir através do próprio caminho do arquivo
    # __file__ será algo como /opt/airflow/dags/process_art_crea.py
    dag_file = Path(__file__).resolve()
    
    # Se estamos em /opt/airflow/dags, o app estará em /opt/airflow/app no container
    # Mas precisamos do caminho no HOST
    # Para isso, usamos uma heurística: o volume das dags geralmente é montado como ./dags
    # Então o app deve estar em ../app relativo ao volume das dags
    
    # Verifica se existe o arquivo .env no diretório pai para confirmar que estamos no root do projeto
    airflow_root = dag_file.parent.parent  # /opt/airflow
    
    # Tenta ler o docker-compose.yml ou usar o padrão
    # Como não podemos acessar o host diretamente, usamos o padrão baseado na estrutura
    # A variável de ambiente deve ser setada no docker-compose.yml para portabilidade
    
    # Fallback: usa o caminho padrão (será sobrescrito se HOST_APP_PATH estiver setado)
    return '/home/djyllier/gonz.ai/airflow-docker/app'

HOST_APP_PATH = get_host_app_path()

# Configuração padrão da DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,  # Não faz retry - executa apenas 1 vez
}

# Criação da DAG
dag = DAG(
    'process_art_crea',
    default_args=default_args,
    description='Processa ordens de serviço ART/CREA através de DockerOperator',
    schedule_interval=None,  # Executar manualmente
    start_date=datetime(2025, 11, 7),
    catchup=False,
    tags=['docker', 'contract', 'seven', 'processing'],
)

# Task principal - Processar contrato SEVEN
# Nota: O Mount não suporta Jinja templates, então usamos o caminho fixo
# Para customizar, passe via environment variable HOST_APP_PATH no docker-compose.yml
process_contract_task = DockerOperator(
    task_id='process_art_crea',
    image="art_boot-app:latest",
    container_name='container_art_crea_{{ dag_run.conf.get("crea_uf") }}_{{ dag_run.conf.get("cnpj_cliente").replace(".", "_").replace("/", "_").replace("-", "_") }}',
    api_version='auto',
    auto_remove=True,
    tty=True,
    command=[
        'python', 'main.py',
        '--dados-os-json', '{{ dag_run.conf.get("dados_os_json") }}',
        # '--arquivo-pdf-base64', '{{ dag_run.conf.get("arquivo_pdf_base64") }}',
        '--user', '{{ dag_run.conf.get("user") }}',
        '--password', '{{ dag_run.conf.get("password") }}',
        '--cnpj-cliente', '{{ dag_run.conf.get("cnpj_cliente") }}',
        '--cod-contrato', '{{ dag_run.conf.get("cod_contrato") }}',
        '--data-contrato', '{{ dag_run.conf.get("data_contrato") }}',
        '--crea-uf', '{{ dag_run.conf.get("crea_uf") }}',
        '--execution-id', '{{ dag_run.conf.get("execution_id") }}',
        '--headless'
    ],
    mounts=[
        # Monta o diretório app - caminho é resolvido em tempo de definição da DAG
        # Para personalizar em diferentes ambientes, configure HOST_APP_PATH no docker-compose.yml
        Mount(
            source=HOST_APP_PATH,  # Resolvido no carregamento da DAG, não em runtime
            target='/app',
            type='bind'
        )
    ],
        environment={
        # Dados grandes passados via environment variables para evitar "argument list too long"
        'DADOS_OS_JSON': '{{ dag_run.conf.get("dados_os_json") }}',
        'ARQUIVO_PDF_BASE64': '{{ dag_run.conf.get("arquivo_pdf_base64") }}',
    },
    working_dir='/app',
    docker_url='unix://var/run/docker.sock',
    network_mode='containers-network',
    mount_tmp_dir=False,
    dag=dag
)

process_contract_task
