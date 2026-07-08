#!/usr/bin/env python3
"""
生成均线交叉策略交互式回测工具 HTML（支持动态获取任意A股数据）。
内嵌5只默认标的数据 + 东方财富JSONP接口动态获取任意标的。
"""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKDIR = os.path.join(BASE, "task3")
DATA_FILE = os.path.join(WORKDIR, "backtest_data", "data_all.json")
OUT_HTML = os.path.join(WORKDIR, "backtest_tool.html")

with open(DATA_FILE, "r", encoding="utf-8") as f:
    raw = json.load(f)

slim = {}
for code, info in raw.items():
    d = info["data"]
    slim[code] = {
        "name": info["name"],
        "code": code,
        "dates": [r["date"] for r in d],
        "open":   [round(r["open"], 2) for r in d],
        "high":   [round(r["high"], 2) for r in d],
        "low":    [round(r["low"], 2) for r in d],
        "close":  [round(r["close"], 2) for r in d],
        "volume": [round(r["volume"], 0) for r in d],
    }

data_json = json.dumps(slim, ensure_ascii=False, separators=(",", ":"))

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>均线交叉策略 · 交互式回测工具</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/echarts/5.5.0/echarts.min.js"></script>
<style>
:root{
  --bg:#f5f6f8; --card:#ffffff; --ink:#1f2330; --muted:#6b7280; --line:#e7e9ee;
  --accent:#534AB7; --accent2:#185FA5; --up:#e74c3c; --down:#27ae60;
  --shadow:0 1px 3px rgba(0,0,0,.06),0 1px 2px rgba(0,0,0,.04);
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Microsoft YaHei","Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--ink);line-height:1.6}
.wrap{max-width:1240px;margin:0 auto;padding:18px 20px 60px}
header{background:linear-gradient(135deg,#3C3489,#534AB7);color:#fff;padding:22px 24px;border-radius:14px;box-shadow:var(--shadow);margin-bottom:18px}
header h1{font-size:20px;font-weight:600;letter-spacing:.5px}
header p{font-size:12.5px;opacity:.88;margin-top:4px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;box-shadow:var(--shadow);margin-bottom:16px}
.ctrl{display:flex;flex-wrap:wrap;gap:14px;align-items:flex-end}
.field{display:flex;flex-direction:column;gap:5px}
.field label{font-size:12px;color:var(--muted);font-weight:500}
.field select,.field input[type=number],.field input[type=text]{
  height:38px;padding:0 10px;border:1px solid var(--line);border-radius:8px;font-size:13.5px;background:#fff;color:var(--ink);min-width:90px}
.field select:focus,.field input:focus{outline:none;border-color:var(--accent)}
.btn{height:38px;padding:0 18px;border:none;border-radius:8px;background:var(--accent);color:#fff;font-size:13.5px;font-weight:500;cursor:pointer;transition:.15s;white-space:nowrap}
.btn:hover{background:#3C3489}
.btn:disabled{opacity:.55;cursor:default}
.btn.ghost{background:#fff;color:var(--accent);border:1px solid var(--accent)}
.btn.ghost:hover{background:#EEEDFE}
.btn.sm{height:32px;padding:0 12px;font-size:12px}
.btn.danger{background:#fff;color:#e74c3c;border:1px solid #e74c3c}
.btn.danger:hover{background:#fdecea}
.adv-toggle{font-size:12px;color:var(--accent);cursor:pointer;text-decoration:underline;margin-left:4px}
.adv{display:none;flex-wrap:wrap;gap:14px;margin-top:14px;padding-top:14px;border-top:1px dashed var(--line)}
.adv.show{display:flex}
.chips{margin-top:12px;display:flex;flex-wrap:wrap;align-items:center;gap:0}
.chips .lbl{font-size:12px;color:var(--muted);margin-right:8px;font-weight:500}
.chip{display:inline-block;padding:4px 12px;margin:2px;background:#f0f1f6;border:1px solid var(--line);border-radius:16px;font-size:12px;color:var(--ink);cursor:pointer;transition:.15s;user-select:none}
.chip:hover{background:var(--accent);color:#fff;border-color:var(--accent)}
.chip.added{background:#eafaf1;color:#1e8449;border-color:#27ae60;cursor:default}
.stock-actions{display:flex;gap:6px;align-items:center;margin-left:6px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:13px 15px;box-shadow:var(--shadow)}
.card .k{font-size:11.5px;color:var(--muted);font-weight:500}
.card .v{font-size:21px;font-weight:600;margin-top:4px}
.card .sub{font-size:11px;color:var(--muted);margin-top:2px}
.up{color:var(--up)} .down{color:var(--down)} .neu{color:var(--ink)}
.grid2{display:grid;grid-template-columns:1.4fr 1fr;gap:16px}
@media(max-width:980px){.grid2{grid-template-columns:1fr}}
.chart{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;box-shadow:var(--shadow);margin-bottom:16px}
.chart h3,.tbl-sec h3{font-size:14px;font-weight:600;margin-bottom:10px;padding-left:2px}
.cbox{width:100%;height:380px}
.cbox.sm{height:300px}
.tbl-sec{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;box-shadow:var(--shadow);margin-bottom:16px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{padding:8px 10px;text-align:center;border-bottom:1px solid var(--line)}
th{background:#f0f1f6;font-weight:600;color:#3c3f4d;position:sticky;top:0}
tbody tr:hover{background:#fafaff}
.scroll{max-height:320px;overflow-y:auto}
.tag{display:inline-block;padding:2px 8px;border-radius:5px;font-size:11px;font-weight:600}
.tag.buy{background:#fdecea;color:#c0392b}
.tag.sell{background:#eafaf1;color:#1e8449}
.tag.src{background:#e8eaf6;color:#3949ab;font-size:10px;padding:1px 6px}
.tag.src.dyn{background:#e8f5e9;color:#1b5e20}
footer{text-align:center;color:var(--muted);font-size:11.5px;margin-top:10px}
.note{font-size:11.5px;color:var(--muted);margin-top:8px}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid rgba(255,255,255,.4);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;vertical-align:middle;margin-right:4px}
@keyframes spin{to{transform:rotate(360deg)}}
.hint{font-size:11px;color:var(--muted);margin-top:3px}
/* Toast */
.toast-wrap{position:fixed;top:16px;right:16px;z-index:99999;display:flex;flex-direction:column;gap:8px}
.toast{padding:11px 18px;border-radius:8px;font-size:13px;color:#fff;opacity:0;transform:translateX(120px);transition:all .3s;max-width:380px;box-shadow:0 4px 12px rgba(0,0,0,.15)}
.toast.show{opacity:1;transform:translateX(0)}
.toast.ok{background:#27ae60} .toast.err{background:#e74c3c} .toast.warn{background:#f39c12} .toast.info{background:#534AB7}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>均线交叉策略 · 交互式回测工具</h1>
  <p>支持任意A股标的动态获取 · 可调快线/慢线天数 · 自动计算累计回报 / 夏普比率 / 最大回撤（MDD）｜ 默认数据：Tushare前复权 · 动态获取：东方财富前复权 · 涨红跌绿</p>
</header>

<!-- 控制面板 -->
<div class="panel">
  <div class="ctrl">
    <div class="field">
      <label>选择标的</label>
      <select id="selStock" style="min-width:180px"></select>
    </div>
    <div class="stock-actions">
      <button class="btn danger sm" id="btnRemove" title="从标的池移除当前标的">移除</button>
    </div>
    <div class="field">
      <label>添加标的（6位代码）</label>
      <div style="display:flex;gap:6px">
        <input type="text" id="inpCode" placeholder="如 000001" style="height:38px;width:130px;padding:0 10px;border:1px solid var(--line);border-radius:8px;font-size:13.5px">
        <button class="btn" id="btnFetch">获取数据</button>
      </div>
    </div>
    <div class="field">
      <label>快线天数</label>
      <input type="number" id="inpFast" value="5" min="1" max="60" step="1">
    </div>
    <div class="field">
      <label>慢线天数</label>
      <input type="number" id="inpSlow" value="20" min="2" max="120" step="1">
    </div>
    <div class="field">
      <label>均线类型</label>
      <select id="selMa">
        <option value="sma">SMA 简单移动平均</option>
        <option value="ema">EMA 指数移动平均</option>
      </select>
    </div>
    <div class="field">
      <label>&nbsp;</label>
      <button class="btn" id="btnRun">运行回测</button>
    </div>
    <div class="field">
      <label>&nbsp;</label>
      <span class="adv-toggle" id="advToggle">高级设置 ▾</span>
    </div>
  </div>
  <div class="adv" id="advPanel">
    <div class="field"><label>初始资金（元）</label><input type="number" id="inpCapital" value="100000" min="1000" step="1000"></div>
    <div class="field"><label>佣金费率（万）</label><input type="number" id="inpComm" value="3" min="0" step="0.5"></div>
    <div class="field"><label>滑点（千）</label><input type="number" id="inpSlip" value="1" min="0" step="0.5"></div>
    <div class="field"><label>无风险年利率(%)</label><input type="number" id="inpRf" value="0" min="0" step="0.5"></div>
    <div class="field" style="justify-content:flex-end"><button class="btn ghost sm" id="btnClearFetched">清空动态标的</button></div>
  </div>
  <!-- 快速添加 -->
  <div class="chips" id="quickAdd">
    <span class="lbl">快速添加：</span>
  </div>
  <div class="note" id="runInfo"></div>
</div>

<!-- 指标卡片 -->
<div class="cards" id="cards"></div>

<!-- 权益曲线 -->
<div class="chart">
  <h3>权益曲线（策略净值 vs 买入持有基准，归一化起点=1.0）</h3>
  <div id="chartEquity" class="cbox"></div>
</div>

<div class="grid2">
  <div class="chart">
    <h3>价格 / 均线 / 买卖信号</h3>
    <div id="chartPrice" class="cbox"></div>
  </div>
  <div class="chart">
    <h3>回撤曲线（Drawdown）</h3>
    <div id="chartDD" class="cbox sm"></div>
  </div>
</div>

<!-- 多标的对比 -->
<div class="tbl-sec">
  <h3>多标的对比（当前参数下全部标的一览）</h3>
  <table id="cmpTable">
    <thead><tr>
      <th>标的</th><th>来源</th><th>策略累计回报</th><th>基准累计回报</th><th>夏普比率</th><th>最大回撤</th><th>年化收益</th><th>年化波动</th><th>交易次数</th><th>胜率</th><th>Calmar</th>
    </tr></thead>
    <tbody></tbody>
  </table>
</div>

<!-- 交易明细 -->
<div class="tbl-sec">
  <h3>交易明细</h3>
  <table id="tradeTable">
    <thead><tr><th>#</th><th>日期</th><th>方向</th><th>价格(元)</th><th>数量(股)</th><th>金额(元)</th><th>手续费(元)</th><th>现金余额(元)</th></tr></thead>
    <tbody></tbody>
  </table>
</div>

<footer>均线交叉策略回测 · 仅供教学研究，不构成投资建议 · 默认数据：Tushare · 动态获取：东方财富</footer>
</div>

<div class="toast-wrap" id="toastWrap"></div>

<script>
const RAW = __DATA__;
const EMBEDDED = new Set(Object.keys(RAW));
const RED="#e74c3c", GREEN="#27ae60";

// 热门标的
const HOT = [
  {code:'000001',name:'平安银行'},{code:'601318',name:'中国平安'},
  {code:'000858',name:'五粮液'},{code:'002415',name:'海康威视'},
  {code:'000725',name:'京东方A'},{code:'600276',name:'恒瑞医药'},
  {code:'300015',name:'爱尔眼科'},{code:'601012',name:'隆基绿能'},
  {code:'600900',name:'长江电力'},{code:'002230',name:'科大讯飞'},
  {code:'601398',name:'工商银行'},{code:'000568',name:'泸州老窖'},
];

// ============ 指标计算 ============
function sma(a,p){const o=new Array(a.length).fill(NaN);let s=0;for(let i=0;i<a.length;i++){s+=a[i];if(i>=p)s-=a[i-p];if(i>=p-1)o[i]=s/p;}return o;}
function ema(a,p){const o=new Array(a.length).fill(NaN);const k=2/(p+1);let prev=NaN;for(let i=0;i<a.length;i++){if(i<p-1)continue;if(i===p-1){let s=0;for(let j=0;j<p;j++)s+=a[j];prev=s/p;}else{prev=a[i]*k+prev*(1-k);}o[i]=prev;}return o;}
function mean(a){return a.reduce((x,y)=>x+y,0)/a.length;}
function std(a){if(a.length<2)return 0;const m=mean(a);return Math.sqrt(a.reduce((s,v)=>s+(v-m)*(v-m),0)/(a.length-1));}

// ============ 信号生成 ============
function genSignals(maS,maL){
  const n=maS.length;
  const pos=new Array(n).fill(0), sig=new Array(n).fill(0);
  for(let i=1;i<n;i++){
    if(isNaN(maS[i])||isNaN(maL[i])||isNaN(maS[i-1])||isNaN(maL[i-1])){pos[i]=pos[i-1];continue;}
    const gold = maS[i]>maL[i] && maS[i-1]<=maL[i-1];
    const dead = maS[i]<maL[i] && maS[i-1]>=maL[i-1];
    if(gold){pos[i]=1;sig[i]=1;}
    else if(dead){pos[i]=0;sig[i]=-1;}
    else pos[i]=pos[i-1];
  }
  return {pos,sig};
}

// ============ 回测引擎 ============
function backtest(dates,open,close,pos,sig,par){
  let cash=par.cap, shares=0, hold=false;
  const eq=[], trades=[];
  for(let t=0;t<dates.length;t++){
    if(t>0){
      if(sig[t-1]===1 && !hold){
        const px=open[t], rate=par.comm+par.slip, costF=1+rate;
        const mx=Math.floor(cash/(px*costF)/100)*100;
        if(mx>0){const tot=mx*px, fee=tot*rate; cash-=tot+fee; shares=mx; hold=true;
          trades.push({idx:t,date:dates[t],type:'BUY',price:px,shares:mx,amt:tot,fee,cash:cash});}
      }else if(sig[t-1]===-1 && hold){
        const px=open[t], proceeds=shares*px, fee=proceeds*(par.comm+par.slip);
        cash+=proceeds-fee;
        trades.push({idx:t,date:dates[t],type:'SELL',price:px,shares,amt:proceeds,fee,cash:cash});
        shares=0; hold=false;
      }
    }
    eq.push(cash+shares*close[t]);
  }
  return {eq,trades};
}

// ============ 指标 ============
function metrics(eq,trades,par){
  const N=eq.length;
  const cumR=eq[N-1]/eq[0]-1;
  const rets=[];for(let i=1;i<N;i++)rets.push(eq[i]/eq[i-1]-1);
  const mR=mean(rets), sR=std(rets);
  const rfD=Math.pow(1+par.rf,1/252)-1;
  const sharpe=sR===0?0:(mR-rfD)/sR*Math.sqrt(252);
  let peak=eq[0],mdd=0,ddArr=new Array(N);
  for(let i=0;i<N;i++){if(eq[i]>peak)peak=eq[i];let dd=(eq[i]-peak)/peak;ddArr[i]=dd*100;if(dd<mdd)mdd=dd;}
  mdd=Math.abs(mdd);
  const annRet=Math.pow(1+cumR,252/N)-1;
  const annVol=sR*Math.sqrt(252);
  const calmar=mdd===0?0:annRet/mdd;
  let wins=0,pairs=0;
  for(let i=0;i+1<trades.length;i+=2){
    if(trades[i].type==='BUY'&&trades[i+1]&&trades[i+1].type==='SELL'){pairs++;if(trades[i+1].price>trades[i].price)wins++;}
  }
  const winRate=pairs===0?0:wins/pairs;
  return {cumR,sharpe,mdd,annRet,annVol,calmar,trades:trades.length,winRate,ddArr};
}

// ============ 主流程 ============
let cur=null;
const params=()=>({fast:+document.getElementById('inpFast').value,slow:+document.getElementById('inpSlow').value,
  ma:document.getElementById('selMa').value,cap:+document.getElementById('inpCapital').value,
  comm:(+document.getElementById('inpComm').value)/1e4,slip:(+document.getElementById('inpSlip').value)/1e3,
  rf:(+document.getElementById('inpRf').value)/100});

function runOne(code){
  const d=RAW[code];
  const p=params();
  const maS=p.ma==='ema'?ema(d.close,p.fast):sma(d.close,p.fast);
  const maL=p.ma==='ema'?ema(d.close,p.slow):sma(d.close,p.slow);
  const {pos,sig}=genSignals(maS,maL);
  const bt=backtest(d.dates,d.open,d.close,pos,sig,p);
  const m=metrics(bt.eq,bt.trades,p);
  const bm=d.close.map(c=>c/d.close[0]);
  return {d,p,maS,maL,sig,bt,m,bm};
}

function fmtPct(x){return (x*100).toFixed(2)+'%';}
function fmtNum(x,n=2){return x.toFixed(n);}
function valColor(x){return x>0?'up':(x<0?'down':'neu');}

function renderCards(r){
  const m=r.m,p=params();
  const items=[
    {k:'策略累计回报',v:fmtPct(m.cumR),c:valColor(m.cumR),s:'初始资金 ¥'+fmtNum(p.cap,0)},
    {k:'基准累计回报',v:fmtPct(r.bm[r.bm.length-1]-1),c:valColor(r.bm[r.bm.length-1]-1),s:'买入持有'},
    {k:'夏普比率 Sharpe',v:fmtNum(m.sharpe),c:valColor(m.sharpe),s:'年化 · rf='+p.rf*100+'%'},
    {k:'最大回撤 MDD',v:fmtPct(m.mdd),c:'down',s:'峰值到谷底'},
    {k:'年化收益率',v:fmtPct(m.annRet),c:valColor(m.annRet),s:'复利年化'},
    {k:'年化波动率',v:fmtPct(m.annVol),c:'neu',s:'日收益标准差×√252'},
    {k:'交易次数',v:m.trades,s:'金叉+死叉'},
    {k:'胜率',v:fmtPct(m.winRate),c:valColor(m.winRate-0.5),s:'盈利交易/总配对'},
    {k:'Calmar 比率',v:fmtNum(m.calmar),c:valColor(m.calmar),s:'年化收益/MDD'},
  ];
  document.getElementById('cards').innerHTML=items.map(it=>
    `<div class="card"><div class="k">${it.k}</div><div class="v ${it.c||''}">${it.v}</div>${it.s?`<div class="sub">${it.s}</div>`:''}</div>`).join('');
}

let cEq,cPr,cDD;
function initCharts(){cEq=echarts.init(document.getElementById('chartEquity'));cPr=echarts.init(document.getElementById('chartPrice'));cDD=echarts.init(document.getElementById('chartDD'));window.addEventListener('resize',()=>{cEq.resize();cPr.resize();cDD.resize();});}

function renderCharts(r){
  const d=r.d,p=r.p;
  const net=r.bt.eq.map(v=>v/params().cap);
  const bm=r.bm;
  cEq.setOption({
    tooltip:{trigger:'axis'},
    legend:{data:['策略净值','基准净值'],top:6},
    grid:{left:50,right:30,top:40,bottom:60},
    xAxis:{type:'category',data:d.dates},
    yAxis:{type:'value',scale:true,name:'净值'},
    dataZoom:[{type:'inside'},{type:'slider',bottom:10}],
    series:[
      {name:'策略净值',type:'line',data:net.map((v,i)=>[d.dates[i],+v.toFixed(4)]),smooth:true,symbol:'none',lineStyle:{width:2,color:'#534AB7'},areaStyle:{color:'rgba(83,74,183,.08)'}},
      {name:'基准净值',type:'line',data:bm.map((v,i)=>[d.dates[i],+v.toFixed(4)]),smooth:true,symbol:'none',lineStyle:{width:1.5,color:'#999',type:'dashed'}},
    ]
  },true);
  const ohlc=d.dates.map((dt,i)=>[dt,d.open[i],d.close[i],d.low[i],d.high[i]]);
  const buyPts=[],sellPts=[];
  for(let t=0;t<d.dates.length;t++){
    if(r.sig[t]===1)buyPts.push({coord:[d.dates[t],d.high[t]*1.01],value:'买'});
    if(r.sig[t]===-1)sellPts.push({coord:[d.dates[t],d.low[t]*0.99],value:'卖'});
  }
  cPr.setOption({
    tooltip:{trigger:'axis',axisPointer:{type:'cross'}},
    legend:{data:['K线','MA'+p.fast,'MA'+p.slow],top:6},
    grid:{left:55,right:60,top:40,bottom:60},
    xAxis:{type:'category',data:d.dates},
    yAxis:[{type:'value',scale:true,name:'价格(元)',position:'left'},{type:'value',scale:true,name:'成交量',position:'right',splitLine:{show:false}}],
    dataZoom:[{type:'inside'},{type:'slider',bottom:10}],
    series:[
      {name:'K线',type:'candlestick',data:ohlc,itemStyle:{color:RED,color0:GREEN,borderColor:RED,borderColor0:GREEN},
        markPoint:{symbol:'triangle',symbolSize:12,data:[...buyPts.map(b=>({...b,itemStyle:{color:RED}})),...sellPts.map(s=>({...s,symbol:'pin',symbolRotate:180,itemStyle:{color:GREEN}}))]}},
      {name:'MA'+p.fast,type:'line',data:d.dates.map((dt,i)=>[dt,r.maS[i].toFixed?+r.maS[i].toFixed(2):r.maS[i]]),smooth:true,symbol:'none',lineStyle:{width:1.3,color:'#f39c12'}},
      {name:'MA'+p.slow,type:'line',data:d.dates.map((dt,i)=>[dt,r.maL[i].toFixed?+r.maL[i].toFixed(2):r.maL[i]]),smooth:true,symbol:'none',lineStyle:{width:1.3,color:'#185FA5'}},
      {name:'成交量',type:'bar',xAxisIndex:0,yAxisIndex:1,data:d.volume.map((v,i)=>[d.dates[i],v]),itemStyle:{color:'#cfd3dc'},large:true},
    ]
  },true);
  cDD.setOption({
    tooltip:{trigger:'axis',formatter:p=>p[0].axisValue+'<br/>回撤: '+p[0].data[1].toFixed(2)+'%'},
    grid:{left:55,right:30,top:30,bottom:50},
    xAxis:{type:'category',data:d.dates},
    yAxis:{type:'value',name:'回撤%',axisLabel:{formatter:'{value}%'}},
    dataZoom:[{type:'inside'},{type:'slider',bottom:10}],
    series:[{type:'line',data:d.dates.map((dt,i)=>[dt,+r.m.ddArr[i].toFixed(2)]),smooth:true,symbol:'none',areaStyle:{color:'rgba(231,76,60,.15)'},lineStyle:{color:RED,width:1.2}}]
  },true);
}

function renderTrades(r){
  const tb=document.querySelector('#tradeTable tbody');
  if(!r.bt.trades.length){tb.innerHTML='<tr><td colspan="8">无交易记录</td></tr>';return;}
  tb.innerHTML=r.bt.trades.map((t,i)=>{
    const cls=t.type==='BUY'?'buy':'sell';
    return `<tr><td>${i+1}</td><td>${t.date}</td><td><span class="tag ${cls}">${t.type==='BUY'?'买入':'卖出'}</span></td>
    <td>${fmtNum(t.price)}</td><td>${t.shares}</td><td>${fmtNum(t.amt,0)}</td><td>${fmtNum(t.fee,2)}</td><td>${fmtNum(t.cash,0)}</td></tr>`;
  }).join('');
}

function renderCompare(){
  const codes=Object.keys(RAW);
  const rows=codes.map(code=>{
    const r=runOne(code);
    const m=r.m;
    return {name:r.d.name+' '+code,code,embedded:EMBEDDED.has(code),m,bm:r.bm[r.bm.length-1]-1,n:r.d.dates.length};
  });
  document.querySelector('#cmpTable tbody').innerHTML=rows.map(r=>
    `<tr><td>${r.name}</td><td><span class="tag ${r.embedded?'src':'src dyn'}">${r.embedded?'默认':'动态'}</span></td>
    <td class="${valColor(r.m.cumR)}">${fmtPct(r.m.cumR)}</td><td class="${valColor(r.bm)}">${fmtPct(r.bm)}</td>
    <td class="${valColor(r.m.sharpe)}">${fmtNum(r.m.sharpe)}</td><td class="down">${fmtPct(r.m.mdd)}</td>
    <td class="${valColor(r.m.annRet)}">${fmtPct(r.m.annRet)}</td><td>${fmtPct(r.m.annVol)}</td>
    <td>${r.m.trades}</td><td class="${valColor(r.m.winRate-0.5)}">${fmtPct(r.m.winRate)}</td><td>${fmtNum(r.m.calmar)}</td></tr>`
  ).join('');
}

function run(){
  const code=document.getElementById('selStock').value;
  if(!code||!RAW[code])return;
  const p=params();
  if(p.fast>=p.slow){toast('快线天数需小于慢线天数','warn');return;}
  if(p.fast<1||p.slow<2){toast('快线≥1，慢线≥2','warn');return;}
  const r=runOne(code);
  cur=r;
  renderCards(r);renderCharts(r);renderTrades(r);renderCompare();
  const src=EMBEDDED.has(code)?'Tushare':'东方财富';
  document.getElementById('runInfo').textContent=
    `${RAW[code].name}(${code}) · ${p.ma.toUpperCase()}(${p.fast},${p.slow}) · ${r.d.dates.length}个交易日 · ${r.d.dates[0]} ~ ${r.d.dates[r.d.dates.length-1]} · 数据:${src} · 金叉/死叉共${r.m.trades}次 · 标的池:${Object.keys(RAW).length}只`;
}

// ============ JSONP 动态获取 ============
let _jpCtr=0;
function jsonp(url,cb,errCb){
  const name='__jp_'+(++_jpCtr);
  const s=document.createElement('script');
  window[name]=function(data){delete window[name];s.remove();cb(data);};
  s.src=url+'&cb='+name;
  s.onerror=function(){delete window[name];s.remove();if(errCb)errCb('network');};
  document.body.appendChild(s);
  setTimeout(()=>{if(window[name]){delete window[name];s.remove();if(errCb)errCb('timeout');}},20000);
}

function detectMarket(code){
  code=code.replace(/\.(SZ|SH|BJ|sz|sh|bj)$/,'');
  const c=code[0];
  if(c==='6')return '1.'+code;      // SH
  if(c==='0'||c==='3')return '0.'+code; // SZ
  if(c==='8'||c==='4')return '0.'+code; // BJ
  return '0.'+code;
}

function fetchStock(inputCode){
  const raw_code=(inputCode||document.getElementById('inpCode').value).trim();
  const code=raw_code.replace(/\.(SZ|SH|BJ|sz|sh|bj)$/,'');
  if(!/^\d{6}$/.test(code)){toast('请输入6位数字股票代码（如 000001）','err');return;}
  if(RAW[code]){
    document.getElementById('selStock').value=code;
    document.getElementById('inpCode').value='';
    run();
    toast(`${RAW[code].name}(${code}) 已在标的池中`,'info');
    return;
  }
  const btn=document.getElementById('btnFetch');
  const orig=btn.innerHTML;
  btn.innerHTML='<span class="spinner"></span>获取中';
  btn.disabled=true;

  const secid=detectMarket(code);
  const url='https://push2his.eastmoney.com/api/qt/stock/kline/get?secid='+secid+
    '&ut=fa5fd1943c7b386f172d6893dbbd1d0c&fields1=f1,f2,f3,f4,f5,f6'+
    '&fields2=f51,f52,f53,f54,f55,f56,f57,f58&klt=101&fqt=1&beg=20240101&end=20261231';

  jsonp(url,function(data){
    btn.innerHTML=orig;btn.disabled=false;
    if(!data||!data.data||!data.data.klines||!data.data.klines.length){
      toast('未获取到 '+code+' 的数据，请检查代码是否正确','err');return;
    }
    const name=data.data.name||code;
    const klines=data.data.klines;
    const dates=[],open=[],high=[],low=[],close=[],volume=[];
    for(const kl of klines){
      const p=kl.split(',');
      if(p.length<6)continue;
      dates.push(p[0]);open.push(+p[1]);close.push(+p[2]);
      high.push(+p[3]);low.push(+p[4]);volume.push(+p[5]);
    }
    if(dates.length<30){toast(code+' 数据不足（仅'+dates.length+'条），无法回测','err');return;}
    RAW[code]={name,code,dates,open,high,low,close,volume};
    const sel=document.getElementById('selStock');
    const opt=document.createElement('option');
    opt.value=code;opt.textContent=name+' ('+code+')';
    sel.appendChild(opt);sel.value=code;
    document.getElementById('inpCode').value='';
    toast('已添加 '+name+'('+code+')，共 '+dates.length+' 个交易日','ok');
    updateChips();run();
  },function(errType){
    btn.innerHTML=orig;btn.disabled=false;
    toast('获取数据失败（'+errType+'），请检查网络后重试','err');
  });
}

function removeStock(){
  const sel=document.getElementById('selStock');
  const code=sel.value;
  if(!code)return;
  if(EMBEDDED.has(code)){toast('默认标的不可删除','warn');return;}
  const name=RAW[code].name;
  delete RAW[code];
  rebuildDropdown();
  updateChips();
  run();
  toast('已移除 '+name+'('+code+')','info');
}

function clearFetched(){
  let cnt=0;
  Object.keys(RAW).forEach(c=>{if(!EMBEDDED.has(c)){delete RAW[c];cnt++;}});
  if(cnt===0){toast('没有动态标的可清空','info');return;}
  rebuildDropdown();
  updateChips();
  run();
  toast('已清空 '+cnt+' 个动态标的','ok');
}

function rebuildDropdown(){
  const sel=document.getElementById('selStock');
  const cur=sel.value;
  sel.innerHTML='';
  Object.keys(RAW).forEach(code=>{
    const o=document.createElement('option');
    o.value=code;o.textContent=RAW[code].name+' ('+code+')';
    sel.appendChild(o);
  });
  if(RAW[cur])sel.value=cur;else if(Object.keys(RAW).length>0)sel.value=Object.keys(RAW)[0];
}

function updateChips(){
  const wrap=document.getElementById('quickAdd');
  wrap.innerHTML='<span class="lbl">快速添加：</span>';
  HOT.forEach(h=>{
    const span=document.createElement('span');
    if(RAW[h.code]){
      span.className='chip added';
      span.textContent=h.name+' '+h.code+' ✓';
    }else{
      span.className='chip';
      span.textContent=h.name+' '+h.code;
      span.onclick=()=>fetchStock(h.code);
    }
    wrap.appendChild(span);
  });
}

// ============ Toast ============
function toast(msg,type){
  const wrap=document.getElementById('toastWrap');
  const t=document.createElement('div');
  t.className='toast '+(type||'info');
  t.textContent=msg;
  wrap.appendChild(t);
  requestAnimationFrame(()=>t.classList.add('show'));
  setTimeout(()=>{t.classList.remove('show');setTimeout(()=>t.remove(),300);},3500);
}

// ============ 初始化 ============
function init(){
  rebuildDropdown();
  initCharts();
  updateChips();
  document.getElementById('advToggle').onclick=function(){document.getElementById('advPanel').classList.toggle('show');this.textContent=document.getElementById('advPanel').classList.contains('show')?'高级设置 ▴':'高级设置 ▾';};
  document.getElementById('btnRun').onclick=run;
  document.getElementById('btnFetch').onclick=()=>fetchStock();
  document.getElementById('btnRemove').onclick=removeStock;
  document.getElementById('btnClearFetched').onclick=clearFetched;
  document.getElementById('inpCode').addEventListener('keydown',e=>{if(e.key==='Enter')fetchStock();});
  document.getElementById('selStock').onchange=run;
  document.getElementById('selMa').onchange=run;
  ['inpFast','inpSlow','inpCapital','inpComm','inpSlip','inpRf'].forEach(id=>{document.getElementById(id).addEventListener('change',run);});
  run();
}
window.addEventListener('load',init);
</script>
</body>
</html>
"""

html_final = HTML.replace("__DATA__", data_json)
with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_final)
print(f"[OK] HTML 已生成: {OUT_HTML}")
print(f"     大小: {os.path.getsize(OUT_HTML)/1024:.1f} KB")
print(f"     默认标的数: {len(slim)}")
