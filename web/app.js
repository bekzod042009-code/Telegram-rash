var L="ABCDEF",$=function(i){return document.getElementById(i)};
var tg=window.Telegram&&window.Telegram.WebApp,INIT=(tg&&tg.initData)||"";
var ME=null,CFG=null,SUBJ=[],me=null,role=null,pend=null,S,mk=[],printed=false,onCreate=true,fin=false;
var cur=null,sa=[],seq=0,timerId=null,deadline=0,sending=false,pickIdx=0,toastId=null;
var PN={t:["create","mine","acct"],s:["find","sec","bal","res"],a:["tests","earn","price","users"]};
var fmt=function(n){return Math.round(n).toLocaleString("ru-RU")};
function newS(){S={n:10,k:4,ans:[],w:[],acc:[],md:[],txt:[],img:[],opt:[]};mk=[]}newS();
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})}

/* ----- server bilan aloqa ----- */
async function api(method,url,body){
  var o={method:method,headers:{Authorization:"tma "+INIT,"X-Role":role||pend||""}},r,d=null;
  if(body instanceof Blob){o.headers["Content-Type"]="application/octet-stream";o.body=body}
  else if(body!==undefined){o.headers["Content-Type"]="application/json";o.body=JSON.stringify(body)}
  try{r=await fetch(url,o)}catch(e){throw new Error("Internet aloqasi yoʻq. Qayta urinib koʻring.")}
  try{d=await r.json()}catch(e){}
  if(!r.ok||d===null){var er=new Error(d&&typeof d.detail==="string"?d.detail:"Server xatosi. Qayta urinib koʻring.");er.status=r.status;throw er}
  return d;
}
function fail(e){toast(e.message,false)}
function setAcc(a){ME.accounts[a.role]=a;if(role===a.role)me=a;head()}
async function refresh(){
  ME=await api("GET","/api/me");CFG=ME.cfg;SUBJ=ME.subjects;
  if(role&&role!=="a")me=ME.accounts[role];head();updTexts();
}

/* ----- bildirishnoma ----- */
function toast(t,j,good){
  clearTimeout(toastId);$("tmsg").textContent=t;$("tj").classList.toggle("hide",!j);
  $("toast").classList.toggle("good",!!good);$("toast").classList.toggle("low",$("bar").classList.contains("hide"));
  $("toast").classList.add("show");if(!j)toastId=setTimeout(hideToast,5000);
}
function hideToast(){clearTimeout(toastId);$("toast").classList.remove("show")}

/* ----- Kirish / navigatsiya ----- */
function updTexts(){if(!CFG)return;$("sm_t").textContent="Test yarataman. Yangi oʻqituvchiga "+CFG.tw+" kredit sovgʻa";$("sm_s").textContent="Test qidiraman va yechaman. Roʻyxatdan oʻtganda "+CFG.sw+" kredit sovgʻa"}
function pickR(r){
  pend=r;
  if(ME.accounts[r]){role=r;me=ME.accounts[r];enter();return}
  $("r2t").textContent=r==="t"?"Test yaratuvchi":"Test yechuvchi";$("r1").classList.add("hide");$("r2").classList.remove("hide");
}
function backR(){$("r2").classList.add("hide");$("r1").classList.remove("hide");$("rerr").textContent=""}
async function login(){
  var f=$("fn").value.trim(),l=$("ln").value.trim();
  if(!f||!l){$("rerr").textContent="Ism va familiyani kiriting.";return}
  $("lb").disabled=true;
  try{var a=await api("POST","/api/register",{role:pend,first:f,last:l});role=pend;me=a;setAcc(a);enter()}
  catch(e){$("rerr").textContent=e.message}
  $("lb").disabled=false;
}
function admin(){me=null;role="a";enter()}
function enter(){
  var m={t:"T",s:"S",a:"A"};$("sRole").classList.add("hide");
  ["T","S","A"].forEach(function(x){$("s"+x).classList.toggle("hide",m[role]!==x)});
  if(role==="t"&&fin)again();
  pane(role,PN[role][0]);head();refresh().catch(fail);
}
function head(){
  $("hx").classList.toggle("hide",!role);
  $("hr").textContent=role==="a"?"Admin":!me?"":me.name+" · "+(role==="t"?me.cr+" kredit":me.cr+" kredit · "+fmt(me.bal)+" soʻm");
}
function logout(){
  hideAll();me=null;role=null;hideToast();["T","S","A"].forEach(function(x){$("s"+x).classList.add("hide")});
  $("sRole").classList.remove("hide");backR();head();barS();
}
function pane(r,p){
  PN[r].forEach(function(x){$("p_"+r+"_"+x).classList.toggle("hide",x!==p);$("tb_"+r+"_"+x).classList.toggle("on",x===p)});
  onCreate=(r==="t"&&p==="create");hideToast();barS();window.scrollTo(0,0);
  var f={mine:mineV,acct:acctV,sec:function(){return secV()},bal:balV,res:resV,tests:aTests,earn:aEarn,price:aPrice,users:aUsers}[p];
  if(f){var el=$("p_"+r+"_"+p);if(!el.innerHTML)el.innerHTML='<p class="lead">Yuklanmoqda…</p>';
    Promise.resolve(f()).catch(function(e){el.innerHTML='<p class="err">'+esc(e.message)+'</p>'})}
}
function barS(){$("bar").classList.toggle("hide",!(role==="t"&&onCreate&&!fin))}

