# rest2-ons

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/rjmalves/rest2-ons/actions/workflows/ci.yml/badge.svg)](https://github.com/rjmalves/rest2-ons/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Generalização ML do Modelo de Radiação Solar REST2** — Aplicação Python para previsão de irradiância solar utilizando parâmetros ajustáveis otimizados com previsões ECMWF CAMS, previsões de COD e dados medidos in-loco.

Desenvolvido pelo [Operador Nacional do Sistema Elétrico (ONS)](https://www.ons.org.br/) para uso em planejamento energético e previsão de geração solar fotovoltaica.

---

## 📋 Visão Geral

Esta aplicação implementa uma generalização por aprendizado de máquina do [modelo de radiação REST2 (Reference Evaluation of Solar Transmittance, 2-band)](https://github.com/NREL/rest2) desenvolvido pelo NREL, considerando condições de céu claro e com nebulosidade. Introduz parâmetros ajustáveis otimizados usando dados medidos in-loco, tornando-o adaptável para locais e condições específicas.

1. **Treina** modelos de regressão usando histórico de irradiância medida e previsões atmosféricas
2. **Otimiza** os parâmetros associados a adaptação do modelo REST2 para considerar a nebulosidade (`mu0`, `g`) a fim de minimizar RMSE contra dados reais
3. **Gera** previsões de irradiância solar em condições de céu claro e com nebulosidade (GHI, DNI, DHI) para operação
4. **Exporta** previsões, métricas de performance e gráficos interativos

### Casos de Uso

- Previsão de irradiância solar para o dia seguinte e mesmo dia
- Calibração de parâmetros para adaptação do modelo REST2 por usina
- Validação de modelo e benchmarking contra baselines
- Preparação de dados de treinamento para modelos de geração de potência

---

## 🏗️ Arquitetura

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              DADOS DE ENTRADA                              │
├─────────────────┬─────────────────┬──────────────────┬─────────────────────┤
│ Previsões CAMS  │ Previsões COD   │ Dados Medidos    │ Metadados Usinas    │
│ (params atm.)   │ (prof. nuvens)  │ (irradiância)    │ (usinas.csv)        │
└────────┬────────┴────────┬────────┴────────┬─────────┴──────────┬──────────┘
         │                 │                 │                    │
         ▼                 ▼                 ▼                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         MODO: TRAIN (train.py)                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │ Carga de Dados & │  │ Cálculo de       │  │ Otimização de Parâmetros │  │
│  │ Pré-processamento│→ │ Geometria Solar  │→ │ (L-BFGS-B com limites)   │  │
│  └──────────────────┘  └──────────────────┘  └───────────┬──────────────┘  │
│                                                          │                 │
│                                                          ▼                 │
│                                              ┌──────────────────────────┐  │
│                                              │ Artefato: {usina}.json   │  │
│                                              │ (mu0, g, métricas)       │  │
│                                              └──────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                        MODO: INFERENCE (inference.py)                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │ Carregar         │  │ Aplicar Modelo   │  │ Gerar Previsões          │  │
│  │ Parâmetros       │→ │ REST2 adaptado   │→ │ & Gráficos               │  │
│  └──────────────────┘  └──────────────────┘  └───────────┬──────────────┘  │
│                                                          │                 │
│                                                          ▼                 │
│                                              ┌──────────────────────────┐  │
│                                              │ Saída: {usina}.parquet   │  │
│                                              │ (time, valor)            │  │
│                                              └──────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

### Componentes Principais

| Módulo             | Descrição                                                |
| ------------------ | -------------------------------------------------------- |
| `app/train.py`     | Pipeline de treinamento com otimização L-BFGS-B com limites |
| `app/inference.py` | Pipeline de previsão usando parâmetros treinados         |
| `app/readers.py`   | Leitura de dados de arquivos Parquet/CSV                 |
| `app/writers.py`   | Geração de saídas (Parquet, JSON, gráficos HTML)         |
| `app/storage/`     | Abstração de storage (local/S3)                          |
| `app/services/`    | Implementação do modelo REST2 adaptado e geometria solar |
| `app/utils/`       | Funções utilitárias (métricas, plots, limites)           |

---

## 🚀 Quick Start

### Pré-requisitos

- Python >= 3.11
- Linux (testado em Ubuntu/Debian)

### Instalação

```bash
# Clone o repositório
git clone https://github.com/rjmalves/rest2-ons.git
cd rest2-ons

# Instale com uv (recomendado)
uv sync

# Ou com pip tradicional
python -m venv venv
source venv/bin/activate
pip install -e .
```

### Execução Rápida

```bash
# 1. Prepare o arquivo de configuração
cp config.example.jsonc config.jsonc
# Edite config.jsonc com seus parâmetros

# 2. Prepare dados de entrada em data/input/

# 3. Treine o modelo
rest2-ons --config config.jsonc  # com mode: "train"

# 4. Altere o mode para "inference" e execute previsões
rest2-ons --config config.jsonc  # com mode: "inference"
```

### Usando Docker

```bash
# Build da imagem
docker build -t rest2-ons .

# Execução com volumes montados
docker run -v $(pwd)/data:/app/data -v $(pwd)/config.jsonc:/app/config.jsonc \
  rest2-ons --config /app/config.jsonc
```

---

## 📖 Uso Detalhado

### Linha de Comando

```bash
rest2-ons --config <ARQUIVO_CONFIG>
rest2-ons --help
```

| Argumento  | Descrição                                  | Default     |
| ---------- | ------------------------------------------ | ----------- |
| `--config` | Caminho para arquivo de configuração JSONC | Obrigatório |

### Arquivo de Configuração (`config.jsonc`)

```jsonc
{
  // Modo de execução: "train" ou "inference"
  "mode": "train",

  // Caminhos de entrada/saída (local ou s3://)
  "input": "data/input",
  "output": "data/output",
  "artifact": "data/artifacts",

  // IDs das usinas a processar (null = todas em usinas.csv)
  "plant_ids": ["BAFJS7"],

  // Horizonte de previsão em dias (0 = mesmo dia)
  "forecasting_day_ahead": 0,

  // Tipo de radiação alvo: "ghi", "dni", "dhi", "ghi_tracker"
  "target_radiation_type": "dni",

  // Janelas temporais (formato ISO 8601: início/fim)
  "time_windows": {
    "training": "2024-01-01T00:00:00/2024-03-01T00:00:00",
    "validation": "2024-03-01T00:00:00/2024-04-01T00:00:00",
    "test": "2024-04-01T00:00:00/2024-05-01T00:00:00",
    "inference": "2024-05-01T00:00:00/2024-06-01T00:00:00"
  },

  // Opções de pós-processamento
  "postprocessing": {
    "plots": true
  }
}
```

### Variáveis de Ambiente (S3)

```bash
# Para uso com S3
export AWS_ACCESS_KEY_ID="sua-access-key"
export AWS_SECRET_ACCESS_KEY="sua-secret-key"
export AWS_DEFAULT_REGION="us-east-1"

rest2-ons --config config.jsonc
```

---

## 📁 Dados de Entrada

O diretório de entrada deve conter os seguintes arquivos:

| Arquivo                       | Formato | Descrição                                 |
| ----------------------------- | ------- | ----------------------------------------- |
| `usinas.csv`                  | CSV     | Metadados das usinas (id, lat, lon)       |
| `albedo.parquet`              | Parquet | Previsão de albedo de superfície (CAMS)   |
| `cod.parquet`                 | Parquet | Previsão de profundidade óptica de nuvens |
| `h2o.parquet`                 | Parquet | Previsão de vapor d'água (CAMS)           |
| `no2.parquet`                 | Parquet | Previsão de dióxido de nitrogênio (CAMS)  |
| `o3.parquet`                  | Parquet | Previsão de ozônio (CAMS)                 |
| `od550.parquet`               | Parquet | Profundidade óptica de aerossóis 550nm    |
| `od670.parquet`               | Parquet | Profundidade óptica de aerossóis 670nm    |
| `psurf.parquet`               | Parquet | Previsão de pressão de superfície (CAMS)  |
| `temp.parquet`                | Parquet | Previsão de temperatura 2m (CAMS)         |
| `measured_irradiance.parquet` | Parquet | Medições de irradiância in-loco           |

### Schemas de Dados

#### `usinas.csv`

```csv
id_usina,latitude,longitude
BAFJS7,-23.5,-46.5
```

#### Dados de previsão (Parquet)

```
latitude,longitude,data_hora_rodada,data_hora_previsao,valor
-23.5,-46.5,2024-01-01T00:00:00,2024-01-01T12:00:00,0.85
```

#### Dados medidos (Parquet)

```
id_usina,data_hora_observacao,valor
BAFJS7,2024-01-01T12:00:00,850.5
```

---

## 📊 Saídas

### Modo Training

| Saída            | Localização       | Descrição                           |
| ---------------- | ----------------- | ----------------------------------- |
| `{usina}.json`   | `artifact/`       | Parâmetros treinados e métricas     |
| `{usina}_*.html` | `artifact/plots/` | Gráficos interativos de treinamento |

#### Schema do Artefato JSON

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

### Modo Inference

| Saída             | Localização     | Descrição                        |
| ----------------- | --------------- | -------------------------------- |
| `{usina}.parquet` | `output/`       | Previsões (time, valor)          |
| `{usina}_*.html`  | `output/plots/` | Gráficos interativos de previsão |

---

## 🔬 Metodologia

O modelo REST2 divide o espectro solar em duas bandas e calcula a transmitância atmosférica através de múltiplos processos físicos (espalhamento Rayleigh, extinção por aerossóis, absorção por gases, efeitos de nuvens).

**Inovação Principal**: Esta implementação considera uma adaptação do modelo REST2 para gerar previsões de irradiância em condições de nebulosidade, e otimiza dois parâmetros de tal adaptação:

- **mu0**: Deslocamento do cosseno efetivo de nuvens em `exp(-cod / (0.5 + mu0))`, limitado a [cos 85° - 0.5, 0.5]; quanto maior o mu0, menor a atenuação por nuvens
- **g**: Parâmetro de assimetria de nuvens na transmitância difusa de nuvens, limitado a [0, 1]

A otimização usa L-BFGS-B com limites físicos para minimizar o RMSE contra dados medidos.

Para metodologia detalhada, veja [METHODOLOGY.md](METHODOLOGY.md).

---

## ⚠️ Limitações Conhecidas

- **Resolução Temporal**: Otimizado para dados horários a sub-horários
- **Resolução Espacial**: Modelo pontual, não para médias de grandes áreas
- **Tratamento de Nuvens**: Simplificado (apenas profundidade óptica)
- **Efeitos de Terreno**: Não considera sombreamento topográfico
- **Requisitos de Dados**: Requer todos os parâmetros atmosféricos e de concentração de gases, que podem ser obtidos do sistema/modelo europeu CAMS/ECMWF

---

## 🧪 Testes

```bash
# Executar todos os testes
make test

# Apenas testes unitários
make test-unit

# Apenas testes de integração
make test-integration

# Com cobertura
make test-cov

# Testes específicos de S3 (requer moto)
make test-s3

# Linting
make lint

# Formatação
make format

# Ou usando pytest diretamente:
pytest
pytest --cov=app

# Type checking
mypy app/
```

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor, leia o [CONTRIBUTING.md](CONTRIBUTING.md) para detalhes sobre:

- Configuração do ambiente de desenvolvimento
- Padrões de código e linting
- Processo de submissão de Pull Requests

---

## 📜 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## 📚 Documentação Adicional

- [METHODOLOGY.md](METHODOLOGY.md) - Detalhes técnicos do modelo REST2 e otimização
- [ARCHITECTURE.md](ARCHITECTURE.md) - Arquitetura do sistema e decisões de design
- [CONTRIBUTING.md](CONTRIBUTING.md) - Guia de contribuição
- [CHANGELOG.md](CHANGELOG.md) - Histórico de versões

---

## 📞 Contato

- **Organização**: [ONS - Operador Nacional do Sistema Elétrico](https://www.ons.org.br/)
- **Issues**: [GitHub Issues](https://github.com/rjmalves/rest2-ons/issues)

---

## Referências

- Gueymard, C. A. (2008). REST2: High-performance solar radiation model for cloudless-sky irradiance, illuminance, and photosynthetically active radiation. _Solar Energy_, 82(3), 272-285.
- [NREL REST2 Implementation](https://github.com/NREL/rest2)

## Citação

```bibtex
@software{rest2ons2025,
  author = {Cossich, William and Alves, Rogério},
  title = {rest2-ons: Generalização ML do Modelo de Radiação Solar REST2},
  year = {2025},
  url = {https://github.com/rjmalves/rest2-ons}
}
```
