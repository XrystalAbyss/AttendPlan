import {standing} from "../standing";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { API_BASE } from "../api/attendance";
import type { CourseRecord } from "../types/attendance";

interface Period { id: string; date: string; start: string | null; end: string | null; period: string | null; course_code: string | null; course_name: string | null; status: string; attended: number; delivered: number; }
export function AttendanceExplorer({ termId, academicYear, course, onClose, targetPercentage = 75 }: { termId: string; academicYear: string; course?: CourseRecord; onClose?: () => void; targetPercentage?: number }) {
  const [month, setMonth] = useState("all");
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const query = useQuery({ queryKey: ["period-ledger", termId], enabled: !!termId, queryFn: async () => {
    const response = await fetch(`${API_BASE}/api/v1/terms/${encodeURIComponent(termId)}/attendance/periods`);
    if (!response.ok) throw new Error("Saved daywise records could not be loaded.");
    return (await response.json()) as { periods: Period[] };
  }});
  const preview = useMutation({mutationFn: async (selection: string) => {
    const response = await fetch(`${API_BASE}/api/v1/terms/${encodeURIComponent(termId)}/attendance/month-preview?month=${encodeURIComponent(selection)}`, {method:"POST"});
    if (!response.ok) { const body = await response.json(); throw new Error(body.detail ?? "Month preview failed."); }
    return await response.json() as {month: string; periods: Period[]};
  }});
  const saved = query.data?.periods ?? [];
  const live = preview.data?.month === month ? preview.data.periods : null;
  const all = live ?? saved;
  const years = [...new Set([...academicYear.split("-").filter(y => /^\d{4}$/.test(y)), ...all.map(p => p.date.slice(0, 4))])].sort();
  const months = years.flatMap(y => Array.from({length: 12}, (_, i) => `${y}-${String(i+1).padStart(2, "0")}`));
  const scoped = all.filter(p => (!course || p.course_code === course.code) && (month === "all" || p.date.startsWith(month)));
  const dates = [...new Set(scoped.map(p => p.date))].sort();
  let attended = 0, delivered = 0;
  const points = dates.map(date => {
    const records = scoped.filter(p => p.date === date);
    attended += records.reduce((n,p) => n+p.attended,0); delivered += records.reduce((n,p) => n+p.delivered,0);
    return { date, percentage: delivered ? attended/delivered*100 : null };
  });
  const plotted = points.map((p,i) => ({...p,x:46+i*734/Math.max(1,points.length-1)})).filter(p => p.percentage !== null);
  const line = plotted.map(p => `${p.x},${122-(p.percentage ?? 0)}`).join(" ");
  const visible = scoped.filter(p => !selectedDate || p.date === selectedDate);
  const content = <section className="attendance-explorer bg-slate-900 border border-slate-700 rounded-lg p-5 space-y-4 min-w-0" aria-label={course ? "Subject attendance detail" : "Daywise attendance"}>
    <div className="flex flex-wrap justify-between gap-3"><div><h2 className="text-xl font-semibold">{course ? `${course.name} · ${course.code}` : "Daywise attendance"}</h2><p className="text-sm text-slate-400">{course ? "Subject history and period ledger" : "Choose any month or review all imported semester observations"}</p></div>{onClose && <button onClick={onClose} className="border rounded px-3 py-1">Close subject details</button>}</div>
    {course && <div className="flex flex-wrap gap-6 text-sm"><span>Term snapshot: <strong>{course.percent == null ? "Unrecorded" : `${course.percent}%`}</strong></span><span>{course.attended} / {course.delivered} periods</span><span>Target status: {standing(course).status.replaceAll("_", " ")}</span><span>{course.margin_summary}</span><span>{course.is_lab ? "Lab" : "Theory"} · {course.credits} credits</span><span>Faculty: {course.faculty ?? "Not supplied"}</span></div>}
    <label className="block text-sm">Attendance month <select aria-label="Attendance month" className="bg-slate-800 border border-slate-600 rounded p-2 ml-2 max-w-full" value={month} onChange={e => {setMonth(e.target.value);setSelectedDate(null);preview.reset();}}><option value="all">All imported months</option>{months.map(m => <option key={m} value={m}>{new Date(`${m}-01T12:00:00`).toLocaleDateString("en-IN", {month:"long",year:"numeric"})}{saved.some(p => p.date.startsWith(m)) ? " · imported observations" : " · not imported"}</option>)}</select></label>
    <div className="flex flex-wrap gap-3 items-center"><button className="border rounded px-3 py-2 disabled:opacity-40 text-sm" disabled={month === "all" || preview.isPending} onClick={() => preview.mutate(month)}>{preview.isPending ? "Checking portal month…" : "Preview this month from portal"}</button><span className="text-xs text-slate-400">Reads one month using your existing session. Does not save or import attendance.</span></div>
    {preview.error && <p role="alert">{preview.error.message}</p>}
    {live && <p role="status" className="text-amber-300 text-sm">Live preview only · {month} · {live.length} period records · not saved. Changing month returns to saved data.</p>}
    <p className="text-xs text-amber-300">Coverage is limited to imported observations. A blank date or month does not mean absent or no classes. Calendar options do not prove the semester ran in that month. Unmapped periods are not assigned to a subject.</p>
    {query.isLoading ? <p>Loading saved periods…</p> : query.isError ? <p role="alert">{query.error.message}</p> : !scoped.length ? <p role="status">No {live ? "verified live" : "imported"} {course ? "mapped subject " : ""}periods for this selection. A reviewed portal import is needed before analytics can cover it.</p> : <>
      <div className="flex flex-wrap gap-6"><span><strong>{delivered ? (attended/delivered*100).toFixed(1)+"%" : "Unknown"}</strong> observed attendance</span><span>{attended} attended / {delivered} delivered</span><span>{dates.length} observed dates</span></div>
      <figure><svg viewBox="0 0 800 152" role="img" aria-label="Cumulative attendance trend across observed dates, zero to one hundred percent" className="w-full max-h-56 rounded">
        {[0,25,50,75,100].map(value=><g key={value}><line x1="46" y1={122-value} x2="780" y2={122-value} stroke="var(--chart-grid)" opacity=".45"/><text x="33" y={126-value} textAnchor="end" fontSize="10" fill="var(--text-muted)">{value}%</text></g>)}
        <line x1="46" y1={122-targetPercentage} x2="780" y2={122-targetPercentage} stroke="var(--tone-caution)" strokeDasharray="6 4" opacity=".7"/>
        <polyline points={line} fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round"/>
        {plotted.map(p=><circle key={p.date} cx={p.x} cy={122-(p.percentage ?? 0)} r="3" fill="var(--accent)"><title>{p.date}: {p.percentage?.toFixed(1)}%</title></circle>)}
      </svg><figcaption className="text-xs text-slate-400">Cumulative trend for this selection · {dates[0]} to {dates.at(-1)} · dashed line: {targetPercentage}%. Gaps between observed dates are unknown.</figcaption></figure>
      <div className="flex flex-wrap gap-2" aria-label="Observed dates"><button className="border rounded p-2 text-xs" onClick={() => setSelectedDate(null)}>All dates</button>{dates.map(d => <button className={`border rounded p-2 text-xs ${selectedDate===d ? "bg-slate-700" : ""}`} aria-pressed={selectedDate===d} key={d} onClick={() => setSelectedDate(d)}>{d.slice(5)}</button>)}</div>
      <div className="overflow-x-auto max-h-96"><table className="w-full min-w-[640px] text-sm text-left"><thead><tr><th>Date</th><th>Subject</th><th>Period / time</th><th>Portal status</th><th>Attended / delivered</th></tr></thead><tbody>{visible.map(p => <tr className="border-t border-slate-800" key={p.id}><td className="py-2 whitespace-nowrap">{p.date}</td><td>{p.course_name ?? "Unmapped subject"}</td><td>{p.start ?? p.period ?? "Not provided"}{p.end ? `–${p.end}` : ""}</td><td className={p.status === "PRESENT" ? "text-emerald-400" : p.status === "ABSENT" ? "text-rose-400" : "text-amber-300"}>{p.status.replaceAll("_", " ")}</td><td>{p.attended} / {p.delivered}</td></tr>)}</tbody></table></div>
    </>}
  </section>;
  return course ? <div className="fixed inset-0 z-50 bg-slate-950/80 overflow-y-auto p-3 sm:p-8" role="dialog" aria-modal="true" aria-label="Subject attendance detail" onKeyDown={e => {if(e.key === "Escape") onClose?.();}}><div className="max-w-6xl mx-auto">{content}</div></div> : content;
}

