import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AttendanceTable } from "../components/AttendanceTable";
import type { CourseRecord } from "../types/attendance";

const MOCK_COURSES: CourseRecord[] = [
  {
    code: "CSH302C",
    name: "OPERATING SYSTEMS",
    short_name: "OS - PP",
    faculty: "TAMANNA SACHDEVA",
    credits: 3.0,
    is_lab: false,
    attended: 19,
    delivered: 19,
    percent: 100.0,
    status: "SAFE",
    can_skip: 6,
    must_attend: 0,
    margin_summary: "Safe to miss up to 6 periods while staying >= 75%",
  },
  {
    code: "CSH311C",
    name: "COMPUTER ARCHITECTURE & ORGANISATION LAB",
    short_name: "CAOR - PR",
    faculty: "Ravi Prakash Chaturvedi",
    credits: 1.0,
    is_lab: true,
    attended: 10,
    delivered: 14,
    percent: 71.43,
    status: "AT_RISK",
    can_skip: 0,
    must_attend: 2,
    margin_summary: "Need 2 consecutive periods attended to reach 75%",
  },
  {
    code: "RDO202C",
    name: "RESEARCH & INNOVATION",
    short_name: "R&I - PP",
    faculty: null,
    credits: 1.0,
    is_lab: false,
    attended: 0,
    delivered: 0,
    percent: null,
    status: "UNRECORDED",
    can_skip: null,
    must_attend: null,
    margin_summary: "No periods delivered yet (unrecorded/pending)",
  },
];

describe("AttendanceTable Component", () => {
  it("renders all courses with their codes and titles", () => {
    const onSelect = vi.fn();
    render(
      <AttendanceTable
        courses={MOCK_COURSES}
        targetPercentage={75}
        onSelectCourseForSimulation={onSelect}
      />
    );

    expect(screen.getByText("CSH302C")).toBeInTheDocument();
    expect(screen.getByText("OPERATING SYSTEMS")).toBeInTheDocument();
    expect(screen.getByText("CSH311C")).toBeInTheDocument();
    expect(screen.getByText("COMPUTER ARCHITECTURE & ORGANISATION LAB")).toBeInTheDocument();
    expect(screen.getByText("RDO202C")).toBeInTheDocument();
  });

  it("renders safe bunk margin and consecutive needed correctly", () => {
    const onSelect = vi.fn();
    render(
      <AttendanceTable
        courses={MOCK_COURSES}
        targetPercentage={75}
        onSelectCourseForSimulation={onSelect}
      />
    );

    // CSH302C (19/19): safe to miss 6
    expect(screen.getByText(/Safe to miss 6 periods/i)).toBeInTheDocument();

    // CSH311C (10/14): need 2 consecutive
    expect(screen.getByText(/Need 2 consecutive periods/i)).toBeInTheDocument();

    // RDO202C (0/0): pending
    expect(screen.getByText(/Pending \(0 delivered\)/i)).toBeInTheDocument();
  });

  it("filters courses when clicking filter pills", () => {
    const onSelect = vi.fn();
    render(
      <AttendanceTable
        courses={MOCK_COURSES}
        targetPercentage={75}
        onSelectCourseForSimulation={onSelect}
      />
    );

    // Click "At Risk" filter
    const atRiskButton = screen.getByRole("button", { name: /At Risk/i });
    fireEvent.click(atRiskButton);

    // CSH311C should remain visible
    expect(screen.getByText("CSH311C")).toBeInTheDocument();
    // CSH302C (SAFE) and RDO202C (UNRECORDED) should now be filtered out
    expect(screen.queryByText("CSH302C")).not.toBeInTheDocument();
    expect(screen.queryByText("RDO202C")).not.toBeInTheDocument();
  });

  it("distinguishes Theory vs Lab badges", () => {
    const onSelect = vi.fn();
    render(
      <AttendanceTable
        courses={MOCK_COURSES}
        targetPercentage={75}
        onSelectCourseForSimulation={onSelect}
      />
    );

    expect(screen.getByText("Lab")).toBeInTheDocument();
    expect(screen.getAllByText("Theory").length).toBeGreaterThan(0);
  });
});
