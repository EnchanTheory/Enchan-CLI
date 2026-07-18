window.EnchanI18n.ready.then(()=>{
const $=id=>document.getElementById(id);
const {t}=window.EnchanI18n;
const dialogs=window.EnchanDialogs;
const state={config:null,mascot:null,timer:null,frame:0,busy:false,ragBusy:false,ragStatus:null,imageData:"",mascotImage:null,previewTimer:null,previewFrame:0,currentAnimation:"",animationToken:0,pendingApproval:null,pendingConfirmation:null};
const messages=$("messages"),welcome=$("welcome"),prompt=$("prompt"),send=$("send");

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
  const raw=await response.text();let data;
  try{data=raw?JSON.parse(raw):{}}
  catch(_){throw new Error(response.ok?"The local API returned an invalid response.":t("errors.backendOutOfDate",{status:response.status}))}
  if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);
  return data;
}
  function approvalDetailLabel(key){return t(`approval.detail.${key}`,{},key.replaceAll("_"," "))}
  function showApproval(request){
    state.pendingApproval=request;
    $("approvalSummary").textContent=t(`approval.summary.${request.capability}`,{},request.summary);
    const details=$("approvalDetails");details.replaceChildren();
    const entries=[["tool",request.tool],["capability",request.capability],...Object.entries(request.details||{})];
    for(const [key,rawValue] of entries){
      const term=document.createElement("dt");term.textContent=approvalDetailLabel(key);
      const value=document.createElement("dd");
      value.textContent=key==="operation"?t(`approval.operation.${rawValue}`,{},rawValue):String(rawValue);
      details.append(term,value);
    }
    $("approvalAllow").disabled=false;$("approvalDeny").disabled=false;
    const dialog=$("approvalDialog");if(!dialog.open)dialogs.open(dialog);
    $("approvalDeny").focus();play("review",{loop:true});
  }
  async function resolveApproval(approved){
    const request=state.pendingApproval;if(!request)return;
    $("approvalAllow").disabled=true;$("approvalDeny").disabled=true;
    state.pendingApproval=null;
    try{await api(`/api/approvals/${encodeURIComponent(request.id)}`,{clientId,approved})}
    finally{if($("approvalDialog").open)dialogs.close("approvalDialog")}
  }
  $("approvalAllow").onclick=()=>resolveApproval(true);
  $("approvalDeny").onclick=()=>resolveApproval(false);
  $("approvalDialog").addEventListener("wa-after-hide",()=>{if(state.pendingApproval)resolveApproval(false)});
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
  prompt.disabled=state.ragBusy;
  prompt.placeholder=state.ragBusy?t("rag.chatDisabled"):t("composer.placeholder");
  send.disabled=state.busy||state.ragBusy||!val.trim();
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
window.addEventListener("enchan:social-outing-start",event=>{
  if(state.busy||state.ragBusy){event.preventDefault();return}
  state.busy=true;resize();play("running-right",{loop:true});
});
window.addEventListener("enchan:social-outing-complete",event=>{
  state.busy=false;resize();addMessage("assistant",event.detail?.message||t("social.outing.returned"));play("waving");
});
window.addEventListener("enchan:social-outing-error",()=>{
  state.busy=false;resize();play("failed");
});
function selectedMascot(){return state.config?.mascots.find(m=>m.id===state.config.selectedMascot)}
function applyMascot(){
  state.mascot=selectedMascot();const stage=$("mascotStage");
  if(!state.mascot?.spritesheet){stage.hidden=true;return}
  const image=new Image();image.onload=()=>{state.mascotImage=image;stage.hidden=false;play("idle")};image.onerror=()=>{stage.hidden=true};image.src=`/api/mascots/${encodeURIComponent(state.mascot.id)}?v=${Date.now()}`
}
function drawFrame(index,canvasId="mascotSprite",imageSrc=state.mascotImage){
  const canvas=$(canvasId);if(!canvas||!imageSrc)return;
  const ctx=canvas.getContext("2d");if(canvas.width!==192||canvas.height!==208){canvas.width=192;canvas.height=208}
  ctx.clearRect(0,0,192,208);ctx.imageSmoothingEnabled=false;const x=index%8,y=Math.floor(index/8);ctx.drawImage(imageSrc,x*192,y*208,192,208,0,0,192,208);
}
function restingAnimation(){return state.busy?"waiting":"idle"}
function play(name,{loop=false,resume=true,restart=true}={}){
  if(!restart&&state.currentAnimation===name)return;
  clearTimeout(state.timer);if(!state.mascot?.spritesheet)return;const anim=state.config.animations[name]||state.config.animations.idle;
  const token=++state.animationToken;state.currentAnimation=name;let frames,durations;
  if(anim.frames){frames=anim.frames;durations=anim.durations}else{const cycle=Array.from({length:anim.count},(_,i)=>anim.row*8+i);frames=Array.from({length:anim.repeats||1},()=>cycle).flat();durations=frames.map((_,i)=>i%anim.count===anim.count-1?anim.finalDuration:anim.frameDuration)}
  state.frame=0;const tick=()=>{const index=frames[state.frame];drawFrame(index);const duration=durations[state.frame]||140;state.frame++;if(state.frame>=frames.length){if(loop||name==="idle"){state.frame=0}else{state.timer=setTimeout(()=>{if(token===state.animationToken&&resume)play(restingAnimation(),{loop:state.busy})},duration);return}}state.timer=setTimeout(()=>{if(token===state.animationToken)tick()},duration)};tick();
}
async function loadConfig(){state.config=await api("/api/config");$("runtime").textContent=`${state.config.model} · ${state.config.backend}`;applyMascot();renderMascotList()}
function formatDuration(value){
  if(value===null||value===undefined||!Number.isFinite(Number(value)))return t("rag.calculating");
  const seconds=Math.max(0,Math.round(Number(value)));if(seconds<60)return t("rag.seconds",{count:seconds});
  const minutes=Math.floor(seconds/60),rest=seconds%60;if(minutes<60)return t("rag.minutes",{minutes,seconds:rest});
  return t("rag.hours",{hours:Math.floor(minutes/60),minutes:minutes%60});
}
function ragStateLabel(value){return t(`rag.jobState.${value}`,{},value||t("rag.jobState.idle"))}
function ragCollectionLabel(value){return t(`rag.collectionStatus.${value}`,{},value||"registered")}
function ragCollectionName(collection){return collection?.source_type==="sessions"?t("rag.sessionsName"):collection?.name}
function setRagPanel(open){
  $("ragPanel").classList.toggle("open",open);$("ragPanel").setAttribute("aria-hidden",String(!open));$("ragToggle").setAttribute("aria-expanded",String(open));document.body.classList.toggle("rag-open",open);localStorage.setItem("enchan.rag.open",open?"1":"0");
}
function renderRagStatus(data){
  state.ragStatus=data;const job=data.job||{};state.ragBusy=["running","stopping"].includes(job.state);resize();
  const jobBox=$("ragJob");jobBox.hidden=!job.collectionId;
  if(job.collectionId){
    const target=(data.collections||[]).find(collection=>collection.id===job.collectionId);$("ragJobCollection").textContent=ragCollectionName(target)||job.collectionName||job.collectionId;$("ragJobState").textContent=ragStateLabel(job.state);$("ragJobPercent").textContent=`${Math.round(job.percent||0)}%`;$("ragProgress").value=job.percent||0;$("ragJobMessage").textContent=job.message||"";$("ragElapsed").textContent=formatDuration(job.elapsedSeconds);$("ragEta").textContent=job.state==="completed"?t("rag.complete"):formatDuration(job.etaSeconds);$("ragCancel").hidden=!state.ragBusy;$("ragCancel").disabled=job.state==="stopping";$("ragDismiss").hidden=job.state!=="completed";
  }
  const list=$("ragCollections");list.replaceChildren();
  for(const collection of data.collections||[]){
    const card=document.createElement("article");card.className="rag-collection";
    const name=ragCollectionName(collection);const head=document.createElement("div");head.className="rag-collection-head";const title=document.createElement("h4");title.textContent=name;head.append(title);if(collection.status==="ready"||collection.status==="stale"){const badge=document.createElement("span");badge.className="rag-badge";badge.textContent=ragCollectionLabel(collection.status);head.append(badge)}
    const description=document.createElement("p");description.className="rag-description";description.textContent=collection.source_type==="sessions"?t("rag.sessionsDescription"):(collection.description||t("rag.noDescription"));
    const path=document.createElement("p");path.className="rag-path";path.textContent=collection.source_path;
    const status=document.createElement("p");status.className="rag-collection-status";status.textContent=`${ragCollectionLabel(collection.status)} · ${collection.chunk_count||0} ${t("rag.chunks")}`;
    const actions=document.createElement("div");actions.className="rag-actions";
    const start=document.createElement("button");start.type="button";start.className="primary";const resumable=!!collection.job?.canResume;start.textContent=resumable?t("rag.resume"):(collection.status==="ready"?t("rag.rebuild"):t("rag.start"));start.disabled=state.ragBusy||collection.source_missing;start.onclick=()=>startRag(collection.id,name,resumable);actions.append(start);
    if(!collection.required){const edit=document.createElement("button");edit.type="button";edit.className="secondary";edit.textContent=t("rag.edit");edit.disabled=state.ragBusy;edit.onclick=()=>openRagRegistration(collection);actions.append(edit);const remove=document.createElement("button");remove.type="button";remove.className="secondary";remove.textContent=t("common.remove");remove.disabled=state.ragBusy;remove.onclick=()=>deleteRag(collection.id,name);actions.append(remove)}
    card.append(head,description,path,status,actions);list.append(card);
  }
}
let ragRequestActive=false;
async function loadRagStatus({showError=false}={}){
  if(ragRequestActive)return;ragRequestActive=true;
  try{renderRagStatus(await api("/api/rag/status"));if(showError)$("ragError").textContent=""}catch(error){if(showError)$("ragError").textContent=t("errors.request",{message:error.message})}finally{ragRequestActive=false}
}
function confirmAction({message}){
  if(state.pendingConfirmation)return Promise.resolve(false);
  const dialog=$("confirmationDialog");
  dialog.label=t("common.confirm");$("confirmationMessage").textContent=message;$("confirmationAccept").textContent=t("common.yes");$("confirmationCancel").textContent=t("common.no");
  return new Promise(resolve=>{state.pendingConfirmation=resolve;dialogs.open(dialog)});
}
function resolveConfirmation(confirmed){
  const resolve=state.pendingConfirmation;if(!resolve)return;
  state.pendingConfirmation=null;dialogs.close("confirmationDialog");resolve(confirmed);
}
window.EnchanConfirmAction=confirmAction;
async function startRag(collectionId,name,resume){
  if(!await confirmAction({label:t(resume?"rag.resume":"rag.start"),message:t(resume?"rag.confirmResume":"rag.confirmStart"),target:name,badge:"RAG"}))return;$("ragError").textContent="";
  try{await api("/api/rag/start",{collectionId});await loadRagStatus({showError:true})}catch(error){$("ragError").textContent=t("errors.request",{message:error.message})}
}
async function deleteRag(collectionId,name){
  if(!await confirmAction({label:t("common.remove"),message:t("rag.confirmDelete",{name}),target:name,badge:"RAG",danger:true}))return;
  try{await api("/api/rag/delete",{collectionId});await loadRagStatus({showError:true})}catch(error){$("ragError").textContent=t("errors.request",{message:error.message})}
}
function openRagRegistration(collection=null){
  const editing=!!collection;$("ragCollectionId").value=collection?.id||"";$("ragTitle").value=collection?.name||"";$("ragDescription").value=collection?.description||"";$("ragDirectory").value=collection?.source_path||"";$("ragBrowse").hidden=editing;$("ragRegisterSubmit").textContent=t(editing?"rag.save":"rag.register");$("ragRegisterError").textContent="";dialogs.open("ragRegisterDialog");
}
async function selectRagDirectory(){
  const button=$("ragBrowse");button.disabled=true;$("ragRegisterError").textContent="";
  try{
    const result=await api("/api/rag/select-directory",{});
    if(!result.cancelled&&result.path){$("ragDirectory").value=result.path;if(!$("ragTitle").value.trim())$("ragTitle").value=result.path.split(/[\\/]/).filter(Boolean).pop()||"RAG"}
  }catch(error){$("ragRegisterError").textContent=t("errors.request",{message:error.message})}finally{button.disabled=false}
}
function renderMascotList(){
  const list=$("mascotList");list.replaceChildren();
  for(const mascot of state.config.mascots){
    const button=document.createElement("button");button.type="button";button.className=`mascot-item ${mascot.id===state.config.selectedMascot?"active":""}`;
    const canvas=document.createElement("canvas");canvas.className="mascot-item-preview";canvas.width=192;canvas.height=208;canvas.setAttribute("aria-hidden","true");
    const copy=document.createElement("span");copy.className="mascot-item-copy";copy.innerHTML="<strong></strong><small></small>";copy.querySelector("strong").textContent=mascot.name;copy.querySelector("small").textContent=mascot.description||mascot.id;
    button.append(canvas,copy);button.onclick=()=>editMascot(mascot);list.append(button);
    if(mascot.spritesheet){const image=new Image();image.onload=()=>{const ctx=canvas.getContext("2d");ctx.clearRect(0,0,192,208);ctx.imageSmoothingEnabled=false;ctx.drawImage(image,0,0,192,208,0,0,192,208)};image.src=`/api/mascots/${encodeURIComponent(mascot.id)}?v=${Date.now()}`}
  }
}
let previewImage=null;
function updatePreviewCanvas(){if(!previewImage)return;const animName=$("previewAnimSelect").value||"idle";const anim=state.config.animations[animName]||state.config.animations.idle;const frames=anim.frames||Array.from({length:anim.count},(_,i)=>anim.row*8+i);state.previewFrame=(state.previewFrame+1)%frames.length;drawFrame(frames[state.previewFrame],"livePreviewCanvas",previewImage);state.previewTimer=setTimeout(updatePreviewCanvas,200)}
function validatePetSheet(image){
  if(image.naturalWidth!==1536||image.naturalHeight!==1872)return t("mascot.sheetDimensions",{width:image.naturalWidth,height:image.naturalHeight});
  const canvas=document.createElement("canvas");canvas.width=1536;canvas.height=1872;const ctx=canvas.getContext("2d",{willReadFrequently:true});ctx.drawImage(image,0,0);const data=ctx.getImageData(0,0,1536,1872).data;const alpha=(x,y)=>data[(y*1536+x)*4+3];
  for(let row=0;row<9;row++)for(let col=0;col<8;col++)for(let inset=0;inset<6;inset++){const left=col*192+inset,right=(col+1)*192-1-inset,top=row*208+inset,bottom=(row+1)*208-1-inset;for(let x=left;x<=right;x++)if(alpha(x,top)>16||alpha(x,bottom)>16)return t("mascot.sheetVerticalEdge",{row:row+1,column:col+1});for(let y=top;y<=bottom;y++)if(alpha(left,y)>16||alpha(right,y)>16)return t("mascot.sheetHorizontalEdge",{row:row+1,column:col+1})}
  return "";
}
function editMascot(m){
  $("mascotId").value=m?.id||"";$("mascotId").readOnly=!!m;$("mascotEditName").value=m?.name||"";$("mascotDescription").value=m?.description||"";$("mascotPersonality").value=m?.personality||"";$("mascotImage").value="";state.imageData="";$("sheetError").textContent="";previewImage=null;clearTimeout(state.previewTimer);
  const preview=$("sheetPreviewText"),cvs=$("livePreviewCanvas"),sel=$("previewAnimSelect");
  if(m?.spritesheet){preview.hidden=true;cvs.hidden=false;sel.hidden=false;previewImage=new Image();previewImage.onload=updatePreviewCanvas;previewImage.src=`/api/mascots/${encodeURIComponent(m.id)}?v=${Date.now()}`}else{preview.hidden=false;cvs.hidden=true;sel.hidden=true}
}
$("composer").addEventListener("submit",async event=>{
  event.preventDefault();
  const text=prompt.value.trim();if(!text||state.busy)return;
  addMessage("user",text);prompt.value="";state.busy=true;resize();play("waiting",{loop:true});
  const row=addMessage("assistant","");const textNode=row.querySelector(".message-text");
  try{
    const response=await fetch("/api/chat_stream",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({message:text,clientId})
    });
    if(!response.ok){const error=await response.json();throw new Error(error.error||`HTTP ${response.status}`)}
    play(state.config?.agentMode?"running":"waiting",{loop:true});
    const reader=response.body.getReader(),decoder=new TextDecoder("utf-8");
    let fullText="",buffer="",isDone=false,toolFailed=false;
    while(true){
      const {value,done}=await reader.read();if(done)break;
      buffer+=decoder.decode(value,{stream:true});const lines=buffer.split("\n");buffer=lines.pop();
      for(const line of lines){
        if(!line.startsWith("data: "))continue;
        const dataText=line.slice(6).trim();if(dataText==="[DONE]"){isDone=true;break}
        const data=JSON.parse(dataText);
        if(data.type==="approval_required"){showApproval(data.request);continue}
        if(data.type==="approval_resolved"){
          if(state.pendingApproval?.id===data.requestId){
            state.pendingApproval=null;
            if($("approvalDialog").open)dialogs.close("approvalDialog");
            play(state.config?.agentMode?"running":"waiting",{loop:true});
          }
          continue;
        }
        if(data.type==="error")throw new Error(data.error||t("errors.emptyResponse"));
        if(data.type==="tool_result"){
          toolFailed=!data.ok;
          fullText=t(data.ok?"toolResult.success":"toolResult.failure",{tool:data.tool});
          if(data.message)fullText+=`\n\n${data.message}`;
          textNode.innerHTML=renderMarkdown(fullText);
          if(toolFailed)row.classList.add("error");
          continue;
        }
        if(data.type==="chunk"&&data.chunk){
          fullText+=data.chunk;textNode.innerHTML=renderMarkdown(fullText)||"&nbsp;";
          window.scrollTo({top:document.body.scrollHeight,behavior:"auto"});
        }
      }
      if(isDone)break;
    }
    if(!fullText)textNode.textContent=t("errors.emptyResponse");
    play(toolFailed?"failed":"waving");
  }catch(error){
    if(state.pendingApproval)await resolveApproval(false).catch(()=>{});
    textNode.textContent=t("errors.request",{message:error.message});row.classList.add("error");play("failed");
  }finally{
    state.busy=false;resize();prompt.focus();
  }
});
prompt.addEventListener("input",resize);prompt.addEventListener("keydown",e=>{if(e.isComposing||e.keyCode===229)return;if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();$("composer").requestSubmit()}});
$("newChat").onclick=async()=>{
  if(!await confirmAction({label:t("header.newChat"),message:t("header.newChatConfirm")}))return;
  if(state.pendingApproval)await resolveApproval(false).catch(()=>{});
  await api("/api/new",{clientId});
  [...messages.querySelectorAll(".message")].forEach(element=>element.remove());
  welcome.hidden=false;
  window.dispatchEvent(new CustomEvent("enchan:new-chat"));
  play("jumping");
};
$("ragToggle").onclick=()=>setRagPanel(!$("ragPanel").classList.contains("open"));
$("ragClose").onclick=()=>setRagPanel(false);
$("ragRefresh").onclick=()=>loadRagStatus({showError:true});
$("ragCancel").onclick=async()=>{try{await api("/api/rag/cancel",{});await loadRagStatus({showError:true})}catch(error){$("ragError").textContent=t("errors.request",{message:error.message})}};
$("ragDismiss").onclick=async()=>{try{await api("/api/rag/dismiss",{});await loadRagStatus({showError:true})}catch(error){$("ragError").textContent=t("errors.request",{message:error.message})}};
$("ragAdd").onclick=openRagRegistration;
$("confirmationAccept").onclick=()=>resolveConfirmation(true);
$("confirmationCancel").onclick=()=>resolveConfirmation(false);
$("confirmationDialog").addEventListener("wa-after-hide",()=>resolveConfirmation(false));
$("ragBrowse").onclick=selectRagDirectory;
$("ragRegisterForm").onsubmit=async event=>{event.preventDefault();const collectionId=$("ragCollectionId").value.trim(),title=$("ragTitle").value.trim(),description=$("ragDescription").value.trim(),path=$("ragDirectory").value.trim();if(!title||!description||(!collectionId&&!path)){$("ragRegisterError").textContent=t("rag.registrationRequired");return}try{await api(collectionId?"/api/rag/update":"/api/rag/register",collectionId?{collectionId,title,description}:{title,description,path});dialogs.close("ragRegisterDialog");await loadRagStatus({showError:true})}catch(error){$("ragRegisterError").textContent=t("errors.request",{message:error.message})}};
$("settings").onclick=()=>{dialogs.open("mascotDialog");editMascot(selectedMascot());$("previewAnimSelect").onchange=()=>{state.previewFrame=0;clearTimeout(state.previewTimer);updatePreviewCanvas()}};
$("addMascot").onclick=()=>editMascot(null);
$("mascotImage").onchange=async e=>{const file=e.target.files[0];if(!file)return;const url=URL.createObjectURL(file);previewImage=new Image();await new Promise((resolve,reject)=>{previewImage.onload=resolve;previewImage.onerror=reject;previewImage.src=url});URL.revokeObjectURL(url);const validationError=validatePetSheet(previewImage);$("sheetError").textContent=validationError;if(validationError){e.target.value="";state.imageData="";return}state.imageData=await new Promise(resolve=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.readAsDataURL(file)});$("sheetPreviewText").hidden=true;$("livePreviewCanvas").hidden=false;$("previewAnimSelect").hidden=false;clearTimeout(state.previewTimer);updatePreviewCanvas()};
$("mascotForm").onsubmit=async e=>{e.preventDefault();$("sheetError").textContent="";try{state.config=await api("/api/mascots",{id:$("mascotId").value,name:$("mascotEditName").value,description:$("mascotDescription").value,personality:$("mascotPersonality").value,image:state.imageData});renderMascotList();applyMascot();dialogs.close("mascotDialog");play("waving")}catch(error){$("sheetError").textContent=t("errors.request",{message:error.message})}};
$("mascotDialog").addEventListener("wa-after-hide",()=>{clearTimeout(state.previewTimer);state.previewTimer=null});
setRagPanel(localStorage.getItem("enchan.rag.open")==="1");
window.EnchanI18n.onChange(()=>{if(state.ragStatus)renderRagStatus(state.ragStatus)});
loadConfig().then(()=>loadRagStatus({showError:true})).catch(error=>addMessage("assistant",t("errors.init",{message:error.message}),true));setInterval(()=>loadRagStatus(),1500);resize();prompt.focus();

