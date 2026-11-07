# AttendPlan interface reference notes

22 October 2026. This is a focused polish of the existing dashboard. Attendance ingestion, historical component identity, authentication and database contracts are outside this visual change.

## References reviewed and decisions

| Reference | Suitable public resource / idea | Applied to AttendPlan |
|---|---|---|
| [Taste Skill](https://www.tasteskill.dev/) | Public guidance about typography, hierarchy, existing-project audits and parity between light/dark modes | Warm editorial overview heading, restrained copper accent, systematic surfaces, readable metrics and both sepia modes |
| [21st navigation guidance](https://21st.dev/community/components/s/navigation-menu) | Public navigation examples and guidance about clear destinations, current-page indication and narrow screens | One consistent navigation component, semantic current-page indication, scrollable mobile navigation and visible keyboard focus |
| [GSAP media-query documentation](https://gsap.com/docs/v3/GSAP/gsap.matchMedia()/) | Public guidance for responsive motion and respecting reduced-motion preferences | A short native CSS entrance; all interface animations/transitions disabled for reduced motion. No count-up animation changes the displayed data |
| [ThreeUI catalog](https://threeui.com/) and [pricing](https://threeui.com/pricing) | Public catalog of Three.js, CSS, shaders and authored interface examples; source offerings include paid plans | Restrained surface depth informed the visual direction. No WebGL effects, paid source, illustrative assets or GPU backgrounds were imported |

The public Taste site identifies its guidance as open source/MIT. The linked individual minimalist skill file could not be fetched during research; it was not installed or claimed as used. 21st components have individual authors and usage terms; no unverified community source was copied. GSAP is a reference here, not an installed dependency. The implementation is original local React/CSS using already installed Lucide icons. No new package, external font, CDN, tracking script or remote runtime resource was added.

## Changes

- Attendance is visible earlier: login/archive tools are grouped in a native expandable control, with the current archive attention/sync status still visible when collapsed.
- All existing settings, preview/approval actions and job controls remain available inside the expanded panel. Collapsing it changes presentation, not authorization or endpoint behavior.
- Overview cards distinguish safe-to-miss subjects from zero-buffer Caution subjects. Those categories no longer overlap. Unknown attendance stays unknown.
- Existing seven views share a consistent navigation treatment. The active view is exposed with `aria-current`; keyboard navigation uses native buttons.
- Both sepia modes share typography, spacing, surfaces and copper accents; green/amber/red retain their attendance meanings. Theme changes remain immediate.
- Course filters expose their selected state; course and semester fields have accessible labels. Dense data stays in horizontally scrollable tables.
- The subject/month chart has a labeled 0–100% axis and target line. It plots only known percentages; unknown initial observations are not drawn as zero attendance.
- Marks tables and assessment details receive consistent spacing, borders and numerical alignment. No marks or results were fabricated.
- Sync Center subtabs wrap on mobile instead of overflowing the page. Archive coverage text explicitly identifies months saved in that run, avoiding confusion with all locally saved months.

## Verification

See the dated UI verification JSON and report in the workspace outputs directory for actual results. Browser checks block every non-GET API request, so they cannot trigger login, discovery, previews or imports. Check desktop/mobile in both themes, every main view, expandable controls, saved September rows, saved marks assessment controls, focus, reduced motion and no root overflow. Also rerun theme-stability and lab-simulation checks because theme styling and shared navigation changed. The complete repository gates are required before reporting completion.

Known historical route/row-identity blockers are documented in `HISTORICAL_PREVIEW_20261022.md` in the workspace outputs. Styling does not resolve those source and persistence issues.
