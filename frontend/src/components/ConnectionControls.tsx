import {useQuery} from "@tanstack/react-query";
import {ChevronDown,Cloud} from "lucide-react";
import {ArchiveSync,request as archiveRequest} from "./ArchiveSync";
import {StartupConnection} from "./StartupConnection";

export function ConnectionControls(){
  // ArchiveSync owns polling; this observer shares its cache without another timer.
  const archive=useQuery({queryKey:["attendance-archive"],queryFn:()=>archiveRequest("status")});
  const state=archive.data?.state;
  const active=state && ["APPROVED","CONNECTING","SYNCING"].includes(state);
  const needsAttention=state && ["ACTION_REQUIRED","PAUSED","STOPPED","COMPLETED_WITH_GAPS"].includes(state);
  return <details className="connection-controls">
    <summary>
      <Cloud size={19} aria-hidden="true"/>
      <span className="connection-heading">Portal connection & imports<span>Manage login preferences, reviewed syncs and saved coverage.</span></span>
      <span className={`connection-state ${needsAttention ? "needs-attention" : ""}`} role="status">
        {archive.isError ? "Status unavailable" : active ? `Syncing · ${archive.data?.completed}/${archive.data?.total}` : state==="COMPLETED_WITH_GAPS" ? "Gaps in coverage" : needsAttention ? "Needs attention" : "Review controls"}
      </span>
      <ChevronDown className="disclosure-chevron" size={16} aria-hidden="true"/>
    </summary>
    <div className="connection-content"><StartupConnection/><ArchiveSync/></div>
  </details>;
}
