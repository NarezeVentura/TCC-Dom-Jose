const catalogoProdutosEl = document.getElementById("catalogoProdutos");
const itensVendaListEl = document.getElementById("itensVendaList");
const form = document.getElementById("closureForm");
const reportsTable = document.getElementById("reportsTable");
const periodoRelatorioEl = document.getElementById("periodoRelatorio");
const addItemBtn = document.getElementById("addItemBtn");
const refreshReportsBtn = document.getElementById("refreshReportsBtn");

const maisVendidoEl = document.getElementById("maisVendido");
const vendasHojeEl = document.getElementById("vendasHoje");
const clientesCadastradosEl = document.getElementById("clientesCadastrados");

let vendas = [];
let totalVendasHoje = 0;
let produtosDisponiveis = [];

function formatarMoeda(valor) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(valor || 0));
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

function preencherCatalogo(produtos) {
  catalogoProdutosEl.innerHTML = "";

  if (!produtos.length) {
    catalogoProdutosEl.innerHTML = '<p class="empty-state">Nenhum produto cadastrado ainda.</p>';
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
    catalogoProdutosEl.appendChild(card);
  });
}

function criarLinhaItem(item = {}) {
  const row = document.createElement("div");
  row.className = "item-row";
  row.innerHTML = `
    <select class="produto-item" required>
      <option value="">Selecione o produto</option>
    </select>
    <input type="number" class="item-quantidade" min="1" value="${item.quantidade || 1}" placeholder="Quantidade" required>
    <input type="number" class="item-valor" step="0.01" placeholder="Valor unitário" readonly>
    <button type="button" class="remove-item-btn">Remover</button>
  `;

  const select = row.querySelector(".produto-item");
  const valorEl = row.querySelector(".item-valor");

  produtosDisponiveis.forEach((produto) => {
    const option = document.createElement("option");
    option.value = produto.tipo;
    option.textContent = produto.tipo;
    option.setAttribute("data-valor", produto.preco_venda);
    select.appendChild(option);
  });

  if (item.produto) {
    select.value = item.produto;
    const selected = Array.from(select.options).find((option) => option.value === item.produto);
    if (selected) {
      valorEl.value = selected.getAttribute("data-valor") || item.valor_unitario || "";
    }
  }

  select.addEventListener("change", () => {
    const selected = select.options[select.selectedIndex];
    valorEl.value = selected?.getAttribute("data-valor") || "";
  });

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
    produtosDisponiveis = produtos;
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

    if (fechamentos.length > 0) {
      const ultimo = fechamentos[0];
      totalVendasHoje = Number(ultimo.total_faturamento || 0);
    } else {
      totalVendasHoje = 0;
    }

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
      reportsTable.innerHTML = '<tr><td colspan="5" class="empty-state">Nenhum relatório encontrado.</td></tr>';
      return;
    }

    relatorios.forEach((item) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${item.data ? new Date(item.data).toLocaleDateString("pt-BR") : "-"}</td>
        <td>${item.vendedor || "-"}</td>
        <td>${formatarMoeda(item.faturamento)}</td>
        <td>${formatarMoeda(item.lucro)}</td>
        <td>${formatarMoeda(item.comissao)}</td>
      `;
      reportsTable.appendChild(row);
    });
  } catch (error) {
    console.error("Erro ao carregar relatórios:", error);
  }
}

addItemBtn.addEventListener("click", () => {
  itensVendaListEl.appendChild(criarLinhaItem());
});

refreshReportsBtn.addEventListener("click", () => {
  carregarRelatorios(periodoRelatorioEl.value);
});

periodoRelatorioEl.addEventListener("change", () => {
  carregarRelatorios(periodoRelatorioEl.value);
});

form.addEventListener("submit", async function (e) {
  e.preventDefault();

  const nomeVendedor = document.getElementById("nomeVendedor").value.trim();
  const dataFechamento = document.getElementById("dataFechamento").value;
  const linhas = Array.from(itensVendaListEl.querySelectorAll(".item-row"));

  const itens = linhas
    .map((linha) => {
      const select = linha.querySelector(".produto-item");
      const quantidade = Number(linha.querySelector(".item-quantidade").value || 0);
      const valor = Number(linha.querySelector(".item-valor").value || 0);
      const produto = select?.value;

      if (!produto || !quantidade || quantidade <= 0) return null;
      return { produto, quantidade, valor_unitario: valor };
    })
    .filter(Boolean);

  if (!nomeVendedor || !itens.length) {
    alert("Informe o nome do vendedor e pelo menos um item para registrar o fechamento.");
    return;
  }

  try {
    const resposta = await fetch("/api/fechamentos-diarios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nome_vendedor: nomeVendedor,
        data_emissao: dataFechamento || null,
        itens,
      }),
    });

    const dados = await resposta.json();
    if (!resposta.ok) throw new Error(dados.error || "Erro ao registrar fechamento diário");

    alert(dados.message);
    form.reset();
    renderizarItens();
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
  await carregarResumo();
  await carregarRelatorios("diario");
});
