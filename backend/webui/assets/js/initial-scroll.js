(()=>{
  const composer=document.getElementById("composer");
  if(!composer)return;

  const originalScrollTo=window.scrollTo.bind(window);
  let isFirstMessage=true;
  let suppressInitialScroll=false;

  window.scrollTo=(options,...args)=>{
    if(suppressInitialScroll)return;
    return originalScrollTo(options,...args);
  };

  composer.addEventListener("submit",()=>{
    if(!isFirstMessage)return;
    isFirstMessage=false;
    suppressInitialScroll=true;
    requestAnimationFrame(()=>requestAnimationFrame(()=>{suppressInitialScroll=false}));
  },true);

  window.addEventListener("enchan:new-chat",()=>{isFirstMessage=true});
})();
