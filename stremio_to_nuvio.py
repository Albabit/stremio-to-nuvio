#!/usr/bin/env python3
"""stremio-to-nuvio: copy your Stremio library into a Nuvio profile.

Three steps, one file, Python 3.8+ standard library only (Windows, macOS, Linux):

    python3 stremio_to_nuvio.py export                     # read your Stremio library (read-only)
    python3 stremio_to_nuvio.py build                      # prepare the import and a report (offline preview)
    python3 stremio_to_nuvio.py push --profile "Name" --dry-run
    python3 stremio_to_nuvio.py push --profile "Name"      # send to that Nuvio profile (additive only)

What is copied: saved titles (Nuvio library "Saved"), watched movies and episodes, and
playback positions (Continue Watching). Nothing is ever deleted, in Stremio or in Nuvio.

Unofficial tool, not affiliated with Stremio or Nuvio. See README.md.
"""
import argparse
import base64
import datetime as dt
import getpass
import json
import locale
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

__version__ = "1.0.1"
USER_AGENT = f"stremio-to-nuvio/{__version__}"
HERE = os.path.dirname(os.path.abspath(__file__))

STREMIO_API = "https://api.strem.io/api/"
STREMIO_LINK = "https://link.stremio.com/api/v2/"
NUVIO_DISCOVERY = "https://api.nuvio.tv/.well-known/nuvio"
META_SOURCES = {
    "Cinemeta": "https://v3-cinemeta.strem.io/meta/{type}/{id}.json",
    "Nuvio Catalog": "https://catalog.nuvio.tv/meta/{type}/{id}.json",
}
PROGRESS_MIN, PROGRESS_MAX = 0.02, 0.92
BATCH = {"library": 200, "watched": 500, "progress": 100}

# --------------------------------------------------------------------------- messages

