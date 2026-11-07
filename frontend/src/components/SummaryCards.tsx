import {AlertTriangle,ArrowUpRight,CheckCircle2,HelpCircle,ShieldCheck} from "lucide-react";
import {standing} from "../standing";
import type {SnapshotSummary} from "../types/attendance";

interface Props {summary:SnapshotSummary;cautionCount?:number;targetPercentage:number;}

export function SummaryCards({summary,targetPercentage,cautionCount=0}:Props){
  const overall=standing({attended:summary.total_attended,delivered:summary.total_delivered,is_lab:false});
  const tone=overall.status==="AT_RISK" ? "risk" : overall.status==="CAUTION" ? "caution" : overall.status==="UNRECORDED" ? "unknown" : "safe";
  const metrics=[
    {label:"Safe to miss",value:Math.max(0,summary.safe_courses-cautionCount),note:"Subjects with a full session to spare",tone:"safe",icon:CheckCircle2},
    {label:"Caution",value:cautionCount,note:"At least 75%, with no full session to spare",tone:"caution",icon:ShieldCheck},
    {label:"At risk",value:summary.at_risk_courses,note:`Subjects below ${targetPercentage}%`,tone:"risk",icon:AlertTriangle},
    {label:"Unrecorded",value:summary.unrecorded_courses,note:"No delivered periods reported",tone:"unknown",icon:HelpCircle},
  ];
  return <section className="summary-grid" aria-label="Attendance summary">
    <article className="attendance-metric" data-tone={tone}>
      <div className="metric-label">Overall term attendance<ArrowUpRight size={17} aria-hidden="true"/></div>
      <div className="attendance-value">{summary.overall_percentage===null ? "Unknown" : <>{summary.overall_percentage.toFixed(2)}<span>%</span></>}</div>
      <div className="attendance-meter" aria-hidden="true"><div style={{width:`${Math.min(100,Math.max(0,summary.overall_percentage??0))}%`}}/><span style={{left:`${targetPercentage}%`}}/></div>
      <div className="metric-footnote"><span>{summary.total_attended} / {summary.total_delivered} periods</span><span>{targetPercentage}% target</span></div>
      <span className="standing-label">{overall.status.replaceAll("_"," ")}</span>
    </article>
    {metrics.map(({label,value,note,tone,icon:Icon})=><article className="subject-metric" key={label} data-tone={tone} aria-label={label}>
      <div className="metric-label"><span>{label}</span><Icon size={16} aria-hidden="true"/></div>
      <div className="metric-value">{value.toString().padStart(2,"0")}</div><p>{note}</p>
    </article>)}
  </section>;
}
