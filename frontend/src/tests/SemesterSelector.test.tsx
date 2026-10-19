import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SemesterSelector } from "../components/SemesterSelector";
import type { AcademicTerm } from "../types/attendance";

const MOCK_TERMS: AcademicTerm[] = [
  {
    id: "term-1",
    institution_key: "mrei",
    academic_year: "2026-2027",
    semester_number: 5,
    class_identifier: "B.Tech CSE AIML-Sem 5",
    academic_start_date: null,
    academic_end_date: null,
    created_at: "2026-10-19T00:00:00Z",
    total_courses: 15,
    total_attended: 185,
    total_delivered: 213,
    overall_percentage: 86.85,
    overall_status: "SAFE",
    has_datewise_data: true,
  },
  {
    id: "term-2",
    institution_key: "mrei",
    academic_year: "2025-2026",
    semester_number: 4,
    class_identifier: "B.Tech CSE AIML-Sem 4",
    academic_start_date: null,
    academic_end_date: null,
    created_at: "2026-05-15T00:00:00Z",
    total_courses: 14,
    total_attended: 140,
    total_delivered: 200,
    overall_percentage: 70.0,
    overall_status: "AT_RISK",
    has_datewise_data: false,
  },
];

describe("SemesterSelector Component", () => {
  it("renders selected semester details and aggregate percentage", () => {
    const onSelect = vi.fn();
    render(
      <SemesterSelector
        terms={MOCK_TERMS}
        selectedTermId="term-1"
        onSelectTerm={onSelect}
      />
    );

    expect(screen.getByText(/2026-2027 • Semester 5/i)).toBeInTheDocument();
    expect(screen.getByText("86.85%")).toBeInTheDocument();
    expect(screen.getByText(/185\/213/i)).toBeInTheDocument();
  });

  it("calls onSelectTerm when changing dropdown selection", () => {
    const onSelect = vi.fn();
    render(
      <SemesterSelector
        terms={MOCK_TERMS}
        selectedTermId="term-1"
        onSelectTerm={onSelect}
      />
    );

    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "term-2" } });
    expect(onSelect).toHaveBeenCalledWith("term-2");
  });
});
