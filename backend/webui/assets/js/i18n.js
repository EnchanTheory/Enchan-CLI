(()=>{
  const STORAGE_KEY="enchan.webui.locale";
  const MANIFEST_URL="/locales/manifest.json";
  const listeners=new Set();
  let manifest={default:"en",locales:[]};
  let locale="en";
  let fallback={};
  let messages={};

  async function fetchJson(url){
    const response=await fetch(`${url}?v=${Date.now()}`,{cache:"no-store"});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  function localeEntry(name){
    const normalized=String(name||"").toLowerCase();
    if(!normalized)return null;
    const exact=manifest.locales.find(entry=>entry.code.toLowerCase()===normalized);
    if(exact)return exact;
    const base=normalized.split("-")[0];
    return manifest.locales.find(entry=>entry.code.toLowerCase().split("-")[0]===base)||null;
  }

  function browserLocale(){
    for(const value of navigator.languages||[navigator.language||manifest.default]){
      const entry=localeEntry(value);
      if(entry)return entry.code;
    }
    return manifest.default;
  }

  function interpolate(text,values={}){
    let result=String(text??"");
    for(const [name,value] of Object.entries(values))result=result.replaceAll(`{${name}}`,String(value));
    return result;
  }

  function t(key,values={},defaultValue=""){
    const value=messages[key]??fallback[key]??defaultValue??key;
    return interpolate(value,values);
  }

  async function loadManifest(){
    const data=await fetchJson(MANIFEST_URL);
    const locales=Array.isArray(data.locales)?data.locales.filter(entry=>entry&&/^[a-z0-9-]+$/i.test(entry.code)&&/^[a-z0-9_.-]+\.json$/i.test(entry.file)&&entry.label):[];
    if(!locales.length)throw new Error("No locales defined");
    const defaultEntry=locales.find(entry=>entry.code===data.default)||locales[0];
    return {default:defaultEntry.code,locales};
  }

  function renderLanguageOptions(){
    const select=document.getElementById("languageSelect");
    if(!select)return;
    select.querySelectorAll("wa-option").forEach(option=>option.remove());
    for(const entry of manifest.locales){
      const option=document.createElement("wa-option");
      option.value=entry.code;
      option.lang=entry.code;
      option.textContent=entry.label;
      select.appendChild(option);
    }
    select.value=locale;
  }

  function apply(root=document){
    const entry=localeEntry(locale);
    document.documentElement.lang=locale;
    document.documentElement.dir=entry?.dir==="rtl"?"rtl":"ltr";
    root.querySelectorAll?.("[data-i18n]").forEach(element=>{element.textContent=t(element.dataset.i18n)});
    root.querySelectorAll?.("[data-i18n-placeholder]").forEach(element=>{element.placeholder=t(element.dataset.i18nPlaceholder)});
    root.querySelectorAll?.("[data-i18n-title]").forEach(element=>{const value=t(element.dataset.i18nTitle);element.title=value;element.setAttribute("aria-label",value)});
    root.querySelectorAll?.("[data-i18n-aria-label]").forEach(element=>element.setAttribute("aria-label",t(element.dataset.i18nAriaLabel)));
    const select=document.getElementById("languageSelect");
    if(select&&select.value!==locale)select.value=locale;
  }

  async function setLocale(name,{persist=true}={}){
    const entry=localeEntry(name)||localeEntry(manifest.default)||manifest.locales[0];
    messages=entry.code===manifest.default?fallback:await fetchJson(`/locales/${entry.file}`).catch(()=>fallback);
    locale=entry.code;
    if(persist)localStorage.setItem(STORAGE_KEY,locale);
    apply();
    for(const listener of listeners)listener(locale);
    window.dispatchEvent(new CustomEvent("enchan:locale-changed",{detail:{locale}}));
    return locale;
  }

  function onChange(listener){listeners.add(listener);return()=>listeners.delete(listener)}

  const ready=(async()=>{
    await import("/vendor/webawesome/select.js");
    await Promise.all([customElements.whenDefined("wa-select"),customElements.whenDefined("wa-option")]);
    manifest=await loadManifest();
    locale=manifest.default;
    fallback=await fetchJson(`/locales/${localeEntry(manifest.default).file}`);
    renderLanguageOptions();
    const saved=localStorage.getItem(STORAGE_KEY);
    await setLocale(localeEntry(saved)?.code||browserLocale(),{persist:false});
    const select=document.getElementById("languageSelect");
    select?.addEventListener("change",()=>setLocale(select.value));
    return locale;
  })().catch(error=>{
    console.error("Failed to initialize localization",error);
    apply();
    return locale;
  });

  window.EnchanI18n={ready,t,apply,setLocale,onChange,get locale(){return locale},get supported(){return manifest.locales.map(entry=>entry.code)}};
})();