const mascotStage=document.querySelector(".mascot-stage");const mascotTrack=document.querySelector(".mascot-track");let mascotDragging=false,mascotGrabOffset=0,mascotLastPointerX=0;const mascotPositionKey="enchan.mascot.position";
function clampMascotPosition(value){return Math.max(0,Math.min(value,Math.max(0,mascotTrack.clientWidth-mascotStage.offsetWidth)))}
function setMascotPosition(value,save=false){const next=clampMascotPosition(value);mascotStage.style.left=next+"px";if(save)localStorage.setItem(mascotPositionKey,String(next))}
mascotStage.addEventListener("pointerdown",event=>{mascotDragging=true;mascotLastPointerX=event.clientX;mascotGrabOffset=event.clientX-mascotStage.getBoundingClientRect().left;mascotStage.setPointerCapture(event.pointerId);play("jumping",{loop:true})});
mascotStage.addEventListener("pointermove",event=>{if(!mascotDragging)return;const delta=event.clientX-mascotLastPointerX;mascotLastPointerX=event.clientX;const trackLeft=mascotTrack.getBoundingClientRect().left;setMascotPosition(event.clientX-trackLeft-mascotGrabOffset);if(Math.abs(delta)>=1)play(delta>0?"running-right":"running-left",{loop:true,restart:false})});
function finishMascotDrag(event){if(!mascotDragging)return;mascotDragging=false;setMascotPosition(parseFloat(mascotStage.style.left)||0,true);if(mascotStage.hasPointerCapture(event.pointerId))mascotStage.releasePointerCapture(event.pointerId);play("jumping")}
mascotStage.addEventListener("pointerup",finishMascotDrag);mascotStage.addEventListener("pointercancel",finishMascotDrag);window.addEventListener("resize",()=>setMascotPosition(parseFloat(mascotStage.style.left)||0));requestAnimationFrame(()=>setMascotPosition(Number(localStorage.getItem(mascotPositionKey))||0));
});
