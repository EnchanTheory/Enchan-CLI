const $=id=>document.getElementById(id);
const state={config:null,mascot:null,timer:null,frame:0,busy:false,imageData:"",mascotImage:null,previewTimer:null,previewFrame:0,currentAnimation:"",animationToken:0};
const messages=$("messages"),welcome=$("welcome"),prompt=$("prompt"),send=$("send");

const translations={
  en:{sheetDimensions:"The image must be 1536×1872 px (selected: {width}×{height}).",sheetVerticalEdge:"Cell {row}-{column} touches its top or bottom edge. Keep at least 6 transparent pixels inside every cell.",sheetHorizontalEdge:"Cell {row}-{column} touches its left or right edge. Keep at least 6 transparent pixels inside every cell.",initError:"Failed to initialize the Web UI: {message}"},
  ja:{newChat:"新しい会話",mascotSettings:"マスコット設定",welcomeTitle:"今日は何をしましょうか？",welcomeBody:"ローカルのEnchanに質問や作業を依頼できます。",messagePlaceholder:"Enchanにメッセージ",send:"送信",toolNotice:"Enchanは設定に従ってローカルツールを実行する場合があります。",mascotTitle:"マスコット",mascotSubtitle:"Codex Pets互換コンタクトシート",close:"閉じる",addMascot:"＋ マスコットを追加",name:"名前",description:"説明",personality:"性格",personalityPlaceholder:"会話時の振る舞い、口調、価値観",contactSheet:"コンタクトシート",sheetRequirement:"必須: 1536×1872 px、8列×9行、1フレーム192×208 px",animationPreview:"アニメーションPreview",idle:"待機",runningRight:"右移動",runningLeft:"左移動",waving:"挨拶",jumping:"ジャンプ",failed:"失敗",waiting:"思考中",running:"作業中",review:"確認",previewEmpty:"画像を登録すると表示されます。",saveAndSelect:"保存して選択",sheetDimensions:"画像は1536×1872 pxが必要です（選択: {width}×{height}）",sheetVerticalEdge:"セル {row}-{column} の上下端に画像があります。各セル内に6px以上の透明余白が必要です。",sheetHorizontalEdge:"セル {row}-{column} の左右端に画像があります。各セル内に6px以上の透明余白が必要です。",initError:"Web UIの初期化に失敗しました: {message}"}
};
const locale=(navigator.languages||[navigator.language||"en"]).some(value=>value.toLowerCase().startsWith("ja"))?"ja":"en";
function tr(key,values={}){let text=translations[locale]?.[key]||document.querySelector(`[data-i18n="${key}"]`)?.textContent||key;for(const [name,value] of Object.entries(values))text=text.replaceAll(`{${name}}`,value);return text}
function applyLocale(){document.documentElement.lang=locale;document.querySelectorAll("[data-i18n]").forEach(element=>{const value=translations[locale]?.[element.dataset.i18n];if(value)element.textContent=value});document.querySelectorAll("[data-i18n-placeholder]").forEach(element=>{const value=translations[locale]?.[element.dataset.i18nPlaceholder];if(value)element.placeholder=value});document.querySelectorAll("[data-i18n-title]").forEach(element=>{const value=translations[locale]?.[element.dataset.i18nTitle];if(value){element.title=value;element.setAttribute("aria-label",value)}})}
applyLocale();

