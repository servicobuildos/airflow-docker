# Guia de Produção

Este documento descreve as adequações necessárias para promover este projeto para produção, considerando o estado atual do repositório, a execução com Airflow em Docker Compose e a dependência do aplicativo externo montado por `HOST_APP_PATH`.

## Objetivo

Colocar em produção a DAG `process_art_rrt`, executada por um cluster Airflow com `CeleryExecutor`, garantindo:

- execução confiável do scheduler, webserver e workers;
- isolamento e rastreabilidade das execuções;
- proteção de segredos e credenciais;
- possibilidade de rollback;
- operação observável e recuperável.

## Arquitetura Atual

Hoje o repositório sobe os seguintes componentes via Docker Compose:

- `postgres`: banco de metadados do Airflow;
- `redis`: broker do Celery;
- `airflow-webserver`: interface e API do Airflow;
- `airflow-scheduler`: orquestração das DAGs;
- `airflow-worker`: execução assíncrona das tasks;
- `airflow-init`: bootstrap do banco e do usuário inicial.

A DAG `process_art_rrt` usa `DockerOperator` para subir o container `art_boot-app:latest`, montando um diretório do host em `/app` a partir da variável `HOST_APP_PATH`.

## Restrições e Gaps do Estado Atual

Antes de promover para produção, trate estes pontos obrigatoriamente:

1. O arquivo `docker-compose.yml` declara explicitamente que é para ambiente local de desenvolvimento.
2. A imagem usada pelo Airflow é local (`airflow:developer`) e não está versionada em registry.
3. Os serviços estão com `restart: "no"`, inadequado para produção.
4. O socket do Docker do host (`/var/run/docker.sock`) está montado nos containers do Airflow, o que concede acesso privilegiado ao host.
5. O projeto depende de código fora deste repositório via `HOST_APP_PATH`, atualmente apontando para outro diretório do host.
6. Segredos sensíveis estão parametrizados por `.env`; em produção eles devem sair de arquivo local simples e ir para um cofre de segredos.
7. `postgres` e `redis` estão expostos por portas do host; isso deve ser restringido à rede privada, salvo necessidade operacional explícita.
8. Não há política de backup, retenção de logs, monitoramento, alerta ou procedimento de rollback documentados no repositório.
9. A rede `containers-network` é externa e precisa existir previamente; isso deve ser automatizado ou gerenciado pela infraestrutura.
10. A DAG depende do contrato de CLI do `main.py` do app externo; qualquer mudança no app pode quebrar a execução da task.

## Decisões de Arquitetura Recomendadas

Para produção, use uma das duas estratégias abaixo.

### Estratégia A: Manter Docker Compose

Adequada para ambiente pequeno ou monolítico, com baixa necessidade de elasticidade.

Use quando:

- haverá um único host ou poucos hosts;
- o volume de execuções é previsível;
- a operação é enxuta e o time aceita gerenciar Docker diretamente.

### Estratégia B: Migrar para Orquestrador

Adequada para operação crítica ou necessidade de escala. Kubernetes é o caminho mais natural se o uso do `DockerOperator` for revisto.

Use quando:

- houver necessidade de múltiplos workers com escala controlada;
- for necessário reduzir acoplamento com o host;
- houver exigência maior de disponibilidade, isolamento e observabilidade.

Observação: com o desenho atual, o uso de `DockerOperator` e `docker.sock` dificulta endurecimento de segurança. Se o objetivo é um ambiente mais robusto, avalie substituir `DockerOperator` por um mecanismo de execução menos acoplado ao daemon Docker do host.

## Adequações Obrigatórias Antes do Go-Live

### 1. Imagens e Versionamento

- Publicar a imagem do Airflow em registry privado com tag imutável, por exemplo `registry.exemplo.com/airflow-docker/airflow:2026.04.05-1`.
- Publicar a imagem do app `art_boot-app` também com tag imutável.
- Proibir uso de `latest` em produção.
- Registrar a combinação aprovada entre a versão da DAG e a versão do app externo.

### 2. Segredos

- Remover credenciais reais de arquivos versionados ou arquivos `.env` distribuídos manualmente.
- Armazenar `SECRET_KEY`, `FERNET_KEY`, senhas SMTP, credenciais de banco e credenciais do app em cofre de segredos.
- Injetar segredos por mecanismo gerenciado da plataforma, não por cópia manual entre servidores.
- Rotacionar todas as chaves e senhas usadas em desenvolvimento.

### 3. Banco de Dados e Broker

