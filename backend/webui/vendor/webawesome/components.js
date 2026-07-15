/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var jt=globalThis,Kt=jt.trustedTypes,oo=Kt?Kt.createPolicy("lit-html",{createHTML:t=>t}):void 0,Le="$lit$",nt=`lit$${Math.random().toFixed(9).slice(2)}$`,_e="?"+nt,Mr=`<${_e}>`,xt=document,It=()=>xt.createComment(""),Bt=t=>t===null||typeof t!="object"&&typeof t!="function",Ee=Array.isArray,lo=t=>Ee(t)||typeof t?.[Symbol.iterator]=="function",xe=`[ 	
\f\r]`,Ft=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,ro=/-->/g,io=/>/g,bt=RegExp(`>|${xe}(?:([^\\s"'>=/]+)(${xe}*=${xe}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),ao=/'/g,so=/"/g,co=/^(?:script|style|textarea|title)$/i,Ae=t=>(e,...o)=>({_$litType$:t,strings:e,values:o}),E=Ae(1),uo=Ae(2),ho=Ae(3),U=Symbol.for("lit-noChange"),$=Symbol.for("lit-nothing"),no=new WeakMap,yt=xt.createTreeWalker(xt,129);function po(t,e){if(!Ee(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return oo!==void 0?oo.createHTML(e):e}var fo=(t,e)=>{let o=t.length-1,r=[],i,a=e===2?"<svg>":e===3?"<math>":"",s=Ft;for(let n=0;n<o;n++){let c=t[n],u,h,p=-1,m=0;for(;m<c.length&&(s.lastIndex=m,h=s.exec(c),h!==null);)m=s.lastIndex,s===Ft?h[1]==="!--"?s=ro:h[1]!==void 0?s=io:h[2]!==void 0?(co.test(h[2])&&(i=RegExp("</"+h[2],"g")),s=bt):h[3]!==void 0&&(s=bt):s===bt?h[0]===">"?(s=i??Ft,p=-1):h[1]===void 0?p=-2:(p=s.lastIndex-h[2].length,u=h[1],s=h[3]===void 0?bt:h[3]==='"'?so:ao):s===so||s===ao?s=bt:s===ro||s===io?s=Ft:(s=bt,i=void 0);let f=s===bt&&t[n+1].startsWith("/>")?" ":"";a+=s===Ft?c+Mr:p>=0?(r.push(u),c.slice(0,p)+Le+c.slice(p)+nt+f):c+nt+(p===-2?n:f)}return[po(t,a+(t[o]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),r]},Ce=class mo{constructor({strings:e,_$litType$:o},r){let i;this.parts=[];let a=0,s=0,n=e.length-1,c=this.parts,[u,h]=fo(e,o);if(this.el=mo.createElement(u,r),yt.currentNode=this.el.content,o===2||o===3){let p=this.el.content.firstChild;p.replaceWith(...p.childNodes)}for(;(i=yt.nextNode())!==null&&c.length<n;){if(i.nodeType===1){if(i.hasAttributes())for(let p of i.getAttributeNames())if(p.endsWith(Le)){let m=h[s++],f=i.getAttribute(p).split(nt),v=/([.?@])?(.*)/.exec(m);c.push({type:1,index:a,name:v[2],strings:f,ctor:v[1]==="."?wo:v[1]==="?"?bo:v[1]==="@"?yo:qt}),i.removeAttribute(p)}else p.startsWith(nt)&&(c.push({type:6,index:a}),i.removeAttribute(p));if(co.test(i.tagName)){let p=i.textContent.split(nt),m=p.length-1;if(m>0){i.textContent=Kt?Kt.emptyScript:"";for(let f=0;f<m;f++)i.append(p[f],It()),yt.nextNode(),c.push({type:2,index:++a});i.append(p[m],It())}}}else if(i.nodeType===8)if(i.data===_e)c.push({type:2,index:a});else{let p=-1;for(;(p=i.data.indexOf(nt,p+1))!==-1;)c.push({type:7,index:a}),p+=nt.length-1}a++}}static createElement(e,o){let r=xt.createElement("template");return r.innerHTML=e,r}};function Ct(t,e,o=t,r){if(e===U)return e;let i=r!==void 0?o._$Co?.[r]:o._$Cl,a=Bt(e)?void 0:e._$litDirective$;return i?.constructor!==a&&(i?._$AO?.(!1),a===void 0?i=void 0:(i=new a(t),i._$AT(t,o,r)),r!==void 0?(o._$Co??(o._$Co=[]))[r]=i:o._$Cl=i),i!==void 0&&(e=Ct(t,i._$AS(t,e.values),i,r)),e}var vo=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:o}=this._$AD,r=(t?.creationScope??xt).importNode(e,!0);yt.currentNode=r;let i=yt.nextNode(),a=0,s=0,n=o[0];for(;n!==void 0;){if(a===n.index){let c;n.type===2?c=new Yt(i,i.nextSibling,this,t):n.type===1?c=new n.ctor(i,n.name,n.strings,this,t):n.type===6&&(c=new xo(i,this,t)),this._$AV.push(c),n=o[++s]}a!==n?.index&&(i=yt.nextNode(),a++)}return yt.currentNode=xt,r}p(t){let e=0;for(let o of this._$AV)o!==void 0&&(o.strings!==void 0?(o._$AI(t,o,e),e+=o.strings.length-2):o._$AI(t[e])),e++}},Yt=class go{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,o,r,i){this.type=2,this._$AH=$,this._$AN=void 0,this._$AA=e,this._$AB=o,this._$AM=r,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode,o=this._$AM;return o!==void 0&&e?.nodeType===11&&(e=o.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,o=this){e=Ct(this,e,o),Bt(e)?e===$||e==null||e===""?(this._$AH!==$&&this._$AR(),this._$AH=$):e!==this._$AH&&e!==U&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):lo(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==$&&Bt(this._$AH)?this._$AA.nextSibling.data=e:this.T(xt.createTextNode(e)),this._$AH=e}$(e){let{values:o,_$litType$:r}=e,i=typeof r=="number"?this._$AC(e):(r.el===void 0&&(r.el=Ce.createElement(po(r.h,r.h[0]),this.options)),r);if(this._$AH?._$AD===i)this._$AH.p(o);else{let a=new vo(i,this),s=a.u(this.options);a.p(o),this.T(s),this._$AH=a}}_$AC(e){let o=no.get(e.strings);return o===void 0&&no.set(e.strings,o=new Ce(e)),o}k(e){Ee(this._$AH)||(this._$AH=[],this._$AR());let o=this._$AH,r,i=0;for(let a of e)i===o.length?o.push(r=new go(this.O(It()),this.O(It()),this,this.options)):r=o[i],r._$AI(a),i++;i<o.length&&(this._$AR(r&&r._$AB.nextSibling,i),o.length=i)}_$AR(e=this._$AA.nextSibling,o){for(this._$AP?.(!1,!0,o);e&&e!==this._$AB;){let r=e.nextSibling;e.remove(),e=r}}setConnected(e){this._$AM===void 0&&(this._$Cv=e,this._$AP?.(e))}},qt=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,o,r,i){this.type=1,this._$AH=$,this._$AN=void 0,this.element=t,this.name=e,this._$AM=r,this.options=i,o.length>2||o[0]!==""||o[1]!==""?(this._$AH=Array(o.length-1).fill(new String),this.strings=o):this._$AH=$}_$AI(t,e=this,o,r){let i=this.strings,a=!1;if(i===void 0)t=Ct(this,t,e,0),a=!Bt(t)||t!==this._$AH&&t!==U,a&&(this._$AH=t);else{let s=t,n,c;for(t=i[0],n=0;n<i.length-1;n++)c=Ct(this,s[o+n],e,n),c===U&&(c=this._$AH[n]),a||(a=!Bt(c)||c!==this._$AH[n]),c===$?t=$:t!==$&&(t+=(c??"")+i[n+1]),this._$AH[n]=c}a&&!r&&this.j(t)}j(t){t===$?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},wo=class extends qt{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===$?void 0:t}},bo=class extends qt{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==$)}},yo=class extends qt{constructor(t,e,o,r,i){super(t,e,o,r,i),this.type=5}_$AI(t,e=this){if((t=Ct(this,t,e,0)??$)===U)return;let o=this._$AH,r=t===$&&o!==$||t.capture!==o.capture||t.once!==o.once||t.passive!==o.passive,i=t!==$&&(o===$||r);r&&this.element.removeEventListener(this.name,this,o),i&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},xo=class{constructor(t,e,o){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=o}get _$AU(){return this._$AM._$AU}_$AI(t){Ct(this,t)}},Co={M:Le,P:nt,A:_e,C:1,L:fo,R:vo,D:lo,V:Ct,I:Yt,H:qt,N:bo,U:yo,B:wo,F:xo},Tr=jt.litHtmlPolyfillSupport;Tr?.(Ce,Yt),(jt.litHtmlVersions??(jt.litHtmlVersions=[])).push("3.3.0");var Lo=(t,e,o)=>{let r=o?.renderBefore??e,i=r._$litPart$;if(i===void 0){let a=o?.renderBefore??null;r._$litPart$=i=new Yt(e.insertBefore(It(),a),a,void 0,o??{})}return i._$AI(t),i};/*! Bundled license information:

lit-html/lit-html.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*//*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Xt=globalThis,$e=Xt.ShadowRoot&&(Xt.ShadyCSS===void 0||Xt.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,Se=Symbol(),_o=new WeakMap,So=class{constructor(t,e,o){if(this._$cssResult$=!0,o!==Se)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if($e&&t===void 0){let o=e!==void 0&&e.length===1;o&&(t=_o.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),o&&_o.set(e,t))}return t}toString(){return this.cssText}},Rr=t=>new So(typeof t=="string"?t:t+"",void 0,Se),A=(t,...e)=>{let o=t.length===1?t[0]:e.reduce(((r,i,a)=>r+(s=>{if(s._$cssResult$===!0)return s.cssText;if(typeof s=="number")return s;throw Error("Value passed to 'css' function must be a 'css' function result: "+s+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+t[a+1]),t[0]);return new So(o,t,Se)},Dr=(t,e)=>{if($e)t.adoptedStyleSheets=e.map((o=>o instanceof CSSStyleSheet?o:o.styleSheet));else for(let o of e){let r=document.createElement("style"),i=Xt.litNonce;i!==void 0&&r.setAttribute("nonce",i),r.textContent=o.cssText,t.appendChild(r)}},Eo=$e?t=>t:t=>t instanceof CSSStyleSheet?(e=>{let o="";for(let r of e.cssRules)o+=r.cssText;return Rr(o)})(t):t,{is:Fr,defineProperty:Ir,getOwnPropertyDescriptor:Br,getOwnPropertyNames:qr,getOwnPropertySymbols:Vr,getPrototypeOf:Nr}=Object,$t=globalThis,Ao=$t.trustedTypes,Hr=Ao?Ao.emptyScript:"",Ur=$t.reactiveElementPolyfillSupport,Vt=(t,e)=>t,Nt={toAttribute(t,e){switch(e){case Boolean:t=t?Hr:null;break;case Object:case Array:t=t==null?t:JSON.stringify(t)}return t},fromAttribute(t,e){let o=t;switch(e){case Boolean:o=t!==null;break;case Number:o=t===null?null:Number(t);break;case Object:case Array:try{o=JSON.parse(t)}catch{o=null}}return o}},Gt=(t,e)=>!Fr(t,e),$o={attribute:!0,type:String,converter:Nt,reflect:!1,useDefault:!1,hasChanged:Gt};Symbol.metadata??(Symbol.metadata=Symbol("metadata")),$t.litPropertyMetadata??($t.litPropertyMetadata=new WeakMap);var Et=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??(this.l=[])).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=$o){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let o=Symbol(),r=this.getPropertyDescriptor(t,o,e);r!==void 0&&Ir(this.prototype,t,r)}}static getPropertyDescriptor(t,e,o){let{get:r,set:i}=Br(this.prototype,t)??{get(){return this[e]},set(a){this[e]=a}};return{get:r,set(a){let s=r?.call(this);i?.call(this,a),this.requestUpdate(t,s,o)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??$o}static _$Ei(){if(this.hasOwnProperty(Vt("elementProperties")))return;let t=Nr(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(Vt("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(Vt("properties"))){let e=this.properties,o=[...qr(e),...Vr(e)];for(let r of o)this.createProperty(r,e[r])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[o,r]of e)this.elementProperties.set(o,r)}this._$Eh=new Map;for(let[e,o]of this.elementProperties){let r=this._$Eu(e,o);r!==void 0&&this._$Eh.set(r,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let o=new Set(t.flat(1/0).reverse());for(let r of o)e.unshift(Eo(r))}else t!==void 0&&e.push(Eo(t));return e}static _$Eu(t,e){let o=e.attribute;return o===!1?void 0:typeof o=="string"?o:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise((t=>this.enableUpdating=t)),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach((t=>t(this)))}addController(t){(this._$EO??(this._$EO=new Set)).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let o of e.keys())this.hasOwnProperty(o)&&(t.set(o,this[o]),delete this[o]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Dr(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),this._$EO?.forEach((t=>t.hostConnected?.()))}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach((t=>t.hostDisconnected?.()))}attributeChangedCallback(t,e,o){this._$AK(t,o)}_$ET(t,e){let o=this.constructor.elementProperties.get(t),r=this.constructor._$Eu(t,o);if(r!==void 0&&o.reflect===!0){let i=(o.converter?.toAttribute!==void 0?o.converter:Nt).toAttribute(e,o.type);this._$Em=t,i==null?this.removeAttribute(r):this.setAttribute(r,i),this._$Em=null}}_$AK(t,e){let o=this.constructor,r=o._$Eh.get(t);if(r!==void 0&&this._$Em!==r){let i=o.getPropertyOptions(r),a=typeof i.converter=="function"?{fromAttribute:i.converter}:i.converter?.fromAttribute!==void 0?i.converter:Nt;this._$Em=r,this[r]=a.fromAttribute(e,i.type)??this._$Ej?.get(r)??null,this._$Em=null}}requestUpdate(t,e,o){if(t!==void 0){let r=this.constructor,i=this[t];if(o??(o=r.getPropertyOptions(t)),!((o.hasChanged??Gt)(i,e)||o.useDefault&&o.reflect&&i===this._$Ej?.get(t)&&!this.hasAttribute(r._$Eu(t,o))))return;this.C(t,e,o)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:o,reflect:r,wrapped:i},a){o&&!(this._$Ej??(this._$Ej=new Map)).has(t)&&(this._$Ej.set(t,a??e??this[t]),i!==!0||a!==void 0)||(this._$AL.has(t)||(this.hasUpdated||o||(e=void 0),this._$AL.set(t,e)),r===!0&&this._$Em!==t&&(this._$Eq??(this._$Eq=new Set)).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??(this.renderRoot=this.createRenderRoot()),this._$Ep){for(let[r,i]of this._$Ep)this[r]=i;this._$Ep=void 0}let o=this.constructor.elementProperties;if(o.size>0)for(let[r,i]of o){let{wrapped:a}=i,s=this[r];a!==!0||this._$AL.has(r)||s===void 0||this.C(r,void 0,i,s)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach((o=>o.hostUpdate?.())),this.update(e)):this._$EM()}catch(o){throw t=!1,this._$EM(),o}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach((e=>e.hostUpdated?.())),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&(this._$Eq=this._$Eq.forEach((e=>this._$ET(e,this[e])))),this._$EM()}updated(t){}firstUpdated(t){}};Et.elementStyles=[],Et.shadowRootOptions={mode:"open"},Et[Vt("elementProperties")]=new Map,Et[Vt("finalized")]=new Map,Ur?.({ReactiveElement:Et}),($t.reactiveElementVersions??($t.reactiveElementVersions=[])).push("2.1.0");var W=!1,Zt=globalThis,At=class extends Et{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var t;let e=super.createRenderRoot();return(t=this.renderOptions).renderBefore??(t.renderBefore=e.firstChild),e}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Lo(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return U}};At._$litElement$=!0,At.finalized=!0,Zt.litElementHydrateSupport?.({LitElement:At});var Wr=Zt.litElementPolyfillSupport;Wr?.({LitElement:At});(Zt.litElementVersions??(Zt.litElementVersions=[])).push("4.2.0");/*! Bundled license information:

@lit/reactive-element/css-tag.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/reactive-element.js:
lit-element/lit-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/is-server.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*//*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var ko=A`
  :host {
    --tag-max-size: 10ch;
    --show-duration: 100ms;
    --hide-duration: 100ms;
  }

  /* Add ellipses to multi select options */
  :host wa-tag::part(content) {
    display: initial;
    white-space: nowrap;
    text-overflow: ellipsis;
    overflow: hidden;
    max-width: var(--tag-max-size);
  }

  :host .disabled [part~='combobox'] {
    opacity: 0.5;
    cursor: not-allowed;
    outline: none;
  }

  :host .enabled:is(.open, :focus-within) [part~='combobox'] {
    outline: var(--wa-focus-ring);
    outline-offset: var(--wa-focus-ring-offset);
  }

  /** The popup */
  .select {
    flex: 1 1 auto;
    display: inline-flex;
    width: 100%;
    position: relative;
    vertical-align: middle;

    /* Pass through from select to the popup */
    --show-duration: inherit;
    --hide-duration: inherit;

    &::part(popup) {
      z-index: 900;
    }

    &[data-current-placement^='top']::part(popup) {
      transform-origin: bottom;
    }

    &[data-current-placement^='bottom']::part(popup) {
      transform-origin: top;
    }
  }

  /* Combobox */
  .combobox {
    flex: 1;
    display: flex;
    width: 100%;
    min-width: 0;
    align-items: center;
    justify-content: start;

    min-height: var(--wa-form-control-height);

    background-color: var(--wa-form-control-background-color);
    border-color: var(--wa-form-control-border-color);
    border-radius: var(--wa-form-control-border-radius);
    border-style: var(--wa-form-control-border-style);
    border-width: var(--wa-form-control-border-width);
    color: var(--wa-form-control-value-color);
    cursor: pointer;
    font-family: inherit;
    font-weight: var(--wa-form-control-value-font-weight);
    line-height: var(--wa-form-control-value-line-height);
    overflow: hidden;
    padding: 0 var(--wa-form-control-padding-inline);
    position: relative;
    vertical-align: middle;
    transition:
      background-color var(--wa-transition-normal),
      border var(--wa-transition-normal),
      outline var(--wa-transition-fast);
    transition-timing-function: var(--wa-transition-easing);

    :host([multiple]) .select:not(.placeholder-visible) & {
      padding-inline-start: 0;
      padding-block: calc(var(--wa-form-control-height) * 0.1 - var(--wa-form-control-border-width));
    }

    /* Pills */
    :host([pill]) & {
      border-radius: var(--wa-border-radius-pill);
    }
  }

  /* Appearance modifiers */
  :host([appearance='outlined']) .combobox {
    background-color: var(--wa-form-control-background-color);
    border-color: var(--wa-form-control-border-color);
  }

  :host([appearance='filled']) .combobox {
    background-color: var(--wa-color-neutral-fill-quiet);
    border-color: var(--wa-color-neutral-fill-quiet);
  }

  :host([appearance='filled-outlined']) .combobox {
    background-color: var(--wa-color-neutral-fill-quiet);
    border-color: var(--wa-form-control-border-color);
  }

  .display-input {
    position: relative;
    width: 100%;
    font: inherit;
    border: none;
    background: none;
    line-height: var(--wa-form-control-value-line-height);
    color: var(--wa-form-control-value-color);
    cursor: inherit;
    overflow: hidden;
    padding: 0;
    margin: 0;
    -webkit-appearance: none;

    &:focus {
      outline: none;
    }

    &::placeholder {
      color: var(--wa-form-control-placeholder-color);
    }
  }

  /* Visually hide the display input when multiple is enabled */
  :host([multiple]) .select:not(.placeholder-visible) .display-input {
    position: absolute;
    z-index: -1;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
  }

  .value-input {
    position: absolute;
    z-index: -1;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    padding: 0;
    margin: 0;
  }

  .tags {
    display: flex;
    flex: 1;
    align-items: center;
    flex-wrap: wrap;
    margin-inline-start: 0.25em;
    gap: 0.25em;

    &::slotted(wa-tag) {
      cursor: pointer !important;
    }

    .disabled &,
    .disabled &::slotted(wa-tag) {
      cursor: not-allowed !important;
    }
  }

  /* Start and End */

  .start,
  .end {
    flex: 0;
    display: inline-flex;
    align-items: center;
    color: var(--wa-color-neutral-on-quiet);
  }

  .end::slotted(*) {
    margin-inline-start: var(--wa-form-control-padding-inline);
  }

  .start::slotted(*) {
    margin-inline-end: var(--wa-form-control-padding-inline);
  }

  :host([multiple]) .start::slotted(*) {
    margin-inline: var(--wa-form-control-padding-inline);
  }

  /* Clear button */
  [part~='clear-button'] {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: inherit;
    color: var(--wa-color-neutral-on-quiet);
    border: none;
    background: none;
    padding: 0;
    transition: color var(--wa-transition-normal);
    cursor: pointer;
    margin-inline-start: var(--wa-form-control-padding-inline);

    &:focus {
      outline: none;
    }

    @media (hover: hover) {
      &:hover {
        color: color-mix(in oklab, currentColor, var(--wa-color-mix-hover));
      }
    }

    &:active {
      color: color-mix(in oklab, currentColor, var(--wa-color-mix-active));
    }
  }

  /* Expand icon */
  .expand-icon {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    color: var(--wa-color-neutral-on-quiet);
    transition: rotate var(--wa-transition-slow) ease;
    rotate: 0deg;
    margin-inline-start: var(--wa-form-control-padding-inline);

    .open & {
      rotate: -180deg;
    }
  }

  /* Listbox */
  .listbox {
    display: block;
    position: relative;
    font: inherit;
    box-shadow: var(--wa-shadow-m);
    background: var(--wa-color-surface-raised);
    border-color: var(--wa-color-surface-border);
    border-radius: var(--wa-border-radius-m);
    border-style: var(--wa-border-style);
    border-width: var(--wa-border-width-s);
    padding-block: 0.5em;
    padding-inline: 0;
    overflow: auto;
    overscroll-behavior: none;

    /* Make sure it adheres to the popup's auto size */
    max-width: var(--auto-size-available-width);
    max-height: var(--auto-size-available-height);

    &::slotted(wa-divider) {
      --spacing: 0.5em;
    }
  }

  slot:not([name])::slotted(small) {
    display: block;
    font-size: var(--wa-font-size-smaller);
    font-weight: var(--wa-font-weight-semibold);
    color: var(--wa-color-text-quiet);
    padding-block: 0.5em;
    padding-inline: 2.25em;
  }
`;/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Jt={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},Qt=t=>(...e)=>({_$litDirective$:t,values:e}),te=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,o){this._$Ct=t,this._$AM=e,this._$Ci=o}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};/*! Bundled license information:

lit-html/directive.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*//*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var ke=class extends te{constructor(t){if(super(t),this.it=$,t.type!==Jt.CHILD)throw Error(this.constructor.directiveName+"() can only be used in child bindings")}render(t){if(t===$||t==null)return this._t=void 0,this.it=t;if(t===U)return t;if(typeof t!="string")throw Error(this.constructor.directiveName+"() called with a non-string value");if(t===this.it)return this._t;this.it=t;let e=[t];return e.raw=e,this._t={_$litType$:this.constructor.resultType,strings:e,values:[]}}};ke.directiveName="unsafeHTML",ke.resultType=1;var Oo=Qt(ke);/*! Bundled license information:

lit-html/directives/unsafe-html.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*//*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */function jr(t,e){return{top:Math.round(t.getBoundingClientRect().top-e.getBoundingClientRect().top),left:Math.round(t.getBoundingClientRect().left-e.getBoundingClientRect().left)}}var Oe=new Set;function Kr(){let t=document.documentElement.clientWidth;return Math.abs(window.innerWidth-t)}function Yr(){let t=Number(getComputedStyle(document.body).paddingRight.replace(/px/,""));return isNaN(t)||!t?0:t}function ze(t){if(Oe.add(t),!document.documentElement.classList.contains("wa-scroll-lock")){let e=Kr()+Yr(),o=getComputedStyle(document.documentElement).scrollbarGutter;(!o||o==="auto")&&(o="stable"),e<2&&(o=""),document.documentElement.style.setProperty("--wa-scroll-lock-gutter",o),document.documentElement.classList.add("wa-scroll-lock"),document.documentElement.style.setProperty("--wa-scroll-lock-size",`${e}px`)}}function Pe(t){Oe.delete(t),Oe.size===0&&(document.documentElement.classList.remove("wa-scroll-lock"),document.documentElement.style.removeProperty("--wa-scroll-lock-size"))}function zo(t,e,o="vertical",r="smooth"){let i=jr(t,e),a=i.top+e.scrollTop,s=i.left+e.scrollLeft,n=e.scrollLeft,c=e.scrollLeft+e.offsetWidth,u=e.scrollTop,h=e.scrollTop+e.offsetHeight;(o==="horizontal"||o==="both")&&(s<n?e.scrollTo({left:s,behavior:r}):s+t.clientWidth>c&&e.scrollTo({left:s-e.offsetWidth+t.clientWidth,behavior:r})),(o==="vertical"||o==="both")&&(a<u?e.scrollTo({top:a,behavior:r}):a+t.clientHeight>h&&e.scrollTo({top:a-e.offsetHeight+t.clientHeight,behavior:r}))}/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Po=class extends Event{constructor(){super("wa-clear",{bubbles:!0,cancelable:!1,composed:!0})}};/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var ee=class extends Event{constructor(){super("wa-show",{bubbles:!0,cancelable:!0,composed:!0})}};/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var oe=class extends Event{constructor(t){super("wa-hide",{bubbles:!0,cancelable:!0,composed:!0}),this.detail=t}};/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var re=class extends Event{constructor(){super("wa-after-hide",{bubbles:!0,cancelable:!1,composed:!0})}};/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var ie=class extends Event{constructor(){super("wa-after-show",{bubbles:!0,cancelable:!1,composed:!0})}};/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */function Me(t,e){return new Promise(o=>{function r(i){i.target===t&&(t.removeEventListener(e,r),o())}t.addEventListener(e,r)})}/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */function ht(t,e){return new Promise(o=>{let r=new AbortController,{signal:i}=r;if(t.classList.contains(e))return;t.classList.remove(e),t.classList.add(e);let a=()=>{t.classList.remove(e),o(),r.abort()};t.addEventListener("animationend",a,{once:!0,signal:i}),t.addEventListener("animationcancel",a,{once:!0,signal:i})})}/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Mo=(t={})=>{let{validationElement:e,validationProperty:o}=t;e||(e=Object.assign(document.createElement("input"),{required:!0})),o||(o="value");let r={observedAttributes:["required"],message:e.validationMessage,checkValidity(i){let a={message:"",isValid:!0,invalidKeys:[]};return(i.required??i.hasAttribute("required"))&&!i[o]&&(a.message=typeof r.message=="function"?r.message(i):r.message||"",a.isValid=!1,a.invalidKeys.push("valueMissing")),a}};return r};/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var To=A`
  :host {
    display: flex;
    flex-direction: column;
  }

  /* Treat wrapped labels, inputs, and hints as direct children of the host element */
  [part~='form-control'] {
    display: contents;
  }

  /* Label */
  :is([part~='form-control-label'], [part~='label']):has(*:not(:empty)),
  :is([part~='form-control-label'], [part~='label']).has-label {
    display: inline-flex;
    color: var(--wa-form-control-label-color);
    font-weight: var(--wa-form-control-label-font-weight);
    line-height: var(--wa-form-control-label-line-height);
    margin-block-end: 0.5em;
  }

  :host([required]) :is([part~='form-control-label'], [part~='label'])::after {
    content: var(--wa-form-control-required-content);
    margin-inline-start: var(--wa-form-control-required-content-offset);
    color: var(--wa-form-control-required-content-color);
  }

  /* Help text */
  [part~='hint'] {
    display: block;
    color: var(--wa-form-control-hint-color);
    font-weight: var(--wa-form-control-hint-font-weight);
    line-height: var(--wa-form-control-hint-line-height);
    margin-block-start: 0.5em;
    font-size: var(--wa-font-size-smaller);

    &:not(.has-slotted, .has-hint) {
      display: none;
    }
  }
`;/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var ae=class extends Event{constructor(){super("wa-invalid",{bubbles:!0,cancelable:!1,composed:!0})}};/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Xr=Object.defineProperty,Zr=Object.getOwnPropertyDescriptor;var Ro=t=>{throw TypeError(t)};var l=(t,e,o,r)=>{for(var i=r>1?void 0:r?Zr(e,o):e,a=t.length-1,s;a>=0;a--)(s=t[a])&&(i=(r?s(e,o,i):s(i))||i);return r&&i&&Xr(e,o,i),i},Do=(t,e,o)=>e.has(t)||Ro("Cannot "+o),Fo=(t,e,o)=>(Do(t,e,"read from private field"),o?o.call(t):e.get(t)),Io=(t,e,o)=>e.has(t)?Ro("Cannot add the same private member more than once"):e instanceof WeakSet?e.add(t):e.set(t,o),Bo=(t,e,o,r)=>(Do(t,e,"write to private field"),r?r.call(t,o):e.set(t,o),o);/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var M=t=>(e,o)=>{o!==void 0?o.addInitializer((()=>{customElements.define(t,e)})):customElements.define(t,e)},Gr={attribute:!0,type:String,converter:Nt,reflect:!1,hasChanged:Gt},Jr=(t=Gr,e,o)=>{let{kind:r,metadata:i}=o,a=globalThis.litPropertyMetadata.get(i);if(a===void 0&&globalThis.litPropertyMetadata.set(i,a=new Map),r==="setter"&&((t=Object.create(t)).wrapped=!0),a.set(o.name,t),r==="accessor"){let{name:s}=o;return{set(n){let c=e.get.call(this);e.set.call(this,n),this.requestUpdate(s,c,t)},init(n){return n!==void 0&&this.C(s,void 0,t,n),n}}}if(r==="setter"){let{name:s}=o;return function(n){let c=this[s];e.call(this,n),this.requestUpdate(s,c,t)}}throw Error("Unsupported decorator location: "+r)};function d(t){return(e,o)=>typeof o=="object"?Jr(t,e,o):((r,i,a)=>{let s=i.hasOwnProperty(a);return i.constructor.createProperty(a,r),s?Object.getOwnPropertyDescriptor(i,a):void 0})(t,e,o)}function D(t){return d({...t,state:!0,attribute:!1})}var qo=(t,e,o)=>(o.configurable=!0,o.enumerable=!0,Reflect.decorate&&typeof e!="object"&&Object.defineProperty(t,e,o),o);function T(t,e){return(o,r,i)=>{let a=s=>s.renderRoot?.querySelector(t)??null;if(e){let{get:s,set:n}=typeof r=="object"?o:i??(()=>{let c=Symbol();return{get(){return this[c]},set(u){this[c]=u}}})();return qo(o,r,{get(){let c=s.call(this);return c===void 0&&(c=a(this),(c!==null||this.hasUpdated)&&n.call(this,c)),c}})}return qo(o,r,{get(){return a(this)}})}}var Qr=A`
  :host {
    box-sizing: border-box !important;
  }

  :host *,
  :host *::before,
  :host *::after {
    box-sizing: inherit !important;
  }

  [hidden] {
    display: none !important;
  }
`,se,O=class extends At{constructor(){super(),Io(this,se,!1),this.initialReflectedProperties=new Map,this.didSSR=W||!!this.shadowRoot,this.customStates={set:(e,o)=>{if(this.internals?.states)try{o?this.internals.states.add(e):this.internals.states.delete(e)}catch(r){if(String(r).includes("must start with '--'"))console.error("Your browser implements an outdated version of CustomStateSet. Consider using a polyfill");else throw r}},has:e=>{if(!this.internals?.states)return!1;try{return this.internals.states.has(e)}catch{return!1}}};try{this.internals=this.attachInternals()}catch{console.error("Element internals are not supported in your browser. Consider using a polyfill")}this.customStates.set("wa-defined",!0);let t=this.constructor;for(let[e,o]of t.elementProperties)o.default==="inherit"&&o.initial!==void 0&&typeof e=="string"&&this.customStates.set(`initial-${e}-${o.initial}`,!0)}static get styles(){let t=Array.isArray(this.css)?this.css:this.css?[this.css]:[];return[Qr,...t]}attributeChangedCallback(t,e,o){Fo(this,se)||(this.constructor.elementProperties.forEach((r,i)=>{r.reflect&&this[i]!=null&&this.initialReflectedProperties.set(i,this[i])}),Bo(this,se,!0)),super.attributeChangedCallback(t,e,o)}willUpdate(t){super.willUpdate(t),this.initialReflectedProperties.forEach((e,o)=>{t.has(o)&&this[o]==null&&(this[o]=e)})}firstUpdated(t){super.firstUpdated(t),this.didSSR&&this.shadowRoot?.querySelectorAll("slot").forEach(e=>{e.dispatchEvent(new Event("slotchange",{bubbles:!0,composed:!1,cancelable:!1}))})}update(t){try{super.update(t)}catch(e){if(this.didSSR&&!this.hasUpdated){let o=new Event("lit-hydration-error",{bubbles:!0,composed:!0,cancelable:!1});o.error=e,this.dispatchEvent(o)}throw e}}relayNativeEvent(t,e){t.stopImmediatePropagation(),this.dispatchEvent(new t.constructor(t.type,{...t,...e}))}};se=new WeakMap;l([d()],O.prototype,"dir",2);l([d()],O.prototype,"lang",2);l([d({type:Boolean,reflect:!0,attribute:"did-ssr"})],O.prototype,"didSSR",2);/*! Bundled license information:

@lit/reactive-element/decorators/custom-element.js:
@lit/reactive-element/decorators/property.js:
@lit/reactive-element/decorators/state.js:
@lit/reactive-element/decorators/event-options.js:
@lit/reactive-element/decorators/base.js:
@lit/reactive-element/decorators/query.js:
@lit/reactive-element/decorators/query-async.js:
@lit/reactive-element/decorators/query-all.js:
@lit/reactive-element/decorators/query-assigned-nodes.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/decorators/query-assigned-elements.js:
  (**
   * @license
   * Copyright 2021 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*//*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var ti=()=>({observedAttributes:["custom-error"],checkValidity(t){let e={message:"",isValid:!0,invalidKeys:[]};return t.customError&&(e.message=t.customError,e.isValid=!1,e.invalidKeys=["customError"]),e}}),q=class extends O{constructor(){super(),this.name=null,this.disabled=!1,this.required=!1,this.assumeInteractionOn=["input"],this.validators=[],this.valueHasChanged=!1,this.hasInteracted=!1,this.customError=null,this.emittedEvents=[],this.emitInvalid=t=>{t.target===this&&(this.hasInteracted=!0,this.dispatchEvent(new ae))},this.handleInteraction=t=>{let e=this.emittedEvents;e.includes(t.type)||e.push(t.type),e.length===this.assumeInteractionOn?.length&&(this.hasInteracted=!0)},W||this.addEventListener("invalid",this.emitInvalid)}static get validators(){return[ti()]}static get observedAttributes(){let t=new Set(super.observedAttributes||[]);for(let e of this.validators)if(e.observedAttributes)for(let o of e.observedAttributes)t.add(o);return[...t]}connectedCallback(){super.connectedCallback(),this.updateValidity(),this.assumeInteractionOn.forEach(t=>{this.addEventListener(t,this.handleInteraction)})}firstUpdated(...t){super.firstUpdated(...t),this.updateValidity()}willUpdate(t){if(!W&&t.has("customError")&&(this.customError||(this.customError=null),this.setCustomValidity(this.customError||"")),t.has("value")||t.has("disabled")){let e=this.value;if(Array.isArray(e)){if(this.name){let o=new FormData;for(let r of e)o.append(this.name,r);this.setValue(o,o)}}else this.setValue(e,e)}t.has("disabled")&&(this.customStates.set("disabled",this.disabled),(this.hasAttribute("disabled")||!W&&!this.matches(":disabled"))&&this.toggleAttribute("disabled",this.disabled)),this.updateValidity(),super.willUpdate(t)}get labels(){return this.internals.labels}getForm(){return this.internals.form}set form(t){t?this.setAttribute("form",t):this.removeAttribute("form")}get form(){return this.internals.form}get validity(){return this.internals.validity}get willValidate(){return this.internals.willValidate}get validationMessage(){return this.internals.validationMessage}checkValidity(){return this.updateValidity(),this.internals.checkValidity()}reportValidity(){return this.updateValidity(),this.hasInteracted=!0,this.internals.reportValidity()}get validationTarget(){return this.input||void 0}setValidity(...t){let e=t[0],o=t[1],r=t[2];r||(r=this.validationTarget),this.internals.setValidity(e,o,r||void 0),this.requestUpdate("validity"),this.setCustomStates()}setCustomStates(){let t=!!this.required,e=this.internals.validity.valid,o=this.hasInteracted;this.customStates.set("required",t),this.customStates.set("optional",!t),this.customStates.set("invalid",!e),this.customStates.set("valid",e),this.customStates.set("user-invalid",!e&&o),this.customStates.set("user-valid",e&&o)}setCustomValidity(t){if(!t){this.customError=null,this.setValidity({});return}this.customError=t,this.setValidity({customError:!0},t,this.validationTarget)}formResetCallback(){this.resetValidity(),this.hasInteracted=!1,this.valueHasChanged=!1,this.emittedEvents=[],this.updateValidity()}formDisabledCallback(t){this.disabled=t,this.updateValidity()}formStateRestoreCallback(t,e){this.value=t,e==="restore"&&this.resetValidity(),this.updateValidity()}setValue(...t){let[e,o]=t;this.internals.setFormValue(e,o)}get allValidators(){let t=this.constructor.validators||[],e=this.validators||[];return[...t,...e]}resetValidity(){this.setCustomValidity(""),this.setValidity({})}updateValidity(){if(this.disabled||this.hasAttribute("disabled")||!this.willValidate){this.resetValidity();return}let t=this.allValidators;if(!t?.length)return;let e={customError:!!this.customError},o=this.validationTarget||this.input||void 0,r="";for(let i of t){let{isValid:a,message:s,invalidKeys:n}=i.checkValidity(this);a||(r||(r=s),n?.length>=0&&n.forEach(c=>e[c]=!0))}r||(r=this.validationMessage),this.setValidity(e,r,o)}};q.formAssociated=!0;l([d({reflect:!0})],q.prototype,"name",2);l([d({type:Boolean})],q.prototype,"disabled",2);l([d({state:!0,attribute:!1})],q.prototype,"valueHasChanged",2);l([d({state:!0,attribute:!1})],q.prototype,"hasInteracted",2);l([d({attribute:"custom-error",reflect:!0})],q.prototype,"customError",2);l([d({attribute:!1,state:!0,type:Object})],q.prototype,"validity",1);/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var V=Qt(class extends te{constructor(t){if(super(t),t.type!==Jt.ATTRIBUTE||t.name!=="class"||t.strings?.length>2)throw Error("`classMap()` can only be used in the `class` attribute and must be the only part in the attribute.")}render(t){return" "+Object.keys(t).filter((e=>t[e])).join(" ")+" "}update(t,[e]){if(this.st===void 0){this.st=new Set,t.strings!==void 0&&(this.nt=new Set(t.strings.join(" ").split(/\s/).filter((r=>r!==""))));for(let r in e)e[r]&&!this.nt?.has(r)&&this.st.add(r);return this.render(e)}let o=t.element.classList;for(let r of this.st)r in e||(o.remove(r),this.st.delete(r));for(let r in e){let i=!!e[r];i===this.st.has(r)||this.nt?.has(r)||(i?(o.add(r),this.st.add(r)):(o.remove(r),this.st.delete(r)))}return U}});/*! Bundled license information:

lit-html/directives/class-map.js:
  (**
   * @license
   * Copyright 2018 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*//*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var St=class{constructor(t,...e){this.slotNames=[],this.handleSlotChange=o=>{let r=o.target;(this.slotNames.includes("[default]")&&!r.name||r.name&&this.slotNames.includes(r.name))&&this.host.requestUpdate()},(this.host=t).addController(this),this.slotNames=e}hasDefaultSlot(){return[...this.host.childNodes].some(t=>{if(t.nodeType===Node.TEXT_NODE&&t.textContent.trim()!=="")return!0;if(t.nodeType===Node.ELEMENT_NODE){let e=t;if(e.tagName.toLowerCase()==="wa-visually-hidden")return!1;if(!e.hasAttribute("slot"))return!0}return!1})}hasNamedSlot(t){return this.host.querySelector(`:scope > [slot="${t}"]`)!==null}test(t){return t==="[default]"?this.hasDefaultSlot():this.hasNamedSlot(t)}hostConnected(){this.host.shadowRoot.addEventListener("slotchange",this.handleSlotChange)}hostDisconnected(){this.host.shadowRoot.removeEventListener("slotchange",this.handleSlotChange)}};/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var kt=A`
  :host([size='small']),
  .wa-size-s {
    font-size: var(--wa-font-size-s);
  }

  :host([size='medium']),
  .wa-size-m {
    font-size: var(--wa-font-size-m);
  }

  :host([size='large']),
  .wa-size-l {
    font-size: var(--wa-font-size-l);
  }
`;/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Te=new Set,Ot=new Map,Lt,Re="ltr",De="en",Vo=typeof MutationObserver<"u"&&typeof document<"u"&&typeof document.documentElement<"u";if(Vo){let t=new MutationObserver(No);Re=document.documentElement.dir||"ltr",De=document.documentElement.lang||navigator.language,t.observe(document.documentElement,{attributes:!0,attributeFilter:["dir","lang"]})}function ne(...t){t.map(e=>{let o=e.$code.toLowerCase();Ot.has(o)?Ot.set(o,Object.assign(Object.assign({},Ot.get(o)),e)):Ot.set(o,e),Lt||(Lt=e)}),No()}function No(){Vo&&(Re=document.documentElement.dir||"ltr",De=document.documentElement.lang||navigator.language),[...Te.keys()].map(t=>{typeof t.requestUpdate=="function"&&t.requestUpdate()})}var Ho=class{constructor(t){this.host=t,this.host.addController(this)}hostConnected(){Te.add(this.host)}hostDisconnected(){Te.delete(this.host)}dir(){return`${this.host.dir||Re}`.toLowerCase()}lang(){return`${this.host.lang||De}`.toLowerCase()}getTranslationData(t){var e,o;let r=new Intl.Locale(t.replace(/_/g,"-")),i=r?.language.toLowerCase(),a=(o=(e=r?.region)===null||e===void 0?void 0:e.toLowerCase())!==null&&o!==void 0?o:"",s=Ot.get(`${i}-${a}`),n=Ot.get(i);return{locale:r,language:i,region:a,primary:s,secondary:n}}exists(t,e){var o;let{primary:r,secondary:i}=this.getTranslationData((o=e.lang)!==null&&o!==void 0?o:this.lang());return e=Object.assign({includeFallback:!1},e),!!(r&&r[t]||i&&i[t]||e.includeFallback&&Lt&&Lt[t])}term(t,...e){let{primary:o,secondary:r}=this.getTranslationData(this.lang()),i;if(o&&o[t])i=o[t];else if(r&&r[t])i=r[t];else if(Lt&&Lt[t])i=Lt[t];else return console.error(`No translation found for: ${String(t)}`),String(t);return typeof i=="function"?i(...e):i}date(t,e){return t=new Date(t),new Intl.DateTimeFormat(this.lang(),e).format(t)}number(t,e){return t=Number(t),isNaN(t)?"":new Intl.NumberFormat(this.lang(),e).format(t)}relativeTime(t,e,o){return new Intl.RelativeTimeFormat(this.lang(),o).format(t,e)}};/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Uo={$code:"en",$name:"English",$dir:"ltr",carousel:"Carousel",clearEntry:"Clear entry",close:"Close",copied:"Copied",copy:"Copy",currentValue:"Current value",dropFileHere:"Drop file here or click to browse",decrement:"Decrement",dropFilesHere:"Drop files here or click to browse",error:"Error",goToSlide:(t,e)=>`Go to slide ${t} of ${e}`,hidePassword:"Hide password",increment:"Increment",loading:"Loading",nextSlide:"Next slide",numOptionsSelected:t=>t===0?"No options selected":t===1?"1 option selected":`${t} options selected`,pauseAnimation:"Pause animation",playAnimation:"Play animation",previousSlide:"Previous slide",progress:"Progress",remove:"Remove",resize:"Resize",scrollableRegion:"Scrollable region",scrollToEnd:"Scroll to end",scrollToStart:"Scroll to start",selectAColorFromTheScreen:"Select a color from the screen",showPassword:"Show password",slideNum:t=>`Slide ${t}`,toggleColorFormat:"Toggle color format",zoomIn:"Zoom in",zoomOut:"Zoom out"};ne(Uo);var Wo=Uo;/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var R=class extends Ho{};ne(Wo);/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */function j(t,e){let o={waitUntilFirstUpdate:!1,...e};return(r,i)=>{let{update:a}=r,s=Array.isArray(t)?t:[t];r.update=function(n){s.forEach(c=>{let u=c;if(n.has(u)){let h=n.get(u),p=this[u];h!==p&&(!o.waitUntilFirstUpdate||this.hasUpdated)&&this[i](h,p)}}),a.call(this,n)}}}/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var b=class extends q{constructor(){super(...arguments),this.assumeInteractionOn=["blur","input"],this.hasSlotController=new St(this,"hint","label"),this.localize=new R(this),this.selectionOrder=new Map,this.typeToSelectString="",this.displayLabel="",this.selectedOptions=[],this.name="",this._defaultValue=null,this.size="medium",this.placeholder="",this.multiple=!1,this.maxOptionsVisible=3,this.disabled=!1,this.withClear=!1,this.open=!1,this.appearance="outlined",this.pill=!1,this.label="",this.placement="bottom",this.hint="",this.withLabel=!1,this.withHint=!1,this.required=!1,this.getTag=t=>E`
        <wa-tag
          part="tag"
          exportparts="
            base:tag__base,
            content:tag__content,
            remove-button:tag__remove-button,
            remove-button__base:tag__remove-button__base
          "
          ?pill=${this.pill}
          size=${this.size}
          with-remove
          data-value=${t.value}
          @wa-remove=${e=>this.handleTagRemove(e,t)}
        >
          ${t.label}
        </wa-tag>
      `,this.handleDocumentFocusIn=t=>{let e=t.composedPath();this&&!e.includes(this)&&this.hide()},this.handleDocumentKeyDown=t=>{let e=t.target,o=e.closest('[part~="clear-button"]')!==null,r=e.closest("wa-button")!==null;if(!(o||r)){if(t.key==="Escape"&&this.open&&(t.preventDefault(),t.stopPropagation(),this.hide(),this.displayInput.focus({preventScroll:!0})),t.key==="Enter"||t.key===" "&&this.typeToSelectString===""){if(t.preventDefault(),t.stopImmediatePropagation(),!this.open){this.show();return}this.currentOption&&!this.currentOption.disabled&&(this.valueHasChanged=!0,this.hasInteracted=!0,this.multiple?this.toggleOptionSelection(this.currentOption):this.setSelectedOptions(this.currentOption),this.updateComplete.then(()=>{this.dispatchEvent(new InputEvent("input",{bubbles:!0,composed:!0})),this.dispatchEvent(new Event("change",{bubbles:!0,composed:!0}))}),this.multiple||(this.hide(),this.displayInput.focus({preventScroll:!0})));return}if(["ArrowUp","ArrowDown","Home","End"].includes(t.key)){let i=this.getAllOptions(),a=i.indexOf(this.currentOption),s=Math.max(0,a);if(t.preventDefault(),!this.open&&(this.show(),this.currentOption))return;t.key==="ArrowDown"?(s=a+1,s>i.length-1&&(s=0)):t.key==="ArrowUp"?(s=a-1,s<0&&(s=i.length-1)):t.key==="Home"?s=0:t.key==="End"&&(s=i.length-1),this.setCurrentOption(i[s])}if(t.key?.length===1||t.key==="Backspace"){let i=this.getAllOptions();if(t.metaKey||t.ctrlKey||t.altKey)return;if(!this.open){if(t.key==="Backspace")return;this.show()}t.stopPropagation(),t.preventDefault(),clearTimeout(this.typeToSelectTimeout),this.typeToSelectTimeout=window.setTimeout(()=>this.typeToSelectString="",1e3),t.key==="Backspace"?this.typeToSelectString=this.typeToSelectString.slice(0,-1):this.typeToSelectString+=t.key.toLowerCase();for(let a of i)if(a.label.toLowerCase().startsWith(this.typeToSelectString)){this.setCurrentOption(a);break}}}},this.handleDocumentMouseDown=t=>{let e=t.composedPath();this&&!e.includes(this)&&this.hide()}}static get validators(){let t=W?[]:[Mo({validationElement:Object.assign(document.createElement("select"),{required:!0})})];return[...super.validators,...t]}get validationTarget(){return this.valueInput}set defaultValue(t){this._defaultValue=this.convertDefaultValue(t)}get defaultValue(){return this.convertDefaultValue(this._defaultValue)}convertDefaultValue(t){return!(this.multiple||this.hasAttribute("multiple"))&&Array.isArray(t)&&(t=t[0]),t}set value(t){let e=this.value;t instanceof FormData&&(t=t.getAll(this.name)),t!=null&&!Array.isArray(t)&&(t=[t]),this._value=t??null,this.value!==e&&(this.valueHasChanged=!0,this.requestUpdate("value",e))}get value(){let t=this._value??this.defaultValue??null;t!=null&&(t=Array.isArray(t)?t:[t]),t==null?this.optionValues=new Set(null):this.optionValues=new Set(this.getAllOptions().filter(o=>!o.disabled).map(o=>o.value));let e=t;return t!=null&&(e=t.filter(o=>this.optionValues.has(o)),e=this.multiple?e:e[0],e=e??null),e}connectedCallback(){super.connectedCallback(),this.handleDefaultSlotChange(),this.open=!1}updateDefaultValue(){let e=this.getAllOptions().filter(o=>o.hasAttribute("selected")||o.defaultSelected);if(e.length>0){let o=e.map(r=>r.value);this._defaultValue=this.multiple?o:o[0]}this.hasAttribute("value")&&(this._defaultValue=this.getAttribute("value")||null)}addOpenListeners(){document.addEventListener("focusin",this.handleDocumentFocusIn),document.addEventListener("keydown",this.handleDocumentKeyDown),document.addEventListener("mousedown",this.handleDocumentMouseDown),this.getRootNode()!==document&&this.getRootNode().addEventListener("focusin",this.handleDocumentFocusIn)}removeOpenListeners(){document.removeEventListener("focusin",this.handleDocumentFocusIn),document.removeEventListener("keydown",this.handleDocumentKeyDown),document.removeEventListener("mousedown",this.handleDocumentMouseDown),this.getRootNode()!==document&&this.getRootNode().removeEventListener("focusin",this.handleDocumentFocusIn)}handleFocus(){this.displayInput.setSelectionRange(0,0)}handleLabelClick(){this.displayInput.focus()}handleComboboxClick(t){t.preventDefault()}handleComboboxMouseDown(t){let o=t.composedPath().some(r=>r instanceof Element&&r.tagName.toLowerCase()==="wa-button");this.disabled||o||(t.preventDefault(),this.displayInput.focus({preventScroll:!0}),this.open=!this.open)}handleComboboxKeyDown(t){t.stopPropagation(),this.handleDocumentKeyDown(t)}handleClearClick(t){t.stopPropagation(),this.value!==null&&(this.selectionOrder.clear(),this.setSelectedOptions([]),this.displayInput.focus({preventScroll:!0}),this.updateComplete.then(()=>{this.dispatchEvent(new Po),this.dispatchEvent(new InputEvent("input",{bubbles:!0,composed:!0})),this.dispatchEvent(new Event("change",{bubbles:!0,composed:!0}))}))}handleClearMouseDown(t){t.stopPropagation(),t.preventDefault()}handleOptionClick(t){let o=t.target.closest("wa-option");o&&!o.disabled&&(this.hasInteracted=!0,this.valueHasChanged=!0,this.multiple?this.toggleOptionSelection(o):this.setSelectedOptions(o),this.updateComplete.then(()=>this.displayInput.focus({preventScroll:!0})),this.requestUpdate("value"),this.updateComplete.then(()=>{this.dispatchEvent(new InputEvent("input",{bubbles:!0,composed:!0})),this.dispatchEvent(new Event("change",{bubbles:!0,composed:!0}))}),this.multiple||(this.hide(),this.displayInput.focus({preventScroll:!0})))}handleDefaultSlotChange(){customElements.get("wa-option")||customElements.whenDefined("wa-option").then(()=>this.handleDefaultSlotChange());let t=this.getAllOptions();this.optionValues=void 0,this.updateDefaultValue();let e=this.value;if(e==null||!this.valueHasChanged&&!this.hasInteracted){this.selectionChanged();return}Array.isArray(e)||(e=[e]);let o=t.filter(r=>e.includes(r.value));this.setSelectedOptions(o)}handleTagRemove(t,e){if(t.stopPropagation(),this.disabled)return;this.hasInteracted=!0,this.valueHasChanged=!0;let o=e;if(!o){let r=t.target.closest("wa-tag[data-value]");if(r){let i=r.dataset.value;o=this.selectedOptions.find(a=>a.value===i)}}o&&(this.toggleOptionSelection(o,!1),this.updateComplete.then(()=>{this.dispatchEvent(new InputEvent("input",{bubbles:!0,composed:!0})),this.dispatchEvent(new Event("change",{bubbles:!0,composed:!0}))}))}getAllOptions(){return this?.querySelectorAll?[...this.querySelectorAll("wa-option")]:[]}getFirstOption(){return this.querySelector("wa-option")}setCurrentOption(t){this.getAllOptions().forEach(o=>{o.current=!1,o.tabIndex=-1}),t&&(this.currentOption=t,t.current=!0,t.tabIndex=0,t.focus())}setSelectedOptions(t){let e=this.getAllOptions(),o=Array.isArray(t)?t:[t];e.forEach(r=>{o.includes(r)||(r.selected=!1)}),o.length&&o.forEach(r=>r.selected=!0),this.selectionChanged()}toggleOptionSelection(t,e){e===!0||e===!1?t.selected=e:t.selected=!t.selected,this.selectionChanged()}selectionChanged(){let e=this.getAllOptions().filter(s=>{if(!this.hasInteracted&&!this.valueHasChanged){let n=this.defaultValue,c=Array.isArray(n)?n:[n];return s.hasAttribute("selected")||s.defaultSelected||s.selected||c?.includes(s.value)}return s.selected}),o=new Set(e.map(s=>s.value));for(let s of this.selectionOrder.keys())o.has(s)||this.selectionOrder.delete(s);let i=(this.selectionOrder.size>0?Math.max(...this.selectionOrder.values()):-1)+1;for(let s of e)this.selectionOrder.has(s.value)||this.selectionOrder.set(s.value,i++);this.selectedOptions=e.sort((s,n)=>{let c=this.selectionOrder.get(s.value)??0,u=this.selectionOrder.get(n.value)??0;return c-u});let a=new Set(this.selectedOptions.map(s=>s.value));if(a.size>0||this._value){let s=this._value;if(this._value==null){let n=this.defaultValue??[];this._value=Array.isArray(n)?n:[n]}this._value=this._value?.filter(n=>!this.optionValues?.has(n))??null,this._value?.unshift(...a),this.requestUpdate("value",s)}if(this.multiple)this.placeholder&&!this.value?.length?this.displayLabel="":this.displayLabel=this.localize.term("numOptionsSelected",this.selectedOptions.length);else{let s=this.selectedOptions[0];this.displayLabel=s?.label??""}this.updateComplete.then(()=>{this.updateValidity()})}get tags(){return this.selectedOptions.map((t,e)=>{if(e<this.maxOptionsVisible||this.maxOptionsVisible<=0){let o=this.getTag(t,e);return o?typeof o=="string"?Oo(o):o:null}else if(e===this.maxOptionsVisible)return E`
          <wa-tag
            part="tag"
            exportparts="
              base:tag__base,
              content:tag__content,
              remove-button:tag__remove-button,
              remove-button__base:tag__remove-button__base
            "
            >+${this.selectedOptions.length-e}</wa-tag
          >
        `;return null})}updated(t){super.updated(t),t.has("value")&&this.customStates.set("blank",!this.value)}handleDisabledChange(){this.disabled&&this.open&&(this.open=!1)}handleValueChange(){let t=this.getAllOptions(),e=Array.isArray(this.value)?this.value:[this.value],o=t.filter(r=>e.includes(r.value));this.setSelectedOptions(o),this.updateValidity()}async handleOpenChange(){if(this.open&&!this.disabled){this.setCurrentOption(this.selectedOptions[0]||this.getFirstOption());let t=new ee;if(this.dispatchEvent(t),t.defaultPrevented){this.open=!1;return}this.addOpenListeners(),this.listbox.hidden=!1,this.popup.active=!0,requestAnimationFrame(()=>{this.setCurrentOption(this.currentOption)}),await ht(this.popup.popup,"show"),this.currentOption&&zo(this.currentOption,this.listbox,"vertical","auto"),this.dispatchEvent(new ie)}else{let t=new oe;if(this.dispatchEvent(t),t.defaultPrevented){this.open=!1;return}this.removeOpenListeners(),await ht(this.popup.popup,"hide"),this.listbox.hidden=!0,this.popup.active=!1,this.dispatchEvent(new re)}}async show(){if(this.open||this.disabled){this.open=!1;return}return this.open=!0,Me(this,"wa-after-show")}async hide(){if(!this.open||this.disabled){this.open=!1;return}return this.open=!1,Me(this,"wa-after-hide")}focus(t){this.displayInput.focus(t)}blur(){this.displayInput.blur()}formResetCallback(){this.selectionOrder.clear(),this.value=this.defaultValue,super.formResetCallback(),this.handleValueChange(),this.updateComplete.then(()=>{this.dispatchEvent(new InputEvent("input",{bubbles:!0,composed:!0})),this.dispatchEvent(new Event("change",{bubbles:!0,composed:!0}))})}render(){let t=this.hasUpdated?this.hasSlotController.test("label"):this.withLabel,e=this.hasUpdated?this.hasSlotController.test("hint"):this.withHint,o=this.label?!0:!!t,r=this.hint?!0:!!e,i=(this.hasUpdated||W)&&this.withClear&&!this.disabled&&this.value&&this.value.length>0,a=!!(this.placeholder&&(!this.value||this.value.length===0));return E`
      <div
        part="form-control"
        class=${V({"form-control":!0,"form-control-has-label":o})}
      >
        <label
          id="label"
          part="form-control-label label"
          class=${V({label:!0,"has-label":o})}
          aria-hidden=${o?"false":"true"}
          @click=${this.handleLabelClick}
        >
          <slot name="label">${this.label}</slot>
        </label>

        <div part="form-control-input" class="form-control-input">
          <wa-popup
            class=${V({select:!0,open:this.open,disabled:this.disabled,enabled:!this.disabled,multiple:this.multiple,"placeholder-visible":a})}
            placement=${this.placement}
            flip
            shift
            sync="width"
            auto-size="vertical"
            auto-size-padding="10"
          >
            <div
              part="combobox"
              class="combobox"
              slot="anchor"
              @keydown=${this.handleComboboxKeyDown}
              @mousedown=${this.handleComboboxMouseDown}
              @click=${this.handleComboboxClick}
            >
              <slot part="start" name="start" class="start"></slot>

              <input
                part="display-input"
                class="display-input"
                type="text"
                placeholder=${this.placeholder}
                .disabled=${this.disabled}
                .value=${this.displayLabel}
                ?required=${this.required}
                autocomplete="off"
                spellcheck="false"
                autocapitalize="off"
                readonly
                aria-invalid=${!this.validity.valid}
                aria-controls="listbox"
                aria-expanded=${this.open?"true":"false"}
                aria-haspopup="listbox"
                aria-labelledby="label"
                aria-disabled=${this.disabled?"true":"false"}
                aria-describedby="hint"
                role="combobox"
                tabindex="0"
                @focus=${this.handleFocus}
              />

              <!-- Tags need to wait for first hydration before populating otherwise it will create a hydration mismatch. -->
              ${this.multiple&&this.hasUpdated?E`<div part="tags" class="tags" @wa-remove=${this.handleTagRemove}>${this.tags}</div>`:""}

              <input
                class="value-input"
                type="text"
                ?disabled=${this.disabled}
                ?required=${this.required}
                .value=${Array.isArray(this.value)?this.value.join(", "):this.value}
                tabindex="-1"
                aria-hidden="true"
                @focus=${()=>this.focus()}
              />

              ${i?E`
                    <button
                      part="clear-button"
                      type="button"
                      aria-label=${this.localize.term("clearEntry")}
                      @mousedown=${this.handleClearMouseDown}
                      @click=${this.handleClearClick}
                      tabindex="-1"
                    >
                      <slot name="clear-icon">
                        <wa-icon name="circle-xmark" library="system" variant="regular"></wa-icon>
                      </slot>
                    </button>
                  `:""}

              <slot name="end" part="end" class="end"></slot>

              <slot name="expand-icon" part="expand-icon" class="expand-icon">
                <wa-icon library="system" name="chevron-down" variant="solid"></wa-icon>
              </slot>
            </div>

            <div
              id="listbox"
              role="listbox"
              aria-expanded=${this.open?"true":"false"}
              aria-multiselectable=${this.multiple?"true":"false"}
              aria-labelledby="label"
              part="listbox"
              class="listbox"
              tabindex="-1"
              @mouseup=${this.handleOptionClick}
            >
              <slot @slotchange=${this.handleDefaultSlotChange}></slot>
            </div>
          </wa-popup>
        </div>

        <slot
          id="hint"
          name="hint"
          part="hint"
          class=${V({"has-slotted":r})}
          aria-hidden=${r?"false":"true"}
          >${this.hint}</slot
        >
      </div>
    `}};b.css=[ko,To,kt];l([T(".select")],b.prototype,"popup",2);l([T(".combobox")],b.prototype,"combobox",2);l([T(".display-input")],b.prototype,"displayInput",2);l([T(".value-input")],b.prototype,"valueInput",2);l([T(".listbox")],b.prototype,"listbox",2);l([D()],b.prototype,"displayLabel",2);l([D()],b.prototype,"currentOption",2);l([D()],b.prototype,"selectedOptions",2);l([D()],b.prototype,"optionValues",2);l([d({reflect:!0})],b.prototype,"name",2);l([d({attribute:!1})],b.prototype,"defaultValue",1);l([d({attribute:"value",reflect:!1})],b.prototype,"value",1);l([d({reflect:!0})],b.prototype,"size",2);l([d()],b.prototype,"placeholder",2);l([d({type:Boolean,reflect:!0})],b.prototype,"multiple",2);l([d({attribute:"max-options-visible",type:Number})],b.prototype,"maxOptionsVisible",2);l([d({type:Boolean})],b.prototype,"disabled",2);l([d({attribute:"with-clear",type:Boolean})],b.prototype,"withClear",2);l([d({type:Boolean,reflect:!0})],b.prototype,"open",2);l([d({reflect:!0})],b.prototype,"appearance",2);l([d({type:Boolean,reflect:!0})],b.prototype,"pill",2);l([d()],b.prototype,"label",2);l([d({reflect:!0})],b.prototype,"placement",2);l([d({attribute:"hint"})],b.prototype,"hint",2);l([d({attribute:"with-label",type:Boolean})],b.prototype,"withLabel",2);l([d({attribute:"with-hint",type:Boolean})],b.prototype,"withHint",2);l([d({type:Boolean,reflect:!0})],b.prototype,"required",2);l([d({attribute:!1})],b.prototype,"getTag",2);l([j("disabled",{waitUntilFirstUpdate:!0})],b.prototype,"handleDisabledChange",1);l([j("value",{waitUntilFirstUpdate:!0})],b.prototype,"handleValueChange",1);l([j("open",{waitUntilFirstUpdate:!0})],b.prototype,"handleOpenChange",1);b=l([M("wa-select")],b);/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var jo=class extends Event{constructor(){super("wa-remove",{bubbles:!0,cancelable:!1,composed:!0})}};/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Ko=A`
  @layer wa-component {
    :host {
      display: inline-flex;
      gap: 0.5em;
      border-radius: var(--wa-border-radius-m);
      align-items: center;
      background-color: var(--wa-color-fill-quiet, var(--wa-color-neutral-fill-quiet));
      border-color: var(--wa-color-border-normal, var(--wa-color-neutral-border-normal));
      border-style: var(--wa-border-style);
      border-width: var(--wa-border-width-s);
      color: var(--wa-color-on-quiet, var(--wa-color-neutral-on-quiet));
      font-size: inherit;
      line-height: 1;
      white-space: nowrap;
      user-select: none;
      -webkit-user-select: none;
      height: calc(var(--wa-form-control-height) * 0.8);
      line-height: calc(var(--wa-form-control-height) - var(--wa-form-control-border-width) * 2);
      padding: 0 0.75em;
    }

    /* Appearance modifiers */
    :host([appearance='outlined']) {
      color: var(--wa-color-on-quiet, var(--wa-color-neutral-on-quiet));
      background-color: transparent;
      border-color: var(--wa-color-border-loud, var(--wa-color-neutral-border-loud));
    }

    :host([appearance='filled']) {
      color: var(--wa-color-on-quiet, var(--wa-color-neutral-on-quiet));
      background-color: var(--wa-color-fill-quiet, var(--wa-color-neutral-fill-quiet));
      border-color: transparent;
    }

    :host([appearance='filled-outlined']) {
      color: var(--wa-color-on-quiet, var(--wa-color-neutral-on-quiet));
      background-color: var(--wa-color-fill-quiet, var(--wa-color-neutral-fill-quiet));
      border-color: var(--wa-color-border-normal, var(--wa-color-neutral-border-normal));
    }

    :host([appearance='accent']) {
      color: var(--wa-color-on-loud, var(--wa-color-neutral-on-loud));
      background-color: var(--wa-color-fill-loud, var(--wa-color-neutral-fill-loud));
      border-color: transparent;
    }
  }

  .content {
    font-size: var(--wa-font-size-smaller);
  }

  [part='remove-button'] {
    line-height: 1;
  }

  [part='remove-button']::part(base) {
    padding: 0;
    height: 1em;
    width: 1em;
    color: currentColor;
  }

  @media (hover: hover) {
    :host(:hover) > [part='remove-button']::part(base) {
      background-color: transparent;
      color: color-mix(in oklab, currentColor, var(--wa-color-mix-hover));
    }
  }

  :host(:active) > [part='remove-button']::part(base) {
    background-color: transparent;
    color: color-mix(in oklab, currentColor, var(--wa-color-mix-active));
  }

  /*
   * Pill modifier
   */
  :host([pill]) {
    border-radius: var(--wa-border-radius-pill);
  }
`;/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var le=A`
  :where(:root),
  .wa-neutral,
  :host([variant='neutral']) {
    --wa-color-fill-loud: var(--wa-color-neutral-fill-loud);
    --wa-color-fill-normal: var(--wa-color-neutral-fill-normal);
    --wa-color-fill-quiet: var(--wa-color-neutral-fill-quiet);
    --wa-color-border-loud: var(--wa-color-neutral-border-loud);
    --wa-color-border-normal: var(--wa-color-neutral-border-normal);
    --wa-color-border-quiet: var(--wa-color-neutral-border-quiet);
    --wa-color-on-loud: var(--wa-color-neutral-on-loud);
    --wa-color-on-normal: var(--wa-color-neutral-on-normal);
    --wa-color-on-quiet: var(--wa-color-neutral-on-quiet);
  }

  .wa-brand,
  :host([variant='brand']) {
    --wa-color-fill-loud: var(--wa-color-brand-fill-loud);
    --wa-color-fill-normal: var(--wa-color-brand-fill-normal);
    --wa-color-fill-quiet: var(--wa-color-brand-fill-quiet);
    --wa-color-border-loud: var(--wa-color-brand-border-loud);
    --wa-color-border-normal: var(--wa-color-brand-border-normal);
    --wa-color-border-quiet: var(--wa-color-brand-border-quiet);
    --wa-color-on-loud: var(--wa-color-brand-on-loud);
    --wa-color-on-normal: var(--wa-color-brand-on-normal);
    --wa-color-on-quiet: var(--wa-color-brand-on-quiet);
  }

  .wa-success,
  :host([variant='success']) {
    --wa-color-fill-loud: var(--wa-color-success-fill-loud);
    --wa-color-fill-normal: var(--wa-color-success-fill-normal);
    --wa-color-fill-quiet: var(--wa-color-success-fill-quiet);
    --wa-color-border-loud: var(--wa-color-success-border-loud);
    --wa-color-border-normal: var(--wa-color-success-border-normal);
    --wa-color-border-quiet: var(--wa-color-success-border-quiet);
    --wa-color-on-loud: var(--wa-color-success-on-loud);
    --wa-color-on-normal: var(--wa-color-success-on-normal);
    --wa-color-on-quiet: var(--wa-color-success-on-quiet);
  }

  .wa-warning,
  :host([variant='warning']) {
    --wa-color-fill-loud: var(--wa-color-warning-fill-loud);
    --wa-color-fill-normal: var(--wa-color-warning-fill-normal);
    --wa-color-fill-quiet: var(--wa-color-warning-fill-quiet);
    --wa-color-border-loud: var(--wa-color-warning-border-loud);
    --wa-color-border-normal: var(--wa-color-warning-border-normal);
    --wa-color-border-quiet: var(--wa-color-warning-border-quiet);
    --wa-color-on-loud: var(--wa-color-warning-on-loud);
    --wa-color-on-normal: var(--wa-color-warning-on-normal);
    --wa-color-on-quiet: var(--wa-color-warning-on-quiet);
  }

  .wa-danger,
  :host([variant='danger']) {
    --wa-color-fill-loud: var(--wa-color-danger-fill-loud);
    --wa-color-fill-normal: var(--wa-color-danger-fill-normal);
    --wa-color-fill-quiet: var(--wa-color-danger-fill-quiet);
    --wa-color-border-loud: var(--wa-color-danger-border-loud);
    --wa-color-border-normal: var(--wa-color-danger-border-normal);
    --wa-color-border-quiet: var(--wa-color-danger-border-quiet);
    --wa-color-on-loud: var(--wa-color-danger-on-loud);
    --wa-color-on-normal: var(--wa-color-danger-on-normal);
    --wa-color-on-quiet: var(--wa-color-danger-on-quiet);
  }
`;/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var pt=class extends O{constructor(){super(...arguments),this.localize=new R(this),this.variant="neutral",this.appearance="filled-outlined",this.size="medium",this.pill=!1,this.withRemove=!1}handleRemoveClick(){this.dispatchEvent(new jo)}render(){return E`
      <slot part="content" class="content"></slot>

      ${this.withRemove?E`
            <wa-button
              part="remove-button"
              exportparts="base:remove-button__base"
              class="remove"
              appearance="plain"
              @click=${this.handleRemoveClick}
              tabindex="-1"
            >
              <wa-icon name="xmark" library="system" variant="solid" label=${this.localize.term("remove")}></wa-icon>
            </wa-button>
          `:""}
    `}};pt.css=[Ko,le,kt];l([d({reflect:!0})],pt.prototype,"variant",2);l([d({reflect:!0})],pt.prototype,"appearance",2);l([d({reflect:!0})],pt.prototype,"size",2);l([d({type:Boolean,reflect:!0})],pt.prototype,"pill",2);l([d({attribute:"with-remove",type:Boolean})],pt.prototype,"withRemove",2);pt=l([M("wa-tag")],pt);/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Yo=A`
  :host {
    display: block;
    color: var(--wa-color-text-normal);
    -webkit-user-select: none;
    user-select: none;

    position: relative;
    display: flex;
    align-items: center;
    font: inherit;
    padding: 0.5em 1em 0.5em 0.25em;
    line-height: var(--wa-line-height-condensed);
    transition: fill var(--wa-transition-normal) var(--wa-transition-easing);
    cursor: pointer;
  }

  :host(:focus) {
    outline: none;
  }

  @media (hover: hover) {
    :host(:not([disabled], :state(current)):is(:state(hover), :hover)) {
      background-color: var(--wa-color-neutral-fill-normal);
      color: var(--wa-color-neutral-on-normal);
    }
  }

  :host(:state(current)),
  :host([disabled]:state(current)) {
    background-color: var(--wa-color-brand-fill-loud);
    color: var(--wa-color-brand-on-loud);
    opacity: 1;
  }

  :host([disabled]) {
    outline: none;
    opacity: 0.5;
    cursor: not-allowed;
  }

  .label {
    flex: 1 1 auto;
    display: inline-block;
  }

  .check {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: var(--wa-font-size-smaller);
    visibility: hidden;
    width: 2em;
  }

  :host(:state(selected)) .check {
    visibility: visible;
  }

  .start,
  .end {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
  }

  .start::slotted(*) {
    margin-inline-end: 0.5em;
  }

  .end::slotted(*) {
    margin-inline-start: 0.5em;
  }

  @media (forced-colors: active) {
    :host(:hover:not([aria-disabled='true'])) {
      outline: dashed 1px SelectedItem;
      outline-offset: -1px;
    }
  }
`;/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */function Ht(t,e=0){if(!t||!globalThis.Node)return"";if(typeof t[Symbol.iterator]=="function")return(Array.isArray(t)?t:[...t]).map(i=>Ht(i,--e)).join("");let o=t;if(o.nodeType===Node.TEXT_NODE)return o.textContent??"";if(o.nodeType===Node.ELEMENT_NODE){let r=o;if(r.hasAttribute("slot")||r.matches("style, script"))return"";if(r instanceof HTMLSlotElement){let i=r.assignedNodes({flatten:!0});if(i.length>0)return Ht(i,--e)}return e>-1?Ht(r,--e):r.textContent??""}return o.hasChildNodes()?Ht(o.childNodes,--e):""}var K=class extends O{constructor(){super(...arguments),this.localize=new R(this),this.isInitialized=!1,this.current=!1,this.value="",this.disabled=!1,this.selected=!1,this.defaultSelected=!1,this._label="",this.defaultLabel="",this.handleHover=t=>{t.type==="mouseenter"?this.customStates.set("hover",!0):t.type==="mouseleave"&&this.customStates.set("hover",!1)}}set label(t){let e=this._label;this._label=t||"",this._label!==e&&this.requestUpdate("label",e)}get label(){return this._label?this._label:(this.defaultLabel||this.updateDefaultLabel(),this.defaultLabel)}connectedCallback(){super.connectedCallback(),this.setAttribute("role","option"),this.setAttribute("aria-selected","false"),this.addEventListener("mouseenter",this.handleHover),this.addEventListener("mouseleave",this.handleHover),this.updateDefaultLabel()}disconnectedCallback(){super.disconnectedCallback(),this.removeEventListener("mouseenter",this.handleHover),this.removeEventListener("mouseleave",this.handleHover)}handleDefaultSlotChange(){this.updateDefaultLabel(),this.isInitialized?(customElements.whenDefined("wa-select").then(()=>{let t=this.closest("wa-select");t&&(t.handleDefaultSlotChange(),t.selectionChanged?.())}),customElements.whenDefined("wa-combobox").then(()=>{let t=this.closest("wa-combobox");t&&(t.handleDefaultSlotChange(),t.selectionChanged?.())})):this.isInitialized=!0}willUpdate(t){if(t.has("defaultSelected")&&!this.closest("wa-combobox, wa-select")?.hasInteracted){let e=this.selected;this.selected=this.defaultSelected,this.requestUpdate("selected",e)}super.willUpdate(t)}updated(t){super.updated(t),t.has("disabled")&&this.setAttribute("aria-disabled",this.disabled?"true":"false"),t.has("selected")&&(this.setAttribute("aria-selected",this.selected?"true":"false"),this.customStates.set("selected",this.selected),this.handleDefaultSlotChange()),t.has("value")&&(typeof this.value!="string"&&(this.value=String(this.value)),this.handleDefaultSlotChange()),t.has("current")&&this.customStates.set("current",this.current)}updateDefaultLabel(){let t=this.defaultLabel;this.defaultLabel=Ht(this).trim();let e=this.defaultLabel!==t;return!this._label&&e&&this.requestUpdate("label",t),e}render(){return E`
      <wa-icon
        part="checked-icon"
        class="check"
        name="check"
        library="system"
        variant="solid"
        aria-hidden="true"
      ></wa-icon>
      <slot part="start" name="start" class="start"></slot>
      <slot part="label" class="label" @slotchange=${this.handleDefaultSlotChange}></slot>
      <slot part="end" name="end" class="end"></slot>
    `}};K.css=Yo;l([T(".label")],K.prototype,"defaultSlot",2);l([D()],K.prototype,"current",2);l([d({reflect:!0})],K.prototype,"value",2);l([d({type:Boolean})],K.prototype,"disabled",2);l([d({type:Boolean,attribute:!1})],K.prototype,"selected",2);l([d({type:Boolean,attribute:"selected"})],K.prototype,"defaultSelected",2);l([d()],K.prototype,"label",1);l([D()],K.prototype,"defaultLabel",2);K=l([M("wa-option")],K);/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Xo=class extends Event{constructor(){super("wa-reposition",{bubbles:!0,cancelable:!1,composed:!0})}};/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Zo=A`
  :host {
    --arrow-color: black;
    --arrow-size: var(--wa-tooltip-arrow-size);
    --show-duration: 100ms;
    --hide-duration: 100ms;

    /*
     * These properties are computed to account for the arrow's dimensions after being rotated 45º. The constant
     * 0.7071 is derived from sin(45), which is the diagonal size of the arrow's container after rotating.
     */
    --arrow-size-diagonal: calc(var(--arrow-size) * 0.7071);
    --arrow-padding-offset: calc(var(--arrow-size-diagonal) - var(--arrow-size));

    display: contents;
  }

  .popup {
    position: absolute;
    isolation: isolate;
    max-width: var(--auto-size-available-width, none);
    max-height: var(--auto-size-available-height, none);

    /* Clear UA styles for [popover] */
    :where(&) {
      inset: unset;
      padding: unset;
      margin: unset;
      width: unset;
      height: unset;
      color: unset;
      background: unset;
      border: unset;
      overflow: unset;
    }
  }

  .popup-fixed {
    position: fixed;
  }

  .popup:not(.popup-active) {
    display: none;
  }

  .arrow {
    position: absolute;
    width: calc(var(--arrow-size-diagonal) * 2);
    height: calc(var(--arrow-size-diagonal) * 2);
    rotate: 45deg;
    background: var(--arrow-color);
    z-index: 3;
  }

  :host([data-current-placement~='left']) .arrow {
    rotate: -45deg;
  }

  :host([data-current-placement~='right']) .arrow {
    rotate: 135deg;
  }

  :host([data-current-placement~='bottom']) .arrow {
    rotate: 225deg;
  }

  /* Hover bridge */
  .popup-hover-bridge:not(.popup-hover-bridge-visible) {
    display: none;
  }

  .popup-hover-bridge {
    position: fixed;
    z-index: 899;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
    clip-path: polygon(
      var(--hover-bridge-top-left-x, 0) var(--hover-bridge-top-left-y, 0),
      var(--hover-bridge-top-right-x, 0) var(--hover-bridge-top-right-y, 0),
      var(--hover-bridge-bottom-right-x, 0) var(--hover-bridge-bottom-right-y, 0),
      var(--hover-bridge-bottom-left-x, 0) var(--hover-bridge-bottom-left-y, 0)
    );
  }

  /* Built-in animations */
  .show {
    animation: show var(--show-duration) ease;
  }

  .hide {
    animation: show var(--hide-duration) ease reverse;
  }

  @keyframes show {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  .show-with-scale {
    animation: show-with-scale var(--show-duration) ease;
  }

  .hide-with-scale {
    animation: show-with-scale var(--hide-duration) ease reverse;
  }

  @keyframes show-with-scale {
    from {
      opacity: 0;
      scale: 0.8;
    }
    to {
      opacity: 1;
      scale: 1;
    }
  }
`;/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var mt=Math.min,F=Math.max,he=Math.round,ce=Math.floor,et=t=>({x:t,y:t}),ei={left:"right",right:"left",bottom:"top",top:"bottom"},oi={start:"end",end:"start"};function Be(t,e,o){return F(t,mt(e,o))}function Tt(t,e){return typeof t=="function"?t(e):t}function vt(t){return t.split("-")[0]}function Rt(t){return t.split("-")[1]}function rr(t){return t==="x"?"y":"x"}function Ne(t){return t==="y"?"height":"width"}function ft(t){return["top","bottom"].includes(vt(t))?"y":"x"}function He(t){return rr(ft(t))}function ri(t,e,o){o===void 0&&(o=!1);let r=Rt(t),i=He(t),a=Ne(i),s=i==="x"?r===(o?"end":"start")?"right":"left":r==="start"?"bottom":"top";return e.reference[a]>e.floating[a]&&(s=pe(s)),[s,pe(s)]}function ii(t){let e=pe(t);return[qe(t),e,qe(e)]}function qe(t){return t.replace(/start|end/g,e=>oi[e])}function ai(t,e,o){let r=["left","right"],i=["right","left"],a=["top","bottom"],s=["bottom","top"];switch(t){case"top":case"bottom":return o?e?i:r:e?r:i;case"left":case"right":return e?a:s;default:return[]}}function si(t,e,o,r){let i=Rt(t),a=ai(vt(t),o==="start",r);return i&&(a=a.map(s=>s+"-"+i),e&&(a=a.concat(a.map(qe)))),a}function pe(t){return t.replace(/left|right|bottom|top/g,e=>ei[e])}function ni(t){return{top:0,right:0,bottom:0,left:0,...t}}function ir(t){return typeof t!="number"?ni(t):{top:t,right:t,bottom:t,left:t}}function fe(t){let{x:e,y:o,width:r,height:i}=t;return{width:r,height:i,top:o,left:e,right:e+r,bottom:o+i,x:e,y:o}}function Go(t,e,o){let{reference:r,floating:i}=t,a=ft(e),s=He(e),n=Ne(s),c=vt(e),u=a==="y",h=r.x+r.width/2-i.width/2,p=r.y+r.height/2-i.height/2,m=r[n]/2-i[n]/2,f;switch(c){case"top":f={x:h,y:r.y-i.height};break;case"bottom":f={x:h,y:r.y+r.height};break;case"right":f={x:r.x+r.width,y:p};break;case"left":f={x:r.x-i.width,y:p};break;default:f={x:r.x,y:r.y}}switch(Rt(e)){case"start":f[s]-=m*(o&&u?-1:1);break;case"end":f[s]+=m*(o&&u?-1:1);break}return f}var li=async(t,e,o)=>{let{placement:r="bottom",strategy:i="absolute",middleware:a=[],platform:s}=o,n=a.filter(Boolean),c=await(s.isRTL==null?void 0:s.isRTL(e)),u=await s.getElementRects({reference:t,floating:e,strategy:i}),{x:h,y:p}=Go(u,r,c),m=r,f={},v=0;for(let g=0;g<n.length;g++){let{name:y,fn:w}=n[g],{x,y:_,data:k,reset:S}=await w({x:h,y:p,initialPlacement:r,placement:m,strategy:i,middlewareData:f,rects:u,platform:s,elements:{reference:t,floating:e}});h=x??h,p=_??p,f={...f,[y]:{...f[y],...k}},S&&v<=50&&(v++,typeof S=="object"&&(S.placement&&(m=S.placement),S.rects&&(u=S.rects===!0?await s.getElementRects({reference:t,floating:e,strategy:i}):S.rects),{x:h,y:p}=Go(u,m,c)),g=-1)}return{x:h,y:p,placement:m,strategy:i,middlewareData:f}};async function Ue(t,e){var o;e===void 0&&(e={});let{x:r,y:i,platform:a,rects:s,elements:n,strategy:c}=t,{boundary:u="clippingAncestors",rootBoundary:h="viewport",elementContext:p="floating",altBoundary:m=!1,padding:f=0}=Tt(e,t),v=ir(f),y=n[m?p==="floating"?"reference":"floating":p],w=fe(await a.getClippingRect({element:(o=await(a.isElement==null?void 0:a.isElement(y)))==null||o?y:y.contextElement||await(a.getDocumentElement==null?void 0:a.getDocumentElement(n.floating)),boundary:u,rootBoundary:h,strategy:c})),x=p==="floating"?{x:r,y:i,width:s.floating.width,height:s.floating.height}:s.reference,_=await(a.getOffsetParent==null?void 0:a.getOffsetParent(n.floating)),k=await(a.isElement==null?void 0:a.isElement(_))?await(a.getScale==null?void 0:a.getScale(_))||{x:1,y:1}:{x:1,y:1},S=fe(a.convertOffsetParentRelativeRectToViewportRelativeRect?await a.convertOffsetParentRelativeRectToViewportRelativeRect({elements:n,rect:x,offsetParent:_,strategy:c}):x);return{top:(w.top-S.top+v.top)/k.y,bottom:(S.bottom-w.bottom+v.bottom)/k.y,left:(w.left-S.left+v.left)/k.x,right:(S.right-w.right+v.right)/k.x}}var ci=t=>({name:"arrow",options:t,async fn(e){let{x:o,y:r,placement:i,rects:a,platform:s,elements:n,middlewareData:c}=e,{element:u,padding:h=0}=Tt(t,e)||{};if(u==null)return{};let p=ir(h),m={x:o,y:r},f=He(i),v=Ne(f),g=await s.getDimensions(u),y=f==="y",w=y?"top":"left",x=y?"bottom":"right",_=y?"clientHeight":"clientWidth",k=a.reference[v]+a.reference[f]-m[f]-a.floating[v],S=m[f]-a.reference[f],N=await(s.getOffsetParent==null?void 0:s.getOffsetParent(u)),P=N?N[_]:0;(!P||!await(s.isElement==null?void 0:s.isElement(N)))&&(P=n.floating[_]||a.floating[v]);let at=k/2-S/2,G=P/2-g[v]/2-1,B=mt(p[w],G),lt=mt(p[x],G),J=B,ct=P-g[v]-lt,Q=P/2-g[v]/2+at,H=Be(J,Q,ct),wt=!c.arrow&&Rt(i)!=null&&Q!==H&&a.reference[v]/2-(Q<J?B:lt)-g[v]/2<0,st=wt?Q<J?Q-J:Q-ct:0;return{[f]:m[f]+st,data:{[f]:H,centerOffset:Q-H-st,...wt&&{alignmentOffset:st}},reset:wt}}}),di=function(t){return t===void 0&&(t={}),{name:"flip",options:t,async fn(e){var o,r;let{placement:i,middlewareData:a,rects:s,initialPlacement:n,platform:c,elements:u}=e,{mainAxis:h=!0,crossAxis:p=!0,fallbackPlacements:m,fallbackStrategy:f="bestFit",fallbackAxisSideDirection:v="none",flipAlignment:g=!0,...y}=Tt(t,e);if((o=a.arrow)!=null&&o.alignmentOffset)return{};let w=vt(i),x=ft(n),_=vt(n)===n,k=await(c.isRTL==null?void 0:c.isRTL(u.floating)),S=m||(_||!g?[pe(n)]:ii(n)),N=v!=="none";!m&&N&&S.push(...si(n,g,v,k));let P=[n,...S],at=await Ue(e,y),G=[],B=((r=a.flip)==null?void 0:r.overflows)||[];if(h&&G.push(at[w]),p){let H=ri(i,s,k);G.push(at[H[0]],at[H[1]])}if(B=[...B,{placement:i,overflows:G}],!G.every(H=>H<=0)){var lt,J;let H=(((lt=a.flip)==null?void 0:lt.index)||0)+1,wt=P[H];if(wt){var ct;let dt=p==="alignment"?x!==ft(wt):!1,tt=((ct=B[0])==null?void 0:ct.overflows[0])>0;if(!dt||tt)return{data:{index:H,overflows:B},reset:{placement:wt}}}let st=(J=B.filter(dt=>dt.overflows[0]<=0).sort((dt,tt)=>dt.overflows[1]-tt.overflows[1])[0])==null?void 0:J.placement;if(!st)switch(f){case"bestFit":{var Q;let dt=(Q=B.filter(tt=>{if(N){let ut=ft(tt.placement);return ut===x||ut==="y"}return!0}).map(tt=>[tt.placement,tt.overflows.filter(ut=>ut>0).reduce((ut,Pr)=>ut+Pr,0)]).sort((tt,ut)=>tt[1]-ut[1])[0])==null?void 0:Q[0];dt&&(st=dt);break}case"initialPlacement":st=n;break}if(i!==st)return{reset:{placement:st}}}return{}}}};async function ui(t,e){let{placement:o,platform:r,elements:i}=t,a=await(r.isRTL==null?void 0:r.isRTL(i.floating)),s=vt(o),n=Rt(o),c=ft(o)==="y",u=["left","top"].includes(s)?-1:1,h=a&&c?-1:1,p=Tt(e,t),{mainAxis:m,crossAxis:f,alignmentAxis:v}=typeof p=="number"?{mainAxis:p,crossAxis:0,alignmentAxis:null}:{mainAxis:p.mainAxis||0,crossAxis:p.crossAxis||0,alignmentAxis:p.alignmentAxis};return n&&typeof v=="number"&&(f=n==="end"?v*-1:v),c?{x:f*h,y:m*u}:{x:m*u,y:f*h}}var hi=function(t){return t===void 0&&(t=0),{name:"offset",options:t,async fn(e){var o,r;let{x:i,y:a,placement:s,middlewareData:n}=e,c=await ui(e,t);return s===((o=n.offset)==null?void 0:o.placement)&&(r=n.arrow)!=null&&r.alignmentOffset?{}:{x:i+c.x,y:a+c.y,data:{...c,placement:s}}}}},pi=function(t){return t===void 0&&(t={}),{name:"shift",options:t,async fn(e){let{x:o,y:r,placement:i}=e,{mainAxis:a=!0,crossAxis:s=!1,limiter:n={fn:y=>{let{x:w,y:x}=y;return{x:w,y:x}}},...c}=Tt(t,e),u={x:o,y:r},h=await Ue(e,c),p=ft(vt(i)),m=rr(p),f=u[m],v=u[p];if(a){let y=m==="y"?"top":"left",w=m==="y"?"bottom":"right",x=f+h[y],_=f-h[w];f=Be(x,f,_)}if(s){let y=p==="y"?"top":"left",w=p==="y"?"bottom":"right",x=v+h[y],_=v-h[w];v=Be(x,v,_)}let g=n.fn({...e,[m]:f,[p]:v});return{...g,data:{x:g.x-o,y:g.y-r,enabled:{[m]:a,[p]:s}}}}}},fi=function(t){return t===void 0&&(t={}),{name:"size",options:t,async fn(e){var o,r;let{placement:i,rects:a,platform:s,elements:n}=e,{apply:c=()=>{},...u}=Tt(t,e),h=await Ue(e,u),p=vt(i),m=Rt(i),f=ft(i)==="y",{width:v,height:g}=a.floating,y,w;p==="top"||p==="bottom"?(y=p,w=m===(await(s.isRTL==null?void 0:s.isRTL(n.floating))?"start":"end")?"left":"right"):(w=p,y=m==="end"?"top":"bottom");let x=g-h.top-h.bottom,_=v-h.left-h.right,k=mt(g-h[y],x),S=mt(v-h[w],_),N=!e.middlewareData.shift,P=k,at=S;if((o=e.middlewareData.shift)!=null&&o.enabled.x&&(at=_),(r=e.middlewareData.shift)!=null&&r.enabled.y&&(P=x),N&&!m){let B=F(h.left,0),lt=F(h.right,0),J=F(h.top,0),ct=F(h.bottom,0);f?at=v-2*(B!==0||lt!==0?B+lt:F(h.left,h.right)):P=g-2*(J!==0||ct!==0?J+ct:F(h.top,h.bottom))}await c({...e,availableWidth:at,availableHeight:P});let G=await s.getDimensions(n.floating);return v!==G.width||g!==G.height?{reset:{rects:!0}}:{}}}};function me(){return typeof window<"u"}function Dt(t){return ar(t)?(t.nodeName||"").toLowerCase():"#document"}function I(t){var e;return(t==null||(e=t.ownerDocument)==null?void 0:e.defaultView)||window}function rt(t){var e;return(e=(ar(t)?t.ownerDocument:t.document)||window.document)==null?void 0:e.documentElement}function ar(t){return me()?t instanceof Node||t instanceof I(t).Node:!1}function Y(t){return me()?t instanceof Element||t instanceof I(t).Element:!1}function ot(t){return me()?t instanceof HTMLElement||t instanceof I(t).HTMLElement:!1}function Jo(t){return!me()||typeof ShadowRoot>"u"?!1:t instanceof ShadowRoot||t instanceof I(t).ShadowRoot}function Ut(t){let{overflow:e,overflowX:o,overflowY:r,display:i}=X(t);return/auto|scroll|overlay|hidden|clip/.test(e+r+o)&&!["inline","contents"].includes(i)}function mi(t){return["table","td","th"].includes(Dt(t))}function ve(t){return[":popover-open",":modal"].some(e=>{try{return t.matches(e)}catch{return!1}})}function ge(t){let e=We(),o=Y(t)?X(t):t;return["transform","translate","scale","rotate","perspective"].some(r=>o[r]?o[r]!=="none":!1)||(o.containerType?o.containerType!=="normal":!1)||!e&&(o.backdropFilter?o.backdropFilter!=="none":!1)||!e&&(o.filter?o.filter!=="none":!1)||["transform","translate","scale","rotate","perspective","filter"].some(r=>(o.willChange||"").includes(r))||["paint","layout","strict","content"].some(r=>(o.contain||"").includes(r))}function vi(t){let e=gt(t);for(;ot(e)&&!Pt(e);){if(ge(e))return e;if(ve(e))return null;e=gt(e)}return null}function We(){return typeof CSS>"u"||!CSS.supports?!1:CSS.supports("-webkit-backdrop-filter","none")}function Pt(t){return["html","body","#document"].includes(Dt(t))}function X(t){return I(t).getComputedStyle(t)}function we(t){return Y(t)?{scrollLeft:t.scrollLeft,scrollTop:t.scrollTop}:{scrollLeft:t.scrollX,scrollTop:t.scrollY}}function gt(t){if(Dt(t)==="html")return t;let e=t.assignedSlot||t.parentNode||Jo(t)&&t.host||rt(t);return Jo(e)?e.host:e}function sr(t){let e=gt(t);return Pt(e)?t.ownerDocument?t.ownerDocument.body:t.body:ot(e)&&Ut(e)?e:sr(e)}function Mt(t,e,o){var r;e===void 0&&(e=[]),o===void 0&&(o=!0);let i=sr(t),a=i===((r=t.ownerDocument)==null?void 0:r.body),s=I(i);if(a){let n=Ve(s);return e.concat(s,s.visualViewport||[],Ut(i)?i:[],n&&o?Mt(n):[])}return e.concat(i,Mt(i,[],o))}function Ve(t){return t.parent&&Object.getPrototypeOf(t.parent)?t.frameElement:null}function nr(t){let e=X(t),o=parseFloat(e.width)||0,r=parseFloat(e.height)||0,i=ot(t),a=i?t.offsetWidth:o,s=i?t.offsetHeight:r,n=he(o)!==a||he(r)!==s;return n&&(o=a,r=s),{width:o,height:r,$:n}}function je(t){return Y(t)?t:t.contextElement}function zt(t){let e=je(t);if(!ot(e))return et(1);let o=e.getBoundingClientRect(),{width:r,height:i,$:a}=nr(e),s=(a?he(o.width):o.width)/r,n=(a?he(o.height):o.height)/i;return(!s||!Number.isFinite(s))&&(s=1),(!n||!Number.isFinite(n))&&(n=1),{x:s,y:n}}var gi=et(0);function lr(t){let e=I(t);return!We()||!e.visualViewport?gi:{x:e.visualViewport.offsetLeft,y:e.visualViewport.offsetTop}}function wi(t,e,o){return e===void 0&&(e=!1),!o||e&&o!==I(t)?!1:e}function _t(t,e,o,r){e===void 0&&(e=!1),o===void 0&&(o=!1);let i=t.getBoundingClientRect(),a=je(t),s=et(1);e&&(r?Y(r)&&(s=zt(r)):s=zt(t));let n=wi(a,o,r)?lr(a):et(0),c=(i.left+n.x)/s.x,u=(i.top+n.y)/s.y,h=i.width/s.x,p=i.height/s.y;if(a){let m=I(a),f=r&&Y(r)?I(r):r,v=m,g=Ve(v);for(;g&&r&&f!==v;){let y=zt(g),w=g.getBoundingClientRect(),x=X(g),_=w.left+(g.clientLeft+parseFloat(x.paddingLeft))*y.x,k=w.top+(g.clientTop+parseFloat(x.paddingTop))*y.y;c*=y.x,u*=y.y,h*=y.x,p*=y.y,c+=_,u+=k,v=I(g),g=Ve(v)}}return fe({width:h,height:p,x:c,y:u})}function Ke(t,e){let o=we(t).scrollLeft;return e?e.left+o:_t(rt(t)).left+o}function cr(t,e,o){o===void 0&&(o=!1);let r=t.getBoundingClientRect(),i=r.left+e.scrollLeft-(o?0:Ke(t,r)),a=r.top+e.scrollTop;return{x:i,y:a}}function bi(t){let{elements:e,rect:o,offsetParent:r,strategy:i}=t,a=i==="fixed",s=rt(r),n=e?ve(e.floating):!1;if(r===s||n&&a)return o;let c={scrollLeft:0,scrollTop:0},u=et(1),h=et(0),p=ot(r);if((p||!p&&!a)&&((Dt(r)!=="body"||Ut(s))&&(c=we(r)),ot(r))){let f=_t(r);u=zt(r),h.x=f.x+r.clientLeft,h.y=f.y+r.clientTop}let m=s&&!p&&!a?cr(s,c,!0):et(0);return{width:o.width*u.x,height:o.height*u.y,x:o.x*u.x-c.scrollLeft*u.x+h.x+m.x,y:o.y*u.y-c.scrollTop*u.y+h.y+m.y}}function yi(t){return Array.from(t.getClientRects())}function xi(t){let e=rt(t),o=we(t),r=t.ownerDocument.body,i=F(e.scrollWidth,e.clientWidth,r.scrollWidth,r.clientWidth),a=F(e.scrollHeight,e.clientHeight,r.scrollHeight,r.clientHeight),s=-o.scrollLeft+Ke(t),n=-o.scrollTop;return X(r).direction==="rtl"&&(s+=F(e.clientWidth,r.clientWidth)-i),{width:i,height:a,x:s,y:n}}function Ci(t,e){let o=I(t),r=rt(t),i=o.visualViewport,a=r.clientWidth,s=r.clientHeight,n=0,c=0;if(i){a=i.width,s=i.height;let u=We();(!u||u&&e==="fixed")&&(n=i.offsetLeft,c=i.offsetTop)}return{width:a,height:s,x:n,y:c}}function Li(t,e){let o=_t(t,!0,e==="fixed"),r=o.top+t.clientTop,i=o.left+t.clientLeft,a=ot(t)?zt(t):et(1),s=t.clientWidth*a.x,n=t.clientHeight*a.y,c=i*a.x,u=r*a.y;return{width:s,height:n,x:c,y:u}}function Qo(t,e,o){let r;if(e==="viewport")r=Ci(t,o);else if(e==="document")r=xi(rt(t));else if(Y(e))r=Li(e,o);else{let i=lr(t);r={x:e.x-i.x,y:e.y-i.y,width:e.width,height:e.height}}return fe(r)}function dr(t,e){let o=gt(t);return o===e||!Y(o)||Pt(o)?!1:X(o).position==="fixed"||dr(o,e)}function _i(t,e){let o=e.get(t);if(o)return o;let r=Mt(t,[],!1).filter(n=>Y(n)&&Dt(n)!=="body"),i=null,a=X(t).position==="fixed",s=a?gt(t):t;for(;Y(s)&&!Pt(s);){let n=X(s),c=ge(s);!c&&n.position==="fixed"&&(i=null),(a?!c&&!i:!c&&n.position==="static"&&!!i&&["absolute","fixed"].includes(i.position)||Ut(s)&&!c&&dr(t,s))?r=r.filter(h=>h!==s):i=n,s=gt(s)}return e.set(t,r),r}function Ei(t){let{element:e,boundary:o,rootBoundary:r,strategy:i}=t,s=[...o==="clippingAncestors"?ve(e)?[]:_i(e,this._c):[].concat(o),r],n=s[0],c=s.reduce((u,h)=>{let p=Qo(e,h,i);return u.top=F(p.top,u.top),u.right=mt(p.right,u.right),u.bottom=mt(p.bottom,u.bottom),u.left=F(p.left,u.left),u},Qo(e,n,i));return{width:c.right-c.left,height:c.bottom-c.top,x:c.left,y:c.top}}function Ai(t){let{width:e,height:o}=nr(t);return{width:e,height:o}}function $i(t,e,o){let r=ot(e),i=rt(e),a=o==="fixed",s=_t(t,!0,a,e),n={scrollLeft:0,scrollTop:0},c=et(0);function u(){c.x=Ke(i)}if(r||!r&&!a)if((Dt(e)!=="body"||Ut(i))&&(n=we(e)),r){let f=_t(e,!0,a,e);c.x=f.x+e.clientLeft,c.y=f.y+e.clientTop}else i&&u();a&&!r&&i&&u();let h=i&&!r&&!a?cr(i,n):et(0),p=s.left+n.scrollLeft-c.x-h.x,m=s.top+n.scrollTop-c.y-h.y;return{x:p,y:m,width:s.width,height:s.height}}function Fe(t){return X(t).position==="static"}function tr(t,e){if(!ot(t)||X(t).position==="fixed")return null;if(e)return e(t);let o=t.offsetParent;return rt(t)===o&&(o=o.ownerDocument.body),o}function ur(t,e){let o=I(t);if(ve(t))return o;if(!ot(t)){let i=gt(t);for(;i&&!Pt(i);){if(Y(i)&&!Fe(i))return i;i=gt(i)}return o}let r=tr(t,e);for(;r&&mi(r)&&Fe(r);)r=tr(r,e);return r&&Pt(r)&&Fe(r)&&!ge(r)?o:r||vi(t)||o}var Si=async function(t){let e=this.getOffsetParent||ur,o=this.getDimensions,r=await o(t.floating);return{reference:$i(t.reference,await e(t.floating),t.strategy),floating:{x:0,y:0,width:r.width,height:r.height}}};function ki(t){return X(t).direction==="rtl"}var ue={convertOffsetParentRelativeRectToViewportRelativeRect:bi,getDocumentElement:rt,getClippingRect:Ei,getOffsetParent:ur,getElementRects:Si,getClientRects:yi,getDimensions:Ai,getScale:zt,isElement:Y,isRTL:ki};function hr(t,e){return t.x===e.x&&t.y===e.y&&t.width===e.width&&t.height===e.height}function Oi(t,e){let o=null,r,i=rt(t);function a(){var n;clearTimeout(r),(n=o)==null||n.disconnect(),o=null}function s(n,c){n===void 0&&(n=!1),c===void 0&&(c=1),a();let u=t.getBoundingClientRect(),{left:h,top:p,width:m,height:f}=u;if(n||e(),!m||!f)return;let v=ce(p),g=ce(i.clientWidth-(h+m)),y=ce(i.clientHeight-(p+f)),w=ce(h),_={rootMargin:-v+"px "+-g+"px "+-y+"px "+-w+"px",threshold:F(0,mt(1,c))||1},k=!0;function S(N){let P=N[0].intersectionRatio;if(P!==c){if(!k)return s();P?s(!1,P):r=setTimeout(()=>{s(!1,1e-7)},1e3)}P===1&&!hr(u,t.getBoundingClientRect())&&s(),k=!1}try{o=new IntersectionObserver(S,{..._,root:i.ownerDocument})}catch{o=new IntersectionObserver(S,_)}o.observe(t)}return s(!0),a}function zi(t,e,o,r){r===void 0&&(r={});let{ancestorScroll:i=!0,ancestorResize:a=!0,elementResize:s=typeof ResizeObserver=="function",layoutShift:n=typeof IntersectionObserver=="function",animationFrame:c=!1}=r,u=je(t),h=i||a?[...u?Mt(u):[],...Mt(e)]:[];h.forEach(w=>{i&&w.addEventListener("scroll",o,{passive:!0}),a&&w.addEventListener("resize",o)});let p=u&&n?Oi(u,o):null,m=-1,f=null;s&&(f=new ResizeObserver(w=>{let[x]=w;x&&x.target===u&&f&&(f.unobserve(e),cancelAnimationFrame(m),m=requestAnimationFrame(()=>{var _;(_=f)==null||_.observe(e)})),o()}),u&&!c&&f.observe(u),f.observe(e));let v,g=c?_t(t):null;c&&y();function y(){let w=_t(t);g&&!hr(g,w)&&o(),g=w,v=requestAnimationFrame(y)}return o(),()=>{var w;h.forEach(x=>{i&&x.removeEventListener("scroll",o),a&&x.removeEventListener("resize",o)}),p?.(),(w=f)==null||w.disconnect(),f=null,c&&cancelAnimationFrame(v)}}var Pi=hi,Mi=pi,Ti=di,er=fi,Ri=ci,Di=(t,e,o)=>{let r=new Map,i={platform:ue,...o},a={...i.platform,_c:r};return li(t,e,{...i,platform:a})};function Fi(t){return Ii(t)}function Ie(t){return t.assignedSlot?t.assignedSlot:t.parentNode instanceof ShadowRoot?t.parentNode.host:t.parentNode}function Ii(t){for(let e=t;e;e=Ie(e))if(e instanceof Element&&getComputedStyle(e).display==="none")return null;for(let e=Ie(t);e;e=Ie(e)){if(!(e instanceof Element))continue;let o=getComputedStyle(e);if(o.display!=="contents"&&(o.position!=="static"||ge(o)||e.tagName==="BODY"))return e}return null}function or(t){return t!==null&&typeof t=="object"&&"getBoundingClientRect"in t&&("contextElement"in t?t instanceof Element:!0)}var de=globalThis?.HTMLElement?.prototype.hasOwnProperty("popover"),L=class extends O{constructor(){super(...arguments),this.localize=new R(this),this.active=!1,this.placement="top",this.boundary="viewport",this.distance=0,this.skidding=0,this.arrow=!1,this.arrowPlacement="anchor",this.arrowPadding=10,this.flip=!1,this.flipFallbackPlacements="",this.flipFallbackStrategy="best-fit",this.flipPadding=0,this.shift=!1,this.shiftPadding=0,this.autoSizePadding=0,this.hoverBridge=!1,this.updateHoverBridge=()=>{if(this.hoverBridge&&this.anchorEl&&this.popup){let t=this.anchorEl.getBoundingClientRect(),e=this.popup.getBoundingClientRect(),o=this.placement.includes("top")||this.placement.includes("bottom"),r=0,i=0,a=0,s=0,n=0,c=0,u=0,h=0;o?t.top<e.top?(r=t.left,i=t.bottom,a=t.right,s=t.bottom,n=e.left,c=e.top,u=e.right,h=e.top):(r=e.left,i=e.bottom,a=e.right,s=e.bottom,n=t.left,c=t.top,u=t.right,h=t.top):t.left<e.left?(r=t.right,i=t.top,a=e.left,s=e.top,n=t.right,c=t.bottom,u=e.left,h=e.bottom):(r=e.right,i=e.top,a=t.left,s=t.top,n=e.right,c=e.bottom,u=t.left,h=t.bottom),this.style.setProperty("--hover-bridge-top-left-x",`${r}px`),this.style.setProperty("--hover-bridge-top-left-y",`${i}px`),this.style.setProperty("--hover-bridge-top-right-x",`${a}px`),this.style.setProperty("--hover-bridge-top-right-y",`${s}px`),this.style.setProperty("--hover-bridge-bottom-left-x",`${n}px`),this.style.setProperty("--hover-bridge-bottom-left-y",`${c}px`),this.style.setProperty("--hover-bridge-bottom-right-x",`${u}px`),this.style.setProperty("--hover-bridge-bottom-right-y",`${h}px`)}}}async connectedCallback(){super.connectedCallback(),await this.updateComplete,this.start()}disconnectedCallback(){super.disconnectedCallback(),this.stop()}async updated(t){super.updated(t),t.has("active")&&(this.active?this.start():this.stop()),t.has("anchor")&&this.handleAnchorChange(),this.active&&(await this.updateComplete,this.reposition())}async handleAnchorChange(){if(await this.stop(),this.anchor&&typeof this.anchor=="string"){let t=this.getRootNode();this.anchorEl=t.getElementById(this.anchor)}else this.anchor instanceof Element||or(this.anchor)?this.anchorEl=this.anchor:this.anchorEl=this.querySelector('[slot="anchor"]');this.anchorEl instanceof HTMLSlotElement&&(this.anchorEl=this.anchorEl.assignedElements({flatten:!0})[0]),this.anchorEl&&this.start()}start(){!this.anchorEl||!this.active||!this.isConnected||(this.popup?.showPopover?.(),this.cleanup=zi(this.anchorEl,this.popup,()=>{this.reposition()}))}async stop(){return new Promise(t=>{this.popup?.hidePopover?.(),this.cleanup?(this.cleanup(),this.cleanup=void 0,this.removeAttribute("data-current-placement"),this.style.removeProperty("--auto-size-available-width"),this.style.removeProperty("--auto-size-available-height"),requestAnimationFrame(()=>t())):t()})}reposition(){if(!this.active||!this.anchorEl||!this.popup)return;let t=[Pi({mainAxis:this.distance,crossAxis:this.skidding})];this.sync?t.push(er({apply:({rects:r})=>{let i=this.sync==="width"||this.sync==="both",a=this.sync==="height"||this.sync==="both";this.popup.style.width=i?`${r.reference.width}px`:"",this.popup.style.height=a?`${r.reference.height}px`:""}})):(this.popup.style.width="",this.popup.style.height="");let e;de&&!or(this.anchor)&&this.boundary==="scroll"&&(e=Mt(this.anchorEl).filter(r=>r instanceof Element)),this.flip&&t.push(Ti({boundary:this.flipBoundary||e,fallbackPlacements:this.flipFallbackPlacements,fallbackStrategy:this.flipFallbackStrategy==="best-fit"?"bestFit":"initialPlacement",padding:this.flipPadding})),this.shift&&t.push(Mi({boundary:this.shiftBoundary||e,padding:this.shiftPadding})),this.autoSize?t.push(er({boundary:this.autoSizeBoundary||e,padding:this.autoSizePadding,apply:({availableWidth:r,availableHeight:i})=>{this.autoSize==="vertical"||this.autoSize==="both"?this.style.setProperty("--auto-size-available-height",`${i}px`):this.style.removeProperty("--auto-size-available-height"),this.autoSize==="horizontal"||this.autoSize==="both"?this.style.setProperty("--auto-size-available-width",`${r}px`):this.style.removeProperty("--auto-size-available-width")}})):(this.style.removeProperty("--auto-size-available-width"),this.style.removeProperty("--auto-size-available-height")),this.arrow&&t.push(Ri({element:this.arrowEl,padding:this.arrowPadding}));let o=de?r=>ue.getOffsetParent(r,Fi):ue.getOffsetParent;Di(this.anchorEl,this.popup,{placement:this.placement,middleware:t,strategy:de?"absolute":"fixed",platform:{...ue,getOffsetParent:o}}).then(({x:r,y:i,middlewareData:a,placement:s})=>{let n=this.localize.dir()==="rtl",c={top:"bottom",right:"left",bottom:"top",left:"right"}[s.split("-")[0]];if(this.setAttribute("data-current-placement",s),Object.assign(this.popup.style,{left:`${r}px`,top:`${i}px`}),this.arrow){let u=a.arrow.x,h=a.arrow.y,p="",m="",f="",v="";if(this.arrowPlacement==="start"){let g=typeof u=="number"?`calc(${this.arrowPadding}px - var(--arrow-padding-offset))`:"";p=typeof h=="number"?`calc(${this.arrowPadding}px - var(--arrow-padding-offset))`:"",m=n?g:"",v=n?"":g}else if(this.arrowPlacement==="end"){let g=typeof u=="number"?`calc(${this.arrowPadding}px - var(--arrow-padding-offset))`:"";m=n?"":g,v=n?g:"",f=typeof h=="number"?`calc(${this.arrowPadding}px - var(--arrow-padding-offset))`:""}else this.arrowPlacement==="center"?(v=typeof u=="number"?"calc(50% - var(--arrow-size-diagonal))":"",p=typeof h=="number"?"calc(50% - var(--arrow-size-diagonal))":""):(v=typeof u=="number"?`${u}px`:"",p=typeof h=="number"?`${h}px`:"");Object.assign(this.arrowEl.style,{top:p,right:m,bottom:f,left:v,[c]:"calc(var(--arrow-size-diagonal) * -1)"})}}),requestAnimationFrame(()=>this.updateHoverBridge()),this.dispatchEvent(new Xo)}render(){return E`
      <slot name="anchor" @slotchange=${this.handleAnchorChange}></slot>

      <span
        part="hover-bridge"
        class=${V({"popup-hover-bridge":!0,"popup-hover-bridge-visible":this.hoverBridge&&this.active})}
      ></span>

      <div
        popover="manual"
        part="popup"
        class=${V({popup:!0,"popup-active":this.active,"popup-fixed":!de,"popup-has-arrow":this.arrow})}
      >
        <slot></slot>
        ${this.arrow?E`<div part="arrow" class="arrow" role="presentation"></div>`:""}
      </div>
    `}};L.css=Zo;l([T(".popup")],L.prototype,"popup",2);l([T(".arrow")],L.prototype,"arrowEl",2);l([d()],L.prototype,"anchor",2);l([d({type:Boolean,reflect:!0})],L.prototype,"active",2);l([d({reflect:!0})],L.prototype,"placement",2);l([d()],L.prototype,"boundary",2);l([d({type:Number})],L.prototype,"distance",2);l([d({type:Number})],L.prototype,"skidding",2);l([d({type:Boolean})],L.prototype,"arrow",2);l([d({attribute:"arrow-placement"})],L.prototype,"arrowPlacement",2);l([d({attribute:"arrow-padding",type:Number})],L.prototype,"arrowPadding",2);l([d({type:Boolean})],L.prototype,"flip",2);l([d({attribute:"flip-fallback-placements",converter:{fromAttribute:t=>t.split(" ").map(e=>e.trim()).filter(e=>e!==""),toAttribute:t=>t.join(" ")}})],L.prototype,"flipFallbackPlacements",2);l([d({attribute:"flip-fallback-strategy"})],L.prototype,"flipFallbackStrategy",2);l([d({type:Object})],L.prototype,"flipBoundary",2);l([d({attribute:"flip-padding",type:Number})],L.prototype,"flipPadding",2);l([d({type:Boolean})],L.prototype,"shift",2);l([d({type:Object})],L.prototype,"shiftBoundary",2);l([d({attribute:"shift-padding",type:Number})],L.prototype,"shiftPadding",2);l([d({attribute:"auto-size"})],L.prototype,"autoSize",2);l([d()],L.prototype,"sync",2);l([d({type:Object})],L.prototype,"autoSizeBoundary",2);l([d({attribute:"auto-size-padding",type:Number})],L.prototype,"autoSizePadding",2);l([d({attribute:"hover-bridge",type:Boolean})],L.prototype,"hoverBridge",2);L=l([M("wa-popup")],L);/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var pr=()=>({checkValidity(t){let e=t.input,o={message:"",isValid:!0,invalidKeys:[]};if(!e)return o;let r=!0;if("checkValidity"in e&&(r=e.checkValidity()),r)return o;if(o.isValid=!1,"validationMessage"in e&&(o.message=e.validationMessage),!("validity"in e))return o.invalidKeys.push("customError"),o;for(let i in e.validity){if(i==="valid")continue;let a=i;e.validity[a]&&o.invalidKeys.push(a)}return o}});/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var fr=A`
  @layer wa-component {
    :host {
      display: inline-block;

      /* Workaround because Chrome doesn't like :host(:has()) below
       * https://issues.chromium.org/issues/40062355
       * Firefox doesn't like this nested rule, so both are needed */
      &:has(wa-badge) {
        position: relative;
      }
    }

    /* Apply relative positioning only when needed to position wa-badge
     * This avoids creating a new stacking context for every button */
    :host(:has(wa-badge)) {
      position: relative;
    }
  }

  .button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    user-select: none;
    -webkit-user-select: none;
    white-space: nowrap;
    vertical-align: middle;
    transition-property: background, border, box-shadow, color, opacity;
    transition-duration: var(--wa-transition-fast);
    transition-timing-function: var(--wa-transition-easing);
    cursor: pointer;
    padding: 0 var(--wa-form-control-padding-inline);
    font-family: inherit;
    font-size: inherit;
    font-weight: var(--wa-font-weight-action);
    line-height: calc(var(--wa-form-control-height) - var(--border-width) * 2);
    height: var(--wa-form-control-height);
    width: 100%;

    background-color: var(--wa-color-fill-loud, var(--wa-color-neutral-fill-loud));
    border-color: transparent;
    color: var(--wa-color-on-loud, var(--wa-color-neutral-on-loud));
    border-radius: var(--wa-form-control-border-radius);
    border-style: var(--wa-border-style);
    border-width: var(--wa-border-width-s);
  }

  /* Appearance modifiers */
  :host([appearance='plain']) {
    .button {
      color: var(--wa-color-on-quiet, var(--wa-color-neutral-on-quiet));
      background-color: transparent;
      border-color: transparent;
    }
    @media (hover: hover) {
      .button:not(.disabled):not(.loading):hover {
        color: var(--wa-color-on-quiet, var(--wa-color-neutral-on-quiet));
        background-color: var(--wa-color-fill-quiet, var(--wa-color-neutral-fill-quiet));
      }
    }
    .button:not(.disabled):not(.loading):active {
      color: var(--wa-color-on-quiet, var(--wa-color-neutral-on-quiet));
      background-color: color-mix(
        in oklab,
        var(--wa-color-fill-quiet, var(--wa-color-neutral-fill-quiet)),
        var(--wa-color-mix-active)
      );
    }
  }

  :host([appearance='outlined']) {
    .button {
      color: var(--wa-color-on-quiet, var(--wa-color-neutral-on-quiet));
      background-color: transparent;
      border-color: var(--wa-color-border-loud, var(--wa-color-neutral-border-loud));
    }
    @media (hover: hover) {
      .button:not(.disabled):not(.loading):hover {
        color: var(--wa-color-on-quiet, var(--wa-color-neutral-on-quiet));
        background-color: var(--wa-color-fill-quiet, var(--wa-color-neutral-fill-quiet));
      }
    }
    .button:not(.disabled):not(.loading):active {
      color: var(--wa-color-on-quiet, var(--wa-color-neutral-on-quiet));
      background-color: color-mix(
        in oklab,
        var(--wa-color-fill-quiet, var(--wa-color-neutral-fill-quiet)),
        var(--wa-color-mix-active)
      );
    }
  }

  :host([appearance='filled']) {
    .button {
      color: var(--wa-color-on-normal, var(--wa-color-neutral-on-normal));
      background-color: var(--wa-color-fill-normal, var(--wa-color-neutral-fill-normal));
      border-color: transparent;
    }
    @media (hover: hover) {
      .button:not(.disabled):not(.loading):hover {
        color: var(--wa-color-on-normal, var(--wa-color-neutral-on-normal));
        background-color: color-mix(
          in oklab,
          var(--wa-color-fill-normal, var(--wa-color-neutral-fill-normal)),
          var(--wa-color-mix-hover)
        );
      }
    }
    .button:not(.disabled):not(.loading):active {
      color: var(--wa-color-on-normal, var(--wa-color-neutral-on-normal));
      background-color: color-mix(
        in oklab,
        var(--wa-color-fill-normal, var(--wa-color-neutral-fill-normal)),
        var(--wa-color-mix-active)
      );
    }
  }

  :host([appearance='filled-outlined']) {
    .button {
      color: var(--wa-color-on-normal, var(--wa-color-neutral-on-normal));
      background-color: var(--wa-color-fill-normal, var(--wa-color-neutral-fill-normal));
      border-color: var(--wa-color-border-normal, var(--wa-color-neutral-border-normal));
    }
    @media (hover: hover) {
      .button:not(.disabled):not(.loading):hover {
        color: var(--wa-color-on-normal, var(--wa-color-neutral-on-normal));
        background-color: color-mix(
          in oklab,
          var(--wa-color-fill-normal, var(--wa-color-neutral-fill-normal)),
          var(--wa-color-mix-hover)
        );
      }
    }
    .button:not(.disabled):not(.loading):active {
      color: var(--wa-color-on-normal, var(--wa-color-neutral-on-normal));
      background-color: color-mix(
        in oklab,
        var(--wa-color-fill-normal, var(--wa-color-neutral-fill-normal)),
        var(--wa-color-mix-active)
      );
    }
  }

  :host([appearance='accent']) {
    .button {
      color: var(--wa-color-on-loud, var(--wa-color-neutral-on-loud));
      background-color: var(--wa-color-fill-loud, var(--wa-color-neutral-fill-loud));
      border-color: transparent;
    }
    @media (hover: hover) {
      .button:not(.disabled):not(.loading):hover {
        background-color: color-mix(
          in oklab,
          var(--wa-color-fill-loud, var(--wa-color-neutral-fill-loud)),
          var(--wa-color-mix-hover)
        );
      }
    }
    .button:not(.disabled):not(.loading):active {
      background-color: color-mix(
        in oklab,
        var(--wa-color-fill-loud, var(--wa-color-neutral-fill-loud)),
        var(--wa-color-mix-active)
      );
    }
  }

  /* Focus states */
  .button:focus {
    outline: none;
  }

  .button:focus-visible {
    outline: var(--wa-focus-ring);
    outline-offset: var(--wa-focus-ring-offset);
  }

  /* Disabled state */
  :host([disabled]) {
    opacity: 0.5;
    cursor: not-allowed;

    /* When disabled, prevent mouse events from bubbling up from children */
    .button {
      pointer-events: none;
    }
  }

  /* Keep it last so Safari doesn't stop parsing this block */
  .button::-moz-focus-inner {
    border: 0;
  }

  /* Icon buttons */
  .button.is-icon-button {
    outline-offset: 2px;
    width: var(--wa-form-control-height);
    aspect-ratio: 1;
  }

  .button.is-icon-button:has(wa-icon) {
    width: auto;
  }

  /* Pill modifier */
  :host([pill]) .button {
    border-radius: var(--wa-border-radius-pill);
  }

  /*
   * Label
   */

  .start,
  .end {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    pointer-events: none;
  }

  .label {
    display: inline-block;
  }

  .is-icon-button .label {
    display: flex;
  }

  .label::slotted(wa-icon) {
    align-self: center;
  }

  /*
   * Caret modifier
   */

  wa-icon[part='caret'] {
    display: flex;
    align-self: center;
    align-items: center;

    &::part(svg) {
      width: 0.875em;
      height: 0.875em;
    }

    .button:has(&) .end {
      display: none;
    }
  }

  /*
   * Loading modifier
   */

  .loading {
    position: relative;
    cursor: wait;

    .start,
    .label,
    .end,
    .caret {
      visibility: hidden;
    }

    wa-spinner {
      --indicator-color: currentColor;
      --track-color: color-mix(in oklab, currentColor, transparent 90%);

      position: absolute;
      font-size: 1em;
      height: 1em;
      width: 1em;
      top: calc(50% - 0.5em);
      left: calc(50% - 0.5em);
    }
  }

  /*
   * Badges
   */

  .button ::slotted(wa-badge) {
    border-color: var(--wa-color-surface-default);
    position: absolute;
    inset-block-start: 0;
    inset-inline-end: 0;
    translate: 50% -50%;
    pointer-events: none;
  }

  :host(:dir(rtl)) ::slotted(wa-badge) {
    translate: -50% -50%;
  }

  /*
  * Button spacing
  */

  slot[name='start']::slotted(*) {
    margin-inline-end: 0.75em;
  }

  slot[name='end']::slotted(*),
  .button:not(.visually-hidden-label) [part='caret'] {
    margin-inline-start: 0.75em;
  }

  /*
   * Button group border radius modifications
   */

  /* Remove border radius from all grouped buttons by default */
  :host(.wa-button-group__button) .button {
    border-radius: 0;
  }

  /* Horizontal orientation */
  :host(.wa-button-group__horizontal.wa-button-group__button-first) .button {
    border-start-start-radius: var(--wa-form-control-border-radius);
    border-end-start-radius: var(--wa-form-control-border-radius);
  }

  :host(.wa-button-group__horizontal.wa-button-group__button-last) .button {
    border-start-end-radius: var(--wa-form-control-border-radius);
    border-end-end-radius: var(--wa-form-control-border-radius);
  }

  /* Vertical orientation */
  :host(.wa-button-group__vertical) {
    flex: 1 1 auto;
  }

  :host(.wa-button-group__vertical) .button {
    width: 100%;
    justify-content: start;
  }

  :host(.wa-button-group__vertical.wa-button-group__button-first) .button {
    border-start-start-radius: var(--wa-form-control-border-radius);
    border-start-end-radius: var(--wa-form-control-border-radius);
  }

  :host(.wa-button-group__vertical.wa-button-group__button-last) .button {
    border-end-start-radius: var(--wa-form-control-border-radius);
    border-end-end-radius: var(--wa-form-control-border-radius);
  }

  /* Handle pill modifier for button groups */
  :host([pill].wa-button-group__horizontal.wa-button-group__button-first) .button {
    border-start-start-radius: var(--wa-border-radius-pill);
    border-end-start-radius: var(--wa-border-radius-pill);
  }

  :host([pill].wa-button-group__horizontal.wa-button-group__button-last) .button {
    border-start-end-radius: var(--wa-border-radius-pill);
    border-end-end-radius: var(--wa-border-radius-pill);
  }

  :host([pill].wa-button-group__vertical.wa-button-group__button-first) .button {
    border-start-start-radius: var(--wa-border-radius-pill);
    border-start-end-radius: var(--wa-border-radius-pill);
  }

  :host([pill].wa-button-group__vertical.wa-button-group__button-last) .button {
    border-end-start-radius: var(--wa-border-radius-pill);
    border-end-end-radius: var(--wa-border-radius-pill);
  }
`;/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Z=t=>t??$;/*! Bundled license information:

lit-html/directives/if-defined.js:
  (**
   * @license
   * Copyright 2018 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*//*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var gr=Symbol.for(""),Bi=t=>{if(t?.r===gr)return t?._$litStatic$},mr=(t,...e)=>({_$litStatic$:e.reduce(((o,r,i)=>o+(a=>{if(a._$litStatic$!==void 0)return a._$litStatic$;throw Error(`Value passed to 'literal' function must be a 'literal' result: ${a}. Use 'unsafeStatic' to pass non-literal values, but
            take care to ensure page security.`)})(r)+t[i+1]),t[0]),r:gr}),vr=new Map,Xe=t=>(e,...o)=>{let r=o.length,i,a,s=[],n=[],c,u=0,h=!1;for(;u<r;){for(c=e[u];u<r&&(a=o[u],(i=Bi(a))!==void 0);)c+=i+e[++u],h=!0;u!==r&&n.push(a),s.push(c),u++}if(u===r&&s.push(e[r]),h){let p=s.join("$$lit$$");(e=vr.get(p))===void 0&&(s.raw=s,vr.set(p,e=s)),o=n}return t(e,...o)},Ye=Xe(E),Mn=Xe(uo),Tn=Xe(ho),C=class extends q{constructor(){super(...arguments),this.assumeInteractionOn=["click"],this.hasSlotController=new St(this,"[default]","start","end"),this.localize=new R(this),this.invalid=!1,this.isIconButton=!1,this.title="",this.variant="neutral",this.appearance="accent",this.size="medium",this.withCaret=!1,this.disabled=!1,this.loading=!1,this.pill=!1,this.type="button"}static get validators(){return[...super.validators,pr()]}constructLightDOMButton(){let t=document.createElement("button");for(let e of this.attributes)e.name!=="style"&&t.setAttribute(e.name,e.value);return t.type=this.type,t.style.position="absolute !important",t.style.width="0 !important",t.style.height="0 !important",t.style.clipPath="inset(50%) !important",t.style.overflow="hidden !important",t.style.whiteSpace="nowrap !important",this.name&&(t.name=this.name),t.value=this.value||"",t}handleClick(t){if(this.disabled||this.loading){t.preventDefault(),t.stopImmediatePropagation();return}if(this.type!=="submit"&&this.type!=="reset"||!this.getForm())return;let o=this.constructLightDOMButton();this.parentElement?.append(o),o.click(),o.remove()}handleInvalid(){this.dispatchEvent(new ae)}handleLabelSlotChange(){let t=this.labelSlot.assignedNodes({flatten:!0}),e=!1,o=!1,r=!1,i=!1;[...t].forEach(a=>{if(a.nodeType===Node.ELEMENT_NODE){let s=a;s.localName==="wa-icon"?(o=!0,e||(e=s.label!==void 0)):i=!0}else a.nodeType===Node.TEXT_NODE&&(a.textContent?.trim()||"").length>0&&(r=!0)}),this.isIconButton=o&&!r&&!i,this.isIconButton&&!e&&console.warn('Icon buttons must have a label for screen readers. Add <wa-icon label="..."> to remove this warning.',this)}isButton(){return!this.href}isLink(){return!!this.href}handleDisabledChange(){this.updateValidity()}setValue(...t){}click(){this.button.click()}focus(t){this.button.focus(t)}blur(){this.button.blur()}render(){let t=this.isLink(),e=t?mr`a`:mr`button`;return Ye`
      <${e}
        part="base"
        class=${V({button:!0,caret:this.withCaret,disabled:this.disabled,loading:this.loading,rtl:this.localize.dir()==="rtl","has-label":this.hasSlotController.test("[default]"),"has-start":this.hasSlotController.test("start"),"has-end":this.hasSlotController.test("end"),"is-icon-button":this.isIconButton})}
        ?disabled=${Z(t?void 0:this.disabled)}
        type=${Z(t?void 0:this.type)}
        title=${this.title}
        name=${Z(t?void 0:this.name)}
        value=${Z(t?void 0:this.value)}
        href=${Z(t?this.href:void 0)}
        target=${Z(t?this.target:void 0)}
        download=${Z(t?this.download:void 0)}
        rel=${Z(t&&this.rel?this.rel:void 0)}
        role=${Z(t?void 0:"button")}
        aria-disabled=${Z(t&&this.disabled?"true":void 0)}
        tabindex=${this.disabled?"-1":"0"}
        @invalid=${this.isButton()?this.handleInvalid:null}
        @click=${this.handleClick}
      >
        <slot name="start" part="start" class="start"></slot>
        <slot part="label" class="label" @slotchange=${this.handleLabelSlotChange}></slot>
        <slot name="end" part="end" class="end"></slot>
        ${this.withCaret?Ye`
                <wa-icon part="caret" class="caret" library="system" name="chevron-down" variant="solid"></wa-icon>
              `:""}
        ${this.loading?Ye`<wa-spinner part="spinner"></wa-spinner>`:""}
      </${e}>
    `}};C.shadowRootOptions={...q.shadowRootOptions,delegatesFocus:!0};C.css=[fr,le,kt];l([T(".button")],C.prototype,"button",2);l([T("slot:not([name])")],C.prototype,"labelSlot",2);l([D()],C.prototype,"invalid",2);l([D()],C.prototype,"isIconButton",2);l([d()],C.prototype,"title",2);l([d({reflect:!0})],C.prototype,"variant",2);l([d({reflect:!0})],C.prototype,"appearance",2);l([d({reflect:!0})],C.prototype,"size",2);l([d({attribute:"with-caret",type:Boolean,reflect:!0})],C.prototype,"withCaret",2);l([d({type:Boolean})],C.prototype,"disabled",2);l([d({type:Boolean,reflect:!0})],C.prototype,"loading",2);l([d({type:Boolean,reflect:!0})],C.prototype,"pill",2);l([d()],C.prototype,"type",2);l([d({reflect:!0})],C.prototype,"name",2);l([d({reflect:!0})],C.prototype,"value",2);l([d({reflect:!0})],C.prototype,"href",2);l([d()],C.prototype,"target",2);l([d()],C.prototype,"rel",2);l([d()],C.prototype,"download",2);l([d({attribute:"formaction"})],C.prototype,"formAction",2);l([d({attribute:"formenctype"})],C.prototype,"formEnctype",2);l([d({attribute:"formmethod"})],C.prototype,"formMethod",2);l([d({attribute:"formnovalidate",type:Boolean})],C.prototype,"formNoValidate",2);l([d({attribute:"formtarget"})],C.prototype,"formTarget",2);l([j("disabled",{waitUntilFirstUpdate:!0})],C.prototype,"handleDisabledChange",1);C=l([M("wa-button")],C);/*! Bundled license information:

lit-html/static.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*//*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var wr=A`
  :host {
    --track-width: 2px;
    --track-color: var(--wa-color-neutral-fill-normal);
    --indicator-color: var(--wa-color-brand-fill-loud);
    --speed: 2s;

    /*
      Resizing a spinner element using anything but font-size will break the animation because the animation uses em
      units. Therefore, if a spinner is used in a flex container without \`flex: none\` applied, the spinner can
      grow/shrink and break the animation. The use of \`flex: none\` on the host element prevents this by always having
      the spinner sized according to its actual dimensions.
    */
    flex: none;
    display: inline-flex;
    width: 1em;
    height: 1em;
  }

  svg {
    width: 100%;
    height: 100%;
    aspect-ratio: 1;
    animation: spin var(--speed) linear infinite;
  }

  .track {
    stroke: var(--track-color);
  }

  .indicator {
    stroke: var(--indicator-color);
    stroke-dasharray: 75, 100;
    stroke-dashoffset: -5;
    animation: dash 1.5s ease-in-out infinite;
    stroke-linecap: round;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }

  @keyframes dash {
    0% {
      stroke-dasharray: 1, 150;
      stroke-dashoffset: 0;
    }
    50% {
      stroke-dasharray: 90, 150;
      stroke-dashoffset: -35;
    }
    100% {
      stroke-dasharray: 90, 150;
      stroke-dashoffset: -124;
    }
  }
`;/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Ze=class extends O{constructor(){super(...arguments),this.localize=new R(this)}render(){return E`
      <svg
        part="base"
        role="progressbar"
        aria-label=${this.localize.term("loading")}
        fill="none"
        viewBox="0 0 50 50"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle class="track" cx="25" cy="25" r="20" fill="none" stroke-width="5" />
        <circle class="indicator" cx="25" cy="25" r="20" fill="none" stroke-width="5" />
      </svg>
    `}};Ze.css=wr;Ze=l([M("wa-spinner")],Ze);/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var br=class extends Event{constructor(){super("wa-error",{bubbles:!0,cancelable:!1,composed:!0})}};/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var yr=class extends Event{constructor(){super("wa-load",{bubbles:!0,cancelable:!1,composed:!0})}};/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var xr=A`
  :host {
    --primary-color: currentColor;
    --primary-opacity: 1;
    --secondary-color: currentColor;
    --secondary-opacity: 0.4;
    --rotate-angle: 0deg;

    box-sizing: content-box;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    vertical-align: -0.125em;
  }

  /* Standard */
  :host(:not([auto-width])) {
    width: 1.25em;
    height: 1em;
  }

  /* Auto-width */
  :host([auto-width]) {
    width: auto;
    height: 1em;
  }

  svg {
    height: 1em;
    overflow: visible;
    width: auto;

    /* Duotone colors with path-specific opacity fallback */
    path[data-duotone-primary] {
      color: var(--primary-color);
      opacity: var(--path-opacity, var(--primary-opacity));
    }

    path[data-duotone-secondary] {
      color: var(--secondary-color);
      opacity: var(--path-opacity, var(--secondary-opacity));
    }
  }

  /* Rotation */
  :host([rotate]) {
    transform: rotate(var(--rotate-angle, 0deg));
  }

  /* Flipping */
  :host([flip='x']) {
    transform: scaleX(-1);
  }
  :host([flip='y']) {
    transform: scaleY(-1);
  }
  :host([flip='both']) {
    transform: scale(-1, -1);
  }

  /* Rotation and Flipping combined */
  :host([rotate][flip='x']) {
    transform: rotate(var(--rotate-angle, 0deg)) scaleX(-1);
  }
  :host([rotate][flip='y']) {
    transform: rotate(var(--rotate-angle, 0deg)) scaleY(-1);
  }
  :host([rotate][flip='both']) {
    transform: rotate(var(--rotate-angle, 0deg)) scale(-1, -1);
  }

  /* Animations */
  :host([animation='beat']) {
    animation-name: beat;
    animation-delay: var(--animation-delay, 0s);
    animation-direction: var(--animation-direction, normal);
    animation-duration: var(--animation-duration, 1s);
    animation-iteration-count: var(--animation-iteration-count, infinite);
    animation-timing-function: var(--animation-timing, ease-in-out);
  }

  :host([animation='fade']) {
    animation-name: fade;
    animation-delay: var(--animation-delay, 0s);
    animation-direction: var(--animation-direction, normal);
    animation-duration: var(--animation-duration, 1s);
    animation-iteration-count: var(--animation-iteration-count, infinite);
    animation-timing-function: var(--animation-timing, cubic-bezier(0.4, 0, 0.6, 1));
  }

  :host([animation='beat-fade']) {
    animation-name: beat-fade;
    animation-delay: var(--animation-delay, 0s);
    animation-direction: var(--animation-direction, normal);
    animation-duration: var(--animation-duration, 1s);
    animation-iteration-count: var(--animation-iteration-count, infinite);
    animation-timing-function: var(--animation-timing, cubic-bezier(0.4, 0, 0.6, 1));
  }

  :host([animation='bounce']) {
    animation-name: bounce;
    animation-delay: var(--animation-delay, 0s);
    animation-direction: var(--animation-direction, normal);
    animation-duration: var(--animation-duration, 1s);
    animation-iteration-count: var(--animation-iteration-count, infinite);
    animation-timing-function: var(--animation-timing, cubic-bezier(0.28, 0.84, 0.42, 1));
  }

  :host([animation='flip']) {
    animation-name: flip;
    animation-delay: var(--animation-delay, 0s);
    animation-direction: var(--animation-direction, normal);
    animation-duration: var(--animation-duration, 1s);
    animation-iteration-count: var(--animation-iteration-count, infinite);
    animation-timing-function: var(--animation-timing, ease-in-out);
  }

  :host([animation='shake']) {
    animation-name: shake;
    animation-delay: var(--animation-delay, 0s);
    animation-direction: var(--animation-direction, normal);
    animation-duration: var(--animation-duration, 1s);
    animation-iteration-count: var(--animation-iteration-count, infinite);
    animation-timing-function: var(--animation-timing, linear);
  }

  :host([animation='spin']) {
    animation-name: spin;
    animation-delay: var(--animation-delay, 0s);
    animation-direction: var(--animation-direction, normal);
    animation-duration: var(--animation-duration, 2s);
    animation-iteration-count: var(--animation-iteration-count, infinite);
    animation-timing-function: var(--animation-timing, linear);
  }

  :host([animation='spin-pulse']) {
    animation-name: spin-pulse;
    animation-direction: var(--animation-direction, normal);
    animation-duration: var(--animation-duration, 1s);
    animation-iteration-count: var(--animation-iteration-count, infinite);
    animation-timing-function: var(--animation-timing, steps(8));
  }

  :host([animation='spin-reverse']) {
    animation-name: spin;
    animation-delay: var(--animation-delay, 0s);
    animation-direction: var(--animation-direction, reverse);
    animation-duration: var(--animation-duration, 2s);
    animation-iteration-count: var(--animation-iteration-count, infinite);
    animation-timing-function: var(--animation-timing, linear);
  }

  /* Keyframes */
  @media (prefers-reduced-motion: reduce) {
    :host([animation='beat']),
    :host([animation='bounce']),
    :host([animation='fade']),
    :host([animation='beat-fade']),
    :host([animation='flip']),
    :host([animation='shake']),
    :host([animation='spin']),
    :host([animation='spin-pulse']),
    :host([animation='spin-reverse']) {
      animation: none !important;
      transition: none !important;
    }
  }
  @keyframes beat {
    0%,
    90% {
      transform: scale(1);
    }
    45% {
      transform: scale(var(--beat-scale, 1.25));
    }
  }

  @keyframes fade {
    50% {
      opacity: var(--fade-opacity, 0.4);
    }
  }

  @keyframes beat-fade {
    0%,
    100% {
      opacity: var(--beat-fade-opacity, 0.4);
      transform: scale(1);
    }
    50% {
      opacity: 1;
      transform: scale(var(--beat-fade-scale, 1.125));
    }
  }

  @keyframes bounce {
    0% {
      transform: scale(1, 1) translateY(0);
    }
    10% {
      transform: scale(var(--bounce-start-scale-x, 1.1), var(--bounce-start-scale-y, 0.9)) translateY(0);
    }
    30% {
      transform: scale(var(--bounce-jump-scale-x, 0.9), var(--bounce-jump-scale-y, 1.1))
        translateY(var(--bounce-height, -0.5em));
    }
    50% {
      transform: scale(var(--bounce-land-scale-x, 1.05), var(--bounce-land-scale-y, 0.95)) translateY(0);
    }
    57% {
      transform: scale(1, 1) translateY(var(--bounce-rebound, -0.125em));
    }
    64% {
      transform: scale(1, 1) translateY(0);
    }
    100% {
      transform: scale(1, 1) translateY(0);
    }
  }

  @keyframes flip {
    50% {
      transform: rotate3d(var(--flip-x, 0), var(--flip-y, 1), var(--flip-z, 0), var(--flip-angle, -180deg));
    }
  }

  @keyframes shake {
    0% {
      transform: rotate(-15deg);
    }
    4% {
      transform: rotate(15deg);
    }
    8%,
    24% {
      transform: rotate(-18deg);
    }
    12%,
    28% {
      transform: rotate(18deg);
    }
    16% {
      transform: rotate(-22deg);
    }
    20% {
      transform: rotate(22deg);
    }
    32% {
      transform: rotate(-12deg);
    }
    36% {
      transform: rotate(12deg);
    }
    40%,
    100% {
      transform: rotate(0deg);
    }
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }

  @keyframes spin-pulse {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }
`;/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var{I:Qn}=Co;var Cr=(t,e)=>e===void 0?t?._$litType$!==void 0:t?._$litType$===e;/*! Bundled license information:

lit-html/directive-helpers.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*//*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */function qi(t){return`data:image/svg+xml,${encodeURIComponent(t)}`}var Ge={solid:{check:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M434.8 70.1c14.3 10.4 17.5 30.4 7.1 44.7l-256 352c-5.5 7.6-14 12.3-23.4 13.1s-18.5-2.7-25.1-9.3l-128-128c-12.5-12.5-12.5-32.8 0-45.3s32.8-12.5 45.3 0l101.5 101.5 234-321.7c10.4-14.3 30.4-17.5 44.7-7.1z"/></svg>',"chevron-down":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M201.4 406.6c12.5 12.5 32.8 12.5 45.3 0l192-192c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 338.7 54.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l192 192z"/></svg>',"chevron-left":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M9.4 233.4c-12.5 12.5-12.5 32.8 0 45.3l192 192c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3L77.3 256 246.6 86.6c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0l-192 192z"/></svg>',"chevron-right":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M311.1 233.4c12.5 12.5 12.5 32.8 0 45.3l-192 192c-12.5 12.5-32.8 12.5-45.3 0s-12.5-32.8 0-45.3L243.2 256 73.9 86.6c-12.5-12.5-12.5-32.8 0-45.3s32.8-12.5 45.3 0l192 192z"/></svg>',circle:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M0 256a256 256 0 1 1 512 0 256 256 0 1 1 -512 0z"/></svg>',eyedropper:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M341.6 29.2l-101.6 101.6-9.4-9.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3l-9.4-9.4 101.6-101.6c39-39 39-102.2 0-141.1s-102.2-39-141.1 0zM55.4 323.3c-15 15-23.4 35.4-23.4 56.6l0 42.4-26.6 39.9c-8.5 12.7-6.8 29.6 4 40.4s27.7 12.5 40.4 4l39.9-26.6 42.4 0c21.2 0 41.6-8.4 56.6-23.4l109.4-109.4-45.3-45.3-109.4 109.4c-3 3-7.1 4.7-11.3 4.7l-36.1 0 0-36.1c0-4.2 1.7-8.3 4.7-11.3l109.4-109.4-45.3-45.3-109.4 109.4z"/></svg>',file:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><!--!Font Awesome Free 7.1.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2026 Fonticons, Inc.--><path fill="currentColor" d="M192 64C156.7 64 128 92.7 128 128L128 512C128 547.3 156.7 576 192 576L448 576C483.3 576 512 547.3 512 512L512 234.5C512 217.5 505.3 201.2 493.3 189.2L386.7 82.7C374.7 70.7 358.5 64 341.5 64L192 64zM453.5 240L360 240C346.7 240 336 229.3 336 216L336 122.5L453.5 240z"/></svg>',"file-audio":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><!--!Font Awesome Free 7.1.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2026 Fonticons, Inc.--><path fill="currentColor" d="M128 128C128 92.7 156.7 64 192 64L341.5 64C358.5 64 374.8 70.7 386.8 82.7L493.3 189.3C505.3 201.3 512 217.6 512 234.6L512 512C512 547.3 483.3 576 448 576L192 576C156.7 576 128 547.3 128 512L128 128zM336 122.5L336 216C336 229.3 346.7 240 360 240L453.5 240L336 122.5zM389.8 307.7C380.7 301.4 368.3 303.6 362 312.7C355.7 321.8 357.9 334.2 367 340.5C390.9 357.2 406.4 384.8 406.4 416C406.4 447.2 390.8 474.9 367 491.5C357.9 497.8 355.7 510.3 362 519.3C368.3 528.3 380.8 530.6 389.8 524.3C423.9 500.5 446.4 460.8 446.4 416C446.4 371.2 424 331.5 389.8 307.7zM208 376C199.2 376 192 383.2 192 392L192 440C192 448.8 199.2 456 208 456L232 456L259.2 490C262.2 493.8 266.8 496 271.7 496L272 496C280.8 496 288 488.8 288 480L288 352C288 343.2 280.8 336 272 336L271.7 336C266.8 336 262.2 338.2 259.2 342L232 376L208 376zM336 448.2C336 458.9 346.5 466.4 354.9 459.8C367.8 449.5 376 433.7 376 416C376 398.3 367.8 382.5 354.9 372.2C346.5 365.5 336 373.1 336 383.8L336 448.3z"/></svg>',"file-code":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><!--!Font Awesome Free 7.1.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2026 Fonticons, Inc.--><path fill="currentColor" d="M128 128C128 92.7 156.7 64 192 64L341.5 64C358.5 64 374.8 70.7 386.8 82.7L493.3 189.3C505.3 201.3 512 217.6 512 234.6L512 512C512 547.3 483.3 576 448 576L192 576C156.7 576 128 547.3 128 512L128 128zM336 122.5L336 216C336 229.3 346.7 240 360 240L453.5 240L336 122.5zM282.2 359.6C290.8 349.5 289.7 334.4 279.6 325.8C269.5 317.2 254.4 318.3 245.8 328.4L197.8 384.4C190.1 393.4 190.1 406.6 197.8 415.6L245.8 471.6C254.4 481.7 269.6 482.8 279.6 474.2C289.6 465.6 290.8 450.4 282.2 440.4L247.6 400L282.2 359.6zM394.2 328.4C385.6 318.3 370.4 317.2 360.4 325.8C350.4 334.4 349.2 349.6 357.8 359.6L392.4 400L357.8 440.4C349.2 450.5 350.3 465.6 360.4 474.2C370.5 482.8 385.6 481.7 394.2 471.6L442.2 415.6C449.9 406.6 449.9 393.4 442.2 384.4L394.2 328.4z"/></svg>',"file-excel":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><!--!Font Awesome Free 7.1.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2026 Fonticons, Inc.--><path fill="currentColor" d="M128 128C128 92.7 156.7 64 192 64L341.5 64C358.5 64 374.8 70.7 386.8 82.7L493.3 189.3C505.3 201.3 512 217.6 512 234.6L512 512C512 547.3 483.3 576 448 576L192 576C156.7 576 128 547.3 128 512L128 128zM336 122.5L336 216C336 229.3 346.7 240 360 240L453.5 240L336 122.5zM292 330.7C284.6 319.7 269.7 316.7 258.7 324C247.7 331.3 244.7 346.3 252 357.3L291.2 416L252 474.7C244.6 485.7 247.6 500.6 258.7 508C269.8 515.4 284.6 512.4 292 501.3L320 459.3L348 501.3C355.4 512.3 370.3 515.3 381.3 508C392.3 500.7 395.3 485.7 388 474.7L348.8 416L388 357.3C395.4 346.3 392.4 331.4 381.3 324C370.2 316.6 355.4 319.6 348 330.7L320 372.7L292 330.7z"/></svg>',"file-image":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><!--!Font Awesome Free 7.1.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2026 Fonticons, Inc.--><path fill="currentColor" d="M128 128C128 92.7 156.7 64 192 64L341.5 64C358.5 64 374.8 70.7 386.8 82.7L493.3 189.3C505.3 201.3 512 217.6 512 234.6L512 512C512 547.3 483.3 576 448 576L192 576C156.7 576 128 547.3 128 512L128 128zM336 122.5L336 216C336 229.3 346.7 240 360 240L453.5 240L336 122.5zM256 320C256 302.3 241.7 288 224 288C206.3 288 192 302.3 192 320C192 337.7 206.3 352 224 352C241.7 352 256 337.7 256 320zM220.6 512L419.4 512C435.2 512 448 499.2 448 483.4C448 476.1 445.2 469 440.1 463.7L343.3 361.9C337.3 355.6 328.9 352 320.1 352L319.8 352C311 352 302.7 355.6 296.6 361.9L199.9 463.7C194.8 469 192 476.1 192 483.4C192 499.2 204.8 512 220.6 512z"/></svg>',"file-pdf":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><!--!Font Awesome Free 7.1.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2026 Fonticons, Inc.--><path fill="currentColor" d="M128 64C92.7 64 64 92.7 64 128L64 512C64 547.3 92.7 576 128 576L208 576L208 464C208 428.7 236.7 400 272 400L448 400L448 234.5C448 217.5 441.3 201.2 429.3 189.2L322.7 82.7C310.7 70.7 294.5 64 277.5 64L128 64zM389.5 240L296 240C282.7 240 272 229.3 272 216L272 122.5L389.5 240zM272 444C261 444 252 453 252 464L252 592C252 603 261 612 272 612C283 612 292 603 292 592L292 564L304 564C337.1 564 364 537.1 364 504C364 470.9 337.1 444 304 444L272 444zM304 524L292 524L292 484L304 484C315 484 324 493 324 504C324 515 315 524 304 524zM400 444C389 444 380 453 380 464L380 592C380 603 389 612 400 612L432 612C460.7 612 484 588.7 484 560L484 496C484 467.3 460.7 444 432 444L400 444zM420 572L420 484L432 484C438.6 484 444 489.4 444 496L444 560C444 566.6 438.6 572 432 572L420 572zM508 464L508 592C508 603 517 612 528 612C539 612 548 603 548 592L548 548L576 548C587 548 596 539 596 528C596 517 587 508 576 508L548 508L548 484L576 484C587 484 596 475 596 464C596 453 587 444 576 444L528 444C517 444 508 453 508 464z"/></svg>',"file-powerpoint":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><!--!Font Awesome Free 7.1.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2026 Fonticons, Inc.--><path fill="currentColor" d="M128 128C128 92.7 156.7 64 192 64L341.5 64C358.5 64 374.8 70.7 386.8 82.7L493.3 189.3C505.3 201.3 512 217.6 512 234.6L512 512C512 547.3 483.3 576 448 576L192 576C156.7 576 128 547.3 128 512L128 128zM336 122.5L336 216C336 229.3 346.7 240 360 240L453.5 240L336 122.5zM280 320C266.7 320 256 330.7 256 344L256 488C256 501.3 266.7 512 280 512C293.3 512 304 501.3 304 488L304 464L328 464C367.8 464 400 431.8 400 392C400 352.2 367.8 320 328 320L280 320zM328 416L304 416L304 368L328 368C341.3 368 352 378.7 352 392C352 405.3 341.3 416 328 416z"/></svg>',"file-video":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><!--!Font Awesome Free 7.1.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2026 Fonticons, Inc.--><path fill="currentColor" d="M128 128C128 92.7 156.7 64 192 64L341.5 64C358.5 64 374.8 70.7 386.8 82.7L493.3 189.3C505.3 201.3 512 217.6 512 234.6L512 512C512 547.3 483.3 576 448 576L192 576C156.7 576 128 547.3 128 512L128 128zM336 122.5L336 216C336 229.3 346.7 240 360 240L453.5 240L336 122.5zM208 368L208 464C208 481.7 222.3 496 240 496L336 496C353.7 496 368 481.7 368 464L368 440L403 475C406.2 478.2 410.5 480 415 480C424.4 480 432 472.4 432 463L432 368.9C432 359.5 424.4 351.9 415 351.9C410.5 351.9 406.2 353.7 403 356.9L368 391.9L368 367.9C368 350.2 353.7 335.9 336 335.9L240 335.9C222.3 335.9 208 350.2 208 367.9z"/></svg>',"file-word":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><!--!Font Awesome Free 7.1.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2026 Fonticons, Inc.--><path fill="currentColor" d="M128 128C128 92.7 156.7 64 192 64L341.5 64C358.5 64 374.8 70.7 386.8 82.7L493.3 189.3C505.3 201.3 512 217.6 512 234.6L512 512C512 547.3 483.3 576 448 576L192 576C156.7 576 128 547.3 128 512L128 128zM336 122.5L336 216C336 229.3 346.7 240 360 240L453.5 240L336 122.5zM263.4 338.8C260.5 325.9 247.7 317.7 234.8 320.6C221.9 323.5 213.7 336.3 216.6 349.2L248.6 493.2C250.9 503.7 260 511.4 270.8 512C281.6 512.6 291.4 505.9 294.8 495.6L320 419.9L345.2 495.6C348.6 505.8 358.4 512.5 369.2 512C380 511.5 389.1 503.8 391.4 493.2L423.4 349.2C426.3 336.3 418.1 323.4 405.2 320.6C392.3 317.8 379.4 325.9 376.6 338.8L363.4 398.2L342.8 336.4C339.5 326.6 330.4 320 320 320C309.6 320 300.5 326.6 297.2 336.4L276.6 398.2L263.4 338.8z"/></svg>',"file-zipper":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><!--!Font Awesome Free 7.1.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2026 Fonticons, Inc.--><path fill="currentColor" d="M128 128C128 92.7 156.7 64 192 64L341.5 64C358.5 64 374.8 70.7 386.8 82.7L493.3 189.3C505.3 201.3 512 217.6 512 234.6L512 512C512 547.3 483.3 576 448 576L192 576C156.7 576 128 547.3 128 512L128 128zM336 122.5L336 216C336 229.3 346.7 240 360 240L453.5 240L336 122.5zM192 136C192 149.3 202.7 160 216 160L264 160C277.3 160 288 149.3 288 136C288 122.7 277.3 112 264 112L216 112C202.7 112 192 122.7 192 136zM192 232C192 245.3 202.7 256 216 256L264 256C277.3 256 288 245.3 288 232C288 218.7 277.3 208 264 208L216 208C202.7 208 192 218.7 192 232zM256 304L224 304C206.3 304 192 318.3 192 336L192 384C192 410.5 213.5 432 240 432C266.5 432 288 410.5 288 384L288 336C288 318.3 273.7 304 256 304zM240 368C248.8 368 256 375.2 256 384C256 392.8 248.8 400 240 400C231.2 400 224 392.8 224 384C224 375.2 231.2 368 240 368z"/></svg>',"grip-vertical":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M128 40c0-22.1-17.9-40-40-40L40 0C17.9 0 0 17.9 0 40L0 88c0 22.1 17.9 40 40 40l48 0c22.1 0 40-17.9 40-40l0-48zm0 192c0-22.1-17.9-40-40-40l-48 0c-22.1 0-40 17.9-40 40l0 48c0 22.1 17.9 40 40 40l48 0c22.1 0 40-17.9 40-40l0-48zM0 424l0 48c0 22.1 17.9 40 40 40l48 0c22.1 0 40-17.9 40-40l0-48c0-22.1-17.9-40-40-40l-48 0c-22.1 0-40 17.9-40 40zM320 40c0-22.1-17.9-40-40-40L232 0c-22.1 0-40 17.9-40 40l0 48c0 22.1 17.9 40 40 40l48 0c22.1 0 40-17.9 40-40l0-48zM192 232l0 48c0 22.1 17.9 40 40 40l48 0c22.1 0 40-17.9 40-40l0-48c0-22.1-17.9-40-40-40l-48 0c-22.1 0-40 17.9-40 40zM320 424c0-22.1-17.9-40-40-40l-48 0c-22.1 0-40 17.9-40 40l0 48c0 22.1 17.9 40 40 40l48 0c22.1 0 40-17.9 40-40l0-48z"/></svg>',indeterminate:'<svg part="indeterminate-icon" class="icon" viewBox="0 0 16 16"><g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd" stroke-linecap="round"><g stroke="currentColor" stroke-width="2"><g transform="translate(2.285714 6.857143)"><path d="M10.2857143,1.14285714 L1.14285714,1.14285714"/></g></g></g></svg>',minus:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M0 256c0-17.7 14.3-32 32-32l384 0c17.7 0 32 14.3 32 32s-14.3 32-32 32L32 288c-17.7 0-32-14.3-32-32z"/></svg>',pause:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M48 32C21.5 32 0 53.5 0 80L0 432c0 26.5 21.5 48 48 48l64 0c26.5 0 48-21.5 48-48l0-352c0-26.5-21.5-48-48-48L48 32zm224 0c-26.5 0-48 21.5-48 48l0 352c0 26.5 21.5 48 48 48l64 0c26.5 0 48-21.5 48-48l0-352c0-26.5-21.5-48-48-48l-64 0z"/></svg>',play:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M91.2 36.9c-12.4-6.8-27.4-6.5-39.6 .7S32 57.9 32 72l0 368c0 14.1 7.5 27.2 19.6 34.4s27.2 7.5 39.6 .7l336-184c12.8-7 20.8-20.5 20.8-35.1s-8-28.1-20.8-35.1l-336-184z"/></svg>',plus:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><!--!Font Awesome Free 7.1.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2026 Fonticons, Inc.--><path fill="currentColor" d="M352 128C352 110.3 337.7 96 320 96C302.3 96 288 110.3 288 128L288 288L128 288C110.3 288 96 302.3 96 320C96 337.7 110.3 352 128 352L288 352L288 512C288 529.7 302.3 544 320 544C337.7 544 352 529.7 352 512L352 352L512 352C529.7 352 544 337.7 544 320C544 302.3 529.7 288 512 288L352 288L352 128z"/></svg>',star:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 576 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M309.5-18.9c-4.1-8-12.4-13.1-21.4-13.1s-17.3 5.1-21.4 13.1L193.1 125.3 33.2 150.7c-8.9 1.4-16.3 7.7-19.1 16.3s-.5 18 5.8 24.4l114.4 114.5-25.2 159.9c-1.4 8.9 2.3 17.9 9.6 23.2s16.9 6.1 25 2L288.1 417.6 432.4 491c8 4.1 17.7 3.3 25-2s11-14.2 9.6-23.2L441.7 305.9 556.1 191.4c6.4-6.4 8.6-15.8 5.8-24.4s-10.1-14.9-19.1-16.3L383 125.3 309.5-18.9z"/></svg>',upload:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><!--!Font Awesome Free 7.1.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2026 Fonticons, Inc.--><path fill="currentColor" d="M352 173.3L352 384C352 401.7 337.7 416 320 416C302.3 416 288 401.7 288 384L288 173.3L246.6 214.7C234.1 227.2 213.8 227.2 201.3 214.7C188.8 202.2 188.8 181.9 201.3 169.4L297.3 73.4C309.8 60.9 330.1 60.9 342.6 73.4L438.6 169.4C451.1 181.9 451.1 202.2 438.6 214.7C426.1 227.2 405.8 227.2 393.3 214.7L352 173.3zM320 464C364.2 464 400 428.2 400 384L480 384C515.3 384 544 412.7 544 448L544 480C544 515.3 515.3 544 480 544L160 544C124.7 544 96 515.3 96 480L96 448C96 412.7 124.7 384 160 384L240 384C240 428.2 275.8 464 320 464zM464 488C477.3 488 488 477.3 488 464C488 450.7 477.3 440 464 440C450.7 440 440 450.7 440 464C440 477.3 450.7 488 464 488z"/></svg>',user:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M224 248a120 120 0 1 0 0-240 120 120 0 1 0 0 240zm-29.7 56C95.8 304 16 383.8 16 482.3 16 498.7 29.3 512 45.7 512l356.6 0c16.4 0 29.7-13.3 29.7-29.7 0-98.5-79.8-178.3-178.3-178.3l-59.4 0z"/></svg>',xmark:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M55.1 73.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L147.2 256 9.9 393.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L192.5 301.3 329.9 438.6c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3L237.8 256 375.1 118.6c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L192.5 210.7 55.1 73.4z"/></svg>'},regular:{"circle-question":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M464 256a208 208 0 1 0 -416 0 208 208 0 1 0 416 0zM0 256a256 256 0 1 1 512 0 256 256 0 1 1 -512 0zm256-80c-17.7 0-32 14.3-32 32 0 13.3-10.7 24-24 24s-24-10.7-24-24c0-44.2 35.8-80 80-80s80 35.8 80 80c0 47.2-36 67.2-56 74.5l0 3.8c0 13.3-10.7 24-24 24s-24-10.7-24-24l0-8.1c0-20.5 14.8-35.2 30.1-40.2 6.4-2.1 13.2-5.5 18.2-10.3 4.3-4.2 7.7-10 7.7-19.6 0-17.7-14.3-32-32-32zM224 368a32 32 0 1 1 64 0 32 32 0 1 1 -64 0z"/></svg>',"circle-xmark":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M256 48a208 208 0 1 1 0 416 208 208 0 1 1 0-416zm0 464a256 256 0 1 0 0-512 256 256 0 1 0 0 512zM167 167c-9.4 9.4-9.4 24.6 0 33.9l55 55-55 55c-9.4 9.4-9.4 24.6 0 33.9s24.6 9.4 33.9 0l55-55 55 55c9.4 9.4 24.6 9.4 33.9 0s9.4-24.6 0-33.9l-55-55 55-55c9.4-9.4 9.4-24.6 0-33.9s-24.6-9.4-33.9 0l-55 55-55-55c-9.4-9.4-24.6-9.4-33.9 0z"/></svg>',copy:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M384 336l-192 0c-8.8 0-16-7.2-16-16l0-256c0-8.8 7.2-16 16-16l133.5 0c4.2 0 8.3 1.7 11.3 4.7l58.5 58.5c3 3 4.7 7.1 4.7 11.3L400 320c0 8.8-7.2 16-16 16zM192 384l192 0c35.3 0 64-28.7 64-64l0-197.5c0-17-6.7-33.3-18.7-45.3L370.7 18.7C358.7 6.7 342.5 0 325.5 0L192 0c-35.3 0-64 28.7-64 64l0 256c0 35.3 28.7 64 64 64zM64 128c-35.3 0-64 28.7-64 64L0 448c0 35.3 28.7 64 64 64l192 0c35.3 0 64-28.7 64-64l0-16-48 0 0 16c0 8.8-7.2 16-16 16L64 464c-8.8 0-16-7.2-16-16l0-256c0-8.8 7.2-16 16-16l16 0 0-48-16 0z"/></svg>',eye:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 576 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M288 80C222.8 80 169.2 109.6 128.1 147.7 89.6 183.5 63 226 49.4 256 63 286 89.6 328.5 128.1 364.3 169.2 402.4 222.8 432 288 432s118.8-29.6 159.9-67.7C486.4 328.5 513 286 526.6 256 513 226 486.4 183.5 447.9 147.7 406.8 109.6 353.2 80 288 80zM95.4 112.6C142.5 68.8 207.2 32 288 32s145.5 36.8 192.6 80.6c46.8 43.5 78.1 95.4 93 131.1 3.3 7.9 3.3 16.7 0 24.6-14.9 35.7-46.2 87.7-93 131.1-47.1 43.7-111.8 80.6-192.6 80.6S142.5 443.2 95.4 399.4c-46.8-43.5-78.1-95.4-93-131.1-3.3-7.9-3.3-16.7 0-24.6 14.9-35.7 46.2-87.7 93-131.1zM288 336c44.2 0 80-35.8 80-80 0-29.6-16.1-55.5-40-69.3-1.4 59.7-49.6 107.9-109.3 109.3 13.8 23.9 39.7 40 69.3 40zm-79.6-88.4c2.5 .3 5 .4 7.6 .4 35.3 0 64-28.7 64-64 0-2.6-.2-5.1-.4-7.6-37.4 3.9-67.2 33.7-71.1 71.1zm45.6-115c10.8-3 22.2-4.5 33.9-4.5 8.8 0 17.5 .9 25.8 2.6 .3 .1 .5 .1 .8 .2 57.9 12.2 101.4 63.7 101.4 125.2 0 70.7-57.3 128-128 128-61.6 0-113-43.5-125.2-101.4-1.8-8.6-2.8-17.5-2.8-26.6 0-11 1.4-21.8 4-32 .2-.7 .3-1.3 .5-1.9 11.9-43.4 46.1-77.6 89.5-89.5z"/></svg>',"eye-slash":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 576 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M41-24.9c-9.4-9.4-24.6-9.4-33.9 0S-2.3-.3 7 9.1l528 528c9.4 9.4 24.6 9.4 33.9 0s9.4-24.6 0-33.9l-96.4-96.4c2.7-2.4 5.4-4.8 8-7.2 46.8-43.5 78.1-95.4 93-131.1 3.3-7.9 3.3-16.7 0-24.6-14.9-35.7-46.2-87.7-93-131.1-47.1-43.7-111.8-80.6-192.6-80.6-56.8 0-105.6 18.2-146 44.2L41-24.9zM176.9 111.1c32.1-18.9 69.2-31.1 111.1-31.1 65.2 0 118.8 29.6 159.9 67.7 38.5 35.7 65.1 78.3 78.6 108.3-13.6 30-40.2 72.5-78.6 108.3-3.1 2.8-6.2 5.6-9.4 8.4L393.8 328c14-20.5 22.2-45.3 22.2-72 0-70.7-57.3-128-128-128-26.7 0-51.5 8.2-72 22.2l-39.1-39.1zm182 182l-108-108c11.1-5.8 23.7-9.1 37.1-9.1 44.2 0 80 35.8 80 80 0 13.4-3.3 26-9.1 37.1zM103.4 173.2l-34-34c-32.6 36.8-55 75.8-66.9 104.5-3.3 7.9-3.3 16.7 0 24.6 14.9 35.7 46.2 87.7 93 131.1 47.1 43.7 111.8 80.6 192.6 80.6 37.3 0 71.2-7.9 101.5-20.6L352.2 422c-20 6.4-41.4 10-64.2 10-65.2 0-118.8-29.6-159.9-67.7-38.5-35.7-65.1-78.3-78.6-108.3 10.4-23.1 28.6-53.6 54-82.8z"/></svg>',star:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 576 512"><!--! Font Awesome Free 7.0.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc. --><path fill="currentColor" d="M288.1-32c9 0 17.3 5.1 21.4 13.1L383 125.3 542.9 150.7c8.9 1.4 16.3 7.7 19.1 16.3s.5 18-5.8 24.4L441.7 305.9 467 465.8c1.4 8.9-2.3 17.9-9.6 23.2s-17 6.1-25 2L288.1 417.6 143.8 491c-8 4.1-17.7 3.3-25-2s-11-14.2-9.6-23.2L134.4 305.9 20 191.4c-6.4-6.4-8.6-15.8-5.8-24.4s10.1-14.9 19.1-16.3l159.9-25.4 73.6-144.2c4.1-8 12.4-13.1 21.4-13.1zm0 76.8L230.3 158c-3.5 6.8-10 11.6-17.6 12.8l-125.5 20 89.8 89.9c5.4 5.4 7.9 13.1 6.7 20.7l-19.8 125.5 113.3-57.6c6.8-3.5 14.9-3.5 21.8 0l113.3 57.6-19.8-125.5c-1.2-7.6 1.3-15.3 6.7-20.7l89.8-89.9-125.5-20c-7.6-1.2-14.1-6-17.6-12.8L288.1 44.8z"/></svg>'}},Vi={name:"system",resolver:(t,e="classic",o="solid")=>{let i=Ge[o][t]??Ge.regular[t]??Ge.regular["circle-question"];return i?qi(i):""}},Lr=Vi;/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Je="";function Ni(t){Je=t}function _r(){if(!Je){let t=document.querySelector("[data-fa-kit-code]");t&&Ni(t.getAttribute("data-fa-kit-code")||"")}return Je}/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Er="7.1.0";function Hi(t,e,o){let r=_r(),i=r.length>0,a="solid";return e==="notdog"&&(o==="solid"&&(a="notdog-solid"),o==="duo-solid"&&(a="notdog-duo-solid")),e==="notdog-duo"&&(a="notdog-duo-solid"),e==="chisel"&&(a="chisel-regular"),e==="etch"&&(a="etch-solid"),e==="jelly"&&(a="jelly-regular",o==="duo-regular"&&(a="jelly-duo-regular"),o==="fill-regular"&&(a="jelly-fill-regular")),e==="jelly-duo"&&(a="jelly-duo-regular"),e==="jelly-fill"&&(a="jelly-fill-regular"),e==="slab"&&((o==="solid"||o==="regular")&&(a="slab-regular"),o==="press-regular"&&(a="slab-press-regular")),e==="slab-press"&&(a="slab-press-regular"),e==="thumbprint"&&(a="thumbprint-light"),e==="whiteboard"&&(a="whiteboard-semibold"),e==="utility"&&(a="utility-semibold"),e==="utility-duo"&&(a="utility-duo-semibold"),e==="utility-fill"&&(a="utility-fill-semibold"),e==="classic"&&(o==="thin"&&(a="thin"),o==="light"&&(a="light"),o==="regular"&&(a="regular"),o==="solid"&&(a="solid")),e==="sharp"&&(o==="thin"&&(a="sharp-thin"),o==="light"&&(a="sharp-light"),o==="regular"&&(a="sharp-regular"),o==="solid"&&(a="sharp-solid")),e==="duotone"&&(o==="thin"&&(a="duotone-thin"),o==="light"&&(a="duotone-light"),o==="regular"&&(a="duotone-regular"),o==="solid"&&(a="duotone")),e==="sharp-duotone"&&(o==="thin"&&(a="sharp-duotone-thin"),o==="light"&&(a="sharp-duotone-light"),o==="regular"&&(a="sharp-duotone-regular"),o==="solid"&&(a="sharp-duotone-solid")),e==="brands"&&(a="brands"),i?`https://ka-p.fontawesome.com/releases/v${Er}/svgs/${a}/${t}.svg?token=${encodeURIComponent(r)}`:`https://ka-f.fontawesome.com/releases/v${Er}/svgs/${a}/${t}.svg`}var Ui={name:"default",resolver:(t,e="classic",o="solid")=>Hi(t,e,o),mutator:(t,e)=>{if(e?.family&&!t.hasAttribute("data-duotone-initialized")){let{family:o,variant:r}=e;if(o==="duotone"||o==="sharp-duotone"||o==="notdog-duo"||o==="notdog"&&r==="duo-solid"||o==="jelly-duo"||o==="jelly"&&r==="duo-regular"||o==="utility-duo"||o==="thumbprint"){let i=[...t.querySelectorAll("path")],a=i.find(n=>!n.hasAttribute("opacity")),s=i.find(n=>n.hasAttribute("opacity"));if(!a||!s)return;if(a.setAttribute("data-duotone-primary",""),s.setAttribute("data-duotone-secondary",""),e.swapOpacity&&a&&s){let n=s.getAttribute("opacity")||"0.4";a.style.setProperty("--path-opacity",n),s.style.setProperty("--path-opacity","1")}t.setAttribute("data-duotone-initialized","")}}}},Ar=Ui;/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Wi="classic",ji=[Ar,Lr],Qe=[];function $r(t){Qe.push(t)}function Sr(t){Qe=Qe.filter(e=>e!==t)}function be(t){return ji.find(e=>e.name===t)}function kr(){return Wi}/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Wt=Symbol(),ye=Symbol(),to,eo=new Map,z=class extends O{constructor(){super(...arguments),this.svg=null,this.autoWidth=!1,this.swapOpacity=!1,this.label="",this.library="default",this.rotate=0,this.resolveIcon=async(t,e)=>{let o;if(e?.spriteSheet){this.hasUpdated||await this.updateComplete,this.svg=E`<svg part="svg">
        <use part="use" href="${t}"></use>
      </svg>`,await this.updateComplete;let r=this.shadowRoot.querySelector("[part='svg']");return typeof e.mutator=="function"&&e.mutator(r,this),this.svg}try{if(o=await fetch(t,{mode:"cors"}),!o.ok)return o.status===410?Wt:ye}catch{return ye}try{let r=document.createElement("div");r.innerHTML=await o.text();let i=r.firstElementChild;if(i?.tagName?.toLowerCase()!=="svg")return Wt;to||(to=new DOMParser);let s=to.parseFromString(i.outerHTML,"text/html").body.querySelector("svg");return s?(s.part.add("svg"),document.adoptNode(s)):Wt}catch{return Wt}}}connectedCallback(){super.connectedCallback(),$r(this)}firstUpdated(t){super.firstUpdated(t),this.hasAttribute("rotate")&&this.style.setProperty("--rotate-angle",`${this.rotate}deg`),this.setIcon()}disconnectedCallback(){super.disconnectedCallback(),Sr(this)}getIconSource(){let t=be(this.library),e=this.family||kr();return this.name&&t?{url:t.resolver(this.name,e,this.variant,this.autoWidth),fromLibrary:!0}:{url:this.src,fromLibrary:!1}}handleLabelChange(){typeof this.label=="string"&&this.label.length>0?(this.setAttribute("role","img"),this.setAttribute("aria-label",this.label),this.removeAttribute("aria-hidden")):(this.removeAttribute("role"),this.removeAttribute("aria-label"),this.setAttribute("aria-hidden","true"))}async setIcon(){let{url:t,fromLibrary:e}=this.getIconSource(),o=e?be(this.library):void 0;if(!t){this.svg=null;return}let r=eo.get(t);r||(r=this.resolveIcon(t,o),eo.set(t,r));let i=await r;if(i===ye&&eo.delete(t),t===this.getIconSource().url){if(Cr(i)){this.svg=i;return}switch(i){case ye:case Wt:this.svg=null,this.dispatchEvent(new br);break;default:this.svg=i.cloneNode(!0),o?.mutator?.(this.svg,this),this.dispatchEvent(new yr)}}}updated(t){super.updated(t);let e=be(this.library);this.hasAttribute("rotate")&&this.style.setProperty("--rotate-angle",`${this.rotate}deg`);let o=this.shadowRoot?.querySelector("svg");o&&e?.mutator?.(o,this)}render(){return this.hasUpdated?this.svg:E`<svg part="svg" width="16" height="16"></svg>`}};z.css=xr;l([D()],z.prototype,"svg",2);l([d({reflect:!0})],z.prototype,"name",2);l([d({reflect:!0})],z.prototype,"family",2);l([d({reflect:!0})],z.prototype,"variant",2);l([d({attribute:"auto-width",type:Boolean,reflect:!0})],z.prototype,"autoWidth",2);l([d({attribute:"swap-opacity",type:Boolean,reflect:!0})],z.prototype,"swapOpacity",2);l([d()],z.prototype,"src",2);l([d()],z.prototype,"label",2);l([d({reflect:!0})],z.prototype,"library",2);l([d({type:Number,reflect:!0})],z.prototype,"rotate",2);l([d({type:String,reflect:!0})],z.prototype,"flip",2);l([d({type:String,reflect:!0})],z.prototype,"animation",2);l([j("label")],z.prototype,"handleLabelChange",1);l([j(["family","name","library","variant","src","autoWidth","swapOpacity"],{waitUntilFirstUpdate:!0})],z.prototype,"setIcon",1);z=l([M("wa-icon")],z);/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license *//*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var Or=A`
  :host {
    --width: 31rem;
    --spacing: var(--wa-space-l);
    --show-duration: 200ms;
    --hide-duration: 200ms;

    display: none;
  }

  :host([open]) {
    display: block;
  }

  .dialog {
    display: flex;
    flex-direction: column;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
    width: var(--width);
    max-width: calc(100% - var(--wa-space-2xl));
    max-height: calc(100% - var(--wa-space-2xl));
    background-color: var(--wa-color-surface-raised);
    border-radius: var(--wa-panel-border-radius);
    border: none;
    box-shadow: var(--wa-shadow-l);
    padding: 0;
    margin: auto;

    &.show {
      animation: show-dialog var(--show-duration) ease;

      &::backdrop {
        animation: show-backdrop var(--show-duration, 200ms) ease;
      }
    }

    &.hide {
      animation: show-dialog var(--hide-duration) ease reverse;

      &::backdrop {
        animation: show-backdrop var(--hide-duration, 200ms) ease reverse;
      }
    }

    &.pulse {
      animation: pulse 250ms ease;
    }
  }

  .dialog:focus {
    outline: none;
  }

  /* Ensure there's enough vertical padding for phones that don't update vh when chrome appears (e.g. iPhone) */
  @media screen and (max-width: 420px) {
    .dialog {
      max-height: 80vh;
    }
  }

  .open {
    display: flex;
    opacity: 1;
  }

  .header {
    flex: 0 0 auto;
    display: flex;
    flex-wrap: nowrap;

    padding-inline-start: var(--spacing);
    padding-block-end: 0;

    /* Subtract the close button's padding so that the X is visually aligned with the edges of the dialog content */
    padding-inline-end: calc(var(--spacing) - var(--wa-form-control-padding-block));
    padding-block-start: calc(var(--spacing) - var(--wa-form-control-padding-block));
  }

  .title {
    align-self: center;
    flex: 1 1 auto;
    font-family: inherit;
    font-size: var(--wa-font-size-l);
    font-weight: var(--wa-font-weight-heading);
    line-height: var(--wa-line-height-condensed);
    margin: 0;
  }

  .header-actions {
    align-self: start;
    display: flex;
    flex-shrink: 0;
    flex-wrap: wrap;
    justify-content: end;
    gap: var(--wa-space-2xs);
    padding-inline-start: var(--spacing);
  }

  .header-actions wa-button,
  .header-actions ::slotted(wa-button) {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
  }

  .body {
    flex: 1 1 auto;
    display: block;
    padding: var(--spacing);
    overflow: auto;
    -webkit-overflow-scrolling: touch;

    &:focus {
      outline: none;
    }

    &:focus-visible {
      outline: var(--wa-focus-ring);
      outline-offset: var(--wa-focus-ring-offset);
    }
  }

  .footer {
    flex: 0 0 auto;
    display: flex;
    flex-wrap: wrap;
    gap: var(--wa-space-xs);
    justify-content: end;
    padding: var(--spacing);
    padding-block-start: 0;
  }

  .footer ::slotted(wa-button:not(:first-of-type)) {
    margin-inline-start: var(--wa-spacing-xs);
  }

  .dialog::backdrop {
    /*
      NOTE: the ::backdrop element doesn't inherit properly in Safari yet, but it will in 17.4! At that time, we can
      remove the fallback values here.
    */
    background-color: var(--wa-color-overlay-modal, rgb(0 0 0 / 0.25));
  }

  @keyframes pulse {
    0% {
      scale: 1;
    }
    50% {
      scale: 1.02;
    }
    100% {
      scale: 1;
    }
  }

  @keyframes show-dialog {
    from {
      opacity: 0;
      scale: 0.8;
    }
    to {
      opacity: 1;
      scale: 1;
    }
  }

  @keyframes show-backdrop {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  @media (forced-colors: active) {
    .dialog {
      border: solid 1px white;
    }
  }
`;/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */function zr(t){return t.split(" ").map(e=>e.trim()).filter(e=>e!=="")}/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */var it=class extends O{constructor(){super(...arguments),this.localize=new R(this),this.hasSlotController=new St(this,"footer","header-actions","label"),this.open=!1,this.label="",this.withoutHeader=!1,this.lightDismiss=!1,this.handleDocumentKeyDown=t=>{t.key==="Escape"&&this.open&&(t.preventDefault(),t.stopPropagation(),this.requestClose(this.dialog))}}firstUpdated(){this.open&&(this.addOpenListeners(),this.dialog.showModal(),ze(this))}disconnectedCallback(){super.disconnectedCallback(),Pe(this),this.removeOpenListeners()}async requestClose(t){let e=new oe({source:t});if(this.dispatchEvent(e),e.defaultPrevented){this.open=!0,ht(this.dialog,"pulse");return}this.removeOpenListeners(),await ht(this.dialog,"hide"),this.open=!1,this.dialog.close(),Pe(this);let o=this.originalTrigger;typeof o?.focus=="function"&&setTimeout(()=>o.focus()),this.dispatchEvent(new re)}addOpenListeners(){document.addEventListener("keydown",this.handleDocumentKeyDown)}removeOpenListeners(){document.removeEventListener("keydown",this.handleDocumentKeyDown)}handleDialogCancel(t){t.preventDefault(),!this.dialog.classList.contains("hide")&&t.target===this.dialog&&this.requestClose(this.dialog)}handleDialogClick(t){let o=t.target.closest('[data-dialog="close"]');o&&(t.stopPropagation(),this.requestClose(o))}async handleDialogPointerDown(t){t.target===this.dialog&&(this.lightDismiss?this.requestClose(this.dialog):await ht(this.dialog,"pulse"))}handleOpenChange(){this.open&&!this.dialog.open?this.show():!this.open&&this.dialog.open&&(this.open=!0,this.requestClose(this.dialog))}async show(){let t=new ee;if(this.dispatchEvent(t),t.defaultPrevented){this.open=!1;return}this.addOpenListeners(),this.originalTrigger=document.activeElement,this.open=!0,this.dialog.showModal(),ze(this),requestAnimationFrame(()=>{let e=this.querySelector("[autofocus]");e&&typeof e.focus=="function"?e.focus():this.dialog.focus()}),await ht(this.dialog,"show"),this.dispatchEvent(new ie)}render(){let t=!this.withoutHeader,e=this.hasSlotController.test("footer");return E`
      <dialog
        part="dialog"
        class=${V({dialog:!0,open:this.open})}
        @cancel=${this.handleDialogCancel}
        @click=${this.handleDialogClick}
        @pointerdown=${this.handleDialogPointerDown}
      >
        ${t?E`
              <header part="header" class="header">
                <h2 part="title" class="title" id="title">
                  <!-- If there's no label, use an invisible character to prevent the header from collapsing -->
                  <slot name="label"> ${this.label.length>0?this.label:"\u200B"} </slot>
                </h2>
                <div part="header-actions" class="header-actions">
                  <slot name="header-actions"></slot>
                  <wa-button
                    part="close-button"
                    exportparts="base:close-button__base"
                    class="close"
                    appearance="plain"
                    @click="${o=>this.requestClose(o.target)}"
                  >
                    <wa-icon
                      name="xmark"
                      label=${this.localize.term("close")}
                      library="system"
                      variant="solid"
                    ></wa-icon>
                  </wa-button>
                </div>
              </header>
            `:""}

        <div part="body" class="body"><slot></slot></div>

        ${e?E`
              <footer part="footer" class="footer">
                <slot name="footer"></slot>
              </footer>
            `:""}
      </dialog>
    `}};it.css=Or;l([T(".dialog")],it.prototype,"dialog",2);l([d({type:Boolean,reflect:!0})],it.prototype,"open",2);l([d({reflect:!0})],it.prototype,"label",2);l([d({attribute:"without-header",type:Boolean,reflect:!0})],it.prototype,"withoutHeader",2);l([d({attribute:"light-dismiss",type:Boolean})],it.prototype,"lightDismiss",2);l([j("open",{waitUntilFirstUpdate:!0})],it.prototype,"handleOpenChange",1);it=l([M("wa-dialog")],it);document.addEventListener("click",t=>{let e=t.target.closest("[data-dialog]");if(e instanceof Element){let[o,r]=zr(e.getAttribute("data-dialog")||"");if(o==="open"&&r?.length){let a=e.getRootNode().getElementById(r);a?.localName==="wa-dialog"?a.open=!0:console.warn(`A dialog with an ID of "${r}" could not be found in this document.`)}}});W||document.addEventListener("pointerdown",()=>{});/*! Copyright 2026 Fonticons, Inc. - https://webawesome.com/license */
