import importlib
import os
import tempfile
import unittest


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
            "nome_vendedor": "Ana",
            "itens": [
                {"produto": "Cone Tradicional", "quantidade": 2, "valor_unitario": 12.0},
                {"produto": "Trufa", "quantidade": 3, "valor_unitario": 6.0},
            ],
        }

        response = self.client.post("/api/fechamentos-diarios", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["fechamento"]["nome_vendedor"], "Ana")
        self.assertEqual(data["fechamento"]["total_faturamento"], 42.0)
        self.assertGreater(data["relatorio"]["faturamento"], 0)
        self.assertGreater(data["relatorio"]["lucro"], 0)


if __name__ == "__main__":
    unittest.main()
