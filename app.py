import datetime as datetime_
import sqlite3
import os

# ----------------------
# CONEXÃO COM BANCO
# ----------------------

db_path = "sistema_vendas.db"

# Criar banco de dados se não existir
if not os.path.exists(db_path):
    conexao = sqlite3.connect(db_path)
    cursor = conexao.cursor()
    
    # Criar tabelas
    cursor.execute("""
        CREATE TABLE vendedores (
            id_vendedor INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE produtos (
            id_produto INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            preco_producao REAL NOT NULL,
            preco_venda REAL NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE vendas (
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
        CREATE TABLE relatorios_diarios (
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
        CREATE TABLE relatorios_semanais (
            id_relatorio INTEGER PRIMARY KEY AUTOINCREMENT,
            semana_inicio DATE,
            semana_fim DATE,
            faturamento REAL,
            lucro REAL,
            data_emissao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE relatorios_mensais (
            id_relatorio INTEGER PRIMARY KEY AUTOINCREMENT,
            mes_inicio DATE,
            mes_fim DATE,
            faturamento REAL,
            lucro REAL,
            data_emissao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Inserir dados padrão
    cursor.execute("INSERT INTO vendedores (id_vendedor, nome) VALUES (1, 'Pedro')")
    cursor.execute("INSERT INTO vendedores (id_vendedor, nome) VALUES (2, 'Nicole')")
    
    produtos_data = [
        (1, 'Trufas', 2.20, 6.00),
        (2, 'Cones', 3.50, 12.00),
        (3, 'Combo Cone + Trufa', 5.70, 17.00),
        (4, 'Combo 2 Cones', 7.00, 22.00),
        (5, 'Combo 3 Trufas', 6.60, 16.00),
        (6, '2 Cones + Trufa', 9.20, 28.00),
        (7, 'Cone + 2 Trufas', 7.90, 22.00),
        (8, '2 Cones + 2 Trufas', 11.40, 32.00)
    ]
    
    for id_p, tipo, prec_prod, prec_venda in produtos_data:
        cursor.execute(
            "INSERT INTO produtos (id_produto, tipo, preco_producao, preco_venda) VALUES (?, ?, ?, ?)",
            (id_p, tipo, prec_prod, prec_venda)
        )
    
    conexao.commit()
else:
    conexao = sqlite3.connect(db_path)

cursor = conexao.cursor()

# ----------------------
# ENTRADA PADRÃO
# ----------------------

def entrada_inteira(mensagem, minimo=0, maximo=None):
    while True:
        try: 
            valor = int(input(mensagem))
            if valor < minimo: 
                print(f"Digite um valor maior ou igual que {minimo}.")
            elif maximo is not None and valor > maximo:
                print(f"Digite um valor menor ou igual a {maximo}.")
            else: 
                return valor 
        except ValueError:
            print("Entrada inválida. Digite apenas números inteiros")

# ----------------------
# CLASSES
# ----------------------

class Produto:
    def __init__(self, id_produto, tipo, preco_producao, preco_venda):
        self.id_produto = id_produto
        self.tipo = tipo
        self.preco_producao = preco_producao
        self.preco_venda = preco_venda


class Vendedor:
    def __init__(self, id_vendedor, nome):
        self.id_vendedor = id_vendedor
        self.nome = nome

    def vender(self, produto, quantidade):
        sql = """
        INSERT INTO vendas (id_vendedor, id_produto, quantidade)
        VALUES (?, ?, ?)
        """
        valores = (self.id_vendedor, produto.id_produto, quantidade)

        cursor.execute(sql, valores)
        conexao.commit()

# ----------------------
# RELATÓRIO BASE
# ----------------------

class RelatorioBase:
    def __init__(self, vendedor):
        self.vendedor = vendedor

    def calcular_faturamento(self, tipo):
        sql = """
        SELECT SUM(p.preco_venda * v.quantidade)
        FROM vendas v
        JOIN produtos p ON v.id_produto = p.id_produto
        WHERE
        """

        if tipo == "dia":
            sql += " DATE(v.data) = DATE('now')"
        elif tipo == "semana":
            sql += " v.data >= datetime('now', '-6 days')"
        elif tipo == "mes":
            sql += " strftime('%Y-%m', v.data) = strftime('%Y-%m', 'now')"

        cursor.execute(sql)
        resultado = cursor.fetchone()[0]
        return resultado if resultado else 0

    def calcular_lucro(self, tipo):
        sql = """
        SELECT SUM((p.preco_venda - p.preco_producao) * v.quantidade)
        FROM vendas v
        JOIN produtos p ON v.id_produto = p.id_produto
        WHERE
        """

        if tipo == "dia":
            sql += " DATE(v.data) = DATE('now')"
        elif tipo == "semana":
            sql += " v.data >= datetime('now', '-6 days')"
        elif tipo == "mes":
            sql += " strftime('%Y-%m', v.data) = strftime('%Y-%m', 'now')"

        cursor.execute(sql)
        resultado = cursor.fetchone()[0]
        return resultado if resultado else 0

# ----------------------
# SALVAR RELATÓRIO
# ----------------------

def salvar_relatorio(tipo, faturamento, lucro, comissao, id_vendedor=None):
    if tipo == "diario":
        sql = """
        INSERT INTO relatorios_diarios (id_vendedor, faturamento, lucro, comissao)
        VALUES (?, ?, ?, ?)
        """
        cursor.execute(sql, (id_vendedor, faturamento, lucro, comissao))
    elif tipo == "semanal":
        from datetime import datetime, timedelta
        hoje = datetime_.datetime.now()
        segunda = hoje - datetime_.timedelta(days=hoje.weekday())
        domingo = segunda + datetime_.timedelta(days=6)
        sql = """
        INSERT INTO relatorios_semanais (semana_inicio, semana_fim, faturamento, lucro)
        VALUES (?, ?, ?, ?)
        """
        cursor.execute(sql, (segunda.date(), domingo.date(), faturamento, lucro))
    elif tipo == "mensal":
        import calendar
        hoje = datetime_.datetime.now()
        primeiro_dia = datetime_.datetime(hoje.year, hoje.month, 1).date()
        ultimo_dia = datetime_.datetime(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1]).date()
        sql = """
        INSERT INTO relatorios_mensais (mes_inicio, mes_fim, faturamento, lucro)
        VALUES (?, ?, ?, ?)
        """
        cursor.execute(sql, (primeiro_dia, ultimo_dia, faturamento, lucro))
    conexao.commit()

# ----------------------
# HISTÓRICO DE RELATÓRIOS
# ----------------------

def consultar_relatorios(tipo=None):
    if tipo == "diario" or tipo is None:
        cursor.execute("""
            SELECT id_relatorio, 'diario' as tipo, data_emissao, faturamento, lucro, comissao
            FROM relatorios_diarios
            ORDER BY data_emissao DESC
        """)
        resultados_diarios = cursor.fetchall()
    else:
        resultados_diarios = []

    if tipo == "semanal" or tipo is None:
        cursor.execute("""
            SELECT id_relatorio, 'semanal' as tipo, data_emissao, faturamento, lucro, 0 as comissao
            FROM relatorios_semanais
            ORDER BY data_emissao DESC
        """)
        resultados_semanais = cursor.fetchall()
    else:
        resultados_semanais = []

    if tipo == "mensal" or tipo is None:
        cursor.execute("""
            SELECT id_relatorio, 'mensal' as tipo, data_emissao, faturamento, lucro, 0 as comissao
            FROM relatorios_mensais
            ORDER BY data_emissao DESC
        """)
        resultados_mensais = cursor.fetchall()
    else:
        resultados_mensais = []

    resultados = resultados_diarios + resultados_semanais + resultados_mensais

    if not resultados:
        print("\nNenhum relatório encontrado.")
        return

    print("\n=== HISTÓRICO DE RELATÓRIOS ===")
    for r in resultados:
        id_r, tipo_rel, data, fat, lucro, comissao = r
        fat = fat if fat else 0
        lucro = lucro if lucro else 0
        comissao = comissao if comissao else 0

        print(f"[{id_r}] {data}")
        print(f"Tipo: {tipo_rel}")
        print(f"Faturamento: R$ {fat:.2f}")
        print(f"Lucro: R$ {lucro:.2f}")
        if comissao > 0:
            print(f"Comissão: R$ {comissao:.2f}")
        print("-" * 30)

# ----------------------
# RELATÓRIOS
# ----------------------

class RelatorioDia(RelatorioBase):
    def gerar(self):
        faturamento = self.calcular_faturamento("dia")
        lucro = self.calcular_lucro("dia")
        comissao = lucro * 0.12

        print("\n=== RELATÓRIO DIÁRIO ===")
        print(f"Faturamento: R$ {faturamento:.2f}")
        print(f"Lucro: R$ {lucro:.2f}")
        print(f"Comissão: R$ {comissao:.2f}")

        salvar_relatorio("diario", faturamento, lucro, comissao, self.vendedor.id_vendedor)


class RelatorioSemana(RelatorioBase):
    def gerar(self):
        faturamento = self.calcular_faturamento("semana")
        lucro = self.calcular_lucro("semana")

        print("\n=== RELATÓRIO SEMANAL ===")
        print(f"Faturamento: R$ {faturamento:.2f}")
        print(f"Lucro: R$ {lucro:.2f}")

        salvar_relatorio("semanal", faturamento, lucro, 0, None)


class RelatorioMes(RelatorioBase):
    def gerar(self):
        faturamento = self.calcular_faturamento("mes")
        lucro = self.calcular_lucro("mes")

        print("\n=== RELATÓRIO MENSAL ===")
        print(f"Faturamento: R$ {faturamento:.2f}")
        print(f"Lucro: R$ {lucro:.2f}")

        salvar_relatorio("mensal", faturamento, lucro, 0, None)

# ----------------------
# PRODUTOS
# ----------------------

produtos = [
    Produto(1, "Trufas", 2.2, 6.0),
    Produto(2, "Cones", 3.5, 12.0),
    Produto(3, "Combo Cone + Trufa", 5.7, 17.0),
    Produto(4, "Combo 2 Cones", 7.0, 22.0),
    Produto(5, "Combo 3 Trufas", 6.6, 16.0),
    Produto(6, "2 Cones + Trufa", 9.2, 28.0),
    Produto(7, "Cone + 2 Trufas", 7.9, 22.0),
    Produto(8, "2 Cones + 2 Trufas", 11.4, 32.0)
]

# ----------------------
# VENDEDORES
# ----------------------

vendedor1 = Vendedor(1, "Pedro")
vendedor2 = Vendedor(2, "Nicole")

# ----------------------
# MENU
# ----------------------

print("\nO que deseja fazer?")
print("1 - Registrar vendas + gerar relatório")
print("2 - Ver histórico de relatórios")

opcao = entrada_inteira("Escolha: ", 1, 2)

# ----------------------
# OPÇÃO 1
# ----------------------

if opcao == 1:
    print("\nQual relatório deseja gerar?")
    print("1 - Diário")
    print("2 - Semanal")
    print("3 - Mensal")

    opcao_relatorio = entrada_inteira("Escolha: ", 1, 3)

    if opcao_relatorio == 1:
        print("Quem está vendendo hoje?")
        print("1 - Pedro")
        print("2 - Nicole")

        opcao_vendedor = entrada_inteira("Escolha: ", 1, 2)
        vendedor = vendedor1 if opcao_vendedor == 1 else vendedor2
    else:
        vendedor = vendedor2

    for p in produtos:
        qtd = entrada_inteira(f"{p.tipo}: ", 0)
        if qtd > 0:
            vendedor.vender(p, qtd)

    if opcao_relatorio == 1:
        rel = RelatorioDia(vendedor)
    elif opcao_relatorio == 2:
        rel = RelatorioSemana(vendedor)
    else:
        rel = RelatorioMes(vendedor)

    rel.gerar()

# ----------------------
# OPÇÃO 2
# ----------------------

elif opcao == 2:
    print("\nQual tipo de relatório deseja ver?")
    print("1 - Diário")
    print("2 - Semanal")
    print("3 - Mensal")
    print("4 - Todos")

    escolha = entrada_inteira("Escolha: ", 1, 4)

    if escolha == 1:
        consultar_relatorios("diario")
    elif escolha == 2:
        consultar_relatorios("semanal")
    elif escolha == 3:
        consultar_relatorios("mensal")
    else:
        consultar_relatorios()