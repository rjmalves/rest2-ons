# Arquitetura do Sistema

Este documento descreve a arquitetura do `rest2-ons`, incluindo o fluxo de dados, componentes principais e decisões de design.

## Visão Geral

O sistema implementa um pipeline de processamento de dados para previsão de irradiância solar usando o modelo REST2 com parâmetros otimizados. Opera em dois modos:

1. **Train**: Otimiza parâmetros do modelo REST2 usando dados medidos históricos
2. **Inference**: Gera previsões usando parâmetros pré-treinados

## Diagrama de Fluxo

```
                              ┌─────────────────────┐
                              │   config.jsonc      │
                              │   (configuração)    │
                              └──────────┬──────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │    main.py          │
                              │  (entry point)      │
                              └──────────┬──────────┘
                                         │
                         ┌───────────────┴────────────┐
                         │                            │
                         ▼                            ▼
              ┌─────────────────────┐      ┌─────────────────────┐
              │   MODO: train       │      │   MODO: inference   │
              │   train.py          │      │   inference.py      │
              └──────────┬──────────┘      └──────────┬──────────┘
                         │                            │
    ┌────────────────────┼────────────────────────────┼──────────────────┐
    │                    │                            │                  │
    │                    ▼                            ▼                  │
    │         ┌─────────────────────┐     ┌─────────────────────┐        │
    │         │  train_plant()      │     │  predict_plant()    │        │
    │         │  (por usina)        │     │  (por usina)        │        │
    │         └──────────┬──────────┘     └──────────┬──────────┘        │
    │                    │                           │                   │
    │     ┌──────────────┴──────────────┐            │                   │
    │     │                             │            │                   │
    │     ▼                             ▼            ▼                   │
    │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
    │  │ load_data()      │  │ optimize_params()│  │ apply_rest2()    │  │
    │  │ readers.py       │  │ minim. L-BFGS-B  │  │ services/rest2   │  │
    │  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
    │           │                     │                     │            │
    │           │                     ▼                     │            │
    │           │           ┌──────────────────┐            │            │
    │           │           │  {usina}.json    │◄───────────┤            │
    │           │           │  (artefato)      │            │            │
    │           │           └──────────────────┘            │            │
    │           │                                           │            │
    │           └──────────────────┬────────────────────────┘            │
    │                              │                                     │
    │                              ▼                                     │
    │                   ┌──────────────────┐                             │
    │                   │ calculate_       │                             │
    │                   │ metrics()        │                             │
    │                   └────────┬─────────┘                             │
    │                            │                                       │
    │                            ▼                                       │
    │                   ┌──────────────────┐                             │
    │                   │ write_outputs()  │                             │
    │                   │ writers.py       │                             │
    │                   └────────┬─────────┘                             │
    │                            │                                       │
    └────────────────────────────┼───────────────────────────────────────┘
                                 │
                                 ▼
                      ┌─────────────────────┐
                      │  SAÍDA              │
                      │  ├─ {usina}.parquet │
                      │  ├─ {usina}.json    │
                      │  └─ plots/*.html    │
                      └─────────────────────┘
```

## Componentes Principais

### 1. Entry Point (`main.py`)

Ponto de entrada do sistema. Responsabilidades:

- Parsear argumentos de linha de comando
- Carregar configuração do arquivo JSONC
- Despachar para modo `train` ou `inference`
- Tratamento de erros de alto nível

### 2. Configuração (`app/internal/config.py`)

Gerencia parsing e validação do arquivo de configuração.

| Função                 | Descrição                                   |
| ---------------------- | ------------------------------------------- |
| `Config.parse()`       | Interpreta e valida configuração completa   |
| `TimeWindow.parse()`   | Parseia intervalos de tempo ISO 8601        |
| `Config.from_json()`   | Carrega configuração de arquivo JSONC       |

### 3. Leitura de Dados (`app/readers.py`)

Carrega dados de entrada de várias fontes.

