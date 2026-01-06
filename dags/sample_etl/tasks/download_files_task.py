import os

import requests

from framework_dataflow.tasks.base_task import BaseTask

from sample_etl.tools.utils import extractall


class DownloadFilesTask(BaseTask):
    """Realiza download do arquivo diretamente do site.
    """

    def __init__(
            self,
            ano: str,
            mes: str,
            pipeline_name: str,
            **kwargs: dict
        ):
        """Realiza inicialização da tarefa.

        Args:
            pipeline_name (str): Nome da pipeline em execução.

        Raises:
            InvalidParamException: Exceção para parâmetros inválidos na inicialização.
        """

        super().__init__(pipeline_name, **kwargs)

        # validações gerais
        self.ano = ano
        if not self.ano:
            raise Exception('Parâmetro `ano` deve ser informado!')

        self.mes = mes
        if not self.mes:
            raise Exception('Parâmetro `mes` deve ser informado!')

        self.file_content = None
        self.base_path = f'/opt/airflow/.storage/datalake/landing/{self.pipeline_name}'

    def _execute(self):
        """Executa o fluxo principal da tarefa.

        Returns:
            list: Retorna uma lista com ano e mês.
        """
        self._download_zip_file()
        self._save_zip_file()
        self._extract_files()
        self._normaliza_files()
        
        return os.path.join(self.base_path, f'{self.ano}{self.mes}')

    def _download_zip_file(self):
        """Realizar o download do arquivo.

        Raises:
            Exception: Exceção para problemas na execução do fluxo de dados.
        """

        url = 'https://www.portaltransparencia.gov.br/download-de-dados/licitacoes/{}{}'.format(
            self.ano,
            self.mes
        )

        self.log.info(f"Baixando dados a partir de {url}...")

        response = requests.get(url)

        # check response
        if not response.status_code == 200:
            raise Exception(f'Site não retornou uma resposta válida. Status Code: {response.status_code}')
        if not response.content:
            raise Exception('Site não retornou um conteúdo para o arquivo!')

        self.file_content = response.content

    def _save_zip_file(self):
        """Realiza gravação do arquivo baixado para o disco local.
        """

        zip_file_name = f"{self.ano}{self.mes}.zip"

        self.log.info(f'Salvando arquivo em {zip_file_name}...')

        if not os.path.isdir(self.base_path):
            os.makedirs(self.base_path)

        with open(os.path.join(self.base_path, zip_file_name), 'wb') as f:
            f.write(self.file_content)

    def _extract_files(self):
        """Realiza extração e normalização dos nomes dos arquivos.

        Raises:
            Exception: Exceção para problemas na execução do fluxo de dados.
        """

        self.log.info(f'Extraindo arquivos para /{self.ano}{self.mes}...')

        extractall(
            os.path.join(self.base_path, f"{self.ano}{self.mes}.zip"),
            os.path.join(self.base_path, f"{self.ano}{self.mes}"),
            overwrite=True
        )

    def _normaliza_files(self):

        files = os.listdir(
            os.path.join(
                self.base_path,
                f"{self.ano}{self.mes}"
            )
        )

        # normaliza o nome dos arquivos para o formato correto
        for file_name in files:

            if '_Empenhos' in file_name:
                new_file_name = 'empenhos'
            elif '_ItemLicita' in file_name:
                new_file_name = 'item'
            elif '_Licita' in file_name:
                new_file_name = 'licitacao'
            elif '_ParticipantesLicita' in file_name:
                new_file_name = 'participantes'
            else:
                raise Exception(f'Tipo de arquivo CSV inválido no ZIP do exercicio {self.mes}/{self.ano}: {file_name}')

            new_file_name = f'{self.ano}{self.mes}_{new_file_name}.csv'

            os.rename(
                os.path.join(self.base_path, f'{self.ano}{self.mes}', file_name),
                os.path.join(self.base_path, f'{self.ano}{self.mes}', new_file_name)
            )
