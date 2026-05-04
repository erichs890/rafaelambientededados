# Agent Log — Contexto do Projeto

> Documento de handoff para outra IA assumir o projeto sem precisar reler tudo do zero.
> Última atualização: 2026-05-04

---

## 1. Visão geral

Projeto acadêmico (AV2 de Banco de Dados) que implementa um **SQL Query Studio** em Python/Tkinter. A aplicação:

1. Recebe uma query SQL digitada pelo usuário.
2. Executa um **tokenizer + parser próprio** (não usa biblioteca SQL).
3. Conecta no MySQL local (`bd_vendas`) e roda a query de verdade.
4. Mostra o resultado em uma `Treeview`.
5. Gera **grafos de execução de álgebra relacional** em janelas separadas, ilustrando heurísticas de otimização de consultas.

Arquivo principal: [trabalho_rafael(1)(1).py](trabalho_rafael(1)(1).py) — toda a lógica está nesse único arquivo (~1320 linhas após implementação completa).

> Documento `EXPLICACAO.md` na raiz contém o guia didático completo (alunos / leitor humano).
> Documento `Projeto 2 - Processador de Consultas 24.2.pdf` é o enunciado oficial.

---

## 2. Stack e dependências

- **Python 3.13** (há um `__pycache__` com `cpython-313`)
- **Tkinter / ttk** — UI (tema dark customizado, paleta tipo Catppuccin)
- **mysql-connector-python** — conexão com MySQL
- **networkx** — estrutura de grafo dirigido (`DiGraph`) para os planos de execução
- **re, json** — stdlib

> Não há `requirements.txt`. Instalar manualmente: `pip install mysql-connector-python networkx`.

### Credenciais MySQL (hardcoded em [trabalho_rafael(1)(1).py:445-450](trabalho_rafael(1)(1).py#L445-L450))
```
host=localhost, user=root, password=132654, database=bd_vendas
```
> ⚠️ Senha hardcoded. Não é boa prática mas é trabalho acadêmico — não "consertar" sem o usuário pedir.

---

## 3. Arquitetura do código

Arquivo único organizado em seções com comentários `# ─── ... ─────`:

| Seção | Linhas aprox. | Responsabilidade |
|---|---|---|
| Constantes de cores / SQL_KEYWORDS | 8–35 | Tema visual + lista de keywords para highlight |
| `SCHEMA` (dict) | 38–58 | Schema do `bd_vendas` para validação |
| `tokenize()` | 60–64 | Regex que quebra SQL em tokens (preserva strings entre aspas) |
| `_flatten_predicates`, `_is_literal`, `validate_against_schema` | 66–149 | Validador top-level (não-membro) usado por `_execute` e `_parse_for_graph` |
| `SQLParser` | 151–211 | Parser recursivo descendente (SELECT/FROM/INNER JOIN/ON/WHERE) |
| Histórico global | 213–215 | `QUERY_HISTORY` + `HISTORY_POS` (navegável com setas ↑/↓) |
| `SQLApp(tk.Tk)` | 218–~1300 | Classe principal — UI + todas as heurísticas |
| `_build_optimal_plan_graph` + `_show_optimal_plan_graph` | ~1042–1300 | Heurística completa (5b) — botão verde "Plano Otimizado" |
| `if __name__ == "__main__"` | final | Entry point |

### Limitações conhecidas do parser
- Só entende `SELECT ... FROM ... [INNER JOIN ... ON ...] [WHERE ...]`
- Não suporta: subqueries, `LEFT/RIGHT JOIN`, `GROUP BY`, `ORDER BY`, `LIMIT`, múltiplos JOINs, `OR` em condições (só `AND`).
- O MySQL ainda executa a query completa — o parser só serve para validar e gerar os grafos.
- Strings entre aspas SIMPLES são reconhecidas (`'Joao'`), aspas duplas não.

---

## 4. Botões da UI (o que cada um faz)