MESSAGES = {
    "export_title": ("Stremio library export (read-only)", "Export de la bibliothèque Stremio (lecture seule)"),
    "login_menu": ("How do you sign in to Stremio?\n  1. E-mail and password\n  2. Facebook, Apple or any account: open a link (stremio.com)\n  3. Paste an auth key (advanced)",
                   "Comment vous connectez-vous à Stremio ?\n  1. E-mail et mot de passe\n  2. Facebook, Apple ou tout autre compte : ouvrir un lien (stremio.com)\n  3. Coller une clé de session (avancé)"),
    "login_choice": ("Your choice [1]: ", "Votre choix [1] : "),
    "email": ("Stremio e-mail: ", "E-mail Stremio : "),
    "password": ("Stremio password (hidden): ", "Mot de passe Stremio (invisible) : "),
    "login_refused": ("Sign-in refused: check the e-mail and password.", "Connexion refusée : vérifiez l'e-mail et le mot de passe."),
    "link_open": ("Open this link in a browser:\n  {link}\n  (or type the code {code} on link.stremio.com)\nIt opens stremio.com (Stremio's website, not web.stremio.com). If that browser is already signed in\non stremio.com, the page approves at once (\"Remote login to new device succeeded\") with THAT account.\nTo choose the account, open the link in a private window and sign in.\nWaiting (up to {minutes} min)...",
                  "Ouvrez ce lien dans un navigateur :\n  {link}\n  (ou saisissez le code {code} sur link.stremio.com)\nIl ouvre stremio.com (le site de Stremio, pas web.stremio.com). Si ce navigateur est déjà connecté\nà stremio.com, la page approuve tout de suite (« Remote login to new device succeeded ») avec CE compte.\nPour choisir le compte, ouvrez le lien dans une fenêtre de navigation privée et connectez-vous.\nEn attente (jusqu'à {minutes} min)..."),
    "link_timeout": ("The link was not opened in time. Run the command again.", "Le lien n'a pas été ouvert à temps. Relancez la commande."),
    "link_ok": ("Approved. Exporting the account that approved the link.", "Approuvé. Export du compte qui a approuvé le lien."),
    "authkey_help": ("On web.stremio.com, signed in, open the browser console (F12) and run:\n  JSON.parse(localStorage.getItem(\"profile\")).auth.key\nthen paste the result here.",
                     "Sur web.stremio.com, connecté, ouvrez la console du navigateur (F12) et lancez :\n  JSON.parse(localStorage.getItem(\"profile\")).auth.key\npuis collez le résultat ici."),
    "authkey": ("Auth key (hidden): ", "Clé de session (invisible) : "),
    "authkey_bad": ("This key was refused by Stremio.", "Cette clé a été refusée par Stremio."),
    "export_done": ("\n{total} items in the Stremio data\n  visible library: {visible} ({movies} movies, {series} series, {other} other)\n  with something watched: {watched}\n  in progress: {progress}\n\nFile written: {path}\nIt contains no password and no session key. Nothing was changed in Stremio.",
                    "\n{total} éléments dans les données Stremio\n  bibliothèque visible : {visible} ({movies} films, {series} séries, {other} autres)\n  avec quelque chose de vu : {watched}\n  en cours de lecture : {progress}\n\nFichier écrit : {path}\nIl ne contient ni mot de passe ni clé de session. Rien n'a été modifié dans Stremio."),
    "build_reading": ("Reading episode lists for {n} series (cached in {cache})...", "Lecture des listes d'épisodes de {n} séries (mises en cache dans {cache})..."),
    "build_done": ("\nPreview (nothing was sent):\n  library: {lib} titles ({movies} movies, {series} series)\n  watched movies: {wm}\n  watched episodes: {we} across {ns} series\n  playback positions: {pr}\n  series not decoded: {unres}\n  left out: {skip}\n\nFiles written in {out}\nRead {report} before sending.",
                   "\nAperçu (rien n'a été envoyé) :\n  bibliothèque : {lib} titres ({movies} films, {series} séries)\n  films vus : {wm}\n  épisodes vus : {we} sur {ns} séries\n  reprises de lecture : {pr}\n  séries non décodées : {unres}\n  laissés de côté : {skip}\n\nFichiers écrits dans {out}\nLisez {report} avant l'envoi."),
    "server": ("Nuvio server: {server}", "Serveur Nuvio : {server}"),
    "nuvio_email": ("Nuvio e-mail: ", "E-mail Nuvio : "),
    "nuvio_password": ("Nuvio password (hidden): ", "Mot de passe Nuvio (invisible) : "),
    "nuvio_refused": ("Sign-in refused: check the Nuvio e-mail and password.", "Connexion refusée : vérifiez l'e-mail et le mot de passe Nuvio."),
    "profiles": ("\nProfiles on this account:", "\nProfils du compte :"),
    "profile_missing": ("\nProfile \"{name}\" not found (or ambiguous). Nothing was sent.", "\nProfil « {name} » introuvable ou ambigu. Rien n'a été envoyé."),
    "push_plan": ("\nTarget profile: {name} (#{index})\n  already there: {l0} saved titles, {w0} watched, {p0} positions\n  already there, skipped: {ls} titles, {ws} watched, {ps} positions\n  to send: {l1} titles, {w1} watched, {p1} positions (add only: nothing is deleted or replaced)",
                  "\nProfil cible : {name} (n° {index})\n  déjà présent : {l0} titres enregistrés, {w0} « vu », {p0} reprises\n  déjà là, ignorés : {ls} titres, {ws} « vu », {ps} reprises\n  à envoyer : {l1} titres, {w1} « vu », {p1} reprises (ajout seulement : rien n'est supprimé ni remplacé)"),
    "dry_run": ("\nDry run: nothing was sent.", "\nSimulation : rien n'a été envoyé."),
    "confirm": ("\nTo confirm, type the profile name ({name}): ", "\nPour confirmer, tapez le nom du profil ({name}) : "),
    "confirm_bad": ("Different answer: nothing was sent.", "Réponse différente : rien n'a été envoyé."),
    "sent": ("  {kind}: {n}/{n} sent      ", "  {kind} : {n}/{n} envoyés      "),
    "push_done": ("\nNow in \"{name}\": {l} saved titles, {w} watched, {p} positions\nClose and reopen Nuvio on this profile to see the changes.",
                  "\nMaintenant dans « {name} » : {l} titres enregistrés, {w} « vu », {p} reprises\nFermez puis rouvrez Nuvio sur ce profil pour voir les changements."),
    "http_error": ("{service} answered {code}: {detail}", "{service} a répondu {code} : {detail}"),
    "net_error": ("Cannot reach {service} ({reason}).", "Impossible de joindre {service} ({reason})."),
    "ssl_hint": ("SSL certificate error. On macOS with the python.org installer, run \"Install Certificates.command\" (in Applications > Python 3.x), then try again.",
                 "Erreur de certificat SSL. Sur macOS avec Python de python.org, lancez « Install Certificates.command » (dans Applications > Python 3.x), puis réessayez."),
    "file_missing": ("File not found: {path}. Run the previous step first.", "Fichier introuvable : {path}. Lancez d'abord l'étape précédente."),
}
LANG = "en"


