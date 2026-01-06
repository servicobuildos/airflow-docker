from datetime import datetime

from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator

from sample_etl.tasks.download_files_task import DownloadFilesTask


#*******************************************
# Criação do objeto que representará a DAG
#*******************************************

dag = DAG(
    'sample_etl', 
    description='Extracao, Transformacao e Carga de dados',
    schedule_interval=None,
    start_date=datetime(2022, 12, 30), 
    catchup=False
)

#*******************************************
# Configura as Tarefas do Fluxo de Trabalho
#*******************************************

# start task
start = DummyOperator(
    task_id='start', 
    dag=dag
)

# download files task
download_files_task = PythonOperator(
    task_id='download_files_task', 
    python_callable=DownloadFilesTask.call, 
    op_args=('2022', '06', 'sample_etl'),
    dag=dag
)

# end task
end = DummyOperator(
    task_id='end', 
    dag=dag
)

#**************************************************************
# Configura a sequencia de execução e dependência das tarefas
#**************************************************************

start >> download_files_task >> end