| Botão | Método | O que faz |
|---|---|---|
| **Executar** (Ctrl+Enter) | `_execute` | Parseia + **valida schema** + executa no MySQL + popula `Treeview` |
| **Limpar** | `_clear` | Limpa editor e resultados |
| **Analisar Parser** | `_show_parse_tree` | Janela com tokens coloridos + JSON da AST (não valida) |
| **Grafo Não Otimizado** | `_show_nonoptimized_graph` | Plano "ingênuo": Cartesiano → Seleção → Projeção |
| **Redução de Tuplas** | `_show_tuple_reduction_graph` | **Heurística 5a-i** — selection pushdown |
| **Redução de Atributos** | `_show_attribute_reduction_graph` | **Heurística 5a-ii** — projection pushdown |
| **Plano Otimizado** (verde) | `_show_optimal_plan_graph` | **Heurística completa 5a + 5b** — combina pushdowns + reordenação de folhas + evita cartesiano + plano textual |

---

## 5. As quatro visualizações de grafo (núcleo do trabalho)

Todas geram um `nx.DiGraph` cujos nós têm `label`, `type` (`table`/`selection`/`projection`/`join`/`cartesian`) e `order` (índice de execução bottom-up). A renderização é feita manualmente em um `tk.Canvas` — **não usa matplotlib**.

### 5.1. Grafo Não Otimizado — `_build_nonoptimized_graph` ([linhas 570-614](trabalho_rafael(1)(1).py#L570-L614))

Plano canônico ruim:
```
        π colunas
           │
        σ (todas as condições juntas)
           │
        × Produto Cartesiano
          / \
         T1  T2
```
Junta tudo no produto cartesiano antes de filtrar — pior caso pedagógico.

### 5.2. Heurística 1 — Redução de Tuplas (selection pushdown) — `_build_tuple_reduction_graph` ([linhas 748-807](trabalho_rafael(1)(1).py#L748-L807))

**Ideia:** empurrar `σ` (seleções) para o mais perto possível das tabelas, reduzindo o número de tuplas **antes** do JOIN.

Algoritmo:
1. Achata todas as condições (`_flatten_conjunction`) — só funciona com `AND`.
2. Classifica cada predicado por quantas tabelas ele referencia (`_predicate_tables` olha o prefixo `tabela.coluna`):
   - **1 tabela** → vira um `σ` separado em cima daquela tabela.
   - **>1 tabela** → vira condição de `JOIN` (substitui o produto cartesiano).
3. Monta o grafo: `Tabela → σ_local → JOIN → π`.

### 5.3. Heurística 2 — Redução de Atributos (projection pushdown) — `_build_attribute_reduction_graph` ([linhas 827-891](trabalho_rafael(1)(1).py#L827-L891))

**Ideia:** empurrar `π` (projeções) para baixo, mantendo só as colunas necessárias em cada ramo antes do JOIN.

Algoritmo:
1. Mesma classificação de predicados da heurística 1.
2. Para cada tabela, calcula o conjunto mínimo de colunas que precisa subir:
   - Colunas do `SELECT` que pertencem àquela tabela (`_columns_for_table`).
   - Colunas usadas em predicados (single + multi-table) que referenciam a tabela.
