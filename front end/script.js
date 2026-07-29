const form = document.getElementById("saleForm");
const table = document.getElementById("salesTable");

const produtoSelect = document.getElementById("produto");
const valorInput = document.getElementById("valor");

const comboArea = document.getElementById("comboArea");
const comboSabores = document.getElementById("comboSabores");

const maisVendidoEl = document.getElementById("maisVendido");
const vendasHojeEl = document.getElementById("vendasHoje");

let vendas = [];
let totalVendasHoje = 0;

// valor automático + combo
produtoSelect.addEventListener("change", function () {

  const option = produtoSelect.options[produtoSelect.selectedIndex];
  const valor = option.getAttribute("data-valor");
  const tipo = option.getAttribute("data-tipo");
  const qtd = option.getAttribute("data-qtd");

  valorInput.value = valor ? valor : "";

  // se for combo
  if (tipo === "combo") {

    comboArea.style.display = "block";
    comboSabores.innerHTML = "";

    for (let i = 1; i <= qtd; i++) {
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

// venda
form.addEventListener("submit", function (e) {
  e.preventDefault();

  const cliente = form.querySelector("input").value;

  const option = produtoSelect.options[produtoSelect.selectedIndex];
  const tipo = option.getAttribute("data-tipo");

  let produto = produtoSelect.value;

  // se for combo, monta sabores
  if (tipo === "combo") {
    const sabores = document.querySelectorAll(".combo-sabor");
    let lista = [];

    sabores.forEach(s => lista.push(s.value));

    produto = `${produtoSelect.value} (${lista.join(", ")})`;
  }

  const quantidade = Number(form.querySelectorAll("input")[1].value);
  const valor = Number(valorInput.value);

  const total = quantidade * valor;

  vendas.push({
    produto,
    quantidade
  });

  totalVendasHoje += total;
  atualizarVendasHoje();

  table.innerHTML += `
    <tr>
      <td>${cliente}</td>
      <td>${produto}</td>
      <td>${quantidade}</td>
      <td>R$ ${total.toFixed(2)}</td>
    </tr>
  `;

  atualizarMaisVendido();

  form.reset();
  valorInput.value = "";
  comboArea.style.display = "none";
  comboSabores.innerHTML = "";
});

// vendas hoje
function atualizarVendasHoje() {
  vendasHojeEl.textContent = `R$ ${totalVendasHoje.toFixed(2)}`;
}

// mais vendido
function atualizarMaisVendido() {
  if (vendas.length === 0) {
    maisVendidoEl.textContent = "Nenhuma venda ainda";
    return;
  }

  const contagem = {};

  vendas.forEach(v => {

    // pega apenas sabores separados por vírgula (caso combo)
    const sabores = v.produto
      .replace(/\(.*\)/g, "") // remove tudo entre parênteses (combos)
      .split(",");

    sabores.forEach(sabor => {
      const clean = sabor.trim();

      if (!clean) return;

      contagem[clean] = (contagem[clean] || 0) + v.quantidade;
    });

  });

  let maisVendido = "";
  let maior = 0;

  for (let sabor in contagem) {
    if (contagem[sabor] > maior) {
      maior = contagem[sabor];
      maisVendido = sabor;
    }
  }

  maisVendidoEl.textContent = maisVendido;
}

function mostrarPagina(pagina) {

  const pages = document.querySelectorAll(".page");

  pages.forEach(p => {
    p.style.display = "none";
  });

  const alvo = document.getElementById(pagina);
  if (alvo) {
    alvo.style.display = "block";
  }
}

/* abre dashboard ao iniciar */
document.addEventListener("DOMContentLoaded", () => {
  mostrarPagina("dashboard");
});