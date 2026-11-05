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

- Python na faixa de `requires-python` do `pyproject.toml`
- [uv](https://github.com/astral-sh/uv) na versão de `[tool.uv] required-version`
  do `pyproject.toml` ou superior
- Git, com acesso de leitura ao repositório do nwp-core no github.com

Para instalar o programa como usuário, as rotas de instalação e os códigos de
saída estão no [README.md](README.md).

### Setup Inicial

```bash
# Clone seu fork
git clone https://github.com/SEU_USUARIO/rest2-ons.git
cd rest2-ons

# Adicione o upstream
git remote add upstream https://github.com/rjmalves/rest2-ons.git

# Instale as dependências
uv sync
```

O `uv sync` busca o nwp-core na sua fonte git, por isso exige o acesso de
leitura dos pré-requisitos. O `uv.lock` é versionado, então `uv sync`
reproduz o ambiente do CI.

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
uv run pytest --cov                                  # testes, com o piso de cobertura
uv run ruff check . && uv run ruff format --check .   # lint e formatação, árvore inteira
uv run mypy                                          # tipos (strict, caminhos via pyproject.toml)
uv run python scripts/ci/check_no_plan_leaks.py       # sem vocabulário de planejamento nos artefatos publicados
uv run python scripts/ci/check_comment_refs.py        # sem referências frágeis na prosa do código
uv run python scripts/ci/check_doc_paths.py           # todo caminho citado nos docs existe
uv run ruff format .                                  # formata o código
```

O CI tem dois workflows:

- `.github/workflows/ci.yml` é a cópia do template do nwp-core e só muda no
  ponto de edição `IMPORT_CHAIN`.
- `.github/workflows/repo-checks.yml` traz as verificações deste repositório:
  os gates de `scripts/ci/`, o `pytest --cov` em cada versão de Python
  suportada com envio ao Codecov, o gate de `ci/gate/` com a lista de nomes
  proibidos obrigatória, o diff da API, as listas de arquivos do pacote, a
  instalação pelo `setup.sh` e a varredura do `uv.lock` pelo osv-scanner em
  busca de vulnerabilidades publicadas. O Dependabot não atualiza o `uv.lock`;
  quando a varredura acusar um pacote, atualize-o com
  `uv lock -P 'pacote==versão'` para uma versão que corrija o aviso.

Os testes falham abaixo do piso de cobertura definido em `pyproject.toml`
(`[tool.coverage.report]`); suba o piso quando a cobertura subir, nunca o
reduza para aprovar uma mudança. O `scripts/README.md` descreve cada gate e os
relatórios consultivos ao lado deles.

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
  `src/rest2_ons`; os testes ficam de fora porque constroem datas naive de
  propósito.
- **Mensagens do CLI passam pelo `logging`**, nunca por `print` (regra `T20`
  do ruff).
- **Dependências de execução batem com os imports.** Todo pacote importado
  por `src/rest2_ons` está em `[project].dependencies`, e todo pacote
  declarado ali é importado pela aplicação ou listado em `LAZILY_IMPORTED`
  (`tests/unit/test_declared_dependencies.py`), quando uma biblioteca o
  importa por conta própria. Ferramentas de desenvolvimento vão no grupo de
  dependências `dev` (`[dependency-groups]`).

### Cópias de template

`.github/workflows/ci.yml`, `Dockerfile`, `.dockerignore` e os arquivos de
`ci/` são cópias de templates do nwp-core. Cada cópia só muda no seu ponto de
edição; qualquer outra mudança vem de uma nova cópia do template.

A cada nova cópia, rode o verificador e coloque a saída no pull request:

```bash
uv run python scripts/ci/check_template_copies.py <checkout do nwp-core>
```

Ele compara cada cópia com o template da tag do nwp-core e sai com 0 quando
todas conformam. Ele roda só localmente, nunca no CI, porque o CI não lê o
repositório privado do nwp-core.

### Dependabot

O Dependabot (`.github/dependabot.yml`) abre pull requests só para os
ecossistemas `github-actions` e `docker`. Uma execução do Dependabot não recebe
os segredos do repositório, então o CI dela não prova a instalação nem o gate
completo. Para verificar, um mantenedor envia um commit vazio à branch do
Dependabot e faz o merge à mão:

```bash
git fetch origin <branch do dependabot>
git checkout <branch do dependabot>
git commit --allow-empty -m "chore: verifica o pull request do Dependabot"
git push origin <branch do dependabot>
```

O `uv.lock` não tem atualização automática; atualize-o à mão.

### Boas Práticas Python

Seguimos os princípios de código limpo e tipagem estática:

#### 1. Type Hints Obrigatórios

```python
# ✅ Bom: função com type hints completos
def calcular_mae(observado: np.ndarray, previsto: np.ndarray) -> float:
    """Calcula o erro médio absoluto."""
    return float(np.mean(np.abs(observado - previsto)))


# ❌ Evitar: funções sem type hints
def calcular_mae(observado, previsto):
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
├── conftest.py     # Fixtures e auxiliares compartilhados (local_storage)
├── fixtures/       # Dados sintéticos de teste e o gerador deles
├── unit/           # Componentes isolados e os scripts de scripts/ci/
├── integration/    # Pipeline completo, backends de entrada e saída, golden
└── surface/        # Snapshots JSON da superfície pública
```

`tests/surface/` guarda os snapshots JSON dos esquemas de configuração, do
artefato e do resumo da execução, e da superfície do CLI. Com
`NWP_UPDATE_SNAPSHOTS=1`, o teste reescreve o snapshot e ainda assim falha,
para que a mudança seja revisada no diff antes de entrar.

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
pytest --cov --cov-report=html  # Com cobertura
pytest -v                        # Saída verbosa
pytest -m "not slow"             # Pular testes lentos
pytest -m s3                     # Apenas testes S3
```

### Categorias de Testes (Markers)

Testes são categorizados usando markers do pytest:

| Marker                     | Descrição                                     |
| -------------------------- | --------------------------------------------- |
| `@pytest.mark.unit`        | Testes unitários para componentes individuais |
| `@pytest.mark.integration` | Testes de integração do pipeline completo     |
| `@pytest.mark.slow`        | Testes que demoram para executar              |
| `@pytest.mark.s3`          | Testes que requerem simulação S3/moto         |
| `@pytest.mark.plotting`    | Testes que geram gráficos                     |

### Escrevendo Testes

Leituras locais usam `local_storage(tmp_path)` de `tests/conftest.py`:

```python
from datetime import UTC, datetime

import polars as pl
from nwp_core.config import TimeWindow

from rest2_ons.readers import InputData
from tests.conftest import local_storage


def test_reads_measured_irradiance_of_one_plant(tmp_path):
    """Lê só as linhas da usina pedida, dentro da janela."""
    pl.DataFrame(
        {
            "id_usina": ["P1", "P1", "P2"],
            "data_hora_observacao": [
                datetime(2024, 1, 15, 12, 0),
                datetime(2024, 1, 15, 12, 10),
                datetime(2024, 1, 15, 12, 0),
            ],
            "valor": [500.0, 520.0, 300.0],
        }
    ).write_parquet(tmp_path / "measured_irradiance.parquet")
    window = TimeWindow(
        start=datetime(2024, 1, 15, 12, 0, tzinfo=UTC),
        end=datetime(2024, 1, 15, 12, 20, tzinfo=UTC),
    )

    reader = InputData(local_storage(tmp_path))
    result = reader.read_measured_for_plant("P1", window)

    assert result["valor"].to_list() == [500.0, 520.0]
```

### Fixtures

Fixtures comuns são definidas em `tests/conftest.py`. Os testes de S3 usam
`isolate_aws_env` e `moto_location()` de `nwp_core._testing.storage`, com
`@pytest.mark.s3`:

```python
import pytest
from nwp_core._testing.storage import isolate_aws_env, moto_location

from rest2_ons.readers import InputData


@pytest.mark.s3
def test_reads_from_s3(monkeypatch, tmp_path):
    isolate_aws_env(monkeypatch, tmp_path)
    with moto_location() as location:
        ...  # abra o local com open_storage e use-o como um Storage
```

### Requisitos de Cobertura

- Novas funções públicas devem ter testes
- Casos de borda (NaN, vazios, tipos errados) devem ser testados
- Testes devem ser independentes e reprodutíveis
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
   uv run pytest --cov   # Testes, com o piso de cobertura
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

Atualize o `src/rest2_ons/_version.py` e `CHANGELOG.md` ao lançar versões; um teste confere que a versão do pacote é a última lançada no changelog.

Uma mudança incompatível entra em `### Breaking` na seção `## [Unreleased]` do
`CHANGELOG.md`. O `scripts/ci/check_api_diff.py` falha quando um nome sai de
`rest2_ons.__all__` desde a última tag `v*` sem um item da forma
``- `rest2_ons.<nome>` `` em `### Breaking`:

```bash
uv run python scripts/ci/check_api_diff.py
```

As tags são criadas por um mantenedor na `main`, depois do merge.

---

## ❓ Dúvidas?

- Abra uma [Discussion](https://github.com/rjmalves/rest2-ons/discussions) para perguntas gerais
- Use [Issues](https://github.com/rjmalves/rest2-ons/issues) para bugs e features
- Consulte a documentação existente

Obrigado por contribuir! 🎉