```
Entrada: caminho do diretório de dados
    │
    ▼
┌─────────────────────────────────┐
│ read_usinas()                   │ → Carrega metadados das usinas (CSV)
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ for_location().build()          │ → Carrega previsões CAMS (Parquet)
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ read_measured_for_plant()       │ → Carrega medições (Parquet)
└─────────────────────────────────┘
    │
    ▼
Saída: Polars DataFrames
```

### 4. Treinamento (`app/train.py`)

Implementa o pipeline de treinamento com otimização de parâmetros.

| Função                  | Descrição                              |
| ----------------------- | -------------------------------------- |
| `TrainManager.train()`  | Orquestra treinamento para todas usinas|
| `_train_for_plant()`    | Processa uma usina                     |
| `_train_rest2()`        | Executa otimização L-BFGS-B            |
| `_evaluate_rest2()`     | Calcula ME, MAE, RMSE                  |

#### Algoritmo de Otimização

Para cada usina, otimiza parâmetros para minimizar RMSE:

```
minimizar: RMSE(medido, REST2(params, dados_atmosfericos))

Método: L-BFGS-B (BFGS de memória limitada com limites)
Parâmetros:
  - mu0: deslocamento do cosseno efetivo de nuvens, em [cos 85° - 0.5, 0.5]
  - g: parâmetro de assimetria de nuvens, em [0, 1]
```

### 5. Inferência (`app/inference.py`)

Aplica o modelo treinado para gerar previsões.

| Função                     | Descrição                              |
| -------------------------- | -------------------------------------- |
| `InferenceManager.predict()` | Orquestra inferência para todas usinas |
| `_predict_for_plant()`     | Gera previsões para uma usina          |
| `read_plant_artifacts()`   | Carrega parâmetros treinados do JSON   |

### 6. Modelo REST2 (`app/services/`)

Implementa o modelo de radiação solar REST2.

| Módulo              | Descrição                                |
| ------------------- | ---------------------------------------- |
| `radiation.py`      | Implementação principal do modelo REST2  |

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

### 7. Utilitários (`app/utils/`)

Funções utilitárias reutilizáveis.

| Módulo          | Descrição                                     |
| --------------- | --------------------------------------------- |
| `metrics.py`    | Cálculo de métricas de erro (ME, MAE, RMSE)   |
| `plots.py`      | Geração de gráficos interativos com Plotly    |
| `data.py`       | Estruturas de dados e funções auxiliares      |
| `utils.py`      | Geometria solar e conversões                  |

### 8. Abstração de Storage (`app/storage/`)

Fornece uma interface unificada para operações de arquivo entre filesystem local e AWS S3.

| Módulo       | Descrição                                        |
| ------------ | ------------------------------------------------ |
| `base.py`    | Interface abstrata `StorageBackend`              |
| `local.py`   | Implementação para filesystem local              |
| `s3.py`      | Implementação AWS S3 usando boto3/s3fs           |
| `factory.py` | `StorageFactory` para seleção automática de backend |

#### Arquitetura de Storage

```
┌─────────────────────────────────────────────────────────────┐
│                     StorageFactory                          │
│  get_storage(path) → StorageBackend                        │
└───────────────────┬─────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────────┐   ┌───────────────────┐
│   LocalBackend    │   │    S3Backend      │
│   (path: /...)    │   │   (path: s3://...)│
├───────────────────┤   ├───────────────────┤
│ read_parquet()    │   │ read_parquet()    │
│ write_parquet()   │   │ write_parquet()   │
│ read_bytes()      │   │ read_bytes()      │
│ write_bytes()     │   │ write_bytes()     │
│ exists()          │   │ exists()          │
│ makedirs()        │   │ makedirs()        │
│ list_files()      │   │ list_files()      │
│ delete()          │   │ delete()          │
│ join_path()       │   │ join_path()       │
│ get_uri()         │   │ get_uri()         │
└───────────────────┘   └───────────────────┘
```

A factory seleciona automaticamente o backend apropriado baseado no prefixo do caminho:
- Caminhos começando com `s3://` usam `S3Backend`
- Todos os outros caminhos usam `LocalBackend`

