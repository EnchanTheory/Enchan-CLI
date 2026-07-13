(()=>{
  const ICON_SIZE=64;
  const SOURCE_SIZE=192;

  function setFavicon(image){
    const canvas=document.createElement("canvas");
    canvas.width=ICON_SIZE;
    canvas.height=ICON_SIZE;
    const ctx=canvas.getContext("2d");
    if(!ctx)return;
    ctx.clearRect(0,0,ICON_SIZE,ICON_SIZE);
    ctx.imageSmoothingEnabled=true;
    ctx.imageSmoothingQuality="high";
    ctx.drawImage(image,0,0,SOURCE_SIZE,SOURCE_SIZE,0,0,ICON_SIZE,ICON_SIZE);

    let link=document.querySelector('link[rel="icon"]');
    if(!link){
      link=document.createElement("link");
      link.rel="icon";
      document.head.appendChild(link);
    }
    link.type="image/png";
    link.href=canvas.toDataURL("image/png");
  }

  async function refreshFavicon(){
    try{
      const response=await fetch("/api/config",{cache:"no-store"});
      if(!response.ok)return;
      const config=await response.json();
      const mascot=config.mascots?.find(item=>item.id===config.selectedMascot);
      if(!mascot?.spritesheet)return;

      const image=new Image();
      image.onload=()=>setFavicon(image);
      image.src=`/api/mascots/${encodeURIComponent(mascot.id)}?favicon=${Date.now()}`;
    }catch(_){
      // Favicon generation is optional and must never affect the Web UI.
    }
  }

  refreshFavicon();
  document.getElementById("mascotDialog")?.addEventListener("close",refreshFavicon);
})();
