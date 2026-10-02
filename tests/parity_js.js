const fs=require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..");

const html=fs.readFileSync(path.join(ROOT, "dashboard", "index.html"),"utf8");
const model=html.slice(html.indexOf("/* ---------- model ---------- */"),
                       html.indexOf("/* ---------- projection ---------- */"));
const D=JSON.parse(fs.readFileSync(path.join(__dirname, "synthetic.json"),"utf8"));
const S=JSON.parse(fs.readFileSync(path.join(__dirname, "sweep_py.json"),"utf8"));
const d0=new Date(D.dates[0]+"T00:00:00Z");
const dayIdx=D.dates.map(s=>Math.round((new Date(s+"T00:00:00Z")-d0)/86400000));
// Take the constants from the page itself. Hard-coding them here means the
// harness can silently drift from the model it is supposed to be checking.
const constLines = html.match(/^\s*var (LOW|MIN_PROM)\s*=.*$/gm);
if (!constLines || constLines.length < 2) { console.error("could not read the model constants from the page"); process.exit(2); }
const prelude = constLines.join("\n");
const runner=`
  var all={};
  CHECKS.forEach(function(ui){
    var row={};
    D.fields.forEach(function(f){
      var a=assess(f,ui);
      row[String(f.id)]={status:a.status,priority:a.priority,ndvi:a.ndvi,
                         since:a.since,cycle:a.cycle,expected:a.expected,deficit:a.deficit};
    });
    all[String(ui)]=row;
  });
  return all;`;
const out=new Function("D","dayIdx","CHECKS",prelude+model+runner)(D,dayIdx,S.checks);
let bad=0,tot=0;
const close=(a,b)=>(a===null&&b===null)||(a!==null&&b!==null&&Math.abs(a-b)<=1e-4);
for(const ui of S.checks){
  for(const k of Object.keys(S.py[ui])){
    const p=S.py[ui][k], j=out[ui][k];
    tot++;
    for(const f of ["status","priority","ndvi","since","cycle","expected","deficit"]){
      const ok = f==="status" ? p[f]===j[f] : close(p[f],j[f]);
      if(!ok){ bad++; if(bad<=12) console.log(`  date#${ui} field ${k} ${f}: py=${p[f]} js=${j[f]}`); break; }
    }
  }
}
console.log(`compared ${tot} field-dates across ${S.checks.length} scrubber positions`);
console.log(bad? `MISMATCHES: ${bad}` : "PARITY: identical everywhere.");
