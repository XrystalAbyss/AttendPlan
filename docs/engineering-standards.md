# AttendPlan Engineering Standards

## 1. Code Standards & Style

### 1.1 Python Backend
- **Python Version**: Python 3.12+
- **Type Checking**: Strict type annotations across all domain, adapter, and API files. Verified with `mypy`.
- **Linting & Formatting**: Follow PEP 8 guidelines enforced by `ruff`.
- **Validation**: Pydantic v2 schemas for all external inputs and DTOs.
- **Error Handling**:
  - Never swallow exceptions with bare `except:` or `except Exception: pass`.
  - Raise explicit, typed domain exceptions (e.g. `InvalidAttendanceError`, `ParserError`).
  - Return clear, human-readable HTTP error payloads.

### 1.2 TypeScript Frontend
- **Frontend Framework**: React 18+ with TypeScript in strict mode.
- **Styling**: Tailwind CSS with clear semantic class grouping and CSS variables.
- **Components**: Functional components with explicit prop types.
- **State Management**:
  - Server state: TanStack Query (React Query) with explicit caching and invalidation keys.
  - Derived state: Compute derived metrics (safe courses, percentages) in pure render functions or `useMemo`. Never duplicate source state.
- **No Blanket `any`**: TypeScript code must avoid `any`. Define explicit interfaces matching backend schemas.

---

## 2. Invariants & Mathematical Precision
1. **Never Round Intermediate Values**: All threshold logic must check against exact rational fractions.
2. **Never Average Percentages**: Aggregate percentage is always:
   $$\frac{\sum \text{attended}}{\sum \text{delivered}} \times 100$$
3. **Handle Undefined (0/0)**: A course with 0 delivered periods has undefined percentage and margins. Never display as 0% or 100%.
4. **Lab Periods Multiplier**: Scheduled lab slots represent their actual counted periods (typically 2). Simulations must account for actual credit / period weights.

---

## 3. Git & Security Hygeine
1. **Never Commit Secrets**: No tokens, session cookies, passwords, or authenticator secrets in git history.
2. **Never Commit PII**: No real student IDs, names, email addresses, or phone numbers in test fixtures or code.
3. **Branch Protection**: Clean commit messages describing the change rationale.
4. **Offline Isolation**: Test fixtures must run completely offline without network calls.