/* ----- Oqituvchi: yaratish ----- */
function mode(m){
  printed=!!m;$("mO").classList.toggle("on",!m);$("mB").classList.toggle("on",!!m);
  $("ft").textContent=m?"Bosma test varaqasi":"Oddiy test";
  $("fl").textContent=m?"Test qogʻozda tarqatiladi. Faqat oʻz oʻquvchilaringiz uchun. Savollar sonini va toʻgʻri javoblarni kiriting.":"Har bir savol uchun matn yozing yoki rasm qoʻshing va toʻgʻri javobni belgilang.";
  $("turBox").classList.toggle("hide",!!m);if(m)$("tur").value="o";
  updTur();mk=[];hideToast();render();
}
function updTur(){$("payBox").classList.toggle("hide",!($("tur").value==="p"&&!printed))}
function updPay(){var c=$("pay").value==="c";$("nl").textContent=c?"Narx (kredit)":"Narx (soʻm)";$("narx").value=c?10:10000}
/* Massivlar qisqartirilmaydi: son maydonida yozayotganda kiritilganlar oʻchib ketmasin. */
function sync(){
  var n=Math.max(1,Math.min(100,parseInt($("soni").value)||1));S.n=n;S.k=parseInt($("var").value);
  while(S.ans.length<n){S.ans.push(null);S.w.push(false);S.acc.push([]);S.md.push("key");S.txt.push("");S.img.push(null);S.opt.push(["","","","","",""])}
  S.ans=S.ans.map(function(a){return a!==null&&L.indexOf(a)>=S.k?null:a});
}
function ansOk(i){return S.w[i]?S.acc[i].length>0:S.ans[i]!==null}
function optsOk(i){for(var j=0;j<S.k;j++)if(!S.opt[i][j].trim())return false;return true}
/* Rasmli savolda variantlar rasm ichida boʻlishi mumkin, shuning uchun ularning matni shart emas. */
function rowOk(i){return ansOk(i)&&(printed||(!!S.img[i]||S.txt[i].trim()!=="")&&(S.w[i]||!!S.img[i]||optsOk(i)))}
function bubble(i,j){return '<button type="button" class="b'+(S.ans[i]===L[j]?' on':'')+'" aria-label="'+(i+1)+'-savol '+L[j]+' toʻgʻri javob" onclick="pick('+i+','+j+')">'+L[j]+'</button>'}
function optRows(i){
  var h='<div class="opts">';
  for(var j=0;j<S.k;j++)h+='<div class="opt">'+bubble(i,j)+'<textarea rows="1" maxlength="500" placeholder="'+L[j]+' variant matni" aria-label="'+(i+1)+'-savol '+L[j]+' variant matni" oninput="S.opt['+i+']['+j+']=this.value;grow(this);chk('+i+')">'+esc(S.opt[i][j])+'</textarea></div>';
  return h+'</div>';
}
function grow(el){el.style.height="auto";el.style.height=(el.scrollHeight+2)+"px"}
var ICON='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="8.5" cy="9.5" r="1.6"/><path d="M4 18l5-5 4 4 3-3 4 4"/></svg>';
function imgBox(i){
  var m=S.img[i];
  if(!m)return '<button type="button" class="addimg" onclick="pickImg('+i+')">'+ICON+'Rasm qoʻshish</button>';
  if(m.busy)return '<div class="pic busy"><img src="'+m.url+'" alt=""><small>Rasm yuklanmoqda…</small></div>';
  return '<div class="pic"><img src="'+m.url+'" alt="'+(i+1)+'-savol rasmi" onclick="zoom(this.src)"><button type="button" class="lnk" onclick="pickImg('+i+')">Almashtirish</button><button type="button" class="lnk" onclick="delImg('+i+')">Olib tashlash</button></div>';
}
function drawImg(i){var el=$("im"+i);if(el)el.innerHTML=imgBox(i);chk(i)}
function pickImg(i){pickIdx=i;$("file").value="";$("file").click()}
function dropImg(m){if(m&&m.id)api("DELETE","/api/images/"+m.id).catch(function(){})}
function delImg(i){dropImg(S.img[i]);S.img[i]=null;drawImg(i)}
/* Telefonda rasm kichraytirib yuboriladi. */
function shrink(file){
  return new Promise(function(ok,no){
    var url=URL.createObjectURL(file),im=new Image();
    im.onload=function(){
      var k=Math.min(1,1600/Math.max(im.naturalWidth,im.naturalHeight)),c=document.createElement("canvas");
      c.width=Math.max(1,Math.round(im.naturalWidth*k));c.height=Math.max(1,Math.round(im.naturalHeight*k));
      var x=c.getContext("2d");x.fillStyle="#fff";x.fillRect(0,0,c.width,c.height);x.drawImage(im,0,0,c.width,c.height);
      URL.revokeObjectURL(url);
      c.toBlob(function(b){b?ok(b):no(new Error("Rasm oʻqilmadi."))},"image/jpeg",0.88);
    };
    im.onerror=function(){URL.revokeObjectURL(url);no(new Error("Rasm oʻqilmadi. JPG yoki PNG tanlang."))};
    im.src=url;
  });
}
async function onFile(){
  var file=$("file").files[0],i=pickIdx,draft=S;if(!file)return;
  var old=S.img[i],m={busy:true,url:URL.createObjectURL(file)};S.img[i]=m;drawImg(i);
  try{
    var blob=await shrink(file),d=await api("POST","/api/images",blob);
    m.id=d.id;m.busy=false;m.url="/img/"+d.id;
    if(draft!==S||S.img[i]!==m){dropImg(m);return}
    dropImg(old);drawImg(i);
  }catch(e){
    if(draft===S&&S.img[i]===m){S.img[i]=old;drawImg(i)}
    fail(e);
  }
}
function render(fi){
  sync();var h="",i,j;
  for(i=0;i<S.n;i++){
    h+='<div class="row'+(mk.indexOf(i)>-1&&!rowOk(i)?' miss':'')+'" id="r'+i+'">';
    if(!printed)h+='<div class="q"><textarea maxlength="2000" placeholder="'+(i+1)+'-savol matni" oninput="S.txt['+i+']=this.value;chk('+i+')">'+esc(S.txt[i])+'</textarea><div id="im'+i+'">'+imgBox(i)+'</div></div>';
    h+='<div class="rl"><span class="num">'+(i+1)+'</span><div class="bub">';
    if(S.w[i])h+='<span class="hint">Yozma javob</span>';
    else if(printed)for(j=0;j<S.k;j++)h+=bubble(i,j);
    else h+='<span class="hint">Toʻgʻri variant harfini bosing</span>';
    h+='</div><button class="wr'+(S.w[i]?' on':'')+'" onclick="tw('+i+')">Yozma</button></div>';
    if(!S.w[i]&&!printed)h+=optRows(i);
    if(S.w[i]){
      h+='<div class="wbox"><div class="chips" id="ch'+i+'">'+chips(i)+'</div>';
      h+='<input id="in'+i+'" maxlength="200" placeholder="Javob yozing va Enter bosing" onkeydown="if(event.key===\'Enter\'||event.key===\',\'){event.preventDefault();add('+i+')}" onblur="add('+i+',1)">';
      h+='<small>Bir nechta variant qoʻshing: Alisher Navoiy, Navoiy.</small><select onchange="S.md['+i+']=this.value">';
      [["key","Kalit soʻz"],["exact","Aniq"],["fuzzy","Imloga bardoshli"]].forEach(function(o){h+='<option value="'+o[0]+'"'+(S.md[i]===o[0]?' selected':'')+'>'+o[1]+'</option>'});
      h+='</select></div>';
    }
    h+='</div>';
  }
  $("rows").innerHTML=h;prog();Array.prototype.forEach.call(document.querySelectorAll("#rows .opt textarea"),function(el){if(el.value)grow(el)});if(fi!==undefined&&$("in"+fi))$("in"+fi).focus();
}
function chips(i){return S.acc[i].map(function(a,k){return '<span class="chip">'+esc(a)+'<button aria-label="Olib tashlash" onclick="rm('+i+','+k+')">×</button></span>'}).join("")}
/* Faqat shu qator yangilanadi: toʻliq qayta chizish keyingi bosishni yoʻqotib qoʻyadi. */
function drawChips(i){$("ch"+i).innerHTML=chips(i);chk(i)}
function chk(i){fix();var r=$("r"+i);if(r)r.classList.toggle("miss",mk.indexOf(i)>-1&&!rowOk(i));prog()}
function pick(i,j){S.ans[i]=L[j];fix();render()}
function tw(i){S.w[i]=!S.w[i];fix();render(S.w[i]?i:undefined)}
function add(i,b){var el=$("in"+i);if(!el)return;var v=el.value.trim().replace(/,$/,"");if(!v)return;el.value="";
  if(!/[a-z0-9Ѐ-ӿ]/i.test(v)){toast("Javobda harf yoki raqam boʻlishi kerak.",false);return}
  if(S.acc[i].length>=20)return;S.acc[i].push(v);drawChips(i);if(!b)el.focus()}
