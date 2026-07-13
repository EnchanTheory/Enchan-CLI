window.EnchanI18n.ready.then(()=>{
(()=>{
  const {t,onChange}=window.EnchanI18n;
  const status=document.getElementById("backendStatus");
  const label=document.getElementById("backendStatusText");
  if(!status||!label)return;

  let timer=null;
  let lastConnected=false;
  let currentState="checking";

  function setState(name){
    currentState=name;
    status.classList.remove("is-connected","is-disconnected","is-checking");
    status.classList.add(`is-${name}`);
    if(name==="connected"){
      label.textContent=t("status.connected");
      status.title=t("status.connectedTitle");
      lastConnected=true;
    }else if(name==="disconnected"){
      label.textContent=t("status.disconnected");
      status.title=t("status.disconnectedTitle");
      lastConnected=false;
    }else{
      label.textContent=t("status.checking");
      status.title=t("status.checkingTitle");
    }
    status.setAttribute("aria-label",status.title);
  }

  async function checkBackend(){
    const controller=new AbortController();
    const timeout=setTimeout(()=>controller.abort(),1800);
    try{
      const response=await fetch(`/api/config?health=${Date.now()}`,{method:"GET",cache:"no-store",signal:controller.signal,headers:{"Accept":"application/json"}});
      if(!response.ok)throw new Error(`HTTP ${response.status}`);
      const data=await response.json();
      if(!data||typeof data.backend!=="string")throw new Error("Invalid health response");
      setState("connected");
    }catch(_){setState("disconnected")}finally{clearTimeout(timeout)}
  }

  function schedule(){clearInterval(timer);timer=setInterval(checkBackend,3000)}
  onChange(()=>setState(currentState));
  setState("checking");
  checkBackend();
  schedule();
  window.addEventListener("pageshow",()=>{if(!lastConnected)setState("checking");checkBackend();schedule()});
  document.addEventListener("visibilitychange",()=>{if(!document.hidden)checkBackend()});
  window.addEventListener("pagehide",()=>clearInterval(timer));
})();
});
