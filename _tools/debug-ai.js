// 调试 AI 评估函数：看它在具体局面上更喜欢哪个方向
const fs = require('fs');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', '2048.html'), 'utf8');
const code = html.slice(html.indexOf('/* ==== CORE-LOGIC-START ==== */'), html.indexOf('/* ==== CORE-LOGIC-END ==== */'));
const core = new Function(`${code}
  return { coreMoveBoard, coreMaxTile, toExps, evaluateExps, aiChooseMove, WEIGHTS, fastMove };`)();

function show(values) {
  return values.map((r) => r.map((v) => String(v).padStart(5)).join(' ')).join('\n');
}

console.log('当前评估权重:', JSON.stringify(core.WEIGHTS));

// 1) 好局面 vs 坏局面（同样的方块，排列不同）
const snake = [
  [2048, 1024, 512, 256],
  [16, 32, 64, 128],
  [8, 4, 2, 0],
  [0, 0, 0, 0],
];
const messy = [
  [2, 2048, 4, 1024],
  [8, 512, 16, 256],
  [32, 128, 64, 0],
  [0, 0, 0, 0],
];
console.log('\n[1] 同样方块、不同排列');
console.log('蛇形排列分数:', core.evaluateExps(core.toExps(snake)).toFixed(0));
console.log('杂乱排列分数:', core.evaluateExps(core.toExps(messy)).toFixed(0));

// 2) 合并前后的分数变化（左移 [2,2,4,4,...]）
const before = [[2, 2, 4, 4], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]];
const after = core.coreMoveBoard(before, 'left').board;
console.log('\n[2] 合并前的分数:', core.evaluateExps(core.toExps(before)).toFixed(0));
console.log('    左移后局面:');
console.log(show(after));
console.log('    合并后的分数:', core.evaluateExps(core.toExps(after)).toFixed(0));

// 3) 开局：一个 2 放在角落 vs 放在中间
const corner = [[2, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]];
const middle = [[0, 0, 0, 0], [0, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]];
console.log('\n[3] 单个 2 在角落:', core.evaluateExps(core.toExps(corner)).toFixed(0));
console.log('    单个 2 在中间:', core.evaluateExps(core.toExps(middle)).toFixed(0));

// 4) 实际对局前 12 步，看 AI 每步的选择
console.log('\n[4] 模拟一局的前 12 步');
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rng = mulberry32(20240913);
let values = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]];
function addRandom(v) {
  const cells = [];
  for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) if (!v[r][c]) cells.push([r, c]);
  const [r, c] = cells[Math.floor(rng() * cells.length)];
  v[r][c] = rng() < 0.9 ? 2 : 4;
}
addRandom(values);
addRandom(values);
for (let step = 0; step < 12; step++) {
  const decision = core.aiChooseMove(values, { maxDepth: 2 });
  console.log(`\n第 ${step + 1} 步：选择 ${decision.dir}`);
  const scores = [];
  for (const dir of ['left', 'right', 'up', 'down']) {
    const res = core.fastMove(core.toExps(values), dir);
    if (res.moved) scores.push(`${dir}=${core.evaluateExps(res.board).toFixed(0)}`);
  }
  console.log('  各方向静态分:', scores.join('  '));
  console.log(show(values));
  const plan = core.coreMoveBoard(values, decision.dir);
  values = plan.board;
  addRandom(values);
}
