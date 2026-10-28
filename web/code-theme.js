// A reading preference, independent of the document and its undo history.
const key='workmoire:code-theme';
const eventName='workmoire:code-theme-change';
export const codeTheme=()=>document.documentElement.dataset.codeTheme==='dark'?'dark':'light';
function apply(value){
 document.documentElement.dataset.codeTheme=value==='dark'?'dark':'light';
 window.dispatchEvent(new Event(eventName));
}
try{apply(localStorage.getItem(key));}catch{apply('light');}
window.addEventListener('storage',event=>{if(event.key===key||event.key===null)apply(event.newValue);});
export function toggleCodeTheme(){
 const next=codeTheme()==='dark'?'light':'dark';
 try{localStorage.setItem(key,next);}catch{/* The current tab still gets the preference. */}
 apply(next);
}
export function onCodeThemeChange(callback){
 window.addEventListener(eventName,callback);
 return ()=>window.removeEventListener(eventName,callback);
}
