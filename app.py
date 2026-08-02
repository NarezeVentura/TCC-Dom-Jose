import os
import sqlite3
from datetime import datetime, timedelta

from flask import Flask, jsonify, request


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(BASE_DIR, "front end")
db_path = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "sistema_vendas.db"))

app = Flask(__name__, static_folder=frontend_dir, static_url_path="/")


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
    if not _has_column(conn, "produtos", "categoria"):
        cursor.execute("ALTER TABLE produtos ADD COLUMN categoria TEXT DEFAULT 'geral'")

    cursor.execute("SELECT COUNT(*) FROM vendedores")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO vendedores (nome) VALUES ('Pedro')")
        cursor.execute("INSERT INTO vendedores (nome) VALUES ('Nicole')")

    produtos_seed = [
        ("Cone Tradicional", 3.50, 12.00, "Cone"),
        ("Cone de Nutella", 3.50, 12.00, "Cone"),
        ("Trufa", 2.20, 6.00, "Trufa"),
        ("Trufa de Nutella", 2.20, 6.00, "Trufa"),
        ("Combo Cone + Trufa", 5.70, 17.00, "Combo"),
        ("Combo 2 Cones", 7.00, 22.00, "Combo"),
        ("Combo 3 Trufas", 6.60, 16.00, "Combo"),
        ("Combo 2 Cones + 2 Trufas", 11.40, 32.00, "Combo"),
    ]
    for produto in produtos_seed:
        cursor.execute("SELECT 1 FROM produtos WHERE lower(tipo) = lower(?)", (produto[0],))
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO produtos (tipo, preco_producao, preco_venda, categoria) VALUES (?, ?, ?, ?)",
                produto,
            )

    cursor.execute(
        "DELETE FROM produtos WHERE categoria = ? OR lower(tipo) LIKE ? OR lower(tipo) LIKE ?",
        ("Mão de obra", "mão de obra%", "mao de obra%"),
    )

    conn.commit()
    conn.close()


init_db()


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


@app.route("/api/produtos", methods=["GET"])
def listar_produtos():
    conn = get_connection()
    produtos = conn.execute(
        "SELECT id_produto, tipo, preco_producao, preco_venda, categoria FROM produtos WHERE categoria != ? AND lower(tipo) NOT LIKE ? AND lower(tipo) NOT LIKE ? ORDER BY id_produto",
        ("Mão de obra", "mão de obra%", "mao de obra%"),
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
        if vendedor_row:
            vendedor_id = vendedor_row["id_vendedor"]
        else:
            cursor.execute("INSERT INTO vendedores (nome) VALUES (?)", (nome_vendedor,))
            vendedor_id = cursor.lastrowid

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
                "INSERT INTO vendas (id_vendedor, id_produto, quantidade, id_fechamento, observacao, data) VALUES (?, ?, ?, ?, ?, ?)",
                (vendedor_id, produto_id, quantidade, fechamento_id, produto_nome, data_emissao),
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


@app.route("/api/vendas", methods=["GET"])
def listar_vendas_api():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT v.id_venda, v.id_vendedor, v.id_produto, v.quantidade, v.data, v.id_fechamento,
               p.tipo AS produto, p.preco_venda, f.nome_vendedor
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
