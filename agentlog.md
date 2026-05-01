# Agent Log — Contexto do Projeto

> Documento de handoff para outra IA assumir o projeto sem precisar reler tudo do zero.
> Última atualização: 2026-04-30

---

## 1. Visão geral

Projeto acadêmico (AV2 de Banco de Dados) que implementa um **SQL Query Studio** em Python/Tkinter. A aplicação:

1. Recebe uma query SQL digitada pelo usuário.
2. Executa um **tokenizer + parser próprio** (não usa biblioteca SQL).
3. Conecta no MySQL local (`bd_vendas`) e roda a query de verdade.
4. Mostra o resultado em uma `Treeview`.
5. Gera **grafos de execução de álgebra relacional** em janelas separadas, ilustrando heurísticas de otimização de consultas.

Arquivo principal: [trabalho_rafael(1)(1).py](trabalho_rafael(1)(1).py) — toda a lógica está nesse único arquivo (~1030 linhas).

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
| `tokenize()` | 38–41 | Regex que quebra SQL em tokens |
| `SQLParser` | 43–105 | Parser recursivo descendente (SELECT/FROM/INNER JOIN/ON/WHERE) |
| Histórico global | 107–109 | `QUERY_HISTORY` + `HISTORY_POS` (navegável com setas ↑/↓) |
| `SQLApp(tk.Tk)` | 112–1028 | Classe principal — contém UI + todas as heurísticas |
| `if __name__ == "__main__"` | 1031–1034 | Entry point |

### Limitações conhecidas do parser
- Só entende `SELECT ... FROM ... [INNER JOIN ... ON ...] [WHERE ...]`
- Não suporta: subqueries, `LEFT/RIGHT JOIN`, `GROUP BY`, `ORDER BY`, `LIMIT`, múltiplos JOINs, `OR` em condições (só `AND`).
- O MySQL ainda executa a query completa — o parser só serve para gerar os grafos.

---

## 4. Botões da UI (o que cada um faz)

[trabalho_rafael(1)(1).py:204-254](trabalho_rafael(1)(1).py#L204-L254)

| Botão | Método | O que faz |
|---|---|---|
| **Executar** (Ctrl+Enter) | `_execute` | Parseia + executa no MySQL + popula `Treeview` |
| **Limpar** | `_clear` | Limpa editor e resultados |
| **Analisar Parser** | `_show_parse_tree` | Janela com tokens coloridos + JSON da AST |
| **Grafo Não Otimizado** | `_show_nonoptimized_graph` | Plano "ingênuo": Cartesiano → Seleção → Projeção |
| **Redução de Tuplas** | `_show_tuple_reduction_graph` | **Heurística 1** — selection pushdown |
| **Redução de Atributos** | `_show_attribute_reduction_graph` | **Heurística 2** — projection pushdown |

---

## 5. As três visualizações de grafo (núcleo do trabalho)

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

### 5.4. Layouts dos grafos
- `_hierarchical_layout` ([616-637](trabalho_rafael(1)(1).py#L616-L637)) — BFS por níveis, usado nas duas primeiras visualizações.
- `_subtree_layout` ([893-933](trabalho_rafael(1)(1).py#L893-L933)) — recursivo por subárvore, evita sobreposição. Usado **só** na visualização de Redução de Atributos (que é a mais larga).

---

## 6. Banco esperado: `bd_vendas`

Não há schema versionado no repo. Pelas queries pedagógicas típicas desse tipo de trabalho, o banco provavelmente tem tabelas de vendas (`cliente`, `produto`, `venda`, etc.). **Confirmar com o usuário antes de assumir nomes de colunas.**

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
- Suportar mais de 2 tabelas no JOIN.
- Adicionar `GROUP BY` / `ORDER BY` nas heurísticas.
- Heurística 3 clássica: **reordenar JOINs** pelo menor produto estimado.
- Exportar o grafo como imagem (PNG via `canvas.postscript` + Pillow).
