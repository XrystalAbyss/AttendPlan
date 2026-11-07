import {standing} from "../standing";
import type React from "react";
import { useState, useEffect } from "react";
import { Sliders, X, ArrowRight, CheckCircle2, AlertTriangle, Plus, Minus } from "lucide-react";
import type { CourseRecord, CourseStatus } from "../types/attendance";

interface Props {
  course: CourseRecord | null;
  targetPercentage: number;
  onClose: () => void;
}

export const WhatIfSimulator: React.FC<Props> = ({
  course,
  targetPercentage,
  onClose,
}) => {

  const [deltaAttended, setDeltaAttended] = useState<number>(0);
  const [deltaMissed, setDeltaMissed] = useState<number>(0);

  // Reset when course changes
  useEffect(() => {
    setDeltaAttended(0);
    setDeltaMissed(0);
  }, [course?.code]);

  if (!course) return null;
  const step = course.is_lab ? 2 : 1;

  // Pure deterministic projection formula (Invariant 7)
  const simulatedAttended = course.attended + deltaAttended;
  const simulatedDelivered = course.delivered + deltaAttended + deltaMissed;

  let simulatedPercent: number | null = null;
  let simulatedStatus: CourseStatus = "UNRECORDED";
  let simulatedCanSkip: number = 0;
  let simulatedMustAttend: number = 0;

  if (simulatedDelivered > 0) {
    const ratio = simulatedAttended / simulatedDelivered;
    simulatedPercent = Math.round(ratio * 10000) / 100;
    const targetFraction = targetPercentage / 100;

    if (ratio >= targetFraction) {
      simulatedStatus = "SAFE";
      simulatedCanSkip = Math.max(
        0,
        Math.floor(simulatedAttended / targetFraction - simulatedDelivered)
      );
      simulatedMustAttend = 0;
    } else {
      simulatedStatus = "AT_RISK";
      simulatedCanSkip = 0;
      simulatedMustAttend = Math.max(
        0,
        Math.ceil((targetFraction * simulatedDelivered - simulatedAttended) / (1 - targetFraction))
      );
    }
  }

  const projectedStanding = standing({attended:simulatedAttended,delivered:simulatedDelivered,is_lab:course.is_lab});
  const currentStanding = standing(course);
  const isStatusChanged = currentStanding.status !== projectedStanding.status;

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[480px] bg-slate-900 border-l border-slate-800 shadow-2xl z-50 flex flex-col justify-between">
      {/* Drawer Header */}
      <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-850 bg-slate-800/40">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded bg-indigo-950/60 border border-indigo-800/60 text-indigo-400">
            <Sliders className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 m-0">
              What-If Scenario Simulator
            </h2>
            <div className="text-xs text-slate-400 font-mono mt-0.5">
              {course.code} &bull; {course.is_lab ? "Practical Lab" : "Theory"}
            </div>
          </div>
        </div>
        <button
          aria-label="Close simulator"
          onClick={onClose}
          className="text-slate-400 hover:text-slate-200 p-1 rounded hover:bg-slate-800 transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Drawer Body */}
      <div className="p-6 space-y-6 overflow-y-auto flex-1">
        <div>
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
              Course Title
            </h3>
            <span className="text-[10px] uppercase font-bold text-indigo-400 bg-indigo-950/80 border border-indigo-800/80 px-2 py-0.5 rounded">
              Hypothetical Projection
            </span>
          </div>
          <p className="text-sm font-medium text-slate-200">{course.name}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">
            This simulation models prospective periods. Official university records are not modified.
          </p>
        </div>

        {/* Dynamic Scenario Sentence */}
        {(deltaAttended > 0 || deltaMissed > 0) && (
          <div className="p-3 bg-indigo-950/40 border border-indigo-800/60 rounded-lg text-xs space-y-1">
            <span className="font-semibold text-indigo-200 block">Active Scenario:</span>
            <p className="text-slate-200 m-0 leading-relaxed">
              {deltaMissed > 0 && deltaAttended === 0 && (
                <>If you miss <strong>{deltaMissed}</strong> more {course.is_lab ? "periods" : "classes"}, your projected attendance becomes <strong className={simulatedPercent! < targetPercentage ? "text-rose-400" : "text-emerald-300"}>{simulatedPercent}%</strong>.</>
              )}
              {deltaAttended > 0 && deltaMissed === 0 && (
                <>If you attend <strong>{deltaAttended}</strong> more {course.is_lab ? "periods" : "classes"}, your projected attendance rises to <strong className="text-emerald-300">{simulatedPercent}%</strong>.</>
              )}
              {deltaAttended > 0 && deltaMissed > 0 && (
                <>With <strong>+{deltaAttended}</strong> attended and <strong>+{deltaMissed}</strong> missed periods, your projected attendance becomes <strong className={simulatedPercent! < targetPercentage ? "text-rose-400" : "text-emerald-300"}>{simulatedPercent}%</strong>.</>
              )}
            </p>
          </div>
        )}

        {/* Current vs Simulated Comparison Card */}
        <div className="bg-slate-800/70 border border-slate-700/80 rounded-lg p-4 space-y-3">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Outcome Comparison
          </div>

          <div className="flex items-center justify-between text-center">
            {/* Current State */}
            <div className="flex-1 bg-slate-900/80 p-3 rounded border border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase block">Current</span>
              <div className="text-xl font-bold font-mono text-slate-200 mt-1">
                {course.percent !== null ? `${course.percent.toFixed(1)}%` : "N/A"}
              </div>
              <div className="text-xs font-mono text-slate-400 mt-0.5">
                {course.attended}/{course.delivered}
              </div>
              <span
                className={`inline-block mt-2 text-[10px] font-bold px-2 py-0.5 rounded border ${
                  currentStanding.status === "CAUTION" ? "bg-amber-950/60 text-amber-300 border-amber-800" : currentStanding.status === "SAFE"
                    ? "bg-emerald-950/60 text-emerald-400 border-emerald-800"
                    : "bg-rose-950/60 text-rose-400 border-rose-800"
                }`}
              >
                {currentStanding.status}
              </span>
            </div>

            <div className="px-3 text-slate-500">
              <ArrowRight className="w-5 h-5" />
            </div>

            {/* Projected State */}
            <div
              className={`flex-1 p-3 rounded border ${
                projectedStanding.status === "CAUTION" ? "bg-amber-950/20 border-amber-700" : simulatedStatus === "SAFE"
                  ? "bg-emerald-950/20 border-emerald-800/60"
                  : "bg-rose-950/20 border-rose-800/60"
              }`}
            >
              <span className="text-[10px] text-slate-400 uppercase block">Projected</span>
              <div
                className={`text-xl font-bold font-mono mt-1 ${
                  projectedStanding.status === "CAUTION" ? "text-amber-300" : simulatedStatus === "SAFE" ? "text-emerald-400" : "text-rose-400"
                }`}
              >
                {simulatedPercent !== null ? `${simulatedPercent.toFixed(1)}%` : "N/A"}
              </div>
              <div className="text-xs font-mono text-slate-400 mt-0.5">
                {simulatedAttended}/{simulatedDelivered}
              </div>
              <span
                className={`inline-block mt-2 text-[10px] font-bold px-2 py-0.5 rounded border ${
                  projectedStanding.status === "CAUTION" ? "bg-amber-950/80 text-amber-300 border-amber-700" : simulatedStatus === "SAFE"
                    ? "bg-emerald-950/80 text-emerald-300 border-emerald-700"
                    : "bg-rose-950/80 text-rose-300 border-rose-700"
                }`}
              >
                {projectedStanding.status}
              </span>
            </div>
          </div>

          {isStatusChanged && (
            <div className="text-xs text-amber-300 bg-amber-950/40 border border-amber-800/60 p-2.5 rounded flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber-400" />
              <span>
                Status change: Transitioned from <strong>{currentStanding.status}</strong> to{" "}
                <strong>{projectedStanding.status}</strong>!
              </span>
            </div>
          )}
        </div>

        {/* Interactive Controls */}
        <div className="space-y-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Adjust Future Lectures
          </div>

          {/* Additional Attended (+x) */}
          <div className="bg-slate-800/50 border border-slate-700/60 p-3.5 rounded-lg flex items-center justify-between">
            <div>
              <div className="text-xs font-medium text-slate-200">
                Additional Attended Periods ({course.is_lab ? "+2 per lab session" : "+1 per class"})
              </div>
              <div className="text-[11px] text-slate-400">
                Increases both attended &amp; delivered counts
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setDeltaAttended(Math.max(0, deltaAttended - step))}
                className="w-7 h-7 rounded bg-slate-700 hover:bg-slate-600 flex items-center justify-center text-slate-200 cursor-pointer"
              >
                <Minus className="w-3.5 h-3.5" />
              </button>
              <span className="w-8 text-center font-mono font-bold text-slate-100">
                {deltaAttended}
              </span>
              <button
                aria-label={course.is_lab ? "Attend one lab session" : "Attend one class"}
                  onClick={() => setDeltaAttended(deltaAttended + step)}
                className="w-7 h-7 rounded bg-slate-700 hover:bg-slate-600 flex items-center justify-center text-slate-200 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Additional Missed (+y) */}
          <div className="bg-slate-800/50 border border-slate-700/60 p-3.5 rounded-lg flex items-center justify-between">
            <div>
              <div className="text-xs font-medium text-slate-200">
                Additional Missed Periods ({course.is_lab ? "+2 per lab session" : "+1 per class"})
              </div>
              <div className="text-[11px] text-slate-400">
                Increases delivered count only (bunk)
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setDeltaMissed(Math.max(0, deltaMissed - step))}
                className="w-7 h-7 rounded bg-slate-700 hover:bg-slate-600 flex items-center justify-center text-slate-200 cursor-pointer"
              >
                <Minus className="w-3.5 h-3.5" />
              </button>
              <span className="w-8 text-center font-mono font-bold text-slate-100">
                {deltaMissed}
              </span>
              <button
                aria-label={course.is_lab ? "Miss one lab session" : "Miss one class"}
                  onClick={() => setDeltaMissed(deltaMissed + step)}
                className="w-7 h-7 rounded bg-slate-700 hover:bg-slate-600 flex items-center justify-center text-slate-200 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Lab Block Quick Presets (2 periods) */}
          {course.is_lab && (
            <div className="p-3 bg-cyan-950/20 border border-cyan-800/40 rounded-lg">
              <div className="text-xs font-medium text-cyan-300 mb-2">
                Lab Block Shortcut (2 periods/meeting):
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setDeltaAttended((d) => d + 2)}
                  className="flex-1 py-1 px-2 text-xs bg-cyan-900/60 hover:bg-cyan-800/80 border border-cyan-700 text-cyan-200 rounded cursor-pointer"
                >
                  +1 Lab Attended (+2)
                </button>
                <button
                  onClick={() => setDeltaMissed((d) => d + 2)}
                  className="flex-1 py-1 px-2 text-xs bg-rose-950/60 hover:bg-rose-900/80 border border-rose-800 text-rose-300 rounded cursor-pointer"
                >
                  +1 Lab Missed (+2)
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Summary Projection Footer */}
        <div className="p-3.5 rounded bg-slate-850 bg-slate-800/40 border border-slate-700 text-xs space-y-1.5">
          <div className="text-slate-400 font-semibold uppercase text-[10px]">
            Projected Margin Details
          </div>
          {projectedStanding.status === "CAUTION" ? <p className="text-amber-300">Caution: attendance is at least 75%, but no complete {course.is_lab ? "two-period lab session" : "class"} can be missed.</p> : simulatedStatus === "SAFE" ? (
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>
                At {targetPercentage}%, you can safely miss up to{" "}
                <strong>{simulatedCanSkip}</strong> further period{simulatedCanSkip > 1 ? "s" : ""}.
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-rose-400">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>
                Need <strong>{simulatedMustAttend}</strong> consecutive attended period{simulatedMustAttend > 1 ? "s" : ""} to reach {targetPercentage}%.
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Drawer Close Button */}
      <div className="p-4 border-t border-slate-800 bg-slate-850 bg-slate-800/40">
        <button
          onClick={onClose}
          className="w-full py-2 px-4 rounded bg-slate-700 hover:bg-slate-600 text-slate-100 font-medium text-xs transition-colors cursor-pointer"
        >
          Close Simulator
        </button>
      </div>
    </div>
  );
};
