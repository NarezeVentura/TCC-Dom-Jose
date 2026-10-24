import importlib
import os
import tempfile
import unittest
from datetime import datetime, timedelta


class TestFluxoFechamentoDiario(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_sistema_vendas.db")
        os.environ["DB_PATH"] = self.db_path

        import app as app_module

        self.app_module = importlib.reload(app_module)
        self.client = self.app_module.app.test_client()

    def tearDown(self):
        self.tmpdir.cleanup()
        os.environ.pop("DB_PATH", None)

    def test_registro_de_fechamento_diario_gera_relatorio(self):
        payload = {
            "nome_vendedor": "Pedro",
            "itens": [
                {"produto": "Cone Tradicional", "quantidade": 2, "valor_unitario": 12.0},
                {"produto": "Trufa", "quantidade": 3, "valor_unitario": 6.0},
            ],
        }

        response = self.client.post("/api/fechamentos-diarios", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["fechamento"]["nome_vendedor"], "Pedro")
        self.assertEqual(data["fechamento"]["total_faturamento"], 42.0)
        self.assertGreater(data["relatorio"]["faturamento"], 0)
        self.assertGreater(data["relatorio"]["lucro"], 0)

    def test_crud_de_fechamento_diario(self):
        criado = self.client.post(
            "/api/fechamentos-diarios",
            json={
                "nome_vendedor": "Pedro",
                "itens": [{"produto": "Cones", "quantidade": 2, "valor_unitario": 12}],
            },
        )
        self.assertEqual(criado.status_code, 200)
        fechamento_id = criado.get_json()["fechamento"]["id"]

        detalhe = self.client.get(f"/api/fechamentos-diarios/{fechamento_id}")
        self.assertEqual(detalhe.status_code, 200)
        self.assertEqual(detalhe.get_json()["itens"][0]["produto"], "Cones")
        self.assertEqual(detalhe.get_json()["itens"][0]["quantidade"], 2)
        self.assertEqual(detalhe.get_json()["itens"][0]["valor_unitario"], 12)

        conn = self.app_module.get_connection()
        conn.execute("UPDATE produtos SET preco_venda = 20, preco_producao = 4 WHERE tipo = 'Cones'")
        conn.commit()
        conn.close()

        editado = self.client.put(
            f"/api/fechamentos-diarios/{fechamento_id}",
            json={
                "nome_vendedor": "Nicole",
                "data_emissao": "2026-10-23",
                "itens": [{"produto": "Cones", "quantidade": 2}],
            },
        )
        self.assertEqual(editado.status_code, 200)
        self.assertEqual(editado.get_json()["total_faturamento"], 24)
        self.assertEqual(editado.get_json()["total_lucro"], 17)

        editado = self.client.put(
            f"/api/fechamentos-diarios/{fechamento_id}",
            json={
                "nome_vendedor": "Nicole",
                "data_emissao": "2026-10-23",
                "itens": [{"produto": "Trufas", "quantidade": 3}],
            },
        )
        self.assertEqual(editado.status_code, 200)
        self.assertEqual(editado.get_json()["total_faturamento"], 18)
        detalhe_editado = self.client.get(f"/api/fechamentos-diarios/{fechamento_id}").get_json()
        self.assertEqual(detalhe_editado["nome_vendedor"], "Nicole")
        self.assertEqual(detalhe_editado["itens"][0]["produto"], "Trufas")

        excluido = self.client.delete(f"/api/fechamentos-diarios/{fechamento_id}")
        self.assertEqual(excluido.status_code, 200)
        self.assertEqual(self.client.get(f"/api/fechamentos-diarios/{fechamento_id}").status_code, 404)
        conn = self.app_module.get_connection()
        vendas_restantes = conn.execute(
            "SELECT COUNT(*) FROM vendas WHERE id_fechamento = ?",
            (fechamento_id,),
        ).fetchone()[0]
        conn.close()
        self.assertEqual(vendas_restantes, 0)

    def test_edicao_de_fechamento_invalida_preserva_dados(self):
        criado = self.client.post(
            "/api/fechamentos-diarios",
            json={
                "nome_vendedor": "Pedro",
                "itens": [{"produto": "Cones", "quantidade": 2, "valor_unitario": 12}],
            },
        )
        fechamento_id = criado.get_json()["fechamento"]["id"]

        resposta = self.client.put(
            f"/api/fechamentos-diarios/{fechamento_id}",
            json={
                "nome_vendedor": "Nicole",
                "data_emissao": "2026-10-23",
                "itens": [{"produto": "Produto inexistente", "quantidade": 1}],
            },
        )

        self.assertEqual(resposta.status_code, 400)
        detalhe = self.client.get(f"/api/fechamentos-diarios/{fechamento_id}").get_json()
        self.assertEqual(detalhe["nome_vendedor"], "Pedro")
        self.assertEqual(detalhe["total_faturamento"], 24)
        self.assertEqual(detalhe["itens"][0]["produto"], "Cones")

    def test_fechamentos_com_mais_de_35_dias_sao_excluidos_automaticamente(self):
        data_antiga = (datetime.now() - timedelta(days=36)).strftime("%Y-%m-%d")
        antigo = self.client.post(
            "/api/fechamentos-diarios",
            json={
                "nome_vendedor": "Pedro",
                "data_emissao": data_antiga,
                "itens": [{"produto": "Cones", "quantidade": 2, "valor_unitario": 12}],
            },
        ).get_json()["fechamento"]
        recente = self.client.post(
            "/api/fechamentos-diarios",
            json={
                "nome_vendedor": "Nicole",
                "itens": [{"produto": "Trufas", "quantidade": 1, "valor_unitario": 6}],
            },
        ).get_json()["fechamento"]

        resposta = self.client.get("/api/fechamentos-diarios")
        ids_restantes = [fechamento["id"] for fechamento in resposta.get_json()]
        self.assertNotIn(antigo["id"], ids_restantes)
        self.assertIn(recente["id"], ids_restantes)
        self.assertEqual(
            self.client.get(f"/api/fechamentos-diarios/{antigo['id']}").status_code,
            404,
        )

        conn = self.app_module.get_connection()
        vendas_antigas = conn.execute(
            "SELECT COUNT(*) FROM vendas WHERE id_fechamento = ?",
            (antigo["id"],),
        ).fetchone()[0]
        conn.close()
        self.assertEqual(vendas_antigas, 0)

    def test_catalogo_contem_apenas_opcoes_padronizadas(self):
        response = self.client.get("/api/produtos")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [produto["tipo"] for produto in response.get_json()],
            [
                "Trufas",
                "Cones",
                "Cone + Trufa",
                "Combo 2 Cones",
                "Combo 3 Trufas",
                "2 Cones + Trufa",
                "Cone + 2 Trufas",
                "2 Cones + 2 Trufas",
            ],
        )

    def test_catalogo_normaliza_nome_do_combo_com_trufa(self):
        conn = self.app_module.get_connection()
        conn.execute("UPDATE produtos SET tipo = 'Cone + trufa' WHERE tipo = 'Cone + Trufa'")
        conn.commit()
        conn.close()

        self.app_module.init_db()
        response = self.client.get("/api/produtos")

        self.assertIn("Cone + Trufa", [produto["tipo"] for produto in response.get_json()])

    def test_crud_de_vendedor(self):
        criado = self.client.post("/api/vendedores", json={"nome": "Marina"})
        self.assertEqual(criado.status_code, 201)
        vendedor = criado.get_json()

        editado = self.client.put(f"/api/vendedores/{vendedor['id']}", json={"nome": "Marina Silva"})
        self.assertEqual(editado.status_code, 200)
        self.assertEqual(editado.get_json()["nome"], "Marina Silva")

        excluido = self.client.delete(f"/api/vendedores/{vendedor['id']}")
        self.assertEqual(excluido.status_code, 200)

    def test_crud_de_produto(self):
        criado = self.client.post(
            "/api/produtos",
            json={
                "tipo": "Brigadeiro",
                "preco_producao": 1.5,
                "preco_venda": 5,
                "categoria": "Matéria prima",
            },
        )
        self.assertEqual(criado.status_code, 201)
        produto = criado.get_json()

        editado = self.client.put(
            f"/api/produtos/{produto['id']}",
            json={"tipo": "Brigadeiro especial", "preco_venda": 6},
        )
        self.assertEqual(editado.status_code, 200)
        self.assertEqual(editado.get_json()["preco_venda"], 6)

        listado = self.client.get("/api/produtos").get_json()
        self.assertIn("Brigadeiro especial", [item["tipo"] for item in listado])

        excluido = self.client.delete(f"/api/produtos/{produto['id']}")
        self.assertEqual(excluido.status_code, 200)

    def test_fechamento_rejeita_vendedor_inexistente(self):
        response = self.client.post(
            "/api/fechamentos-diarios",
            json={
                "nome_vendedor": "Vendedor que não existe",
                "itens": [{"produto": "Trufa", "quantidade": 1, "valor_unitario": 6}],
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_produto_rejeita_categoria_fora_da_lista_fixa(self):
        response = self.client.post(
            "/api/produtos",
            json={"tipo": "Produto inválido", "preco_producao": 1, "preco_venda": 2, "categoria": "Doces"},
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
