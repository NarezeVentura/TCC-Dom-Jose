import os
import sqlite3
from datetime import datetime, timedelta

from flask import Flask, jsonify, request


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(BASE_DIR, "front end")
db_path = os.path.join(BASE_DIR, "sistema_vendas.db")

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


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendedores (
            id_vendedor INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id_produto INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            preco_producao REAL NOT NULL,
            preco_venda REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id_venda INTEGER PRIMARY KEY AUTOINCREMENT,
            id_vendedor INTEGER NOT NULL,
            id_produto INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_vendedor) REFERENCES vendedores(id_vendedor),
            FOREIGN KEY (id_produto) REFERENCES produtos(id_produto)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relatorios_diarios (
            id_relatorio INTEGER PRIMARY KEY AUTOINCREMENT,
            id_vendedor INTEGER NOT NULL,
            faturamento REAL,
            lucro REAL,
            comissao REAL,
            data_emissao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_vendedor) REFERENCES vendedores(id_vendedor)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relatorios_semanais (
            id_relatorio INTEGER PRIMARY KEY AUTOINCREMENT,
            semana_inicio DATE,
            semana_fim DATE,
            faturamento REAL,
            lucro REAL,
            data_emissao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relatorios_mensais (
            id_relatorio INTEGER PRIMARY KEY AUTOINCREMENT,
            mes_inicio DATE,
            mes_fim DATE,
            faturamento REAL,
            lucro REAL,
            data_emissao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM vendedores")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO vendedores (nome) VALUES ('Pedro')")
        cursor.execute("INSERT INTO vendedores (nome) VALUES ('Nicole')")

    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] == 0:
        produtos_data = [
            ("Trufas", 2.20, 6.00),
            ("Cones", 3.50, 12.00),
            ("Combo Cone + Trufa", 5.70, 17.00),
            ("Combo 2 Cones", 7.00, 22.00),
            ("Combo 3 Trufas", 6.60, 16.00),
            ("2 Cones + Trufa", 9.20, 28.00),
            ("Cone + 2 Trufas", 7.90, 22.00),
            ("2 Cones + 2 Trufas", 11.40, 32.00),
        ]
        cursor.executemany(
            "INSERT INTO produtos (tipo, preco_producao, preco_venda) VALUES (?, ?, ?)",
            produtos_data,
        )

    conn.commit()
    conn.close()


init_db()


def get_period_filter(tipo_relatorio):
    if tipo_relatorio == "diario":
        return "DATE(v.data) = DATE('now')"
    if tipo_relatorio == "semanal":
        return "v.data >= datetime('now', '-6 days')"
    if tipo_relatorio == "mensal":
        return "strftime('%Y-%m', v.data) = strftime('%Y-%m', 'now')"
    return "1=1"


def calcular_relatorio(tipo_relatorio, vendedor_id=None):
    conn = get_connection()
    cursor = conn.cursor()

    where_clause = get_period_filter(tipo_relatorio)
    params = []

    if vendedor_id is not None:
        where_clause += " AND v.id_vendedor = ?"
        params.append(vendedor_id)

    sql_faturamento = f"""
        SELECT COALESCE(SUM(p.preco_venda * v.quantidade), 0) AS faturamento
        FROM vendas v
        JOIN produtos p ON v.id_produto = p.id_produto
        WHERE {where_clause}
    """

    sql_lucro = f"""
        SELECT COALESCE(SUM((p.preco_venda - p.preco_producao) * v.quantidade), 0) AS lucro
        FROM vendas v
        JOIN produtos p ON v.id_produto = p.id_produto
        WHERE {where_clause}
    """

    cursor.execute(sql_faturamento, params)
    faturamento = cursor.fetchone()[0]

    cursor.execute(sql_lucro, params)
    lucro = cursor.fetchone()[0]

    comissao = lucro * 0.12 if tipo_relatorio == "diario" else 0

    conn.close()
    return {
        "faturamento": round(float(faturamento), 2),
        "lucro": round(float(lucro), 2),
        "comissao": round(float(comissao), 2),
    }


