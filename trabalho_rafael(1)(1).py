import re
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
import mysql.connector
import json
import networkx as nx

# ─── Cores do tema ───────────────────────────────────────────────────────────
BG_DARK      = "#1e1e2e"
BG_PANEL     = "#282840"
BG_EDITOR    = "#1a1a2e"
BG_BUTTON    = "#7c3aed"
BG_BTN_HOVER = "#6d28d9"
BG_SUCCESS   = "#22c55e"
BG_ERROR     = "#ef4444"
FG_TEXT       = "#cdd6f4"
FG_DIM        = "#6c7086"
FG_ACCENT     = "#cba6f7"
FG_KEYWORD    = "#f38ba8"
FG_STRING     = "#a6e3a1"
FG_NUMBER     = "#fab387"
FG_OPERATOR   = "#89dceb"
FG_TABLE_HD   = "#b4befe"
BORDER_COLOR  = "#45475a"
SELECTION_BG  = "#45475a"

SQL_KEYWORDS = [
    "SELECT", "FROM", "WHERE", "INNER", "JOIN", "LEFT", "RIGHT", "ON",
    "AND", "OR", "NOT", "INSERT", "INTO", "VALUES", "UPDATE", "SET",
    "DELETE", "CREATE", "TABLE", "DROP", "ALTER", "ORDER", "BY",
    "GROUP", "HAVING", "LIMIT", "AS", "DISTINCT", "COUNT", "SUM",
    "AVG", "MIN", "MAX", "LIKE", "IN", "BETWEEN", "IS", "NULL",
    "ASC", "DESC", "UNION", "ALL", "EXISTS", "CASE", "WHEN", "THEN",
    "ELSE", "END"
]

# ─── Tokenizer e Parser (original) ──────────────────────────────────────────
def tokenize(sql):
    pattern = r"<=|>=|<>|=|>|<|\(|\)|,|[\w.]+"
    tokens = re.findall(pattern, sql, re.IGNORECASE)
    return [t.strip() for t in tokens]

class SQLParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, expected=None):
        token = self.peek()
        if not token:
            raise Exception(f"Unexpected end of input. Expected {expected if expected else 'more tokens'}")
        if expected and token.upper() != expected.upper():
            raise Exception(f"Expected {expected}, got {token}")
        self.pos += 1
        return token

    def parse(self):
        data = {}
        self.consume("SELECT")
        data['columns'] = self.parse_list()
        self.consume("FROM")
        data['table'] = self.consume()
        if self.peek() and self.peek().upper() == "INNER":
            self.consume("INNER")
            self.consume("JOIN")
            data['join_table'] = self.consume()
            if self.peek() and self.peek().upper() == "ON":
                self.consume("ON")
                data['join_on'] = self.parse_condition()
        if self.peek() and self.peek().upper() == "WHERE":
            self.consume("WHERE")
            data['where'] = self.parse_condition()
        return data

    def parse_list(self):
        items = []
        items.append(self.consume())
        while self.peek() == ",":
            self.consume(",")
            items.append(self.consume())
        return items

    def parse_condition(self):
        nodes = []
        while self.pos < len(self.tokens):
            token = self.peek()
            if token == "(":
                self.consume("(")
                nodes.append(self.parse_condition())
                self.consume(")")
            elif token.upper() in ["SELECT", "FROM", "WHERE", ")"]:
                break
            else:
                left = self.consume()
                op = self.consume()
                right = self.consume()
                nodes.append([left, op, right])
            if self.peek() and self.peek().upper() == "AND":
                nodes.append(self.consume().upper())
            else:
                break
        return nodes

# ─── Historico de queries ────────────────────────────────────────────────────
QUERY_HISTORY = []
HISTORY_POS = [-1]

