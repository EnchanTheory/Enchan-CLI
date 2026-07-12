(()=>{
  const status=document.getElementById("backendStatus");
  const label=document.getElementById("backendStatusText");
  if(!status||!label)return;

  const connectedLabel="Local";
  const disconnectedLabel="Disconnected";
  const checkingLabel="Checking";
  let timer=null;
  let lastConnected=false;

  function setState(name){
    status.classList.remove("is-connected","is-disconnected","is-checking");
    status.classList.add(`is-${name}`);
    if(name==="connected"){
      label.textContent=connectedLabel;
      status.title="Local backend connected";
      lastConnected=true;
    }else if(name==="disconnected"){
      label.textContent=disconnectedLabel;
      status.title="Local backend disconnected";
      lastConnected=false;
    }else{
      label.textContent=checkingLabel;
      status.title="Checking local backend connection";
    }
  }

  async function checkBackend(){
    const controller=new AbortController();
    const timeout=setTimeout(()=>controller.abort(),1800);
    try{
      const response=await fetch(`/api/config?health=${Date.now()}`,{
        method:"GET",
        cache:"no-store",
        signal:controller.signal,
        headers:{"Accept":"application/json"},
      });
      if(!response.ok)throw new Error(`HTTP ${response.status}`);
      const data=await response.json();
      if(!data||typeof data.backend!=="string")throw new Error("Invalid health response");
      setState("connected");
    }catch(_){
      setState("disconnected");
    }finally{
      clearTimeout(timeout);
    }
  }

  function schedule(){
    clearInterval(timer);
    timer=setInterval(checkBackend,3000);
  }

  setState("checking");
  checkBackend();
  schedule();
  window.addEventListener("pageshow",()=>{if(!lastConnected)setState("checking");checkBackend();schedule()});
  document.addEventListener("visibilitychange",()=>{if(!document.hidden)checkBackend()});
  window.addEventListener("pagehide",()=>clearInterval(timer));
})();
