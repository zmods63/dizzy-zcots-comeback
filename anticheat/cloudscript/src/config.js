const env = process.env;
const list = (v) => (v || "").split(",").map((s) => s.trim()).filter(Boolean);
const num = (v, d) => (v === undefined || v === "" ? d : Number(v));
const hours = (v, d) => (v === undefined || v === "" ? d : v === "permanent" ? null : Number(v));

module.exports = {
  titleId: env.PLAYFAB_TITLE_ID,
  secretKey: env.PLAYFAB_DEV_SECRET_KEY,

  dryRun: env.AC_DRY_RUN !== "false",

  platforms: list(env.AC_PLATFORMS || "android"),

  failOpen: env.AC_FAIL_OPEN === "true",
  failOpenTtlMs: 5 * 60 * 1000,

  android: {
    packageName: env.ANDROID_PACKAGE_NAME,
    certSha256: list(env.ANDROID_CERT_SHA256),
    requirePlayRecognized: env.ANDROID_REQUIRE_PLAY_RECOGNIZED !== "false",
    requireStrong: env.ANDROID_REQUIRE_STRONG === "true",
    requireLicensed: env.ANDROID_REQUIRE_LICENSED === "true",
    blockControllingApps: env.ANDROID_BLOCK_CONTROLLING_APPS !== "false",
    serviceAccountJson: env.GOOGLE_SERVICE_ACCOUNT_JSON,
    maxTokenAgeMs: 2 * 60 * 1000,
  },

  quest: {
    appId: env.QUEST_APP_ID,
    appSecret: env.QUEST_APP_SECRET,
    packageName: env.QUEST_PACKAGE_NAME,
    certSha256: list(env.QUEST_CERT_SHA256),
    allowBasicDevice: env.QUEST_ALLOW_BASIC_DEVICE !== "false",
    maxTokenAgeMs: 2 * 60 * 1000,
  },

  attestTtlMs: num(env.AC_ATTEST_TTL_MIN, 30) * 60 * 1000,
  nonceTtlMs: 2 * 60 * 1000,
  minAttestIntervalMs: 10 * 1000,

  banHoursTamper: hours(env.AC_BAN_HOURS_TAMPER, null),
  banLadderHours: [1, 24, 168, null],

  shadowDays: num(env.AC_SHADOW_DAYS, 14),
  lagMinMs: num(env.AC_LAG_MIN_MS, 1500),
  lagMaxMs: num(env.AC_LAG_MAX_MS, 5000),
};
