// 生成端到端冒烟测试页：在真实浏览器里跑真实 DOM 代码，把结果写进页面，再用 --dump-dom 取回
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, '2048.html'), 'utf8');

const inject = `
<script>
window.addEventListener('load', function () {
  var out = [];
  var lastMismatch = null;
  function log(name, ok, extra) {
    out.push((ok ? 'PASS' : 'FAIL') + ' | ' + name + (extra ? ' | ' + extra : ''));
  }
  function tileCount() { return el.tileLayer.querySelectorAll('.tile').length; }
  function gridText() { return currentValues().map(function (r) { return r.join(','); }).join(';'); }

  try {
    // 1. 初始状态
    log('初始棋盘有 2 个方块', tileCount() === 2, 'tiles=' + tileCount());
    log('初始分数 / 步数为 0', score === 0 && moves === 0, 'score=' + score + ' moves=' + moves);

    // 2. localStorage 在 file:// 下是否可用（关系到“双击即可打开”）
    var lsOK = false;
    try { localStorage.setItem('__probe__', '1'); lsOK = localStorage.getItem('__probe__') === '1'; localStorage.removeItem('__probe__'); } catch (e) { lsOK = false; }
    log('localStorage 可用（file:// 场景）', lsOK);

    // 3. 随机走 120 步，检查分数与方块数守恒
    //    关键校验：每一步之后，界面里的真实盘面必须等于纯算法算出的盘面 + 一个随机新方块
    var dirs = ['left', 'right', 'up', 'down'];
    var movedCount = 0;
    var ruleMismatch = 0;
    for (var i = 0; i < 120; i++) {
      var before = currentValues();
      var dir = dirs[i % 4];
      var expect = coreMoveBoard(before, dir);
      if (!doMove(dir)) continue;
      movedCount++;
      var after = currentValues();
      var diff = [];
      for (var r = 0; r < 4; r++) {
        for (var c = 0; c < 4; c++) {
          if (after[r][c] !== expect.board[r][c]) diff.push([r, c, expect.board[r][c], after[r][c]]);
        }
      }
      // 允许的差异只有“多出一个新方块”，且必须落在原来是空格的位置、值只能是 2 或 4
      var okDiff = diff.length === 1 && expect.board[diff[0][0]][diff[0][1]] === 0
        && (diff[0][3] === 2 || diff[0][3] === 4);
      if (!okDiff) { ruleMismatch++; if (ruleMismatch <= 2) lastMismatch = JSON.stringify({ dir: dir, before: before, expect: expect.board, after: after }); }
    }
    log('每一步盘面都与核心算法完全一致（120 步）', ruleMismatch === 0, 'mismatch=' + ruleMismatch + (lastMismatch ? ' ' + lastMismatch : ''));

    var filled = tileCount();
    var nonEmpty = currentValues().reduce(function (a, r) { return a + r.filter(function (v) { return v > 0; }).length; }, 0);
    log('随机走子产生有效移动', movedCount > 0, 'moved=' + movedCount);
    log('DOM 方块数 = 模型方块数 + 待删除动画残留', filled === nonEmpty + pendingRemovals.length,
        'dom=' + filled + ' model=' + nonEmpty + ' pending=' + pendingRemovals.length);
    flushRemovals();
    log('清理动画残留后 DOM 与模型完全一致', tileCount() === nonEmpty, 'dom=' + tileCount() + ' model=' + nonEmpty);
    log('分数随合并增长或为 0', score >= 0, 'score=' + score);
    log('撤回栈记录了步数', undoStack.length === Math.min(movedCount, 500), 'stack=' + undoStack.length);

    // 4. 单步撤回：局面必须完全还原（先确保本局没有因为压力测试而结束）
    if (roundEnded) newGame();
    var snapValues = gridText(), snapScore = score, snapMoves = moves;
    var dir = null;
    for (var k = 0; k < 4; k++) { if (coreMoveBoard(currentValues(), dirs[k]).moved) { dir = dirs[k]; break; } }
    if (dir) {
      doMove(dir);
      undo();
      log('单步撤回完全还原局面', gridText() === snapValues && score === snapScore && moves === snapMoves,
          'score=' + score + '/' + snapScore);
    } else { log('单步撤回完全还原局面', false, '找不到可走方向'); }

    // 5. 多次撤回：连走 6 步再连撤 6 步，回到同一局面
    var beforeMulti = gridText(), beforeScore = score;
    var applied = 0;
    for (var t = 0; t < 40 && applied < 6; t++) { if (doMove(dirs[t % 4])) applied++; }
    for (var u = 0; u < applied; u++) undo();
    log('多次撤回回到 6 步之前的局面', gridText() === beforeMulti && score === beforeScore,
        'applied=' + applied + ' score=' + score + '/' + beforeScore);

    // 6. 键盘事件真的能驱动游戏
    var beforeKey = gridText();
    var changed = false;
    for (var q = 0; q < 12 && !changed; q++) {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: ['ArrowLeft','ArrowUp','ArrowRight','ArrowDown'][q % 4], bubbles: true }));
      if (gridText() !== beforeKey) changed = true;
    }
    log('键盘事件可以驱动游戏', changed);
    log('Ctrl+Z 撤回不报错', (function () {
      try { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'z', ctrlKey: true, bubbles: true })); return true; } catch (e) { return false; }
    })());

    // 7. 配色规则：2 白底深字、64 红、128 浅黄、2048 深黄、4096 黑
    //    注意：浏览器会把 #RRGGBB 规范化成 rgb(r, g, b)，所以断言用 rgb 形式
    function bgOf(v) { var t = createTile(v, 0, 0, null); var s = t.el.style.background; t.el.remove(); return s; }
    function colorOf(v) { var t = createTile(v, 0, 0, null); var s = t.el.style.color; t.el.remove(); return s; }
    var WHITE = 'rgb(255, 255, 255)';
    log('数字 2 底色为白色', bgOf(2).indexOf('rgb(255, 255, 255)') >= 0, bgOf(2));
    log('数字 2 的字色不是白色（保证可见）', colorOf(2).indexOf(WHITE) < 0, colorOf(2));
    log('数字 64 底色为红色 #E8452F', bgOf(64).indexOf('rgb(232, 69, 47)') >= 0, bgOf(64));
    log('数字 128 底色为浅黄 #FAF08C', bgOf(128).indexOf('rgb(250, 240, 140)') >= 0, bgOf(128));
    log('数字 2048 底色为深黄 #C08A00', bgOf(2048).indexOf('rgb(192, 138, 0)') >= 0, bgOf(2048));
    log('数字 4096 及以上底色为黑色', bgOf(4096).indexOf('rgb(10, 10, 10)') >= 0 && bgOf(8192).indexOf('rgb(10, 10, 10)') >= 0, bgOf(4096));
    log('2~64 色阶由浅至深（亮度依次下降）', (function () {
      var ladder = [2, 4, 8, 16, 32, 64];
      var lum = ladder.map(function (v) {
        var m = bgOf(v).match(/rgb\\((\\d+), (\\d+), (\\d+)\\)/);
        return m ? (0.299 * +m[1] + 0.587 * +m[2] + 0.114 * +m[3]) : -1;
      });
      for (var i = 1; i < lum.length; i++) { if (!(lum[i] < lum[i - 1])) return false; }
      return true;
    })());
    log('128~2048 色阶由浅至深', (function () {
      var ladder = [128, 256, 512, 1024, 2048];
      var lum = ladder.map(function (v) {
        var m = bgOf(v).match(/rgb\\((\\d+), (\\d+), (\\d+)\\)/);
        return m ? (0.299 * +m[1] + 0.587 * +m[2] + 0.114 * +m[3]) : -1;
      });
      for (var i = 1; i < lum.length; i++) { if (!(lum[i] < lum[i - 1])) return false; }
      return true;
    })());
    log('除数字 2 外全部方块数字使用白色', [4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096].every(function (v) { return colorOf(v).indexOf(WHITE) >= 0; }));

    // 8. 一局结束会写入历史，新一局不清零
    var roundBefore = records.length;
    var bestBefore = best;
    endRound('gameover');
    log('本局结束写入一条历史记录', records.length === roundBefore + 1, 'records=' + records.length);
    log('历史记录已持久化到 localStorage', (function () {
      try { return JSON.parse(localStorage.getItem('game2048.records')).length === records.length; } catch (e) { return false; }
    })());
    newGame();
    log('新一局不清零（记录与最高分保留）', records.length === roundBefore + 1 && best >= bestBefore, 'records=' + records.length + ' best=' + best);
    log('新一局棋盘重置为 2 个方块', tileCount() === 2 && score === 0, 'tiles=' + tileCount() + ' score=' + score);

    // 9. 侧边栏渲染出记录条目
    log('侧边栏渲染出历史条目', el.historyList.querySelectorAll('li').length === records.length,
        'li=' + el.historyList.querySelectorAll('li').length);

    // 10. 主题切换
    applyTheme('dark');
    var darkOK = document.documentElement.dataset.theme === 'dark' && el.btnTheme.textContent.indexOf('浅色') >= 0;
    applyTheme('light');
    log('主题切换即时生效并更新按钮文案', darkOK, 'theme=' + document.documentElement.dataset.theme);

    // 11. AI 能给出合法决策，且真的能推动游戏
    var decision = aiChooseMove(currentValues(), { maxDepth: 2, timeBudget: 0 });
    log('AI 给出决策（含深度与节点统计）', !!decision.dir && decision.nodes > 0 && decision.depth > 0,
        'dir=' + decision.dir + ' depth=' + decision.depth + ' nodes=' + decision.nodes);
    var aiMoved = doMove(decision.dir);
    log('AI 决策可以真正走子', aiMoved === true);
  } catch (err) {
    log('测试过程抛出异常', false, err && err.message);
  }

  var box = document.createElement('pre');
  box.id = 'TESTOUT';
  box.style.cssText = 'position:fixed;left:0;top:0;right:0;bottom:0;z-index:9999;margin:0;padding:16px;'
    + 'background:#fff;color:#111;font:15px/1.55 Consolas,monospace;white-space:pre-wrap;overflow:hidden';
  var passed = out.filter(function (s) { return s.indexOf('PASS') === 0; }).length;
  box.textContent = 'SMOKE TEST  ' + passed + '/' + out.length + ' PASSED\\n\\n' + out.join('\\n');
  document.body.innerHTML = '';
  document.body.appendChild(box);
});
</script>
`;

fs.writeFileSync(path.join(__dirname, 'smoke.html'), html.replace('</body>', inject + '</body>'), 'utf8');
console.log('已生成 _tools/smoke.html');
