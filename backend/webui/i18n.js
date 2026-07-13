(()=>{
  const STORAGE_KEY="enchan.webui.locale";
  const SUPPORTED=["en","ja"];
  const listeners=new Set();
  let locale="en";
  let fallback={};
  let messages={};

  function browserLocale(){
    const values=navigator.languages||[navigator.language||"en"];
    return values.some(value=>String(value).toLowerCase().startsWith("ja"))?"ja":"en";
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

  async function loadLocale(name){
    const response=await fetch(`/locales/${name}.json?v=${Date.now()}`,{cache:"no-store"});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  function apply(root=document){
    document.documentElement.lang=locale;
    root.querySelectorAll?.("[data-i18n]").forEach(element=>{element.textContent=t(element.dataset.i18n)});
    root.querySelectorAll?.("[data-i18n-placeholder]").forEach(element=>{element.placeholder=t(element.dataset.i18nPlaceholder)});
    root.querySelectorAll?.("[data-i18n-title]").forEach(element=>{const value=t(element.dataset.i18nTitle);element.title=value;element.setAttribute("aria-label",value)});
    root.querySelectorAll?.("[data-i18n-aria-label]").forEach(element=>element.setAttribute("aria-label",t(element.dataset.i18nAriaLabel)));
    const select=document.getElementById("languageSelect");
    if(select&&select.value!==locale)select.value=locale;
  }

  async function setLocale(name,{persist=true}={}){
    const next=SUPPORTED.includes(name)?name:"en";
    messages=next==="en"?fallback:await loadLocale(next).catch(()=>fallback);
    locale=next;
    if(persist)localStorage.setItem(STORAGE_KEY,locale);
    apply();
    for(const listener of listeners)listener(locale);
    window.dispatchEvent(new CustomEvent("enchan:locale-changed",{detail:{locale}}));
    return locale;
  }

  function onChange(listener){listeners.add(listener);return()=>listeners.delete(listener)}

  const ready=(async()=>{
    fallback=await loadLocale("en");
    const saved=localStorage.getItem(STORAGE_KEY);
    await setLocale(SUPPORTED.includes(saved)?saved:browserLocale(),{persist:false});
    const select=document.getElementById("languageSelect");
    if(select)select.addEventListener("change",event=>setLocale(event.target.value));
    return locale;
  })().catch(error=>{
    console.error("Failed to initialize localization",error);
    apply();
    return locale;
  });

  window.EnchanI18n={ready,t,apply,setLocale,onChange,get locale(){return locale},supported:SUPPORTED};
})();
