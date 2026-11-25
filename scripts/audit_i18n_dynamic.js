/**
 * 动态审计：以英文模式执行页面脚本，找出「最终会在页面上残留中文」的文本。
 *
 * 判定规则贴近真实浏览器：
 *   把元素写入的 innerHTML 拆成一个个文本节点（translateDom 的粒度），
 *   只要该文本在词典里有对应译文，就认为会被替换掉；
 *   没有译文的才算漏网。
 *
 * 用法: node scripts/audit_i18n_dynamic.js
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "site", "index.html"), "utf8");
const i18nJs = fs.readFileSync(path.join(ROOT, "site", "data", "i18n.js"), "utf8");
const dataJs = fs.readFileSync(path.join(ROOT, "site", "data", "teci.js"), "utf8");
const inline = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]).pop();

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
const els = new Map();
const get = (s) => (els.has(s) ? els.get(s) : (els.set(s, new El(s)), els.get(s)));

const document = {
  body: { insertAdjacentHTML() {} },
  documentElement: {},
  title: "",
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

vm.runInNewContext(i18nJs, sandbox, { filename: "i18n.js" });
vm.runInNewContext(dataJs, sandbox, { filename: "teci.js" });
vm.runInNewContext(inline, sandbox, { filename: "inline", timeout: 10000 });

const dict = (sandbox.window.TECI_I18N || {}).en || {};
const norm = (s) =>
  String(s)
    .replace(/\s+/g, " ")
    .replace(/[\u201c\u201d]/g, '"')
    .replace(/[\u2018\u2019]/g, "'")
    .trim();
const known = new Set(Object.keys(dict).map(norm));
const CJK = /[\u4e00-\u9fff]/;

// translateDom 会跳过这些元素内部
const SKIP_ANCESTOR = /class="(?:lang-bar)"|id="beian"/;

const missing = [];
for (const [sel, el] of els) {
  if (SKIP_ANCESTOR.test(el._html)) continue;
  // 把 innerHTML 拆成文本节点
  const nodes = [...el._html.matchAll(/(?:^|>)([^<]+)/g)].map((m) => m[1]);
  const list = nodes.length ? nodes : [el._text || ""];
  for (const raw of list) {
    const t = norm(raw);
    if (!t || !CJK.test(t)) continue;
    if (known.has(t)) continue; // 有译文，translateDom 会替换
    missing.push({ sel, t });
  }
}

// 标题单独看
if (document.title && CJK.test(document.title) && !known.has(norm(document.title))) {
  missing.push({ sel: "<title>", t: document.title });
}

// 统计口径：确认审计确实看过了哪些元素、认出了多少中文片段
let cjkSeen = 0, cjkOk = 0;
for (const [, el] of els) {
  const nodes = [...el._html.matchAll(/(?:^|>)([^<]+)/g)].map((m) => m[1]);
  for (const raw of nodes) {
    const t = norm(raw);
    if (t && CJK.test(t)) { cjkSeen++; if (known.has(t)) cjkOk++; }
  }
}
console.log(`审计范围：${els.size} 个元素，词典 ${known.size} 条`);
console.log(`含中文片段 ${cjkSeen} 条，可翻译 ${cjkOk} 条，残留 ${missing.length} 条`);
if (els.has("#calc-out")) {
  const h = els.get("#calc-out")._html;
  const frags = [...h.matchAll(/(?:^|>)([^<]+)/g)].map((m) => norm(m[1])).filter((t) => t && CJK.test(t));
  console.log(`#calc-out 片段：${frags.length} 条${frags.length ? " -> " + frags.slice(0, 2).join(" | ") : "（全英文）"}`);
}

console.log(`\n英文模式下会残留中文的文本：${missing.length} 条\n`);
for (const m of missing) {
  console.log(`  ${m.sel.padEnd(14)} ${m.t.slice(0, 90)}${m.t.length > 90 ? "…" : ""}`);
}
process.exit(missing.length ? 1 : 0);
