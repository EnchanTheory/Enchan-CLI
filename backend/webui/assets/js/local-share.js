(function(){
  const $=id=>document.getElementById(id);
  const t=(key,values={},fallback=key)=>window.EnchanI18n?.t(key,values,fallback)||fallback;
  let password="";
  let busy=false;

  async function request(path,body){
    const response=await fetch(path,{method:body===undefined?"GET":"POST",headers:body===undefined?{}:{"Content-Type":"application/json"},body:body===undefined?undefined:JSON.stringify(body),cache:"no-store"});
    const data=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);
    return data;
  }

  function updateControls(active){
    $("localShareEnable").disabled=busy||active;
    $("localShareStop").disabled=busy||!active;
    $("localShareBannerStop").disabled=busy||!active;
  }

  function render(status){
    const active=Boolean(status.active);
    $("localShareDetails").hidden=!active;
    $("localShareIdle").hidden=active;
    $("localShareBanner").hidden=!active||document.body.classList.contains("mobile-share-client");
    $("localShareHeader").classList.toggle("is-active",active);
    document.querySelectorAll(".local-share-controller-only").forEach(element=>element.hidden=!status.controller);
    updateControls(active);
    if(!active){
      password="";
      $("localSharePassword").textContent="----";
      $("localShareQr").removeAttribute("src");
      if(status.stopReason&&status.stopReason!=="manual"){
        $("localShareError").textContent=t(`localShare.stopReason.${status.stopReason}`,{},status.stopReason);
      }
      return;
    }
    $("localShareUrl").textContent=status.url||t("localShare.active",{},"Active");
    $("localSharePassword").textContent=password||"••••";
    $("localShareDevice").textContent=status.deviceIp||t("localShare.waiting",{},"Waiting for a device");
    $("localShareCount").textContent=`${status.connectedCount||0}/${status.maxDevices||1}`;
    $("localShareBannerDevice").textContent=status.deviceIp?`${status.deviceIp} · ${status.connectedCount||0}/1`:`${status.connectedCount||0}/1`;
    if(status.url&&!$("localShareQr").getAttribute("src"))$("localShareQr").src=`/api/local-share/qr?v=${Date.now()}`;
    const network=status.network||{};
    const connection=network.connectionType?t(`localShare.connection.${network.connectionType}`,{},network.connectionType):"";
    const wirelessSecurity=network.connectionType==="wifi"?[network.authentication,network.cipher].filter(Boolean).join("/"):"";
    $("localShareNetwork").textContent=[connection,network.ssid,network.networkType,wirelessSecurity,network.ip].filter(Boolean).join(" · ");
  }

  async function refresh(){
    try{render(await request("/api/local-share/status"))}
    catch(error){if($("localShareDialog").open)$("localShareError").textContent=error.message}
  }

  async function setActive(active){
    if(busy)return;
    busy=true;
    $("localShareError").textContent="";
    updateControls(!$("localShareDetails").hidden);
    try{
      if(active){
        const status=await request("/api/local-share/start",{locale:window.EnchanI18n?.locale||"en"});
        password=status.password||"";
        render(status);
        await window.EnchanAppearance?.syncBackground?.();
      }else{
        await request("/api/local-share/stop",{});
        render({active:false,stopReason:"manual",controller:true});
      }
    }catch(error){
      $("localShareError").textContent=error.message;
    }finally{
      busy=false;
      updateControls(!$("localShareDetails").hidden);
    }
  }

  window.EnchanI18n.ready.then(()=>{
    const menuToggle=$("mobileMenuToggle");
    const menu=$("headerMenu");
    const closeMenu=()=>{menu.classList.remove("is-open");menuToggle.setAttribute("aria-expanded","false")};
    menuToggle.onclick=event=>{event.stopPropagation();const open=menu.classList.toggle("is-open");menuToggle.setAttribute("aria-expanded",String(open))};
    menu.addEventListener("click",event=>{if(event.target.closest("button"))closeMenu()});
    document.addEventListener("click",event=>{if(!event.target.closest("nav"))closeMenu()});
    document.addEventListener("keydown",event=>{if(event.key==="Escape")closeMenu()});
    $("localShareHeader").onclick=()=>window.EnchanDialogs.open($("localShareDialog"));
    $("localShareEnable").onclick=()=>setActive(true);
    $("localShareStop").onclick=()=>setActive(false);
    $("localShareBannerStop").onclick=()=>setActive(false);
    refresh();
    setInterval(refresh,3000);
  });
})();