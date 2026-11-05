# Arquitetura do Sistema

Este documento descreve a arquitetura do `rest2-ons`: o fluxo de dados, os
módulos e as decisões de design. A instalação, a configuração e os códigos de
saída estão no [README.md](README.md); as equações do modelo, em
[METHODOLOGY.md](METHODOLOGY.md).

## Visão Geral

O `rest2-ons` ajusta os parâmetros do modelo REST2 de cada usina contra a
irradiância medida e prevê a irradiância com os parâmetros ajustados. Há dois
subcomandos, `rest2-ons train` e `rest2-ons infer`, e uma API em Python com as
funções `rest2_ons.train` e `rest2_ons.infer`. O subcomando é uma camada fina
sobre a API: lê a configuração, chama a função e devolve o resultado da
execução ao `nwp_core.cli`, que o converte em código de saída.

1. **`train`**: otimiza os parâmetros do REST2 de cada usina com dados medidos
   históricos e grava um artefato por usina.
2. **`infer`**: lê o artefato de cada usina e grava a previsão da janela pedida.

Cada usina é um item de trabalho independente: a falha de uma usina não impede
as demais.

## Diagrama de Fluxo

```
   TOML (--config)      variáveis REST2_ONS_*      opções do CLI
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 ▼
                      ┌─────────────────────┐
                      │      _cli.py        │  subcomandos train e infer
                      │  load_config()      │  (click + nwp_core.cli)
                      └──────────┬──────────┘
                                 ▼
                      ┌─────────────────────┐
                      │     _config.py      │  TrainConfig / InferConfig
                      └──────────┬──────────┘
                                 ▼
                      ┌─────────────────────┐
                      │      _api.py        │  train() / infer()
                      │  open_storage()     │  abre cada local uma vez
                      │  usinas.csv         │  lista de usinas, se plant_ids
                      │                     │  não está definido
                      │  run_items()        │  um item de trabalho por usina
                      └──────────┬──────────┘
                                 │ para cada usina
                 ┌───────────────┴────────────────┐
                 ▼                                ▼
      ┌─────────────────────┐          ┌─────────────────────┐
      │     readers.py      │          │     readers.py      │
      │  InputData          │          │  InputData e        │
      │                     │          │  read_plant_artifact│
      └──────────┬──────────┘          └──────────┬──────────┘
                 ▼                                ▼
      ┌─────────────────────┐          ┌─────────────────────┐
      │    training.py      │          │    inference.py     │
      │  train_plant()      │          │  predict_plant()    │
      └──────────┬──────────┘          └──────────┬──────────┘
                 └───────────────┬────────────────┘
                                 ▼
                      ┌─────────────────────┐
                      │ services/radiation  │  modelo REST2, métricas
                      └──────────┬──────────┘
                                 ▼
                      ┌─────────────────────┐
                      │     writers.py      │  chaves de _keys.py
                      └──────────┬──────────┘
                                 ▼
                      ┌─────────────────────┐
                      │  armazenamento      │  disco local ou s3://
                      │  {usina}.json       │  artefato (train)
                      │  {usina}.parquet    │  previsão (infer)
                      │  plots/*.html       │  gráficos, se plots = true
                      └─────────────────────┘

   Na saída padrão: o resumo da execução, uma linha JSON (ver README.md).
```

## Componentes Principais

### 1. Entrada de linha de comando (`src/rest2_ons/_cli.py`)

Define o grupo `rest2-ons` e os subcomandos `train` e `infer` com `click`.
Cada subcomando carrega a configuração com `nwp_core.config.load_config` e o
prefixo `REST2_ONS`, registra os valores secretos para que os logs os
ocultem e chama a API. A precedência das fontes e os códigos de saída estão no
[README.md](README.md).

| Símbolo  | Descrição                                           |
| -------- | --------------------------------------------------- |
| `cli()`  | Grupo `click` com os dois subcomandos               |
| `main()` | Ponto de entrada do console script; roda o `run_cli`|

### 2. Configuração (`src/rest2_ons/_config.py`)

`TrainConfig` e `InferConfig` definem e validam a configuração dos
subcomandos `train` e `infer`. Compartilham o local `input`, o local
`artifact`, `plant_ids`, `target_radiation_type`, `forecasting_day_ahead`,
`plots` e `storage`; cada um acrescenta as janelas de tempo do seu subcomando.
O esquema JSON de cada modelo é fixado em `tests/surface/`.

