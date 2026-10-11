using System;
using System.Collections;
using System.Collections.Generic;
using Photon.Pun;
using Photon.Realtime;
using PlayFab;
using PlayFab.CloudScriptModels;
using UnityEngine;
using Hashtable = ExitGames.Client.Photon.Hashtable;
#if UNITY_ANDROID && !UNITY_EDITOR && !AC_QUEST
using Google.Play.Integrity;
#endif
#if AC_QUEST && !UNITY_EDITOR
using Oculus.Platform;
#endif

public class AntiCheatClient : MonoBehaviourPunCallbacks
{
    public static AntiCheatClient Instance { get; private set; }
    public static bool IsAttested { get; private set; }

    public static event Action<string> OnKicked;

    [Tooltip("Google Cloud project number. Only needed if the app is NOT installed from Google Play.")]
    public long cloudProjectNumber = 0;
    public float reattestMinutes = 20f;
    public float roomCheckSeconds = 10f;
    public float newPlayerGraceSeconds = 45f;

    const string BlockKey = "ac_block";

    readonly Dictionary<int, float> joinTimes = new Dictionary<int, float>();
    readonly HashSet<string> blocked = new HashSet<string>();
    bool started;

    [Serializable] public class ChallengeResult { public string nonce; }
    [Serializable] public class AttestResult { public bool ok; public bool retry; public bool kick; public string reason; }

    void Awake()
    {
        if (Instance != null) { Destroy(gameObject); return; }
        Instance = this;
        DontDestroyOnLoad(gameObject);
    }

    public void BeginAfterPlayFabLogin()
    {
        if (started) return;
        started = true;
        StartCoroutine(AttestLoop());
        StartCoroutine(RoomWatchLoop());
    }

    IEnumerator AttestLoop()
    {
        while (true)
        {
            bool done = false, ok = false, retry = true;
            RunAttestation((success, shouldRetry) => { ok = success; retry = shouldRetry; done = true; });
            while (!done) yield return null;
            IsAttested = ok;
            if (!ok && !retry) yield break;
            yield return new WaitForSecondsRealtime(ok ? reattestMinutes * 60f : 15f);
        }
    }

    void RunAttestation(Action<bool, bool> finish)
    {
        Execute("AC_GetChallenge", null, raw =>
        {
            var challenge = Parse<ChallengeResult>(raw);
            if (challenge == null || string.IsNullOrEmpty(challenge.nonce)) { finish(false, true); return; }
            RequestPlatformToken(challenge.nonce, (platform, token) =>
            {
                if (string.IsNullOrEmpty(token)) { finish(false, true); return; }
                Execute("AC_Attest", new Dictionary<string, object> { { "platform", platform }, { "token", token } }, raw2 =>
                {
                    var result = Parse<AttestResult>(raw2);
                    if (result == null) { finish(false, true); return; }
                    if (result.kick) { Kick(result.reason); finish(false, false); return; }
                    finish(result.ok, true);
                }, () => finish(false, true));
            });
        }, () => finish(false, true));
    }

    void RequestPlatformToken(string nonce, Action<string, string> done)
    {
#if AC_QUEST && !UNITY_EDITOR
        DeviceApplicationIntegrity.GetIntegrityToken(nonce).OnComplete(msg =>
            done("quest", msg.IsError ? null : msg.GetString()));
#elif UNITY_ANDROID && !UNITY_EDITOR
        StartCoroutine(PlayIntegrity(nonce, done));
#else
        Debug.Log("[AntiCheat] No attestation in the editor; use AC_DRY_RUN=true while testing.");
        done("editor", null);
#endif
    }

#if UNITY_ANDROID && !UNITY_EDITOR && !AC_QUEST
    IEnumerator PlayIntegrity(string nonce, Action<string, string> done)
    {
        var manager = new IntegrityManager();
        var request = cloudProjectNumber != 0 ? new IntegrityTokenRequest(nonce, cloudProjectNumber) : new IntegrityTokenRequest(nonce);
        var op = manager.RequestIntegrityToken(request);
        yield return op;
        done("android", op.Error == IntegrityErrorCode.NoError ? op.GetResult().Token : null);
    }
#endif

    void Kick(string reason)
    {
        IsAttested = false;
        StopAllCoroutines();
        if (PhotonNetwork.IsConnected) PhotonNetwork.Disconnect();
        string message = reason == "device"
            ? "Rooted or modified devices are not allowed."
            : "Modified game detected. You have been banned.";
        Debug.LogWarning("[AntiCheat] " + message);
        OnKicked?.Invoke(message);
    }

