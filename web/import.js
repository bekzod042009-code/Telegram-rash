/* ----- Tayyor testni fayldan yuklash: PDF → AI → JSON → shu forma ----- */
/* Server oʻzgarmaydi: fayl formani toʻldiradi, oʻqituvchi tekshirib "Yuklash"ni bosadi. */

/* AI'ga beriladigan koʻrsatma. Tanlangan fan qolipiga moslab tuziladi. */
function buildPrompt(id){
  var t=id&&CFG.tpl[id],lines=[
    "Biriktirilgan fayldagi (PDF yoki rasm) testni JSON koʻrinishiga oʻtkaz.",
    "Javobingda faqat bitta JSON kod bloki boʻlsin, boshqa hech narsa yozma. Imkon boʻlsa, uni test.json fayli qilib ham ber.",
    "",
    "Qoidalar:",
    "- Savol va variant matnlarini aslidagidek koʻchir: qisqartirma, tarjima qilma, savol toʻqima, birorta savolni tashlab ketma.",
    "- Toʻgʻri javobni faqat fayldagi javoblar kalitidan ol. Kalit boʻlmasa yoki aniq boʻlmasa, \"javob\": null yoki boʻsh roʻyxat qoldir. Savolni oʻzing yechma.",
    "- Formulalarni oddiy matnda yoz (masalan: x², √3, π, 1/2). LaTeX ($, \\frac) ishlatma.",
    "- Savolda rasm, chizma, grafik, xarita yoki rasmli jadval boʻlsa, \"rasm\": true qoʻy.",
    "- Bir nechta savolga umumiy matn boʻlsa, uni oʻsha savollarning har birining \"matn\"iga qoʻsh.",
    "- \"variantlar\" ichida A), B) harflarini yozma.",
    "",
    "Format namunasi:",
    "{",
    "  \"fan\": \""+(id||"")+"\",",
    "  \"nom\": \"Test nomi\",",
    "  \"savollar\": [",
    "    {\"n\": 1, \"matn\": \"Savol matni\", \"variantlar\": [\"birinchi\", \"ikkinchi\", \"uchinchi\", \"toʻrtinchi\"], \"javob\": \"B\", \"rasm\": false},",
    t?"    {\"n\": 36, \"matn\": \"Umumiy shart. a) ... b) ...\", \"javoblar\": [[\"12\"], [\"0,5\", \"1/2\"]], \"rasm\": false}"
     :"    {\"n\": 2, \"matn\": \"Yozma javobli savol\", \"javoblar\": [[\"Alisher Navoiy\", \"Navoiy\"]], \"rasm\": false}",
    "  ]",
    "}",
    ""];
  if(!t){
    lines.push("Test tuzilishi:",
      "- Variantli savol: \"variantlar\" (2–6 ta) va \"javob\" (A–F harfi).",
      "- Yozma javobli savol: \"variantlar\" yoʻq, \"javoblar\": [[qabul qilinadigan barcha yozilishlar]].",
      "- Savolning a, b bandlari boʻlsa, har bandni alohida savol qil.",
      "- Koʻpi bilan 100 ta savol.");
    return lines.join("\n");
  }
  lines.push("Test tuzilishi ("+t.name+", jami "+t.slots.length+" ta savol). \"n\" — savolning shu tuzilishdagi raqami:");
  var i=0,j,s;
  while(i<t.slots.length){
    s=t.slots[i];j=i;
    while(j+1<t.slots.length&&t.slots[j+1].type===s.type&&(s.type!=="m"||t.slots[j+1].sec===s.sec))j++;
    var r=(i===j?s.n:s.n+"–"+t.slots[j].n)+"-savol";
    if(s.type==="y1")lines.push("- "+r+": yopiq, 4 ta variant (A–D): \"variantlar\" va \"javob\".");
    else if(s.type==="y2")lines.push("- "+r+": moslashtirish, 6 ta variant (A–F). Variantlar umumiy boʻlsa, har bir savolda takrorla.");
    else if(s.type==="o")lines.push("- "+r+": ochiq savol, variantsiz. \"javoblar\" ichida har bir band (a, b, ...) uchun alohida roʻyxat, unda shu bandning barcha qabul qilinadigan yozilishlari. Javob nomaʼlum boʻlsa: [[], []].");
    else lines.push("- "+r+": "+(s.sec||"yozma ish")+" (oʻqituvchi baholaydi): faqat \"matn\".");
    i=j+1;
  }
  return lines.join("\n");
}
function copyPrompt(){
  var t=buildPrompt($("tpl").value),b=$("pcopy"),
    done=function(){b.textContent="Nusxalandi ✓";setTimeout(function(){b.textContent="1. AI uchun koʻrsatmani nusxalash"},2000)},
    /* Nusxalash ishlamasa, matn koʻrsatiladi: qoʻlda nusxalash mumkin. */
    manual=function(){var a=$("ptext");a.value=t;a.classList.remove("hide");a.focus();a.select();try{if(document.execCommand("copy"))done()}catch(e){}};
  if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(t).then(done,manual);else manual();
}