### 3. API (`src/rest2_ons/_api.py`)

`train()` e `infer()` são a API pública. Cada uma:

1. cria o contexto da execução (`RunContext`);
2. abre cada local de armazenamento uma vez com `open_storage`;
3. lê o `usinas.csv` quando `plant_ids` não está definido;
4. executa um item de trabalho por usina com `run_items`, em sequência.

Uma usina que levanta exceção termina como `FAILED`, as outras continuam e o
`RunFailedError` final carrega o resultado de todos os itens. O formato do
resumo e o código de saída 3 estão no [README.md](README.md).

### 4. Erros e chaves (`_errors.py`, `_keys.py`)

`_errors.py` guarda a hierarquia de erros do programa, com raiz em
`Rest2Error`; os erros do `usinas.csv` ausente ou malformado são fatais para a
execução, os demais isolam uma usina. `_keys.py` compõe as chaves de cada
usina (`{id}.json`, `{id}.parquet`, `plots/{id}_*.html`) e recusa um
identificador de usina que não seria um componente válido de chave.

| Símbolo            | Descrição                                          |
| ------------------ | -------------------------------------------------- |
| `artifact_key()`   | Chave do artefato de parâmetros                    |
| `output_key()`     | Chave da previsão                                  |
| `plot_key()`       | Chave de um gráfico                                |
| `check_plant_id()` | Valida o identificador antes de qualquer gravação  |

### 5. Leitura de Dados (`src/rest2_ons/readers.py`)

`InputData` recebe um `Storage` e carrega as entradas do local `input`.

```
Entrada: Storage do local input
    │
    ▼
┌─────────────────────────────────┐
│ read_usinas() / plant_ids()     │ → metadados das usinas (CSV)
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ for_location().build()          │ → previsões CAMS e COD (Parquet)
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ read_measured_for_plant()       │ → medições (Parquet)
└─────────────────────────────────┘
    │
    ▼
Saída: Polars DataFrames e LocationInputData
```

| Símbolo                        | Descrição                                           |
| ------------------------------ | --------------------------------------------------- |
| `InputData`                    | Leitor das entradas de um local                     |
| `LocationDataBuilder`          | Monta os dados de um ponto de grade e uma janela    |
| `LocationInputData`            | Séries do local, já na unidade das equações         |
| `read_plant_artifact()`        | Lê e valida o artefato de uma usina                 |