function rm(i,k){S.acc[i].splice(k,1);drawChips(i)}
function prog(){var d=0;for(var i=0;i<S.n;i++)if(rowOk(i))d++;var p=Math.round(d/S.n*100);
  $("pt").textContent=d+" / "+S.n+" toʻldirildi";$("pp").textContent=p+"%";$("pf").style.width=p+"%"}
function fix(){if(!mk.length)return;mk=mk.filter(function(i){return i<S.n&&!rowOk(i)});if(mk.length)showMiss();else hideToast()}
function showMiss(){var m=mk.map(function(i){return i+1});
  toast(m.length+" ta savolda "+(printed?"javob belgilanmagan":"javob, matn yoki variant yetishmaydi")+": "+m.slice(0,6).join(", ")+(m.length>6?" …":""),true)}
function jump(){if(mk.length)$("r"+mk[0]).scrollIntoView({behavior:"smooth",block:"center"})}
async function upload(){
  sync();mk=[];var i,q=[];for(i=0;i<S.n;i++)if(!rowOk(i))mk.push(i);
  if(mk.length){render();showMiss();jump();return}
  if(!printed)for(i=0;i<S.n;i++)if(S.img[i]&&S.img[i].busy){toast("Rasm hali yuklanyapti, biroz kuting.",false);return}
  if(me.cr<CFG.tc){toast("Kredit yetarli emas. Hisob boʻlimida kredit paketini sotib oling.",false);return}
  var pub=$("tur").value==="p"&&!printed,subj=$("subj").value;
  for(i=0;i<S.n;i++)q.push({t:printed?"":S.txt[i].trim(),img:!printed&&S.img[i]?S.img[i].id:null,w:S.w[i],a:S.w[i]?null:S.ans[i],acc:S.w[i]?S.acc[i]:[],md:S.md[i],opts:!printed&&!S.w[i]?S.opt[i].slice(0,S.k):[]});
  $("ub").disabled=true;
  try{
    var d=await api("POST","/api/tests",{title:$("nom").value,min:Math.max(1,Math.min(600,parseInt($("vaqt").value)||30)),k:S.k,printed:printed,pub:pub,
      open:$("kir").value==="Ochiq",subj:pub?subj:"",pay:$("pay").value,price:pub?Math.max(0,parseInt($("narx").value)||0):0,questions:q});
    setAcc(d.account);fin=true;newS();
    $("kod").textContent=d.code;$("dl").textContent=d.cost+" kredit yechildi, qoldi: "+d.account.cr+". "+(pub?"Test "+subj+" boʻlimiga qoʻshildi.":"Oʻquvchilarga shu kodni bering.");
    $("form").classList.add("hide");$("done").classList.remove("hide");barS();hideToast();window.scrollTo(0,0);
  }catch(e){fail(e)}
  $("ub").disabled=false;
}
function copyText(t){try{navigator.clipboard.writeText(t)}catch(e){}}
function copyCode(){copyText($("kod").textContent);$("cp").textContent="Nusxalandi";setTimeout(function(){$("cp").textContent="Kodni nusxalash"},1500)}
function again(){newS();fin=false;$("nom").value="";$("soni").value=10;$("done").classList.add("hide");$("form").classList.remove("hide");mode(printed?1:0);barS()}
async function toStudent(){
  var c=$("kod").textContent;
  try{
    if(!ME.accounts.s){var p=me.name.split(" ");setAcc(await api("POST","/api/register",{role:"s",first:p[0],last:p.slice(1).join(" ")}))}
    role="s";me=ME.accounts.s;enter();$("kodin").value=c;showT(c);
  }catch(e){fail(e)}
}