/* ----- faylni oʻqish ----- */
function readImport(text){
  var a=text.indexOf("{"),b=text.lastIndexOf("}"),s=text.slice(a,b+1),d;
  if(a<0||b<a)throw new Error("Kod topilmadi. AI bergan JSON kodini toʻliq joylang.");
  try{d=JSON.parse(s)}catch(e){
    try{d=JSON.parse(s.replace(/,\s*([}\]])/g,"$1"))}
    catch(e2){throw new Error("Kod oʻqilmadi: toʻliq nusxalanmagan yoki AI javobi uzilib qolgan. AI'dan JSON'ni qayta, toʻliq berishni soʻrang.")}
  }
  if(d&&Array.isArray(d.savollar))d.savollar=d.savollar.filter(function(q){return q&&typeof q==="object"});
  if(!d||!Array.isArray(d.savollar)||!d.savollar.length)throw new Error("Faylda savollar topilmadi.");
  return d;
}
function str(v,max){return typeof v==="string"||typeof v==="number"?String(v).trim().slice(0,max):""}
function accList(v){return [].concat(v==null?[]:v).map(function(a){return str(a,200)}).filter(valid).slice(0,20)}
/* "javoblar": [["12"],["5"]] — bandlar; ["Navoiy"] — bitta band. */
function answerParts(q){
  var j=q.javoblar;
  if(j==null)return [];
  if(!Array.isArray(j))return [[j]];
  return j.some(Array.isArray)?j:j.length?[j]:[];
}
function optList(q){
  var v=q.variantlar;
  if(!v||typeof v!=="object")return [];
  if(!Array.isArray(v))v=Object.keys(v).sort().map(function(k){return v[k]});
  v=v.slice(0,6).map(function(x){return str(x,500)});
  var pre=function(j){return new RegExp("^"+L[j]+"\\s*\\)\\s*","i")};
  if(v.every(function(x,j){return pre(j).test(x)}))v=v.map(function(x,j){return x.replace(pre(j),"")});
  return v;
}
function letter(v,k){
  var s=str(v,3).toUpperCase().replace(/[).]$/,""),j=s.length===1?L.indexOf(s):-1;
  return j>-1&&j<k?s:null;
}
function putChoice(i,q,k){
  var o=optList(q);
  for(var j=0;j<6;j++)S.opt[i][j]=j<k?o[j]||"":"";
  S.ans[i]=letter(q.javob,k);
}
function putText(i,q){S.txt[i]=str(q.matn,8000);S.need[i]=q.rasm===true}

