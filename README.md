# rest2-ons

[![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue)](https://www.python.org/downloads/)
[![CI](https://github.com/rjmalves/rest2-ons/actions/workflows/ci.yml/badge.svg)](https://github.com/rjmalves/rest2-ons/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Previsão de irradiância solar por usina com o modelo
[REST2](https://github.com/NREL/rest2), adaptado para céu com nuvens.

O `rest2-ons` é uma ferramenta de linha de comando com dois modos:

- **Treino**: para cada usina, ajusta os dois parâmetros da atenuação por
  nuvens (`mu0` e `g`) que minimizam o RMSE entre a irradiância calculada e a
  medida.
- **Inferência**: com os parâmetros ajustados, prevê a irradiância (GHI, DNI,
  DHI ou GHI em seguidor) a partir de previsões atmosféricas do ECMWF CAMS e
  de profundidade óptica de nuvens (COD).

Entradas e saídas podem estar em disco local ou no S3. Desenvolvido pelo
[Operador Nacional do Sistema Elétrico (ONS)](https://www.ons.org.br/).

## Instalação

Todas as formas abaixo instalam o comando `rest2-ons` e passam pelo
[uv](https://docs.astral.sh/uv/getting-started/installation/). O `pyproject.toml`
declara o `nwp-core` em `[tool.uv.sources]`, uma seção que só o uv lê.

O `nwp-core` está num repositório do GitHub com acesso de leitura restrito.
Quem não tem esse acesso não consegue instalar o `rest2-ons` até a publicação
do `nwp-core`, e o CI de pull requests vindos de forks falha pelo mesmo motivo.

### uv (recomendado)

O git precisa autenticar no github.com (por exemplo, com um credential helper
ou uma chave SSH com acesso de leitura ao `nwp-core`):

```bash
uv tool install git+https://github.com/rjmalves/rest2-ons
rest2-ons --help
```

O uv instala o programa num ambiente isolado e baixa uma versão compatível do
Python se a do sistema não servir. Se o comando `rest2-ons` não for
encontrado, `uv tool update-shell` adiciona o diretório dos executáveis ao
`PATH`.

```bash
uv tool upgrade rest2-ons     # atualiza
uv tool uninstall rest2-ons   # remove
```

Para executar sem instalar:

```bash
uvx --from git+https://github.com/rjmalves/rest2-ons rest2-ons train --config train.toml
```

### pipx (retirado)

O pipx não instala mais o `rest2-ons`. O pip e o pipx ignoram
`[tool.uv.sources]` e resolveriam o `nwp-core` pelo PyPI, onde o nome não está
reservado antes da publicação do `nwp-core`: um pacote de terceiros com esse
nome seria instalado no lugar do `nwp-core` verdadeiro. Quem instalou com o
pipx remove a instalação antiga:

```bash
pipx uninstall rest2-ons
```

### setup.sh e make install, a partir de um clone

O `setup.sh` cria um ambiente virtual com o uv e instala o programa nele. Ele
exige o uv na versão de `required-version` em `[tool.uv]` do `pyproject.toml`
ou mais nova, e a variável `NWP_CORE_READ_TOKEN_FILE`, que aponta para um
arquivo de uma linha, com modo `0600`, contendo um token de acesso de
granularidade fina e somente leitura ao `nwp-core`:

```bash
git clone https://github.com/rjmalves/rest2-ons.git
cd rest2-ons
export NWP_CORE_READ_TOKEN_FILE=/caminho/do/arquivo-do-token
./setup.sh --user      # ou: make install-user
```

Com `--user`, o programa fica em `$HOME/.local/rest2-ons` e o comando em
`$HOME/.local/bin`, que precisa estar no `PATH`. Sem `--user`, `make install`
instala para todos os usuários, em `/opt/rest2-ons` e `/usr/local/bin`; ele
repassa ao `sudo` somente a variável `NWP_CORE_READ_TOKEN_FILE`. Sob `sudo`, o
`PATH` é o `secure_path` do `sudoers`, então o uv precisa estar num diretório
dele, como `/usr/local/bin`. Para atualizar, rode `git pull` e repita o comando
com `--force` (`make reinstall`); para remover, use `--uninstall`.
`./setup.sh --help` lista as opções.

### Docker

A imagem é construída a partir de um clone, com o mesmo arquivo de token
passado como segredo de build. O token não fica na imagem:

```bash
docker build --secret id=nwp_core_token,src="$NWP_CORE_READ_TOKEN_FILE" \
  -t rest2-ons .
```

O contêiner roda com o usuário de UID 10001 e tem o `rest2-ons` como
`ENTRYPOINT`. O exemplo monta um TOML e um diretório de dados, e o TOML usa
caminhos absolutos dentro do contêiner (`/data/input`, `/data/artifact`):

```bash
mkdir -p data/input data/artifact
docker run --rm --read-only --tmpfs /tmp \
  --user "$(id -u):$(id -g)" \
  -v "$PWD/train.toml:/config/train.toml:ro" \
  -v "$PWD/data:/data" \
  rest2-ons train --config /config/train.toml
```

- Crie o diretório do host antes do `docker run`. Um diretório de origem que o
  Docker cria sozinho pertence ao root, e o processo do contêiner recebe
  `AccessDenied` (código de saída 2) ao escrever nele.
- Sem `--user`, o processo roda com o UID 10001 e só escreve em diretórios que
  esse usuário possa escrever.
- No Podman sem root, acrescente `--userns=keep-id` para que o seu usuário
  tenha o mesmo UID dentro do contêiner.

### Desenvolvimento

Para trabalhar no código (ambiente de desenvolvimento, testes e verificações),
veja o [CONTRIBUTING.md](CONTRIBUTING.md).

## Uso

1. Crie o arquivo de configuração de cada subcomando a partir dos exemplos
   [train.example.toml](train.example.toml) e
   [infer.example.toml](infer.example.toml):

   ```bash
   cp train.example.toml train.toml
   cp infer.example.toml infer.toml
   ```

   Fora de um clone, baixe os arquivos da raiz do repositório.

2. Coloque os arquivos de entrada no local `input` (veja
   [Dados de entrada](#dados-de-entrada)).

3. Ajuste os parâmetros:

   ```bash
   rest2-ons train --config train.toml
   ```

4. Gere as previsões com os artefatos do treino:

   ```bash
   rest2-ons infer --config infer.toml
   ```

A janela da inferência vem de `window` no TOML ou das opções da linha de
comando, que a substituem: `--start` e `--end` juntos, ou `--lookback` sozinho.

```bash
rest2-ons infer --config infer.toml --start 2024-03-01T00:00:00Z --end 2024-03-02T00:00:00Z
rest2-ons infer --config infer.toml --lookback P2D
```

`--lookback` recebe uma duração ISO 8601 e define a janela
`[âncora - duração, âncora)`, em que a âncora é o instante UTC de início da
execução; ela só alcança o passado. `rest2-ons --version` mostra a versão.

### Configuração

O arquivo é TOML, indicado por `--config` ou pela variável `REST2_ONS_CONFIG`.
O `train` e o `infer` têm chaves diferentes; uma chave do outro subcomando é
recusada com código de saída 2. A tabela lista as chaves, agrupadas pela chave
de nível mais alto.

| Chave                                                             | Subcomando | Descrição                                                                                                                                                                                                                                                                    |
| ----------------------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `input.uri`                                                       | ambos      | Local dos arquivos de entrada                                                                                                                                                                                                                                                |
| `artifact.uri`                                                    | ambos      | Local dos artefatos: gravados no treino, lidos na inferência                                                                                                                                                                                                                 |
| `output.uri`                                                      | infer      | Local das previsões                                                                                                                                                                                                                                                          |
| `plant_ids`                                                       | ambos      | Lista de `id_usina` a processar; sem a chave, processa todas as usinas de `usinas.csv`                                                                                                                                                                                       |
| `target_radiation_type`                                           | ambos      | Tipo de irradiância medida e prevista: `"ghi"`, `"dni"`, `"dhi"` ou `"ghi_tracker"` (GHI em seguidor)                                                                                                                                                                        |
| `forecasting_day_ahead`                                           | ambos      | Antecedência da previsão em dias inteiros, contada de `data_hora_rodada` a `data_hora_previsao`: `0` usa as previsões feitas com menos de 24 h de antecedência, `1` as de 24 h a 48 h, e assim por diante; se mais de uma rodada prevê o mesmo instante, vale a mais recente |
| `plots`                                                           | ambos      | `true` grava gráficos HTML interativos; padrão `false`                                                                                                                                                                                                                       |
| `training_window.start`, `training_window.end`                    | train      | Janela de ajuste dos parâmetros                                                                                                                                                                                                                                              |
| `validation_window.start`, `validation_window.end`                | train      | Janela de validação, só para métricas                                                                                                                                                                                                                                        |
| `test_window.start`, `test_window.end`                            | train      | Janela de teste, só para métricas                                                                                                                                                                                                                                            |
| `window.start`, `window.end`                                      | infer      | Janela prevista; as opções `--start`, `--end` e `--lookback` a substituem                                                                                                                                                                                                    |
| `storage.max_attempts`, `storage.connect_timeout_s`               | ambos      | Tentativas por requisição e tempo limite de conexão do cliente de armazenamento                                                                                                                                                                                              |
| `storage.read_timeout_s`, `storage.max_pool_connections`          | ambos      | Tempo limite de leitura e tamanho do pool de conexões do cliente de armazenamento                                                                                                                                                                                            |
| `input.anonymous`, `artifact.anonymous`, `output.anonymous`       | ambos      | Só em locais S3: requisições sem assinatura, para fontes públicas                                                                                                                                                                                                            |
| `input.endpoint_url`, `artifact.endpoint_url`, `output.endpoint_url` | ambos   | Só em locais S3: endpoint de um armazenamento compatível com S3                                                                                                                                                                                                              |
| `input.provider_source`, `artifact.provider_source`, `output.provider_source` | ambos | Só em locais S3: ignora os endpoints configurados no ambiente da AWS                                                                                                                                                                                                  |
| `input.storage_class`, `artifact.storage_class`, `output.storage_class` | ambos | Só em locais S3: classe de armazenamento dos objetos gravados                                                                                                                                                                                                                |

Cada janela tem os campos `start` e `end`. Em `storage`, os campos são
`max_attempts`, `connect_timeout_s`, `read_timeout_s` e `max_pool_connections`;
em cada local, `uri` e, só em S3, `anonymous`, `endpoint_url`,
`provider_source` e `storage_class`. As chaves `output.*` existem só no `infer`. Os limites dos valores de `storage`
e dos campos de local S3 pertencem ao nwp-core; `rest2-ons train --help` e
`rest2-ons infer --help` listam as opções da linha de comando.

**Janelas.** Cada janela é semiaberta, em UTC: o início está incluído e o fim,
excluído. O treino ajusta os parâmetros em `training_window` e calcula as
métricas também em `validation_window` e `test_window`; a inferência prevê a
janela `window`.

**Locais.** `uri` é um caminho local absoluto ou um URI `s3://`. Cada
componente de um caminho local usa só `[A-Za-z0-9._-]`, não é `.` nem `..` e não
começa com `.nwp-`; um caminho com espaço ou letra acentuada é recusado na
validação, com código de saída 2. Os limites de tamanho vêm da gramática de
locais do nwp-core.

**Raízes existentes.** Um local de artefato ou de saída em disco precisa existir
antes da execução. Se não existir, a primeira gravação falha com
`LocationUnusableError` (código 2); no `train`, isso acontece depois do ajuste
da primeira usina. Subdiretórios como `plots/` são criados. Prefixos S3 não
exigem nada.

**Identificadores de usina.** Os `plant_ids` explícitos são validados contra a
regra de componente de chave de armazenamento, e um valor que a viole encerra
com código 2, citando a regra e nunca o valor. Um `id_usina` lido de
`usinas.csv` que a viole falha só a usina dele (código 3). O limite de tamanho
da chave gravada conta o prefixo S3, não é verificado na validação e falha a
gravação da usina (código 3).

**Variáveis de ambiente.** Cada chave também vem de uma variável `REST2_ONS_`
seguida do caminho da chave em maiúsculas, com `__` entre os níveis: por
exemplo, `REST2_ONS_INPUT__URI` e `REST2_ONS_WINDOW__START`. A precedência é:
opções da linha de comando, variáveis de ambiente, arquivo TOML e valores
padrão. Uma variável de uma chave do outro subcomando, como
`REST2_ONS_OUTPUT__URI` no `train`, encerra com código 2.

### S3

`input.uri`, `artifact.uri` e `output.uri` aceitam `s3://example-bucket/prefixo`,
combinados livremente com caminhos locais. As credenciais seguem a
[cadeia padrão da AWS](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html):
variáveis de ambiente (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`AWS_DEFAULT_REGION`), um perfil (`AWS_PROFILE`) ou o papel IAM da máquina.

### Execução

- Cada usina é um item de trabalho. Se uma usina falha, as outras continuam e
  ficam gravadas, e a execução encerra com código 3.
- As gravações substituem o conteúdo existente. O `train` grava o artefato e
  depois os gráficos; o `infer` grava a saída e depois os gráficos. Os arquivos
  locais têm modo `0600`.
- O resumo da execução é uma linha JSON na saída padrão, com o esquema
  `nwp.run-summary/1`. Campos como `exit_code`, `counts` e `items` mostram o
  resultado geral e o de cada usina; a lista completa está no esquema.
- Os logs são JSON na saída de erro.

Códigos de saída:

| Código | Significado                                                                                                                                                                       |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0      | Sucesso.                                                                                                                                                                          |
| 1      | Erro interno ou erro transitório de armazenamento: `StorageUnavailable`, `ObjectArchived` ou outro `StorageError`.                                                                |
| 2      | Erro de configuração ou de uso; `usinas.csv` ausente ou malformado, lido antes da execução; `AccessDenied`; `LocationUnusableError`.                                              |
| 3      | Ao menos uma usina falhou.                                                                                                                                                        |
| 4      | Não usado pelo `rest2-ons`.                                                                                                                                                       |

## Dados de entrada

O local `input` contém um arquivo por variável:

| Arquivo                       | Conteúdo                                                        |
| ----------------------------- | --------------------------------------------------------------- |
| `usinas.csv`                  | Uma linha por usina: `id_usina`, `latitude`, `longitude`        |
| `measured_irradiance.parquet` | Irradiância medida: `id_usina`, `data_hora_observacao`, `valor` |
| `cod.parquet`                 | Previsão de profundidade óptica de nuvens                       |
| `albedo.parquet`              | Previsão CAMS de albedo da superfície                           |
| `h2o.parquet`                 | Previsão CAMS de vapor d'água                                   |
| `no2.parquet`                 | Previsão CAMS de dióxido de nitrogênio                          |
| `o3.parquet`                  | Previsão CAMS de ozônio                                         |
| `od550.parquet`               | Previsão CAMS de profundidade óptica de aerossóis em 550 nm     |
| `od670.parquet`               | Previsão CAMS de profundidade óptica de aerossóis em 670 nm     |
| `psurf.parquet`               | Previsão CAMS de pressão na superfície                          |
| `temp.parquet`                | Previsão CAMS de temperatura a 2 m                              |

O `usinas.csv` e os arquivos de previsão são obrigatórios nos dois modos; o
`measured_irradiance.parquet` só é lido no treino. Os arquivos de previsão têm
as colunas `latitude`, `longitude`, `data_hora_rodada` (início da rodada),
`data_hora_previsao` (instante previsto) e `valor`.

- Datas e horas não têm fuso horário e significam UTC.
- Latitude e longitude estão em graus decimais.
- Em `measured_irradiance.parquet`, `valor` é a irradiância em W/m² do tipo
  escolhido em `target_radiation_type`.
- Cada variável de previsão tem uma unidade declarada. Um arquivo cujos
  valores caem fora da faixa plausível dessa unidade, o sinal típico de
  unidade trocada, é rejeitado na leitura. A tabela de unidades e a regra
  exata estão em
  [METHODOLOGY.md](METHODOLOGY.md#input-data-requirements).
- Cada usina usa o ponto de grade mais próximo das suas coordenadas: o de
  `albedo.parquet` para todas as variáveis CAMS e o de `cod.parquet` para a
  COD. Os arquivos CAMS precisam, portanto, ter os mesmos pontos de grade de
  `albedo.parquet`.

## Saídas

Treino, no local `artifact`:

- `{id_usina}.json`: parâmetros ajustados, métricas (ME, MAE e RMSE, em
  W/m²) nas janelas de treino, validação e teste, e o tipo de radiação.
- `plots/{id_usina}_train_*.html`: gráficos, quando `plots` é `true`.

```json
{
  "parameters": { "mu0": 0.2, "g": 0.85 },
  "metrics": {
    "train": { "ME": -9.2, "MAE": 66.6, "RMSE": 134.0 },
    "validation": { "ME": -0.7, "MAE": 69.9, "RMSE": 220.6 },
    "testing": { "ME": -3.8, "MAE": 64.4, "RMSE": 134.0 }
  },
  "radiation_type": "dni"
}
```

Inferência, no local `output`:

- `{id_usina}.parquet`: colunas `time` (sem fuso horário, em UTC) e `valor`
  (irradiância prevista em W/m², do tipo `target_radiation_type`).
- `plots/{id_usina}_inference_*.html`: gráficos, quando `plots` é `true`.

## Metodologia

O REST2 calcula a irradiância de céu claro em duas bandas espectrais a partir
de pressão, ozônio, NO₂, vapor d'água, aerossóis e albedo. O `rest2-ons`
acrescenta a atenuação por nuvens a partir da COD, com dois parâmetros, `mu0`
e `g`, que o treino ajusta por usina com L-BFGS-B dentro de limites físicos,
minimizando o RMSE na janela de treino. As equações, os limites dos
parâmetros e as métricas estão em [METHODOLOGY.md](METHODOLOGY.md).

## Limitações

- Cada usina é tratada como um ponto: usa um único ponto de grade, sem média
  espacial.
- As nuvens são descritas apenas pela profundidade óptica.
- O sombreamento por relevo não é considerado.

## Documentação

- [METHODOLOGY.md](METHODOLOGY.md): equações do REST2, unidades de entrada,
  calibração e métricas (em inglês).
- [ARCHITECTURE.md](ARCHITECTURE.md): módulos e fluxo de dados.
- [CONTRIBUTING.md](CONTRIBUTING.md): ambiente de desenvolvimento, testes e
  verificações.
- [CHANGELOG.md](CHANGELOG.md): mudanças entre versões.

Dúvidas e problemas: [GitHub Issues](https://github.com/rjmalves/rest2-ons/issues).

## Licença

MIT. Veja [LICENSE](LICENSE).

## Referências

- Gueymard, C. A. (2008). REST2: High-performance solar radiation model for
  cloudless-sky irradiance, illuminance, and photosynthetically active
  radiation. _Solar Energy_, 82(3), 272-285.
- [Implementação do REST2 pelo NREL](https://github.com/NREL/rest2)

## Citação

```bibtex
@software{rest2ons2025,
  author = {Cossich, William and Alves, Rogério},
  title = {rest2-ons: Generalização ML do Modelo de Radiação Solar REST2},
  year = {2025},
  url = {https://github.com/rjmalves/rest2-ons}
}
```