/* ----- umumiy: paketlar, arizalar, kartalar ----- */
function payNote(){return '<small style="margin-top:8px">Tanlasangiz adminga ariza ketadi, toʻlov tasdiqlangach hisobga tushadi.'+(ME.payment_info?'<br>'+esc(ME.payment_info):'')+'</small>'}
function pkB(){return '<div class="pk">'+CFG.pk.map(function(p){return '<button class="cta alt" onclick="ask(\'pack\','+p.c+')">+'+p.c+' kredit<small>'+fmt(p.p)+' soʻm</small></button>'}).join("")+'</div>'+payNote()}
async function ask(type,v){
  try{
    var d=await api("POST","/api/requests",{type:type,amount:type==="topup"?v:0,credits:type==="pack"?v:0});
    setAcc(d.account);await (role==="t"?acctV():balV());toast("Ariza yuborildi. 1 soat ichida javob olasiz.",false,true);
  }catch(e){fail(e)}
}
function reqName(r){return r.type==="pack"?r.credits+" kredit · "+fmt(r.amount)+" soʻm":(r.type==="topup"?"Balans toʻldirish: ":"Pul yechish: ")+fmt(r.amount)+" soʻm"}
function reqList(a){
  if(!a.length)return '<p class="lead">Ariza yoʻq.</p>';
  return a.map(function(r){return '<div class="card"><b>'+reqName(r)+'</b><small>'+{new:"Kutilmoqda · 1 soat ichida javob olasiz",done:"Tasdiqlandi",rejected:"Rad etildi"}[r.status]+'</small></div>'}).join("");
}
function st(t){return t.votes?"★ "+t.rating.toFixed(1)+" ("+t.votes+")":"Baholanmagan"}
function ptx(t){return t.pay==="c"?t.price+" kredit":fmt(t.price)+" soʻm"}
function cardL(a){return a.map(function(t){return '<div class="card click" data-c="'+t.code+'" onclick="go(this.dataset.c)"><b>'+esc(t.title)+'</b><small>'+esc(t.subj)+' · '+t.n+' savol · '+t.code+'</small><small>'+st(t)+' · '+(t.price?ptx(t):"Tekin")+'</small></div>'}).join("")}
function go(c){pane("s","find");$("kodin").value=c;showT(c)}

