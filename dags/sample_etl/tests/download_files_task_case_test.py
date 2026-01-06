import os

from sample_etl.tasks.download_files_task import DownloadFilesTask
from sample_etl.tests.pipeline_case_test import TestPipelineCase


class TestDownloadFiles(TestPipelineCase):

    def test_download_files_DEV(self):

        kwargs = dict(
            ano='2022',
            mes='06',
            pipeline_name=self.pipeline_name
        )

        # execute task
        result = DownloadFilesTask(**kwargs).execute()

        file_exists = os.listdir(result)

        # check result
        assert file_exists, f"Arquivos na pasta `{result}` não localizado!"
