import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AbsenceAnalyticsView } from "../components/AbsenceAnalyticsView";
import type {
  MonthlyAnalyticsItem,
  SubjectAnalyticsResponse,
  WeekdayAnalyticsItem,
} from "../types/attendance";

const MOCK_MONTHLY: MonthlyAnalyticsItem[] = [
  {
    year: 2026,
    month: 10,
    month_label: "October 2026",
    delivered: 20,
    attended: 16,
    missed: 4,
    attendance_percentage: 80.0,
    absence_percentage: 20.0,
    observed_dates_count: 5,
    coverage: "PARTIAL",
  },
];

const MOCK_WEEKDAY: WeekdayAnalyticsItem[] = [
  {
    weekday_index: 0,
    weekday_name: "Monday",
    delivered: 10,
    attended: 8,
    missed: 2,
    absence_rate: 20.0,
    observed_teaching_dates: 2,
    coverage: "PARTIAL",
  },
  {
    weekday_index: 1,
    weekday_name: "Tuesday",
    delivered: 0,
    attended: 0,
    missed: 0,
    absence_rate: 0.0,
    observed_teaching_dates: 0,
    coverage: "NO_DATA",
  },
];

const MOCK_SUBJECTS: SubjectAnalyticsResponse = {
  subjects: [
    {
      course_code: "CSH301C",
      course_name: "Computer Architecture",
      course_type: "THEORY",
      faculty_name: "Dr. Smith",
      credits: 3.0,
      attended: 15,
      delivered: 20,
      missed: 5,
      percentage: 75.0,
      status: "SAFE",
      can_skip: 0,
      must_attend: 0,
      absence_contribution_percentage: 100.0,
      margin_summary: "At 75%",
    },
  ],
  rankings: {
    by_absolute_missed: [
      { course_code: "CSH301C", course_name: "Computer Architecture", value: 5 },
    ],
    by_missed_rate: [
      { course_code: "CSH301C", course_name: "Computer Architecture", value: 25.0 },
    ],
    by_total_delivered: [
      { course_code: "CSH301C", course_name: "Computer Architecture", value: 20 },
    ],
  },
};

describe("AbsenceAnalyticsView Component", () => {
  it("renders insufficient data warning when no daywise observations exist", () => {
    render(
      <AbsenceAnalyticsView
        monthly={[]}
        weekday={[]}
        subjects={MOCK_SUBJECTS}
        isLoading={false}
      />
    );

    expect(
      screen.getByText(/Insufficient Timetable Observations/i)
    ).toBeInTheDocument();
  });

  it("renders monthly and weekday breakdowns when data is present", () => {
    render(
      <AbsenceAnalyticsView
        monthly={MOCK_MONTHLY}
        weekday={MOCK_WEEKDAY}
        subjects={MOCK_SUBJECTS}
        isLoading={false}
      />
    );

    expect(screen.getByText("October 2026")).toBeInTheDocument();
    expect(screen.getByText("Monday")).toBeInTheDocument();
    expect(screen.getByText("20.0%")).toBeInTheDocument(); // Absence rate
    expect(screen.getByText("Computer Architecture")).toBeInTheDocument();
  });

  it("switches ranking tabs between absolute missed, missed rate, and total delivered", () => {
    render(
      <AbsenceAnalyticsView
        monthly={MOCK_MONTHLY}
        weekday={MOCK_WEEKDAY}
        subjects={MOCK_SUBJECTS}
        isLoading={false}
      />
    );

    const rateTab = screen.getByRole("button", { name: /By Absence Rate/i });
    fireEvent.click(rateTab);
    expect(screen.getByText("25.00%")).toBeInTheDocument();

    const deliveredTab = screen.getByRole("button", { name: /By Total Delivered/i });
    fireEvent.click(deliveredTab);
    expect(screen.getByText("20 periods")).toBeInTheDocument();
  });
});
