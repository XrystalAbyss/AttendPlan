import {describe,it,expect,vi} from "vitest";
import {render,screen,fireEvent} from "@testing-library/react";
import {ThemeSwitch} from "../components/ThemeSwitch";
import {readTheme,applyTheme} from "../theme";

describe("Sepia themes",()=>{
  it("switches both themes and remembers the user's choice",()=>{
    localStorage.clear();render(<ThemeSwitch/>);
    const select=screen.getByLabelText("Color theme");
    fireEvent.change(select,{target:{value:"sepia-light"}});
    expect(document.documentElement.dataset.theme).toBe("sepia-light");
    fireEvent.change(select,{target:{value:"sepia-dark"}});
    expect(document.documentElement.dataset.theme).toBe("sepia-dark");
    expect(readTheme()).toBe("sepia-dark");
  });
  it("handles old or unknown preferences without breaking the app",()=>{
    localStorage.setItem("attendplan-theme","unknown");
    expect(readTheme()).toBe("system");
    applyTheme("sepia-light");
    expect(document.documentElement.style.colorScheme).toBe("light");
  });
});

it("keeps the selected theme in memory when browser storage is unavailable",async()=>{
 const {setTheme,readTheme}=await import("../theme");
 const get=vi.spyOn(Storage.prototype,"getItem").mockImplementation(()=>{throw new Error("restricted");});
 const set=vi.spyOn(Storage.prototype,"setItem").mockImplementation(()=>{throw new Error("restricted");});
 setTheme("sepia-dark");expect(readTheme()).toBe("sepia-dark");
 get.mockRestore();set.mockRestore();
});

