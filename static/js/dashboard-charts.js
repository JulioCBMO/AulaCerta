(function () {
  "use strict";

  const root = document.getElementById("dashboard-charts");
  if (!root) return;

  const competenciaInput = document.getElementById("dashboard-competencia");
  const feedback = document.getElementById("dashboard-charts-feedback");
  const errorBox = document.getElementById("dashboard-charts-error");
  const emptyBox = document.getElementById("dashboard-charts-empty");
  const content = document.getElementById("dashboard-charts-content");
  const summary = document.getElementById("dashboard-charts-summary");
  const financeiroCanvas = document.getElementById("dashboard-financeiro-chart");
  const mensalidadesCanvas = document.getElementById("dashboard-mensalidades-chart");

  const moeda = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
  const inteiro = new Intl.NumberFormat("pt-BR");

  let financeiroChart = null;
  let mensalidadesChart = null;
  let requisicaoAtual = null;

  function destruirGraficos() {
    if (financeiroChart) financeiroChart.destroy();
    if (mensalidadesChart) mensalidadesChart.destroy();
    financeiroChart = null;
    mensalidadesChart = null;
  }

  function formatarCompetencia(valor) {
    const [ano, mes] = valor.split("-").map(Number);
    return new Intl.DateTimeFormat("pt-BR", {
      month: "long",
      year: "numeric",
      timeZone: "UTC",
    }).format(new Date(Date.UTC(ano, mes - 1, 1)));
  }

  function exibirCarregamento() {
    root.setAttribute("aria-busy", "true");
    feedback.dataset.state = "loading";
    feedback.textContent = "Carregando indicadores…";
    errorBox.hidden = true;
  }

  function exibirErro(mensagem) {
    destruirGraficos();
    root.setAttribute("aria-busy", "false");
    feedback.dataset.state = "error";
    feedback.textContent = "Os dados não puderam ser atualizados.";
    errorBox.textContent = mensagem;
    errorBox.hidden = false;
    emptyBox.hidden = true;
    content.hidden = true;
    summary.textContent = mensagem;
  }

  function exibirVazio(dados) {
    destruirGraficos();
    root.setAttribute("aria-busy", "false");
    feedback.dataset.state = "empty";
    feedback.textContent = `Competência: ${formatarCompetencia(dados.competencia)}.`;
    errorBox.hidden = true;
    emptyBox.hidden = false;
    content.hidden = true;
    summary.textContent = `Não existem dados financeiros para ${formatarCompetencia(dados.competencia)}.`;
  }

  function criarGraficos(dados) {
    destruirGraficos();

    const faturamento = Number(dados.faturamento_gerado);
    const pago = Number(dados.valor_total_pago);
    const pendente = Number(dados.valor_pendente);
    const total = Number(dados.total_mensalidades);
    const totalPendentes = Number(dados.total_pendentes);
    const vencidas = Number(dados.total_vencidas);
    const pagas = Math.max(total - totalPendentes, 0);
    const pendentesNoPrazo = Math.max(totalPendentes - vencidas, 0);

    financeiroChart = new Chart(financeiroCanvas, {
      type: "bar",
      data: {
        labels: ["Faturamento", "Recebido", "Pendente"],
        datasets: [{
          label: "Valor",
          data: [faturamento, pago, pendente],
          backgroundColor: ["#23302b", "#3c7a64", "#c97a2b"],
          borderRadius: 7,
          borderSkipped: false,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (context) => moeda.format(context.parsed.y),
            },
          },
        },
        scales: {
          x: { grid: { display: false } },
          y: {
            beginAtZero: true,
            ticks: { callback: (valor) => moeda.format(valor) },
            grid: { color: "rgba(217, 212, 198, 0.65)" },
          },
        },
      },
    });

    mensalidadesChart = new Chart(mensalidadesCanvas, {
      type: "doughnut",
      data: {
        labels: ["Pagas", "Pendentes", "Vencidas"],
        datasets: [{
          data: [pagas, pendentesNoPrazo, vencidas],
          backgroundColor: ["#3c7a64", "#e4a93b", "#b24a3d"],
          borderColor: "#ffffff",
          borderWidth: 3,
          hoverOffset: 5,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "64%",
        plugins: {
          legend: {
            position: "bottom",
            labels: { usePointStyle: true, boxWidth: 8, padding: 16 },
          },
          tooltip: {
            callbacks: {
              label: (context) => `${context.label}: ${inteiro.format(context.parsed)}`,
            },
          },
        },
      },
    });

    root.setAttribute("aria-busy", "false");
    feedback.dataset.state = "success";
    feedback.textContent = `Dados de ${formatarCompetencia(dados.competencia)} atualizados.`;
    errorBox.hidden = true;
    emptyBox.hidden = true;
    content.hidden = false;
    summary.textContent = [
      `Em ${formatarCompetencia(dados.competencia)},`,
      `o faturamento foi ${moeda.format(faturamento)},`,
      `com ${moeda.format(pago)} recebidos e ${moeda.format(pendente)} pendentes.`,
      `Há ${inteiro.format(pagas)} mensalidades pagas,`,
      `${inteiro.format(pendentesNoPrazo)} pendentes e`,
      `${inteiro.format(vencidas)} vencidas.`,
    ].join(" ");
  }

  async function carregarIndicadores(competencia) {
    if (!competencia) {
      exibirErro("Selecione uma competência válida.");
      return;
    }
    if (typeof Chart === "undefined") {
      exibirErro("A biblioteca de gráficos não pôde ser carregada.");
      return;
    }

    if (requisicaoAtual) requisicaoAtual.abort();
    requisicaoAtual = new AbortController();
    exibirCarregamento();

    const parametros = new URLSearchParams({ competencia });
    try {
      const resposta = await fetch(`${root.dataset.estatisticasUrl}?${parametros}`, {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
        signal: requisicaoAtual.signal,
      });
      const dados = await resposta.json();
      if (!resposta.ok) {
        throw new Error(dados.erro || "Não foi possível consultar os indicadores.");
      }

      if (Number(dados.total_mensalidades) === 0) {
        exibirVazio(dados);
      } else {
        criarGraficos(dados);
      }
    } catch (erro) {
      if (erro.name !== "AbortError") {
        exibirErro(erro.message || "Não foi possível carregar os indicadores.");
      }
    }
  }

  competenciaInput.addEventListener("change", function () {
    carregarIndicadores(competenciaInput.value);
  });

  carregarIndicadores(competenciaInput.value);
})();
