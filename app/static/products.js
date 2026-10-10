const P={st:{parent:'TOTAL',path:[]},charts:[],ready:false,metric:'value',last:null,lastDetail:null,
async init(){if(this.ready)return;this.ready=true;let t;$('#psearch').oninput=e=>{clearTimeout(t);t=setTimeout(()=>this.search(e.target.value),300)};
 const h=hp();if(h.get('metric'))this.metric=$('#pmetric').value=h.get('metric')=='qty'?'qty':'value';
 if(h.get('path')){this.st.path=h.get('path').split(',').filter(c=>/^\d{2,4}$/.test(c));this.st.parent=this.st.path.at(-1)||'TOTAL'}this.load()},
q(){return `flow=${FLOW}&year=${YEAR}&partner=${PTN}`},
go(code){const p=[];if(code.length>=2)p.push(code.slice(0,2));if(code.length>=4)p.push(code.slice(0,4));this.st.path=p;this.st.parent=p.at(-1)||'TOTAL';this.load(code.length==6?code:null)},
async search(v){if(v.length<2){$('#presults').innerHTML='';return}const r=await(await fetch('/api/hs_search?q='+encodeURIComponent(v))).json();
 $('#presults').innerHTML=`<div class=card style="position:absolute;z-index:9;width:560px;max-height:300px;overflow:auto">${r.map(x=>`<div style="cursor:pointer;padding:3px" onclick="P.go('${x.code}');$('#presults').innerHTML=''"><b>${x.code}</b> ${x.name.replace(/^\d+ - /,'')}</div>`).join('')||'No match'}</div>`},
mv(r){return this.metric=='qty'?r.netWgt:r.value},
async load(sel){const s=this.st;setHash({path:s.path.join(','),metric:this.metric});
 $('#ptable').innerHTML=`Loading live Comtrade data for ${PNAME}… (first load of a level makes 4 API calls)`;
 try{const r=await fetch(`/api/prod?${this.q()}&parent=${s.parent}`);const j=await r.json();if(!r.ok)throw new Error(j.error);this.last=j;
  const pn=j.data.pathNames||{};$('#crumb').innerHTML=[`<a href="#" onclick="P.go('');return false">All products (HS2)</a>`,...s.path.map(c=>`<a href="#" onclick="P.go('${c}');return false"><b>${c}</b> ${(pn[c]||'').replace(/^\d+ - /,'').slice(0,60)}</a>`)].join(' › ')+` <span style="color:#666">· partner: <b>${PNAME}</b></span>`;
  this.render();const first=sel||(s.parent!='TOTAL'&&s.parent)||j.data.rows[0]?.code;if(first)this.detail(first)
 }catch(e){$('#ptable').innerHTML=`<p class=err>Comtrade preview could not serve this level: ${e.message}</p><p class=def>Needs Comtrade key (full data/v1 API), coming soon. No mirror fallback shown for this level.</p>`}},
render(){const j=this.last;if(!j)return;setHash({path:this.st.path.join(','),metric:this.metric});const d=j.data,s=this.st,f=v=>v==null?'–':(v>=0?'+':'')+v.toFixed(1)+'%';
 const rows=[...d.rows].sort((a,b)=>(this.mv(b)??-1)-(this.mv(a)??-1));const hs2=s.parent=='TOTAL';const anyQ=rows.some(r=>r.netWgt!=null);
 $('#ptable').innerHTML=`<h3><span style="background:#01411c;color:#fff;padding:1px 8px;border-radius:9px">${FL()}</span> ${hs2?'HS2 chapters':s.parent.length==2?'HS4 headings in chapter '+s.parent:'HS6 products in heading '+s.parent} · partner ${PNAME} · total ${FLOW=='X'?'exports':'imports'} ${fmt(d.total)} · sorted by ${this.metric=='qty'?'net weight':'value'}</h3>
 ${!anyQ?`<p class=def>⚠ Quantity: n/a at this level. The Comtrade preview returns no quantity or net weight for ${hs2?'HS2 chapters (they mix units)':'these codes'}. ${this.metric=='qty'?'Sorting falls back to the API order.':''}</p>`:''}
 <div style="max-height:620px;overflow:auto"><table><tr><th>HS code</th><th>Description</th><th>Value (US$)</th><th>Share</th><th>Δ value vs ${YEAR-1}</th><th>Quantity (unit)</th><th>Net weight (kg)</th><th>Unit value</th><th title="Exports FOB − imports CIF, same code & partner">Balance (X−M)</th><th></th></tr>
 ${rows.map(r=>`<tr style="cursor:pointer" onclick="P.detail('${r.code}')" data-code="${r.code}"><td><b>${r.code}</b></td><td>${r.name.replace(/^\d+ - /,'').slice(0,70)}</td><td>${fmt(r.value)}</td><td>${r.share==null?'–':r.share.toFixed(2)+'%'}</td><td style="color:${r.chg<0?'#b00':'#080'}">${f(r.chg)}</td>
 <td>${num(r.qty,r.qtyUnit)}${r.qtyEst?' <span title="Estimated by UN Comtrade">(est.)</span>':''}${r.altQty&&r.altQtyUnit&&r.altQtyUnit!=r.qtyUnit?'<br><small>alt: '+num(r.altQty,r.altQtyUnit)+'</small>':''}</td><td>${num(r.netWgt)}${r.netWgtEst?' (est.)':''}</td>
 <td>${r.unitValue?'$'+r.unitValue.toFixed(2)+'/'+r.qtyUnit:r.unitValueKg?'$'+r.unitValueKg.toFixed(2)+'/kg':'n/a'}</td><td style="color:${r.balance>=0?'#080':'#b00'}">${r.balance==null?`<span title="No ${FLOW=='X'?'imports':'exports'} reported for this code/partner, so no balance">n/a</span>`:fmt(r.balance)}</td>
 <td>${r.hasChildren?`<a href="#" onclick="event.stopPropagation();P.drill('${r.code}');return false">drill ›</a>`:''}</td></tr>`).join('')}</table></div>
 <p class=def>Quantity and unit come straight from Comtrade (qty, qtyUnitCode mapped through the QuantityUnits reference); "est." means estimated by UN Comtrade. Unit value = value ÷ quantity (or ÷ net kg). n/a = not reported, never imputed. Balance n/a = other flow not reported (never assumed 0).</p>${meta(j.meta)}`;
 if(this.lastDetail)this.drawDetail()},
drill(c){this.st.path.push(c);this.st.parent=c;this.load()},
async detail(code){const el=$('#pdetail');el.innerHTML=`<h3>${code}: loading partners & 5-year trend…</h3>`;
 try{const [p,t]=await Promise.all(['prod_partners','prod_trend'].map(async n=>{const r=await fetch(`/api/${n}?${this.q()}&code=${code}`);const j=await r.json();if(!r.ok)throw new Error(j.error);return j}));
  this.lastDetail={p,t,code};this.drawDetail()}catch(e){el.innerHTML=`<p class=err>Detail failed: ${e.message}</p><p class=def>Needs Comtrade key, coming soon.</p>`}},
drawDetail(){const {p,t,code}=this.lastDetail,el=$('#pdetail'),Q=this.metric=='qty';this.charts.forEach(c=>c.destroy());this.charts=[];
 const nm=(p.codeName||code).replace(/^\d+ - /,''),u=Q?'kg':'US$',fm=Q?v=>num(v,'kg'):fmt;
 const pd=[...p.data].sort((a,b)=>((Q?b.netWgt:b.value)??-1)-((Q?a.netWgt:a.value)??-1)),noQ=Q&&!pd.some(r=>r.netWgt!=null),tq=Q&&!t.data.some(r=>r[2]!=null);
 el.innerHTML=`<h3>Top partners for HS <b>${code}</b>: ${nm.slice(0,80)} <small>(${Q?'net weight kg':'value US$'}; all partners, world view)</small></h3>${noQ?'<p class=def>⚠ Quantity n/a for this code in the preview.</p>':'<canvas id=pc1></canvas>'}
 <table style="font-size:12px"><tr><th>Partner</th><th>HS code</th><th>Value (US$)</th><th>Share</th><th>Quantity</th><th>Net kg</th><th>Unit value</th></tr>${pd.map(r=>`<tr><td>${r.partner}</td><td>${code}</td><td>${fmt(r.value)}</td><td>${r.share?.toFixed(1)??'–'}%</td><td>${num(r.qty,r.qtyUnit)}</td><td>${num(r.netWgt)}</td><td>${r.unitValue?'$'+r.unitValue.toFixed(2)+'/'+r.qtyUnit:'n/a'}</td></tr>`).join('')}</table>${meta(p.meta)}
 <h3 style="margin-top:14px">Trend for HS <b>${code}</b>: ${nm.slice(0,60)} · partner ${PNAME} (${u})</h3>${tq?'<p class=def>⚠ Quantity n/a for this code across these years.</p>':'<canvas id=pc2></canvas>'}${meta(t.meta)}`;
 if(!noQ)this.charts.push(new Chart($('#pc1'),{type:'bar',data:{labels:pd.map(r=>r.partner),datasets:[{data:pd.map(r=>Q?r.netWgt:r.value),backgroundColor:'#01411c'}]},options:{indexAxis:'y',plugins:{legend:{display:false},tooltip:{callbacks:{label:x=>fm(x.raw)}}},scales:{x:{ticks:{callback:fm}}}}}));
 if(!tq)this.charts.push(new Chart($('#pc2'),{type:'line',data:{labels:t.data.map(r=>r[0]),datasets:[{label:u,data:t.data.map(r=>Q?r[2]:r[1]),borderColor:'#01411c',pointRadius:x=>t.data[x.dataIndex]?.[0]==YEAR?7:3,pointBackgroundColor:x=>t.data[x.dataIndex]?.[0]==YEAR?'#f0a000':'#01411c'}]},options:{plugins:{legend:{display:false}},scales:{y:{ticks:{callback:fm}}}}}));
 el.dataset.loaded=code}};
