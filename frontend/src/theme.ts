export type ThemePreference = "system" | "sepia-dark" | "sepia-light";
let memoryPreference: ThemePreference = "system";
export function readTheme(): ThemePreference {
  try {
    const value = localStorage.getItem("attendplan-theme");
    return value === "sepia-dark" || value === "sepia-light" ? value : "system";
  } catch { return memoryPreference; }
}
export function applyTheme(preference: ThemePreference) {
  const dark = preference === "sepia-dark" || (preference === "system" && typeof window.matchMedia === "function" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  const resolved = dark ? "sepia-dark" : "sepia-light";
  if(document.documentElement.dataset.theme !== resolved) document.documentElement.dataset.theme = resolved;
  document.documentElement.style.colorScheme = dark ? "dark" : "light";
  // Keep browser overscroll/background in sync with the active CSS theme.
  document.documentElement.style.backgroundColor = "var(--bg-page)";
}

const listeners=new Set<()=>void>();
export function setTheme(value:ThemePreference){
 memoryPreference=value;
 try{localStorage.setItem("attendplan-theme",value);}catch{/* Storage may be restricted. */}
 applyTheme(value);listeners.forEach(listener=>listener());
}
export function subscribeTheme(listener:()=>void){listeners.add(listener);return ()=>{listeners.delete(listener);};}
window.addEventListener("storage",event=>{if(event.key === "attendplan-theme"){applyTheme(readTheme());listeners.forEach(listener=>listener());}});
if(typeof window.matchMedia === "function") window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change",()=>{if(readTheme()==="system") applyTheme("system");});