def detect_lang(forced=None):
    if forced in ("en", "fr"):
        return forced
    candidates = [os.environ.get(k, "") for k in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE")]
    try:
        candidates.append(locale.getlocale()[0] or "")
    except ValueError:
        pass
    return "fr" if any(c.lower().startswith(("fr", "french")) for c in candidates if c) else "en"


def t(key, **kw):
    en, fr = MESSAGES[key]
    return (fr if LANG == "fr" else en).format(**kw)


def die(message):
    print(message, file=sys.stderr)
    sys.exit(1)


# --------------------------------------------------------------------------- HTTP

def http(method, url, body=None, headers=None, service="server", tries=4, allow_errors=False):
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(tries):
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": "application/json", "User-Agent": USER_AGENT,
                                              **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                return json.loads(raw) if raw.strip() else None
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            if allow_errors:
                return {"_http_error": e.code, "_detail": detail}
            die(t("http_error", service=service, code=e.code, detail=detail))
        except urllib.error.URLError as e:
            if isinstance(e.reason, ssl.SSLError):
                die(t("ssl_hint"))
            if attempt < tries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            die(t("net_error", service=service, reason=e.reason))
        except (TimeoutError, ConnectionError) as e:
            if attempt < tries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            die(t("net_error", service=service, reason=e))


def stremio(method, payload):
    body = http("POST", STREMIO_API + method, payload, service="Stremio", allow_errors=True) or {}
    if body.get("_http_error") or body.get("error"):
        return None, body.get("error") or body.get("_detail")
    return body.get("result"), None


def ms(value, fallback=0):
    if value in (None, "", 0):
        return fallback
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)
    except ValueError:
        return fallback


def write_private_json(path, data):
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def read_json(path):
    if not os.path.exists(path):
        die(t("file_missing", path=path))
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- 1. export

def login_password():
    email = input(t("email")).strip()
    password = getpass.getpass(t("password"))
    result, _ = stremio("login", {"type": "Login", "email": email, "password": password, "facebook": False})
    if not result or not result.get("authKey"):
        die(t("login_refused"))
    return result["authKey"], True


