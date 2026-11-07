# AttendPlan — Synchronization Troubleshooting Guide

## 1. Quick Diagnostic Checklist
If synchronization fails or status shows `DISCONNECTED` or `ERROR`:

| Symptom | Probable Cause | Action |
|---|---|---|
| Status: `DISCONNECTED` | Dedicated Chrome is not running or CDP is not listening. | Click "Launch Dedicated Chrome" or run PowerShell command. |
| Status: `LOGIN_REQUIRED` | Student portal session not authenticated. | Complete Keycloak login and Google Authenticator MFA in Chrome. |
| Status: `SESSION_EXPIRED` | University portal timed out after inactivity. | Re-open Chrome, navigate to portal landing page, and log in. |
| Port 9222 Error | Another process occupies port 9222. | Check `netstat -ano \| findstr :9222` and terminate colliding task. |
| `403 Forbidden` from Portal | Automation triggered bot detection. | Headless Playwright is blocked. Use AttendPlan's dedicated Chrome CDP. |

---

## 2. Launching Dedicated Chrome Manually via PowerShell
If the UI "Launch Dedicated Chrome" button is blocked by Windows UAC or system policies, launch Chrome directly from PowerShell:

```powershell
$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$ProfileDir = "$env:LOCALAPPDATA\AttendPlan\chrome-profile"

Start-Process -FilePath $ChromePath -ArgumentList @(
    "--remote-debugging-port=9222",
    "--remote-debugging-address=127.0.0.1",
    "--user-data-dir=$ProfileDir",
    "--no-first-run",
    "--no-default-browser-check",
    "https://mrei.icloudems.com/corecampus/index.php"
)
```

---

## 3. Verifying CDP Connectivity
To verify that Chrome is responding on loopback port 9222:
```powershell
curl http://127.0.0.1:9222/json
```
Output should contain a JSON array with `type: "page"` and the active portal tab URL.

---

## 4. Manual HTML Fallback Procedure
If the university portal blocks browser automation entirely or CDP is restricted by host security software:
1. In the student's normal browser, log into iCloudEMS.
2. Navigate to `Subject Wise Attendance` or `Day Wise Attendance`.
3. Right-click the page -> **View Page Source** or press `Ctrl + U`.
4. Copy the raw HTML source.
5. In AttendPlan Sync Center, click **"Use Manual HTML Fallback"**.
6. Paste the HTML into the text box and click **"Discover Subject-Wise"** or **"Discover Day-Wise"**.
7. The deterministic parser processes the HTML offline without CDP or Playwright dependencies.
