/**
 * 2048 核心逻辑无头测试（Node.js）
 * 作用：把 2048.html 里 CORE-LOGIC 区域的纯逻辑抽出来，脱离浏览器验证。
 *   A. 经典用例：移动 / 合并 / 得分是否符合 2048 规则
 *   B. 一致性：AI 用的快速移动 fastMove 与渲染用的 coreMoveBoard 结果必须一致
 *   C. AI 实战：让 AI 自动玩 N 局，统计最高方块分布、达成 1024 / 2048 的比例
 *
 * 运行：node _tools/test-core.js [局数] [搜索深度] [权重覆盖] [评估方案]
 *   例：node _tools/test-core.js 12 3
 *       node _tools/test-core.js 12 3 "empty=300,merges=800" table
 *       node _tools/test-core.js 12 3 "" legacy
 */
const fs = require('fs');
const path = require('path');

const htmlPath = path.join(__dirname, '..', '2048.html');
const html = fs.readFileSync(htmlPath, 'utf8');
const START = '/* ==== CORE-LOGIC-START ==== */';
const END = '/* ==== CORE-LOGIC-END ==== */';
const s = html.indexOf(START);
const e = html.indexOf(END);
if (s < 0 || e < 0) throw new Error('没有找到 CORE-LOGIC 标记');
let coreCode = html.slice(s, e);

// 可选参数 5：历史遗留的“评估方案”参数，现已固定为加权版，传什么都忽略，仅为兼容旧命令
const evalMode = process.argv[5] || 'weights';

// 可选参数 4：覆盖评估权重（在源码里替换数字，保证在建表之前生效）。
// 支持 '{"merges":0.8}' 或 merges=0.8,empty=3 两种写法；写 - 表示不覆盖
const weightJson = process.argv[4] === '-' ? '' : process.argv[4];
const tuning = !!weightJson;
if (weightJson) {
  const startAt = coreCode.indexOf('const WEIGHTS = {');
  const endAt = coreCode.indexOf('};', startAt);
  if (startAt < 0 || endAt < 0) throw new Error('找不到权重对象 WEIGHTS');
  let block = coreCode.slice(startAt, endAt);

  const pairs = weightJson.trim().startsWith('{')
    ? Object.entries(JSON.parse(weightJson))
    : weightJson.split(',').map((part) => part.split('=').map((x) => x.trim()));
  for (const [key, value] of pairs) {
    const re = new RegExp(`(${key}:\\s*)-?[\\d.]+`);
    if (!re.test(block)) throw new Error('权重里没有这个字段: ' + key);
    block = block.replace(re, `$1${Number(value)}`);
  }
  coreCode = coreCode.slice(0, startAt) + block + coreCode.slice(endAt);
}

const core = new Function(`${coreCode}
  return { SIZE, DIRECTIONS, lineCoords, planLine, coreMoveBoard, coreHasMoves, coreMaxTile,
           toExps, fastMove, evaluateExps, aiChooseMove, emptyIndices, WEIGHTS };`)();

let pass = 0;
let fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual);
  const b = JSON.stringify(expected);
  if (a === b) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; console.log(`  ✗ ${name}\n      期望 ${b}\n      实际 ${a}`); }
}

/* ------------------------------------------------------------------ A. 规则 */
console.log('\n[A] 经典用例');
const empty = () => [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]];

