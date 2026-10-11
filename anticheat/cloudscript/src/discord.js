const url = process.env.DISCORD_WEBHOOK_URL;

const clean = (s, max) => String(s ?? "").slice(0, max).replace(/[\\`*_~|>]/g, "\\$&") || "-";

async function reportCheater({ playFabId, name, platform, severity, reasons, action, banHours, strikes, dryRun }) {
  if (!url) return;
  const ban = action !== "banned" ? "none" : banHours === null ? "PERMANENT" : `${banHours}h`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: "Anti-Cheat",
      allowed_mentions: { parse: [] },
      embeds: [
        {
          title: dryRun ? "Cheater detected (DRY RUN - not punished)" : "Cheater detected & kicked",
          color: severity === "tamper" ? 0xe02424 : severity === "device" ? 0xf59e0b : 0x7c3aed,
          fields: [
            { name: "Name", value: clean(name, 100), inline: true },
            { name: "PlayFab ID", value: clean(playFabId, 32), inline: true },
            { name: "Platform", value: clean(platform, 20), inline: true },
            { name: "Type", value: clean(severity, 20), inline: true },
            { name: "Ban", value: ban, inline: true },
            { name: "Strikes", value: String(strikes ?? "-"), inline: true },
            { name: "Reasons", value: clean((reasons || []).join(", "), 1000) },
          ],
          timestamp: new Date().toISOString(),
        },
      ],
    }),
  });
  if (!res.ok) throw new Error(`Discord webhook failed: ${res.status}`);
}

module.exports = { reportCheater };
