const crypto = require("crypto");
const cfg = require("./config");
const { certMatches } = require("./digest");

let cachedToken = null;

async function googleAccessToken() {
  if (cachedToken && cachedToken.exp - 60_000 > Date.now()) return cachedToken.value;
  const sa = JSON.parse(cfg.android.serviceAccountJson);
  const now = Math.floor(Date.now() / 1000);
  const b64 = (o) => Buffer.from(JSON.stringify(o)).toString("base64url");
  const unsigned = `${b64({ alg: "RS256", typ: "JWT" })}.${b64({
    iss: sa.client_email,
    scope: "https://www.googleapis.com/auth/playintegrity",
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
  })}`;
  const sig = crypto.createSign("RSA-SHA256").update(unsigned).sign(sa.private_key).toString("base64url");
  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: `${unsigned}.${sig}`,
    }),
  });
  if (!res.ok) throw new Error(`Google OAuth failed: ${res.status} ${await res.text()}`);
  const json = await res.json();
  cachedToken = { value: json.access_token, exp: Date.now() + json.expires_in * 1000 };
  return cachedToken.value;
}

async function decode(token) {
  const pkg = encodeURIComponent(cfg.android.packageName);
  const res = await fetch(`https://playintegrity.googleapis.com/v1/${pkg}:decodeIntegrityToken`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${await googleAccessToken()}` },
    body: JSON.stringify({ integrity_token: token }),
  });
  if (res.status === 400) return { invalid: true, detail: await res.text() };
  if (!res.ok) throw new Error(`Play Integrity decode failed: ${res.status} ${await res.text()}`);
  return { payload: (await res.json()).tokenPayloadExternal };
}

function judge(p, expectedNonce, now, c = cfg.android) {
  const reasons = { tamper: [], invalid: [], device: [] };
  const rd = p.requestDetails || {};
  const ai = p.appIntegrity || {};
  const di = p.deviceIntegrity || {};

  if (rd.requestPackageName !== c.packageName) reasons.tamper.push("request_package_mismatch");
  if (rd.nonce !== expectedNonce) reasons.invalid.push("nonce_mismatch");
  const age = now - Number(rd.timestampMillis);
  if (!(age > -60_000 && age < c.maxTokenAgeMs)) reasons.invalid.push("token_stale");

  if (ai.appRecognitionVerdict === "UNEVALUATED" || !ai.appRecognitionVerdict) {
    reasons.device.push("app_unevaluated");
  } else {
    if (c.requirePlayRecognized && ai.appRecognitionVerdict !== "PLAY_RECOGNIZED")
      reasons.tamper.push(`app_${ai.appRecognitionVerdict.toLowerCase()}`);
    if (ai.packageName && ai.packageName !== c.packageName) reasons.tamper.push("app_package_mismatch");
    if (!certMatches(ai.certificateSha256Digest, c.certSha256)) reasons.tamper.push("cert_mismatch");
  }

  const verdicts = di.deviceRecognitionVerdict || [];
  const need = c.requireStrong ? "MEETS_STRONG_INTEGRITY" : "MEETS_DEVICE_INTEGRITY";
  if (!verdicts.includes(need)) reasons.device.push(verdicts.length ? `device_lacks_${need.toLowerCase()}` : "device_no_integrity");

  if (c.requireLicensed && (p.accountDetails || {}).appLicensingVerdict !== "LICENSED") reasons.invalid.push("unlicensed");

  const apps = ((p.environmentDetails || {}).appAccessRiskVerdict || {}).appsDetected || [];
  if (c.blockControllingApps && apps.includes("UNKNOWN_CONTROLLING")) reasons.device.push("controlling_app_detected");

  const severity = ["tamper", "invalid", "device"].find((k) => reasons[k].length);
  return { ok: !severity, severity, reasons: [...reasons.tamper, ...reasons.invalid, ...reasons.device] };
}

async function verify(token, expectedNonce, now) {
  const { payload, invalid } = await decode(token);
  if (invalid) return { ok: false, severity: "invalid", reasons: ["token_rejected_by_google"] };
  return judge(payload, expectedNonce, now);
}

module.exports = { verify, judge };
