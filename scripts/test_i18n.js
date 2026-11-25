/**
 * 验证英文模式真的生效：跑一遍页面脚本，断言 tr() 系列与 DOM 替换都输出英文。
 *
 * 沙箱里没有浏览器，所以这里造一个最小 DOM：一批假文本节点 + 一个能遍历它们的
 * createTreeWalker，用来真正跑一遍 translateDom()。
 *
 * 用法: node scripts/test_i18n.js
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "site", "index.html"), "utf8");
const i18nJs = fs.readFileSync(path.join(ROOT, "site", "data", "i18n.js"), "utf8");
const dataJs = fs.readFileSync(path.join(ROOT, "site", "data", "teci.js"), "utf8");
const inline = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]).pop();

const results = [];
const ok = (name, cond, detail) => results.push({ name, cond: !!cond, detail });

// ---- 最小 DOM ----
class El {
  constructor(sel) {
    this.sel = sel;
    this._html = "";
    this._text = "";
    this.dataset = {};
    this.style = {};
    this.classList = { add() {}, remove() {}, contains: () => false };
    this.value = "zh";
  }
  set innerHTML(v) { this._html = String(v); this._text = String(v).replace(/<[^>]*>/g, ""); }
  get innerHTML() { return this._html; }
  set textContent(v) { this._text = String(v); }
  get textContent() { return this._text; }
  addEventListener() {}
}

const els = new Map();
const get = (sel) => (els.has(sel) ? els.get(sel) : (els.set(sel, new El(sel)), els.get(sel)));

// 假文本节点：模拟页面里几段静态中文
function mkText(value) {
  return {
    nodeType: 3,
    nodeValue: value,
    parentNode: { nodeType: 1, tagName: "DIV", classList: { contains: () => false }, parentNode: null },
  };
}
const fakeNodes = [
  mkText("  模型  "),
  mkText("国内"),
  mkText("数据日期"),
  mkText("未评级"),
  mkText("中文语言选择器不该被替换"),
].map((n) => {
  n.parentNode.parentNode = null; // 让循环停在 parentNode 为 null
  return n;
});

const document = {
  body: { insertAdjacentHTML() {} },
  documentElement: {},
  getElementById: () => get("#lang-select"),
  querySelector: get,
  querySelectorAll: () => [],
  createTreeWalker: () => {
    let i = -1;
    return { nextNode: () => (++i < fakeNodes.length ? (this_cur = fakeNodes[i]) : null), get currentNode() { return this_cur; } };
  },
};
let this_cur = null;

const store = { "teci-lang": "en" };
const sandbox = {
  window: {},
  document,
  console,
  location: { search: "?lang=en", reload() {} },
  localStorage: {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
  },
  NodeFilter: { SHOW_TEXT: 4, FILTER_ACCEPT: 1, FILTER_REJECT: 2 },
};
sandbox.window = sandbox;
sandbox.window.document = document;
sandbox.window.localStorage = sandbox.localStorage;

try {
  vm.runInNewContext(i18nJs, sandbox, { filename: "i18n.js" });
  vm.runInNewContext(dataJs, sandbox, { filename: "teci.js" });
  vm.runInNewContext(inline, sandbox, { filename: "inline", timeout: 10000 });
} catch (e) {
  console.error("FAIL 脚本抛异常 ->", e.message);
  process.exit(1);
}

const vlead = get("#vlead").textContent;
ok("结论句已英文化", /best value|cheapest|most expensive/i.test(vlead), vlead.slice(0, 60) + "…");
ok("结论句不含中文", !/[\u4e00-\u9fff]/.test(vlead), "");

const kPrice = get("#k-price").textContent;
ok("KPI 不带中文", !/[\u4e00-\u9fff]/.test(kPrice), kPrice);

const note = get("#scatter-note").textContent;
ok("图注已英文化", !/[\u4e00-\u9fff]/.test(note), note.slice(0, 60) + "…");

// 静态文本经 translateDom 替换
const byVal = {};
fakeNodes.forEach((n) => (byVal[n.nodeValue.trim()] = n));
ok("静态文本已替换（模型）", (byVal["Model"] || "").nodeValue !== undefined, byVal["Model"] ? "Model" : "未找到");
ok("静态文本已替换（国内）", (byVal["Domestic"] || "").nodeValue !== undefined, byVal["Domestic"] ? "Domestic" : "未找到");
ok("静态文本已替换（数据日期）", (byVal["Data date"] || "").nodeValue !== undefined, "");
ok("未命中的文本保持原样", fakeNodes[4].nodeValue.includes("中文语言选择器"), "");
ok("替换保留原有空白", (byVal["Model"] || "").nodeValue === "  模型  ".replace("模型", "Model"), JSON.stringify(byVal["Model"] && byVal["Model"].nodeValue));

ok("html lang 已设置", document.documentElement.lang === "en", String(document.documentElement.lang));

let failed = 0;
for (const r of results) {
  console.log(`${r.cond ? "PASS" : "FAIL"}  ${r.name}${r.detail ? "  (" + r.detail + ")" : ""}`);
  if (!r.cond) failed++;
}
console.log(`\n${results.length - failed}/${results.length} 通过`);
process.exit(failed ? 1 : 0);
