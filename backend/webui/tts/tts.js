(function(){
  const $=id=>document.getElementById(id);
  const presets={browser:["127.0.0.1",0],bouyomi:["127.0.0.1",50080],voicevox:["127.0.0.1",50021],coeiroink:["127.0.0.1",50031],aivis:["127.0.0.1",10101],openai:["127.0.0.1",8000],http:["127.0.0.1",50021]};
  let settings=null,audio=null,audioUrl="",controller=null,externalTimer=null,mediaUnlocked=false;
  const t=(key,values={},fallback=key)=>window.EnchanI18n?.t(key,values,fallback)||fallback;
  const SILENT_AUDIO="data:audio/wav;base64,UklGRnQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YVAAAACAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgA==";
  async function jsonApi(path,body){
    const response=await fetch(path,{method:body?"POST":"GET",headers:body?{"Content-Type":"application/json"}:{},body:body?JSON.stringify(body):undefined});
    const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);return data;
  }
  function setError(message=""){$("ttsError").textContent=message}
  function updateButton(){
    $("ttsSettings").classList.toggle("is-enabled",!!settings?.enabled);
    $("ttsSettings").setAttribute("aria-pressed",String(!!settings?.enabled));
    $("ttsSettings").title=settings?.enabled?t("tts.status.enabled"):t("tts.status.disabled");
  }
  function providerFields(){
    const provider=$("ttsProvider").value;
    document.querySelectorAll("[data-tts-providers]").forEach(node=>{node.hidden=!node.dataset.ttsProviders.split(" ").includes(provider)});
  }
  function formSettings(){
    let headers={};const source=$("ttsHeaders").value.trim();if(source){try{headers=JSON.parse(source)}catch(_){throw new Error(t("tts.error.headers"))}}
    const provider=$("ttsProvider").value;return {enabled:$("ttsEnabled").checked,autoSpeak:$("ttsAutoSpeak").checked,provider,
      host:$("ttsHost").value.trim(),port:Number($("ttsPort").value),baseUrl:["openai","http"].includes($("ttsProvider").value)?$("ttsBaseUrl").value.trim():"",
      voice:provider==="browser"?$("ttsBrowserVoice").value:(provider==="openai"?$("ttsOpenAIVoice").value.trim():""),speaker:Number($("ttsSpeaker").value),model:$("ttsModel").value.trim(),
      format:$("ttsFormat").value,speed:Number($("ttsSpeed").value),instructions:$("ttsInstructions").value.trim(),
      apiKeyEnv:$("ttsApiKeyEnv").value.trim(),allowRemote:$("ttsAllowRemote").checked,path:$("ttsPath").value.trim(),
      method:$("ttsMethod").value,bodyFormat:$("ttsBodyFormat").value,textField:$("ttsTextField").value.trim(),
      responseMode:$("ttsResponseMode").value,headers};
  }
  function fillForm(value){
    settings=value;$("ttsEnabled").checked=!!value.enabled;$("ttsAutoSpeak").checked=!!value.autoSpeak;$("ttsProvider").value=value.provider;
    $("ttsHost").value=value.host;$("ttsPort").value=value.port;$("ttsBaseUrl").value=value.baseUrl;
    $("ttsSpeaker").value=value.speaker;$("ttsModel").value=value.model;$("ttsFormat").value=value.format;$("ttsSpeed").value=value.speed;
    $("ttsInstructions").value=value.instructions;$("ttsApiKeyEnv").value=value.apiKeyEnv;$("ttsAllowRemote").checked=!!value.allowRemote;
    $("ttsPath").value=value.path;$("ttsMethod").value=value.method;$("ttsBodyFormat").value=value.bodyFormat;
    $("ttsTextField").value=value.textField;$("ttsResponseMode").value=value.responseMode;$("ttsHeaders").value=Object.keys(value.headers||{}).length?JSON.stringify(value.headers,null,2):"";
    if(value.provider==="browser")setSelectOptions($("ttsBrowserVoice"),browserVoices(),value.voice);
    if(value.provider==="openai")$("ttsOpenAIVoice").value=value.voice||"alloy";
    if(["voicevox","coeiroink","aivis"].includes(value.provider))setSelectOptions($("ttsSpeaker"),[],value.speaker);
    providerFields();updateButton();
  }
  async function load(){const data=await jsonApi("/api/tts/status");fillForm(data.settings);return data.settings}
  async function save({close=false}={}){
    setError();const button=$("ttsSave");button.disabled=true;
    try{settings=await jsonApi("/api/tts/settings",{settings:formSettings()});fillForm(settings);if(close)window.EnchanDialogs.close("ttsDialog");return settings}
    catch(error){setError(t("tts.error.request",{message:error.message}));throw error}finally{button.disabled=false}
  }
  function setSelectOptions(select,items,selected=select.value){
    const requested=selected===null||selected===undefined||String(selected)===""?String(items[0]?.id??""):String(selected);
    select.replaceChildren();for(const item of items){const option=document.createElement("option");option.value=String(item.id);option.textContent=item.name;select.append(option)}
    if(requested&&!items.some(item=>String(item.id)===requested)){const option=document.createElement("option");option.value=requested;option.textContent=requested;select.prepend(option)}
    select.value=requested;
  }
  function browserVoices(){return (window.speechSynthesis?.getVoices?.()||[]).map(voice=>({id:voice.name,name:voice.name+" ("+voice.lang+")"}))}
  async function refreshVoices(){
    setError();try{
      await save();const provider=settings.provider;
      if(provider==="browser"){setSelectOptions($("ttsBrowserVoice"),browserVoices(),$("ttsBrowserVoice").value);return}
      const data=await jsonApi("/api/tts/voices");const selected=$("ttsSpeaker").value||String(data.voices?.[0]?.id??"");setSelectOptions($("ttsSpeaker"),data.voices||[],selected);
    }catch(error){setError(t("tts.error.request",{message:error.message}))}
  }
  function readableText(value){return String(value||"").replace(/```[\s\S]*?```/g," ").replace(/!?(?:\[([^\]]*)\])\([^)]*\)/g,"$1").replace(/https?:\/\/\S+/g," ").replace(/[`*_~#>]/g,"").replace(/\s+/g," ").trim().slice(0,10000)}
  function notify(type,detail={}){window.dispatchEvent(new CustomEvent(`enchan:tts-${type}`,{detail}))}
  function clearAudioUrl(){if(audioUrl){URL.revokeObjectURL(audioUrl);audioUrl=""}}
  function unlockPlayback(){
    if(mediaUnlocked)return;
    const player=audio||(audio=new Audio());
    player.src=SILENT_AUDIO;
    const attempt=player.play();
    if(attempt?.then)attempt.then(()=>{player.pause();player.removeAttribute("src");player.load();mediaUnlocked=true}).catch(()=>{});
    if(window.speechSynthesis&&window.SpeechSynthesisUtterance){
      const probe=new window.SpeechSynthesisUtterance(" ");probe.volume=0;window.speechSynthesis.speak(probe);
    }
  }
  function stop(){
    controller?.abort();controller=null;if(audio){audio.pause();clearAudioUrl();audio.removeAttribute("src");audio.load()}window.speechSynthesis?.cancel();clearTimeout(externalTimer);externalTimer=null;notify("end");
  }
  async function speak(rawText,{force=false}={}){
    if(!settings)await load();if(!force&&(!settings.enabled||!settings.autoSpeak))return;
    const text=readableText(rawText);if(!text)return;stop();notify("start");
    try{
      if(settings.provider==="browser"){if(!window.speechSynthesis||!window.SpeechSynthesisUtterance)throw new Error("Browser speech synthesis is not available.");
        const utterance=new window.SpeechSynthesisUtterance(text);const chosen=window.speechSynthesis.getVoices().find(item=>item.name===settings.voice);if(chosen)utterance.voice=chosen;
        utterance.rate=Math.min(4,Math.max(.25,settings.speed||1));utterance.onend=()=>notify("end");utterance.onerror=event=>notify("error",{message:event.error});window.speechSynthesis.speak(utterance);return;
      }
      controller=new AbortController();const response=await fetch("/api/tts/synthesize",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text}),signal:controller.signal});controller=null;
      const contentType=response.headers.get("Content-Type")||"";
      if(!response.ok){const problem=await response.json().catch(()=>({}));throw new Error(problem.error||`HTTP ${response.status}`)}
      if(contentType.includes("application/json")){
        const result=await response.json();if(result.externalPlayback){externalTimer=setTimeout(()=>notify("end"),Math.min(30000,Math.max(1500,text.length*125)));return}
        throw new Error(t("tts.error.noAudio"));
      }
      const blob=await response.blob();const player=audio||(audio=new Audio());clearAudioUrl();audioUrl=URL.createObjectURL(blob);player.src=audioUrl;player.onended=()=>{clearAudioUrl();notify("end")};player.onerror=()=>{clearAudioUrl();notify("error",{message:t("tts.error.playback")})};await player.play();
    }catch(error){if(error.name!=="AbortError"){setError(t("tts.error.request",{message:error.message}));notify("error",{message:error.message})}}
  }
  async function test(){try{await save();await speak(t("tts.testText"),{force:true})}catch(_){}}
  async function init(){
    await window.EnchanI18n.ready;document.addEventListener("pointerdown",unlockPlayback,{capture:true});$("ttsSettings").onclick=()=>{setError();window.EnchanDialogs.open("ttsDialog")};$("ttsForm").onsubmit=event=>{event.preventDefault();save({close:true}).catch(()=>{})};
    $("ttsProvider").onchange=()=>{const provider=$("ttsProvider").value;const [host,port]=presets[provider]||presets.http;$("ttsHost").value=host;$("ttsPort").value=port;if(!["openai","http"].includes(provider))$("ttsBaseUrl").value="";if(provider==="browser")setSelectOptions($("ttsBrowserVoice"),browserVoices(),$("ttsBrowserVoice").value);if(provider==="openai"&&!$("ttsOpenAIVoice").value)$("ttsOpenAIVoice").value="alloy";providerFields()};
    $("ttsRefreshVoices").onclick=refreshVoices;$("ttsTest").onclick=test;$("ttsStop").onclick=stop;
    window.addEventListener("enchan:new-chat",stop);window.EnchanI18n.onChange(updateButton);window.speechSynthesis?.addEventListener?.("voiceschanged",()=>{if($("ttsProvider").value==="browser")setSelectOptions($("ttsBrowserVoice"),browserVoices(),$("ttsBrowserVoice").value)});
    try{await load()}catch(error){setError(t("tts.error.request",{message:error.message}))}
  }
  window.EnchanTTS={speak,stop,reload:load,get settings(){return settings}};init();
})();
