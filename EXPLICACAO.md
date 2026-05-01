# SQL Query Studio — Explicação Didática Completa

> Guia passo a passo do projeto, do "o que é" ao "como cada linha funciona".
> Pensado para quem está estudando **otimização de consultas** em Banco de Dados.

---

## Sumário

1. [O que é esse projeto](#1-o-que-é-esse-projeto)
2. [O problema que ele resolve (a teoria)](#2-o-problema-que-ele-resolve-a-teoria)
3. [Conceitos de Álgebra Relacional](#3-conceitos-de-álgebra-relacional)
4. [Como rodar](#4-como-rodar)
5. [Tour pela interface](#5-tour-pela-interface)
6. [Como o código funciona — passo a passo](#6-como-o-código-funciona--passo-a-passo)
7. [As três visualizações de grafo (o coração do trabalho)](#7-as-três-visualizações-de-grafo-o-coração-do-trabalho)
8. [Exemplo completo: do SQL ao grafo otimizado](#8-exemplo-completo-do-sql-ao-grafo-otimizado)
9. [Glossário rápido](#9-glossário-rápido)

---

## 1. O que é esse projeto

É um **estúdio de consultas SQL com visualização de planos de execução**. Você digita uma query, e o programa:

1. Mostra a query "decomposta" (tokens + árvore sintática).
2. Roda a query no MySQL e exibe o resultado.
3. Desenha **três grafos diferentes** mostrando como aquela query *poderia* ser executada — um ruim e dois otimizados por heurísticas clássicas.

**Por que isso importa?** Porque em Banco de Dados, a mesma query pode ser executada de várias formas. Algumas são **milhões de vezes mais rápidas** que outras. O otimizador de consultas é o componente do SGBD que escolhe entre essas formas. Esse projeto te mostra **como ele pensa**.

---

## 2. O problema que ele resolve (a teoria)

Imagine duas tabelas:

- `cliente` com **1.000.000** de linhas
- `pedido` com **5.000.000** de linhas

E a query:

```sql
SELECT cliente.nome, pedido.valor
FROM cliente
INNER JOIN pedido ON cliente.id = pedido.cliente_id
WHERE cliente.cidade = 'Recife'
```

### Forma ingênua (ruim)

1. Faz **produto cartesiano** entre as duas tabelas → `1.000.000 × 5.000.000 = 5 trilhões` de linhas em memória 💥
2. Filtra pelas condições do JOIN e do WHERE.
3. Projeta as colunas pedidas.

### Forma otimizada (boa)

1. **Filtra primeiro** `cliente WHERE cidade = 'Recife'` → talvez sobrem 50.000 linhas.
2. **Projeta primeiro** só `id` e `nome` (descarta colunas que não vão ser usadas).
3. **Aí sim** faz o JOIN — agora entre 50.000 e 5.000.000, com poucas colunas.

Resultado: o SGBD trabalha com bilhões de operações a menos. Esse projeto **visualiza essa transformação**.

---

## 3. Conceitos de Álgebra Relacional

A álgebra relacional é a "matemática" por trás do SQL. Você precisa de **5 operadores** para entender os grafos:

| Símbolo | Nome | O que faz | Equivalente em SQL |
|---|---|---|---|
| **σ** (sigma) | Seleção | Filtra **linhas** que atendem uma condição | `WHERE` |
| **π** (pi) | Projeção | Filtra **colunas** | `SELECT col1, col2` |
| **×** (vezes) | Produto Cartesiano | Combina toda linha de A com toda linha de B | `FROM a, b` (sem `ON`) |
| **⋈** (bowtie) | Junção (JOIN) | Produto cartesiano + seleção pela condição de junção | `INNER JOIN ... ON` |
| (raiz) | Tabela | Folha do grafo, a tabela física | nome da tabela |

> No código, como o terminal Tkinter não renderiza esses símbolos com fonte garantida, eles são representados como `o` (σ), `pi` (π), `|x|` (⋈), `X` (×). Veja [trabalho_rafael(1)(1).py:586](trabalho_rafael(1)(1).py#L586) e [trabalho_rafael(1)(1).py:611](trabalho_rafael(1)(1).py#L611).

### Como ler um grafo de álgebra relacional

Os grafos são lidos de **baixo para cima** (bottom-up). As folhas são as tabelas. Cada nó pai aplica uma operação no resultado dos filhos. O nó raiz produz o resultado final.

```
              π nome, valor          ← (3) projeta as colunas finais
                  │
              ⋈ cliente.id = pedido.cliente_id  ← (2) faz a junção
                ╱   ╲
        σ cidade=Recife    pedido      ← (1) filtra cliente antes
              │
           cliente
```

---

## 4. Como rodar

### Pré-requisitos

```bash
pip install mysql-connector-python networkx
```

E ter o MySQL local com:

- usuário `root`, senha `132654`
- banco `bd_vendas` criado e populado

### Executar

```bash
python "trabalho_rafael(1)(1).py"
```

Abre uma janela com editor SQL no topo, botões no meio e tabela de resultados embaixo.

> Se sua senha do MySQL for diferente, edite [trabalho_rafael(1)(1).py:445-450](trabalho_rafael(1)(1).py#L445-L450).

---

## 5. Tour pela interface

```
┌──────────────────────────────────────────────────────┐
│  SQL Query Studio                  Parser + MySQL    │
│                                                      │
│  EDITOR SQL                                          │
│  ┌──┬───────────────────────────────────────────┐    │
│  │ 1│ SELECT cliente.nome, pedido.valor         │    │
│  │ 2│ FROM cliente                              │    │
│  │ 3│ INNER JOIN pedido ON ...                  │    │
│  └──┴───────────────────────────────────────────┘    │
│                                                      │
│  [Executar] [Limpar] [Analisar Parser]               │
│  [Grafo Não Otimizado] [Tuplas] [Atributos]          │
│                                                      │
│  RESULTADOS                                          │
│  ┌──────────────────────────────────────────────┐    │
│  │ NOME      │ VALOR                            │    │
│  │ João      │ 150.00                           │    │
│  │ Maria     │ 320.00                           │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

### Os 6 botões

| Botão | Atalho | O que faz |
|---|---|---|
| **Executar** | `Ctrl+Enter` | Roda a query no MySQL e mostra o resultado |
| **Limpar** | — | Apaga editor + resultados |
| **Analisar Parser** | — | Janela com tokens coloridos + JSON da árvore sintática |
| **Grafo Não Otimizado** | — | Plano "ingênuo" — para você ver como **não** fazer |
| **Redução de Tuplas** | — | Heurística 1 — empurra **σ** (seleções) para perto das tabelas |
| **Redução de Atributos** | — | Heurística 2 — empurra **π** (projeções) para perto das tabelas |

### Recursos extras do editor

- **Highlight de sintaxe**: keywords em rosa, strings em verde, números em laranja, operadores em ciano. ([_highlight_syntax](trabalho_rafael(1)(1).py#L339-L375))
- **Histórico**: setas ↑/↓ navegam pelas queries já executadas. ([_history_prev/_history_next](trabalho_rafael(1)(1).py#L386-L404))
- **Numeração de linha**: à esquerda, fixa.
- **Placeholder**: texto cinza sumindo quando você clica.

---

## 6. Como o código funciona — passo a passo

O arquivo [trabalho_rafael(1)(1).py](trabalho_rafael(1)(1).py) tem ~1030 linhas, divididas em blocos com comentários `# ─── título ────`.

### 6.1. `tokenize(sql)` — quebrar a query em pedaços

[Linhas 38-41](trabalho_rafael(1)(1).py#L38-L41)

```python
def tokenize(sql):
    pattern = r"<=|>=|<>|=|>|<|\(|\)|,|[\w.]+"
    tokens = re.findall(pattern, sql, re.IGNORECASE)
    return [t.strip() for t in tokens]
```

Uma regex que captura, em ordem de prioridade:

1. Operadores compostos: `<=`, `>=`, `<>`
2. Operadores simples: `=`, `>`, `<`
3. Pontuação: `(`, `)`, `,`
4. Palavras e identificadores com ponto: `cliente.nome`, `SELECT`, `123`

**Exemplo:**

```python
tokenize("SELECT * FROM cliente WHERE id = 5")
# ['SELECT', '*', 'FROM', 'cliente', 'WHERE', 'id', '=', '5']
```

### 6.2. `SQLParser` — construir uma estrutura a partir dos tokens

[Linhas 43-105](trabalho_rafael(1)(1).py#L43-L105)

É um **parser recursivo descendente** simples. Tem dois métodos auxiliares:

- `peek()` — espia o próximo token sem consumir
- `consume(expected)` — consome um token, opcionalmente exigindo que seja o esperado

E o método `parse()` segue a gramática:

```
SELECT <colunas> FROM <tabela>
       [INNER JOIN <tabela2> ON <condição>]
       [WHERE <condição>]
```

**Saída do parser** para `SELECT nome FROM cliente WHERE idade > 18`:

```json
{
  "columns": ["nome"],
  "table": "cliente",
  "where": [["idade", ">", "18"]]
}
```

> Limitação importante: o parser **só entende `AND`** entre condições, não `OR`. Veja [parse_condition linhas 86-105](trabalho_rafael(1)(1).py#L86-L105).

### 6.3. `_execute()` — rodar a query

[Linhas 421-490](trabalho_rafael(1)(1).py#L421-L490)

Sequência:

1. Pega o texto do editor.
2. Tokeniza e parseia (só para extrair o nome da tabela e validar).
3. Conecta no MySQL com `mysql.connector.connect(...)`.
4. Executa `cursor.execute(query)` — **aqui é o MySQL real rodando**, o parser próprio não executa nada.
5. Pega resultados com `fetchall()` e nomes de coluna com `cursor.description`.
6. Popula a `Treeview` com linhas alternadas (tags `odd`/`even`).
7. Atualiza status: "OK - Tabela: cliente" ou "MySQL Error: ...".

### 6.4. Funções auxiliares para os grafos

#### `_flatten_conjunction(cond)` — [linhas 724-736](trabalho_rafael(1)(1).py#L724-L736)

A árvore do parser pode ter listas aninhadas (por causa de parênteses). Essa função **achata** tudo em uma lista plana de predicados.

```python
# entrada: [['a', '=', '1'], 'AND', ['b', '>', '2']]
# saída:   [['a', '=', '1'], ['b', '>', '2']]
```

#### `_predicate_tables(pred, table_names)` — [linhas 738-746](trabalho_rafael(1)(1).py#L738-L746)

Descobre **quais tabelas** um predicado referencia, olhando o prefixo `tabela.coluna`.

```python
# pred = ['cliente.id', '=', 'pedido.cliente_id']
# tables = ['cliente', 'pedido']
# retorna: {'cliente', 'pedido'}    ← predicado de JOIN

# pred = ['cliente.cidade', '=', "'Recife'"]
# retorna: {'cliente'}               ← predicado de uma tabela só
```

**Essa é a função-chave** que separa "predicado que filtra uma tabela" de "predicado de junção".

---

## 7. As três visualizações de grafo (o coração do trabalho)

Todas constroem um `nx.DiGraph` (grafo dirigido do networkx) onde:

- Cada nó tem um `type` (`table`, `selection`, `projection`, `join`, `cartesian`).
- Cada nó tem um `order` (a posição na execução bottom-up).
- A visualização desenha tudo manualmente em um `tk.Canvas` — sem matplotlib.

### 7.1. Grafo Não Otimizado

[`_build_nonoptimized_graph` — linhas 570-614](trabalho_rafael(1)(1).py#L570-L614)

A construção é direta e propositalmente ruim:

```
1. Cria um nó para cada tabela.
2. Se há mais de uma → cria nó × (cartesiano) ligado a todas.
3. Se há condições (JOIN ou WHERE) → cria UM nó σ enorme com todas juntas.
4. Cria nó π com as colunas pedidas no SELECT.
```

**Resultado visual:**

```
        π nome, valor
            │
        σ cliente.id = pedido.cliente_id AND cliente.cidade = 'Recife'
            │
            ×
          ╱   ╲
    cliente   pedido
```

**Por que é ruim?** O `×` materializa o produto cartesiano antes de qualquer filtro. Se as tabelas têm 1M e 5M linhas, o nó σ recebe **5 trilhões** de linhas para filtrar.

### 7.2. Heurística 1 — Redução de Tuplas (selection pushdown)

[`_build_tuple_reduction_graph` — linhas 748-807](trabalho_rafael(1)(1).py#L748-L807)

**Regra:** sempre que possível, aplique a seleção (σ) **antes** do JOIN.

Algoritmo:

```
1. Achata todas as condições com _flatten_conjunction.
2. Classifica cada predicado:
     - Se referencia 1 tabela → vira σ "local" naquela tabela.
     - Se referencia 2 tabelas → vira condição de JOIN (⋈).
3. Se sobrar predicado multi-tabela, troca o × por ⋈ com aquela condição.
4. Coloca π no topo.
```

**Resultado visual** para o nosso exemplo:

```
        π nome, valor
            │
        ⋈ cliente.id = pedido.cliente_id
          ╱     ╲
    σ cidade=Recife   pedido
          │
       cliente
```

**Ganho:** o JOIN agora trabalha com o `cliente` já filtrado (50.000 linhas em vez de 1.000.000). E mais: o `×` virou `⋈`, que internamente já é otimizado pelo SGBD usando hash join, merge join etc.

### 7.3. Heurística 2 — Redução de Atributos (projection pushdown)

[`_build_attribute_reduction_graph` — linhas 827-891](trabalho_rafael(1)(1).py#L827-L891)

**Regra:** mantenha apenas as colunas estritamente necessárias em cada ramo.

Algoritmo (em cima do que a Heurística 1 já fez):

```
Para cada tabela T:
  1. Lista colunas de T usadas no SELECT final.
  2. Lista colunas de T usadas em qualquer predicado (local ou de JOIN).
  3. Cria um π_T logo acima do σ_T, com a união dessas colunas.
```

**Resultado visual:**

```
                π nome, valor
                     │
                ⋈ cliente.id = pedido.cliente_id
              ╱                    ╲
        π id, nome             π cliente_id, valor
           │                        │
      σ cidade=Recife            pedido
           │
        cliente
```

**Ganho:** quando os dados sobem para o JOIN, **cada linha é menor** (menos bytes). Em tabelas com colunas tipo `descricao TEXT` ou `foto BLOB`, isso pode ser dramático.

> Observação técnica em [linha 861-870](trabalho_rafael(1)(1).py#L861-L870): a função filtra por `"." in side` para garantir que só nomes qualificados (ex: `cliente.id`) entrem na projeção — números e literais não viram colunas.

### 7.4. Como os grafos são desenhados

Existem dois algoritmos de layout:

#### `_hierarchical_layout` — [linhas 616-637](trabalho_rafael(1)(1).py#L616-L637)

Usado nas duas primeiras visualizações. BFS por níveis: nó raiz no topo, filhos espalhados horizontalmente em cada nível. Simples mas pode sobrepor labels.

#### `_subtree_layout` — [linhas 893-933](trabalho_rafael(1)(1).py#L893-L933)

Usado na Redução de Atributos (que é a mais larga). Calcula recursivamente a **largura mínima** que cada subárvore precisa para os filhos não se sobreporem. Distribui o espaço proporcionalmente. É o layout mais bonito, mas mais caro.

A renderização em si é manual no `Canvas`:

- `create_rectangle` desenha caixas com cor por tipo de nó.
- `create_line` desenha as conexões (com sombra de tema escuro).
- `create_text` escreve o label.

Veja [_render_graph_window linhas 639-703](trabalho_rafael(1)(1).py#L639-L703) e [_show_attribute_reduction_graph linhas 935-1028](trabalho_rafael(1)(1).py#L935-L1028).

---

## 8. Exemplo completo: do SQL ao grafo otimizado

Vamos rastrear o que acontece quando você digita:

```sql
SELECT cliente.nome, pedido.valor
FROM cliente
INNER JOIN pedido ON cliente.id = pedido.cliente_id
WHERE cliente.cidade = 'Recife'
```

### Passo 1: tokenização

```python
['SELECT', 'cliente.nome', ',', 'pedido.valor',
 'FROM', 'cliente',
 'INNER', 'JOIN', 'pedido',
 'ON', 'cliente.id', '=', 'pedido.cliente_id',
 'WHERE', 'cliente.cidade', '=', "'Recife'"]
```

### Passo 2: parsing

```json
{
  "columns": ["cliente.nome", "pedido.valor"],
  "table": "cliente",
  "join_table": "pedido",
  "join_on":  [["cliente.id", "=", "pedido.cliente_id"]],
  "where":    [["cliente.cidade", "=", "'Recife'"]]
}
```

### Passo 3: classificação dos predicados

Aplicando `_predicate_tables` em cada predicado:

| Predicado | Tabelas referenciadas | Tipo |
|---|---|---|
| `cliente.id = pedido.cliente_id` | `{cliente, pedido}` | multi (vira ⋈) |
| `cliente.cidade = 'Recife'` | `{cliente}` | local em `cliente` |

### Passo 4: monta o grafo de Redução de Tuplas

```
T0 = cliente,  T1 = pedido

single_table_preds = {
  cliente: [['cliente.cidade', '=', "'Recife'"]],
  pedido:  []
}
multi_table_preds = [['cliente.id', '=', 'pedido.cliente_id']]

→ cria SEL_0 sobre T0 (cliente)
→ T1 (pedido) vai direto pro JOIN
→ cria JOIN ligando SEL_0 e T1
→ cria PROJ no topo
```

### Passo 5: o grafo na tela

```
                π cliente.nome, pedido.valor
                          │
                ⋈ cliente.id = pedido.cliente_id
                ╱                          ╲
        σ cliente.cidade = 'Recife'      pedido
                │
            cliente
```

E embaixo da janela aparece a **ordem de execução bottom-up**:

```
1. cliente
2. pedido
3. σ cliente.cidade = 'Recife'
4. ⋈ cliente.id = pedido.cliente_id
5. π cliente.nome, pedido.valor
```

---

## 9. Glossário rápido

| Termo | Significado |
|---|---|
| **AST** (Abstract Syntax Tree) | Estrutura em árvore que representa o código (ou query) parseado |
| **Tokenizer / Lexer** | Componente que quebra texto em "palavras" (tokens) |
| **Parser** | Componente que monta uma árvore a partir dos tokens, validando a gramática |
| **DiGraph** | Grafo dirigido (arestas têm direção). Aqui: `pai → filho` |
| **Bottom-up** | Lê de baixo (folhas) para cima (raiz). Ordem natural de execução |
| **Pushdown** | "Empurrar para baixo" uma operação. Ex: selection pushdown = mover σ para perto das tabelas |
| **Predicado** | Uma condição booleana, ex: `idade > 18` |
| **Cardinalidade** | Quantidade de linhas de uma relação |
| **Heurística** | Regra prática que costuma melhorar o resultado, sem garantir o ótimo absoluto |

---

## TL;DR

- O programa parseia SQL → executa no MySQL → desenha 3 planos de execução em álgebra relacional.
- O plano "não otimizado" mostra **como não fazer** (× antes de σ).
- A **Redução de Tuplas** empurra σ para perto das tabelas → JOIN com menos linhas.
- A **Redução de Atributos** empurra π para perto das tabelas → JOIN com linhas menores.
- Junte as duas e você tem 90% do que um otimizador de consultas real faz no plano lógico.
