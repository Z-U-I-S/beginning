// 生成视觉校验用的预览文件：在 2048.html 副本末尾注入一段脚本，摆出指定棋盘
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, '2048.html'), 'utf8');

function build(theme) {
  const inject = `
<script>
// —— 仅用于截图校验：摆出一个包含 2 ~ 8192 全部色阶的棋盘，并填充示例战绩 ——
window.addEventListener('load', function () {
  applyTheme('${theme}');
  var pattern = [
    [2,    4,    8,    16],
    [32,   64,   128,  256],
    [512,  1024, 2048, 4096],
    [8192, 0,    0,    0]
  ];
  rebuildBoard(pattern);
  score = 131072; moves = 888; best = 262144;
  roundStartAt = Date.now() - 754000;

  var now = Date.now();
  records = [
    { id: 'a1', score: 20164, maxTile: 2048, moves: 1204, duration: 612000, endedAt: now - 86400000 * 2, reason: 'gameover', ai: false, reached1024: true, reached2048: true },
    { id: 'a2', score: 12048, maxTile: 1024, moves: 902,  duration: 431000, endedAt: now - 86400000,     reason: 'gameover', ai: true,  reached1024: true, reached2048: false },
    { id: 'a3', score: 8452,  maxTile: 512,  moves: 640,  duration: 288000, endedAt: now - 7200000,      reason: 'abandon',  ai: false, reached1024: false, reached2048: false },
    { id: 'a4', score: 22180, maxTile: 2048, moves: 1330, duration: 705000, endedAt: now - 3600000,      reason: 'gameover', ai: true,  reached1024: true, reached2048: true },
    { id: 'a5', score: 131072, maxTile: 8192, moves: 888, duration: 754000, endedAt: now,                reason: 'gameover', ai: false, reached1024: true, reached2048: true }
  ];
  highlightRecordId = 'a5';
  renderStats();
  renderHistory();
  setAiStatus('AI 演示中…（Expectimax 期望最大搜索）', true);
  aiStats.depth = 4; aiStats.nodes = 168400;
  updateAiMeta();
  el.statTimer.textContent = formatDuration(elapsedMs());
});
</script>
`;
  return html.replace('</body>', inject + '</body>');
}

fs.writeFileSync(path.join(__dirname, 'preview-light.html'), build('light'), 'utf8');
fs.writeFileSync(path.join(__dirname, 'preview-dark.html'), build('dark'), 'utf8');
console.log('已生成 _tools/preview-light.html 与 _tools/preview-dark.html');
