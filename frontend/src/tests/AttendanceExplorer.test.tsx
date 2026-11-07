import { afterEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AttendanceExplorer } from "../components/AttendanceExplorer";
import { fetchSubjectAnalytics } from "../api/attendance";

afterEach(() => vi.unstubAllGlobals());
it("maps the real ranking response fields into visible subject values", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ok:true,json:async()=>({subjects:[],rankings:{by_absolute_missed:[{code:"TEST",name:"Synthetic",missed_periods:3}],by_missed_rate:[{code:"TEST",name:"Synthetic",absence_rate:25}],by_total_delivered:[{code:"TEST",name:"Synthetic",delivered_periods:12}]}})}));
  const result = await fetchSubjectAnalytics("synthetic");
  expect(result.rankings.by_absolute_missed[0]).toEqual({course_code:"TEST",course_name:"Synthetic",value:3});
  expect(result.rankings.by_missed_rate[0].value).toBe(25);
});
it("offers missing months without fabricating absence and previews only the chosen month", async () => {
  const fetch = vi.fn().mockImplementation(async (url:string) => ({ok:true,json:async()=>url.includes("month-preview") ? {month:"2026-09",periods:[]} : {periods:[{id:"synthetic",date:"2026-10-03",start:null,end:null,period:"1",course_code:"TEST",course_name:"Synthetic",status:"UNKNOWN",attended:0,delivered:0}]}}));
  vi.stubGlobal("fetch",fetch);
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><AttendanceExplorer termId="synthetic" academicYear="2026-2027" /></QueryClientProvider>);
  expect(await screen.findByText("UNKNOWN")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Attendance month"),{target:{value:"2026-09"}});
  expect(screen.getByRole("status")).toHaveTextContent("No imported");
  fireEvent.click(screen.getByRole("button",{name:"Preview this month from portal"}));
  expect(await screen.findByText(/Live preview only/)).toBeInTheDocument();
  expect(fetch.mock.calls[1][0]).toContain("month=2026-09");
  expect(fetch.mock.calls[1][1]).toEqual({method:"POST"});
});