### 9. Escrita de Resultados (`app/writers.py`)

Exporta resultados em vários formatos.

| Função                       | Descrição                              |
| ---------------------------- | -------------------------------------- |
| `write_plant_artifacts()`    | Salva parâmetros treinados em JSON     |
| `write_inference_results()`  | Exporta previsões para Parquet         |
| `write_plant_train_plots()`  | Gera gráficos HTML de visualização     |

## Fluxo de Dados

### Entrada

```
data/input/
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
└── measured_irradiance.parquet   # Medições in-loco
```

### Processamento Interno

```
readers.py
    │
    ├── read_usinas() → pl.DataFrame
    ├── for_location().build() → LocationInputData
    └── read_measured_for_plant() → pl.DataFrame
```

### Saída

```
data/artifacts/
├── {id_usina}.json              # Parâmetros treinados + métricas
└── plots/
    └── {id_usina}_*.html        # Gráficos de treinamento

data/output/
├── {id_usina}.parquet           # Previsões
└── plots/
    └── {id_usina}_*.html        # Gráficos de inferência
```

## Decisões de Design

### Por que Polars ao invés de Pandas?

- **Performance**: Mais rápido para grandes datasets (milhões de linhas)
- **Eficiência de memória**: Avaliação lazy e armazenamento colunar
- **Segurança de tipos**: Tipagem forte detecta erros cedo
- **API moderna**: Sintaxe mais limpa para operações comuns

### Por que L-BFGS-B para Otimização?

- **Eficiência**: Método Quasi-Newton, eficiente para espaços de parâmetros pequenos
- **Convergência**: Boas propriedades de convergência para funções suaves
- **Disponibilidade**: Embutido no scipy, implementação bem testada
- **Limites**: Os limites mantêm mu0 e g em suas faixas físicas

### Por que Processar Usinas Individualmente?

- **Paralelização**: Trivial de paralelizar com multiprocessing
- **Isolamento de falhas**: Erro em uma usina não afeta outras
- **Debugging**: Mais fácil rastrear e debugar problemas por usina
- **Flexibilidade**: Diferentes usinas podem ter configurações diferentes

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
2. Atualizar enum `target_radiation_type` na config
3. Adicionar tratamento de saída correspondente

### Adicionando Novo Algoritmo de Otimização

1. Criar novo otimizador em `train.py`
2. Adicionar opção de configuração para seleção de otimizador
3. Implementar interface comum para otimização de parâmetros

## Dependências

As dependências de execução e suas versões mínimas são declaradas em
`[project].dependencies` do `pyproject.toml`; esta lista registra apenas o
papel de cada uma.

```
numpy        Equações do REST2 e operações com arrays
polars       Leitura, filtragem e junção das séries de entrada
pandas       Escrita de Parquet e preparo dos dados dos gráficos
pyarrow      Motor de Parquet usado pelo pandas
scipy        Calibração dos parâmetros (L-BFGS-B)
pytz         Conversão de UTC para a hora local na geometria solar
pyjson5      Configuração JSONC e artefatos de parâmetros calibrados
plotly       Gráficos HTML interativos
statsmodels  Linha de tendência OLS dos gráficos de dispersão (plotly)
boto3        Cliente S3
botocore     Erros do cliente S3
s3fs         Sistema de arquivos S3 para Polars e Pandas
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

1. **Carga de Dados**: Arquivos Parquet grandes podem ser lentos
   - Mitigação: Usar predicate pushdown, seleção de colunas
2. **Iterações de Otimização**: L-BFGS-B pode requerer muitas iterações
   - Mitigação: Bons valores iniciais, tolerância de convergência
3. **Geração de Gráficos**: Grandes datasets criam arquivos HTML pesados
   - Mitigação: Downsample para visualização

### Otimizações Futuras

- Processamento paralelo de usinas com multiprocessing
- Avaliação lazy para transformações de dados
- Cache de resultados intermediários
- Processamento streaming para datasets muito grandes
