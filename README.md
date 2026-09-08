TCC - Sistema de Vendas - Doces Caseiros

Este projeto é uma aplicação web local para controlar vendas, organizar o fechamento diário e visualizar relatórios por período. O sistema permite registrar um fechamento consolidado do dia, com nome do vendedor e itens do catálogo.

Funcionalidades

- Registro de fechamento diário com vendedor e itens
- Catálogo de produtos e combos (cones, trufas, combinações e pacotes)
- Cálculo de faturamento, lucro e comissão
- Relatórios diários, semanais e mensais
- Histórico de fechamentos armazenado em banco SQLite
- Interface web simples em HTML, CSS e JavaScript

Tecnologias utilizadas

- Python
- Flask
- SQLite
- HTML, CSS e JavaScript

Estrutura do projeto

- `app.py` — backend Flask, API e lógica do sistema
- `front end/` — arquivos da interface web
- `sistema_vendas.db` — banco de dados SQLite

Como executar

No Windows, abra o PowerShell dentro da pasta do projeto e execute os comandos abaixo, na ordem:

```powershell
py -m pip install -r requirements.txt
py app.py
```

Depois, abra este endereço no navegador:

```text
http://127.0.0.1:5000
```

Se o comando `py` não funcionar, use estes comandos no lugar:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Observações

- O backend já serve a interface frontend automaticamente.
- O sistema utiliza SQLite para armazenar vendedores, produtos, fechamentos diários e relatórios.
- Em Windows, pode ser necessário executar o comando no terminal como `python app.py`.