# ─── Aplicacao principal ─────────────────────────────────────────────────────
class SQLApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SQL Query Studio")
        self.geometry("1100x750")
        self.configure(bg=BG_DARK)
        self.minsize(900, 600)

        self._build_styles()
        self._build_ui()
        self._bind_events()
        self.after(100, lambda: self.sql_editor.focus_set())

    # ── Estilos ──────────────────────────────────────────────────────────
    def _build_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(".", background=BG_DARK, foreground=FG_TEXT, borderwidth=0)
        style.configure("Dark.TFrame", background=BG_DARK)
        style.configure("Panel.TFrame", background=BG_PANEL)
        style.configure("Title.TLabel", background=BG_DARK, foreground=FG_ACCENT,
                         font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", background=BG_DARK, foreground=FG_DIM,
                         font=("Segoe UI", 9))
        style.configure("Section.TLabel", background=BG_PANEL,    # ── Heuristica: Reducao de Atributos (projection pushdown) ──────────
    def _columns_for_table(self, columns, table_name):
        result = []
        prefix = table_name.lower() + "."
        for col in columns:
            if col == "*":
                result.append(col)
            elif col.lower().startswith(prefix):
                result.append(col)
        return result

    def _build_attribute_reduction_graph(self, parsed):
        G = nx.DiGraph()

        tables = [parsed["table"]]
        if "join_table" in parsed:
            tables.append(parsed["join_table"])

        predicates = []
        if "join_on" in parsed:
            predicates.extend(self._flatten_conjunction(parsed["join_on"]))
        if "where" in parsed:
            predicates.extend(self._flatten_conjunction(parsed["where"]))

        single_table_preds = {t: [] for t in tables}
        multi_table_preds = []
        for p in predicates:
            refs = self._predicate_tables(p, tables)
            if len(refs) == 1:
                single_table_preds[next(iter(refs))].append(p)
            else:
                multi_table_preds.append(p)

        table_outputs = {}
        for i, t in enumerate(tables):
            tnode = f"T{i}"
            G.add_node(tnode, label=t, type="table", order=0)
            current = tnode

            if single_table_preds[t]:
                sel_id = f"SEL_{i}"
                cond_txt = " AND ".join(f"{p[0]} {p[1]} {p[2]}" for p in single_table_preds[t])
                G.add_node(sel_id, label=f"o  {cond_txt}", type="selection", order=1)
                G.add_edge(sel_id, current)
                current = sel_id

            # FIX: only real column refs (must contain '.') — no literals like "Joao"/"100"
            cols_for_t = self._columns_for_table(parsed["columns"], t)
            pred_cols = []
            for p in single_table_preds[t] + multi_table_preds:
                for side in (p[0], p[2]):
                    if (isinstance(side, str) and "." in side
                            and side.lower().startswith(t.lower() + ".")
                            and side not in cols_for_t
                            and side not in pred_cols):
                        pred_cols.append(side)
            all_cols = list(dict.fromkeys(cols_for_t + pred_cols)) or ["*"]

            proj_id = f"PROJ_{i}"
            G.add_node(proj_id, label=f"pi  {', '.join(all_cols)}", type="projection", order=2)
            G.add_edge(proj_id, current)
            table_outputs[t] = proj_id

        if len(tables) > 1:
            if multi_table_preds:
                cond_txt = " AND ".join(f"{p[0]} {p[1]} {p[2]}" for p in multi_table_preds)
                G.add_node("JOIN", label=f"|x|  {cond_txt}", type="join", order=3)
                for t in tables:
                    G.add_edge("JOIN", table_outputs[t])
                root = "JOIN"
            else:
                G.add_node("CART", label="X  Produto Cartesiano", type="cartesian", order=3)
                for t in tables:
                    G.add_edge("CART", table_outputs[t])
                root = "CART"
        else:
            root = table_outputs[tables[0]]

        return G, root

    # ── Layout recursivo por subarvore (evita sobreposicao) ───────────────
    def _subtree_layout(self, G, root, canvas_w, canvas_h):
        CHAR_W   = 7
        NODE_PAD = 44
        H_GAP    = 50
        V_STEP   = 105
        TOP      = 55

        def node_w(n):
            return len(G.nodes[n].get("label", n)) * CHAR_W + NODE_PAD

        memo = {}
        def sub_w(n):
            if n in memo:
                return memo[n]
            ch = list(G.successors(n))
            v = node_w(n) if not ch else max(
                node_w(n),
                sum(sub_w(c) for c in ch) + H_GAP * (len(ch) - 1)
            )
            memo[n] = v
            return v

        depths = {root: 0}
        q = [root]
        while q:
            n = q.pop(0)
            for c in G.successors(n):
                if c not in depths:
                    depths[c] = depths[n] + 1
                    q.append(c)

        effective_w = max(canvas_w - 60, sub_w(root) + 80)

        pos = {}
        def assign(n, left, right):
            pos[n] = ((left + right) / 2, TOP + depths[n] * V_STEP)
            ch = list(G.successors(n))
            if not ch:
                return
            cws = [sub_w(c) for c in ch]
            span = sum(cws) + H_GAP * (len(ch) - 1)
            cx = (left + right) / 2 - span / 2
            for c, cw in zip(ch, cws):
                assign(c, cx, cx + cw)
                cx += cw + H_GAP

        assign(root, 20, effective_w - 20)
        return pos, depths, effective_w

    # ── Janela premium de Reducao de Atributos ────────────────────────────
    def _show_attribute_reduction_graph(self):
        parsed = self._parse_for_graph()
        if parsed is None:
            return
        G, root = self._build_attribute_reduction_graph(parsed)

        NODE_H = 36
        CHAR_W = 7
        STYLES = {
            "table":      {"bg": "#1f1233", "border": FG_NUMBER,   "fg": FG_NUMBER},
            "selection":  {"bg": "#0f1e30", "border": FG_OPERATOR,  "fg": FG_OPERATOR},
            "projection": {"bg": "#0d2618", "border": FG_STRING,    "fg": FG_STRING},
            "join":       {"bg": "#1e1a08", "border": FG_TABLE_HD,  "fg": FG_TABLE_HD},
            "cartesian":  {"bg": "#2a0f0f", "border": FG_KEYWORD,   "fg": FG_KEYWORD},
        }

        win = tk.Toplevel(self)
        win.title("Heuristica - Reducao de Atributos")
        win.geometry("1180x820")
        win.configure(bg=BG_DARK)
        win.transient(self)

        tk.Label(win, text="HEURISTICA  —  REDUCAO DE ATRIBUTOS",
                 bg=BG_DARK, fg=FG_ACCENT,
                 font=("Segoe UI", 17, "bold")).pack(pady=(16, 0))
        tk.Label(win, text=f"Nos: {G.number_of_nodes()}  |  Arestas: {G.number_of_edges()}",
                 bg=BG_DARK, fg=FG_DIM, font=("Segoe UI", 9)).pack(anchor="w", padx=22)

        cf = tk.Frame(win, bg=BORDER_COLOR)
        cf.pack(fill="both", expand=True, padx=20, pady=(10, 6))
        hbar = tk.Scrollbar(cf, orient="horizontal")
        hbar.pack(side="bottom", fill="x")
        canvas = tk.Canvas(cf, bg=BG_EDITOR, highlightthickness=0,
                           xscrollcommand=hbar.set)
        canvas.pack(fill="both", expand=True, padx=1, pady=1)
        hbar.config(command=canvas.xview)

        def redraw(*_):
            canvas.delete("all")
            cw = canvas.winfo_width()
            if cw < 50:
                return
            pos, depths, eff_w = self._subtree_layout(G, root, cw, 0)
            max_y = max(y for _, y in pos.values()) + NODE_H + 40
            canvas.config(scrollregion=(0, 0, eff_w, max_y))

            for u, v in G.edges():
                x1, y1 = pos[u]
                x2, y2 = pos[v]
                mid = (y1 + y2) / 2
                canvas.create_line(x1, y1 + NODE_H // 2 + 1,
                                   x1, mid, x2, mid,
                                   x2, y2 - NODE_H // 2 - 1,
                                   fill="#50507a", width=2, joinstyle="round")
                canvas.create_line(x2, mid, x2, y2 - NODE_H // 2 - 1,
                                   fill="#7878b0", width=2,
                                   arrow="last", arrowshape=(10, 13, 4))

            for n in G.nodes():
                x, y = pos[n]
                ntype = G.nodes[n].get("type", "table")
                label = G.nodes[n].get("label", n)
                st = STYLES.get(ntype, STYLES["table"])
                bw = max(len(label) * CHAR_W + 44, 90)
                x1, y1 = x - bw / 2, y - NODE_H / 2
                x2, y2 = x + bw / 2, y + NODE_H / 2
                canvas.create_rectangle(x1 + 4, y1 + 4, x2 + 4, y2 + 4,
                                        fill="#0a0a18", outline="")
                canvas.create_rectangle(x1, y1, x2, y2,
                                        fill=st["bg"], outline=st["border"], width=2)
                canvas.create_rectangle(x1 + 2, y1 + 2, x2 - 2, y1 + 6,
                                        fill=st["border"], outline="")
                canvas.create_text(x, y + 2, text=label,
                                   fill=st["fg"],
                                   font=("Cascadia Code", 10, "bold"))

        canvas.bind("<Configure>", redraw)

        of = tk.Frame(win, bg=BG_PANEL)
        of.pack(fill="x", padx=20, pady=(0, 16))
        tk.Label(of, text="Ordem de Execucao (bottom-up)",
                 bg=BG_PANEL, fg=FG_TABLE_HD,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
        grid = tk.Frame(of, bg=BG_PANEL)
        grid.pack(fill="x", padx=10, pady=(0, 8))
        ordered = sorted(G.nodes(data=True), key=lambda x: x[1].get("order", 0))
        for idx, (nid, data) in enumerate(ordered):
            st = STYLES.get(data.get("type", "table"), {"fg": FG_TEXT})
            tk.Label(grid, text=f"{idx+1}.  {data.get('label', nid)}",
                     bg=BG_PANEL, fg=st["fg"],
                     font=("Cascadia Code", 10), anchor="w"
                     ).grid(row=idx // 2, column=idx % 2,
                            sticky="w", padx=16, pady=2)
        tk.Label(of, text="", bg=BG_PANEL).pack(pady=2)

        style.configure("Error.TLabel", background=BG_DARK, foreground=BG_ERROR,
                         font=("Segoe UI", 9, "bold"))

        style.configure("Treeview",
                         background=BG_EDITOR, foreground=FG_TEXT, rowheight=28,
                         fieldbackground=BG_EDITOR, borderwidth=0,
                         font=("Cascadia Code", 10))
        style.configure("Treeview.Heading",
                         background=BG_PANEL, foreground=FG_TABLE_HD,
                         font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("Treeview",
                   background=[("selected", SELECTION_BG)],
                   foreground=[("selected", FG_TEXT)])
        style.map("Treeview.Heading",
                   background=[("active", BG_PANEL)])

    # ── Interface ────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        header = ttk.Frame(self, style="Dark.TFrame")
        header.pack(fill="x", padx=20, pady=(18, 0))
        ttk.Label(header, text="SQL Query Studio", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="Parser + MySQL  |  bd_vendas", style="Subtitle.TLabel").pack(side="left", padx=(12, 0), pady=(6, 0))

        # ── Editor area ─────────────────────────────────────────────────
        editor_frame = ttk.Frame(self, style="Dark.TFrame")
        editor_frame.pack(fill="x", padx=20, pady=(14, 0))

        ttk.Label(editor_frame, text="EDITOR SQL", style="Section.TLabel").pack(anchor="w", pady=(0, 6))

        editor_border = tk.Frame(editor_frame, bg=BORDER_COLOR, highlightthickness=0)
        editor_border.pack(fill="x")

        editor_inner = tk.Frame(editor_border, bg=BG_EDITOR, highlightthickness=0)
        editor_inner.pack(fill="both", padx=1, pady=1)

        # Line numbers
        self.line_numbers = tk.Text(
            editor_inner, width=4, bg=BG_PANEL, fg=FG_DIM,
            font=("Cascadia Code", 12), padx=8, pady=10,
            state="disabled", cursor="arrow", relief="flat",
            selectbackground=BG_PANEL, selectforeground=FG_DIM,
            highlightthickness=0, borderwidth=0
        )
        self.line_numbers.pack(side="left", fill="y")

        self.sql_editor = tk.Text(
            editor_inner, height=6, bg=BG_EDITOR, fg=FG_TEXT,
            font=("Cascadia Code", 12), insertbackground=FG_ACCENT,
            selectbackground=SELECTION_BG, selectforeground=FG_TEXT,
            padx=10, pady=10, wrap="word", undo=True,
            relief="flat", highlightthickness=0, borderwidth=0
        )
        self.sql_editor.pack(fill="both", expand=True)

        # Placeholder
        self._placeholder_visible = True
        self.sql_editor.insert("1.0", "SELECT * FROM tabela WHERE ...")
        self.sql_editor.tag_add("placeholder", "1.0", "end")
        self.sql_editor.tag_configure("placeholder", foreground=FG_DIM)

        # ── Botoes ───────────────────────────────────────────────────────
        btn_bar = ttk.Frame(self, style="Dark.TFrame")
        btn_bar.pack(fill="x", padx=20, pady=(10, 0))

        self.btn_exec = tk.Button(
            btn_bar, text="  Executar  (Ctrl+Enter)", bg=BG_BUTTON, fg="white",
            font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
            activebackground=BG_BTN_HOVER, activeforeground="white",
            padx=18, pady=6, command=self._execute
        )
        self.btn_exec.pack(side="left")

        self.btn_clear = tk.Button(
            btn_bar, text="  Limpar", bg=BORDER_COLOR, fg=FG_TEXT,
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            activebackground=BG_PANEL, activeforeground=FG_TEXT,
            padx=14, pady=6, command=self._clear
        )
        self.btn_clear.pack(side="left", padx=(8, 0))

        self.btn_parse = tk.Button(
            btn_bar, text="  Analisar Parser", bg=BORDER_COLOR, fg=FG_TEXT,
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            activebackground=BG_PANEL, activeforeground=FG_TEXT,
            padx=14, pady=6, command=self._show_parse_tree
        )
        self.btn_parse.pack(side="left", padx=(8, 0))

        self.btn_graph = tk.Button(
            btn_bar, text="  Grafo Nao Otimizado", bg=BORDER_COLOR, fg=FG_TEXT,
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            activebackground=BG_PANEL, activeforeground=FG_TEXT,
            padx=14, pady=6, command=self._show_nonoptimized_graph
        )
        self.btn_graph.pack(side="left", padx=(8, 0))

        self.btn_tuple = tk.Button(
            btn_bar, text="  Reducao de Tuplas", bg=BORDER_COLOR, fg=FG_TEXT,
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            activebackground=BG_PANEL, activeforeground=FG_TEXT,
            padx=14, pady=6, command=self._show_tuple_reduction_graph
        )
        self.btn_tuple.pack(side="left", padx=(8, 0))

        self.btn_attr = tk.Button(
            btn_bar, text="  Reducao de Atributos", bg=BORDER_COLOR, fg=FG_TEXT,
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            activebackground=BG_PANEL, activeforeground=FG_TEXT,
            padx=14, pady=6, command=self._show_attribute_reduction_graph
        )
        self.btn_attr.pack(side="left", padx=(8, 0))

        # Status
        self.status_var = tk.StringVar(value="Pronto")
        self.status_label = ttk.Label(btn_bar, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.pack(side="right", pady=(4, 0))

        self.row_count_var = tk.StringVar()
        self.row_count_label = ttk.Label(btn_bar, textvariable=self.row_count_var, style="Status.TLabel")
        self.row_count_label.pack(side="right", padx=(0, 14), pady=(4, 0))

        # ── Painel de resultados ─────────────────────────────────────────
        results_frame = ttk.Frame(self, style="Dark.TFrame")
        results_frame.pack(fill="both", expand=True, padx=20, pady=(14, 18))

        ttk.Label(results_frame, text="RESULTADOS", style="Section.TLabel").pack(anchor="w", pady=(0, 6))

        tree_border = tk.Frame(results_frame, bg=BORDER_COLOR, highlightthickness=0)
        tree_border.pack(fill="both", expand=True)

        tree_inner = tk.Frame(tree_border, bg=BG_EDITOR, highlightthickness=0)
        tree_inner.pack(fill="both", expand=True, padx=1, pady=1)

        # Scrollbars
        y_scroll = ttk.Scrollbar(tree_inner, orient="vertical")
        y_scroll.pack(side="right", fill="y")
        x_scroll = ttk.Scrollbar(tree_inner, orient="horizontal")
        x_scroll.pack(side="bottom", fill="x")

        self.tree = ttk.Treeview(
            tree_inner, show="headings",
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set
        )
        self.tree.pack(fill="both", expand=True)
        y_scroll.config(command=self.tree.yview)
        x_scroll.config(command=self.tree.xview)

        # Tag para linhas alternadas
        self.tree.tag_configure("odd", background="#1f1f35")
        self.tree.tag_configure("even", background=BG_EDITOR)

        # Mensagem vazia
        self.empty_label = tk.Label(
            tree_inner, text="Nenhum resultado ainda.\nDigite uma query e pressione Executar.",
            bg=BG_EDITOR, fg=FG_DIM, font=("Segoe UI", 11), justify="center"
        )
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")

    # ── Bindings ─────────────────────────────────────────────────────────
    def _bind_events(self):
        self.sql_editor.bind("<Control-Return>", lambda e: (self._execute(), "break"))
        self.sql_editor.bind("<KeyRelease>", self._on_key_release)
        self.sql_editor.bind("<FocusIn>", self._on_focus_in)
        self.sql_editor.bind("<FocusOut>", self._on_focus_out)
        self.sql_editor.bind("<Up>", self._history_prev)
        self.sql_editor.bind("<Down>", self._history_next)

        # Hover nos botoes
        for btn, bg_normal in [(self.btn_exec, BG_BUTTON), (self.btn_clear, BORDER_COLOR),
                                (self.btn_parse, BORDER_COLOR), (self.btn_graph, BORDER_COLOR),
                                (self.btn_tuple, BORDER_COLOR), (self.btn_attr, BORDER_COLOR)]:
            hover = BG_BTN_HOVER if btn == self.btn_exec else BG_PANEL
            btn.bind("<Enter>", lambda e, b=btn, h=hover: b.configure(bg=h))
            btn.bind("<Leave>", lambda e, b=btn, n=bg_normal: b.configure(bg=n))

    # ── Placeholder ──────────────────────────────────────────────────────
    def _on_focus_in(self, event):
        if self._placeholder_visible:
            self.sql_editor.delete("1.0", "end")
            self._placeholder_visible = False

    def _on_focus_out(self, event):
        if not self.sql_editor.get("1.0", "end").strip():
            self._placeholder_visible = True
            self.sql_editor.insert("1.0", "SELECT * FROM tabela WHERE ...")
            self.sql_editor.tag_add("placeholder", "1.0", "end")

    # ── Syntax highlight ─────────────────────────────────────────────────
    def _on_key_release(self, event):
        if self._placeholder_visible:
            return
        self._highlight_syntax()
        self._update_line_numbers()

    def _highlight_syntax(self):
        editor = self.sql_editor
        content = editor.get("1.0", "end-1c")

        for tag in ("keyword", "string", "number", "operator"):
            editor.tag_remove(tag, "1.0", "end")

        editor.tag_configure("keyword", foreground=FG_KEYWORD, font=("Cascadia Code", 12, "bold"))
        editor.tag_configure("string", foreground=FG_STRING)
        editor.tag_configure("number", foreground=FG_NUMBER)
        editor.tag_configure("operator", foreground=FG_OPERATOR)

        # Keywords
        for kw in SQL_KEYWORDS:
            pattern = r'\b' + kw + r'\b'
            for m in re.finditer(pattern, content, re.IGNORECASE):
                start = f"1.0+{m.start()}c"
                end = f"1.0+{m.end()}c"
                editor.tag_add("keyword", start, end)

        # Strings
        for m in re.finditer(r"'[^']*'", content):
            start = f"1.0+{m.start()}c"
            end = f"1.0+{m.end()}c"
            editor.tag_add("string", start, end)

        # Numbers
        for m in re.finditer(r'\b\d+\.?\d*\b', content):
            start = f"1.0+{m.start()}c"
            end = f"1.0+{m.end()}c"
            editor.tag_add("number", start, end)

        # Operators
        for m in re.finditer(r'<=|>=|<>|[=<>]', content):
            start = f"1.0+{m.start()}c"
            end = f"1.0+{m.end()}c"
            editor.tag_add("operator", start, end)

    def _update_line_numbers(self):
        self.line_numbers.config(state="normal")
        self.line_numbers.delete("1.0", "end")
        line_count = int(self.sql_editor.index("end-1c").split(".")[0])
        lines = "\n".join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.insert("1.0", lines)
        self.line_numbers.config(state="disabled")

    # ── Historico ────────────────────────────────────────────────────────
    def _history_prev(self, event):
        if not QUERY_HISTORY:
            return
        if HISTORY_POS[0] < len(QUERY_HISTORY) - 1:
            HISTORY_POS[0] += 1
        self.sql_editor.delete("1.0", "end")
        self.sql_editor.insert("1.0", QUERY_HISTORY[-(HISTORY_POS[0] + 1)])
        self._placeholder_visible = False
        self._highlight_syntax()

    def _history_next(self, event):
        if HISTORY_POS[0] > 0:
            HISTORY_POS[0] -= 1
            self.sql_editor.delete("1.0", "end")
            self.sql_editor.insert("1.0", QUERY_HISTORY[-(HISTORY_POS[0] + 1)])
            self._highlight_syntax()
        elif HISTORY_POS[0] == 0:
            HISTORY_POS[0] = -1
            self.sql_editor.delete("1.0", "end")

    # ── Limpar ───────────────────────────────────────────────────────────
    def _clear(self):
        self.sql_editor.delete("1.0", "end")
        self._placeholder_visible = False
        self.tree["columns"] = ()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        self.status_var.set("Pronto")
        self.status_label.configure(style="Status.TLabel")
        self.row_count_var.set("")
        self._update_line_numbers()
        self.sql_editor.focus_set()

    # ── Executar query ───────────────────────────────────────────────────
    def _execute(self):
        query = self.sql_editor.get("1.0", "end").strip()
        if not query or self._placeholder_visible:
            return

        # Limpar tabela
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.empty_label.place_forget()

        # 1) Parse
        try:
            tokens = tokenize(query)
            parser = SQLParser(tokens)
            parsed = parser.parse()
            table_name = parsed.get('table', '?')
        except Exception as e:
            self.status_var.set(f"Parser Error: {e}")
            self.status_label.configure(style="Error.TLabel")
            self.row_count_var.set("")
            return

        # 2) Executar no MySQL
        try:
            db = mysql.connector.connect(
                host="localhost",
                user="root",
                password="132654",
                database="bd_vendas"
            )
            cursor = db.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description] if cursor.description else []

            # Salvar no historico
            if query not in QUERY_HISTORY:
                QUERY_HISTORY.append(query)
            HISTORY_POS[0] = -1

            # Montar tabela
            if col_names:
                self.tree["columns"] = col_names
                for col in col_names:
                    self.tree.heading(col, text=col.upper(), anchor="w")
                    self.tree.column(col, anchor="w", minwidth=100, width=150)

            for i, row in enumerate(results):
                tag = "odd" if i % 2 == 0 else "even"
                self.tree.insert("", "end", values=row, tags=(tag,))

            count = len(results)
            self.row_count_var.set(f"{count} linha{'s' if count != 1 else ''}")
            self.status_var.set(f"OK  -  Tabela: {table_name}")
            self.status_label.configure(style="Success.TLabel")

            if count == 0:
                self.empty_label.config(text="Query executada com sucesso.\n0 resultados retornados.")
                self.empty_label.place(relx=0.5, rely=0.5, anchor="center")

        except mysql.connector.Error as err:
            self.status_var.set(f"MySQL Error: {err}")
            self.status_label.configure(style="Error.TLabel")
            self.row_count_var.set("")
            self.empty_label.config(text=f"Erro ao executar query.\n{err}")
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        finally:
            if 'db' in locals() and db.is_connected():
                cursor.close()
                db.close()

    # ── Mostrar arvore do parser ─────────────────────────────────────────
    def _show_parse_tree(self):
        query = self.sql_editor.get("1.0", "end").strip()
        if not query or self._placeholder_visible:
            return

        try:
            tokens = tokenize(query)
            parser = SQLParser(tokens)
            parsed = parser.parse()
        except Exception as e:
            messagebox.showerror("Parser Error", str(e))
            return

        # Janela de analise
        win = tk.Toplevel(self)
        win.title("Analise do Parser")
        win.geometry("600x500")
        win.configure(bg=BG_DARK)
        win.transient(self)

        ttk.Label(win, text="ARVORE SINTATICA", style="Title.TLabel").pack(padx=20, pady=(16, 4))
        ttk.Label(win, text=f"Tokens: {len(tokens)}", style="Subtitle.TLabel").pack(padx=20, anchor="w")

        # Tokens
        token_frame = tk.Frame(win, bg=BG_PANEL, highlightthickness=0)
        token_frame.pack(fill="x", padx=20, pady=(10, 0))

        tk.Label(token_frame, text="Tokens", bg=BG_PANEL, fg=FG_TABLE_HD,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(8, 4))

        token_canvas = tk.Frame(token_frame, bg=BG_PANEL)
        token_canvas.pack(fill="x", padx=10, pady=(0, 10))

        col = 0
        row = 0
        for t in tokens:
            is_kw = t.upper() in SQL_KEYWORDS
            bg = FG_KEYWORD if is_kw else BORDER_COLOR
            fg = "white" if is_kw else FG_TEXT
            lbl = tk.Label(token_canvas, text=t, bg=bg, fg=fg,
                           font=("Cascadia Code", 9), padx=6, pady=2)
            lbl.grid(row=row, column=col, padx=2, pady=2)
            col += 1
            if col > 8:
                col = 0
                row += 1

        # Parsed JSON
        json_frame = tk.Frame(win, bg=BG_PANEL, highlightthickness=0)
        json_frame.pack(fill="both", expand=True, padx=20, pady=(10, 18))

        tk.Label(json_frame, text="Estrutura Parseada", bg=BG_PANEL, fg=FG_TABLE_HD,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(8, 4))

        json_text = tk.Text(
            json_frame, bg=BG_EDITOR, fg=FG_STRING,
            font=("Cascadia Code", 11), relief="flat",
            padx=12, pady=10, wrap="word", highlightthickness=0
        )
        json_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        json_text.insert("1.0", json.dumps(parsed, indent=2, ensure_ascii=False))
        json_text.config(state="disabled")

    # ── Grafo nao otimizado ──────────────────────────────────────────────
    def _format_condition(self, cond):
        if isinstance(cond, list):
            if len(cond) == 3 and all(isinstance(x, str) for x in cond):
                return f"{cond[0]} {cond[1]} {cond[2]}"
            parts = []
            for item in cond:
                if isinstance(item, str) and item.upper() in ("AND", "OR"):
                    parts.append(item.upper())
                else:
                    parts.append(self._format_condition(item))
            return " ".join(parts)
        return str(cond)

    def _build_nonoptimized_graph(self, parsed):
        G = nx.DiGraph()

        tables = [parsed["table"]]
        if "join_table" in parsed:
            tables.append(parsed["join_table"])

        table_nodes = []
        for i, t in enumerate(tables):
            nid = f"T{i}"
            G.add_node(nid, label=t, type="table", order=0)
            table_nodes.append(nid)

        order_counter = 1
        if len(tables) > 1:
            cart_id = "CART"
            G.add_node(cart_id, label="X  Produto Cartesiano", type="cartesian", order=order_counter)
            for tn in table_nodes:
                G.add_edge(cart_id, tn)
            current = cart_id
            order_counter += 1
        else:
            current = table_nodes[0]

        conditions = []
        if "join_on" in parsed:
            conditions.append(self._format_condition(parsed["join_on"]))
        if "where" in parsed:
            conditions.append(self._format_condition(parsed["where"]))
        conditions = [c for c in conditions if c]

        if conditions:
            sel_id = "SEL"
            cond_txt = " AND ".join(conditions)
            G.add_node(sel_id, label=f"o  {cond_txt}", type="selection", order=order_counter)
            G.add_edge(sel_id, current)
            current = sel_id
            order_counter += 1

        proj_id = "PROJ"
        cols_txt = ", ".join(parsed["columns"])
        G.add_node(proj_id, label=f"pi  {cols_txt}", type="projection", order=order_counter)
        G.add_edge(proj_id, current)

        return G, proj_id

    def _hierarchical_layout(self, G, root, width=900, height=520):
        levels = {root: 0}
        queue = [root]
        while queue:
            n = queue.pop(0)
            for child in G.successors(n):
                if child not in levels:
                    levels[child] = levels[n] + 1
                    queue.append(child)

        by_level = {}
        for n, l in levels.items():
            by_level.setdefault(l, []).append(n)

        max_level = max(by_level.keys()) if by_level else 0
        pos = {}
        for l, nodes in by_level.items():
            y = 60 + (l / max(max_level, 1)) * (height - 120)
            for i, n in enumerate(sorted(nodes)):
                x = (i + 1) * width / (len(nodes) + 1)
                pos[n] = (x, y)
        return pos

    def _render_graph_window(self, title, G, root):
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("960x720")
        win.configure(bg=BG_DARK)
        win.transient(self)

        ttk.Label(win, text=title.upper(), style="Title.TLabel").pack(padx=20, pady=(16, 4))
        ttk.Label(win, text=f"Nos: {G.number_of_nodes()}  |  Arestas: {G.number_of_edges()}",
                  style="Subtitle.TLabel").pack(padx=20, anchor="w")

        canvas_border = tk.Frame(win, bg=BORDER_COLOR, highlightthickness=0)
        canvas_border.pack(fill="both", expand=True, padx=20, pady=(12, 8))

        canvas = tk.Canvas(canvas_border, bg=BG_EDITOR, highlightthickness=0)
        canvas.pack(fill="both", expand=True, padx=1, pady=1)

        color_map = {
            "table": FG_NUMBER,
            "cartesian": FG_KEYWORD,
            "selection": FG_OPERATOR,
            "projection": FG_STRING,
            "join": FG_TABLE_HD,
        }

        def redraw(*_args):
            canvas.delete("all")
            w_c = canvas.winfo_width()
            h_c = canvas.winfo_height()
            if w_c < 50 or h_c < 50:
                return
            pos = self._hierarchical_layout(G, root, w_c, h_c)

            for u, v in G.edges():
                x1, y1 = pos[u]
                x2, y2 = pos[v]
                canvas.create_line(x1, y1 + 18, x2, y2 - 18,
                                   fill=FG_DIM, width=2, arrow="last")

            for n in G.nodes():
                x, y = pos[n]
                ntype = G.nodes[n].get("type", "table")
                label = G.nodes[n].get("label", n)
                color = color_map.get(ntype, FG_TEXT)
                box_w = max(len(label) * 7 + 24, 80)
                canvas.create_rectangle(x - box_w / 2, y - 18, x + box_w / 2, y + 18,
                                        fill=BG_PANEL, outline=color, width=2)
                canvas.create_text(x, y, text=label, fill=color,
                                   font=("Cascadia Code", 10, "bold"))

        canvas.bind("<Configure>", redraw)

        order_frame = tk.Frame(win, bg=BG_PANEL, highlightthickness=0)
        order_frame.pack(fill="x", padx=20, pady=(0, 18))

        tk.Label(order_frame, text="Ordem de Execucao (bottom-up)",
                 bg=BG_PANEL, fg=FG_TABLE_HD,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(8, 4))

        exec_order = sorted(G.nodes(data=True), key=lambda x: x[1].get("order", 0))
        for i, (nid, data) in enumerate(exec_order, 1):
            tk.Label(order_frame, text=f"{i}. {data.get('label', nid)}",
                     bg=BG_PANEL, fg=FG_TEXT,
                     font=("Cascadia Code", 10)).pack(anchor="w", padx=20)
        tk.Label(order_frame, text="", bg=BG_PANEL).pack(pady=2)

    def _parse_for_graph(self):
        query = self.sql_editor.get("1.0", "end").strip()
        if not query or self._placeholder_visible:
            return None
        try:
            tokens = tokenize(query)
            return SQLParser(tokens).parse()
        except Exception as e:
            messagebox.showerror("Parser Error", str(e))
            return None

    def _show_nonoptimized_graph(self):
        parsed = self._parse_for_graph()
        if parsed is None:
            return
        G, root = self._build_nonoptimized_graph(parsed)
        self._render_graph_window("Grafo de Execucao - Nao Otimizado", G, root)

    # ── Heuristica: Reducao de Tuplas (selection pushdown) ───────────────
    def _flatten_conjunction(self, cond):
        if not cond:
            return []
        if isinstance(cond, list):
            if len(cond) == 3 and all(isinstance(x, str) for x in cond):
                return [cond]
            result = []
            for item in cond:
                if isinstance(item, str):
                    continue
                result.extend(self._flatten_conjunction(item))
            return result
        return []

    def _predicate_tables(self, pred, table_names):
        refs = set()
        lower_tables = {t.lower(): t for t in table_names}
        for side in (pred[0], pred[2]):
            if isinstance(side, str) and "." in side:
                prefix = side.split(".", 1)[0].lower()
                if prefix in lower_tables:
                    refs.add(lower_tables[prefix])
        return refs

    def _build_tuple_reduction_graph(self, parsed):
        G = nx.DiGraph()

        tables = [parsed["table"]]
        if "join_table" in parsed:
            tables.append(parsed["join_table"])

        predicates = []
        if "join_on" in parsed:
            predicates.extend(self._flatten_conjunction(parsed["join_on"]))
        if "where" in parsed:
            predicates.extend(self._flatten_conjunction(parsed["where"]))

        single_table_preds = {t: [] for t in tables}
        multi_table_preds = []
        for p in predicates:
            refs = self._predicate_tables(p, tables)
            if len(refs) == 1:
                single_table_preds[next(iter(refs))].append(p)
            else:
                multi_table_preds.append(p)

        table_outputs = {}
        for i, t in enumerate(tables):
            tnode = f"T{i}"
            G.add_node(tnode, label=t, type="table", order=0)
            if single_table_preds[t]:
                sel_id = f"SEL_{i}"
                cond_txt = " AND ".join(f"{p[0]} {p[1]} {p[2]}" for p in single_table_preds[t])
                G.add_node(sel_id, label=f"o  {cond_txt}", type="selection", order=1)
                G.add_edge(sel_id, tnode)
                table_outputs[t] = sel_id
            else:
                table_outputs[t] = tnode

        order = 2
        if len(tables) > 1:
            if multi_table_preds:
                join_id = "JOIN"
                cond_txt = " AND ".join(f"{p[0]} {p[1]} {p[2]}" for p in multi_table_preds)
                G.add_node(join_id, label=f"|x|  {cond_txt}", type="join", order=order)
                for t in tables:
                    G.add_edge(join_id, table_outputs[t])
                current = join_id
            else:
                cart_id = "CART"
                G.add_node(cart_id, label="X  Produto Cartesiano", type="cartesian", order=order)
                for t in tables:
                    G.add_edge(cart_id, table_outputs[t])
                current = cart_id
            order += 1
        else:
            current = table_outputs[tables[0]]

        proj_id = "PROJ"
        cols_txt = ", ".join(parsed["columns"])
        G.add_node(proj_id, label=f"pi  {cols_txt}", type="projection", order=order)
        G.add_edge(proj_id, current)

        return G, proj_id

    def _show_tuple_reduction_graph(self):
        parsed = self._parse_for_graph()
        if parsed is None:
            return
        G, root = self._build_tuple_reduction_graph(parsed)
        self._render_graph_window("Heuristica - Reducao de Tuplas", G, root)

    # ── Heuristica: Reducao de Atributos (projection pushdown) ──────────
    def _columns_for_table(self, columns, table_name):
        """Retorna as colunas do SELECT que pertencem a uma tabela especifica."""
        result = []
        prefix = table_name.lower() + "."
        for col in columns:
            if col == "*":
                result.append(col)
            elif col.lower().startswith(prefix):
                result.append(col)
        return result

    def _build_attribute_reduction_graph(self, parsed):
        """
        Heuristica de Reducao de Atributos:
        - O pi (projecao) desce logo acima de cada sigma (selecao),
          projetando apenas os atributos necessarios para aquela tabela.
        - O JOIN fica no TOPO, acima dos ramos ja projetados.
        Estrutura resultante (com JOIN):
            JOIN
            ├── pi <cols_t0>          pi <cols_t1>
            │     └── sigma (t0)            └── sigma (t1)
            │           └── T0                    └── T1
        """
        G = nx.DiGraph()

        tables = [parsed["table"]]
        if "join_table" in parsed:
            tables.append(parsed["join_table"])

        # Separar predicados por tabela (igual a reducao de tuplas)
        predicates = []
        if "join_on" in parsed:
            predicates.extend(self._flatten_conjunction(parsed["join_on"]))
        if "where" in parsed:
            predicates.extend(self._flatten_conjunction(parsed["where"]))

        single_table_preds = {t: [] for t in tables}
        multi_table_preds = []
        for p in predicates:
            refs = self._predicate_tables(p, tables)
            if len(refs) == 1:
                single_table_preds[next(iter(refs))].append(p)
            else:
                multi_table_preds.append(p)

        # Para cada tabela: T -> sigma -> pi  (pi logo acima do sigma)
        order_counter = [0]
        table_outputs = {}  # topo de cada ramo apos projecao

        for i, t in enumerate(tables):
            # No da tabela
            tnode = f"T{i}"
            G.add_node(tnode, label=t, type="table", order=0)
            current = tnode

            # Sigma (se houver predicado para esta tabela)
            if single_table_preds[t]:
                sel_id = f"SEL_{i}"
                cond_txt = " AND ".join(f"{p[0]} {p[1]} {p[2]}" for p in single_table_preds[t])
                G.add_node(sel_id, label=f"o  {cond_txt}", type="selection", order=1)
                G.add_edge(sel_id, current)
                current = sel_id

            # Pi logo acima do sigma (projecao empurrada para baixo)
            cols_for_t = self._columns_for_table(parsed["columns"], t)
            # Incluir tambem colunas usadas no join/where desta tabela
            pred_cols = []
            for p in single_table_preds[t]:
                for side in (p[0], p[2]):
                    if isinstance(side, str) and side not in pred_cols:
                        pred_cols.append(side)
            for p in multi_table_preds:
                for side in (p[0], p[2]):
                    if isinstance(side, str) and side.lower().startswith(t.lower() + ".") and side not in pred_cols:
                        pred_cols.append(side)
            all_cols_for_t = list(dict.fromkeys(cols_for_t + pred_cols))  # sem duplicatas
            if not all_cols_for_t:
                all_cols_for_t = ["*"]

            proj_id = f"PROJ_{i}"
            cols_txt = ", ".join(all_cols_for_t)
            G.add_node(proj_id, label=f"pi  {cols_txt}", type="projection", order=2)
            G.add_edge(proj_id, current)
            table_outputs[t] = proj_id

        # JOIN (ou Produto Cartesiano) no topo
        if len(tables) > 1:
            if multi_table_preds:
                join_id = "JOIN"
                cond_txt = " AND ".join(f"{p[0]} {p[1]} {p[2]}" for p in multi_table_preds)
                G.add_node(join_id, label=f"|x|  {cond_txt}", type="join", order=3)
                for t in tables:
                    G.add_edge(join_id, table_outputs[t])
                root = join_id
            else:
                cart_id = "CART"
                G.add_node(cart_id, label="X  Produto Cartesiano", type="cartesian", order=3)
                for t in tables:
                    G.add_edge(cart_id, table_outputs[t])
                root = cart_id
        else:
            root = table_outputs[tables[0]]

        return G, root

    def _show_attribute_reduction_graph(self):
        parsed = self._parse_for_graph()
        if parsed is None:
            return
        G, root = self._build_attribute_reduction_graph(parsed)
        self._render_graph_window("Heuristica - Reducao de Atributos", G, root)


# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = SQLApp()
    app.mainloop()