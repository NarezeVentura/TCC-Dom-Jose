const catalogoProdutosVendaEl = document.getElementById("catalogoProdutosVenda");
const catalogoMateriaPrimaEl = document.getElementById("catalogoMateriaPrima");
const itensVendaListEl = document.getElementById("itensVendaList");
const form = document.getElementById("closureForm");
const reportsTable = document.getElementById("reportsTable");
const periodoRelatorioEl = document.getElementById("periodoRelatorio");
const addItemBtn = document.getElementById("addItemBtn");
const refreshReportsBtn = document.getElementById("refreshReportsBtn");
const salvarFechamentoBtn = document.getElementById("salvarFechamentoBtn");
const cancelarFechamentoBtn = document.getElementById("cancelarFechamentoBtn");
const produtoForm = document.getElementById("produtoForm");
const produtosTableEl = document.getElementById("produtosTable");
const cancelarProdutoBtn = document.getElementById("cancelarProdutoBtn");
const vendedorForm = document.getElementById("vendedorForm");
const vendedoresTableEl = document.getElementById("vendedoresTable");
const cancelarVendedorBtn = document.getElementById("cancelarVendedorBtn");
const vendedorSelectEl = document.getElementById("nomeVendedor");
const CATEGORIA_VENDA = "Produtos para venda";
const CATEGORIA_MATERIA_PRIMA = "Matéria prima";

const maisVendidoEl = document.getElementById("maisVendido");
const vendasHojeEl = document.getElementById("vendasHoje");
const clientesCadastradosEl = document.getElementById("clientesCadastrados");

let vendas = [];
let totalVendasHoje = 0;
let produtosDisponiveis = [];

function formatarMoeda(valor) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(valor || 0));
}