`input_contract.py` declara a unidade de cada arquivo de entrada
(`DECLARED_UNITS`) e rejeita um arquivo fora da faixa plausível com
`validate_input_units()`; `LocationInputData.apply_unit_conversions` converte
para as unidades das equações. A tabela de unidades está em
[METHODOLOGY.md](METHODOLOGY.md#input-data-requirements).

### 6. Treinamento (`src/rest2_ons/training.py`)

`TrainManager.train_plant()` processa uma usina: ajusta os parâmetros na
janela de treino e avalia nas janelas de validação e de teste.

| Símbolo                       | Descrição                                  |
| ----------------------------- | ------------------------------------------ |
| `TrainManager.train_plant()`  | Ajusta e avalia uma usina                  |
| `TrainManager._train_rest2()` | Executa a otimização L-BFGS-B              |
| `TrainManager._evaluate_rest2()` | Calcula ME, MAE e RMSE de uma janela    |
| `PlantResult`                 | Resultado de treino, validação e teste     |

#### Algoritmo de Otimização

Para cada usina, otimiza parâmetros para minimizar RMSE:

```
minimizar: RMSE(medido, REST2(params, dados_atmosfericos))

Método: L-BFGS-B (BFGS de memória limitada com limites)
Parâmetros:
  - mu0: deslocamento do cosseno efetivo de nuvens, em [cos 85° - 0.5, 0.5]
  - g: parâmetro de assimetria de nuvens, em [0, 1]
```

### 7. Inferência (`src/rest2_ons/inference.py`)

O gerenciador de inferência aplica o artefato de uma usina para prever a
janela configurada.

| Símbolo           | Descrição                                           |
| ----------------- | --------------------------------------------------- |
| `predict_plant()` | Método do gerenciador: prevê a janela de uma usina  |
| `PlantResult`     | Previsão de uma usina; `chosen_radiation()` seleciona o tipo configurado |

### 8. Modelo REST2 (`src/rest2_ons/services/`)

`radiation.py` implementa o modelo de radiação solar REST2 na classe `REST2`:
`REST2.train()` ajusta os parâmetros, `REST2.evaluate()` aplica-os a uma
janela e `REST2.convert_radiation()` devolve o tipo de radiação pedido. As
métricas ME, MAE e RMSE vêm de `nwp_core.metrics.skill`.

#### Componentes do Modelo REST2

```
┌─────────────────────────────────────────────────────┐
│                   MODELO REST2                       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Radiação Extraterrestre (I₀)                       │
│       │                                              │
│       ▼                                              │
│  ┌─────────────────────────────────────────────┐    │
│  │         Componentes de Transmitância         │    │
│  │  ├── Espalhamento Rayleigh (TR)             │    │
│  │  ├── Extinção por Aerossóis (TA)            │    │
│  │  ├── Absorção por Ozônio (To)               │    │
│  │  ├── Absorção por Gases (Tg, Tn, Tw)        │    │
│  │  └── Transmitância de Nuvens (Tc)           │    │
│  └─────────────────────────────────────────────┘    │
│       │                                              │
│       ▼                                              │
│  ┌─────────────────────────────────────────────┐    │
│  │         Componentes de Radiação              │    │
│  │  ├── DNI = I₀ × ΠT × Tc_direct              │    │
│  │  ├── DHI = espalhado + refletido            │    │
│  │  └── GHI = DNI × cos(θz) + DHI              │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 9. Utilitários (`src/rest2_ons/utils/`)

| Módulo       | Descrição                                                    |
| ------------ | ------------------------------------------------------------ |
| `plots.py`   | Geração de gráficos interativos com Plotly                   |
| `data.py`    | `PlantArtifact` (formato do artefato) e coordenadas da usina |
| `utils.py`   | Geometria solar: `haversine_distance()` e `extraterrestrial_radiation()` |

`internal/constants.py` guarda as constantes do modelo e as cores dos gráficos.

### 10. Armazenamento (`nwp_core.storage`)

Toda leitura e escrita passa por `nwp_core.storage`, que abre um caminho local
absoluto ou uma URI `s3://`. As regras dos locais e a variável de ambiente de
cada campo estão no [README.md](README.md). As chaves por usina são compostas
em `src/rest2_ons/_keys.py`.

### 11. Escrita de Resultados (`src/rest2_ons/writers.py`)

Cada função grava no `Storage` que recebe e devolve os recibos de escrita; a
API soma os bytes e os artefatos gravados no item da usina.

| Símbolo                          | Descrição                                   |
| -------------------------------- | ------------------------------------------- |
| `write_plant_artifact()`         | Salva os parâmetros treinados em JSON       |
| `write_plant_train_plots()`      | Gera os gráficos HTML do treino             |
| `write_plant_output()`           | Exporta a previsão para Parquet             |
| `write_plant_inference_plots()`  | Gera os gráficos HTML da inferência         |

## Fluxo de Dados

### Entrada

Os arquivos do local `input`; a lista completa e as colunas estão no
[README.md](README.md#dados-de-entrada).

```
input/
├── usinas.csv                    # Metadados das usinas
├── albedo.parquet                # Albedo de superfície (CAMS)
├── cod.parquet                   # Profundidade óptica de nuvens
├── h2o.parquet                   # Vapor d'água (CAMS)
├── no2.parquet                   # Dióxido de nitrogênio (CAMS)
├── o3.parquet                    # Ozônio (CAMS)
├── od550.parquet                 # AOD em 550nm (CAMS)
├── od670.parquet                 # AOD em 670nm (CAMS)
├── psurf.parquet                 # Pressão de superfície (CAMS)
├── temp.parquet                  # Temperatura (CAMS)
└── measured_irradiance.parquet   # Medições in-loco (só no treino)
```

### Processamento por usina

```
_api.py: um item de trabalho por usina
    │
    ├── check_plant_id()             → recusa um id inválido
    ├── train:  TrainManager.train_plant() → parâmetros e métricas
    │           write_plant_artifact()     → {id}.json
    ├── infer:  read_plant_artifact()      → parâmetros ajustados
    │           predict_plant()            → previsão
    │           write_plant_output()       → {id}.parquet
    └── plots:  gráficos, se plots = true
```

### Saída

```
artifact/
├── {id_usina}.json              # Parâmetros treinados + métricas
└── plots/
    └── {id_usina}_train_*.html  # Gráficos de treinamento

output/
├── {id_usina}.parquet           # Previsões
└── plots/
    └── {id_usina}_inference_*.html  # Gráficos de inferência
```

## Decisões de Design

### Por que Polars ao invés de Pandas?

- **Performance**: Mais rápido para grandes datasets (milhões de linhas)
- **Eficiência de memória**: Armazenamento colunar
- **Segurança de tipos**: Tipagem forte detecta erros cedo
- **API moderna**: Sintaxe mais limpa para operações comuns

### Por que L-BFGS-B para Otimização?

- **Eficiência**: Método Quasi-Newton, eficiente para espaços de parâmetros pequenos
- **Convergência**: Boas propriedades de convergência para funções suaves
- **Disponibilidade**: Embutido no scipy, implementação bem testada
- **Limites**: Os limites mantêm mu0 e g em suas faixas físicas

### Por que um Item de Trabalho por Usina?

- **Isolamento de falhas**: Uma usina que falha termina como `FAILED`, as outras continuam e ficam gravadas, e a execução encerra com código 3
- **Resultado por usina**: O resumo da execução lista o resultado de cada item
- **Debugging**: Mais fácil rastrear e debugar problemas por usina
- **Flexibilidade**: `plant_ids` restringe a execução a um subconjunto de usinas
- **Sequencial**: Os itens rodam em sequência; paralelizar exigiria uma mudança em `_api.py`

### Por que JSON para Artefatos?

- **Legível**: Fácil de inspecionar e debugar
- **Amigável ao versionamento**: Diffs do Git são significativos
- **Portabilidade**: Formato padrão, funciona em qualquer lugar
- **Simplicidade**: Sem dependências de formato binário

### Por que Parquet para Previsões?

- **Eficiência**: Armazenamento colunar, excelente compressão
- **Performance**: Leitura rápida, especialmente para colunas parciais
- **Schema**: Força tipos de dados e estrutura
- **Ecossistema**: Funciona com Polars, Pandas, Arrow, Spark

## Extensibilidade

### Adicionando Novo Parâmetro Atmosférico

1. Adicionar leitura em `readers.py`
2. Atualizar `LocationInputData` para incluir novo parâmetro
3. Atualizar modelo REST2 para usar novo parâmetro
4. Atualizar schema de configuração se necessário

### Adicionando Novo Tipo de Radiação

1. Adicionar cálculo em `services/radiation.py`
2. Adicionar o valor a `RadiationType` em `src/rest2_ons/_config.py`, que
   tipa tanto `target_radiation_type` quanto o campo `radiation_type` do
   artefato
3. Adicionar tratamento de saída correspondente

## Dependências

As dependências de execução e suas versões mínimas são declaradas em
`[project].dependencies` do `pyproject.toml`; esta lista registra apenas o
papel de cada uma.

```
numpy         Equações do REST2 e operações com arrays
polars        Leitura, filtragem e junção das séries de entrada
pandas        Escrita de Parquet e preparo dos dados dos gráficos
pyarrow       Motor de Parquet usado pelo pandas
scipy         Calibração dos parâmetros (L-BFGS-B)
pytz          Conversão de UTC para a hora local na geometria solar
plotly        Gráficos HTML interativos
statsmodels   Linha de tendência OLS dos gráficos de dispersão (plotly)
click         Subcomandos train e infer
pydantic      Modelos da configuração e do artefato
pydantic-core Erros de validação personalizados da configuração
nwp-core      Armazenamento, configuração, CLI, execução, logs e métricas compartilhados
```

## Considerações de Performance

### Complexidade

| Operação               | Complexidade                    |
| ---------------------- | ------------------------------- |
| Carga de dados         | O(N) onde N = número de linhas  |
| Geometria solar        | O(N) por usina                  |
| Otimização de parâmetros | O(I × N) onde I = iterações   |
| Cálculo de métricas    | O(N)                            |
| Geração de gráficos    | O(N)                            |

### Gargalos

1. **Carga de Dados**: cada arquivo de entrada é lido inteiro na memória
   (`Storage.open_read` seguido de `pl.read_parquet` ou `pl.read_csv`), dentro
   do item de cada usina, e só depois filtrado pela usina e pela janela. O
   custo cresce com o tamanho do arquivo, não com a janela pedida.
2. **Iterações de Otimização**: o L-BFGS-B parte de `REST2.DEFAULT_PARAMETERS`
   e usa as tolerâncias padrão do scipy.
3. **Geração de Gráficos**: os gráficos HTML incluem todos os pontos da série,
   então séries longas geram arquivos grandes.
