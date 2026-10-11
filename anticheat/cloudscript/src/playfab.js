const cfg = require("./config");

async function server(api, body) {
  const res = await fetch(`https://${cfg.titleId}.playfabapi.com/Server/${api}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-SecretKey": cfg.secretKey },
    body: JSON.stringify(body),
  });
  const json = await res.json().catch(() => ({}));
  if (json.code !== 200) throw new Error(`PlayFab ${api} failed: ${json.errorMessage || res.status}`);
  return json.data;
}

async function getInternal(playFabId, key) {
  const data = await server("GetUserInternalData", { PlayFabId: playFabId, Keys: [key] });
  const entry = data.Data && data.Data[key];
  return entry ? entry.Value : null;
}

const setInternal = (playFabId, key, value) =>
  server("UpdateUserInternalData", { PlayFabId: playFabId, Data: { [key]: value } });

const ban = (playFabId, hours, reason) =>
  server("BanUsers", {
    Bans: [{ PlayFabId: playFabId, Reason: reason, ...(hours === null ? {} : { DurationInHours: hours }) }],
  });

const addTag = (playFabId, tag) => server("AddPlayerTag", { PlayFabId: playFabId, TagName: tag });

const event = (playFabId, name, body) =>
  server("WritePlayerEvent", { PlayFabId: playFabId, EventName: name, Body: body });

async function displayName(playFabId) {
  const data = await server("GetPlayerProfile", {
    PlayFabId: playFabId,
    ProfileConstraints: { ShowDisplayName: true },
  });
  return (data.PlayerProfile && data.PlayerProfile.DisplayName) || "(no name)";
}

module.exports = { getInternal, setInternal, ban, addTag, event, displayName };
