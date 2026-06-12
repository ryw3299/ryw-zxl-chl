/**
 * 知识点关键词分析：n-gram + 短语切分 → 频次/概率图表 + 关键词共现网络（G6）
 */
(function () {
  "use strict";

  const STOP = new Set(
    "的 了 和 与 在 是 为 及 或 等 中 对 从 将 之 能 可 有 要 需 应 会 由 通过 基于 进行 方法 方式 包括 以及 不同 相同 本章 本节 例子 例如 一个 一种 一些 可以 能够 需要 必须 如果 由于 因此 所以 但是 然而 其中 其 各 每 当 时 后 前 上 下 内 外 所 以 于 即 也 又 还 都 而 则 且 但 并 被 把 让 使 得 着 过 地 很 更 最 较 再 已 已 未 无 非 是否 如何 什么 哪些 该 此 这 那 它 它们 它们 我们 你们 他们 其 之间 情况 部分 内容 过程 结果 作用 意义 目的 特点 优点 缺点 问题 原因 影响 因素 条件 要求 原则 步骤 第一 第二 第三 一步 二步 总结 分析 计算 确定 得到 得出 应用 使用 采用 选择 根据 按照 有关 相关 关于 对于 来说 而言 方面 领域 类型 形式 结构 系统 设备 装置 线路 电路 电流 电压 大小 数值 具体 实际 理想 对称 平衡 不平衡 正常 故障 状态 变化 增加 减少 升高 降低".split(
      /\s+/
    )
  );

  /** @type {string[]} */
  let knowledgePoints = [];
  /** @type {Map<string, number>} */
  let keywordDocFreq = new Map();
  /** @type {string[]} */
  let vocabulary = [];
  /** @type {Map<string, string[]>} */
  let pointKeywords = new Map();
  /** @type {Map<string, Map<string, number>>} */
  let edgeWeights = new Map();

  let pieChart = null;
  let barChart = null;
  let lineChart = null;
  let graph = null;

  /** 供 AI 系统提示使用的当前分析摘要 */
  let analysisContextForAI = "";
  /** OpenAI 格式多轮对话（仅 user / assistant） */
  let chatTurns = [];

  /**
   * @param {unknown} data
   * @returns {unknown[]}
   */
  function extractKnowledgeArray(data) {
    if (Array.isArray(data)) return data;
    if (data && typeof data === "object") {
      const o = /** @type {Record<string, unknown>} */ (data);
      if (Array.isArray(o.knowledge_points)) return o.knowledge_points;
      if (Array.isArray(o.knowledgePoints)) return o.knowledgePoints;
      if (Array.isArray(o.points)) return o.points;
    }
    throw new Error("未找到知识点数组（支持 knowledge_points / knowledgePoints / points 或根级数组）");
  }

  function countCooccurrenceEdges() {
    let n = 0;
    edgeWeights.forEach((inner) => {
      inner.forEach(() => {
        n += 1;
      });
    });
    return n;
  }

  /**
   * @param {{ k: string; c: number }[]} freqForCharts
   * @param {number} total
   */
  function buildAnalysisContextForAI(freqForCharts, total) {
    const top = freqForCharts
      .slice(0, 30)
      .map((x) => `${x.k}(${x.c})`)
      .join("、");
    const edges = countCooccurrenceEdges();
    return [
      `知识点条数：${knowledgePoints.length}`,
      `词表规模：${vocabulary.length}`,
      `关键词出现总计数（同一词在多条知识点中重复计数）：${total}`,
      `共现边条数（无向，边权为同知识点内共现次数）：${edges}`,
      `按文档频次排序的前 30 个关键词及频次：${top || "无"}`,
    ].join("\n");
  }

  function setNetworkCursor(c) {
    if (!graph) return;
    const canvas = graph.get("canvas");
    const el = canvas && canvas.get("el");
    if (el && el.style) el.style.cursor = c || "";
  }

  /** 节点包围盒等效半径 + 少量间距，用于拖动时软排斥 */
  function approxNodeRadius(item) {
    try {
      const bb = item.getBBox();
      return Math.sqrt((bb.width * bb.width + bb.height * bb.height) / 4) + 8;
    } catch (_) {
      return 36;
    }
  }

  /**
   * 拖动时与重叠邻居互相「挤开」，类似果冻弹性位移（每帧轻推，不替代力导向）
   * @param {*} g G6 Graph
   */
  function bindSoftRepulsionWhileDragging(g) {
    const jelly = 0.34;
    g.on("node:drag", (evt) => {
      const dragged = evt.item;
      if (!dragged || (typeof dragged.getType === "function" && dragged.getType() !== "node")) return;
      const dm = dragged.getModel();
      const x0 = dm.x;
      const y0 = dm.y;
      if (typeof x0 !== "number" || typeof y0 !== "number") return;
      const r0 = approxNodeRadius(dragged);
      const others = g.getNodes();
      for (let i = 0; i < others.length; i++) {
        const node = others[i];
        if (node === dragged) continue;
        const nm = node.getModel();
        const x1 = nm.x;
        const y1 = nm.y;
        if (typeof x1 !== "number" || typeof y1 !== "number") continue;
        const r1 = approxNodeRadius(node);
        const dx = x1 - x0;
        const dy = y1 - y0;
        const dist = Math.hypot(dx, dy);
        const need = r0 + r1 + 12;
        if (dist >= need || dist < 1e-6) continue;
        const push = (need - dist) * jelly;
        const ux = dx / dist;
        const uy = dy / dist;
        g.updateItem(node, { x: x1 + ux * push, y: y1 + uy * push });
      }
    });
  }

  /**
   * 松手后给力模拟补一点能量，让图继续慢慢归位
   * @param {*} g G6 Graph
   */
  function reheatForceLayout(g) {
    try {
      const lc = g.get("layoutController");
      const method =
        lc &&
        (lc.layoutMethod ||
          (Array.isArray(lc.layoutMethods) && lc.layoutMethods[0]));
      const sim = method && (method.forceSimulation || method.simulation);
      if (sim && typeof sim.alpha === "function") {
        const cur = typeof sim.alpha() === "number" ? sim.alpha() : 0;
        sim.alpha(Math.max(cur, 0.42));
        if (typeof sim.restart === "function") sim.restart();
      }
    } catch (_) {
      /* ignore */
    }
  }

  function onlyCjk(s) {
    return s.replace(/[^\u4e00-\u9fff]/g, "");
  }

  function isStopGram(sub) {
    if (STOP.has(sub)) return true;
    if (sub.length <= 1) return true;
    return false;
  }

  /**
   * 从单条知识点提取 n-gram（2～4 字），每条内去重
   * @param {string} text
   * @returns {Set<string>}
   */
  function ngramsForText(text) {
    const s = onlyCjk(text);
    const set = new Set();
    for (let L = 4; L >= 2; L--) {
      for (let i = 0; i + L <= s.length; i++) {
        const sub = s.slice(i, i + L);
        if (isStopGram(sub)) continue;
        set.add(sub);
      }
    }
    return set;
  }

  /**
   * 按标点切出短语片段，补充领域词
   * @param {string} text
   * @returns {Set<string>}
   */
  function phraseChunks(text) {
    const set = new Set();
    const parts = text.split(/[，。；、：？!！\s,.;:]+/).filter(Boolean);
    for (const p of parts) {
      const t = p.trim();
      if (t.length >= 2 && t.length <= 14 && !/^[\d.、\s]+$/.test(t)) {
        const cjk = onlyCjk(t);
        if (cjk.length >= 2 && cjk.length <= 14 && !isStopGram(cjk)) set.add(cjk);
      }
    }
    return set;
  }

  function buildAnalysis(minDocFreq, maxVocab, maxKwPerPoint) {
    keywordDocFreq = new Map();
    pointKeywords = new Map();
    edgeWeights = new Map();

    /** 每条知识点：候选词集合 */
    const perPointTerms = knowledgePoints.map((raw, idx) => {
      const a = ngramsForText(raw);
      const b = phraseChunks(raw);
      const merged = new Set([...a, ...b]);
      for (const term of merged) {
        keywordDocFreq.set(term, (keywordDocFreq.get(term) || 0) + 1);
      }
      return { idx, raw, merged };
    });

    /** 按文档频次筛词表，再按长度与频次排序 */
    const candidates = [...keywordDocFreq.entries()]
      .filter(([, df]) => df >= minDocFreq)
      .map(([w, df]) => ({ w, df, len: w.length }))
      .sort((x, y) => y.len - x.len || y.df - x.df || y.w.localeCompare(x.w));

    const vocabSet = new Set();
    for (const { w } of candidates) {
      if (vocabSet.size >= maxVocab) break;
      if (w.length >= 2) vocabSet.add(w);
    }
    vocabulary = [...vocabSet];

    /** 每条知识点：在词表中且被原文包含的词，取长优先、频次优先，截断 */
    for (const { idx, raw, merged } of perPointTerms) {
      const hits = vocabulary
        .filter((k) => raw.includes(k) && merged.has(k))
        .sort((a, b) => b.length - a.length || (keywordDocFreq.get(b) || 0) - (keywordDocFreq.get(a) || 0));
      const picked = [];
      const used = new Set();
      for (const k of hits) {
        if (picked.length >= maxKwPerPoint) break;
        let overlap = false;
        for (const u of used) {
          if (u.includes(k) || k.includes(u)) {
            overlap = true;
            break;
          }
        }
        if (overlap && picked.length > 0) continue;
        picked.push(k);
        used.add(k);
      }
      pointKeywords.set(String(idx), picked);

      for (let i = 0; i < picked.length; i++) {
        for (let j = i + 1; j < picked.length; j++) {
          const a = picked[i];
          const b = picked[j];
          const x = a < b ? a : b;
          const y = a < b ? b : a;
          if (!edgeWeights.has(x)) edgeWeights.set(x, new Map());
          const m = edgeWeights.get(x);
          m.set(y, (m.get(y) || 0) + 1);
        }
      }
    }

    /** 展示用频次：关键词在多少条知识点中出现（文档频次） */
    const freqForCharts = vocabulary.map((k) => ({ k, c: keywordDocFreq.get(k) || 0 })).filter((x) => x.c > 0);
    freqForCharts.sort((a, b) => b.c - a.c);

    const total = freqForCharts.reduce((s, x) => s + x.c, 0) || 1;

    return { freqForCharts, total };
  }

  function destroyCharts() {
    if (pieChart) {
      pieChart.destroy();
      pieChart = null;
    }
    if (barChart) {
      barChart.destroy();
      barChart = null;
    }
    if (lineChart) {
      lineChart.destroy();
      lineChart = null;
    }
  }

  function renderCharts(freqForCharts, total) {
    if (typeof Chart !== "undefined") {
      Chart.defaults.color = "#8b9cb3";
      Chart.defaults.borderColor = "rgba(100, 140, 180, 0.2)";
    }
    destroyCharts();
    const pieTop = 10;
    const top = freqForCharts.slice(0, pieTop);
    const rest = freqForCharts.slice(pieTop);
    const restSum = rest.reduce((s, x) => s + x.c, 0);
    const pieLabels = top.map((x) => x.k);
    const pieData = top.map((x) => x.c);
    if (restSum > 0) {
      pieLabels.push("（其余）");
      pieData.push(restSum);
    }

    const colors = [
      "#5b9fd4",
      "#7eb87e",
      "#d4a55b",
      "#c97b9c",
      "#9b7ed4",
      "#5bc0c0",
      "#d47e5b",
      "#8bc34a",
      "#e57373",
      "#64b5f6",
      "#9575cd",
      "#4db6ac",
    ];

    pieChart = new Chart(document.getElementById("va-chart-pie"), {
      type: "pie",
      data: {
        labels: pieLabels,
        datasets: [
          {
            data: pieData,
            backgroundColor: pieLabels.map((_, i) => colors[i % colors.length]),
            borderWidth: 1,
            borderColor: "#1a2332",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "right", labels: { color: "#8b9cb3", font: { size: 11 } } },
          tooltip: {
            callbacks: {
              label(ctx) {
                const v = ctx.raw;
                const p = ((v / total) * 100).toFixed(2);
                return ` ${ctx.label}: ${v} 次（占全部关键词出现计数的 ${p}%）`;
              },
            },
          },
        },
      },
    });

    const barN = Math.min(20, freqForCharts.length);
    const barSlice = freqForCharts.slice(0, barN);
    barChart = new Chart(document.getElementById("va-chart-bar"), {
      type: "bar",
      data: {
        labels: barSlice.map((x) => x.k),
        datasets: [
          {
            label: "出现知识点条数（文档频次）",
            data: barSlice.map((x) => x.c),
            backgroundColor: "rgba(91, 159, 212, 0.65)",
            borderColor: "#5b9fd4",
            borderWidth: 1,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            ticks: { color: "#8b9cb3" },
            grid: { color: "rgba(100,140,180,0.15)" },
          },
          y: {
            ticks: { color: "#8b9cb3", font: { size: 10 } },
            grid: { display: false },
          },
        },
        plugins: {
          legend: { labels: { color: "#8b9cb3" } },
          tooltip: {
            callbacks: {
              afterLabel(ctx) {
                const c = ctx.raw;
                const p = ((c / total) * 100).toFixed(2);
                return `概率（相对全部计数）: ${p}%`;
              },
            },
          },
        },
      },
    });

    const lineN = Math.min(40, freqForCharts.length);
    const lineSlice = freqForCharts.slice(0, lineN);
    const probs = lineSlice.map((x) => x.c / total);
    const cum = [];
    let s = 0;
    for (const p of probs) {
      s += p;
      cum.push(s);
    }

    lineChart = new Chart(document.getElementById("va-chart-line"), {
      type: "line",
      data: {
        labels: lineSlice.map((x, i) => `${i + 1}`),
        datasets: [
          {
            label: "单关键词概率 P(k)",
            data: probs.map((p) => Number((p * 100).toFixed(4))),
            borderColor: "#7eb87e",
            backgroundColor: "rgba(126, 184, 126, 0.15)",
            fill: true,
            tension: 0.25,
            yAxisID: "y",
          },
          {
            label: "累计概率 ΣP（前 n 位）",
            data: cum.map((c) => Number((c * 100).toFixed(2))),
            borderColor: "#5b9fd4",
            backgroundColor: "transparent",
            tension: 0.2,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: {
            title: { display: true, text: "按频次排序的名次", color: "#8b9cb3" },
            ticks: { color: "#8b9cb3", maxRotation: 0 },
            grid: { color: "rgba(100,140,180,0.1)" },
          },
          y: {
            position: "left",
            title: { display: true, text: "P × 100 (%)", color: "#8b9cb3" },
            ticks: { color: "#8b9cb3" },
            grid: { color: "rgba(100,140,180,0.12)" },
          },
          y1: {
            position: "right",
            title: { display: true, text: "累计 %", color: "#8b9cb3" },
            ticks: { color: "#8b9cb3" },
            grid: { drawOnChartArea: false },
          },
        },
        plugins: {
          legend: { labels: { color: "#8b9cb3" } },
          tooltip: {
            callbacks: {
              title(items) {
                const i = items[0].dataIndex;
                return lineSlice[i] ? lineSlice[i].k : "";
              },
            },
          },
        },
      },
    });
  }

  let vaKwNodeRegistered = false;
  function registerKeywordNode(G6) {
    if (vaKwNodeRegistered) return;
    vaKwNodeRegistered = true;
    G6.registerNode(
      "va-kw",
      {
        draw(cfg, group) {
          const w = Math.min(120, Math.max(56, (cfg.label || "").length * 11));
          const h = 36;
          group.addShape("rect", {
            attrs: {
              x: -w / 2,
              y: -h / 2,
              width: w,
              height: h,
              radius: 6,
              fill: "#243044",
              stroke: "#5b9fd4",
              lineWidth: cfg.isMax ? 2 : 1,
            },
            name: "bg",
          });
          group.addShape("text", {
            attrs: {
              text: fitting(cfg.label || "", 14),
              x: 0,
              y: 0,
              textAlign: "center",
              textBaseline: "middle",
              fontSize: 11,
              fill: "#e8eef5",
            },
            name: "txt",
          });
          /** 叠在文字之上、几乎透明，保证点在字上也能拖到节点 */
          const keyShape = group.addShape("rect", {
            attrs: {
              x: -w / 2,
              y: -h / 2,
              width: w,
              height: h,
              radius: 6,
              fill: "rgba(0,0,0,0.004)",
              stroke: "transparent",
              lineWidth: 0,
              cursor: "grab",
            },
            name: "hit",
          });
          return keyShape;
        },
      },
      "single-node"
    );
  }

  function fitting(s, maxLen) {
    if (s.length <= maxLen) return s;
    return s.slice(0, maxLen - 1) + "…";
  }

  function renderNetwork(freqForCharts) {
    const container = document.getElementById("va-network");
    if (!container || typeof G6 === "undefined") return;

    if (graph) {
      graph.destroy();
      graph = null;
    }

    const freqMap = new Map(freqForCharts.map((x) => [x.k, x.c]));
    const maxC = Math.max(...freqForCharts.map((x) => x.c), 1);

    const nodeSet = new Set();
    const edges = [];
    edgeWeights.forEach((inner, a) => {
      inner.forEach((w, b) => {
        if (w < 1) return;
        nodeSet.add(a);
        nodeSet.add(b);
        edges.push({
          id: `${a}||${b}`,
          source: a,
          target: b,
          label: String(w),
          w,
        });
      });
    });

    /** 孤立高频词也入图 */
    for (const { k } of freqForCharts.slice(0, 40)) {
      nodeSet.add(k);
    }

    const nodes = [...nodeSet].map((id) => {
      const c = freqMap.get(id) || 1;
      const size = 28 + Math.min(40, (c / maxC) * 36);
      return {
        id,
        label: id,
        type: "va-kw",
        size: [size + 40, 40],
        isMax: c === maxC,
      };
    });

    edges.sort((a, b) => b.w - a.w);
    const maxW = Math.max(...edges.map((e) => e.w), 1);
    const gEdges = edges.slice(0, 200).map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: `共现 ${e.w}`,
      style: {
        stroke: "rgba(91, 159, 212, 0.45)",
        lineWidth: 0.8 + (e.w / maxW) * 4,
      },
      labelCfg: {
        autoRotate: true,
        style: { fill: "#8b9cb3", fontSize: 10, background: { fill: "#1a2332", stroke: "#334", padding: [2, 4, 2, 4] } },
      },
    }));

    registerKeywordNode(G6);
    const { clientWidth: cw, clientHeight: ch } = container;

    const forceLayoutCfg = {
      type: "force",
      preventOverlap: true,
      nodeSpacing: 42,
      linkDistance: 118,
      nodeStrength: -165,
      edgeStrength: 0.2,
    };

    graph = new G6.Graph({
      container,
      width: cw || 800,
      height: ch || 520,
      layout: forceLayoutCfg,
      defaultNode: { type: "va-kw" },
      defaultEdge: {
        type: "line",
        style: { endArrow: false },
      },
      modes: { default: ["drag-canvas", "zoom-canvas", "drag-node"] },
      fitView: true,
      fitViewPadding: 24,
      minZoom: 0.2,
      maxZoom: 2.5,
    });
    graph.data({ nodes, edges: gEdges });
    graph.render();

    bindSoftRepulsionWhileDragging(graph);

    graph.on("node:mouseenter", () => setNetworkCursor("grab"));
    graph.on("node:mouseleave", () => setNetworkCursor(""));
    graph.on("node:dragstart", () => setNetworkCursor("grabbing"));
    graph.on("node:dragend", (evt) => {
      reheatForceLayout(graph);
      const item = evt.item;
      if (item && typeof item.getType === "function" && item.getType() === "node") setNetworkCursor("grab");
      else setNetworkCursor("");
    });
  }

  function run() {
    const minDf = parseInt(document.getElementById("va-min-df").value, 10) || 2;
    const maxVocab = parseInt(document.getElementById("va-max-vocab").value, 10) || 80;
    const maxKw = parseInt(document.getElementById("va-max-kw").value, 10) || 12;
    const status = document.getElementById("va-status");

    const { freqForCharts, total } = buildAnalysis(minDf, maxVocab, maxKw);
    analysisContextForAI = buildAnalysisContextForAI(freqForCharts, total);
    status.textContent = `知识点 ${knowledgePoints.length} 条 · 词表 ${vocabulary.length} · 关键词出现总计数 ${total}（同一词在多条知识点中重复计数）`;

    renderCharts(freqForCharts, total);
    renderNetwork(freqForCharts);
  }

  function loadData() {
    const status = document.getElementById("va-status");
    status.textContent = "加载 points.json…";
    fetch("points.json")
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      })
      .then((data) => {
        const arr = extractKnowledgeArray(data);
        knowledgePoints = arr.map((x) => String(x || "").trim()).filter(Boolean);
        run();
      })
      .catch((e) => {
        status.textContent = "";
        document.getElementById("va-error").textContent = "无法加载数据：" + (e.message || String(e));
      });
  }

  document.getElementById("va-rerun").addEventListener("click", () => {
    if (knowledgePoints.length) run();
  });

  ["va-min-df", "va-max-vocab", "va-max-kw"].forEach((id) => {
    document.getElementById(id).addEventListener("input", () => {
      if (knowledgePoints.length) run();
    });
  });

  window.addEventListener("resize", () => {
    if (!graph) return;
    const el = document.getElementById("va-network");
    graph.changeSize(el.clientWidth, el.clientHeight);
    graph.fitView(24);
  });

  function appendAiBubble(role, text, isErr) {
    const box = document.getElementById("va-ai-messages");
    if (!box) return;
    const div = document.createElement("div");
    const base = role === "user" ? "va-ai-msg--user" : "va-ai-msg--assistant";
    div.className = "va-ai-msg " + base + (isErr ? " va-ai-msg--err" : "");
    div.textContent = text;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  }

  function clearAiChat() {
    chatTurns = [];
    const box = document.getElementById("va-ai-messages");
    if (box) box.innerHTML = "";
  }

  async function sendAiMessage() {
    const input = document.getElementById("va-ai-input");
    if (!input) return;

    const text = input.value.trim();
    if (!text) return;

    if (!knowledgePoints.length) {
      appendAiBubble("assistant", "请先加载或导入知识点数据。", true);
      return;
    }

    input.value = "";
    appendAiBubble("user", text, false);
    chatTurns.push({ role: "user", content: text });

    const systemContent =
      "你是教育数据分析助手。下面「当前统计」来自本页实时分析结果，请据此回答，不要编造统计里没有的数字；若信息不足请说明。\n\n【当前统计】\n" +
      (analysisContextForAI || "（尚未完成分析，请用户点击「重新分析」或调整滑块。）");

    const sendBtn = document.getElementById("va-ai-send");
    if (sendBtn) sendBtn.disabled = true;

    try {
      const res = await fetch("/api/va-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "system", content: systemContent }, ...chatTurns],
        }),
      });

      const raw = await res.text();
      let data;
      try {
        data = JSON.parse(raw);
      } catch {
        throw new Error(res.ok ? "响应不是合法 JSON" : raw.slice(0, 200));
      }

      if (!res.ok) {
        const msg = data.error?.message || data.message || raw.slice(0, 300) || String(res.status);
        throw new Error(msg);
      }

      const reply = data.choices?.[0]?.message?.content;
      if (typeof reply !== "string" || !reply.trim()) {
        throw new Error("模型未返回有效文本");
      }
      appendAiBubble("assistant", reply.trim(), false);
      chatTurns.push({ role: "assistant", content: reply.trim() });
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : String(e);
      appendAiBubble(
        "assistant",
        "请求失败：" + errMsg + "\n请在本目录运行 node va-chat-server.mjs，用其地址打开页面（/api/va-chat 同域）；并在 .env 中配置 DEEPSEEK_API_KEY。",
        true
      );
    } finally {
      if (sendBtn) sendBtn.disabled = false;
    }
  }

  const importInput = document.getElementById("va-import-json");
  const importBtn = document.getElementById("va-import-btn");
  if (importBtn && importInput) {
    importBtn.addEventListener("click", () => importInput.click());
    importInput.addEventListener("change", (e) => {
      const f = /** @type {HTMLInputElement} */ (e.target).files?.[0];
      /** @type {HTMLInputElement} */ (e.target).value = "";
      if (!f) return;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const data = JSON.parse(String(reader.result || "{}"));
          const arr = extractKnowledgeArray(data);
          knowledgePoints = arr.map((x) => String(x || "").trim()).filter(Boolean);
          const errEl = document.getElementById("va-error");
          if (errEl) errEl.textContent = "";
          run();
          const st = document.getElementById("va-status");
          if (st) st.textContent += " · 已从文件导入";
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          const errEl = document.getElementById("va-error");
          if (errEl) errEl.textContent = "导入失败：" + msg;
        }
      };
      reader.readAsText(f, "UTF-8");
    });
  }

  const aiSend = document.getElementById("va-ai-send");
  const aiClear = document.getElementById("va-ai-clear");
  const aiInput = document.getElementById("va-ai-input");
  if (aiSend) aiSend.addEventListener("click", () => sendAiMessage());
  if (aiClear) aiClear.addEventListener("click", () => clearAiChat());
  if (aiInput) {
    aiInput.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && (ev.metaKey || ev.ctrlKey)) {
        ev.preventDefault();
        sendAiMessage();
      }
    });
  }

  loadData();
})();