3. Monta: `Tabela → σ_local → π_local (só colunas necessárias) → JOIN → ...`.
4. **Fix importante** em [linha 861](trabalho_rafael(1)(1).py#L861): só inclui referências reais de colunas (com `.`), evitando incluir literais/números.

### 5.4. Plano Otimizado (heurística completa) — `_build_optimal_plan_graph` (botão verde)

Implementa **todas** as heurísticas do enunciado de uma vez:
- 5a-i Selection pushdown
- 5a-ii Projection pushdown
- **5b-i Reordenação de folhas**: tabela com mais predicados locais (mais "restritiva") fica em T0 (esquerda do JOIN). Marcada com badge `[PRIMARIA]`.
- **5b-ii Evitar cartesiano**: se há predicado multi-tabela vira ⋈; senão, mostra `× CARTESIANO (sem condicao de juncao!)` como aviso explícito.
- **5b-iii Ajusta o resto da árvore** (reflete a nova ordem de folhas).

Janela tem 3 painéis: heurísticas aplicadas (checklist), grafo, e plano de execução textual passo-a-passo.

A descrição textual usa `_describe_step(ntype, label)` que traduz cada nó em uma frase ("Aplicar SELECAO (sigma)...", "Realizar JUNCAO (bowtie) usando..."). Isso atende explicitamente o item 2c do enunciado ("Ordem de execução").

### 5.5. Layouts dos grafos
- `_hierarchical_layout` — BFS por níveis, usado nas duas primeiras visualizações.
- `_subtree_layout` — recursivo por subárvore, evita sobreposição. Usado em Redução de Atributos **e** no Plano Otimizado.

---

## 6. Banco esperado: `bd_vendas`

Schema oficial está no PDF do enunciado. Reproduzido na constante `SCHEMA` em [trabalho_rafael(1)(1).py:38-58](trabalho_rafael(1)(1).py#L38-L58). 11 tabelas: `categoria`, `produto`, `tipocliente`, `cliente`, `tipoendereco`, `endereco`, `telefone`, `status`, `pedido`, `pedido_has_produto`.

**Pegadinhas comuns:**
- `Cidade`, `UF`, `CEP` estão em `endereco`, **não** em `cliente`.
- A FK em `pedido` é `Cliente_idCliente` (com underscore e camelCase), não `cliente_id`.
- A PK de `cliente` é `idCliente`, não `id`.
- Validador é case-insensitive nas comparações mas mostra os nomes na forma original.

---

## 7. Estado git

- Branch: `main`
- Working tree limpo no início da sessão.
- Commits recentes: `f299338 heuristicas`, `68a1765 heuristicas`, `b71f0aa first commit`.
- Repo remoto: `origin/main` existe.

---

## 8. Convenções e preferências observadas

- Idioma do código e UI: **português** (sem acento em strings — usa "Heuristica", "Reducao", "Analise" para evitar problemas de encoding).
- Comentários em pt-BR usam separadores ASCII art `# ─── título ────`.
- Símbolos de álgebra relacional escritos como ASCII no `label`: `π` → `pi`, `σ` → `o`, `⋈` → `|x|`, `×` → `X`.
- Tema dark fixo (Catppuccin-like). Não há opção de tema claro.
- O usuário está em **Windows** (path `c:\Users\Erich\...`). Usar barras compatíveis e Tkinter sabe lidar.

---

## 9. O que NÃO fazer

- **Não** quebrar a estrutura de arquivo único — é um trabalho de entrega.
- **Não** introduzir dependências novas sem pedir.
- **Não** mexer nas credenciais MySQL hardcoded — é ambiente local de estudo.
- **Não** adicionar acentos em strings da UI sem testar encoding.
- **Não** trocar o renderer manual de Canvas por matplotlib — foi escolha consciente.

---

## 10. Pontos de extensão prováveis (se o usuário pedir)

- Suportar `OR` no parser (hoje só `AND` em `parse_condition`).
- Suportar mais de 2 tabelas no JOIN (a heurística de reordenação de folhas vira algo de verdade só com 3+ tabelas).
- Adicionar `GROUP BY` / `ORDER BY` nas heurísticas.
- Heurística 3 clássica: **reordenar JOINs** pelo menor produto estimado (cost-based).
- Exportar o grafo como imagem (PNG via `canvas.postscript` + Pillow).
- Aceitar aspas duplas nas strings (hoje só aspas simples).

## 11. Cobertura dos critérios de avaliação (PDF)

Todos os 10,0 pontos cobertos. Mapa em `EXPLICACAO.md` seção 10. Resumo:

- Interface (1,5) ✅
- Local para SQL (1,0) ✅
- Parsing (1,0) ✅
- **Validação de schema (1,0)** ✅ — `validate_against_schema`
- Grafo otimizado na GUI (1,0) ✅ — botão "Plano Otimizado"
- Plano de execução (1,5) ✅ — `_describe_step` traduz cada nó
- Heurística Tuplas (1,0) ✅
- Heurística Atributos (1,0) ✅
- **Demais heurísticas (1,0)** ✅ — `_build_optimal_plan_graph` faz 5b-i, 5b-ii, 5b-iii