const clientId=crypto.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
function heartbeat(){return fetch("/api/client/heartbeat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({clientId}),keepalive:true}).catch(()=>{})}
function closeClient(){clearInterval(heartbeatTimer);const body=new Blob([JSON.stringify({clientId})],{type:"text/plain;charset=UTF-8"});navigator.sendBeacon("/api/client/close",body)}
heartbeat();
const heartbeatTimer=setInterval(heartbeat,3000);
window.addEventListener("pageshow",heartbeat);
window.addEventListener("pagehide",closeClient);
window.addEventListener("beforeunload",closeClient);

async function api(path,body){
  const response=await fetch(path,{method:body?"POST":"GET",headers:body?{"Content-Type":"application/json"}:{},body:body?JSON.stringify(body):undefined});
  const data=await response.json();
  if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);
  return data;
}
const ghost=document.createElement("div");
ghost.style.cssText="position:absolute;visibility:hidden;white-space:pre-wrap;overflow-wrap:anywhere;line-height:22px;padding:9px 2px 7px;border:0;box-sizing:border-box;word-break:break-all;";
document.body.appendChild(ghost);
function resize(){
  const val=prompt.value;
  const style=window.getComputedStyle(prompt);
  ghost.style.width=style.width;
  ghost.style.font=style.font;
  ghost.textContent=val+"\n";
  const h=Math.min(Math.max(ghost.offsetHeight,40),180);
  prompt.style.height=h+"px";
  prompt.style.overflowY=ghost.offsetHeight>180?"auto":"hidden";
  send.disabled=state.busy||!val.trim();
}
function renderMarkdown(text){
  if(!text)return"";let html=text.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  html=html.replace(/```([\s\S]*?)```/g,(match,code)=>{const lines=code.split("\n");let lang="";if(lines[0]&&!lines[0].includes(" ")&&lines[0].length<15)lang=lines.shift();return`<pre><code class="language-${lang}">${lines.join("\n").trim()}</code></pre>`});
  html=html.replace(/`([^`\n]+)`/g,"<code>$1</code>").replace(/\*\*([\s\S]+?)\*\*/g,"<strong>$1</strong>").replace(/\*([\s\S]+?)\*/g,"<em>$1</em>");
  html=html.replace(/^(#{1,6})\s+(.+)$/gm,(match,hashes,content)=>`<h${hashes.length}>${content}</h${hashes.length}>`);
  html=html.replace(/^>\s+(.+)$/gm,"<blockquote>$1</blockquote>").replace(/^[\s]*[-*+]\s+(.+)$/gm,"<li>$1</li>").replace(/(<li>[\s\S]*?<\/li>)/g,"<ul>$1</ul>").replace(/<\/ul>\s*<ul>/g,"");
  const parts=html.split(/(<pre>[\s\S]*?<\/pre>)/g);
  html=parts.map(part=>{if(part.startsWith("<pre>"))return part;let p=part.replace(/\n/g,"<br>");p=p.replace(/<br>\s*<\/?(ul|li|blockquote|h\d)/gi,m=>m.replace("<br>",""));p=p.replace(/<\/(ul|li|blockquote|h\d)>\s*<br>/gi,m=>m.replace("<br>",""));return p}).join("");
  return html.replace(/(<br>){2,}/g,"<br>").trim();
}
function addMessage(role,text,error=false){
  welcome.hidden=true;const row=document.createElement("article");row.className=`message ${role}${error?" error":""}`;
  if(role==="user"){const bubble=document.createElement("div");bubble.className="user-bubble";bubble.textContent=text;row.append(bubble)}
  else{const body=document.createElement("div");const name=document.createElement("div");name.className="assistant-name";name.textContent=state.mascot?.name||"Enchan";const content=document.createElement("div");content.className="message-text";content.innerHTML=renderMarkdown(text);body.append(name,content);row.append(body)}
  messages.append(row);window.scrollTo({top:document.body.scrollHeight,behavior:"smooth"});return row
}
function selectedMascot(){return state.config?.mascots.find(m=>m.id===state.config.selectedMascot)}
function applyMascot(){
  state.mascot=selectedMascot();const stage=$("mascotStage");
  if(!state.mascot?.spritesheet){stage.hidden=true;return}
  const image=new Image();image.onload=()=>{state.mascotImage=image;stage.hidden=false;play("idle")};image.onerror=()=>{stage.hidden=true};image.src=`/api/mascots/${encodeURIComponent(state.mascot.id)}?v=${Date.now()}`
}
function drawFrame(index, canvasId="mascotSprite", imageSrc=state.mascotImage){
  const canvas=$(canvasId);
  if(!canvas||!imageSrc)return;
  const ctx=canvas.getContext("2d");
  if(canvas.width!==192||canvas.height!==208){canvas.width=192;canvas.height=208}
  ctx.clearRect(0,0,192,208);ctx.imageSmoothingEnabled=false;
  const x=index%8,y=Math.floor(index/8);
  ctx.drawImage(imageSrc,x*192,y*208,192,208,0,0,192,208);
}
function restingAnimation(){return state.busy?"waiting":"idle"}
function play(name,{loop=false,resume=true,restart=true}={}){
  if(!restart&&state.currentAnimation===name)return;
  clearTimeout(state.timer);if(!state.mascot?.spritesheet)return;const anim=state.config.animations[name]||state.config.animations.idle;
  const token=++state.animationToken;state.currentAnimation=name;
  let frames,durations;
  if(anim.frames){frames=anim.frames;durations=anim.durations}
  else{const cycle=Array.from({length:anim.count},(_,i)=>anim.row*8+i);frames=Array.from({length:anim.repeats||1},()=>cycle).flat();durations=frames.map((_,i)=>i%anim.count===anim.count-1?anim.finalDuration:anim.frameDuration)}
  state.frame=0;const tick=()=>{const index=frames[state.frame];
  drawFrame(index);
  const duration=durations[state.frame]||140;state.frame++;
    if(state.frame>=frames.length){
      if(loop||name==="idle"){state.frame=0}
      else{state.timer=setTimeout(()=>{if(token===state.animationToken&&resume)play(restingAnimation(),{loop:state.busy})},duration);return}
    }
    state.timer=setTimeout(()=>{if(token===state.animationToken)tick()},duration)
  };tick()
}
async function loadConfig(){state.config=await api("/api/config");$("runtime").textContent=`${state.config.model} · ${state.config.backend}`;applyMascot();renderMascotList()}
function renderMascotList(){
  const list=$("mascotList");list.replaceChildren();
  for(const mascot of state.config.mascots){
    const button=document.createElement("button");button.type="button";button.className=`mascot-item ${mascot.id===state.config.selectedMascot?"active":""}`;
    const canvas=document.createElement("canvas");canvas.className="mascot-item-preview";canvas.width=192;canvas.height=208;canvas.setAttribute("aria-hidden","true");
    const copy=document.createElement("span");copy.className="mascot-item-copy";copy.innerHTML="<strong></strong><small></small>";
    copy.querySelector("strong").textContent=mascot.name;copy.querySelector("small").textContent=mascot.description||mascot.id;
    button.append(canvas,copy);button.onclick=()=>editMascot(mascot);list.append(button);
    if(mascot.spritesheet){
      const image=new Image();image.onload=()=>{const ctx=canvas.getContext("2d");ctx.clearRect(0,0,192,208);ctx.imageSmoothingEnabled=false;ctx.drawImage(image,0,0,192,208,0,0,192,208)};
      image.src=`/api/mascots/${encodeURIComponent(mascot.id)}?v=${Date.now()}`;
    }
  }
}
let previewImage = null;
function updatePreviewCanvas(){
  if(!previewImage)return;
  const animName=$("previewAnimSelect").value||"idle";
  const anim=state.config.animations[animName]||state.config.animations.idle;
  const frames=anim.frames || Array.from({length:anim.count},(_,i)=>anim.row*8+i);
  state.previewFrame=(state.previewFrame+1)%frames.length;
  drawFrame(frames[state.previewFrame], "livePreviewCanvas", previewImage);
  state.previewTimer=setTimeout(updatePreviewCanvas, 200);
}
function validatePetSheet(image){
  if(image.naturalWidth!==1536||image.naturalHeight!==1872)return tr("sheetDimensions",{width:image.naturalWidth,height:image.naturalHeight});
  const canvas=document.createElement("canvas");canvas.width=1536;canvas.height=1872;const ctx=canvas.getContext("2d",{willReadFrequently:true});ctx.drawImage(image,0,0);const data=ctx.getImageData(0,0,1536,1872).data;
  const alpha=(x,y)=>data[(y*1536+x)*4+3];
  for(let row=0;row<9;row++)for(let col=0;col<8;col++)for(let inset=0;inset<6;inset++){
    const left=col*192+inset,right=(col+1)*192-1-inset,top=row*208+inset,bottom=(row+1)*208-1-inset;
    for(let x=left;x<=right;x++)if(alpha(x,top)>16||alpha(x,bottom)>16)return tr("sheetVerticalEdge",{row:row+1,column:col+1});
    for(let y=top;y<=bottom;y++)if(alpha(left,y)>16||alpha(right,y)>16)return tr("sheetHorizontalEdge",{row:row+1,column:col+1});
  }
  return "";
}
function editMascot(m){
  $("mascotId").value=m?.id||"";$("mascotId").readOnly=!!m;$("mascotEditName").value=m?.name||"";$("mascotDescription").value=m?.description||"";$("mascotPersonality").value=m?.personality||"";
  $("mascotImage").value="";state.imageData="";
  $("sheetError").textContent="";
  previewImage=null;clearTimeout(state.previewTimer);
  const preview=$("sheetPreviewText"),cvs=$("livePreviewCanvas"),sel=$("previewAnimSelect");
  if(m?.spritesheet){
    preview.hidden=true;cvs.hidden=false;sel.hidden=false;
    previewImage=new Image();previewImage.onload=updatePreviewCanvas;
    previewImage.src=`/api/mascots/${encodeURIComponent(m.id)}?v=${Date.now()}`;
  }else{
    preview.hidden=false;cvs.hidden=true;sel.hidden=true;
  }
}
$("composer").addEventListener("submit",async e=>{e.preventDefault();const text=prompt.value.trim();if(!text||state.busy)return;addMessage("user",text);prompt.value="";state.busy=true;resize();play("waiting",{loop:true});
  const row=addMessage("assistant","");const textNode=row.querySelector(".message-text");
  try{const response=await fetch("/api/chat_stream",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:text})});
  if(!response.ok){const err=await response.json();throw new Error(err.error||`HTTP ${response.status}`)}
  play(state.config?.agentMode?"running":"waiting",{loop:true});const reader=response.body.getReader();const decoder=new TextDecoder("utf-8");let fullText="";let buffer="";
  let isDone=false;while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const lines=buffer.split("\n");buffer=lines.pop();for(const line of lines){if(line.startsWith("data: ")){const dataStr=line.slice(6).trim();if(dataStr==="[DONE]"){isDone=true;break;}try{const data=JSON.parse(dataStr);if(data.chunk){fullText+=data.chunk;textNode.innerHTML=renderMarkdown(fullText)||"&nbsp;";window.scrollTo({top:document.body.scrollHeight,behavior:"auto"})}}catch(err){}}}if(isDone)break;}
  if(!fullText)textNode.innerHTML="(empty response)";play("waving")}catch(error){textNode.textContent=error.message;row.classList.add("error");play("failed")}finally{state.busy=false;resize();prompt.focus()}});
prompt.addEventListener("input",resize);prompt.addEventListener("keydown",e=>{if(e.isComposing||e.keyCode===229)return;if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();$("composer").requestSubmit()}});
$("newChat").onclick=async()=>{await api("/api/new",{});[...messages.querySelectorAll(".message")].forEach(x=>x.remove());welcome.hidden=false;play("jumping")};
$("settings").onclick=()=>{
  $("mascotDialog").showModal();
  editMascot(selectedMascot());
  $("previewAnimSelect").onchange=()=>{state.previewFrame=0;clearTimeout(state.previewTimer);updatePreviewCanvas()};
};
$("addMascot").onclick=()=>editMascot(null);
$("mascotImage").onchange=async e=>{
  const file=e.target.files[0];if(!file)return;const url=URL.createObjectURL(file);
  previewImage=new Image();
  await new Promise((resolve,reject)=>{previewImage.onload=resolve;previewImage.onerror=reject;previewImage.src=url});
  URL.revokeObjectURL(url);
  const validationError=validatePetSheet(previewImage);$("sheetError").textContent=validationError;
  if(validationError){e.target.value="";state.imageData="";return}
  state.imageData=await new Promise(resolve=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.readAsDataURL(file)});
  $("sheetPreviewText").hidden=true;$("livePreviewCanvas").hidden=false;$("previewAnimSelect").hidden=false;
  clearTimeout(state.previewTimer);updatePreviewCanvas();
};
$("mascotForm").onsubmit=async e=>{e.preventDefault();try{
  state.config=await api("/api/mascots",{id:$("mascotId").value,name:$("mascotEditName").value,description:$("mascotDescription").value,personality:$("mascotPersonality").value,image:state.imageData});
  renderMascotList();applyMascot();$("mascotDialog").close();play("waving")
}catch(error){alert(error.message)}};
$("mascotDialog").addEventListener("close",()=>{clearTimeout(state.previewTimer);state.previewTimer=null});
loadConfig().catch(error=>addMessage("assistant",tr("initError",{message:error.message}),true));resize();prompt.focus();

const mascotStage=document.querySelector(".mascot-stage");
const mascotTrack=document.querySelector(".mascot-track");
let mascotDragging=false,mascotGrabOffset=0,mascotLastPointerX=0;
const mascotPositionKey="enchan.mascot.position";
function clampMascotPosition(value){return Math.max(0,Math.min(value,Math.max(0,mascotTrack.clientWidth-mascotStage.offsetWidth)))}
function setMascotPosition(value,save=false){const next=clampMascotPosition(value);mascotStage.style.left=next+"px";if(save)localStorage.setItem(mascotPositionKey,String(next))}
mascotStage.addEventListener("pointerdown",event=>{
  mascotDragging=true;mascotLastPointerX=event.clientX;mascotGrabOffset=event.clientX-mascotStage.getBoundingClientRect().left;
  mascotStage.setPointerCapture(event.pointerId);play("jumping",{loop:true});
});
mascotStage.addEventListener("pointermove",event=>{
  if(!mascotDragging)return;
  const delta=event.clientX-mascotLastPointerX;mascotLastPointerX=event.clientX;
  const trackLeft=mascotTrack.getBoundingClientRect().left;setMascotPosition(event.clientX-trackLeft-mascotGrabOffset);
  if(Math.abs(delta)>=1)play(delta>0?"running-right":"running-left",{loop:true,restart:false});
});
function finishMascotDrag(event){
  if(!mascotDragging)return;
  mascotDragging=false;setMascotPosition(parseFloat(mascotStage.style.left)||0,true);
  if(mascotStage.hasPointerCapture(event.pointerId))mascotStage.releasePointerCapture(event.pointerId);
  play("jumping");
}
mascotStage.addEventListener("pointerup",finishMascotDrag);mascotStage.addEventListener("pointercancel",finishMascotDrag);
window.addEventListener("resize",()=>setMascotPosition(parseFloat(mascotStage.style.left)||0));
requestAnimationFrame(()=>setMascotPosition(Number(localStorage.getItem(mascotPositionKey))||0));