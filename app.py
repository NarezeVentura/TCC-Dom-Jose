import os
import sqlite3
from datetime import datetime, timedelta

from flask import Flask, jsonify, request


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(BASE_DIR, "front end")
db_path = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "sistema_vendas.db"))
CATEGORIA_VENDA = "Produtos para venda"
CATEGORIA_MATERIA_PRIMA = "Matéria prima"
CATEGORIAS_PRODUTO = (CATEGORIA_VENDA, CATEGORIA_MATERIA_PRIMA)

CATALOGO_PRODUTOS = [
    ("Trufas", 2.20, 6.00, CATEGORIA_VENDA),
    ("Cones", 3.50, 12.00, CATEGORIA_VENDA),
    
    ("Cone + Trufa", 5.70, 17.00, CATEGORIA_VENDA),
    ("Combo 2 Cones", 7.00, 22.00, CATEGORIA_VENDA),
    ("Combo 3 Trufas", 6.60, 16.00, CATEGORIA_VENDA),
    ("2 Cones + Trufa", 8.70, 27.00, CATEGORIA_VENDA),
    ("Cone + 2 Trufas", 7.90, 24.00, CATEGORIA_VENDA),
    ("2 Cones + 2 Trufas", 11.40, 32.00, CATEGORIA_VENDA),
]
NOMES_CATALOGO = tuple(produto[0] for produto in CATALOGO_PRODUTOS)
NOMES_LEGADOS_OCULTOS = (
    "cone tradicional",
    "cone de nutella",
    "trufa",
    "trufa de nutella",
    "combo cone + trufa",
    "combo cone + trufa (bueno, bueno)",
    "combo cone + trufa (nutella, bueno)",
    "combo 2 cones + 2 trufas",
)

app = Flask(__name__, static_folder=frontend_dir, static_url_path="/")