- Usar PostgreSQL gerenciado ou instância dedicada com backup automático.
- Configurar política de retenção e restore testado.
- Restringir acesso ao PostgreSQL e Redis apenas à rede interna.
- Definir sizing mínimo de CPU, memória e disco com base na concorrência esperada.
- Configurar monitoramento de conexão, latência e espaço em disco.

### 4. Docker Compose de Produção

Criar um arquivo dedicado, por exemplo `docker-compose.prod.yml`, com pelo menos estas diferenças em relação ao atual:

- `restart: unless-stopped` ou política equivalente;
- imagens vindas de registry, sem `build: .` no host de produção;
- volumes persistentes nomeados ou storage dedicado para logs e metadados;
- remoção de portas públicas desnecessárias de `postgres` e `redis`;
- uso de proxy reverso com TLS na frente do `airflow-webserver`;
- definição explícita de recursos e limites;
- healthchecks preservados e ajustados ao ambiente real.

### 5. Segurança

- Colocar o webserver atrás de Nginx, Traefik ou load balancer com TLS.
- Restringir acesso à UI e API por IP, SSO, VPN ou autenticação corporativa.
- Revisar o uso de `basic_auth` para API; em produção, prefira integração com autenticação central.
- Revisar o risco de montar `/var/run/docker.sock`; isso equivale a alto privilégio no host.
- Executar varredura de imagem e dependências antes de cada release.

### 6. Dependência Externa do App

Este é o principal ponto de atenção operacional do projeto atual.

- O valor de `HOST_APP_PATH` aponta para um diretório externo ao repositório do Airflow.
- Em produção, esse código não deve depender de um path manual em disco fora do artefato implantado.
- Preferência 1: embutir tudo que o `art_boot-app` precisa dentro da própria imagem do app.
- Preferência 2: publicar um artefato versionado e montar somente dados, nunca código-fonte solto do host.
- Documentar claramente qual commit do app corresponde a cada release do Airflow.

### 7. Logging e Observabilidade

- Habilitar centralização de logs.
- Definir retenção de logs do Airflow e do app executado pelo `DockerOperator`.
- Configurar métricas e alertas para scheduler parado, worker indisponível, filas crescendo, tasks falhando e banco indisponível.
- Monitorar tempo de execução por DAG run, taxa de falhas e tempo de fila.

### 8. Operação da DAG

- Padronizar payload de disparo da API.
- Validar obrigatoriedade de todos os parâmetros aceitos pelo `main.py`.
- Padronizar `dag_run_id` para rastreabilidade.
- Definir limite de concorrência da DAG e expectativa de throughput.
- Formalizar contrato de entrada e saída do processamento.

## Checklist de Produção

Antes do deploy, valide:

- imagem do Airflow publicada e assinada;
- imagem do app publicada e assinada;
- segredos provisionados no cofre;
- banco e Redis provisionados com backup e monitoramento;
- rede e DNS criados;
- proxy reverso com TLS configurado;
- volumes persistentes criados;
- política de restart ativa;
- usuário admin inicial criado por procedimento controlado;
- DAG validada com payload real de homologação;
- rollback ensaiado;
- observabilidade validada;
- procedimento de suporte documentado.

## Exemplo de Variáveis de Ambiente para Produção

Exemplo conceitual. Ajuste aos nomes e mecanismos da sua plataforma:

```env
ENVIRONMENT=prod
AIRFLOW_UID=50000
AIRFLOW_IMAGE_NAME=registry.exemplo.com/airflow-docker/airflow:2026.04.05-1
HOST_STORAGE_PATH=/srv/airflow/storage
HOST_APP_PATH=/srv/art-rrt-bot/app
SMTP_HOST=smtp.exemplo.com
SMTP_PORT=587
SMTP_USER=airflow-notifier
SMTP_PASSWORD=<secret>
SMTP_SENDER_EMAIL=airflow@exemplo.com
SECRET_KEY=<secret>
FERNET_KEY=<secret>
```

Observações:

- `DAG_DEBUG_MODE=true` não deve ser mantido em produção sem necessidade justificada.
- `HOST_APP_PATH` deve apontar para artefato controlado e versionado.
- `AIRFLOW_IMAGE_NAME` deve apontar para registry privado.

## Fluxo Recomendado de Implantação

### Etapa 1. Preparar artefatos

1. Congelar versões do Airflow, providers e dependências Python.
2. Buildar a imagem do Airflow.
3. Buildar a imagem do app `art_boot-app`.
4. Publicar ambas em registry privado.
5. Registrar as tags aprovadas no changelog de release.

### Etapa 2. Preparar infraestrutura

