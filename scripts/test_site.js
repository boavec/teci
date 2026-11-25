/**
 * 无头验证 site/index.html 的前端逻辑。
 *
 * 沙箱里跑不了 headless 浏览器（需要命名管道），所以这里用最小 DOM 桩
 * 真正执行页面里的内联脚本，断言它不抛异常、并且把数据渲染进了关键节点。
 *
 * 用法: node scripts/test_site.js
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const htmlPath = path.join(ROOT, "site", "index.html");
const dataPath = path.join(ROOT, "site", "data", "teci.js");

const html = fs.readFileSync(htmlPath, "utf8");

// 取最后一个内联 <script>
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
if (!scripts.length) {
  console.error("FAIL: 没找到内联脚本");
  process.exit(1);
}
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
  set innerHTML(v) {
    this._html = String(v);
    // 模拟浏览器：写 innerHTML 后 textContent 是去标签后的文本
    this._text = String(v).replace(/<[^>]*>/g, "");
  }
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

const win = {
  innerWidth: 1280,
  innerHeight: 900,
};

const sandbox = { window: win, document, console, __err: null };
win.document = document;

// 先把数据脚本挂到 window，再执行页面脚本
vm.runInNewContext(fs.readFileSync(dataPath, "utf8"), sandbox, { filename: "teci.js" });

try {
  vm.runInNewContext(inline, sandbox, { filename: "index.html:inline", timeout: 10000 });
} catch (e) {
  console.error("FAIL: 页面脚本抛异常 ->", e && e.message);
  console.error(e && e.stack);
  process.exit(1);
}

const check = [];
const ok = (name, cond, detail) => check.push({ name, cond: !!cond, detail });

check.push(() => {});
check.length = 0; // 清掉占位

ok("KPI 价格已渲染", /^\$\d/.test(get("#k-price").textContent), get("#k-price").textContent);
ok("KPI 每点成本已渲染", /^\$\d/.test(get("#k-cpp").textContent), get("#k-cpp").textContent);
ok("KPI 最优模型已渲染", get("#k-best").textContent.length > 0, get("#k-best").textContent);
ok("KPI 价差已渲染", /[0-9]/.test(get("#k-gap").textContent), get("#k-gap").textContent);

const svg = get("#scatter").innerHTML;
ok("散点图有圆点", (svg.match(/<circle/g) || []).length >= 10, `${(svg.match(/<circle/g) || []).length} 个圆点`);
ok("散点图有前沿线", svg.includes("polyline"), "");
ok("散点图有坐标轴标签", svg.includes("第三方智能评分"), "");

// 国内前沿与国内标签
const D0 = sandbox.window.TECI_DATA;
ok("数据含国内前沿", Array.isArray(D0.frontier_cn) && D0.frontier_cn.length >= 2,
   `${(D0.frontier_cn || []).length} 个点`);
ok("数据含国内前十", Array.isArray(D0.top_cn) && D0.top_cn.length === 10,
   `${(D0.top_cn || []).length} 个`);
ok("画出国内前沿曲线", svg.includes("front-line-cn"), "");
const cnLabels = (svg.match(/class="plabel plabel-cn"/g) || []).length;
ok("国内标签已标注", cnLabels >= 8, `${cnLabels} 个国内标签`);
const allLabels = (svg.match(/class="plabel/g) || []).length;
ok("标签总数符合预期", allLabels >= 15, `${allLabels} 个`);
// 标签不应超出画布
const tx = [...svg.matchAll(/<text class="plabel[^"]*" x="(-?[\d.]+)" y="(-?[\d.]+)"/g)]
  .map((m) => [parseFloat(m[1]), parseFloat(m[2])]);
ok("标签坐标在画布内", tx.every(([x, y]) => x >= 0 && x <= 1000 && y >= 0 && y <= 470),
   tx.length ? `x:[${Math.min(...tx.map(p => p[0])).toFixed(0)},${Math.max(...tx.map(p => p[0])).toFixed(0)}]` : "无");
ok("图注提到国内前沿", get("#scatter-note").textContent.includes("国内前沿"), "");

const tbody = get("#tbl tbody").innerHTML;
const rows = (tbody.match(/<tr>/g) || []).length;
ok("表格行数正确", rows >= 30, `${rows} 行`);

ok("分档位条形已渲染", (get("#tier-bars").innerHTML.match(/bar-row/g) || []).length === 3, "");
ok("国内海外对比表已渲染", get("#region-cmp").innerHTML.includes("中位每点成本"), "");
ok("国内海外结论已渲染", get("#region-note").innerHTML.length > 0, "");
ok("页脚日期已渲染", /\d{4}-\d{2}-\d{2}/.test(get("#f-date").textContent), get("#f-date").textContent);

// 新增：结论区
ok("结论一句话已生成", get("#vlead").textContent.includes("最划算"), get("#vlead").textContent.slice(0, 40) + "…");
ok("三个推荐卡已填充",
   ["#v-value-name", "#v-cheap-name", "#v-strong-name"].every((s) => get(s).textContent.length > 0),
   [get("#v-value-name").textContent, get("#v-cheap-name").textContent, get("#v-strong-name").textContent].join(" / "));

// 新增：能力门槛表
const capRows = (get("#cap-tbl").innerHTML.match(/<tr>/g) || []).length;
ok("能力门槛表有数据", capRows >= 5, `${capRows - 1} 行门槛`);

// 新增：厂商表
const vendRows = (get("#vendor-tbl").innerHTML.match(/<tr>/g) || []).length;
ok("厂商表有数据", vendRows >= 5, `${vendRows - 1} 家厂商`);

// 新增：区域档位矩阵
const matrix = get("#matrix-tbl").innerHTML;
ok("区域档位矩阵已生成",
   matrix.includes("国内") && matrix.includes("海外") && matrix.includes("旗舰"),
   "");
ok("矩阵对空档位有解释", get("#matrix-note").textContent.includes("不是漏数"), get("#matrix-note").textContent.slice(0, 30) + "…");

// 新增：采购计算器
ok("计算器已渲染结果", get("#calc-out").innerHTML.includes("符合条件的模型"),
   get("#calc-out").textContent.slice(0, 26) + "…");

const calc = sandbox.window.__TECI_CALC;
ok("计算器纯函数已暴露", typeof calc === "function", typeof calc);

if (typeof calc === "function") {
  const r = calc({ minScore: 50, region: "不限", volume: 100, wIn: 4, wOut: 1 });
  ok("达标筛选有结果", r.n > 0 && !!r.best, `${r.n} 个达标`);
  ok("月成本为正数", r.best.monthly > 0, "$" + r.best.monthly.toFixed(2));
  ok("前 3 按单价升序",
     r.top.every((t, i, a) => i === 0 || t.unit >= a[i - 1].unit), "");
  ok("最便宜的就是 top[0]",
     r.top.every((t) => t.unit >= r.best.unit - 1e-9), "");

  // 用公式手算一遍，确认单价和月成本没被写错
  const D2 = sandbox.window.TECI_DATA;
  const dm = D2.models.find((m) => m.id === r.best.id);
  const expectUnit = (4 * dm.usd_in + 1 * dm.usd_out) / 5;
  ok("单价与 4:1 公式一致", Math.abs(r.best.unit - expectUnit) < 1e-9,
     `计算 $${r.best.unit.toFixed(4)} / 手算 $${expectUnit.toFixed(4)}`);
  ok("月成本 = 单价 × 用量", Math.abs(r.best.monthly - expectUnit * 100) < 1e-6,
     "$" + r.best.monthly.toFixed(2));

  // 换权重应当改变单价（输出价通常远高于输入价）
  const r13 = calc({ minScore: 0, region: "不限", volume: 10, wIn: 1, wOut: 3 });
  ok("输入输出比会改变结果", r13.n > 0 && r13.best.unit !== r.best.unit,
     r13.best.id === r.best.id ? `同款但单价 $${r13.best.unit.toFixed(4)}` : "换了款");

  const rCN = calc({ minScore: 50, region: "国内", volume: 10, wIn: 4, wOut: 1 });
  ok("地区过滤生效", rCN.n === 0 || rCN.best.region === "国内", `${rCN.n} 个国内达标`);

  const rNone = calc({ minScore: 999, region: "不限", volume: 10, wIn: 4, wOut: 1 });
  ok("无达标时安全返回", rNone.n === 0 && !rNone.best, "n=0");
  ok("无达标时给出能力天花板",
     !!rNone.ceiling && rNone.ceiling.score > 0,
     rNone.ceiling ? `${rNone.ceiling.name} @ ${rNone.ceiling.score}` : "—");
}

// 检查 SVG 坐标是否越界
const cys = [...svg.matchAll(/cy="([\d.]+)"/g)].map((m) => parseFloat(m[1]));
const cxs = [...svg.matchAll(/cx="([\d.]+)"/g)].map((m) => parseFloat(m[1]));
const inBox = (arr, lo, hi) => arr.every((v) => v >= lo && v <= hi);
ok("散点坐标在画布内", inBox(cxs, 0, 1000) && inBox(cys, 0, 470),
   `x:[${Math.min(...cxs).toFixed(0)},${Math.max(...cxs).toFixed(0)}] y:[${Math.min(...cys).toFixed(0)},${Math.max(...cys).toFixed(0)}]`);

let failed = 0;
for (const c of check) {
  console.log(`${c.cond ? "PASS" : "FAIL"}  ${c.name}${c.detail ? "  (" + c.detail + ")" : ""}`);
  if (!c.cond) failed++;
}
console.log(`\n${check.length - failed}/${check.length} 通过`);
process.exit(failed ? 1 : 0);
