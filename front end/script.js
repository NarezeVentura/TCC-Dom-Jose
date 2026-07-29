const form = document.getElementById("saleForm");
const table = document.getElementById("salesTable");

const produtoSelect = document.getElementById("produto");
const valorInput = document.getElementById("valor");
const comboArea = document.getElementById("comboArea");
const comboSabores = document.getElementById("comboSabores");

const maisVendidoEl = document.getElementById("maisVendido");
const vendasHojeEl = document.getElementById("vendasHoje");
const clientesCadastradosEl = document.getElementById("clientesCadastrados");

let vendas = [];
let totalVendasHoje = 0;

function formatarMoeda(valor) {
  return `R$ ${Number(valor || 0).toFixed(2)}`;
}

function atualizarVendasHoje() {
  vendasHojeEl.textContent = formatarMoeda(totalVendasHoje);
}

function atualizarMaisVendido() {
  if (vendas.length === 0) {
    maisVendidoEl.textContent = "Nenhuma venda registrada";
    return;
  }

  const contagem = {};

  vendas.forEach((v) => {
    const nome = v.produto.replace(/\(.*\)/g, "").trim();
    if (!nome) return;
    contagem[nome] = (contagem[nome] || 0) + v.quantidade;
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

function mostrarPagina(pagina) {
  const pages = document.querySelectorAll(".page");
  pages.forEach((p) => {
    p.style.display = "none";
  });

  const alvo = document.getElementById(pagina);
  if (alvo) {
    alvo.style.display = "block";
  }
}

async function carregarProdutos() {
  try {
    const resposta = await fetch("/api/produtos");
    const produtos = await resposta.json();

    produtoSelect.innerHTML = '<option value="">Selecione o produto</option>';

    const addGroup = (label, items) => {
      if (!items.length) return;

      const grupo = document.createElement("optgroup");
      grupo.label = label;

      items.forEach((produto) => {
        const option = document.createElement("option");
        option.value = produto.tipo;
        option.textContent = produto.tipo;
        option.setAttribute("data-valor", produto.preco_venda);
        option.setAttribute("data-id", produto.id);
        option.setAttribute("data-tipo", /combo/i.test(produto.tipo) ? "combo" : "normal");
        grupo.appendChild(option);
      });

      produtoSelect.appendChild(grupo);
    };

    addGroup("🍫 Cones", produtos.filter((p) => /cone|cones/i.test(p.tipo)));
    addGroup("🍬 Trufas", produtos.filter((p) => /trufa|bombom/i.test(p.tipo)));
    addGroup("🎁 Combos", produtos.filter((p) => /combo/i.test(p.tipo)));
  } catch (error) {
    console.error("Erro ao carregar produtos:", error);
  }
}

async function carregarResumo() {
  try {
    const [vendedoresResp, relatoriosResp] = await Promise.all([
      fetch("/api/vendedores"),
      fetch("/api/relatorios?tipo=diario")
    ]);

    const vendedores = await vendedoresResp.json();
    const relatorios = await relatoriosResp.json();

    clientesCadastradosEl.textContent = `${vendedores.length} vendedores`;

    if (relatorios.length > 0) {
      const ultimo = relatorios[0];
      totalVendasHoje = Number(ultimo.faturamento || 0);
      atualizarVendasHoje();
    } else {
      totalVendasHoje = 0;
      atualizarVendasHoje();
    }
  } catch (error) {
    console.error("Erro ao carregar resumo:", error);
  }
}

produtoSelect.addEventListener("change", function () {
  const option = produtoSelect.options[produtoSelect.selectedIndex];
  const valor = option.getAttribute("data-valor");
  const tipo = option.getAttribute("data-tipo");
  const qtd = option.getAttribute("data-qtd") || "2";

  valorInput.value = valor ? valor : "";

  if (tipo === "combo") {
    comboArea.style.display = "block";
    comboSabores.innerHTML = "";

    for (let i = 1; i <= Number(qtd); i++) {
      comboSabores.innerHTML += `
        <div style="margin-bottom:10px;">
          <label>Sabor ${i}</label>
          <select class="combo-sabor">
            <option>Bueno</option>
            <option>Nutella</option>
            <option>Ninho</option>
            <option>Ninho com Nutella</option>
            <option>Morango</option>
            <option>Morango com Nutella</option>
            <option>Maracujá</option>
            <option>Maracujá com Nutella</option>
            <option>Paçoca</option>
            <option>Brigadeiro</option>
            <option>Beijinho</option>
            <option>2 amores</option>
            <option>Tradicional</option>
          </select>
        </div>
      `;
    }
  } else {
    comboArea.style.display = "none";
    comboSabores.innerHTML = "";
  }
});

form.addEventListener("submit", async function (e) {
  e.preventDefault();

  const cliente = document.getElementById("cliente").value.trim();
  const option = produtoSelect.options[produtoSelect.selectedIndex];
  const tipo = option.getAttribute("data-tipo");

  let produto = option.value;

  if (tipo === "combo") {
    const sabores = Array.from(document.querySelectorAll(".combo-sabor")).map((s) => s.value);
    produto = `${produto} (${sabores.join(", ")})`;
  }

  const quantidade = Number(document.getElementById("quantidade").value);
  const valor = Number(valorInput.value || option.getAttribute("data-valor") || 0);

  if (!produto || !quantidade || quantidade <= 0) {
    alert("Preencha o produto e a quantidade corretamente.");
    return;
  }

  try {
    const resposta = await fetch("/api/vendas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        vendedor_id: 1,
        tipo_relatorio: "diario",
        itens: [{ produto, quantidade, valor_unitario: valor }],
        cliente
      })
    });

    const dados = await resposta.json();

    if (!resposta.ok) {
      throw new Error(dados.error || "Erro ao registrar venda");
    }

    vendas.push({ produto, quantidade });
    atualizarMaisVendido();

    const total = quantidade * valor;
    totalVendasHoje = Number(dados.relatorio?.faturamento || totalVendasHoje + total);
    atualizarVendasHoje();

    table.innerHTML += `
      <tr>
        <td>${cliente || "Cliente"}</td>
        <td>${produto}</td>
        <td>${quantidade}</td>
        <td>${formatarMoeda(total)}</td>
      </tr>
    `;

    form.reset();
    valorInput.value = "";
    comboArea.style.display = "none";
    comboSabores.innerHTML = "";
  } catch (error) {
    console.error(error);
    alert(error.message);
  }
});

/* abre dashboard ao iniciar */
document.addEventListener("DOMContentLoaded", async () => {
  mostrarPagina("dashboard");
  await carregarProdutos();
  await carregarResumo();
});