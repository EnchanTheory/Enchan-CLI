window.EnchanI18n.ready.then(()=>{
(()=>{
  const {t,onChange}=window.EnchanI18n;
  const THEME_KEY="enchan.webui.theme";
  const BACKGROUND_SETTINGS_KEY="enchan.webui.background.settings";
  const FALLBACK_THEME="enchan-dark";
  const DB_NAME="enchan-webui";
  const DB_VERSION=1;
  const STORE_NAME="appearance";
  const IMAGE_KEY="background-image";
  const MAX_IMAGE_BYTES=20*1024*1024;
  const root=document.documentElement;
  const dialog=document.getElementById("appearanceDialog");
  const openButton=document.getElementById("appearanceSettings");
  const grid=document.getElementById("themeGrid");
  const imageInput=document.getElementById("backgroundImage");
  const removeButton=document.getElementById("removeBackground");
  const preview=document.getElementById("backgroundPreview");
  const previewText=document.getElementById("backgroundPreviewText");
  const darkness=document.getElementById("backgroundDarkness");
  const darknessValue=document.getElementById("backgroundDarknessValue");
  const blur=document.getElementById("backgroundBlur");
  const blurValue=document.getElementById("backgroundBlurValue");
  const position=document.getElementById("backgroundPosition");
  const error=document.getElementById("backgroundError");
  if(!dialog||!openButton||!grid)return;

  let manifest={default:FALLBACK_THEME,themes:[]};
  let selected=localStorage.getItem(THEME_KEY)||FALLBACK_THEME;
  let backgroundUrl="";
  let backgroundSettings=loadBackgroundSettings();

  function loadBackgroundSettings(){
    try{
      const data=JSON.parse(localStorage.getItem(BACKGROUND_SETTINGS_KEY)||"{}");
      return {darkness:clamp(Number(data.darkness)||55,30,85),blur:clamp(Number(data.blur)||2,0,12),position:["center","top","bottom","left","right"].includes(data.position)?data.position:"center"};
    }catch(_){return {darkness:55,blur:2,position:"center"}}
  }
  function clamp(value,min,max){return Math.min(max,Math.max(min,value))}
  function saveBackgroundSettings(){localStorage.setItem(BACKGROUND_SETTINGS_KEY,JSON.stringify(backgroundSettings))}
  function openDatabase(){return new Promise((resolve,reject)=>{const request=indexedDB.open(DB_NAME,DB_VERSION);request.onupgradeneeded=()=>{const db=request.result;if(!db.objectStoreNames.contains(STORE_NAME))db.createObjectStore(STORE_NAME)};request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error||new Error(t("appearance.error.openStorage")))})}
  async function readStoredImage(){const db=await openDatabase();try{return await new Promise((resolve,reject)=>{const tx=db.transaction(STORE_NAME,"readonly");const request=tx.objectStore(STORE_NAME).get(IMAGE_KEY);request.onsuccess=()=>resolve(request.result||null);request.onerror=()=>reject(request.error)})}finally{db.close()}}
  async function writeStoredImage(blob){const db=await openDatabase();try{await new Promise((resolve,reject)=>{const tx=db.transaction(STORE_NAME,"readwrite");tx.objectStore(STORE_NAME).put(blob,IMAGE_KEY);tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error||new Error(t("appearance.error.cancelled")))})}finally{db.close()}}
  async function deleteStoredImage(){const db=await openDatabase();try{await new Promise((resolve,reject)=>{const tx=db.transaction(STORE_NAME,"readwrite");tx.objectStore(STORE_NAME).delete(IMAGE_KEY);tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error)})}finally{db.close()}}

  function applyTheme(themeId,{persist=false}={}){
    const exists=manifest.themes.some(theme=>theme.id===themeId);selected=exists?themeId:(manifest.default||FALLBACK_THEME);root.dataset.theme=selected;if(persist)localStorage.setItem(THEME_KEY,selected);
    grid.querySelectorAll(".theme-card").forEach(card=>{const active=card.dataset.theme===selected;card.classList.toggle("active",active);card.setAttribute("aria-pressed",String(active))});
  }
  function renderThemes(){
    grid.replaceChildren();
    for(const theme of manifest.themes){
      const button=document.createElement("button");button.type="button";button.className="theme-card";button.dataset.theme=theme.id;button.setAttribute("aria-pressed","false");
      const swatches=document.createElement("span");swatches.className="theme-swatches";swatches.setAttribute("aria-hidden","true");for(const color of theme.swatches||[]){const dot=document.createElement("i");dot.style.background=color;swatches.appendChild(dot)}
      const copy=document.createElement("span");copy.className="theme-copy";const name=document.createElement("strong");name.textContent=t(`themes.${theme.id}.name`,{},theme.name||theme.id);const description=document.createElement("small");description.textContent=t(`themes.${theme.id}.description`,{},theme.description||"");copy.append(name,description);button.append(swatches,copy);button.addEventListener("click",()=>applyTheme(theme.id,{persist:true}));grid.appendChild(button);
    }
    applyTheme(selected);
  }
  async function loadManifest(){
    try{const response=await fetch(`/data/themes.json?v=${Date.now()}`,{cache:"no-store"});if(!response.ok)throw new Error(`HTTP ${response.status}`);const data=await response.json();if(!Array.isArray(data.themes)||!data.themes.length)throw new Error(t("appearance.error.noThemes"));manifest=data}
    catch(_){manifest={default:FALLBACK_THEME,themes:[{id:FALLBACK_THEME,name:"Enchan Dark",description:"",swatches:["#1d2021","#2a2b2b","#a59164"]}]}}
    renderThemes();
  }
  function setControlsEnabled(enabled){for(const control of [darkness,blur,position,removeButton])if(control)control.disabled=!enabled}
  function applyBackground(){
    const enabled=Boolean(backgroundUrl);root.classList.toggle("has-custom-background",enabled);root.style.setProperty("--background-image",enabled?`url("${backgroundUrl}")`:"none");root.style.setProperty("--background-darkness",String(backgroundSettings.darkness/100));root.style.setProperty("--background-blur",`${backgroundSettings.blur}px`);root.style.setProperty("--background-position",backgroundSettings.position);
    if(preview){preview.classList.toggle("has-image",enabled);preview.style.backgroundImage=enabled?`linear-gradient(rgba(12,14,15,${backgroundSettings.darkness/100}),rgba(12,14,15,${backgroundSettings.darkness/100})),url("${backgroundUrl}")`:"none"}
    if(previewText)previewText.textContent=t(enabled?"appearance.background.selected":"appearance.background.none");if(darkness)darkness.value=String(backgroundSettings.darkness);if(darknessValue)darknessValue.value=`${backgroundSettings.darkness}%`;if(blur)blur.value=String(backgroundSettings.blur);if(blurValue)blurValue.value=`${backgroundSettings.blur}px`;if(position)position.value=backgroundSettings.position;setControlsEnabled(enabled);
  }
  function replaceBackgroundUrl(blob){if(backgroundUrl)URL.revokeObjectURL(backgroundUrl);backgroundUrl=blob?URL.createObjectURL(blob):"";applyBackground()}
  async function loadBackground(){try{const blob=await readStoredImage();if(blob instanceof Blob)replaceBackgroundUrl(blob);else applyBackground()}catch(_){applyBackground()}}

  imageInput?.addEventListener("change",async event=>{const file=event.target.files?.[0];if(!file)return;error.textContent="";if(!["image/png","image/jpeg","image/webp"].includes(file.type)){error.textContent=t("appearance.error.invalidType");event.target.value="";return}if(file.size>MAX_IMAGE_BYTES){error.textContent=t("appearance.error.tooLarge");event.target.value="";return}try{await writeStoredImage(file);replaceBackgroundUrl(file)}catch(err){error.textContent=err?.message||t("appearance.error.store")}finally{event.target.value=""}});
  removeButton?.addEventListener("click",async()=>{error.textContent="";try{await deleteStoredImage();replaceBackgroundUrl(null)}catch(err){error.textContent=err?.message||t("appearance.error.remove")}});
  darkness?.addEventListener("input",()=>{backgroundSettings.darkness=clamp(Number(darkness.value),30,85);saveBackgroundSettings();applyBackground()});
  blur?.addEventListener("input",()=>{backgroundSettings.blur=clamp(Number(blur.value),0,12);saveBackgroundSettings();applyBackground()});
  position?.addEventListener("change",()=>{backgroundSettings.position=position.value;saveBackgroundSettings();applyBackground()});

  const saved=localStorage.getItem(THEME_KEY);root.dataset.theme=saved||FALLBACK_THEME;openButton.addEventListener("click",()=>window.EnchanDialogs.open(dialog));window.addEventListener("pagehide",()=>{if(backgroundUrl)URL.revokeObjectURL(backgroundUrl)});onChange(()=>{renderThemes();applyBackground()});loadManifest();loadBackground();
})();
});
