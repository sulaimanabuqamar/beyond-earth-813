const fs=require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..");
 const {JSDOM}=require("jsdom");
const html=fs.readFileSync(path.join(ROOT, "dashboard", "index.html"),"utf8");

function visibleText(d){
  const walk=d.createTreeWalker(d.body, 5 /*SHOW_ELEMENT|SHOW_TEXT*/);
  let n, out=[];
  while((n=walk.nextNode())){
    if(n.nodeType===1 && /^(script|style)$/i.test(n.tagName)) { walk.currentNode = n; 
      // skip subtree
      let next=n.nextSibling; while(!next && n.parentNode){ n=n.parentNode; next=n.nextSibling; }
      if(next) walk.currentNode=next; continue; }
    if(n.nodeType===3) out.push(n.nodeValue);
  }
  return out.join(" ");
}

async function run(name, data, actions){
  const errors=[];
  const dom=new JSDOM(html,{runScripts:"dangerously",pretendToBeVisual:true,
    url:"https://example.invalid/d/index.html",
    beforeParse(w){
      w.fetch=()=>Promise.resolve({ok:true,status:200,json:()=>Promise.resolve(data)});
      // jsdom does not implement these two; every real browser does.
      w.Element.prototype.scrollIntoView = function(){};
      w.SVGElement.prototype.getBBox = w.SVGElement.prototype.getBBox || function(){ return {x:0,y:0,width:100,height:20}; };
      w.addEventListener("error",e=>errors.push("onerror: "+(e.error?e.error.stack:e.message)));
      w.addEventListener("unhandledrejection",e=>errors.push("reject: "+((e.reason&&e.reason.stack)||e.reason)));
      const ce=w.console.error.bind(w.console);
      w.console.error=(...a)=>{errors.push("console.error: "+a.join(" ")); ce(...a);};
    }});
  await new Promise(r=>setTimeout(r,2000));
  const d=dom.window.document;
  if(actions) { try { actions(dom.window, d); } catch(e){ errors.push("action: "+e.stack); } 
                await new Promise(r=>setTimeout(r,800)); }
  const t=visibleText(d);
  const res={
    errors: errors.length,
    polys: d.querySelectorAll("svg path[data-id]").length,
    rows: d.querySelectorAll("table tbody tr").length,
    undef: (t.match(/undefined/g)||[]).length,
    nan: (t.match(/NaN/g)||[]).length,
    objs: (t.match(/\[object /g)||[]).length,
    chars: t.length,
  };
  const ok = errors.length===0 && res.undef===0 && res.nan===0 && res.objs===0 && res.chars>500;
  console.log((ok?"  PASS  ":"  FAIL  ")+name.padEnd(42), JSON.stringify(res));
  if(errors.length) errors.slice(0,4).forEach(e=>console.log("        "+String(e).split("\n")[0]));
  dom.window.close();
  return ok;
}

(async ()=>{
  const base=JSON.parse(fs.readFileSync(path.join(__dirname, "synthetic.json"),"utf8"));
  const clone=()=>JSON.parse(JSON.stringify(base));
  let all=true;

  all &= await run("baseline, emit empty", base);

  // every field blank -> no_data everywhere
  let d1=clone(); Object.keys(d1.ndvi).forEach(k=>d1.ndvi[k]=d1.ndvi[k].map(()=>null));
  all &= await run("all NDVI null (no_data path)", d1);

  // one field only, two dates
  let d2=clone(); d2.fields=d2.fields.slice(0,1);
  const id=String(d2.fields[0].id);
  d2.ndvi={[id]: d2.ndvi[id].slice(0,2)}; d2.dates=d2.dates.slice(0,2);
  d2.meta.n_fields=1; d2.meta.n_days=2;
  all &= await run("1 field, 2 dates (degenerate)", d2);

  // emit rows present
  let d3=clone();
  d3.meta.emit_scenes=["2026-02-18","2026-07-22"];
  d3.meta.emit_granules=["EMIT_L2A_RFL_001_20260218T091142_2604906_005","EMIT_L2A_RFL_001_20260722T101501_2620307_011"];
  d3.emit=d3.fields.slice(0,20).flatMap(f=>d3.meta.emit_scenes.map(s=>({
    id:f.id,d:s,PRI:0.012,NDVI:0.41,NDWI:0.08,REP:721.4,D970:0.0731})));
  all &= await run("with hyperspectral rows", d3);

  // emit rows carrying nulls (real granules do this)
  let d4=JSON.parse(JSON.stringify(d3));
  d4.emit=d4.emit.map((r,i)=> i%3===0 ? {...r,PRI:null,REP:null,D970:null} : r);
  all &= await run("hyperspectral rows with nulls", d4);

  // scrubber dragged to the start
  all &= await run("scrubber moved to earliest date", base, (w,d)=>{
    const s=d.querySelector('input[type="range"]');
    if(!s) throw new Error("no range input found");
    s.value=s.min; s.dispatchEvent(new w.Event("input",{bubbles:true}));
  });

  // status filter chip clicked
  all &= await run("status chip clicked (filter)", base, (w,d)=>{
    const c=d.querySelectorAll(".chip");
    if(!c.length) throw new Error("no chips");
    c[2].dispatchEvent(new w.MouseEvent("click",{bubbles:true}));
  });

  // a field selected on the map
  all &= await run("field selected from map", base, (w,d)=>{
    const p=d.querySelector("svg path[data-id]");
    if(!p) throw new Error("no field path");
    p.dispatchEvent(new w.MouseEvent("click",{bubbles:true}));
  });

  console.log(all ? "\nALL CHECKS PASSED" : "\nSOME CHECKS FAILED");
  process.exit(all?0:1);
})();
