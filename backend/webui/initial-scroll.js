(()=>{
  const composer=document.getElementById("composer");
  const newChat=document.getElementById("newChat");
  if(!composer)return;

  const originalScrollTo=window.scrollTo.bind(window);
  let isFirstMessage=true;
  let suppressSmoothScroll=false;

  window.scrollTo=(options,...args)=>{
    if(suppressSmoothScroll&&options&&typeof options==="object"&&options.behavior==="smooth"){
      return originalScrollTo({...options,behavior:"auto"},...args);
    }
    return originalScrollTo(options,...args);
  };

  composer.addEventListener("submit",()=>{
    if(!isFirstMessage)return;
    isFirstMessage=false;
    suppressSmoothScroll=true;
    setTimeout(()=>{suppressSmoothScroll=false},0);
  },true);

  newChat?.addEventListener("click",()=>{isFirstMessage=true},true);
})();