1. Provisionar PostgreSQL.
2. Provisionar Redis.
3. Provisionar storage persistente.
4. Provisionar proxy reverso e certificados TLS.
5. Provisionar cofre de segredos.
6. Provisionar monitoramento e alertas.

### Etapa 3. Preparar configuração

1. Criar `docker-compose.prod.yml` ou manifesto equivalente.
2. Remover `build: .` e apontar imagens versionadas.
3. Ajustar políticas de restart.
4. Restringir exposição de portas internas.
5. Injetar segredos por mecanismo seguro.
6. Confirmar o path ou artefato do app externo.

### Etapa 4. Implantar

1. Subir `postgres` e `redis`.
2. Executar bootstrap do `airflow-init`.
3. Subir `airflow-webserver`, `airflow-scheduler` e `airflow-worker`.
4. Validar healthchecks.
5. Validar acesso à UI.
6. Disparar uma execução controlada da DAG com payload de homologação.

### Etapa 5. Validar pós-deploy

1. Confirmar importação da DAG.
2. Confirmar worker consumindo fila Celery.
3. Confirmar criação do container do app externo.
4. Confirmar persistência de logs.
5. Confirmar que alertas estão funcionando.

## Procedimento de Release

Para cada release:

1. Validar mudanças em DAG, Dockerfile, dependências e compose.
2. Executar smoke test em homologação.
3. Publicar imagens com nova tag.
4. Atualizar configuração de produção para as novas tags.
5. Implantar em janela controlada.
6. Executar DAG de teste.
7. Monitorar métricas e logs por período mínimo definido pelo time.

## Procedimento de Rollback

O rollback deve estar pronto antes do primeiro deploy.

1. Manter a última tag estável do Airflow e do app.
2. Manter versão anterior do compose ou manifesto.
3. Em caso de falha, reimplantar as tags anteriores.
4. Validar webserver, scheduler, worker e execução de uma DAG de smoke test.
5. Se houver migração de banco, garantir estratégia reversível ou plano de contingência específico.

## Smoke Test Recomendado

Após cada deploy em produção:

1. Acessar `/health` do webserver.
2. Verificar se scheduler e worker estão `healthy`.
3. Disparar a DAG com `dag_run_id` controlado.
4. Confirmar que a task cria o container do app com sucesso.
5. Confirmar conclusão do processamento e rastreabilidade no log.

Exemplo de disparo:

```bash
curl -X POST "https://airflow.exemplo.com/api/v1/dags/process_art_rrt/dagRuns" \
  -H "Content-Type: application/json" \
  -u "<usuario>:<senha>" \
  -d '{
    "dag_run_id": "Exec_RRT_001",
    "conf": {
      "dados_os_json": "<json>",
      "user": "<usuario>",
      "password": "<senha>",
      "cnpj_cliente": "00.000.000/0000-00",
      "cod_contrato": "12345/2026",
      "data_contrato": "05/04/2026",
      "conselho": "CAU",
      "crea_uf": "RN",
      "execution_id": "exec-rrt-001",
      "dag_run_id": "Exec_RRT_001",
      "considerar_deslocamento_doc_rt": "false"
    }
  }'
```

## Runbook de Incidentes

Quando houver falha operacional:

1. Verificar `docker compose ps` ou ferramenta equivalente.
2. Verificar logs de `airflow-webserver`, `airflow-scheduler` e `airflow-worker`.
3. Verificar disponibilidade do PostgreSQL e Redis.
4. Verificar se o `dag_run_id` e os parâmetros obrigatórios foram enviados.
5. Verificar se o app externo está acessível pela imagem e pelo path configurado.
6. Verificar se houve mudança incompatível na CLI do `main.py`.
7. Se necessário, executar rollback da release.

## Itens que Devem Ser Implementados no Repositório

Para sustentar produção de forma consistente, recomenda-se adicionar a este repositório:

1. `docker-compose.prod.yml`.
2. `env.prod.example` sem segredos reais.
3. pipeline de CI para build e push de imagens.
4. checklist de release.
5. política de backup e restauração.
6. documentação de monitoramento e alertas.

## Critério de Pronto para Produção

Considere este projeto apto para produção apenas quando:

- não depender de imagem `developer` nem tag `latest`;
- não depender de código solto do host sem versionamento;
- segredos estiverem fora de `.env` local;
- reinício automático, monitoramento e rollback estiverem definidos;
- a DAG tiver sido validada com payload realista em homologação;
- o time de operação souber recuperar webserver, scheduler, worker e app externo sem intervenção ad hoc.