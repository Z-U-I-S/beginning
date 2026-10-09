**写在前面**
---
这是考核仓库的README，下文包含了我对每一个考核任务的解析与提交，当然也要在这里写几句话
<p>终于做完了……不容易啊，任务里面使用AI的部分只有小游戏和电路的几个.py文件，其余文本内容、html标签、本地环境的部署、git的所有提交与GitHub的部署为手搓（包括这个README）</p>
<p>在完成任务的过程中还是学到了不少新东西的，包括很多命令行操作，电脑系统的安装（说来话长）还有本地环境的部署，其实使用AI还是有点惶恐，在做
电路的部分时，很多内容其实我都不是很懂，也没有什么基础知识，纯自己在硬啃，今天也是请教了代院长关于放大电路的内容，才知道这个是大二才会学到的
知识，虽然现在不懂，不过也可以慢慢学吧……这里完成的所有内容，我都尽可能去搞懂了，但还是有一些实在没办法很快理解的部分，请见谅</p>
<p>↓以下是提交部分↓</p>

考核任务仓库
---
<h3>1.环境准备</h3>
<p>Ai编程工具使用：Deepseek Harness(部分使用Codex）</p>
<p>代码编辑器使用：WebStorm（部分使用CLion）</p>
<h3>2.个人简介</h3>
<p>PDF文件版：<a href=https://github.com/Z-U-I-S/beginning/blob/main/%E4%B8%AA%E4%BA%BA%E7%AE%80%E5%8E%86.pdf>个人简介</a></p>
<p>个人网站：<a href=https://z-u-i-s.github.io/self-page/>个人网站</a></p>
<h3>3.通用素养</h3>
<ol>
  <li>对分支与合并的理解:</li>
  <ol type='I'>
    <li>分支：新建存档</li>
    <li>合并：合并（覆盖？）存档（在没有冲突的情况下）</li>
  </ol>
  <li>Git命令行用法</li>
  <ol type='I'>
    <li>cd:访问指定目录（文件夹）</li>
    <li>ls/dir:列出当前文件夹内容</li>
    <li>mkdir:创建新文件夹</li>
    图片示意：
    <img src='img/git.png' title="Git效果图">
    <li>git 常用命令：</li>
      <ol type="1">
        <li>git add .：将更改好的文件存入暂存区</li>
        <li>git status：查看目录未提交文件状态</li>
        <li>git commit -m '……'：提交文件至本地仓库</li>
        <li>git push：推送文件至远程仓库</li>
        <li>git switch ……：更换到另一个分支</li>
      </ol>
  </ol>
    <li>信息安全意识：</li>
    <ul>
      <li>LICENSE：为项目添加许可证，为开源项目提供法律基础、建立信任、促进协作、保障商业合规</li>
      <li>GitHub两步验证：</li>
      <img src='img/double.png' title="两步验证">
      <li>查证：这个可能有点难找，目前用的模型还没遇到过，但有一些小bug是我检查后修正的，如图：</li>
      <img src='img/warning1.png' title='DS写出来的代码显示的报错' width="98" height="160">
      <img src='img/warning2.png' title='DS写出来的代码显示的报错' width="95" height="164">
      <p>修复后效果：</p>
      <img src='img/restore.png' title='修复后效果'>
    </ul>
    <li>关键代码：</li>
</ol>
<h3>4.小游戏</h3>
<p>提示词：最难受的来了，因为做这个项目的期间电脑重装了系统，但是我没有保存好API Key，所以之前输的提示词都丢失了，现在只能凭记忆复刻</p>
<p>第一段：请你按照以下要求，依据传统2048规则，生成一个不依赖其他框架的纯html格式的2048小游戏</p>
<p>要求：1.可以使用asdw或方向键操控数字方块移动方向</p>
<p>2.在游戏界面旁边添加游戏描述和操作介绍</p>
<p>3.添加AI操作功能，可以在网页端实现AI自动游玩</p>
<p>4.添加计时器与统计功能，计算玩家游玩时长与移动步数，将其保存到本地的历史记录</p>
<p>5.允许游玩时多次撤回</p>
<p>6.游戏界面可设置深色界面和浅色界面</p>
<p>第二段（发现了合出2048后界面有Bug）：在合出2048后有部分数字块显示在游戏胜利的界面上方，请你修改这部分代码，使合成出2048后弹出的胜利界面始终位于最上层；AI行动间隔太短，使AI模式运行时电脑卡顿，请你为AI模式每一步行动之间添加0.01秒的时间间隔</p>
<p>第三段（优化AI逻辑）：AI模式下的算法不符合主流游戏技巧，请你优化算法，使其运行时满足最大的数字保持在角落，其余数字由大到小向外分布的游戏思路</p>
<p>阶段1：</p>
<p>24~425行：游戏操作界面与设置</p>
<p>441~466行：计时器</p>
<p>475~599行：用asdw或方向键控制方块移动，合并，然后加分</p>
<p>阶段2：</p>
<p>612~662行：AI移动操作</p>
<p>669~876行：AI评估局面并决策操作</p>
<p>下附游戏截图</p>
<img src='img/2048AI.png' title='AI'>
<img src='img/2048pc.png' title='pc'>
<img src='img/2048phone.jpg' title='手机'>
<h3>5.电路</h3>
<ol type="1">
  <li>RC滤波电路</li>
<img src='img/理论值与误差值.png' title='理论值与误差值'>
<p>理论与误差值</p>
  <img src='img/手画电路.jpg' title='电路图'>
  <img src='img/rc_transient.png' title='波形图'>
  <img src='img/rc_bode.png' title='bode图'>
  <li>验证戴维南定理</li>
  <p><del>我还以为我要考研了</del></p>
  <img src='img/戴维南电路.jpg' title='手画图'>
<p>上面的第一个电路图是未接负载的电路（A与A'为端口），下面的是接入RL=1kΩ后的电路</p>
  <img src='img/戴维南定理数值.png' title='输出表格'>
  <img src='img/戴维南定理.png' title='输出表格'>
<p>输出表格如上图</p>
  <li>放大电路</li>
<p><del>这里我真学不会，没招了</del></p>
<p>对照表</p>
<img src='img/放大电路对照.png' title='输出表格'>
<p>波形图</p>
<img src='img/nmos_wave.png' title='波形图'>
手画图与I_D、V_DS、gm计算与饱和区判断（不知道为什么这里下标打不出来，我模仿AI的）
<img src='img/放大电路图.jpg' title='手画图'>
<img src='img/计算.jpg' title='计算'>
</ol>
以上
