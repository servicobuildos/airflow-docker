import logging

from collections import defaultdict


class BaseTask(object):

    def __init__(self, pipeline_name, **kwargs) -> None:
        """Realiza inicialização da tarefa.

        Este método é executado antes da lógica principal no método '_execute'
        para preparar a tarefa.
        """
        # TODO : Esse método possui lógica especifica do airflow, precisa deixar esta classe agnostica ou mover esta para outro pacote

        self.log = logging.getLogger()

        # get task config from default kwargs (for tests and mocks)
        self.task_config = kwargs.get('task_config', defaultdict(dict))

        self.task_number = 0

        # general validations
        self.pipeline_name = pipeline_name
        if not self.pipeline_name:
            raise Exception('O parâmetro `pipeline_name` deve ser informado para executar esta tarefa!')

        # captura instância da tarefa
        self.task_instance = kwargs.get('ti', None)
        if self.task_instance:

            # captura o índice da tarefa se esta for dinâmica
            if hasattr(self.task_instance, 'map_index'):
                self.task_number = self.task_instance.map_index if self.task_instance.map_index >= 0 else 0

            # captura o id da execução da tarefa
            self.task_instance_id = f"{self.task_instance.task_id}_MI{self.task_number}_{self.task_instance.run_id}"

        # captura dependências da tarefa
        self.depends_on = kwargs.get('depends_on', None)
        if self.depends_on:
            for task_id in self.depends_on:
                self.task_config[task_id] = self.task_instance.xcom_pull(task_ids=task_id, map_indexes=self.task_number or None)

    @classmethod
    def call(cls, *args, **kwargs) -> object:
        """Chama a execução da tarefa de forma estática.

        Este método é um `wrapper` para execução da tarefa.
        Necessário para permitir a execução das tarefas pelo `PythonOperador` do Airflow.
        Por padrão, o `PythonOperador` do Airflow espera receber um método executável
        que não possui estado.

        Este método, cria uma instância da própria classe e executa a tarefa retornando
        o resultado e simulando o comportamento de um método sem estado.

        Isso é necessário para manter as classes de tarefas com estado quando
        utilizados em lógica com multi processamento.

        Returns:
            object: Resultado da execução da tarefa.
        """
        return cls(*args, **kwargs).execute()

    def execute(self, *args, **kwargs) -> object:
        """Executa lógia principal da tarefa.

        Este é um método público e deve ser utilizado pelos clientes externos 
        dessa classe para chamar a execução da tarefa.

        Returns:
            object: Resultado da execução da tarefa.
        """
        self._pre_execute()
        result = self._execute()
        return self._post_execute() or result

    def _pre_execute(self) -> None:
        """Executa pré-inicialização da tarefa.

        Este método pode ser utilizada para realizar passos adicionais
        antes de execução da lógica principal.
        """
        pass

    def _execute(self) -> object:
        """Executa lógia principal da tarefa.

        Este é um método privado onde deve ser implementado a lógica nas classes filhas.

        Returns:
            object: Resultado da execução da tarefa.
        """
        raise NotImplementedError

    def _post_execute(self) -> object:
        """Executa as etapas finais da tarefa.

        Returns:
            object: Objeto contendo o resultado da pós execução.
                Caso nenhum resultado seja retornado, será utilizado o resultado
                da função `_execute()`.
        """
        return None