    IEnumerator RoomWatchLoop()
    {
        var wait = new WaitForSecondsRealtime(roomCheckSeconds);
        while (true)
        {
            yield return wait;
            if (!PhotonNetwork.InRoom || !PhotonNetwork.IsMasterClient) continue;

            var ids = new List<string>();
            var byId = new Dictionary<string, Player>();
            foreach (var p in PhotonNetwork.PlayerListOthers)
            {
                if (string.IsNullOrEmpty(p.UserId))
                {
                    if (PhotonNetwork.CurrentRoom.PublishUserId) KickFromRoom(p);
                    continue;
                }
                if (joinTimes.TryGetValue(p.ActorNumber, out var t) && Time.realtimeSinceStartup - t < newPlayerGraceSeconds) continue;
                ids.Add(p.UserId);
                byId[p.UserId] = p;
            }
            if (ids.Count == 0) continue;

            Execute("AC_CheckPlayers", new Dictionary<string, object> { { "playFabIds", ids } }, raw =>
            {
                var players = ParsePlayers(raw);
                foreach (var kv in players)
                    if ((kv.Value == "flagged" || kv.Value == "unverified") && byId.TryGetValue(kv.Key, out var p))
                        KickFromRoom(p);
            }, null);
        }
    }

    void KickFromRoom(Player p)
    {
        if (!string.IsNullOrEmpty(p.UserId) && blocked.Add(p.UserId))
        {
            var list = new List<string>(blocked).ToArray();
            PhotonNetwork.CurrentRoom.SetCustomProperties(new Hashtable { { BlockKey, list } });
        }
        PhotonNetwork.CloseConnection(p);
        HidePlayer(p);
    }

    public static bool IsBlocked(Player p)
    {
        return Instance != null && p != null && !string.IsNullOrEmpty(p.UserId) && Instance.blocked.Contains(p.UserId);
    }

    void HidePlayer(Player p)
    {
        foreach (var view in PhotonNetwork.PhotonViewCollection)
            if (view != null && view.Owner == p) view.gameObject.SetActive(false);
    }

    public override void OnPlayerEnteredRoom(Player p)
    {
        joinTimes[p.ActorNumber] = Time.realtimeSinceStartup;
        if (IsBlocked(p)) { if (PhotonNetwork.IsMasterClient) PhotonNetwork.CloseConnection(p); HidePlayer(p); }
    }

    public override void OnPlayerLeftRoom(Player p) { joinTimes.Remove(p.ActorNumber); }

    public override void OnJoinedRoom()
    {
        joinTimes.Clear();
        foreach (var p in PhotonNetwork.PlayerListOthers) joinTimes[p.ActorNumber] = Time.realtimeSinceStartup;
        ApplyBlockList(PhotonNetwork.CurrentRoom.CustomProperties);
    }

    public override void OnMasterClientSwitched(Player newMaster)
    {
        foreach (var p in PhotonNetwork.PlayerListOthers) joinTimes[p.ActorNumber] = Time.realtimeSinceStartup;
    }

    public override void OnRoomPropertiesUpdate(Hashtable changed) { ApplyBlockList(changed); }

    void ApplyBlockList(Hashtable props)
    {
        if (props == null || !props.TryGetValue(BlockKey, out var value) || !(value is string[] ids)) return;
        foreach (var id in ids) blocked.Add(id);
        foreach (var p in PhotonNetwork.PlayerListOthers)
            if (IsBlocked(p)) HidePlayer(p);
    }

    void Execute(string function, object args, Action<object> onOk, Action onFail)
    {
        PlayFabCloudScriptAPI.ExecuteFunction(new ExecuteFunctionRequest
        {
            FunctionName = function,
            FunctionParameter = args,
            GeneratePlayStreamEvent = false
        }, r =>
        {
            if (r.Error != null) { Debug.LogWarning($"[AntiCheat] {function}: {r.Error.Message}"); onFail?.Invoke(); return; }
            onOk(r.FunctionResult);
        }, e =>
        {
            if (e.Error == PlayFabErrorCode.AccountBanned) { Kick("tamper"); return; }
            Debug.LogWarning($"[AntiCheat] {function}: {e.GenerateErrorReport()}");
            onFail?.Invoke();
        });
    }

    static T Parse<T>(object raw) where T : class
    {
        if (raw == null) return null;
        var json = PluginManager.GetPlugin<ISerializerPlugin>(PluginContract.PlayFab_Serializer).SerializeObject(raw);
        return JsonUtility.FromJson<T>(json);
    }

    static Dictionary<string, string> ParsePlayers(object raw)
    {
        var serializer = PluginManager.GetPlugin<ISerializerPlugin>(PluginContract.PlayFab_Serializer);
        var root = serializer.DeserializeObject<Dictionary<string, object>>(serializer.SerializeObject(raw));
        var result = new Dictionary<string, string>();
        if (root != null && root.TryGetValue("players", out var players) && players != null)
        {
            var map = serializer.DeserializeObject<Dictionary<string, string>>(serializer.SerializeObject(players));
            if (map != null) foreach (var kv in map) result[kv.Key] = kv.Value;
        }
        return result;
    }
}
