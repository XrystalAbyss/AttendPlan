import {describe,it,expect} from "vitest";
import {render,screen,within} from "@testing-library/react";
import {SummaryCards} from "../components/SummaryCards";
import type {SnapshotSummary} from "../types/attendance";

const summary:SnapshotSummary={total_courses:5,active_courses:4,safe_courses:3,at_risk_courses:1,unrecorded_courses:1,total_attended:32,total_delivered:40,overall_percentage:80,overall_status:"SAFE"};

describe("Attendance overview",()=>{
  it("keeps zero-buffer caution subjects separate from subjects safe to miss",()=>{
    render(<SummaryCards summary={summary} cautionCount={1} targetPercentage={75}/>);
    expect(within(screen.getByRole("article",{name:"Safe to miss"})).getByText("02")).toBeInTheDocument();
    expect(within(screen.getByRole("article",{name:"Caution"})).getByText("01")).toBeInTheDocument();
    expect(within(screen.getByRole("article",{name:"At risk"})).getByText("01")).toBeInTheDocument();
    expect(within(screen.getByRole("article",{name:"Unrecorded"})).getByText("01")).toBeInTheDocument();
  });
  it("presents zero delivered periods as unknown rather than risk or a percentage",()=>{
    const {container}=render(<SummaryCards summary={{...summary,total_attended:0,total_delivered:0,overall_percentage:null,overall_status:"UNRECORDED",active_courses:0,safe_courses:0,at_risk_courses:0,unrecorded_courses:5}} targetPercentage={75}/>);
    expect(screen.getByText("Unknown")).toBeInTheDocument();
    expect(screen.getByText("UNRECORDED")).toBeInTheDocument();
    expect(container.querySelector('.attendance-metric')).toHaveAttribute('data-tone','unknown');
  });
});
