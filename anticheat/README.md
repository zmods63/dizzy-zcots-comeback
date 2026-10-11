# Anti-cheat (PlayFab + Photon)

Two parts:

| Folder | Needs a game update? | What it does |
|---|---|---|
| `legacy-cloudscript/` | **No** - server only, use it now | Bans blocked PlayFab IDs and non-moderators who own staff cosmetics or impossible coins/stats (moderators may hold up to 1M coins). Revokes items, wipes coins, bans, tags `ac_cheater`, posts name + PlayFab ID to Discord |
| `cloudscript/` + `unity/` | **Yes** - next client update | Real device attestation (Google Play Integrity / Meta Quest). Blocks rooted devices and re-signed APKs (Frida gadget), escalating bans, shadowban lag, Photon room kicks, Discord alerts |

> No server script can see Frida or root on its own. The device has to send an attestation
> token, and only the game client can request one. Until you ship the client part, the server
> can only catch what cheaters *do* (currency, stats, items).

---

## 1. Server-only (works today): `legacy-cloudscript/anticheat.js`

1. **Game Manager > Automation > CloudScript > Revisions (Legacy)**: add `anticheat.js` to your
   current revision (or paste it at the bottom of your existing script). Do **not** replace your
   existing script, or every handler you already have stops working. Deploy the revision.
2. **Title Settings > Title Internal Data** (server-only, players can't read it):
   - `ac_discord_webhook` = your Discord webhook URL. Keep it here, not in code or git.
   - `ac_config` = JSON, e.g.
     ```json
     {
       "dryRun": true,
       "banHours": null,
       "wipeCurrency": true,
       "moderators":     ["MOD_PLAYFAB_ID_1", "MOD_PLAYFAB_ID_2"],
       "modCurrencyCap": 1000000,
       "bannedIds":      ["CHEATER_PLAYFAB_ID"],
       "forbiddenItems": ["mod_badge", "dev_hat"],
       "currencyCaps":    { "CO": 100000 },
       "maxCurrencyGain": { "CO": 5000 },
       "statCaps": {}, "maxStatJump": {}
     }
     ```
   - `banHours: null` = permanent.
   - `forbiddenItems` = staff-only cosmetics. Anyone not in `moderators` who owns one is caught.
   - `moderators` may own them and hold up to `modCurrencyCap` coins. A moderator over that cap
     gets the extra coins removed and a Discord alert, but is never banned.
   - `bannedIds` = PlayFab IDs to kick and ban.
   - Use your real currency code, item IDs and stat names. Leave `maxCurrencyGain` above anything
     a real purchase can grant.
3. **Automation > Rules**, one rule per event, action **Execute CloudScript**:
   - `com.playfab.player_logged_in` -> `AC_OnLogin` (checks blocked ID, staff cosmetics and coins at every login)
   - `com.playfab.player_virtual_currency_balance_changed` -> `AC_OnCurrencyChanged`
   - `com.playfab.player_statistic_changed` -> `AC_OnStatisticChanged`
   - `com.playfab.player_inventory_item_added` -> `AC_OnItemAdded`
4. **Automation > Scheduled Tasks**: new task, type *Execute CloudScript*, function
   `AC_SweepBlockedIds`, every hour. Click *Run now* after you add IDs to `bannedIds`, to ban them
   right away even if they're online. Each run handles 5 IDs.
5. Run with `"dryRun": true` for a day. Discord shows "DRY RUN" hits; nobody is punished.
   When the hits are all real cheaters, set `"dryRun": false`.

When someone is caught: staff cosmetics revoked, all coins wiped, permanent ban (their PlayFab
calls fail right away), tagged `ac_cheater`, PlayStream `ac_violation` event, and a Discord post
with their name and PlayFab ID. A ban can't pull them out of the Photon room they're already in.
If Photon uses PlayFab auth, they can't connect again. A true instant room kick needs a client update.

### Zero-code lockdown (do this now, biggest win)
- **Title Settings > API Features**: turn off *Allow client to add virtual currency*,
  *Allow client to subtract virtual currency* and *Allow client to post player statistics*,
  unless your game really needs them. Check first: switching off something the game uses breaks that feature.
- Check your existing CloudScript handlers: any handler that grants currency or items from
  `args` without checking is how mod menus give themselves stuff.
- **Photon dashboard > your app > Authentication**: use PlayFab custom auth
  (`https://<TITLEID>.playfabapi.com/photon/authenticate`) and **disallow anonymous clients**.
  Banned PlayFab accounts then can't connect to Photon at all. Only turn this on if your client
  already sends the PlayFab Photon token, otherwise nobody can connect.

---

## 2. Attestation (next client update): `cloudscript/` + `unity/AntiCheatClient.cs`

PlayFab CloudScript **using Azure Functions** (Node 18+). It can't be legacy CloudScript, because
verifying Google tokens needs RSA signing, which the legacy runtime doesn't have.

Functions: `AC_GetChallenge`, `AC_Attest`, `AC_CheckPlayers`.

1. Deploy `cloudscript/` as an Azure Function App (`func azure functionapp publish <app>`).
2. Set the App Settings listed in `local.settings.example.json`: PlayFab title/secret,
   `DISCORD_WEBHOOK_URL`, package name, signing-cert SHA-256, Google service-account JSON
   (Play Console > App integrity > link a Cloud project, enable Play Integrity API).
3. Register each function in **PlayFab > Automation > CloudScript > Functions** with its
   function-key URL (keep `authLevel: function`, so only PlayFab can call it).
4. Unity: add `AntiCheatClient` to a startup object and call `BeginAfterPlayFabLogin()` after
   login. Android needs the Google Play Integrity Unity plugin. For Quest, add the scripting
   define `AC_QUEST` and use the Meta Platform SDK v55+. Create Photon rooms with `PublishUserId = true`.
5. `AC_DRY_RUN` defaults to **true**. Check Discord and PlayStream `ac_violation`, then set it to `false`.

What happens when it fails:
- **Modified/re-signed APK** (Frida gadget, patched libs): permanent ban (`AC_BAN_HOURS_TAMPER`).
- **Rooted / untrusted device, bad or replayed token**: bans of 1h, then 24h, then 7d, then permanent.
- **Every violation**: 14-day shadowban. Their CloudScript calls get 1.5-5s of added delay, and the
  room master client kicks them (`CloseConnection`) and blocks them for everyone in the room.
- **Never attested** (attestation skipped or blocked): kicked from rooms after a 45s grace period, not banned.

Tests: `cd cloudscript && npm install && npm test`.

### Limits
- Quest attestation only works for builds from the Meta Horizon Store. Sideloaded builds always
  fail it, so leave `quest` out of `AC_PLATFORMS` for sideloaded builds.
- Root-hiding modules can sometimes fake basic/device integrity. `ANDROID_REQUIRE_STRONG=true`
  (hardware-backed) is much harder to fake, but older phones fail it.
- Photon Cloud relays traffic without inspecting it. Movement cheats (fly, speed, tag-all) can't be
  seen server-side without a Photon Server plugin. Attestation stops the modified client from
  getting in, which is the main defense.
