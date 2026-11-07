# AttendPlan Student Authenticator & Login Enrollment Guide (F2-C)

## 1. Overview
AttendPlan F2-C provides seamless, one-time enrollment of your university login credentials (registered mobile number and Google Authenticator TOTP secret) to enable automated Keycloak login while maintaining strict local-first security.

---

## 2. Step-by-Step Enrollment Guide

### Step 1: Save Your Registered Mobile Number
1. In AttendPlan, click the **Auth & Vault** button in the top navigation header (or navigate to **Settings > Authentication**).
2. Select the **Mobile Identity** tab.
3. Enter your 10-digit registered university mobile number (e.g., `9876543210`).
4. Ensure the toggles **Automatic Mobile Autofill** and **Automatic Login Continuation** are checked.
5. Click **Save Settings**.
   *Note: Your mobile number is stored locally in `%LOCALAPPDATA%\AttendPlan\settings.json` and will never leave your machine.*

---

### Step 2: Enroll Your Google Authenticator Secret
Navigate to the **Google Authenticator** tab in the Authentication Settings modal. AttendPlan supports three convenient enrollment methods:

#### Option A: Upload QR Code Screenshot (Recommended)
1. If you saved the QR code image provided by Keycloak during your initial university MFA setup, click **Upload QR Screenshot**.
2. Select the `.png`, `.jpg`, or `.webp` file.
3. AttendPlan parses the QR image completely offline in memory, populates the Account Candidate details, and prompts you to save it.

#### Option B: Google Authenticator Cloud / Device Transfer URI
1. In Google Authenticator on your mobile phone:
   - Tap the top-right menu $\to$ **Transfer accounts** $\to$ **Export accounts**.
   - Select your university account and export.
   - Scan or copy the resulting migration URI beginning with `otpauth-migration://offline?data=...`.
2. Paste this URI into the **Secret Key / URI** input field and click **Inspect Secret**.
3. AttendPlan automatically decodes the Google migration protobuf payload offline, extracts the Base32 secret and issuer, and prepares enrollment.

#### Option C: Manual Base32 Secret Key
1. If you have the original alphanumeric Base32 setup key (e.g., `JBSWY3DPEHPK3PXP`), paste it directly into the input field.
2. Enter the account name (e.g., your student roll number or email) and issuer (`iCloudEMS`).
3. Click **Enroll in Vault**.

---

### Step 3: Verify Time Synchronization & Clock Drift
1. Once enrolled, the modal will display **Status: Enrolled (Unverified)**.
2. Open your Google Authenticator mobile app and look at the current 6-digit code for your university account.
3. Type the 6-digit code into the **Verify TOTP Code** input box in AttendPlan.
4. Click **Verify Code**.
5. AttendPlan verifies that its local RFC 6238 time generator matches your device's time step. Upon match, the vault status updates to **Verified & Active**.

---

### Step 4: Run Automated Student Login
1. On the AttendPlan **Sync Center** tab (or inside the **Automated Login** tab of the Auth modal), click **Run Automated Keycloak Login**.
2. AttendPlan executes the automated login state machine:
   - **Session Check**: Verifies if an existing active student session exists in Chrome. If already authenticated, it skips login immediately.
   - **Mobile Entry**: Navigates to the Keycloak login page, autofills your registered mobile number into `input#username`, and submits.
   - **TOTP Generation**: Detects the OTP challenge form, retrieves the secret from Windows Credential Manager, generates the active 6-digit code, enters it into `input#otp`, and submits.
   - **Dashboard Verification**: Confirms redirection to the authenticated student dashboard.
3. The browser remains in your control, and AttendPlan proceeds with attendance synchronization.

---

## 3. Manual Fallback & Edge Cases

| Scenario | System Behavior & User Action |
| :--- | :--- |
| **Existing Session Valid** | Skips login entirely and resumes sync immediately. |
| **CAPTCHA Challenge** | State transitions to `MANUAL_ACTION_REQUIRED`. User solves CAPTCHA in Chrome; AttendPlan detects completion. |
| **Password Change / Portal Reset** | State transitions to `MANUAL_ACTION_REQUIRED`. User logs in once manually; AttendPlan preserves session cookies. |
| **Missing Mobile Number** | Halts with `MANUAL_ACTION_REQUIRED` and directs student to configure mobile number in Settings. |
| **Missing TOTP Enrollment** | Submits mobile number, then halts at OTP screen for manual entry if vault is unconfigured. |
| **Repeated Submission Prevention** | AttendPlan will never submit identical forms in a loop; halts on first failure or invalid origin. |
