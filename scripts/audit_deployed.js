/**
 * 线上版本审核：抓取已部署页面，以英文模式真跑一遍，列出残留中文。
 *
 * 判定依据是实际执行结果，不是截图，也不是静态文本。
 *
 * 用法:
 *   node scripts/audit_deployed.js            # 自动抓取线上页面
 *   node scripts/audit_deployed.js 文件路径    # 审核本地保存的 HTML
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const URL = "https://boavec.github.io/teci/?cb=" + Date.now();
const ROOT = path.resolve(__dirname, "..");

async function loadHtml() {
  const arg = process.argv[2];
  if (arg) return fs.readFileSync(arg, "utf8");
  const res = await fetch(URL, { headers: { "User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache" } });
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.text();
}

// 版本标记：判断部署的是不是最新代码
const MARKERS = {
  "规范化词典索引": "I18N_INDEX",
  "切换语言同步 URL": "searchParams.delete",
  "页脚来源走 T()": "T('数据来源：{src}",
  "矩阵脚注走 tr()": "tr('本次快照中国内厂商最高智能分未达旗舰阈值",
  "计算器走 T()": "T('符合条件的模型",
};

class El {
  constructor(sel) {
    this.sel = sel; this._html = ""; this._text = "";
    this.dataset = {}; this.style = {};
    this.classList = { add() {}, remove() {}, contains: () => false };
    this.value = "en";
  }
  set innerHTML(v) { this._html = String(v); this._text = String(v).replace(/<[^>]*>/g, " "); }
  get innerHTML() { return this._html; }
  set textContent(v) { this._text = String(v); this._html = String(v); }
  get textContent() { return this._text; }
  addEventListener() {}
}

function runScripts(html) {
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
  const els = new Map();
  // 给表单控件合理的默认值，否则计算器会走「无结果」分支，测不到结果区
  const DEFAULTS = { "#c-score": "50", "#c-region": "不限", "#c-vol": "50", "#c-ratio": "4:1" };
  const get = (s) => {
    if (els.has(s)) return els.get(s);
    const el = new El(s);
    if (DEFAULTS[s] !== undefined) el.value = DEFAULTS[s];
    els.set(s, el);
    return el;
  };
  const document = {
    body: { insertAdjacentHTML() {} },
    documentElement: {}, title: "",
    getElementById: () => get("#lang-select"),
    querySelector: get,
    querySelectorAll: () => [],
    createTreeWalker: () => ({ nextNode: () => null, currentNode: null }),
  };
  const store = { "teci-lang": "en" };
  const sandbox = {
    document, console,
    location: { search: "", reload() {} },
    localStorage: { getItem: (k) => store[k] ?? null, setItem: (k, v) => (store[k] = String(v)) },
    NodeFilter: { SHOW_TEXT: 4, FILTER_ACCEPT: 1, FILTER_REJECT: 2 },
    devicePixelRatio: 1,
  };
  sandbox.window = sandbox;
  sandbox.window.document = document;
  sandbox.window.localStorage = sandbox.localStorage;
  for (const s of scripts) vm.runInNewContext(s, sandbox, { timeout: 10000 });
  return { els, document, sandbox };
}

(async () => {
  const html = await loadHtml();
  console.log(`页面大小 ${(html.length / 1024).toFixed(0)} KB，内联脚本 ${[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].length} 段\n`);

  console.log("=== 部署版本 ===");
  let stale = 0;
  for (const [label, m] of Object.entries(MARKERS)) {
    const hit = html.includes(m);
    if (!hit) stale++;
    console.log(`  ${hit ? "✅" : "❌"}  ${label}`);
  }
  console.log(stale ? `\n→ ${stale} 项缺失，部署的仍是旧代码\n` : "\n→ 部署的是最新代码\n");

  let run;
  try {
    run = runScripts(html);
  } catch (e) {
    console.log(`❌ 脚本执行失败：${e.name}: ${e.message}`);
    process.exit(1);
  }
  const { els, sandbox } = run;

  const CJK = /[\u4e00-\u9fff]/;
  const norm = (s) => String(s).replace(/\s+/g, " ").replace(/[\u201c\u201d]/g, '"').trim();
  const dict = (sandbox.window.TECI_I18N || {}).en || {};
  const known = new Set(Object.keys(dict).map(norm));

  const left = [];
  for (const [sel, el] of els) {
    const nodes = [...el._html.matchAll(/(?:^|>)([^<]+)/g)].map((m) => m[1]);
    for (const raw of nodes) {
      const t = norm(raw);
      if (t && CJK.test(t) && !known.has(t)) left.push({ sel, t });
    }
  }

  console.log("=== 英文模式实际渲染 ===");
  console.log("  数据日期:", (els.get("#m-date") || {}).textContent || "(空)");
  console.log("  结论句  :", ((els.get("#vlead") || {}).textContent || "").slice(0, 60));
  console.log("  计算器  :", ((els.get("#calc-out") || {}).textContent || "").slice(0, 60));

  console.log(`\n=== 残留中文 ${left.length} 条 ===`);
  for (const l of left.slice(0, 15)) console.log(`  ${l.sel.padEnd(14)} ${l.t.slice(0, 80)}`);

  process.exit(left.length || stale ? 1 : 0);
})();
