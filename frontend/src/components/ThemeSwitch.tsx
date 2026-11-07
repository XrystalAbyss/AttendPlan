import {useSyncExternalStore} from "react";
import {readTheme,setTheme,subscribeTheme} from "../theme";
import type {ThemePreference} from "../theme";
export function ThemeSwitch(){
 const preference=useSyncExternalStore(subscribeTheme,readTheme,readTheme);
 return <label className="flex items-center gap-2 text-slate-300">Theme<select aria-label="Color theme" className="bg-slate-900 border border-slate-700 rounded p-1.5 text-slate-100" value={preference} onChange={e=>setTheme(e.target.value as ThemePreference)}><option value="system">Follow system</option><option value="sepia-dark">Dark sepia</option><option value="sepia-light">Light sepia</option></select></label>;
}
