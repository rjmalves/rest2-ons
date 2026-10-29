# rest2-ons

[![Python](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Frjmalves%2Frest2-ons%2Fmain%2Fpyproject.toml)](https://www.python.org/downloads/)
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

Todas as formas abaixo instalam o comando `rest2-ons`.

### uv (recomendado)

Com o [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado:

```bash
uv tool install git+https://github.com/rjmalves/rest2-ons
rest2-ons --help
```

O uv instala o programa num ambiente isolado e baixa uma versão compatível do
Python se a do sistema não servir. Se o comando `rest2-ons` não for
encontrado, `uv tool update-shell` adiciona o diretório dos executáveis ao
`PATH`.

```bash
uv tool upgrade rest2-ons     # atualiza para o último commit do main
uv tool uninstall rest2-ons   # remove
```

Para executar sem instalar:

```bash
uvx --from git+https://github.com/rjmalves/rest2-ons rest2-ons --config config.jsonc
```

### pipx

Com o [pipx](https://pipx.pypa.io/stable/how-to/install-pipx.html) instalado e
um Python na versão exigida (veja o selo no topo da página):

```bash
pipx install git+https://github.com/rjmalves/rest2-ons
rest2-ons --help
```

Se o comando não for encontrado, `pipx ensurepath` adiciona o diretório dos
executáveis ao `PATH`.

```bash
pipx reinstall rest2-ons   # atualiza para o último commit do main
pipx uninstall rest2-ons   # remove
```

### setup.sh, a partir de um clone

O `setup.sh` cria um ambiente virtual com o `python3` do sistema e instala o
programa nele:

```bash
git clone https://github.com/rjmalves/rest2-ons.git
cd rest2-ons
./setup.sh --user      # ou: make install-user
```

Com `--user`, o programa fica em `$HOME/.local/rest2-ons` e o comando em
`$HOME/.local/bin`, que precisa estar no `PATH`. Sem `--user`,
`sudo ./setup.sh` (ou `make install`) instala para todos os usuários, em
`/opt/rest2-ons` e `/usr/local/bin`. Para atualizar, rode `git pull` e repita
o comando com `--force`; para remover, use `--uninstall`. `./setup.sh --help`
lista as opções.

### Docker

A imagem é construída a partir de um clone. Com o `config.jsonc` e o diretório
`data` no diretório atual:

```bash
docker build -t rest2-ons .
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$PWD/data:/app/data" \
  -v "$PWD/config.jsonc:/app/config.jsonc:ro" \
  rest2-ons --config config.jsonc
```

O diretório de trabalho do contêiner é `/app`, então caminhos relativos no
`config.jsonc`, como `data/input`, apontam para o diretório `data` montado.
`--user` roda o contêiner com o seu usuário; sem ele, o processo usa o usuário
da imagem e pode não ter permissão de escrita em `data`.

### Desenvolvimento

Para trabalhar no código (ambiente de desenvolvimento, testes e verificações),
veja o [CONTRIBUTING.md](CONTRIBUTING.md).

## Uso

1. Crie o arquivo de configuração a partir do exemplo:

   ```bash
   curl -fsSL -o config.jsonc https://raw.githubusercontent.com/rjmalves/rest2-ons/main/config.example.jsonc
   ```

   Num clone, `cp config.example.jsonc config.jsonc` faz o mesmo.

2. Coloque os arquivos de entrada no diretório `input` da configuração (veja
   [Dados de entrada](#dados-de-entrada)).

3. Com `"mode": "train"`, ajuste os parâmetros:

   ```bash
   rest2-ons --config config.jsonc
   ```

4. Mude para `"mode": "inference"` e rode o mesmo comando para gerar as
   previsões.

Sem `--config`, o programa lê `config.jsonc` do diretório atual. O log vai
para a saída de erro, e qualquer falha encerra o programa com código 1.

### Configuração

O arquivo é JSON com comentários (JSONC). Todas as chaves são obrigatórias,
exceto `postprocessing`.

| Chave                   | Descrição                                                                                                                                                                                                                                                                    |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mode`                  | `"train"` ajusta os parâmetros e grava os artefatos; `"inference"` lê os artefatos e grava as previsões                                                                                                                                                                      |
| `input`                 | Diretório dos arquivos de entrada                                                                                                                                                                                                                                            |
| `artifact`              | Diretório dos artefatos: gravados no treino, lidos na inferência                                                                                                                                                                                                             |
| `output`                | Diretório das previsões                                                                                                                                                                                                                                                      |
| `plant_ids`             | Lista de `id_usina` a processar; `null` processa todas as usinas de `usinas.csv`                                                                                                                                                                                             |
| `forecasting_day_ahead` | Antecedência da previsão em dias inteiros, contada de `data_hora_rodada` a `data_hora_previsao`: `0` usa as previsões feitas com menos de 24 h de antecedência, `1` as de 24 h a 48 h, e assim por diante; se mais de uma rodada prevê o mesmo instante, vale a mais recente |
| `target_radiation_type` | Tipo de irradiância medida e prevista: `"ghi"`, `"dni"`, `"dhi"` ou `"ghi_tracker"` (GHI em seguidor)                                                                                                                                                                        |
| `time_windows`          | Janelas `training`, `validation`, `test` e `inference`, cada uma como `"início/fim"` em ISO 8601, em UTC, com as duas pontas incluídas                                                                                                                                       |
| `postprocessing.plots`  | `true` grava gráficos HTML interativos; padrão `false`                                                                                                                                                                                                                       |

As quatro janelas são exigidas nos dois modos. O treino ajusta os parâmetros
em `training` e calcula as métricas também em `validation` e `test`; a
inferência prevê a janela `inference`.

Na inferência, use o mesmo `target_radiation_type` do treino. O tipo gravado
no artefato não é conferido, e outro tipo aplica os parâmetros a outra
grandeza sem aviso.

### S3

`input`, `output` e `artifact` aceitam caminhos `s3://bucket/prefixo`,
combinados livremente com caminhos locais. As credenciais seguem a
[cadeia padrão da AWS](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html):
variáveis de ambiente (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`AWS_DEFAULT_REGION`), um perfil (`AWS_PROFILE`) ou o papel IAM da máquina.

## Dados de entrada

O diretório `input` contém um arquivo por variável:

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

Treino, no diretório `artifact`:

- `{id_usina}.json`: parâmetros ajustados, métricas (ME, MAE e RMSE, em
  W/m²) nas janelas de treino, validação e teste, e o tipo de radiação.
- `plots/{id_usina}_train_*.html`: gráficos, quando `postprocessing.plots` é
  `true`.

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

Inferência, no diretório `output`:

- `{id_usina}.parquet`: colunas `time` (sem fuso horário, em UTC) e `valor`
  (irradiância prevista em W/m², do tipo `target_radiation_type`).
- `plots/{id_usina}_inference_*.html`: gráficos, quando
  `postprocessing.plots` é `true`.

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