def salvar_relatorio(tipo_relatorio, faturamento, lucro, comissao, vendedor_id=None):
    conn = get_connection()
    cursor = conn.cursor()

    if tipo_relatorio == "diario":
        cursor.execute(
            """
            INSERT INTO relatorios_diarios (id_vendedor, faturamento, lucro, comissao)
            VALUES (?, ?, ?, ?)
            """,
            (vendedor_id, faturamento, lucro, comissao),
        )
    elif tipo_relatorio == "semanal":
        hoje = datetime.now()
        segunda = hoje - timedelta(days=hoje.weekday())
        domingo = segunda + timedelta(days=6)
        cursor.execute(
            """
            INSERT INTO relatorios_semanais (semana_inicio, semana_fim, faturamento, lucro)
            VALUES (?, ?, ?, ?)
            """,
            (segunda.date(), domingo.date(), faturamento, lucro),
        )
    elif tipo_relatorio == "mensal":
        hoje = datetime.now()
        primeiro_dia = datetime(hoje.year, hoje.month, 1).date()
        ultimo_dia = datetime(hoje.year, hoje.month, 28).date()
        cursor.execute(
            """
            INSERT INTO relatorios_mensais (mes_inicio, mes_fim, faturamento, lucro)
            VALUES (?, ?, ?, ?)
            """,
            (primeiro_dia, ultimo_dia, faturamento, lucro),
        )

    conn.commit()
    conn.close()


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
        "SELECT id_produto, tipo, preco_producao, preco_venda FROM produtos ORDER BY id_produto"
    ).fetchall()
    conn.close()
    return jsonify([
        {
            "id": row["id_produto"],
            "tipo": row["tipo"],
            "preco_producao": row["preco_producao"],
            "preco_venda": row["preco_venda"],
        }
        for row in produtos
    ])


@app.route("/api/vendas", methods=["POST"])
def registrar_vendas():
    dados = request.get_json(silent=True) or {}

    vendedor_id = dados.get("vendedor_id") or 1
    tipo_relatorio = (dados.get("tipo_relatorio") or "diario").lower()
    itens = dados.get("itens") or []

    if tipo_relatorio not in {"diario", "semanal", "mensal"}:
        return jsonify({"error": "tipo_relatorio inválido"}), 400

    if not itens:
        produto_nome = dados.get("produto") or dados.get("nome_produto")
        quantidade = int(dados.get("quantidade", 0) or 0)
        valor_unitario = float(dados.get("valor_unitario") or dados.get("valor") or 0)

        if not produto_nome or quantidade <= 0:
            return jsonify({"error": "Informe pelo menos um produto válido"}), 400

        itens = [{"produto": produto_nome, "quantidade": quantidade, "valor_unitario": valor_unitario}]

    conn = get_connection()
    cursor = conn.cursor()

    try:
        total_faturamento = 0.0
        for item in itens:
            produto_id = item.get("produto_id")
            produto_nome = item.get("produto") or item.get("nome_produto")
            quantidade = int(item.get("quantidade", 0) or 0)
            valor_unitario = float(item.get("valor_unitario") or item.get("valor") or 0)

            if not produto_id and produto_nome:
                cursor.execute("SELECT id_produto FROM produtos WHERE tipo = ?", (produto_nome,))
                produto_existente = cursor.fetchone()
                if produto_existente:
                    produto_id = produto_existente[0]
                else:
                    preco_producao = valor_unitario * 0.7 if valor_unitario else 0.0
                    cursor.execute(
                        "INSERT INTO produtos (tipo, preco_producao, preco_venda) VALUES (?, ?, ?)",
                        (produto_nome, preco_producao, valor_unitario),
                    )
                    produto_id = cursor.lastrowid

            if not produto_id or quantidade <= 0:
                continue

            cursor.execute(
                "INSERT INTO vendas (id_vendedor, id_produto, quantidade) VALUES (?, ?, ?)",
                (vendedor_id, produto_id, quantidade),
            )
            total_faturamento += (valor_unitario or 0) * quantidade

        conn.commit()
    except Exception as exc:
        conn.rollback()
        conn.close()
        return jsonify({"error": f"Erro ao registrar vendas: {exc}"}), 500

    relatorio = calcular_relatorio(tipo_relatorio, vendedor_id)
    salvar_relatorio(
        tipo_relatorio,
        relatorio["faturamento"] if relatorio["faturamento"] else round(total_faturamento, 2),
        relatorio["lucro"] if relatorio["lucro"] else 0,
        relatorio["comissao"] if relatorio["comissao"] else 0,
        vendedor_id,
    )

    conn.close()
    return jsonify({
        "message": "Vendas registradas com sucesso",
        "tipo_relatorio": tipo_relatorio,
        "relatorio": relatorio,
    })


