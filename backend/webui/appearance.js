(()=>{
  const STORAGE_KEY="enchan.webui.theme";
  const FALLBACK_THEME="enchan-dark";
  const root=document.documentElement;
  const dialog=document.getElementById("appearanceDialog");
  const openButton=document.getElementById("appearanceSettings");
  const grid=document.getElementById("themeGrid");
  if(!dialog||!openButton||!grid)return;

  let manifest={default:FALLBACK_THEME,themes:[]};
  let selected=localStorage.getItem(STORAGE_KEY)||FALLBACK_THEME;

  function applyTheme(themeId,{persist=false}={}){
    const exists=manifest.themes.some(theme=>theme.id===themeId);
    selected=exists?themeId:(manifest.default||FALLBACK_THEME);
    root.dataset.theme=selected;
    if(persist)localStorage.setItem(STORAGE_KEY,selected);
    grid.querySelectorAll(".theme-card").forEach(card=>{
      const active=card.dataset.theme===selected;
      card.classList.toggle("active",active);
      card.setAttribute("aria-pressed",String(active));
    });
  }

  function renderThemes(){
    grid.replaceChildren();
    for(const theme of manifest.themes){
      const button=document.createElement("button");
      button.type="button";
      button.className="theme-card";
      button.dataset.theme=theme.id;
      button.setAttribute("aria-pressed","false");

      const swatches=document.createElement("span");
      swatches.className="theme-swatches";
      swatches.setAttribute("aria-hidden","true");
      for(const color of theme.swatches||[]){
        const dot=document.createElement("i");
        dot.style.background=color;
        swatches.appendChild(dot);
      }

      const copy=document.createElement("span");
      copy.className="theme-copy";
      const name=document.createElement("strong");
      name.textContent=theme.name||theme.id;
      const description=document.createElement("small");
      description.textContent=theme.description||"";
      copy.append(name,description);
      button.append(swatches,copy);
      button.addEventListener("click",()=>applyTheme(theme.id,{persist:true}));
      grid.appendChild(button);
    }
    applyTheme(selected);
  }

  async function loadManifest(){
    try{
      const response=await fetch(`/themes.json?v=${Date.now()}`,{cache:"no-store"});
      if(!response.ok)throw new Error(`HTTP ${response.status}`);
      const data=await response.json();
      if(!Array.isArray(data.themes)||!data.themes.length)throw new Error("No themes defined");
      manifest=data;
    }catch(_){
      manifest={
        default:FALLBACK_THEME,
        themes:[{id:FALLBACK_THEME,name:"Enchan Dark",description:"Original Enchan theme.",swatches:["#1d2021","#2a2b2b","#a59164"]}],
      };
    }
    renderThemes();
  }

  const saved=localStorage.getItem(STORAGE_KEY);
  root.dataset.theme=saved||FALLBACK_THEME;
  openButton.addEventListener("click",()=>dialog.showModal());
  loadManifest();
})();