/* Faylda "fan" boʻlmasa, roʻyxatda tanlangani olinadi. */
function fanOf(d){
  var id=d.fan===undefined?$("tpl").value:str(d.fan,20);
  if(id&&!CFG.tpl.hasOwnProperty(id))throw new Error("Fayldagi fan notanish: "+id+". Fanni tanlab, koʻrsatmani qayta nusxalang.");
  return id;
}
function applyImport(d){
  var id=fanOf(d),notes=[],extra=[],absent=[],oneBand=[];
  fillTpl(id);
  if(id){
    var by={},slots=CFG.tpl[id].slots;
    d.savollar.forEach(function(q){var n=parseInt(q.n,10);if(n>=1&&n<=slots.length&&!by[n])by[n]=q;else extra.push(str(q.n,6)||"?")});
    ARR.forEach(function(a){S[a]=[]});
    slots.forEach(function(s){
      var q=by[s.n]||{},p=s.type==="o"?answerParts(q):[],count=s.type==="o"?Math.min(6,p.length||s.parts):1;
      if(!by[s.n])absent.push(s.n);
      /* Bandlar ajratilmagan boʻlsa, oʻqituvchiga aytiladi. */
      if(p.length===1&&p[0].length>1)oneBand.push(s.n);
      for(var j=0;j<count;j++){
        var e=entry(s,count>1?L[j].toLowerCase():""),i=S.meta.length;
        ARR.forEach(function(a){S[a].push(e[a])});
        if(!j)putText(i,q);
        if(s.type==="o")S.acc[i]=accList(p[j]);else if(s.type!=="m")putChoice(i,q,s.k);
      }
    });
  }else{
    var list=d.savollar.slice(0,100),k=0;
    list.forEach(function(q){k=Math.max(k,optList(q).length)});
    k=k?Math.max(2,k):4;
    $("soni").value=list.length;$("var").value=k;sync();
    list.forEach(function(q,i){
      putText(i,q);
      if(!optList(q).length&&q.javoblar!=null){var p=answerParts(q);S.w[i]=true;S.acc[i]=accList(p[0]);if(p.length>1)notes.push((i+1)+"-savol: faqat a) bandi olindi.")}
      else putChoice(i,q,k);
    });
    if(d.savollar.length>100)notes.push("Faqat birinchi 100 ta savol olindi.");
  }
  if(str(d.nom,120))$("nom").value=str(d.nom,120);
  var min=parseInt(d.vaqt,10);if(min>=1&&min<=600)$("vaqt").value=min;
  sync();
  var noAns=[],noImg=[],other=[],total=0,i,x;
  mk=[];
  for(i=0;i<S.n;i++){
    if(isB(i))continue;total++;
    if(rowOk(i))continue;
    mk.push(i);
    var miss=false;for(x=i;x<i+(isOpen(i)?parts(i):1);x++)if(!ansOk(x))miss=true;
    if(id&&absent.indexOf(qNum(i))>-1)continue; /* alohida qatorda aytiladi */
    if(miss)noAns.push(qNum(i));
    if(!printed&&S.need[i]&&!S.img[i])noImg.push(qNum(i));
    else if(!miss)other.push(qNum(i));
  }
  render();
  var sum=total+" ta savol joylandi"+(id?" ("+CFG.tpl[id].name+")":"")+", toʻliq: "+(total-mk.length)+".";
  var h="<b>"+esc(sum)+"</b>",line=function(t,a){if(a.length)h+="<span>"+esc(t+": "+a.slice(0,15).join(", ")+(a.length>15?" … (jami "+a.length+")":""))+"</span>"};
  line("Javob yetishmaydi",noAns);line("Rasm qoʻshing",noImg);line("Matn yoki variant yetishmaydi",other);
  line("Faylda yoʻq savollar",absent);line("Qolipga sigʻmagan raqamlar",extra);line("Bandlari ajratilmagan, tekshiring",oneBand);
  notes.forEach(function(n){h+="<span>"+esc(n)+"</span>"});
  h+="<span>AI xato qilishi mumkin: javoblarni tekshiring, keyin pastdagi Yuklash tugmasini bosing.</span>";
  $("impmsg").className="impmsg";$("impmsg").innerHTML=h;
  if(mk.length)showMiss();
}
function importText(text){
  var d;
  try{d=readImport(String(text));fanOf(d)}catch(e){impError(e.message);return}
  var run=function(ok){if(!ok)return;try{applyImport(d);$("imptext").value=""}catch(e){impError(e.message)}};
  if(!isFilled())return run(true);
  confirmBox("Kiritilgan savollar fayldagilar bilan almashtiriladi. Davom etilsinmi?",run);
}
function impError(t){$("impmsg").className="err";$("impmsg").textContent=t}
function pickImport(){$("impfile").value="";$("impfile").click()}
$("impfile").addEventListener("change",function(){
  var f=this.files[0];if(!f)return;
  if(f.size>1024*1024){impError("Fayl juda katta. AI bergan JSON faylni tanlang (PDF emas).");return}
  var r=new FileReader();
  r.onload=function(){importText(r.result)};
  r.onerror=function(){impError("Fayl oʻqilmadi. Kodni nusxalab joylang.")};
  r.readAsText(f);
});
