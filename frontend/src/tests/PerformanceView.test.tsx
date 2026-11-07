import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PerformanceView } from "../components/PerformanceView";

afterEach(() => vi.unstubAllGlobals());
const data = {
  terms: [], discovered_terms: [{term_key:"synthetic_s4",label:"Synthetic Semester 4",selector_verified:true}],
  note:"Only imported semesters are shown.",live_capture_enabled:false,
};
function show() {
  const client = new QueryClient({defaultOptions:{queries:{retry:false}}});
  return render(<QueryClientProvider client={client}><PerformanceView /></QueryClientProvider>);
}
describe("PerformanceView", () => {
  it("shows the missing-data state without inventing results", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ok:true,json:async()=>data}));
    show();
    expect(await screen.findByText(/No marks or semester results have been imported/)).toBeInTheDocument();
    expect(screen.getByText(/Live performance imports are disabled/)).toBeInTheDocument();
    expect(screen.getByRole("button",{name:"Preview performance scope"})).toBeDisabled();
  });
  it("previews one exact semester and keeps capture disabled", async () => {
    const fetch = vi.fn().mockImplementation(async (url:string) => ({ok:true,json:async()=>url.endsWith("preview") ? {
      approval_id:"synthetic-preview",term_key:"synthetic_s4",label:"Synthetic Semester 4",class_label:"Synthetic class",view:"marks",scope:"One semester only",
    } : data}));
    vi.stubGlobal("fetch",fetch);
    show();
    await screen.findByRole("option",{name:"Synthetic Semester 4"});
    fireEvent.change(screen.getByLabelText("Performance semester"),{target:{value:"synthetic_s4"}});
    fireEvent.change(screen.getByLabelText("Performance view"),{target:{value:"results"}});
    fireEvent.click(screen.getByRole("button",{name:"Preview performance scope"}));
    expect(await screen.findByText("One semester only")).toBeInTheDocument();
    expect(screen.getByRole("button",{name:"Approve this performance import"})).toBeDisabled();
    await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(2));
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({term_key:"synthetic_s4",view:"results"});
    fireEvent.change(screen.getByLabelText("Performance view"),{target:{value:"marks"}});
    expect(screen.queryByRole("button",{name:"Approve this performance import"})).not.toBeInTheDocument();
  });
});