@app.route("/api/relatorios", methods=["GET"])
def listar_relatorios():
    tipo_relatorio = request.args.get("tipo", "todos").lower()
    conn = get_connection()

    if tipo_relatorio == "diario":
        rows = conn.execute(
            "SELECT id_relatorio, id_vendedor, faturamento, lucro, comissao, data_emissao AS data FROM relatorios_diarios ORDER BY data_emissao DESC"
        ).fetchall()
        dados = [
            {
                "id": row["id_relatorio"],
                "tipo": "diario",
                "vendedor_id": row["id_vendedor"],
                "faturamento": row["faturamento"],
                "lucro": row["lucro"],
                "comissao": row["comissao"],
                "data": row["data"],
            }
            for row in rows
        ]
    elif tipo_relatorio == "semanal":
        rows = conn.execute(
            "SELECT id_relatorio, semana_inicio, semana_fim, faturamento, lucro, data_emissao AS data FROM relatorios_semanais ORDER BY data_emissao DESC"
        ).fetchall()
        dados = [
            {
                "id": row["id_relatorio"],
                "tipo": "semanal",
                "semana_inicio": row["semana_inicio"],
                "semana_fim": row["semana_fim"],
                "faturamento": row["faturamento"],
                "lucro": row["lucro"],
                "data": row["data"],
            }
            for row in rows
        ]
    elif tipo_relatorio == "mensal":
        rows = conn.execute(
            "SELECT id_relatorio, mes_inicio, mes_fim, faturamento, lucro, data_emissao AS data FROM relatorios_mensais ORDER BY data_emissao DESC"
        ).fetchall()
        dados = [
            {
                "id": row["id_relatorio"],
                "tipo": "mensal",
                "mes_inicio": row["mes_inicio"],
                "mes_fim": row["mes_fim"],
                "faturamento": row["faturamento"],
                "lucro": row["lucro"],
                "data": row["data"],
            }
            for row in rows
        ]
    else:
        diarios = conn.execute(
            "SELECT id_relatorio, 'diario' AS tipo, id_vendedor, faturamento, lucro, comissao, data_emissao AS data FROM relatorios_diarios ORDER BY data_emissao DESC"
        ).fetchall()
        semanais = conn.execute(
            "SELECT id_relatorio, 'semanal' AS tipo, NULL AS id_vendedor, faturamento, lucro, 0 AS comissao, data_emissao AS data FROM relatorios_semanais ORDER BY data_emissao DESC"
        ).fetchall()
        mensais = conn.execute(
            "SELECT id_relatorio, 'mensal' AS tipo, NULL AS id_vendedor, faturamento, lucro, 0 AS comissao, data_emissao AS data FROM relatorios_mensais ORDER BY data_emissao DESC"
        ).fetchall()

        dados = []
        for row in diarios + semanais + mensais:
            dados.append(
                {
                    "id": row["id_relatorio"],
                    "tipo": row["tipo"],
                    "vendedor_id": row["id_vendedor"],
                    "faturamento": row["faturamento"],
                    "lucro": row["lucro"],
                    "comissao": row["comissao"],
                    "data": row["data"],
                }
            )

    conn.close()
    return jsonify(dados)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)