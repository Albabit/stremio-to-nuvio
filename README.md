# stremio-to-nuvio

**English** · [Français](README.fr.md)

Copy your **Stremio library into a Nuvio profile**: saved titles, watched movies and episodes, and your
"Continue Watching" positions. One Python file, no extra packages, works on Windows, macOS and Linux.

> Unofficial tool, not affiliated with Stremio or Nuvio. It only **adds** data to the Nuvio profile you name:
> nothing is ever deleted, in Stremio or in Nuvio.

## What gets copied

| From Stremio | To Nuvio |
|---|---|
| Titles in your library | Library › **Saved** |
| Watched movies | Watched marks |
| Watched episodes (decoded from Stremio's internal format) | Watched marks, episode by episode |
| Videos in progress (between 2 % and 92 %) | **Continue Watching** |

Not copied: TV channels and items coming from other add-ons that Nuvio cannot read (they are listed in the report).

Tested on two real libraries of 480 and 680 titles (5,400 watched marks in total).

## Before you start

- **Nuvio installed, with the target profile already created** (one profile per person).
- **Your Stremio account**: e-mail and password, or a Facebook / Apple account (see [Signing in to Stremio](#signing-in-to-stremio)).
- **Your Nuvio e-mail and password.**
- **Python 3.8 or newer** (see below).

### Install Python

<details>
<summary><b>Windows</b></summary>

1. Download Python from [python.org/downloads](https://www.python.org/downloads/), or install "Python 3" from the Microsoft Store.
2. With the python.org installer, tick **"Add python.exe to PATH"** on the first screen.
3. On Windows, the command is **`py`** (or `python`), not `python3`.

</details>

<details>
<summary><b>macOS</b></summary>

1. Open **Terminal** and type `python3 --version`. If macOS offers to install the developer tools, accept: Python comes with them.
2. Or download Python from [python.org/downloads](https://www.python.org/downloads/). In that case, also run
   **"Install Certificates.command"** (in Applications › Python 3.x), otherwise downloads fail with an SSL error.

</details>

<details>
<summary><b>Linux</b></summary>

Python 3 is usually already installed (`python3 --version`). Otherwise: `sudo apt install python3` (Debian, Ubuntu),
`sudo dnf install python3` (Fedora) or `sudo pacman -S python` (Arch).

</details>

### Download the tool and open a terminal in its folder

Download [`stremio_to_nuvio.py`](stremio_to_nuvio.py) (or **Code › Download ZIP**), put it in a folder, then open a terminal there:

- **Windows**: open the folder in File Explorer, type `cmd` in the address bar and press Enter.
- **macOS**: open Terminal, type `cd ` (with a space), drag the folder into the window, press Enter.
- **Linux**: right-click in the folder › "Open in Terminal", or `cd` to it.

## Usage

The commands below use `python3`. **On Windows, type `py` instead.**

**1. Export your Stremio library** (read-only: nothing changes in Stremio)

```
python3 stremio_to_nuvio.py export
```

Choose how you sign in to Stremio, then follow the instructions. This writes `stremio-library.json`.

**2. Prepare the import** (offline preview, nothing is sent)

```
python3 stremio_to_nuvio.py build
```

This writes the `out` folder and `out/report.md`: what will be sent, series that could not be decoded, items left out.
Read the report.

**3. Dry run**: signs in to Nuvio, lists your profiles and the counts, writes nothing

```
python3 stremio_to_nuvio.py push --profile "Your profile" --dry-run
```

**4. Send** to that profile, then type the profile name again to confirm

```
python3 stremio_to_nuvio.py push --profile "Your profile"
```

**5. Close and reopen Nuvio** on that profile: your library, watched marks and Continue Watching appear.

### Several people

Give each export its own file and folder, then send each one to its own profile:

```
python3 stremio_to_nuvio.py export --out stremio-library-anna.json
python3 stremio_to_nuvio.py build stremio-library-anna.json --out out-anna
python3 stremio_to_nuvio.py push --profile "Anna" --dir out-anna --dry-run
python3 stremio_to_nuvio.py push --profile "Anna" --dir out-anna
```

## Signing in to Stremio

`export` asks which method to use (or pass `--login password|link|authkey`):

| Method | For | How |
|---|---|---|
| **1. E-mail and password** | accounts with a Stremio password | type them in the terminal (the password stays hidden) |
| **2. Link (stremio.com)** | **Facebook, Apple** or any account | the tool shows a link that opens **stremio.com**, Stremio's website (its sign-in is separate from web.stremio.com). If that browser is already signed in on stremio.com, the page approves at once ("Remote login to new device succeeded") **with that account**. To choose the account, open the link in a private window and sign in. No password is typed in the terminal. |
| **3. Auth key** (advanced) | fallback | on [web.stremio.com](https://web.stremio.com), signed in, open the browser console (F12) and run `JSON.parse(localStorage.getItem("profile")).auth.key`, then paste the result |

## Safety

- **Passwords and session keys are never written to disk.**
- Stremio: methods 1 and 2 open a temporary session, closed at the end. A pasted key (method 3) is never closed,
  since it belongs to your browser.
- Nuvio: the tool signs in with your account, then closes **only its own session** at the end. Your apps stay signed in.
- Only **additive** Nuvio server functions are used (`sync_push_library_items`, `sync_push_watched_items`,
  `sync_push_watch_progress`). The function that replaces a whole library is never called.
- Titles, watched marks and positions **already in the profile are skipped**, so your existing data is never overwritten.
- `push` only writes to the profile you name, and asks you to type its name again.
- The exported files contain your personal library: **don't share them**, don't commit them (`.gitignore` excludes them).

## Known limitations

- **"Series watched" check on posters**: Nuvio computes it on each device, gradually, after the import (or right away when
  you open the series page). The episodes themselves are marked as soon as the import is done.
- **A few series may not be decoded** when their episode numbering changed since you watched them (listed in
  `report.md`): mark them by hand in Nuvio.
- If an episode is both watched and in progress, Nuvio keeps it as watched.
- To see the imported titles, keep **Nuvio** as the library source in Nuvio's settings (with Trakt as the source,
  Nuvio shows your Trakt watchlist instead).

## Troubleshooting

| Message | Fix |
|---|---|
| `python3: command not found` (Windows) | use `py` |
| SSL certificate error (macOS) | run "Install Certificates.command" in Applications › Python 3.x |
| "Profile not found" | use the exact profile name shown in the list (case doesn't matter) |
| The link was not opened in time | run `export` again and open the new link within 5 minutes |
| The wrong library was exported (method 2) | the browser was signed in on stremio.com with another account: open the link in a private window and sign in with the right one |
| Nuvio sign-in refused | use the e-mail and password of your Nuvio account |

## How it works

1. **export** reads the `libraryItem` collection of your Stremio account (`api.strem.io`).
2. **build** converts it. Watched episodes are stored by Stremio as a compressed bitfield indexed on the series'
   episode list. The tool rebuilds that list from public metadata (Cinemeta, Nuvio Catalog) and accepts a list only when
   your last watched episode sits exactly where Stremio recorded it. Otherwise it realigns like Stremio does, and only
   when every watched mark lands on an episode. `--source-file` adds your own metadata sources, tried first.
3. **push** finds the Nuvio server through its public discovery document (`/.well-known/nuvio`), signs in, and calls
   Nuvio's sync functions for the chosen profile. `--server` targets a self-hosted Nuvio server.

Options: `python3 stremio_to_nuvio.py <command> --help`. Messages follow your system language (English or French);
force one with `--lang en` or `--lang fr`.

## License

[MIT](LICENSE)