def login_link(timeout_s):
    created = http("GET", STREMIO_LINK + "create?type=Create", service="Stremio") or {}
    res = created.get("result") or created
    code, link = res.get("code"), res.get("link")
    if not code:
        die(t("net_error", service="link.stremio.com", reason="no code"))
    print(t("link_open", link=link, code=code, minutes=max(1, timeout_s // 60)))
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(3)
        body = http("GET", STREMIO_LINK + "read?type=Read&code=" + urllib.parse.quote(code),
                    service="Stremio", allow_errors=True) or {}
        result = body.get("result") or {}
        key = result.get("authKey") if isinstance(result, dict) else None
        if key:
            print(t("link_ok"))
            return key, True
    die(t("link_timeout"))


def login_authkey():
    print(t("authkey_help"))
    key = getpass.getpass(t("authkey")).strip().strip('"')
    result, err = stremio("getUser", {"authKey": key})
    if err or not result:
        die(t("authkey_bad"))
    return key, False  # never sign out a session you pasted: it is your browser's session


def cmd_export(args):
    print(t("export_title") + "\n")
    method = args.login
    if not method:
        print(t("login_menu"))
        choice = input(t("login_choice")).strip() or "1"
        method = {"1": "password", "2": "link", "3": "authkey"}.get(choice, "password")
    if method == "link":
        auth_key, own_session = login_link(args.link_timeout)
    elif method == "authkey":
        auth_key, own_session = login_authkey()
    else:
        auth_key, own_session = login_password()
    try:
        items, err = stremio("datastoreGet", {"authKey": auth_key, "collection": "libraryItem", "ids": [], "all": True})
        if err is not None and items is None:
            die(t("http_error", service="Stremio", code="datastoreGet", detail=err))
        items = items or []
    finally:
        if own_session:
            stremio("logout", {"authKey": auth_key})  # closes only the temporary session opened above
        auth_key = None

    write_private_json(args.out, items)

    def st(i):
        return i.get("state") or {}

    visible = [i for i in items if not i.get("removed") and not i.get("temp")]
    movies = sum(1 for i in visible if i.get("type") == "movie")
    series = sum(1 for i in visible if i.get("type") == "series")
    watched = sum(1 for i in items if (st(i).get("timesWatched") or 0) > 0 or (st(i).get("flaggedWatched") or 0) > 0
                  or st(i).get("watched"))
    progress = sum(1 for i in items if (st(i).get("timeOffset") or 0) > 0 and not i.get("removed"))
    print(t("export_done", total=len(items), visible=len(visible), movies=movies, series=series,
            other=len(visible) - movies - series, watched=watched, progress=progress, path=os.path.abspath(args.out)))


# --------------------------------------------------------------------------- 2. build

class MetaCache:
    def __init__(self, folder, sources):
        self.folder, self.sources = folder, sources
        os.makedirs(folder, exist_ok=True)

    def videos(self, source, ctype, cid):
        safe = urllib.parse.quote(f"{source}_{ctype}_{cid}", safe="")
        path = os.path.join(self.folder, safe + ".json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        url = self.sources[source].format(type=ctype, id=urllib.parse.quote(cid, safe=":"))
        body = http("GET", url, service=source, allow_errors=True) or {}
        meta = {} if body.get("_http_error") else (body.get("meta") or {})
        vids = [{"id": v.get("id"), "season": v.get("season"), "episode": v.get("episode") or v.get("number")}
                for v in meta.get("videos") or [] if v.get("id")]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(vids, f)
        time.sleep(0.15)
        return vids


def decode_bitfield(serialized):
    """Stremio stores watched episodes as '<anchor video id>:<anchor length>:<base64(zlib(bits))>'."""
    parts = serialized.split(":")
    if len(parts) < 3:
        raise ValueError("unexpected format")
    anchor, anchor_len = ":".join(parts[:-2]), int(parts[-2])
    raw = zlib.decompress(base64.b64decode(parts[-1]))
    bits = {i for i in range(len(raw) * 8) if (raw[i // 8] >> (i % 8)) & 1}
    return anchor, anchor_len, bits


def candidate_lists(cache, cid):
    key = lambda v: ((v["season"] if v["season"] is not None else 0), v["episode"] or 0)
    for source in cache.sources:
        if source == "Cinemeta" and not cid.startswith("tt"):
            continue
        vids = cache.videos(source, "series", cid) or []
        if vids:
            yield source, "source order", vids
            yield source, "season/episode", sorted(vids, key=key)
            yield source, "specials last", sorted(vids, key=lambda v: (1 if (v["season"] or 0) == 0 else 0,) + key(v))


def resolve_series(cache, cid, serialized):
    """Map Stremio's bitfield onto an episode list.

    The bit order follows the episode list Stremio used. A list is accepted as is when the anchor
    (last watched episode) sits exactly where Stremio stored it. Otherwise the list changed since
    (episodes or specials added/removed): like Stremio, realign on the anchor, but only when every
    stored bit lands on an episode; prefer the list marking the fewest specials, then the smallest shift.
    """
    anchor, anchor_len, bits = decode_bitfield(serialized)
    realigned, anchor_seen = [], False
    for source, order, vids in candidate_lists(cache, cid):
        ids = [v["id"] for v in vids]
        if anchor not in ids:
            continue
        anchor_seen = True
        offset = anchor_len - ids.index(anchor) - 1
        episodes = [v for i, v in enumerate(vids) if (i + offset) in bits]
        if offset == 0:
            return (source, order, episodes, 0), None
        if len(episodes) == len(bits):
            specials = sum(1 for v in episodes if (v["season"] or 0) == 0)
            realigned.append((specials, abs(offset), (source, order, episodes, offset)))
    if realigned:
        realigned.sort(key=lambda r: (r[0], r[1]))
        return realigned[0][2], None
    if anchor_seen:
        return None, "episode numbering differs from Stremio's"
    return None, f"last watched episode ({anchor}) not found in metadata sources"


def cmd_build(args):
    items = read_json(args.input)
    sources = dict(META_SOURCES)
    if args.source_file:
        extra = {}
        with open(args.source_file, encoding="utf-8") as f:
            for line in f:
                if "|" in line:
                    name, template = line.strip().split("|", 1)
                    extra[name] = template
        sources = {**extra, **sources}
    cache = MetaCache(args.cache, sources)

    library, watched, progress, skipped, unresolved, decoded = [], [], [], [], [], []
    n_series = sum(1 for i in items if i.get("type") == "series" and (i.get("state") or {}).get("watched"))
    print(t("build_reading", n=n_series, cache=os.path.abspath(args.cache)))

    for it in items:
        cid, ctype, name = it.get("_id") or "", it.get("type"), it.get("name") or ""
        st = it.get("state") or {}
        visible = not it.get("removed") and not it.get("temp")
        if ctype not in ("movie", "series") or not (cid.startswith("tt") or cid.startswith("tmdb:")):
            if visible or st.get("watched") or (st.get("timesWatched") or 0) > 0:
                skipped.append((name, cid, ctype))
            continue
        last = ms(st.get("lastWatched"), ms(it.get("_mtime")))

        if visible:
            shape = (it.get("posterShape") or "poster").upper()
            library.append({
                "content_id": cid, "content_type": ctype, "name": name, "poster": it.get("poster") or None,
                "poster_shape": shape if shape in ("POSTER", "LANDSCAPE", "SQUARE") else "POSTER",
                "background": it.get("background") or None, "logo": it.get("logo") or None,
                "release_info": str(it.get("year")) if it.get("year") else None,
                "added_at": ms(it.get("_ctime"), last),
            })

        if ctype == "movie" and ((st.get("timesWatched") or 0) > 0 or (st.get("flaggedWatched") or 0) > 0):
            watched.append({"content_id": cid, "content_type": "movie", "title": name,
                            "season": None, "episode": None, "watched_at": last})

        if ctype == "series" and st.get("watched"):
            try:
                result, why = resolve_series(cache, cid, st["watched"])
            except (ValueError, zlib.error, base64.binascii.Error) as e:
                result, why = None, f"unreadable Stremio data ({e})"
            if result:
                source, order, episodes, offset = result
                for v in episodes:
                    if v["season"] is not None and v["episode"] is not None:
                        watched.append({"content_id": cid, "content_type": "series", "title": name,
                                        "season": int(v["season"]), "episode": int(v["episode"]), "watched_at": last})
                label = order if offset == 0 else f"{order}, realigned {offset:+d}"
                decoded.append((name, cid, len(episodes), source, label))
            else:
                unresolved.append((name, cid, why))

        offset_ms, duration = st.get("timeOffset") or 0, st.get("duration") or 0
        if offset_ms > 0 and duration > 0 and not it.get("removed") and PROGRESS_MIN < offset_ms / duration < PROGRESS_MAX:
            vid, season, episode = st.get("video_id") or cid, None, None
            if ctype == "series":
                bits = vid.split(":")
                if len(bits) >= 3 and bits[-1].isdigit() and bits[-2].isdigit():
                    season, episode = int(bits[-2]), int(bits[-1])
            progress.append({"content_id": cid, "content_type": ctype, "video_id": vid, "season": season,
                             "episode": episode, "position": int(offset_ms), "duration": int(duration),
                             "last_watched": last, "_name": name})

    os.makedirs(args.out, exist_ok=True)
    write_private_json(os.path.join(args.out, "nuvio-library.json"), library)
    write_private_json(os.path.join(args.out, "nuvio-watched.json"), watched)
    write_private_json(os.path.join(args.out, "nuvio-progress.json"),
                       [{k: v for k, v in p.items() if not k.startswith("_")} for p in progress])

    n_eps = sum(1 for w in watched if w["content_type"] == "series")
    lines = ["# Stremio → Nuvio: preview (nothing was sent)", "",
             f"- Library (Saved): **{len(library)}** titles",
             f"- Watched movies: **{sum(1 for w in watched if w['content_type'] == 'movie')}**",
             f"- Watched episodes: **{n_eps}** across {len(decoded)} series",
             f"- Playback positions: **{len(progress)}**", "",
             f"## Series not decoded ({len(unresolved)}): mark them by hand in Nuvio", ""]
    lines += [f"- {n} (`{c}`): {w}" for n, c, w in sorted(unresolved)] or ["None."]
    lines += ["", f"## Left out ({len(skipped)}): not readable by Nuvio (TV channels, other add-ons' ids)", ""]
    lines += [f"- {n or '(no name)'} (`{c}`, {ty})" for n, c, ty in sorted(skipped, key=lambda x: x[0] or "")] or ["None."]
    lines += ["", "## Playback positions", ""]
    lines += [f"- {p['_name']}: {p['video_id']}, {round(100 * p['position'] / p['duration'])} %" for p in progress] or ["None."]
    lines += ["", "## Decoded series (episode list used)", ""]
    lines += [f"- {n} (`{c}`): {k} episodes ({s}, {o})" for n, c, k, s, o in sorted(decoded)]
    report = os.path.join(args.out, "report.md")
    with open(report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(t("build_done", lib=len(library), movies=sum(1 for x in library if x["content_type"] == "movie"),
            series=sum(1 for x in library if x["content_type"] == "series"),
            wm=sum(1 for w in watched if w["content_type"] == "movie"), we=n_eps, ns=len(decoded),
            pr=len(progress), unres=len(unresolved), skip=len(skipped), out=os.path.abspath(args.out),
            report=os.path.abspath(report)))


# --------------------------------------------------------------------------- 3. push

class Nuvio:
    def __init__(self, discovery_url):
        doc = http("GET", discovery_url, service="Nuvio") or {}
        self.base = (doc.get("backend_url") or "").rstrip("/")
        self.key = doc.get("publishable_key") or ""
        if not self.base or not self.key:
            die(t("net_error", service="Nuvio", reason="invalid discovery document"))
        self.token = None

    def headers(self):
        h = {"apikey": self.key}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def sign_in(self, email, password):
        res = http("POST", f"{self.base}/auth/v1/token?grant_type=password", {"email": email, "password": password},
                   self.headers(), service="Nuvio", tries=1, allow_errors=True) or {}
        self.token = res.get("access_token")
        if not self.token:
            die(t("nuvio_refused"))

    def sign_out(self):
        # scope=local closes ONLY this session. Without it the server defaults to scope=global
        # and would sign the account out on every device.
        if self.token:
            http("POST", f"{self.base}/auth/v1/logout?scope=local", {}, self.headers(), service="Nuvio",
                 tries=1, allow_errors=True)
            self.token = None

    def rpc(self, name, params):
        return http("POST", f"{self.base}/rest/v1/rpc/{name}", params, self.headers(), service="Nuvio")

    def existing(self, profile):
        library, offset = set(), 0
        while True:
            rows = self.rpc("sync_pull_library", {"p_profile_id": profile, "p_limit": 500, "p_offset": offset}) or []
            library |= {(r["content_id"], r["content_type"]) for r in rows}
            if len(rows) < 500:
                break
            offset += 500
        watched, page = set(), 1
        while True:  # the server returns at most 1000 rows per request
            rows = self.rpc("sync_pull_watched_items", {"p_profile_id": profile, "p_page": page, "p_page_size": 1000}) or []
            watched |= {(r["content_id"], r.get("season"), r.get("episode")) for r in rows}
            if len(rows) < 1000:
                break
            page += 1
        progress = {r["progress_key"] for r in self.rpc("sync_pull_watch_progress", {"p_profile_id": profile}) or []}
        return {"library": library, "watched": watched, "progress": progress}


def key_of(kind, item):
    if kind == "library":
        return (item["content_id"], item["content_type"])
    if kind == "watched":
        return (item["content_id"], item.get("season"), item.get("episode"))
    if item.get("season") is not None and item.get("episode") is not None:
        return f"{item['content_id']}_s{item['season']}e{item['episode']}"
    return item["content_id"]


def discovery_url(server):
    if not server:
        return NUVIO_DISCOVERY
    server = server.strip().rstrip("/")
    if "://" not in server:
        server = "https://" + server
    return server if server.endswith("/.well-known/nuvio") else server + "/.well-known/nuvio"


def cmd_push(args):
    payloads = {kind: read_json(os.path.join(args.dir, f"nuvio-{kind}.json")) for kind in ("library", "watched", "progress")}
    nuvio = Nuvio(discovery_url(args.server))
    print(t("server", server=nuvio.base) + "\n")
    email = input(t("nuvio_email")).strip()
    password = getpass.getpass(t("nuvio_password"))
    nuvio.sign_in(email, password)
    password = None
    try:
        profiles = nuvio.rpc("sync_pull_profiles", {}) or []
        print(t("profiles"))
        for p in profiles:
            print(f"  {p['profile_index']}. {p['name']}")
        target = [p for p in profiles if p["name"].strip().casefold() == args.profile.strip().casefold()]
        if len(target) != 1:
            die(t("profile_missing", name=args.profile))
        index, name = target[0]["profile_index"], target[0]["name"]

        before = nuvio.existing(index)
        todo = {kind: [it for it in items if key_of(kind, it) not in before[kind]] for kind, items in payloads.items()}
        print(t("push_plan", name=name, index=index,
                l0=len(before["library"]), w0=len(before["watched"]), p0=len(before["progress"]),
                ls=len(payloads["library"]) - len(todo["library"]), ws=len(payloads["watched"]) - len(todo["watched"]),
                ps=len(payloads["progress"]) - len(todo["progress"]),
                l1=len(todo["library"]), w1=len(todo["watched"]), p1=len(todo["progress"])))
        if args.dry_run:
            print(t("dry_run"))
            return
        if input(t("confirm", name=name)).strip().casefold() != name.strip().casefold():
            die(t("confirm_bad"))

        # Additive server functions only. sync_push_library (which REPLACES the whole library) is never used.
        for kind, fn, param in (("library", "sync_push_library_items", "p_items"),
                                ("watched", "sync_push_watched_items", "p_items"),
                                ("progress", "sync_push_watch_progress", "p_entries")):
            items, size = todo[kind], BATCH[kind]
            for start in range(0, len(items), size):
                nuvio.rpc(fn, {param: items[start:start + size], "p_profile_id": index})
                print(f"  {kind}: {min(start + size, len(items))}/{len(items)}", end="\r", flush=True)
                time.sleep(0.3)
            print(t("sent", kind=kind, n=len(items)))

        after = nuvio.existing(index)
        print(t("push_done", name=name, l=len(after["library"]), w=len(after["watched"]), p=len(after["progress"])))
    finally:
        nuvio.sign_out()


# --------------------------------------------------------------------------- main

def main():
    global LANG
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # old Windows consoles: never crash on a character
        except AttributeError:
            pass

    parser = argparse.ArgumentParser(prog="stremio_to_nuvio.py",
                                     description="Copy your Stremio library into a Nuvio profile (unofficial).")
    parser.add_argument("--lang", choices=("en", "fr"), help="messages language (default: from the system)")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("export", help="1. read your Stremio library into a local file (read-only)")
    p.add_argument("--out", default="stremio-library.json", help="output file (default: stremio-library.json)")
    p.add_argument("--login", choices=("password", "link", "authkey"),
                   help="password, link (Facebook/Apple/any account: open a link on stremio.com) or authkey")
    p.add_argument("--link-timeout", type=int, default=300, help="seconds to wait for the code approval (default 300)")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("build", help="2. prepare the import and a report, offline preview")
    p.add_argument("input", nargs="?", default="stremio-library.json", help="export file (default: stremio-library.json)")
    p.add_argument("--out", default="out", help="output folder (default: out)")
    p.add_argument("--cache", default=".meta-cache", help="metadata cache folder (default: .meta-cache)")
    p.add_argument("--source-file", help="extra metadata sources tried first, one per line: Name|https://…/meta/{type}/{id}.json")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("push", help="3. send to ONE Nuvio profile (additive only)")
    p.add_argument("--profile", required=True, help="exact name of the target Nuvio profile")
    p.add_argument("--dir", default="out", help="folder made by build (default: out)")
    p.add_argument("--dry-run", action="store_true", help="sign in and count, write nothing")
    p.add_argument("--server", help="self-hosted Nuvio server (domain or discovery URL); default: official Nuvio")
    p.set_defaults(func=cmd_push)

    args = parser.parse_args()
    LANG = detect_lang(args.lang)
    try:
        args.func(args)
    except KeyboardInterrupt:
        die("\nInterrupted." if LANG == "en" else "\nInterrompu.")


if __name__ == "__main__":
    main()