def remover_dados_expirados():
    conn = get_connection()
    try:
        limite = (datetime.now() - timedelta(days=35)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            """
            DELETE FROM vendas
            WHERE datetime(data) < datetime(?)
               OR id_fechamento IN (
                    SELECT id_fechamento
                    FROM fechamentos_diarios
                    WHERE datetime(data_emissao) < datetime(?)
               )
            """,
            (limite, limite),
        )
        conn.execute(
            "DELETE FROM fechamentos_diarios WHERE datetime(data_emissao) < datetime(?)",
            (limite,),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@app.before_request
def limpar_dados_expirados_antes_da_requisicao():
    remover_dados_expirados()


@app.after_request
def adicionar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def get_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _has_column(conn, table_name, column_name):
    columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(column["name"] == column_name for column in columns)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS vendedores (
            id_vendedor INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS produtos (
            id_produto INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            preco_producao REAL NOT NULL,
            preco_venda REAL NOT NULL,
            categoria TEXT DEFAULT 'geral'
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS vendas (
            id_venda INTEGER PRIMARY KEY AUTOINCREMENT,
            id_vendedor INTEGER NOT NULL,
            id_produto INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            id_fechamento INTEGER,
            observacao TEXT,
            FOREIGN KEY (id_vendedor) REFERENCES vendedores(id_vendedor),
            FOREIGN KEY (id_produto) REFERENCES produtos(id_produto)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS fechamentos_diarios (
            id_fechamento INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_vendedor TEXT NOT NULL,
            total_faturamento REAL NOT NULL DEFAULT 0,
            total_lucro REAL NOT NULL DEFAULT 0,
            total_comissao REAL NOT NULL DEFAULT 0,
            data_emissao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            observacoes TEXT
        )
        """
    )

    if not _has_column(conn, "vendas", "id_fechamento"):
        cursor.execute("ALTER TABLE vendas ADD COLUMN id_fechamento INTEGER")
    if not _has_column(conn, "vendas", "observacao"):
        cursor.execute("ALTER TABLE vendas ADD COLUMN observacao TEXT")
    if not _has_column(conn, "vendas", "preco_venda"):
        cursor.execute("ALTER TABLE vendas ADD COLUMN preco_venda REAL")
    if not _has_column(conn, "vendas", "preco_producao"):
        cursor.execute("ALTER TABLE vendas ADD COLUMN preco_producao REAL")
    if not _has_column(conn, "produtos", "categoria"):
        cursor.execute("ALTER TABLE produtos ADD COLUMN categoria TEXT DEFAULT 'geral'")

    cursor.execute("SELECT COUNT(*) FROM vendedores")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO vendedores (nome) VALUES ('Pedro')")
        cursor.execute("INSERT INTO vendedores (nome) VALUES ('Nicole')")

    for produto in CATALOGO_PRODUTOS:
        cursor.execute("SELECT 1 FROM produtos WHERE lower(tipo) = lower(?)", (produto[0],))
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO produtos (tipo, preco_producao, preco_venda, categoria) VALUES (?, ?, ?, ?)",
                produto,
            )

    for tipo, _, _, _ in CATALOGO_PRODUTOS:
        cursor.execute(
            """
            UPDATE produtos
            SET tipo = ?
            WHERE lower(tipo) = lower(?) AND tipo != ?
            """,
            (tipo, tipo, tipo),
        )

    cursor.execute(
        "DELETE FROM produtos WHERE categoria = ? OR lower(tipo) LIKE ? OR lower(tipo) LIKE ?",
        ("Mão de obra", "mão de obra%", "mao de obra%"),
    )
    cursor.execute(
        """
        UPDATE produtos
        SET categoria = ?
        WHERE lower(categoria) IN (?, ?)
        """,
        (CATEGORIA_MATERIA_PRIMA, "produtos de materia prima", "materia prima"),
    )
    cursor.execute(
        """
        UPDATE produtos
        SET categoria = ?
        WHERE categoria IS NULL OR lower(categoria) NOT IN (?, ?)
        """,
        (CATEGORIA_VENDA, CATEGORIA_VENDA.lower(), CATEGORIA_MATERIA_PRIMA.lower()),
    )

    conn.commit()
    conn.close()


init_db()
remover_dados_expirados()


def calcular_relatorio(tipo_relatorio):
    conn = get_connection()
    cursor = conn.cursor()

    hoje = datetime.now()
    if tipo_relatorio == "diario":
        where_clause = "DATE(data_emissao) = DATE(?)"
        params = [hoje.date().isoformat()]
    elif tipo_relatorio == "semanal":
        where_clause = "data_emissao >= ?"
        params = [hoje - timedelta(days=6)]
    elif tipo_relatorio == "mensal":
        where_clause = "strftime('%Y-%m', data_emissao) = ?"
        params = [hoje.strftime('%Y-%m')]
    else:
        where_clause = "1=1"
        params = []

    cursor.execute(
        f"""
        SELECT COALESCE(SUM(total_faturamento), 0) AS faturamento,
               COALESCE(SUM(total_lucro), 0) AS lucro,
               COALESCE(SUM(total_comissao), 0) AS comissao
        FROM fechamentos_diarios
        WHERE {where_clause}
        """,
        params,
    )
    resultado = cursor.fetchone()
    conn.close()

    return {
        "faturamento": round(float(resultado["faturamento"] or 0), 2),
        "lucro": round(float(resultado["lucro"] or 0), 2),
        "comissao": round(float(resultado["comissao"] or 0), 2),
    }


@app.route("/", methods=["GET"])
def index():
    return app.send_static_file("index.html")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Backend pronto para o frontend"})


@app.route("/api/vendedores", methods=["GET"])
def listar_vendedores():
    conn = get_connection()
    vendedores = conn.execute("SELECT id_vendedor, nome FROM vendedores ORDER BY id_vendedor").fetchall()
    conn.close()
    return jsonify([{"id": row["id_vendedor"], "nome": row["nome"]} for row in vendedores])


@app.route("/api/vendedores", methods=["POST"])
def criar_vendedor():
    dados = request.get_json(silent=True) or {}
    nome = (dados.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome do vendedor"}), 400

    conn = get_connection()
    try:
        if conn.execute("SELECT 1 FROM vendedores WHERE lower(nome) = lower(?)", (nome,)).fetchone():
            return jsonify({"error": "Já existe um vendedor com esse nome"}), 409
        cursor = conn.execute("INSERT INTO vendedores (nome) VALUES (?)", (nome,))
        conn.commit()
        return jsonify({"id": cursor.lastrowid, "nome": nome}), 201
    finally:
        conn.close()


@app.route("/api/vendedores/<int:vendedor_id>", methods=["PUT"])
def editar_vendedor(vendedor_id):
    dados = request.get_json(silent=True) or {}
    nome = (dados.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome do vendedor"}), 400

    conn = get_connection()
    try:
        if not conn.execute("SELECT 1 FROM vendedores WHERE id_vendedor = ?", (vendedor_id,)).fetchone():
            return jsonify({"error": "Vendedor não encontrado"}), 404
        if conn.execute(
            "SELECT 1 FROM vendedores WHERE lower(nome) = lower(?) AND id_vendedor != ?",
            (nome, vendedor_id),
        ).fetchone():
            return jsonify({"error": "Já existe um vendedor com esse nome"}), 409
        conn.execute("UPDATE vendedores SET nome = ? WHERE id_vendedor = ?", (nome, vendedor_id))
        conn.commit()
        return jsonify({"id": vendedor_id, "nome": nome})
    finally:
        conn.close()


@app.route("/api/vendedores/<int:vendedor_id>", methods=["DELETE"])
def excluir_vendedor(vendedor_id):
    conn = get_connection()
    try:
        if not conn.execute("SELECT 1 FROM vendedores WHERE id_vendedor = ?", (vendedor_id,)).fetchone():
            return jsonify({"error": "Vendedor não encontrado"}), 404
        if conn.execute("SELECT 1 FROM vendas WHERE id_vendedor = ?", (vendedor_id,)).fetchone():
            return jsonify({"error": "Não é possível excluir um vendedor com vendas registradas"}), 409
        conn.execute("DELETE FROM vendedores WHERE id_vendedor = ?", (vendedor_id,))
        conn.commit()
        return jsonify({"message": "Vendedor excluído com sucesso"})
    finally:
        conn.close()


@app.route("/api/produtos", methods=["GET"])
def listar_produtos():
    conn = get_connection()
    produtos = conn.execute(
                """
                SELECT id_produto, tipo, preco_producao, preco_venda, categoria
                FROM produtos
                WHERE categoria != ?
                    AND lower(tipo) NOT LIKE ?
                    AND lower(tipo) NOT LIKE ?
                    AND lower(tipo) NOT IN (?, ?, ?, ?, ?, ?, ?, ?)
                ORDER BY id_produto
                """,
                ("Mão de obra", "mão de obra%", "mao de obra%", *NOMES_LEGADOS_OCULTOS),
    ).fetchall()
    conn.close()
    return jsonify(
        [
            {
                "id": row["id_produto"],
                "tipo": row["tipo"],
                "preco_producao": row["preco_producao"],
                "preco_venda": row["preco_venda"],
                "categoria": row["categoria"],
            }
            for row in produtos
        ]
    )


def _dados_produto(dados, produto_atual=None):
    tipo = (dados.get("tipo") or dados.get("nome") or (produto_atual["tipo"] if produto_atual else "")).strip()
    categoria = (dados.get("categoria") or (produto_atual["categoria"] if produto_atual else CATEGORIA_VENDA)).strip()
    try:
        preco_producao = float(dados.get("preco_producao", produto_atual["preco_producao"] if produto_atual else 0))
        preco_venda = float(dados.get("preco_venda", produto_atual["preco_venda"] if produto_atual else 0))
    except (TypeError, ValueError):
        return None, "Os preços devem ser numéricos"
    if not tipo:
        return None, "Informe o nome do produto"
    if categoria not in CATEGORIAS_PRODUTO:
        return None, "Selecione uma categoria válida"
    if preco_producao < 0 or preco_venda <= 0:
        return None, "Informe preços válidos"
    return (tipo, preco_producao, preco_venda, categoria or "geral"), None


@app.route("/api/produtos", methods=["POST"])
def criar_produto():
    dados = request.get_json(silent=True) or {}
    produto, erro = _dados_produto(dados)
    if erro:
        return jsonify({"error": erro}), 400

    conn = get_connection()
    try:
        if conn.execute("SELECT 1 FROM produtos WHERE lower(tipo) = lower(?)", (produto[0],)).fetchone():
            return jsonify({"error": "Já existe um produto com esse nome"}), 409
        cursor = conn.execute(
            "INSERT INTO produtos (tipo, preco_producao, preco_venda, categoria) VALUES (?, ?, ?, ?)",
            produto,
        )
        conn.commit()
        return jsonify({"id": cursor.lastrowid, "tipo": produto[0], "preco_producao": produto[1], "preco_venda": produto[2], "categoria": produto[3]}), 201
    finally:
        conn.close()


@app.route("/api/produtos/<int:produto_id>", methods=["PUT"])
def editar_produto(produto_id):
    conn = get_connection()
    try:
        produto_atual = conn.execute(
            "SELECT id_produto, tipo, preco_producao, preco_venda, categoria FROM produtos WHERE id_produto = ?",
            (produto_id,),
        ).fetchone()
        if not produto_atual:
            return jsonify({"error": "Produto não encontrado"}), 404
        dados = request.get_json(silent=True) or {}
        produto, erro = _dados_produto(dados, produto_atual)
        if erro:
            return jsonify({"error": erro}), 400
        if conn.execute(
            "SELECT 1 FROM produtos WHERE lower(tipo) = lower(?) AND id_produto != ?",
            (produto[0], produto_id),
        ).fetchone():
            return jsonify({"error": "Já existe um produto com esse nome"}), 409
        conn.execute(
            "UPDATE produtos SET tipo = ?, preco_producao = ?, preco_venda = ?, categoria = ? WHERE id_produto = ?",
            (*produto, produto_id),
        )
        conn.commit()
        return jsonify({"id": produto_id, "tipo": produto[0], "preco_producao": produto[1], "preco_venda": produto[2], "categoria": produto[3]})
    finally:
        conn.close()


@app.route("/api/produtos/<int:produto_id>", methods=["DELETE"])
def excluir_produto(produto_id):
    conn = get_connection()
    try:
        if not conn.execute("SELECT 1 FROM produtos WHERE id_produto = ?", (produto_id,)).fetchone():
            return jsonify({"error": "Produto não encontrado"}), 404
        if conn.execute("SELECT 1 FROM vendas WHERE id_produto = ?", (produto_id,)).fetchone():
            return jsonify({"error": "Não é possível excluir um produto com vendas registradas"}), 409
        conn.execute("DELETE FROM produtos WHERE id_produto = ?", (produto_id,))
        conn.commit()
        return jsonify({"message": "Produto excluído com sucesso"})
    finally:
        conn.close()


@app.route("/api/vendas", methods=["POST"])
def registrar_vendas():
    dados = request.get_json(silent=True) or {}
    if "nome_vendedor" in dados or "itens" in dados:
        return registrar_fechamento_diario()

    return jsonify({"error": "Use o endpoint /api/fechamentos-diarios para o fechamento consolidado"}), 400


@app.route("/api/fechamentos-diarios", methods=["POST"])
def registrar_fechamento_diario():
    dados = request.get_json(silent=True) or {}
    nome_vendedor = (dados.get("nome_vendedor") or dados.get("vendedor") or "").strip()
    itens = dados.get("itens") or []

    if not nome_vendedor:
        return jsonify({"error": "Informe o nome do vendedor do dia"}), 400

    if not itens:
        return jsonify({"error": "Informe pelo menos um item para o fechamento diário"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id_vendedor FROM vendedores WHERE lower(nome) = lower(?)", (nome_vendedor,))
        vendedor_row = cursor.fetchone()
        if not vendedor_row:
            conn.close()
            return jsonify({"error": "Selecione um vendedor cadastrado"}), 400
        vendedor_id = vendedor_row["id_vendedor"]

        data_emissao = dados.get("data_emissao") or dados.get("data") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not data_emissao:
            data_emissao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO fechamentos_diarios (nome_vendedor, total_faturamento, total_lucro, total_comissao, data_emissao, observacoes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (nome_vendedor, 0, 0, 0, data_emissao, dados.get("observacoes") or ""),
        )
        fechamento_id = cursor.lastrowid

        total_faturamento = 0.0
        total_lucro = 0.0

        for item in itens:
            produto_nome = item.get("produto") or item.get("nome_produto")
            quantidade = int(item.get("quantidade", 0) or 0)
            valor_unitario = float(item.get("valor_unitario") or item.get("valor") or 0)

            if not produto_nome or quantidade <= 0 or valor_unitario <= 0:
                continue

            cursor.execute(
                "SELECT id_produto, preco_producao, preco_venda FROM produtos WHERE lower(tipo) = lower(?)",
                (produto_nome,),
            )
            produto_row = cursor.fetchone()
            if produto_row:
                produto_id = produto_row["id_produto"]
                custo_unitario = float(produto_row["preco_producao"] or 0)
            else:
                custo_unitario = valor_unitario * 0.7
                cursor.execute(
                    "INSERT INTO produtos (tipo, preco_producao, preco_venda, categoria) VALUES (?, ?, ?, ?)",
                    (produto_nome, custo_unitario, valor_unitario, "geral"),
                )
                produto_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO vendas (
                    id_vendedor, id_produto, quantidade, id_fechamento, observacao,
                    data, preco_venda, preco_producao
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vendedor_id,
                    produto_id,
                    quantidade,
                    fechamento_id,
                    produto_nome,
                    data_emissao,
                    valor_unitario,
                    custo_unitario,
                ),
            )

            total_faturamento += quantidade * valor_unitario
            total_lucro += quantidade * (valor_unitario - custo_unitario)

        total_comissao = total_lucro * 0.12
        cursor.execute(
            "UPDATE fechamentos_diarios SET total_faturamento = ?, total_lucro = ?, total_comissao = ? WHERE id_fechamento = ?",
            (round(total_faturamento, 2), round(total_lucro, 2), round(total_comissao, 2), fechamento_id),
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        conn.close()
        return jsonify({"error": f"Erro ao registrar fechamento diário: {exc}"}), 500

    relatorio = calcular_relatorio("diario")
    conn.close()
    return jsonify(
        {
            "message": "Fechamento diário registrado com sucesso",
            "fechamento": {
                "id": fechamento_id,
                "nome_vendedor": nome_vendedor,
                "total_faturamento": round(total_faturamento, 2),
                "total_lucro": round(total_lucro, 2),
                "total_comissao": round(total_comissao, 2),
                "data_emissao": data_emissao,
            },
            "relatorio": relatorio,
        }
    )


@app.route("/api/fechamentos-diarios", methods=["GET"])
def listar_fechamentos_diarios():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id_fechamento, nome_vendedor, total_faturamento, total_lucro, total_comissao, data_emissao
        FROM fechamentos_diarios
        ORDER BY data_emissao DESC, id_fechamento DESC
        """
    ).fetchall()
    conn.close()
    return jsonify(
        [
            {
                "id": row["id_fechamento"],
                "nome_vendedor": row["nome_vendedor"],
                "total_faturamento": row["total_faturamento"],
                "total_lucro": row["total_lucro"],
                "total_comissao": row["total_comissao"],
                "data_emissao": row["data_emissao"],
            }
            for row in rows
        ]
    )


def _preparar_itens_fechamento(cursor, itens):
    if not isinstance(itens, list) or not itens:
        return None, "Informe pelo menos um item para o fechamento diário"

    itens_preparados = []
    for item in itens:
        if not isinstance(item, dict):
            return None, "Informe itens válidos para o fechamento"
        produto_nome = item.get("produto") or item.get("nome_produto") or ""
        if not isinstance(produto_nome, str):
            return None, "Informe um nome de produto válido"
        produto_nome = produto_nome.strip()
        try:
            quantidade_original = item.get("quantidade", 0)
            quantidade = int(quantidade_original)
        except (TypeError, ValueError):
            return None, "A quantidade dos itens deve ser um número inteiro positivo"
        if (
            isinstance(quantidade_original, bool)
            or quantidade <= 0
            or str(quantidade_original).strip() != str(quantidade)
            or not produto_nome
        ):
            return None, "Informe produto e quantidade válida em todos os itens"

        produto = cursor.execute(
            """
            SELECT id_produto, preco_producao, preco_venda
            FROM produtos
            WHERE lower(tipo) = lower(?)
            """,
            (produto_nome,),
        ).fetchone()
        if not produto:
            return None, f"Produto não encontrado: {produto_nome}"

        itens_preparados.append(
            {
                "produto_id": produto["id_produto"],
                "produto": produto_nome,
                "quantidade": quantidade,
                "preco_venda": float(produto["preco_venda"]),
                "preco_producao": float(produto["preco_producao"]),
            }
        )
    return itens_preparados, None


@app.route("/api/fechamentos-diarios/<int:fechamento_id>", methods=["GET"])
def obter_fechamento_diario(fechamento_id):
    conn = get_connection()
    fechamento = conn.execute(
        """
        SELECT id_fechamento, nome_vendedor, total_faturamento, total_lucro,
               total_comissao, data_emissao, observacoes
        FROM fechamentos_diarios
        WHERE id_fechamento = ?
        """,
        (fechamento_id,),
    ).fetchone()
    if not fechamento:
        conn.close()
        return jsonify({"error": "Fechamento não encontrado"}), 404

    itens = conn.execute(
        """
        SELECT v.id_venda, p.tipo AS produto, v.quantidade,
               COALESCE(v.preco_venda, p.preco_venda) AS valor_unitario
        FROM vendas v
        LEFT JOIN produtos p ON p.id_produto = v.id_produto
        WHERE v.id_fechamento = ?
        ORDER BY v.id_venda
        """,
        (fechamento_id,),
    ).fetchall()
    conn.close()
    return jsonify(
        {
            "id": fechamento["id_fechamento"],
            "nome_vendedor": fechamento["nome_vendedor"],
            "total_faturamento": fechamento["total_faturamento"],
            "total_lucro": fechamento["total_lucro"],
            "total_comissao": fechamento["total_comissao"],
            "data_emissao": fechamento["data_emissao"],
            "observacoes": fechamento["observacoes"],
            "itens": [
                {
                    "id": item["id_venda"],
                    "produto": item["produto"],
                    "quantidade": item["quantidade"],
                    "valor_unitario": item["valor_unitario"],
                }
                for item in itens
            ],
        }
    )


@app.route("/api/fechamentos-diarios/<int:fechamento_id>", methods=["PUT"])
def editar_fechamento_diario(fechamento_id):
    dados = request.get_json(silent=True) or {}
    if not isinstance(dados, dict):
        return jsonify({"error": "Informe os dados do fechamento"}), 400
    nome_vendedor = dados.get("nome_vendedor") or dados.get("vendedor") or ""
    if not isinstance(nome_vendedor, str):
        return jsonify({"error": "Informe o nome do vendedor do dia"}), 400
    nome_vendedor = nome_vendedor.strip()
    itens = dados.get("itens")
    data_emissao = dados.get("data_emissao") or dados.get("data")

    if not nome_vendedor:
        return jsonify({"error": "Informe o nome do vendedor do dia"}), 400
    if not data_emissao:
        return jsonify({"error": "Informe a data do fechamento"}), 400
    try:
        datetime.fromisoformat(data_emissao)
    except (TypeError, ValueError):
        return jsonify({"error": "Informe uma data válida para o fechamento"}), 400

    conn = get_connection()
    try:
        fechamento = conn.execute(
            "SELECT id_fechamento, observacoes FROM fechamentos_diarios WHERE id_fechamento = ?",
            (fechamento_id,),
        ).fetchone()
        if not fechamento:
            return jsonify({"error": "Fechamento não encontrado"}), 404

        vendedor = conn.execute(
            "SELECT id_vendedor FROM vendedores WHERE lower(nome) = lower(?)",
            (nome_vendedor,),
        ).fetchone()
        if not vendedor:
            return jsonify({"error": "Selecione um vendedor cadastrado"}), 400

        itens_preparados, erro = _preparar_itens_fechamento(conn.cursor(), itens)
        if erro:
            return jsonify({"error": erro}), 400

        vendas_anteriores = conn.execute(
            """
            SELECT id_produto, preco_venda, preco_producao
            FROM vendas
            WHERE id_fechamento = ?
            ORDER BY id_venda
            """,
            (fechamento_id,),
        ).fetchall()
        precos_anteriores = {}
        for venda in vendas_anteriores:
            precos_anteriores.setdefault(venda["id_produto"], []).append(venda)
        for item in itens_preparados:
            anteriores = precos_anteriores.get(item["produto_id"], [])
            if anteriores:
                anterior = anteriores.pop(0)
                if anterior["preco_venda"] is not None:
                    item["preco_venda"] = float(anterior["preco_venda"])
                if anterior["preco_producao"] is not None:
                    item["preco_producao"] = float(anterior["preco_producao"])

        total_faturamento = sum(item["quantidade"] * item["preco_venda"] for item in itens_preparados)
        total_lucro = sum(
            item["quantidade"] * (item["preco_venda"] - item["preco_producao"])
            for item in itens_preparados
        )
        total_comissao = total_lucro * 0.12
        observacoes = dados.get("observacoes", fechamento["observacoes"]) or ""

        conn.execute("DELETE FROM vendas WHERE id_fechamento = ?", (fechamento_id,))
        conn.execute(
            """
            UPDATE fechamentos_diarios
            SET nome_vendedor = ?, total_faturamento = ?, total_lucro = ?,
                total_comissao = ?, data_emissao = ?, observacoes = ?
            WHERE id_fechamento = ?
            """,
            (
                nome_vendedor,
                round(total_faturamento, 2),
                round(total_lucro, 2),
                round(total_comissao, 2),
                data_emissao,
                observacoes,
                fechamento_id,
            ),
        )
        for item in itens_preparados:
            conn.execute(
                """
                INSERT INTO vendas (
                    id_vendedor, id_produto, quantidade, id_fechamento, observacao,
                    data, preco_venda, preco_producao
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vendedor["id_vendedor"],
                    item["produto_id"],
                    item["quantidade"],
                    fechamento_id,
                    item["produto"],
                    data_emissao,
                    item["preco_venda"],
                    item["preco_producao"],
                ),
            )
        conn.commit()
        return jsonify(
            {
                "message": "Fechamento diário atualizado com sucesso",
                "id": fechamento_id,
                "total_faturamento": round(total_faturamento, 2),
                "total_lucro": round(total_lucro, 2),
                "total_comissao": round(total_comissao, 2),
            }
        )
    except Exception as exc:
        conn.rollback()
        return jsonify({"error": f"Erro ao atualizar fechamento diário: {exc}"}), 500
    finally:
        conn.close()


@app.route("/api/fechamentos-diarios/<int:fechamento_id>", methods=["DELETE"])
def excluir_fechamento_diario(fechamento_id):
    conn = get_connection()
    try:
        fechamento = conn.execute(
            "SELECT id_fechamento FROM fechamentos_diarios WHERE id_fechamento = ?",
            (fechamento_id,),
        ).fetchone()
        if not fechamento:
            return jsonify({"error": "Fechamento não encontrado"}), 404
        conn.execute("DELETE FROM vendas WHERE id_fechamento = ?", (fechamento_id,))
        conn.execute("DELETE FROM fechamentos_diarios WHERE id_fechamento = ?", (fechamento_id,))
        conn.commit()
        return jsonify({"message": "Fechamento diário excluído com sucesso"})
    except Exception as exc:
        conn.rollback()
        return jsonify({"error": f"Erro ao excluir fechamento diário: {exc}"}), 500
    finally:
        conn.close()


@app.route("/api/vendas", methods=["GET"])
def listar_vendas_api():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT v.id_venda, v.id_vendedor, v.id_produto, v.quantidade, v.data, v.id_fechamento,
               p.tipo AS produto, COALESCE(v.preco_venda, p.preco_venda) AS preco_venda,
               f.nome_vendedor
        FROM vendas v
        LEFT JOIN produtos p ON p.id_produto = v.id_produto
        LEFT JOIN fechamentos_diarios f ON f.id_fechamento = v.id_fechamento
        ORDER BY v.data DESC, v.id_venda DESC
        """
    ).fetchall()
    conn.close()
    return jsonify(
        [
            {
                "id": row["id_venda"],
                "vendedor_id": row["id_vendedor"],
                "produto_id": row["id_produto"],
                "produto": row["produto"],
                "quantidade": row["quantidade"],
                "valor_unitario": row["preco_venda"],
                "data": row["data"],
                "nome_vendedor": row["nome_vendedor"],
            }
            for row in rows
        ]
    )


@app.route("/api/relatorios", methods=["GET"])
def listar_relatorios():
    tipo_relatorio = request.args.get("tipo", "diario").lower()
    conn = get_connection()

    if tipo_relatorio == "diario":
        where_clause = "DATE(data_emissao) = DATE('now')"
    elif tipo_relatorio == "semanal":
        where_clause = "data_emissao >= datetime('now', '-6 days')"
    elif tipo_relatorio == "mensal":
        where_clause = "strftime('%Y-%m', data_emissao) = strftime('%Y-%m', 'now')"
    else:
        where_clause = "1=1"

    rows = conn.execute(
        f"""
        SELECT id_fechamento AS id, nome_vendedor AS vendedor, total_faturamento AS faturamento,
               total_lucro AS lucro, total_comissao AS comissao, data_emissao AS data
        FROM fechamentos_diarios
        WHERE {where_clause}
        ORDER BY data_emissao DESC, id_fechamento DESC
        """
    ).fetchall()
    conn.close()

    return jsonify(
        [
            {
                "id": row["id"],
                "tipo": tipo_relatorio,
                "vendedor": row["vendedor"],
                "faturamento": row["faturamento"],
                "lucro": row["lucro"],
                "comissao": row["comissao"],
                "data": row["data"],
            }
            for row in rows
        ]
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
