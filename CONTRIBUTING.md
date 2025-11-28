# Contribuindo para o rest2-ons

Obrigado pelo interesse em contribuir! Este documento fornece diretrizes para contribuições ao projeto.

## 📋 Índice

- [Como Contribuir](#como-contribuir)
- [Configuração do Ambiente](#configuração-do-ambiente)
- [Padrões de Código](#padrões-de-código)
- [Testes](#testes)
- [Documentação](#documentação)
- [Processo de Pull Request](#processo-de-pull-request)

---

## 🤝 Como Contribuir

### Reportando Bugs

1. Verifique se o bug já não foi reportado nas [Issues](https://github.com/rjmalves/rest2-ons/issues)
2. Se não encontrar, crie uma nova issue usando o template de bug report
3. Inclua:
   - Descrição clara do problema
   - Passos para reproduzir
   - Comportamento esperado vs. observado
   - Versão do Python e do pacote
   - Logs de erro (se aplicável)

### Sugerindo Melhorias

1. Abra uma issue usando o template de feature request
2. Descreva:
   - O problema que a melhoria resolve
   - A solução proposta
   - Alternativas consideradas

### Contribuindo com Código

1. Fork o repositório
2. Crie uma branch para sua feature (`git checkout -b feature/minha-feature`)
3. Faça commits atômicos com mensagens descritivas
4. Escreva/atualize testes para suas mudanças
5. Garanta que todos os testes passam
6. Abra um Pull Request

---

## 🛠️ Configuração do Ambiente

### Pré-requisitos

- Python >= 3.11
- [uv](https://github.com/astral-sh/uv) (gerenciador de pacotes recomendado)
- Git

### Setup Inicial

```bash
# Clone seu fork
git clone https://github.com/SEU_USUARIO/rest2-ons.git
cd rest2-ons

# Adicione o upstream
git remote add upstream https://github.com/rjmalves/rest2-ons.git

# Instale as dependências com uv
uv sync --all-extras --dev

# Ou com pip tradicional
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### Verificando a Instalação

```bash
# Executar testes
uv run pytest tests/

# Verificar linting
uv run ruff check app/ tests/

# Verificar tipos
uv run mypy app/
```

---

## 📐 Padrões de Código

### Estilo

Seguimos as convenções PEP 8 com algumas customizações definidas em `pyproject.toml`.

### Verificação de Estilo

```bash
# Executar linter
uv run ruff check app/ tests/

# Formatar código automaticamente
uv run ruff format app/ tests/

# Verificar formatação sem modificar
uv run ruff format --check app/ tests/
```

### Boas Práticas Python

Seguimos os princípios de código limpo e tipagem estática:

#### 1. Type Hints Obrigatórios

```python
# ✅ Bom: função com type hints completos
def calcular_rmse(observado: np.ndarray, previsto: np.ndarray) -> float:
    """Calcula o erro médio absoluto."""
    return float(np.mean(np.abs(observado - previsto)))

# ❌ Evitar: funções sem type hints
def calcular_rmse(observado, previsto):
    return np.mean(np.abs(observado - previsto))
```

#### 2. Docstrings Claras

```python
# ✅ Bom: docstring informativa
def train_plant(plant_id: str, data: pl.DataFrame) -> TrainResult:
    """
    Treina parâmetros do modelo REST2 para uma usina.

    Otimiza os parâmetros mu0 e g usando minimização BFGS
    para minimizar o RMSE contra dados medidos de irradiância.

    Args:
        plant_id: Identificador único da usina.
        data: DataFrame com parâmetros atmosféricos e valores medidos.

    Returns:
        TrainResult contendo parâmetros otimizados e métricas.

    Raises:
        ValueError: Se plant_id não for encontrado nos dados.
    """
    ...
```

#### 3. Validação de Entrada

```python
# ✅ Bom: validar tipos e valores
def processar_dados(df: pl.DataFrame, coluna: str) -> pl.DataFrame:
    if coluna not in df.columns:
        raise ValueError(f"Coluna '{coluna}' não encontrada no DataFrame")
    # ...
```

#### 4. Evitar Efeitos Colaterais

```python
# ✅ Bom: função pura
def normalizar(valores: np.ndarray) -> np.ndarray:
    return (valores - valores.min()) / (valores.max() - valores.min())

# ❌ Evitar: modificar entrada in-place sem documentar
def normalizar(valores: np.ndarray) -> None:
    valores[:] = (valores - valores.min()) / (valores.max() - valores.min())
```

---

## 🧪 Testes

### Estrutura de Testes

```
tests/
├── __init__.py
├── conftest.py              # Fixtures compartilhadas e configuração pytest
├── fixtures/
│   ├── data/                # Arquivos de dados de teste
│   └── generate_test_data.py  # Gerador de dados mock
├── unit/
│   ├── test_config.py       # Testes de configuração
│   ├── test_readers.py      # Testes de leitura de dados
│   └── test_storage.py      # Testes de backends de storage
└── integration/
    └── test_pipeline.py     # Testes de integração do pipeline
```

### Executando Testes

```bash
# Usando Makefile (recomendado)
make test              # Todos os testes
make test-unit         # Apenas testes unitários
make test-integration  # Apenas testes de integração
make test-cov          # Com relatório de cobertura
make test-s3           # Testes específicos de S3 (requer moto)

# Ou usando pytest diretamente
pytest                           # Todos os testes
pytest tests/unit/               # Testes unitários
pytest tests/integration/        # Testes de integração
pytest --cov=app --cov-report=html  # Com cobertura
pytest -v                        # Saída verbosa
pytest -m "not slow"             # Pular testes lentos
pytest -m s3                     # Apenas testes S3
```

### Categorias de Testes (Markers)

Testes são categorizados usando markers do pytest:

| Marker        | Descrição                                   |
| ------------- | ------------------------------------------- |
| `@pytest.mark.unit`        | Testes unitários para componentes individuais |
| `@pytest.mark.integration` | Testes de integração do pipeline completo   |
| `@pytest.mark.slow`        | Testes que demoram para executar            |
| `@pytest.mark.s3`          | Testes que requerem simulação S3/moto       |
| `@pytest.mark.plotting`    | Testes que geram gráficos                   |

### Escrevendo Testes

```python
import pytest
from app.readers import InputData

class TestInputData:
    """Testa a classe InputData."""

    def test_initialization(self):
        """Testa inicialização do InputData."""
        reader = InputData("data/input")
        assert reader.path == "data/input"

    def test_initialization_with_s3(self):
        """Testa inicialização do InputData com caminho S3."""
        reader = InputData("s3://bucket/input")
        assert reader.path == "s3://bucket/input"

    @pytest.mark.integration
    def test_reads_parquet_files(self, tmp_path, sample_atmospheric_data):
        """Testa leitura de arquivos parquet (teste de integração)."""
        # Write test data
        test_file = tmp_path / "test.parquet"
        sample_atmospheric_data.write_parquet(test_file)

        reader = InputData(str(tmp_path))
        result = reader._read("test.parquet", {})

        assert len(result) == len(sample_atmospheric_data)
```

### Fixtures

Fixtures comuns são definidas em `tests/conftest.py`:

```python
@pytest.fixture
def sample_atmospheric_data():
    """Cria dados atmosféricos sintéticos para testes."""
    # Retorna polars DataFrame com dados mock
    ...

@pytest.fixture
def mock_s3_bucket():
    """Cria um bucket S3 mock usando moto."""
    # Requer moto instalado
    ...
```

### Requisitos de Cobertura

- Novas funções públicas devem ter testes
- Casos de borda (NaN, vazios, tipos errados) devem ser testados
- Testes devem ser independentes e reprodutíveis
- Meta: >80% de cobertura para código novo

---

## 📝 Documentação

### Docstrings

Todas as funções e classes públicas devem ter documentação completa:

```python
class REST2:
    """
    Modelo de radiação solar REST2 com parâmetros otimizáveis.

    Esta classe implementa o modelo REST2 (Reference Evaluation of
    Solar Transmittance, 2-band) com parâmetros ajustáveis para
    calibração com dados medidos in-loco.

    Attributes:
        location_data: Dados atmosféricos para o local.
        parameters: Parâmetros otimizados (mu0, g).

    Example:
        >>> location_data = reader.for_location(lat, lon).build()
        >>> rest2 = REST2(location_data)
        >>> params = rest2.train(measured_data, "dni")
    """
```

### Atualizando Documentação

- Atualize o README se adicionar funcionalidades visíveis ao usuário
- Atualize ARCHITECTURE.md se modificar a estrutura do sistema
- Atualize CHANGELOG.md para mudanças relevantes

---

## 🔄 Processo de Pull Request

### Antes de Abrir o PR

1. **Sincronize com upstream**

   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Execute verificações locais**

   ```bash
   uv run ruff check app/ tests/     # Linting
   uv run ruff format app/ tests/    # Formatação
   uv run mypy app/                  # Type checking
   uv run pytest tests/              # Testes
   ```

3. **Commits organizados**
   - Mensagens descritivas em português ou inglês
   - Um commit por mudança lógica
   - Formato: `tipo: descrição curta`
     - `feat:` nova funcionalidade
     - `fix:` correção de bug
     - `docs:` documentação
     - `test:` testes
     - `refactor:` refatoração

### Template do PR

```markdown
## Descrição

Breve descrição das mudanças.

## Tipo de Mudança

- [ ] Bug fix
- [ ] Nova feature
- [ ] Breaking change
- [ ] Documentação

## Checklist

- [ ] Testes adicionados/atualizados
- [ ] Documentação atualizada
- [ ] CI passa sem erros
- [ ] Código segue os padrões do projeto

## Issues Relacionadas

Closes #123
```

### Revisão

- PRs requerem pelo menos 1 aprovação
- CI deve passar (testes, lint, type check)
- Discussões devem ser resolvidas antes do merge

---

## 🏷️ Versionamento

Seguimos [Semantic Versioning](https://semver.org/):

- **MAJOR**: mudanças incompatíveis na API
- **MINOR**: novas funcionalidades compatíveis
- **PATCH**: correções de bugs compatíveis

Atualize o `app/__init__.py` e `CHANGELOG.md` ao lançar versões.

---

## ❓ Dúvidas?

- Abra uma [Discussion](https://github.com/rjmalves/rest2-ons/discussions) para perguntas gerais
- Use [Issues](https://github.com/rjmalves/rest2-ons/issues) para bugs e features
- Consulte a documentação existente

Obrigado por contribuir! 🎉
