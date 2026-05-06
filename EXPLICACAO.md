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
7. [Validação de Schema (bd_vendas)](#7-validação-de-schema-bd_vendas)
8. [As quatro visualizações de grafo (o coração do trabalho)](#8-as-quatro-visualizações-de-grafo-o-coração-do-trabalho)
9. [Múltiplos INNER JOINs (queries com 3+ tabelas)](#9-múltiplos-inner-joins-queries-com-3-tabelas)
10. [Exemplo completo: do SQL ao plano otimizado](#10-exemplo-completo-do-sql-ao-plano-otimizado)
11. [Mapeamento dos critérios de avaliação](#11-mapeamento-dos-critérios-de-avaliação)
12. [Glossário rápido](#12-glossário-rápido)

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

### Os 7 botões

| Botão | Atalho | O que faz |
|---|---|---|
| **Executar** | `Ctrl+Enter` | Valida + roda a query no MySQL e mostra o resultado |
| **Limpar** | — | Apaga editor + resultados |
| **Analisar Parser** | — | Janela com tokens coloridos + JSON da árvore sintática |
| **Grafo Não Otimizado** | — | Plano "ingênuo" — para você ver como **não** fazer |
| **Redução de Tuplas** | — | Heurística 5a-i — empurra **σ** (seleções) para perto das tabelas |
| **Redução de Atributos** | — | Heurística 5a-ii — empurra **π** (projeções) para perto das tabelas |
| **Plano Otimizado** (verde) | — | **Heurística completa** (5a + 5b): combina tudo + reordena folhas + evita cartesiano |

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
       (INNER JOIN <tabela_n> ON <condição>)*    ← zero ou mais joins
       [WHERE <condição>]
```

**Saída do parser** para `SELECT nome FROM cliente WHERE idade > 18`:

```json
{
  "columns": ["nome"],
  "table": "cliente",
  "joins": [],
  "where": [["idade", ">", "18"]]
}
```

**Saída para uma query com 2 INNER JOINs**:

```json
{
  "columns": ["cliente.Nome", "pedido.ValorTotalPedido", "status.Descricao"],
  "table": "cliente",
  "joins": [
    {"table": "pedido", "on": [["cliente.idCliente", "=", "pedido.Cliente_idCliente"]]},
    {"table": "status", "on": [["pedido.Status_idStatus", "=", "status.idStatus"]]}
  ],
  "where": [["cliente.Nome", "=", "'Joao'"]]
}
```

> O campo `joins` é uma **lista** que pode ter 0, 1, 2 ou mais entradas. Cada entrada tem `table` (nome da tabela junta) e `on` (lista de predicados achatada).
>
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

## 7. Validação de Schema (bd_vendas)

O enunciado exige (item 4.b): *"O banco exemplo servirá como base na validação dos nomes de tabelas e campos no momento da validação da cláusula SQL."*

### O que está implementado

No topo do arquivo existe um dicionário `SCHEMA` que reproduz **todas as tabelas e colunas** do `bd_vendas` exatamente como no script SQL do PDF. Veja [SCHEMA — linhas 39-58](trabalho_rafael(1)(1).py#L39-L58).

```python
SCHEMA = {
  "categoria":          ["idCategoria", "Descricao"],
  "produto":            ["idProduto", "Nome", "Descricao", "Preco", ...],
  "cliente":            ["idCliente", "Nome", "Email", ...],
  "endereco":           [..., "Cidade", "UF", "CEP", ...],
  "pedido":             ["idPedido", "Status_idStatus", ...],
  "pedido_has_produto": [...],
  ...
}
```

### A função `validate_against_schema(parsed)` ([linhas 76-149](trabalho_rafael(1)(1).py#L76-L149))

Ela faz 5 checagens:

1. **Tabela do FROM** existe em `bd_vendas`?
2. **Tabela do INNER JOIN** existe?
3. **Cada coluna do SELECT** está na(s) tabela(s) certa(s)?
4. **Cada coluna do WHERE** existe?
5. **Cada coluna do JOIN ON** existe?

Para cada referência ela aplica regras inteligentes:

- `*` → ok, é coringa, sempre passa.
- `'Recife'`, `42` → literais (string ou número), não são colunas, ignoradas.
- `cliente.Cidade` → checa se `cliente` está no FROM/JOIN E se `Cidade` é coluna de `cliente`. (Aqui dá erro — `Cidade` está em `endereco`!)
- `Nome` (sem prefixo) → procura em todas as tabelas disponíveis. Se achar em uma só → ok. Se achar em duas → erro de **ambiguidade** (você tem que prefixar). Se não achar → erro.

### Quando a validação roda

| Ação | Comportamento |
|---|---|
| Botão **Executar** | Bloqueia execução e mostra os erros no painel central |
| Qualquer botão de **grafo** | Abre uma `messagebox` com a lista de erros e cancela |
| Botão **Analisar Parser** | Não bloqueia (você pode querer ver a AST mesmo de query errada) |

### Por que isso importa

O enunciado dá **1,0 ponto** para "Campos e comandos errados são validados". Antes desta implementação, o programa simplesmente jogava a query no MySQL e mostrava o erro do MySQL — o que não é validação, é só repassar o erro. Agora o programa **rejeita a query antes de tocar no banco**, com mensagens em português apontando exatamente o problema.

### Exemplo

```sql
SELECT cliente.Cidade, pedido.valor
FROM cliente
INNER JOIN pedido ON cliente.id = pedido.cliente_id
```

Erros detectados:

```
- Coluna 'Cidade' nao existe em 'cliente' (em 'cliente.Cidade', no SELECT).
- Coluna 'valor' nao existe em 'pedido' (em 'pedido.valor', no SELECT).
- Coluna 'id' nao existe em 'cliente' (em 'cliente.id', no JOIN ON).
- Coluna 'cliente_id' nao existe em 'pedido' (em 'pedido.cliente_id', no JOIN ON).
```

E sugere implicitamente: `Cidade` está em `endereco`, `ValorTotalPedido` em `pedido`, `idCliente` em `cliente`, `Cliente_idCliente` em `pedido`.

---

## 8. As quatro visualizações de grafo (o coração do trabalho)

Todas constroem um `nx.DiGraph` (grafo dirigido do networkx) onde:

- Cada nó tem um `type` (`table`, `selection`, `projection`, `join`, `cartesian`).
- Cada nó tem um `order` (a posição na execução bottom-up).
- A visualização desenha tudo manualmente em um `tk.Canvas` — sem matplotlib.

### 8.1. Grafo Não Otimizado

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

### 8.2. Heurística 5a-i — Redução de Tuplas (selection pushdown)

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

### 8.3. Heurística 5a-ii — Redução de Atributos (projection pushdown)

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

### 8.4. Plano Final Otimizado — Heurística 5b (reordenação + evitar cartesiano)

> **Esta é a novidade.** Botão verde "Plano Otimizado". Implementa o item 5b inteiro do enunciado.

O enunciado lista três sub-heurísticas em 5b:

> i. reordenar os nós folha da árvore de consulta
> ii. evitar a operação de produto cartesiano
> iii. ajustar o restante da árvore de forma apropriada

Construído por [`_build_optimal_plan_graph` — linhas ~1042-1149](trabalho_rafael(1)(1).py).

#### Como funciona

1. **Aplica primeiro** as duas heurísticas anteriores: pushdown de σ e de π.
2. **Reordena as folhas**: a tabela com **mais predicados locais** vai para a posição "primária" (esquerda do JOIN). Critério: `key=lambda t: -len(predicados_locais[t])`. A tabela primária ganha um badge `[PRIMARIA]` no rótulo.
3. **Evita o produto cartesiano**: se existe pelo menos um predicado que toca **2 tabelas** (ex: `cliente.id = pedido.cliente_id`), ele vira a condição do `⋈` — **substitui** o `×`. Se não houver predicado de junção, o programa **avisa explicitamente** com `CARTESIANO (sem condicao de juncao!)`.
4. **Ajusta o restante**: a projeção final fica no topo, recebendo o resultado da junção otimizada.

#### Por que reordenar folhas importa?

Em planos de execução de SGBDs reais (PostgreSQL, MySQL), o **lado esquerdo** do JOIN costuma ser a "outer relation" — a que dirige o loop. Se você coloca a tabela com 50.000 linhas filtradas como esquerda e a de 5.000.000 como direita, faz menos comparações que o contrário. É exatamente o que essa heurística simula visualmente.

#### Resultado visual (mesmo exemplo das outras heurísticas)

```
                          π cliente.nome, pedido.valor
                                      │
                          ⋈ cliente.id = pedido.cliente_id
                        ╱                              ╲
                  π id, nome                  π cliente_id, valor
                       │                              │
              σ cidade='Recife'                    pedido
                       │
              cliente [PRIMARIA]
```

> Como nesse exemplo só `cliente` tem σ local, ela é a primária e fica na esquerda.

#### Painel "Heurísticas Aplicadas"

A janela mostra um checklist no topo, listando exatamente quais heurísticas foram aplicadas naquela query específica. Exemplo:

```
[OK]  5a-i  Reducao de Tuplas (selecao empurrada para perto das tabelas)
[OK]  5a-ii Reducao de Atributos (projecao local mantem so colunas necessarias)
[OK]  5b-i  Reordenacao de folhas (tabela 'cliente' eh a mais restritiva)
[OK]  5b-ii Evita produto cartesiano (usa JOIN com predicado)
```

Se a query não tiver nenhum predicado de junção, aparece o aviso:

```
[OK]  5b-ii AVISO: nao foi possivel evitar cartesiano (sem condicao de juncao)
```

#### Plano de Execução textual (passo a passo)

Embaixo do grafo, em vez de só listar nomes de nós, o programa traduz cada operador para uma frase didática usando [`_describe_step` — linhas ~1151-1167](trabalho_rafael(1)(1).py):

```
Passo 1.  Acessar a tabela 'cliente'
Passo 2.  Acessar a tabela 'pedido'
Passo 3.  Aplicar SELECAO (sigma): filtra linhas onde cliente.cidade = 'Recife'
Passo 4.  Aplicar PROJECAO (pi): mantem apenas as colunas cliente.idCliente, cliente.Nome
Passo 5.  Aplicar PROJECAO (pi): mantem apenas as colunas pedido.Cliente_idCliente, pedido.ValorTotalPedido
Passo 6.  Realizar JUNCAO (bowtie) usando cliente.idCliente = pedido.Cliente_idCliente
Passo 7.  Aplicar PROJECAO (pi): mantem apenas as colunas cliente.Nome, pedido.ValorTotalPedido
```

Isso atende explicitamente o item **2c do enunciado** ("Ordem de execução da consulta") com **descrições semânticas**, não só símbolos.

---

### 8.5. Como os grafos são desenhados

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

## 9. Múltiplos INNER JOINs (queries com 3+ tabelas)

O enunciado pede suporte a `INNER JOIN`, sem especificar quantos. O parser foi estendido para aceitar **N joins encadeados**, cobrindo queries reais que cruzam várias tabelas.

### 9.1. Como o parser representa N joins

Antes (versão inicial, só 1 JOIN):

```python
# parsed era assim:
{ "table": "cliente",
  "join_table": "pedido",          # ← campo único
  "join_on": [["...", "=", "..."]] }
```

Agora (versão atual, N JOINs):

```python
{ "table": "cliente",
  "joins": [                        # ← lista
    {"table": "pedido", "on": [["cliente.idCliente", "=", "pedido.Cliente_idCliente"]]},
    {"table": "status", "on": [["pedido.Status_idStatus", "=", "status.idStatus"]]}
  ] }
```

A mudança é só estrutural — o parser executa um `while` em vez de um `if`:

```python
data['joins'] = []
while self.peek() and self.peek().upper() == "INNER":
    self.consume("INNER")
    self.consume("JOIN")
    join_table = self.consume()
    join_on = []
    if self.peek() and self.peek().upper() == "ON":
        self.consume("ON")
        join_on = self.parse_condition()
    data['joins'].append({'table': join_table, 'on': join_on})
```

### 9.2. O que mudou nos consumidores

Quatro lugares precisaram ser atualizados para iterar a lista em vez de checar um único campo:

| Onde | Antes | Agora |
|---|---|---|
| `validate_against_schema` | `if join_lower not in SCHEMA: ...` | `for j in joins: if j['table'].lower() not in SCHEMA: ...` |
| `_build_nonoptimized_graph` | mesmo padrão | itera `joins` para coletar tabelas e condições |
| `_build_tuple_reduction_graph` | mesmo padrão | itera `joins` para coletar predicados |
| `_build_attribute_reduction_graph` | mesmo padrão | itera `joins` |
| `_build_optimal_plan_graph` | mesmo padrão | itera `joins` |

Padrão de coleta de tabelas:

```python
tables = [parsed["table"]]
for j in parsed.get('joins', []):
    tables.append(j['table'])
```

Padrão de coleta de predicados:

```python
predicates = []
for j in parsed.get('joins', []):
    if j.get('on'):
        predicates.extend(self._flatten_conjunction(j['on']))
if "where" in parsed:
    predicates.extend(self._flatten_conjunction(parsed["where"]))
```

### 9.3. Como ficam os grafos com 3+ tabelas

Para uma query com 3 tabelas (ex: `cliente ⋈ pedido ⋈ status`):

**Não Otimizado** — produto cartesiano N-ário, depois seleção monstro, depois projeção:

```
        π colunas
            │
        σ todas as condições juntas
            │
            ×
          ╱ │ ╲
       T0  T1  T2
```

**Plano Otimizado** — mesma lógica de antes, só que com mais folhas:

```
                π colunas
                    │
            ⋈ todos os predicados de junção
          ╱         │         ╲
       π loc0    π loc1     π loc2
         │         │           │
      σ loc0    (sem σ)     (sem σ)
         │
       T0[PRIMARIA]    T1         T2
```

A heurística de **reordenação de folhas** continua funcionando: a tabela com mais predicados locais ainda recebe o badge `[PRIMARIA]` e fica como primeira aresta do JOIN. Com 3 tabelas, isso pode ser ainda mais visível — pode existir uma tabela primária E uma "secundária com filtros", ambas posicionadas antes das que não têm filtro.

### 9.4. Exemplo prático

```sql
SELECT cliente.Nome, pedido.ValorTotalPedido, status.Descricao
FROM cliente
INNER JOIN pedido ON cliente.idCliente = pedido.Cliente_idCliente
INNER JOIN status ON pedido.Status_idStatus = status.idStatus
WHERE cliente.Nome = 'Joao'
```

Classificação dos predicados:

| Predicado | Tabelas referenciadas | Tipo |
|---|---|---|
| `cliente.idCliente = pedido.Cliente_idCliente` | `{cliente, pedido}` | multi → entra no JOIN |
| `pedido.Status_idStatus = status.idStatus` | `{pedido, status}` | multi → entra no JOIN |
| `cliente.Nome = 'Joao'` | `{cliente}` | local → vira σ em cliente |

No grafo do **Plano Otimizado** o nó JOIN agora carrega **2 condições** unidas por `AND`, e `cliente` aparece marcado como `[PRIMARIA]`.

### 9.5. Limitação visual

O grafo trata o JOIN como uma operação **N-ária** (um nó com N folhas), não como uma árvore binária esquerda-profunda (`((T0 ⋈ T1) ⋈ T2)`). Isso é uma simplificação didática:

- ✅ **Vantagem**: mais simples de ler, mostra todos os predicados de junção em um lugar.
- ⚠️ **Limitação**: SGBDs reais escolhem uma ORDEM de junção (qual par junta primeiro). Esse projeto não faz cost-based join ordering — só a reordenação de folhas heurística.

Se você quiser implementar join ordering binário (uma extensão clássica), seria a próxima evolução natural do `_build_optimal_plan_graph`.

---

## 10. Exemplo completo: do SQL ao plano otimizado

Vamos rastrear o que acontece quando você digita uma query **válida** (com nomes corretos do `bd_vendas`):

```sql
SELECT cliente.Nome, pedido.ValorTotalPedido
FROM cliente
INNER JOIN pedido ON cliente.idCliente = pedido.Cliente_idCliente
WHERE cliente.Nome = 'Joao'
```

> Note: usei `cliente.Nome = 'Joao'` em vez de `cidade = 'Recife'` porque `cidade` está em `endereco`, não em `cliente`. O validador agora detecta isso!

### Passo 1: tokenização

```python
['SELECT', 'cliente.Nome', ',', 'pedido.ValorTotalPedido',
 'FROM', 'cliente',
 'INNER', 'JOIN', 'pedido',
 'ON', 'cliente.idCliente', '=', 'pedido.Cliente_idCliente',
 'WHERE', 'cliente.Nome', '=', "'Joao'"]
```

> O `'Joao'` (com aspas) vira **um único token**, graças à atualização da regex do tokenizer.

### Passo 2: parsing

```json
{
  "columns": ["cliente.Nome", "pedido.ValorTotalPedido"],
  "table": "cliente",
  "join_table": "pedido",
  "join_on":  [["cliente.idCliente", "=", "pedido.Cliente_idCliente"]],
  "where":    [["cliente.Nome", "=", "'Joao'"]]
}
```

### Passo 3: validação contra o schema bd_vendas

```
cliente               → existe? sim ✓
pedido                → existe? sim ✓
cliente.Nome          → coluna valida? sim ✓
pedido.ValorTotalPedido → coluna valida? sim ✓
cliente.idCliente     → coluna valida? sim ✓
pedido.Cliente_idCliente → coluna valida? sim ✓
'Joao'                → literal string, ignorado ✓
```

Lista de erros: vazia → segue.

### Passo 4: classificação dos predicados

Aplicando `_predicate_tables` em cada predicado:

| Predicado | Tabelas referenciadas | Tipo |
|---|---|---|
| `cliente.idCliente = pedido.Cliente_idCliente` | `{cliente, pedido}` | multi (vira ⋈) |
| `cliente.Nome = 'Joao'` | `{cliente}` | local em `cliente` |

### Passo 5: monta o grafo do **Plano Otimizado**

```
single_table_preds = {
  cliente: [['cliente.Nome', '=', "'Joao'"]],   ← 1 predicado local
  pedido:  []                                    ← 0 predicados locais
}
multi_table_preds = [['cliente.idCliente', '=', 'pedido.Cliente_idCliente']]

→ Reordena folhas: cliente vai primeiro (mais predicados locais).
→ T0=cliente, T1=pedido.
→ T0: cria SEL_0 (Nome='Joao'), depois PROJ_0 (idCliente, Nome).
→ T1: pula SEL (sem predicado), cria PROJ_1 (Cliente_idCliente, ValorTotalPedido).
→ Multi-pred existe → JOIN com a condição (evita cartesiano).
→ PROJ_FINAL no topo (Nome, ValorTotalPedido).
```

### Passo 6: o grafo na tela

```
              π cliente.Nome, pedido.ValorTotalPedido
                          │
              ⋈ cliente.idCliente = pedido.Cliente_idCliente
            ╱                                ╲
      π idCliente, Nome              π Cliente_idCliente, ValorTotalPedido
              │                                │
      σ Nome = 'Joao'                       pedido
              │
      cliente [PRIMARIA]
```

### Passo 7: painel de heurísticas aplicadas

```
[OK]  5a-i  Reducao de Tuplas (selecao empurrada para perto das tabelas)
[OK]  5a-ii Reducao de Atributos (projecao local mantem so colunas necessarias)
[OK]  5b-i  Reordenacao de folhas (tabela 'cliente' eh a mais restritiva)
[OK]  5b-ii Evita produto cartesiano (usa JOIN com predicado)
```

### Passo 8: plano de execução textual

```
Passo 1.  Acessar a tabela 'cliente'
Passo 2.  Acessar a tabela 'pedido'
Passo 3.  Aplicar SELECAO (sigma): filtra linhas onde cliente.Nome = 'Joao'
Passo 4.  Aplicar PROJECAO (pi): mantem apenas as colunas cliente.idCliente, cliente.Nome
Passo 5.  Aplicar PROJECAO (pi): mantem apenas as colunas pedido.Cliente_idCliente, pedido.ValorTotalPedido
Passo 6.  Realizar JUNCAO (bowtie) usando cliente.idCliente = pedido.Cliente_idCliente
Passo 7.  Aplicar PROJECAO (pi): mantem apenas as colunas cliente.Nome, pedido.ValorTotalPedido
```

---

## 11. Mapeamento dos critérios de avaliação

| Critério (PDF) | Pontos | Onde está implementado |
|---|---|---|
| Interface Gráfica funcional | 1,5 | `SQLApp` em [trabalho_rafael(1)(1).py:222](trabalho_rafael(1)(1).py#L222) — toda a UI Tkinter com tema dark |
| Local para inserir SQL | 1,0 | `self.sql_editor` em [_build_ui](trabalho_rafael(1)(1).py#L289-L306) — editor Text com numeração de linhas e syntax highlight |
| String é parseada | 1,0 | `tokenize` + `SQLParser` em [linhas 60-205](trabalho_rafael(1)(1).py#L60-L205) |
| **Campos e comandos errados são validados** | 1,0 | `validate_against_schema` em [linhas 76-149](trabalho_rafael(1)(1).py#L76-L149), chamada em `_execute` e `_parse_for_graph` |
| Grafo Otimizado mostrado na GUI | 1,0 | `_show_optimal_plan_graph` (botão verde "Plano Otimizado") |
| **Ordem de execução (plano de execução)** | 1,5 | Painel "Plano de Execução" com `_describe_step` traduzindo cada passo |
| Heurística Redução de Tuplas | 1,0 | `_build_tuple_reduction_graph` em [linhas 848-907](trabalho_rafael(1)(1).py#L848-L907) |
| Heurística Redução de Atributos | 1,0 | `_build_attribute_reduction_graph` em [linhas 927-991](trabalho_rafael(1)(1).py#L927-L991) |
| **Demais Heurísticas** | 1,0 | `_build_optimal_plan_graph` — reordenação de folhas (5b-i) + evita cartesiano (5b-ii) + ajuste da árvore (5b-iii) |
| **TOTAL** | **10,0** | |

---

---

## 12. Glossário rápido

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
| **Join N-ário** | Operação de junção que combina N tabelas de uma vez, em vez de pares |
| **Left-deep tree** | Árvore de joins onde o lado esquerdo é sempre o resultado intermediário |

---

## TL;DR

- O programa parseia SQL (com **N INNER JOINs encadeados**) → **valida contra o schema bd_vendas** → executa no MySQL → desenha **4 planos de execução** em álgebra relacional.
- O plano "não otimizado" mostra **como não fazer** (× antes de σ).
- A **Redução de Tuplas** (5a-i) empurra σ para perto das tabelas → JOIN com menos linhas.
- A **Redução de Atributos** (5a-ii) empurra π para perto das tabelas → JOIN com linhas menores.
- O **Plano Otimizado** combina tudo e ainda **reordena folhas** (mais restritiva primeiro, 5b-i) e **evita cartesiano** (5b-ii), mostrando um checklist das heurísticas aplicadas e um plano de execução textual passo a passo.
- Funciona com **2, 3 ou mais tabelas** — o parser aceita uma cadeia de `INNER JOIN ... ON ...` e os 4 graph builders iteram sobre a lista de joins.
- Resultado: cobre os 10,0 pontos do enunciado.