function escaparHtml(valor) {
  return String(valor ?? "").replace(/[&<>'"]/g, (caractere) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  }[caractere]));
}

async function requisicaoJson(url, opcoes = {}) {
  const resposta = await fetch(url, opcoes);
  const dados = await resposta.json();
  if (!resposta.ok) throw new Error(dados.error || "Não foi possível concluir a operação");
  return dados;
}

function mostrarPagina(pagina) {
  const pages = document.querySelectorAll(".page");
  pages.forEach((p) => {
    p.style.display = "none";
    p.classList.remove("active");
  });

  const alvo = document.getElementById(pagina);
  if (alvo) {
    alvo.style.display = "block";
    alvo.classList.add("active");
    alvo.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function renderizarGrupoCatalogo(elemento, produtos) {
  elemento.innerHTML = "";
  if (!produtos.length) {
    elemento.innerHTML = '<p class="empty-state">Nenhum produto cadastrado ainda.</p>';
    return;
  }

  produtos.forEach((produto) => {
    const card = document.createElement("article");
    card.className = "produto-card";
    card.innerHTML = `
      <h3>${produto.tipo}</h3>
      <p class="categoria">${produto.categoria || "Geral"}</p>
      <span>Venda: ${formatarMoeda(produto.preco_venda)}</span>
      <small>Produção: ${formatarMoeda(produto.preco_producao)}</small>
    `;
    elemento.appendChild(card);
  });
}

function preencherCatalogo(produtos) {
  renderizarGrupoCatalogo(
    catalogoProdutosVendaEl,
    produtos.filter((produto) => produto.categoria === CATEGORIA_VENDA),
  );
  renderizarGrupoCatalogo(
    catalogoMateriaPrimaEl,
    produtos.filter((produto) => produto.categoria === CATEGORIA_MATERIA_PRIMA),
  );
}

function renderizarTabelaProdutos(produtos) {
  produtosTableEl.innerHTML = produtos.length ? produtos.map((produto) => `
    <tr>
      <td>${escaparHtml(produto.tipo)}</td>
      <td>${escaparHtml(produto.categoria || "Geral")}</td>
      <td>${formatarMoeda(produto.preco_producao)}</td>
      <td>${formatarMoeda(produto.preco_venda)}</td>
      <td class="row-actions">
        <button type="button" class="edit-product-btn" data-id="${produto.id}">Editar</button>
        <button type="button" class="delete-product-btn remove-item-btn" data-id="${produto.id}">Excluir</button>
      </td>
    </tr>
  `).join("") : '<tr><td colspan="5" class="empty-state">Nenhum produto cadastrado.</td></tr>';

  produtosTableEl.querySelectorAll(".edit-product-btn").forEach((botao) => {
    botao.addEventListener("click", () => iniciarEdicaoProduto(produtos.find((produto) => produto.id === Number(botao.dataset.id))));
  });
  produtosTableEl.querySelectorAll(".delete-product-btn").forEach((botao) => {
    botao.addEventListener("click", () => excluirProduto(Number(botao.dataset.id)));
  });
}

function limparFormularioProduto() {
  produtoForm.reset();
  document.getElementById("produtoId").value = "";
  document.getElementById("produtoCategoria").value = CATEGORIA_VENDA;
  document.getElementById("salvarProdutoBtn").textContent = "Adicionar produto";
  cancelarProdutoBtn.hidden = true;
}

function iniciarEdicaoProduto(produto) {
  if (!produto) return;
  document.getElementById("produtoId").value = produto.id;
  document.getElementById("produtoTipo").value = produto.tipo;
  document.getElementById("produtoPrecoProducao").value = produto.preco_producao;
  document.getElementById("produtoPrecoVenda").value = produto.preco_venda;
  document.getElementById("produtoCategoria").value = produto.categoria || "geral";
  document.getElementById("salvarProdutoBtn").textContent = "Salvar alterações";
  cancelarProdutoBtn.hidden = false;
  document.getElementById("produtoTipo").focus();
}

async function excluirProduto(id) {
  if (!window.confirm("Deseja excluir este produto?")) return;
  try {
    await requisicaoJson(`/api/produtos/${id}`, { method: "DELETE" });
    await carregarProdutos();
  } catch (error) {
    alert(error.message);
  }
}

function renderizarTabelaVendedores(vendedores) {
  vendedoresTableEl.innerHTML = vendedores.length ? vendedores.map((vendedor) => `
    <tr>
      <td>${escaparHtml(vendedor.nome)}</td>
      <td class="row-actions">
        <button type="button" class="edit-seller-btn" data-id="${vendedor.id}">Editar</button>
        <button type="button" class="delete-seller-btn remove-item-btn" data-id="${vendedor.id}">Excluir</button>
      </td>
    </tr>
  `).join("") : '<tr><td colspan="2" class="empty-state">Nenhum vendedor cadastrado.</td></tr>';

  vendedoresTableEl.querySelectorAll(".edit-seller-btn").forEach((botao) => {
    botao.addEventListener("click", () => iniciarEdicaoVendedor(vendedores.find((vendedor) => vendedor.id === Number(botao.dataset.id))));
  });
  vendedoresTableEl.querySelectorAll(".delete-seller-btn").forEach((botao) => {
    botao.addEventListener("click", () => excluirVendedor(Number(botao.dataset.id)));
  });
}

function limparFormularioVendedor() {
  vendedorForm.reset();
  document.getElementById("vendedorId").value = "";
  document.getElementById("salvarVendedorBtn").textContent = "Adicionar vendedor";
  cancelarVendedorBtn.hidden = true;
}

function iniciarEdicaoVendedor(vendedor) {
  if (!vendedor) return;
  document.getElementById("vendedorId").value = vendedor.id;
  document.getElementById("vendedorNome").value = vendedor.nome;
  document.getElementById("salvarVendedorBtn").textContent = "Salvar alterações";
  cancelarVendedorBtn.hidden = false;
  document.getElementById("vendedorNome").focus();
}

async function carregarVendedores() {
  try {
    const vendedores = await requisicaoJson("/api/vendedores");
    renderizarTabelaVendedores(vendedores);
    vendedorSelectEl.innerHTML = '<option value="">Selecione um vendedor</option>';
    vendedores.forEach((vendedor) => {
      const option = document.createElement("option");
      option.value = vendedor.nome;
      option.textContent = vendedor.nome;
      vendedorSelectEl.appendChild(option);
    });
    clientesCadastradosEl.textContent = `${vendedores.length} vendedores`;
  } catch (error) {
    console.error("Erro ao carregar vendedores:", error);
  }
}

async function excluirVendedor(id) {
  if (!window.confirm("Deseja excluir este vendedor?")) return;
  try {
    await requisicaoJson(`/api/vendedores/${id}`, { method: "DELETE" });
    await carregarVendedores();
  } catch (error) {
    alert(error.message);
  }
}

function criarLinhaItem(item = {}) {
  const row = document.createElement("div");
  row.className = "item-row";
  row.innerHTML = `
    <select class="produto-item" required>
      <option value="">Selecione o produto</option>
    </select>
    <input type="number" class="item-quantidade" min="1" value="${item.quantidade || 1}" placeholder="Quantidade" required>
    <input type="number" class="item-valor" step="0.01" placeholder="Total" readonly>
    <button type="button" class="remove-item-btn">Remover</button>
  `;

  const select = row.querySelector(".produto-item");
  const quantidadeEl = row.querySelector(".item-quantidade");
  const valorEl = row.querySelector(".item-valor");

  function atualizarTotal() {
    const selected = select.options[select.selectedIndex];
    const valorUnitario = Number(selected?.getAttribute("data-valor") || 0);
    const quantidade = Number(quantidadeEl.value || 0);
    valorEl.value = valorUnitario && quantidade > 0 ? (valorUnitario * quantidade).toFixed(2) : "";
  }

  produtosDisponiveis.forEach((produto) => {
    const option = document.createElement("option");
    option.value = produto.tipo;
    option.textContent = produto.tipo;
    option.setAttribute("data-valor", produto.preco_venda);
    select.appendChild(option);
  });

  if (item.produto) {
    if (!Array.from(select.options).some((option) => option.value === item.produto)) {
      const option = document.createElement("option");
      option.value = item.produto;
      option.textContent = item.produto;
      option.setAttribute("data-valor", item.valor_unitario || 0);
      select.appendChild(option);
    }
    select.value = item.produto;
    const selected = Array.from(select.options).find((option) => option.value === item.produto);
    if (selected) {
      if (item.valor_unitario != null) {
        selected.setAttribute("data-valor", item.valor_unitario);
      }
      atualizarTotal();
    }
  }

  select.addEventListener("change", () => {
    atualizarTotal();
  });

  quantidadeEl.addEventListener("input", atualizarTotal);

  row.querySelector(".remove-item-btn").addEventListener("click", () => {
    row.remove();
  });

  return row;
}

function renderizarItens(items = []) {
  itensVendaListEl.innerHTML = "";
  if (!items.length) {
    itensVendaListEl.appendChild(criarLinhaItem());
    return;
  }

  items.forEach((item) => itensVendaListEl.appendChild(criarLinhaItem(item)));
}

function atualizarVendasHoje() {
  vendasHojeEl.textContent = formatarMoeda(totalVendasHoje);
}

function atualizarMaisVendido() {
  if (!vendas.length) {
    maisVendidoEl.textContent = "Nenhuma venda registrada";
    return;
  }

  const contagem = {};
  vendas.forEach((v) => {
    const nome = (v.produto || "").replace(/\(.*\)/g, "").trim();
    if (!nome) return;
    contagem[nome] = (contagem[nome] || 0) + Number(v.quantidade || 0);
  });

  let maisVendido = "";
  let maior = 0;

  Object.entries(contagem).forEach(([produto, quantidade]) => {
    if (quantidade > maior) {
      maior = quantidade;
      maisVendido = produto;
    }
  });

  maisVendidoEl.textContent = maisVendido || "Nenhuma venda registrada";
}

async function carregarProdutos() {
  try {
    const resposta = await fetch("/api/produtos");
    const produtos = await resposta.json();
    renderizarTabelaProdutos(produtos);
    produtosDisponiveis = produtos.filter((produto) => produto.categoria === CATEGORIA_VENDA);
    preencherCatalogo(produtos);
    renderizarItens();
  } catch (error) {
    console.error("Erro ao carregar produtos:", error);
  }
}

async function carregarResumo() {
  try {
    const [vendedoresResp, fechamentosResp, vendasResp] = await Promise.all([
      fetch("/api/vendedores"),
      fetch("/api/fechamentos-diarios"),
      fetch("/api/vendas")
    ]);

    const vendedores = await vendedoresResp.json();
    const fechamentos = await fechamentosResp.json();
    const vendasRecebidas = await vendasResp.json();

    vendas = vendasRecebidas;
    clientesCadastradosEl.textContent = `${vendedores.length} vendedores`;
    atualizarMaisVendido();

    const agora = new Date();
    const dataHoje = [
      agora.getFullYear(),
      String(agora.getMonth() + 1).padStart(2, "0"),
      String(agora.getDate()).padStart(2, "0"),
    ].join("-");
    totalVendasHoje = fechamentos
      .filter((fechamento) => String(fechamento.data_emissao).slice(0, 10) === dataHoje)
      .reduce((total, fechamento) => total + Number(fechamento.total_faturamento || 0), 0);

    atualizarVendasHoje();
  } catch (error) {
    console.error("Erro ao carregar resumo:", error);
  }
}

async function carregarRelatorios(periodo = "diario") {
  try {
    const resposta = await fetch(`/api/relatorios?tipo=${periodo}`);
    const relatorios = await resposta.json();
    reportsTable.innerHTML = "";

    if (!relatorios.length) {
      reportsTable.innerHTML = '<tr><td colspan="6" class="empty-state">Nenhum relatório encontrado.</td></tr>';
      return;
    }

    relatorios.forEach((item) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${item.data ? new Date(item.data).toLocaleDateString("pt-BR") : "-"}</td>
        <td>${escaparHtml(item.vendedor || "-")}</td>
        <td>${formatarMoeda(item.faturamento)}</td>
        <td>${formatarMoeda(item.lucro)}</td>
        <td>${formatarMoeda(item.comissao)}</td>
        <td class="row-actions">
          <button type="button" class="view-closure-btn" data-id="${item.id}">Ver itens</button>
          <button type="button" class="edit-closure-btn" data-id="${item.id}">Editar</button>
          <button type="button" class="delete-closure-btn remove-item-btn" data-id="${item.id}">Excluir</button>
        </td>
      `;
      reportsTable.appendChild(row);
    });

    reportsTable.querySelectorAll(".view-closure-btn").forEach((button) => {
      button.addEventListener("click", () => visualizarFechamento(Number(button.dataset.id), button));
    });
    reportsTable.querySelectorAll(".edit-closure-btn").forEach((button) => {
      button.addEventListener("click", () => iniciarEdicaoFechamento(Number(button.dataset.id)));
    });
    reportsTable.querySelectorAll(".delete-closure-btn").forEach((button) => {
      button.addEventListener("click", () => excluirFechamento(Number(button.dataset.id)));
    });
  } catch (error) {
    console.error("Erro ao carregar relatórios:", error);
  }
}

async function visualizarFechamento(id, button) {
  const row = button.closest("tr");
  const detalheExistente = row.nextElementSibling;
  if (detalheExistente?.classList.contains("closure-details-row")) {
    detalheExistente.remove();
    button.textContent = "Ver itens";
    return;
  }

  try {
    const fechamento = await requisicaoJson(`/api/fechamentos-diarios/${id}`);
    const detalhe = document.createElement("tr");
    detalhe.className = "closure-details-row";
    const itens = fechamento.itens.map((item) => `
      <li>${escaparHtml(item.produto || "Produto removido")} — ${item.quantidade} un. × ${formatarMoeda(item.valor_unitario)}</li>
    `).join("");
    detalhe.innerHTML = `<td colspan="6"><strong>Itens:</strong><ul>${itens}</ul></td>`;
    row.after(detalhe);
    button.textContent = "Ocultar itens";
  } catch (error) {
    alert(error.message);
  }
}

async function iniciarEdicaoFechamento(id) {
  try {
    const fechamento = await requisicaoJson(`/api/fechamentos-diarios/${id}`);
    document.getElementById("nomeVendedor").value = fechamento.nome_vendedor;
    document.getElementById("dataFechamento").value = String(fechamento.data_emissao || "").slice(0, 10);
    document.getElementById("closureId").value = fechamento.id;
    renderizarItens(fechamento.itens);
    salvarFechamentoBtn.textContent = "Salvar alterações";
    cancelarFechamentoBtn.hidden = false;
    mostrarPagina("vendas");
  } catch (error) {
    alert(error.message);
  }
}

function limparEdicaoFechamento() {
  form.reset();
  document.getElementById("closureId").value = "";
  salvarFechamentoBtn.textContent = "Registrar fechamento diário";
  cancelarFechamentoBtn.hidden = true;
  renderizarItens();
}

async function excluirFechamento(id) {
  if (!window.confirm("Deseja excluir este fechamento e todas as vendas associadas?")) return;
  try {
    await requisicaoJson(`/api/fechamentos-diarios/${id}`, { method: "DELETE" });
    await carregarResumo();
    await carregarRelatorios(periodoRelatorioEl.value);
  } catch (error) {
    alert(error.message);
  }
}

addItemBtn.addEventListener("click", () => {
  itensVendaListEl.appendChild(criarLinhaItem());
});

refreshReportsBtn.addEventListener("click", () => {
  carregarRelatorios(periodoRelatorioEl.value);
});
cancelarFechamentoBtn.addEventListener("click", limparEdicaoFechamento);

periodoRelatorioEl.addEventListener("change", () => {
  carregarRelatorios(periodoRelatorioEl.value);
});

produtoForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("produtoId").value;
  const dados = {
    tipo: document.getElementById("produtoTipo").value.trim(),
    preco_producao: Number(document.getElementById("produtoPrecoProducao").value),
    preco_venda: Number(document.getElementById("produtoPrecoVenda").value),
    categoria: document.getElementById("produtoCategoria").value.trim() || "geral",
  };
  try {
    await requisicaoJson(id ? `/api/produtos/${id}` : "/api/produtos", {
      method: id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(dados),
    });
    limparFormularioProduto();
    await carregarProdutos();
  } catch (error) {
    alert(error.message);
  }
});

cancelarProdutoBtn.addEventListener("click", limparFormularioProduto);

vendedorForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("vendedorId").value;
  const dados = { nome: document.getElementById("vendedorNome").value.trim() };
  try {
    await requisicaoJson(id ? `/api/vendedores/${id}` : "/api/vendedores", {
      method: id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(dados),
    });
    limparFormularioVendedor();
    await carregarVendedores();
  } catch (error) {
    alert(error.message);
  }
});

cancelarVendedorBtn.addEventListener("click", limparFormularioVendedor);

form.addEventListener("submit", async function (e) {
  e.preventDefault();

  const fechamentoId = document.getElementById("closureId").value;
  const nomeVendedor = document.getElementById("nomeVendedor").value.trim();
  const dataFechamento = document.getElementById("dataFechamento").value;
  const linhas = Array.from(itensVendaListEl.querySelectorAll(".item-row"));

  const itens = linhas
    .map((linha) => {
      const select = linha.querySelector(".produto-item");
      const quantidade = Number(linha.querySelector(".item-quantidade").value || 0);
      const produto = select?.value;
      const valor = Number(select?.options[select.selectedIndex]?.getAttribute("data-valor") || 0);

      if (!produto || !quantidade || quantidade <= 0) return null;
      return { produto, quantidade, valor_unitario: valor };
    })
    .filter(Boolean);

  if (!nomeVendedor || !itens.length) {
    alert("Informe o nome do vendedor e pelo menos um item para registrar o fechamento.");
    return;
  }

  try {
    const resposta = await fetch(
      fechamentoId ? `/api/fechamentos-diarios/${fechamentoId}` : "/api/fechamentos-diarios",
      {
      method: fechamentoId ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nome_vendedor: nomeVendedor,
        data_emissao: dataFechamento || null,
        itens,
      }),
      },
    );

    const dados = await resposta.json();
    if (!resposta.ok) throw new Error(dados.error || "Erro ao registrar fechamento diário");

    alert(dados.message);
    limparEdicaoFechamento();
    await carregarResumo();
    await carregarRelatorios(periodoRelatorioEl.value);
  } catch (error) {
    console.error(error);
    alert(error.message);
  }
});

document.addEventListener("DOMContentLoaded", async () => {
  mostrarPagina("dashboard");
  await carregarProdutos();
  await carregarVendedores();
  await carregarResumo();
  await carregarRelatorios("diario");
});
