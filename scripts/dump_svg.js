/**
 * 把页面跑出来的散点图 SVG 导出来，供 preview_chart.py 做视觉检查。
 *
 * 沙箱里不能开 headless 浏览器（需要命名管道），所以用最小 DOM 桩执行页面脚本，
 * 拿到 #scatter 的 innerHTML 落盘。
 *
 * 用法: node scripts/dump_svg.js
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "site", "index.html"), "utf8");
const dataPath = path.join(ROOT, "site", "data", "teci.js");

const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const inline = scripts[scripts.length - 1];

class El {
  constructor(sel) {
    this.sel = sel;
    this._html = "";
    this._text = "";
    this.dataset = {};
    this.style = {};
    this.classList = { add() {}, remove() {} };
  }
  set innerHTML(v) { this._html = String(v); this._text = String(v).replace(/<[^>]*>/g, ""); }
  get innerHTML() { return this._html; }
  set textContent(v) { this._text = String(v); }
  get textContent() { return this._text; }
  addEventListener() {}
}

const els = new Map();
const get = (sel) => {
  if (!els.has(sel)) els.set(sel, new El(sel));
  return els.get(sel);
};

const document = {
  querySelector: get,
  querySelectorAll: () => [],
  body: { insertAdjacentHTML() {} },
};
const win = { innerWidth: 1280, innerHeight: 900 };
const sandbox = { window: win, document, console };
win.document = document;

vm.runInNewContext(fs.readFileSync(dataPath, "utf8"), sandbox, { filename: "teci.js" });
vm.runInNewContext(inline, sandbox, { filename: "index.html:inline", timeout: 10000 });

const svg = get("#scatter").innerHTML;
const outDir = path.join(ROOT, "build");
fs.mkdirSync(outDir, { recursive: true });
const out = path.join(outDir, "scatter.svg");
fs.writeFileSync(out, `<svg xmlns="http://www.w3.org/2000/svg">${svg}</svg>`, "utf8");

const circles = (svg.match(/<circle/g) || []).length;
const labels = (svg.match(/<text/g) || []).length;
const lines = (svg.match(/<polyline/g) || []).length;
console.log(`导出 ${path.relative(ROOT, out)}  circle=${circles} text=${labels} polyline=${lines}`);