let r = core.coreMoveBoard([[2, 2, 4, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], 'left');
check('[2,2,4,0] 左移 → [4,4,0,0]', r.board[0], [4, 4, 0, 0]);
check('  得分 = 4', r.gained, 4);

r = core.coreMoveBoard([[2, 2, 2, 2], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], 'left');
check('[2,2,2,2] 左移 → [4,4,0,0]（同一步内不连锁合并）', r.board[0], [4, 4, 0, 0]);
check('  得分 = 8', r.gained, 8);

r = core.coreMoveBoard([[4, 4, 8, 8], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], 'left');
check('[4,4,8,8] 左移 → [8,16,0,0]', r.board[0], [8, 16, 0, 0]);
check('  得分 = 24', r.gained, 24);

r = core.coreMoveBoard([[2, 0, 2, 4], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], 'left');
check('[2,0,2,4] 左移 → [4,4,0,0]', r.board[0], [4, 4, 0, 0]);

r = core.coreMoveBoard([[2, 4, 8, 16], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], 'right');
check('[2,4,8,16] 右移：已经贴边 → 没有变化', r.moved, false);

r = core.coreMoveBoard([[0, 4, 0, 2], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], 'right');
check('[0,4,0,2] 右移 → [0,0,4,2]', r.board[0], [0, 0, 4, 2]);

r = core.coreMoveBoard([[2, 0, 0, 0], [2, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], 'up');
check('竖直方向合并（上移）', [r.board[0][0], r.board[1][0], r.gained], [4, 0, 4]);

r = core.coreMoveBoard([[2, 0, 0, 0], [2, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], 'down');
check('竖直方向滑动（下移）', [r.board[3][0], r.board[2][0], r.gained], [4, 0, 4]);

r = core.coreMoveBoard([[2, 4, 2, 4], [4, 2, 4, 2], [2, 4, 2, 4], [4, 2, 4, 2]], 'left');
check('满盘且无相邻相同 → 走不动', r.moved, false);
check('  且 coreHasMoves = false', core.coreHasMoves(r.board), false);

check('[2,4,2,4] 满盘横排有可合并 → coreHasMoves = true',
  core.coreHasMoves([[2, 2, 4, 8], [4, 8, 16, 32], [8, 16, 32, 64], [16, 32, 64, 128]]), true);

/* ------------------------------------------------- B. 两个实现的一致性 */
console.log('\n[B] fastMove（AI 用）与 coreMoveBoard（渲染用）一致性');
function randomBoard(rng) {
  const values = empty();
  const pool = [0, 0, 2, 2, 4, 4, 8, 16, 32, 64, 128, 256];
  for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) values[r][c] = pool[Math.floor(rng() * pool.length)];
  return values;
}
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rng = mulberry32(20240913);
let mismatch = 0;
for (let i = 0; i < 3000; i++) {
  const values = randomBoard(rng);
  const dir = core.DIRECTIONS[i % 4];
  const slow = core.coreMoveBoard(values, dir);
  const fast = core.fastMove(core.toExps(values), dir);
  const fastBoard = [];
  for (let r = 0; r < 4; r++) {
    const row = [];
    for (let c = 0; c < 4; c++) {
      const exp = fast.board[r * 4 + c];
      row.push(exp === 0 ? 0 : 2 ** exp);
    }
    fastBoard.push(row);
  }
  if (JSON.stringify(slow.board) !== JSON.stringify(fastBoard) || slow.moved !== fast.moved) {
    mismatch++;
    if (mismatch <= 3) console.log('  不一致：', JSON.stringify(values), dir, JSON.stringify(slow.board), JSON.stringify(fastBoard));
  }
}
check('3000 个随机棋盘 × 4 方向，两个实现结果完全一致', mismatch, 0);

/* --------------------------------------------------------- C. AI 实战测试 */
console.log('\n[C] AI 自动对局');
const games = Number(process.argv[2] || 10);
const depth = Number(process.argv[3] || 3);
// 可选参数 6：随机种子基数。换一个基数就换一批全新的随机方块序列，
// 用来判断“好成绩”是真实力还是运气。
const seedBase = Number(process.argv[6] || 1000);

function addRandom(values, rng2) {
  const cells = [];
  for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) if (!values[r][c]) cells.push([r, c]);
  if (!cells.length) return;
  const [r, c] = cells[Math.floor(rng2() * cells.length)];
  values[r][c] = rng2() < 0.9 ? 2 : 4;
}

function playGame(depth2, seed) {
  const rng2 = mulberry32(seed);
  const values = empty();
  addRandom(values, rng2);
  addRandom(values, rng2);
  let score = 0;
  let moves = 0;
  let nodes = 0;
  while (true) {
    const decision = core.aiChooseMove(values, { maxDepth: depth2 });
    nodes += decision.nodes;
    if (!decision.dir) break;
    const plan = core.coreMoveBoard(values, decision.dir);
    if (!plan.moved) break;
    for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) values[r][c] = plan.board[r][c];
    score += plan.gained;
    moves++;
    addRandom(values, rng2);
    if (!core.coreHasMoves(values)) break;
  }
  return { score, moves, max: core.coreMaxTile(values), nodes };
}

const t0 = Date.now();
const results = [];
for (let i = 0; i < games; i++) {
  const game = playGame(depth, seedBase + i * 7919);
  results.push(game);
  if (!tuning) {
    console.log(`  第 ${String(i + 1).padStart(2)} 局：得分 ${String(game.score).padStart(6)} · 最大方块 ${String(game.max).padStart(5)} · ${String(game.moves).padStart(4)} 步 · 搜索节点 ${game.nodes}`);
  }
}
const seconds = (Date.now() - t0) / 1000;
const reached = (v) => results.filter((g) => g.max >= v).length;
const avg = (key) => Math.round(results.reduce((a, g) => a + g[key], 0) / results.length);
const dist = {};
for (const g of results) dist[g.max] = (dist[g.max] || 0) + 1;
const distText = Object.keys(dist).sort((a, b) => a - b).map((k) => `${k}×${dist[k]}`).join('  ');

if (tuning) {
  // 调参模式：只输出一行结果，方便批量对比
  console.log(`SUMMARY weights=${weightJson} mode=${evalMode} depth=${depth} games=${games} reach1024=${reached(1024)} reach2048=${reached(2048)} avgScore=${avg('score')} avgMoves=${avg('moves')} dist=[${distText}] time=${seconds.toFixed(0)}s`);
} else {
  console.log('\n  结果汇总');
  console.log(`    对局数        : ${games}（搜索深度 ${depth}）`);
  console.log(`    达成 1024 比例: ${reached(1024)}/${games} = ${(reached(1024) / games * 100).toFixed(0)}%`);
  console.log(`    达成 2048 比例: ${reached(2048)}/${games} = ${(reached(2048) / games * 100).toFixed(0)}%`);
  console.log(`    平均得分      : ${avg('score')}`);
  console.log(`    平均步数      : ${avg('moves')}`);
  console.log(`    最高方块分布  : ${distText}`);
  console.log(`    总耗时        : ${seconds.toFixed(1)} s`);
  // 固定输出一行纯英文摘要，方便外部脚本抓取（中文在部分终端会乱码）
  console.log(`SUMMARY weights="${weightJson || 'default'}" mode=${evalMode} depth=${depth} games=${games} reach1024=${reached(1024)} reach2048=${reached(2048)} avgScore=${avg('score')} avgMoves=${avg('moves')} dist=[${distText}] time=${seconds.toFixed(0)}s`);
}

console.log(`\n测试结束：通过 ${pass} 项，失败 ${fail} 项`);
process.exitCode = fail === 0 ? 0 : 1;