/* ----- Oqituvchi: testlar, hisob ----- */
async function mineV(){
  var a=await api("GET","/api/my/tests"),h='<h1>Testlarim</h1>';
  if(!a.length)h+='<p class="lead">Hali test yaratilmagan.</p>';
  a.forEach(function(t){h+='<div class="card"><b>'+esc(t.title)+'</b><small>'+t.code+' · '+(t.printed?'Bosma':'Oddiy')+' · '+t.n+' savol · '+(t.open?'Ochiq':'Yopiq')+'</small><small>'+(t.pub?esc(t.subj)+' · '+(t.price?ptx(t):'Tekin')+' · sotilgan: '+t.sold+' · '+st(t):'Oʻz oʻquvchilari uchun')+'</small>'
    +'<button class="lnk" data-c="'+t.code+'" onclick="resT(this.dataset.c).catch(fail)">Natijalar ('+t.attempts+')</button><button class="lnk" data-c="'+t.code+'" onclick="copyText(this.dataset.c);this.textContent=\'Nusxalandi\'">Kodni nusxalash</button><button class="lnk" data-c="'+t.code+'" onclick="setOpen(this.dataset.c,'+!t.open+')">'+(t.open?'Yopish':'Ochish')+'</button></div>'});
  $("p_t_mine").innerHTML=h;
}
async function resT(c){
  var d=await api("GET","/api/my/tests/"+c+"/attempts");
  var h='<button class="lnk" onclick="mineV().catch(fail)">← Testlarim</button><h1>'+esc(d.title)+'</h1><p class="lead">'+(d.items.length?'Javoblarni koʻrish uchun oʻquvchini tanlang.':'Hali hech kim yechmagan.')+'</p>';
  d.items.forEach(function(a){h+='<div class="card click" onclick="attV('+a.id+').catch(fail)"><b>'+esc(a.name)+'</b><small>'+a.ok+' / '+a.n+' · '+Math.round(a.ok/a.n*100)+'% · '+new Date(a.at).toLocaleString("ru-RU",{day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"})+'</small>'+(a.check?'<small class="tbad">Tekshirib koʻring: '+a.check+' ta yozma javob xato deb olingan</small>':'')+'</div>'});
  $("p_t_mine").innerHTML=h;window.scrollTo(0,0);
}
function attHtml(d){
  return '<button class="lnk" data-c="'+d.code+'" onclick="resT(this.dataset.c).catch(fail)">← Natijalar</button><h1>'+esc(d.name)+'</h1><p class="lead">'+esc(d.title)+' · '+d.ok+' / '+d.n+' toʻgʻri</p><div class="panel">'+reviewRows(d.review,d.k,d.id)+'</div>';
}
async function attV(id){
  var d=await api("GET","/api/my/attempts/"+id);$("p_t_mine").innerHTML=attHtml(d);window.scrollTo(0,0);
}
async function mark(id,i,ok,btn){
  btn.disabled=true;
  try{var d=await api("POST","/api/my/attempts/"+id+"/mark",{index:i,ok:ok});var y=window.scrollY;$("p_t_mine").innerHTML=attHtml(d);window.scrollTo(0,y)}
  catch(e){btn.disabled=false;fail(e)}
}
async function setOpen(c,v){try{await api("POST","/api/my/tests/"+c+"/open",{open:v});await mineV()}catch(e){fail(e)}}
async function acctV(){
  var d=await api("GET","/api/requests");setAcc(d.account);
  var h='<h1>Hisob</h1><div class="card"><b>Kredit: '+me.cr+'</b><small>ID: '+me.tg_id+' · har bir test '+CFG.tc+' kredit</small>'+pkB()+'</div>';
  h+='<div class="card"><b>Daromad: '+fmt(me.earn)+' soʻm + '+me.ecr+' kredit</b><small>Pullik test sotuvining '+CFG.com+' foizi sizniki.</small><div style="height:10px"></div><button class="cta" onclick="ask(\'withdraw\',0)"'+(me.earn>0?'':' disabled')+'>Pul yechish arizasi</button><small style="margin-top:8px">Admin arizani tekshirib, toʻlovni qoʻlda amalga oshiradi.</small></div><h2>Arizalar</h2>';
  $("p_t_acct").innerHTML=h+reqList(d.items);
}

/* ----- Oquvchi ----- */
function stopTimer(){clearInterval(timerId);timerId=null}
function hideAll(){seq++;stopTimer();["buy","sTest","sRes"].forEach(function(x){$(x).classList.add("hide")});$("serr").textContent="";$("sres").innerHTML=""}
function err(t){$("serr").textContent=t}
async function findQ(){
  var q=$("kodin").value.trim(),m=q.match(/^rash\s*-?\s*(\d{6})$/i);
  if(m){showT("RASH-"+m[1]);return}
  hideAll();var my=seq;if(!q){err("Kod yoki fan nomini kiriting.");return}
  try{
    var a=await api("GET","/api/search?q="+encodeURIComponent(q));if(my!==seq)return;
    if(!a.length){err("Hech narsa topilmadi. Boshqa soʻz yozing yoki Boʻlimlar sahifasini oching.");return}
    $("sres").innerHTML='<p class="lead">Eng yuqori baholangan testlar birinchi:</p>'+cardL(a);
  }catch(e){if(my===seq)err(e.message)}
}
async function showT(c){
  hideAll();var my=seq;
  try{var t=await api("GET","/api/tests/"+encodeURIComponent(c));if(my!==seq)return;cur=t;buyCard()}
  catch(e){if(my===seq)err(e.message)}
}
function buyCard(){
  var need=cur.need_buy;
  $("buy").innerHTML='<b>'+esc(cur.title)+'</b><small>'+(cur.subj?esc(cur.subj)+' · ':'')+cur.n+' savol · '+cur.min+' daqiqa · '+st(cur)+'</small>'+(need?'<small>Narxi: '+ptx(cur)+'</small>':'')
    +'<div style="height:10px"></div><button class="cta" id="bb" onclick="'+(need?'buy()':'startT()')+'">'+(need?(cur.pay==="c"?"Kredit bilan olish":"Balansdan sotib olish"):"Testni boshlash")+'</button>';
  $("buy").classList.remove("hide");
}
async function buy(){
  var my=seq;$("bb").disabled=true;err("");
  try{var d=await api("POST","/api/tests/"+cur.code+"/buy");setAcc(d.account);if(my!==seq)return;cur.need_buy=false;buyCard()}
  catch(e){if(my===seq){err(e.message);$("bb").disabled=false}}
}
async function startT(){
  var my=seq;$("bb").disabled=true;err("");
  try{var d=await api("POST","/api/tests/"+cur.code+"/start");if(my!==seq)return;cur=d;openT()}
  catch(e){if(my===seq){err(e.message);$("bb").disabled=false}}
}
function qHead(q,i){return (q.t?'<div class="qt">'+esc(q.t)+'</div>':'')+(q.img?'<img class="qimg" src="/img/'+q.img+'" alt="'+(i+1)+'-savol rasmi" onclick="zoom(this.src)">':'')}
function hasOpts(q){return !!q.opts&&q.opts.some(function(o){return o})}
function openT(){
  sa=cur.questions.map(function(){return null});
  $("sTitle").textContent=cur.title+" · "+cur.n+" ta savol, "+cur.min+" daqiqa";var h="";
  cur.questions.forEach(function(q,i){
    h+='<div class="row">'+qHead(q,i)+'<div class="rl'+(!q.w&&hasOpts(q)?' top':'')+'"><span class="num">'+(i+1)+'</span>';
    if(!q.w&&hasOpts(q)){h+='<div class="opts flat">';for(var o=0;o<cur.k;o++)h+='<button class="optb" id="s'+i+'_'+o+'" aria-pressed="false" onclick="sp('+i+','+o+')"><span class="b">'+L[o]+'</span><span>'+esc(q.opts[o])+'</span></button>';h+='</div>'}
    else if(q.w)h+='<input maxlength="500" placeholder="Javobingizni yozing" oninput="sa['+i+']=this.value">';
    else{h+='<div class="bub">';for(var j=0;j<cur.k;j++)h+='<button class="b" id="s'+i+'_'+j+'" aria-label="'+(i+1)+'-savol '+L[j]+'" onclick="sp('+i+','+j+')">'+L[j]+'</button>';h+='</div>'}
    h+='</div></div>';
  });
  $("sRows").innerHTML=h;$("buy").classList.add("hide");$("sRes").classList.add("hide");$("sTest").classList.remove("hide");
  sending=false;$("sb").disabled=false;deadline=Date.now()+cur.left*1000;stopTimer();timerId=setInterval(tick,500);tick();
}
function tick(){
  var s=Math.max(0,Math.ceil((deadline-Date.now())/1000));
  $("timer").textContent="Qolgan vaqt: "+Math.floor(s/60)+":"+("0"+s%60).slice(-2);
  if(!s){stopTimer();submitS()}
}
function sp(i,j){sa[i]=L[j];for(var x=0;x<cur.k;x++){var el=$("s"+i+"_"+x);el.classList.toggle("on",x===j);el.setAttribute("aria-pressed",x===j)}}
async function submitS(){
  if(sending)return;sending=true;$("sb").disabled=true;var my=seq;
  try{var d=await api("POST","/api/attempts/"+cur.attempt+"/submit",{answers:sa});if(my===seq){stopTimer();showRes(d)}}
  catch(e){
    if(my===seq){
      if(e.status===409||e.status===410){hideAll();err(e.message)}else fail(e);
    }
  }
  sending=false;$("sb").disabled=false;
}
/* Natija qatorlari: oʻquvchi ham, oʻqituvchi ham koʻradi. attempt berilsa tuzatish tugmalari chiqadi. */
function reviewRows(list,k,attempt){
  return list.map(function(q,i){
    var r=q.ok,j,full=!q.w&&hasOpts(q),mark=function(j){return L[j]===q.a?'ok':L[j]===q.my?'bad':''};
    var h='<div class="row">'+qHead(q,i)+'<div class="rl'+(full?' top':'')+'"><span class="num" style="color:var(--'+(r?'green':'red')+')">'+(i+1)+'</span>';
    if(q.w){
      h+='<div style="flex:1"><div class="'+(r?'okt':'tbad')+'">'+esc(q.my||"Javob yozilmagan")+'</div>'+(q.auto?'':'<div class="okt">Toʻgʻri javob: '+esc(q.acc.join(", "))+'</div>')+(q.manual?'<small class="hint">Oʻqituvchi toʻgʻri deb hisobladi</small>':'');
      if(attempt&&!q.auto&&q.my&&q.my.trim())h+='<button class="cta alt mark" onclick="mark('+attempt+','+i+','+!q.manual+',this)">'+(q.manual?'Bekor qilish (xato)':'Toʻgʻri deb hisoblash')+'</button>';
      h+='</div>';
    }else if(full){
      h+='<div class="opts flat">';
      for(j=0;j<k;j++)h+='<div class="optv"><span class="b '+mark(j)+'">'+L[j]+'</span><span class="'+(L[j]===q.a?'okt':L[j]===q.my?'tbad':'')+'">'+esc(q.opts[j])+'</span></div>';
      h+=(q.my==null?'<span class="tbad" style="font-size:13px">belgilanmagan</span>':'')+'</div>';
    }else{
      h+='<div class="bub">';for(j=0;j<k;j++)h+='<span class="b '+mark(j)+'">'+L[j]+'</span>';
      h+='</div>'+(q.my==null?'<span class="tbad" style="font-size:13px">belgilanmagan</span>':'');
    }
    return h+'</div></div>';
  }).join("");
}
function showRes(d){
  var h=reviewRows(d.review,d.k);
  $("sScore").textContent=d.ok+" / "+d.n;$("sPct").textContent=Math.round(d.ok/d.n*100)+"% toʻgʻri";$("sRv").innerHTML=h;
  $("rateBox").classList.toggle("hide",!d.can_rate);stars(d.my_rating);
  $("rtxt").textContent=d.my_rating?"Bahoyingiz: "+d.my_rating+" / 5":"Yulduzchani bosing, 5 tadan eng yuqorisi.";
  $("sTest").classList.add("hide");$("sRes").classList.remove("hide");window.scrollTo(0,0);
}
function stars(r){$("stars").innerHTML=[1,2,3,4,5].map(function(n){return '<button class="star'+(n<=r?' on':'')+'" aria-label="'+n+' yulduz" onclick="rate('+n+')">★</button>'}).join("")}
async function rate(n){
  try{await api("POST","/api/tests/"+cur.code+"/rate",{stars:n});stars(n);$("rtxt").textContent="Bahoyingiz: "+n+" / 5. Rahmat!"}catch(e){fail(e)}
}
async function secV(i){
  var h;
  if(i===undefined){
    var c=await api("GET","/api/sections");
    h='<h1>Boʻlimlar</h1><p class="lead">Fanni tanlang, shu fandagi pullik testlar chiqadi.</p><div class="sg">'+SUBJ.map(function(x,k){
      return '<button onclick="secV('+k+').catch(fail)">'+x+'<small>'+(c[x]||0)+' ta test</small></button>'}).join("")+'</div>';
  }else{
    var a=await api("GET","/api/section?subj="+encodeURIComponent(SUBJ[i]));
    h='<button class="lnk" onclick="secV().catch(fail)">← Barcha boʻlimlar</button><h1>'+SUBJ[i]+'</h1>'+(a.length?cardL(a):'<p class="lead">Bu boʻlimda hozircha test yoʻq.</p>');
  }
  $("p_s_sec").innerHTML=h;
}
function refLink(){return "https://t.me/"+ME.bot+"?start=ref"+ME.tg_id}
function share(){var u="https://t.me/share/url?url="+encodeURIComponent(refLink());if(tg&&tg.openTelegramLink)tg.openTelegramLink(u);else window.open(u)}
async function balV(){
  var d=await api("GET","/api/requests");setAcc(d.account);
  $("p_s_bal").innerHTML='<h1>Balans</h1><div class="card"><div class="big">'+fmt(me.bal)+' soʻm</div><small>ID: '+me.tg_id+'</small><div class="pk">'
   +[10000,50000,100000,200000].map(function(n){return '<button class="cta alt" onclick="ask(\'topup\','+n+')">+'+fmt(n)+'</button>'}).join("")+'</div>'+payNote()+'</div>'
   +'<div class="card"><b>Kredit: '+me.cr+'</b><small>Kreditli testlarni olish uchun. Yangi foydalanuvchiga '+CFG.sw+' kredit beriladi.</small>'+pkB()+'</div>'
   +(ME.bot?'<div class="card"><b>Doʻstni taklif qiling: +'+CFG.ref+' kredit</b><small>'+esc(refLink())+'</small><button class="cta alt" onclick="share()">Havolani ulashish</button></div>':'')
   +'<h2>Arizalar</h2>'+reqList(d.items);
}
async function resV(){
  var a=await api("GET","/api/results"),h='<h1>Natijalar</h1>';if(!a.length)h+='<p class="lead">Hali test yechilmagan.</p>';
  a.forEach(function(r){h+='<div class="card"><b>'+esc(r.title)+'</b><small>'+r.code+'</small><small>'+r.ok+' / '+r.n+' · '+Math.round(r.ok/r.n*100)+'%</small></div>'});
  $("p_s_res").innerHTML=h;
}

/* ----- Admin ----- */
async function aTests(){
  var a=await api("GET","/api/admin/tests"),h='<h1>Barcha testlar</h1><p class="lead">Admin sifatida hammasi bepul koʻrinadi, javoblar ham.</p>';
  if(!a.length)h+='<p class="lead">Hali test yoʻq.</p>';
  a.forEach(function(t){
    h+='<div class="card"><b>'+esc(t.title)+'</b><small>'+t.code+' · '+esc(t.owner)+' · '+(t.pub?esc(t.subj)+' · '+ptx(t)+' · sotilgan '+t.sold+' · '+st(t):(t.printed?'Bosma, oʻz oʻquvchilari':'Oddiy, oʻz oʻquvchilari'))+'</small><small class="okt">Javoblar: '
     +t.key.map(function(q,i){return(i+1)+"-"+(q.w?"["+esc(q.acc.join("/"))+"]":q.a)}).join("  ")+'</small>'
     +t.key.map(function(q,i){return q.img?'<button class="lnk" data-s="/img/'+q.img+'" onclick="zoom(this.dataset.s)">'+(i+1)+'-rasm</button>':''}).join("")+'</div>'});
  $("p_a_tests").innerHTML=h;
}
async function aEarn(){
  var d=await api("GET","/api/admin/earn"),s=0,c=0,h='<h1>Arizalar</h1>';
  if(!d.requests.length)h+='<p class="lead">Kutilayotgan ariza yoʻq.</p>';
  d.requests.forEach(function(r){h+='<div class="card"><b>'+reqName(r)+'</b><small>'+esc(r.name)+' · '+(r.role==="t"?"Oʻqituvchi":"Oʻquvchi")+' · ID '+r.tg_id+'</small><div class="pk"><button class="cta" onclick="decide('+r.id+',true,this)">Tasdiqlash</button><button class="cta alt" onclick="decide('+r.id+',false,this)">Rad etish</button></div></div>'});
  d.teachers.forEach(function(u){s+=u.earn;c+=u.ecr});
  h+='<h2>Oʻqituvchilar daromadi</h2><div class="card"><div class="big">'+fmt(s)+' soʻm</div><small>+ '+c+' kredit · ularning ulushi '+CFG.com+'%</small></div>';
  d.teachers.forEach(function(u){h+='<div class="card"><b>'+esc(u.name)+'</b><small>ID '+u.tg_id+' · testlar: '+u.tests+' · sotuv: '+u.sales+'</small><small>Daromad: '+fmt(u.earn)+' soʻm + '+u.ecr+' kredit</small></div>'});
  $("p_a_earn").innerHTML=h;
}
async function decide(id,ok,btn){
  btn.disabled=true;
  try{await api("POST","/api/admin/requests/"+id,{approve:ok})}catch(e){fail(e)}
  aEarn().catch(fail);
}
function aPrice(){
  var h='<h1>Narxlar va sozlamalar</h1>';
  [["tc","Test yaratish narxi (kredit)"],["tw","Yangi oʻqituvchiga kredit"],["sw","Yangi oʻquvchiga kredit"],["ref","Doʻst taklif uchun kredit"],["com","Oʻqituvchi ulushi (%)"]].forEach(function(x){
    h+='<label>'+x[1]+'</label><input type="number" min="0" value="'+CFG[x[0]]+'" onchange="CFG.'+x[0]+'=+this.value">'});
  h+='<h2>Kredit paketlari</h2>';
  CFG.pk.forEach(function(p,i){h+='<div class="two" style="align-items:end"><div><label>Kredit</label><input type="number" min="1" value="'+p.c+'" onchange="CFG.pk['+i+'].c=+this.value"></div><div><label>Narx (soʻm)</label><input type="number" min="0" value="'+p.p+'" onchange="CFG.pk['+i+'].p=+this.value"></div></div><button class="lnk" onclick="CFG.pk.splice('+i+',1);aPrice()">Oʻchirish</button>'});
  h+='<button class="cta alt" onclick="CFG.pk.push({c:50,p:25000});aPrice()">Paket qoʻshish</button><button class="cta" style="margin-top:10px" onclick="saveCfg()">Saqlash</button>';
  $("p_a_price").innerHTML=h;
}
async function saveCfg(){
  try{CFG=ME.cfg=await api("PUT","/api/admin/settings",CFG);aPrice();updTexts();toast("Saqlandi.",false,true)}catch(e){fail(e)}
}
function uCard(u){return (u.role==="t"?"Oʻqituvchi":"Oʻquvchi")+' · ID '+u.tg_id}
async function aUsers(){
  var a=await api("GET","/api/admin/users");
  var h='<h1>Foydalanuvchi</h1><label for="uq">Foydalanuvchi ID</label><input id="uq" inputmode="numeric" placeholder="Telegram ID"><div style="height:10px"></div><button class="cta" onclick="findU($(\'uq\').value.trim())">Profilni ochish</button><div id="up" style="margin-top:14px"></div><h2>Oxirgi foydalanuvchilar</h2>';
  a.forEach(function(u){h+='<div class="card click" data-i="'+u.tg_id+'" onclick="findU(this.dataset.i)"><b>'+esc(u.name)+'</b><small>'+uCard(u)+'</small></div>'});
  $("p_a_users").innerHTML=h;
}
async function findU(id){
  try{
    var a=/^\d{1,18}$/.test(id)?await api("GET","/api/admin/users/"+id):[],el=$("up");
    window.scrollTo(0,0);
    if(!a.length){el.innerHTML='<p class="err">Bunday ID topilmadi.</p>';return}
    el.innerHTML=a.map(function(u){return '<div class="card"><b>'+esc(u.name)+'</b><small>'+uCard(u)+'</small><small>Kredit: '+u.cr+(u.role==="s"?' · balans: '+fmt(u.bal)+' soʻm':' · daromad: '+fmt(u.earn)+' soʻm + '+u.ecr+' kredit')+'</small>'
      +(u.role==="s"?'<label>Nima beriladi</label><select id="gk'+u.id+'"><option value="cr">Kredit</option><option value="bal">Balans (soʻm)</option></select>':'')
      +'<label>Miqdor</label><input id="gv'+u.id+'" type="number" min="1" placeholder="Masalan, 100"><div style="height:10px"></div><button class="cta" data-i="'+u.tg_id+'" onclick="give('+u.id+',this)">Berish</button></div>'}).join("");
  }catch(e){fail(e)}
}
async function give(id,btn){
  var n=parseInt($("gv"+id).value),k=$("gk"+id);if(!n||n<1){toast("Miqdorni kiriting.",false);return}
  btn.disabled=true;
  try{await api("POST","/api/admin/give",{account_id:id,kind:k?k.value:"cr",amount:n});await findU(btn.dataset.i);toast("Berildi.",false,true)}
  catch(e){fail(e);btn.disabled=false}
}

/* ----- rasmni kattalashtirish ----- */
function zoom(src){$("zimg").src=src;$("zimg").classList.remove("max");$("zoom").classList.remove("hide")}
function unzoom(){$("zoom").classList.add("hide")}

/* ----- ishga tushirish ----- */
$("var").addEventListener("change",function(){render();fix()});
$("soni").addEventListener("input",function(){if($("soni").value){render();fix()}});
$("soni").addEventListener("change",function(){if(String(S.n)!==$("soni").value)$("soni").value=S.n});
$("file").addEventListener("change",onFile);
mode(0);
(async function(){
  if(tg){tg.ready();tg.expand()}
  if(!INIT){$("boot").textContent="Ilovani Telegram botidagi tugma orqali oching.";return}
  try{
    await refresh();
    SUBJ.forEach(function(x){var o=document.createElement("option");o.textContent=x;$("subj").appendChild(o)});
    $("fn").value=ME.first_name;$("ln").value=ME.last_name;
    $("boot").classList.add("hide");$("rc").classList.remove("hide");$("adm").classList.toggle("hide",!ME.is_admin);
  }catch(e){$("boot").textContent=e.message}
})();
