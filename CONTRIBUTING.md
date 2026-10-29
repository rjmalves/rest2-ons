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
uv sync --extra dev

# Ou com pip tradicional
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

O `uv.lock` é versionado, então `uv sync` reproduz o ambiente do CI.

Instale o hook de pre-commit para rodar, antes de cada commit, os mesmos
passos de lint, tipos e gates do CI:

```bash
ln -sf ../../scripts/pre-commit .git/hooks/pre-commit
```

O `.git-blame-ignore-revs` lista commits que só mudam o layout do código; o
GitHub os ignora no blame, e
`git config blame.ignoreRevsFile .git-blame-ignore-revs` faz o mesmo
localmente.

### Verificando a Instalação

```bash
uv run pytest   # Testes
make check      # Lint, formatação, tipos e gates (o mesmo que o hook)
```

---

## 📐 Padrões de Código

### Estilo

Seguimos as convenções PEP 8 com algumas customizações definidas em `pyproject.toml`.

### Executando as Verificações

```bash
uv run pytest --cov=app                               # testes, com o piso de cobertura
uv run ruff check . && uv run ruff format --check .   # lint e formatação, árvore inteira
uv run mypy app main.py tests scripts/ci              # tipos (strict, via pyproject.toml)
uv run python scripts/ci/check_no_plan_leaks.py       # sem vocabulário de planejamento nos artefatos publicados
uv run python scripts/ci/check_comment_refs.py        # sem referências frágeis na prosa do código
uv run python scripts/ci/check_doc_paths.py           # todo caminho citado nos docs existe
uv run ruff format .                                  # formata o código
```

O CI (`.github/workflows/ci.yml`) roda o ruff, a checagem de formatação e os
gates de `scripts/ci/` uma vez, e a checagem de tipos e os testes em cada
versão de Python suportada. Os testes falham abaixo do piso de cobertura definido em
`pyproject.toml` (`[tool.coverage.report]`); suba o piso quando a cobertura
subir, nunca o reduza para aprovar uma mudança. O `scripts/README.md` descreve
cada gate e os relatórios consultivos ao lado deles.

### Convenções que o CI Aplica

Os arquivos de regras em `.claude/rules/` são escritos para que um agente de
código possa segui-los, e são a referência também para pessoas. Em resumo:

- **Formatação e lint.** O `ruff format` define o layout; o `ruff check`
  aplica o conjunto de regras do `pyproject.toml`. Todo `# noqa` e
  `# type: ignore` nomeia o código e traz o motivo.
- **Comentários desligados por padrão.** Um comentário só entra se removê-lo
  permitir que um leitor competente introduza um bug ou perca um fato que vive
  fora do arquivo. Contratos de unidade, de base de tempo e de tipo de radiação
  nunca são removidos (`.claude/rules/comments.md`).
- **Sem vocabulário de planejamento nem referências frágeis** na prosa do
  código ou nos docs publicados (`.claude/rules/comments.md`,
  `.claude/rules/doc-integrity.md`).
- **Docs nunca fixam uma contagem ou versão à mão.** Declare a regra, ou fixe
  o literal com um teste.
- **Timestamps são naive e significam UTC.** A regra `DTZ` do ruff vale em
  `app/` e `main.py`; os testes e os scripts de preparação de dados ficam de
  fora porque constroem datas naive de propósito.
- **Mensagens do CLI passam pelo `logging`**, nunca por `print` (regra `T20`
  do ruff).

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

    Otimiza os parâmetros mu0 e g usando minimização L-BFGS-B com limites
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
- O CI falha abaixo do piso de cobertura definido em `pyproject.toml`
- As regras completas estão em `.claude/rules/testing.md`

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
   make check      # Lint, formatação, tipos e gates
   uv run pytest   # Testes, com o piso de cobertura
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
- CI deve passar (testes, lint, formatação, tipos e gates)
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
