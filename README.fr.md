# stremio-to-nuvio

[English](README.md) · **Français**

Copiez votre **bibliothèque Stremio dans un profil Nuvio** : titres enregistrés, films et épisodes vus, et reprises de
lecture (« Continuer à regarder »). Un seul fichier Python, sans module à installer, sous Windows, macOS et Linux.

> Outil non officiel, sans lien avec Stremio ni Nuvio. Il ne fait qu'**ajouter** des données au profil Nuvio que vous
> nommez : rien n'est jamais supprimé, ni dans Stremio, ni dans Nuvio.

**[⬇ Télécharger stremio_to_nuvio.py](https://github.com/Albabit/stremio-to-nuvio/releases/latest/download/stremio_to_nuvio.py)** (dernière version) · [Notes de version](https://github.com/Albabit/stremio-to-nuvio/releases/latest)

## Ce qui est copié

| Depuis Stremio | Vers Nuvio |
|---|---|
| Titres de votre bibliothèque | Bibliothèque › **Enregistrés** |
| Films vus | Coches « vu » |
| Épisodes vus (décodés depuis le format interne de Stremio) | Coches « vu », épisode par épisode |
| Vidéos en cours (entre 2 % et 92 %) | **Continuer à regarder** |

Non copiés : les chaînes TV et les éléments venus d'autres addons que Nuvio ne sait pas lire (listés dans le rapport).

Testé sur deux vraies bibliothèques de 480 et 680 titres (5 400 coches « vu » au total).

## Avant de commencer

- **Nuvio installé, avec le profil cible déjà créé** (un profil par personne).
- **Votre compte Stremio** : e-mail et mot de passe, ou compte Facebook / Apple (voir [Se connecter à Stremio](#se-connecter-à-stremio)).
- **L'e-mail et le mot de passe de votre compte Nuvio.**
- **Python 3.8 ou plus récent** (voir ci-dessous).

### Installer Python

<details>
<summary><b>Windows</b></summary>

1. Téléchargez Python sur [python.org/downloads](https://www.python.org/downloads/), ou installez « Python 3 » depuis le Microsoft Store.
2. Avec l'installeur de python.org, cochez **« Add python.exe to PATH »** sur le premier écran.
3. Sous Windows, la commande est **`py`** (ou `python`), et non `python3`.

</details>

<details>
<summary><b>macOS</b></summary>

1. Ouvrez le **Terminal** et tapez `python3 --version`. Si macOS propose d'installer les outils de développement, acceptez : Python est fourni avec.
2. Ou téléchargez Python sur [python.org/downloads](https://www.python.org/downloads/). Dans ce cas, lancez aussi
   **« Install Certificates.command »** (dans Applications › Python 3.x), sinon les téléchargements échouent avec une erreur SSL.

</details>

<details>
<summary><b>Linux</b></summary>

Python 3 est en général déjà installé (`python3 --version`). Sinon : `sudo apt install python3` (Debian, Ubuntu),
`sudo dnf install python3` (Fedora) ou `sudo pacman -S python` (Arch).

</details>

### Télécharger l'outil et ouvrir un terminal dans son dossier

Téléchargez [`stremio_to_nuvio.py`](https://github.com/Albabit/stremio-to-nuvio/releases/latest/download/stremio_to_nuvio.py) (dernière version), placez-le dans un dossier, puis ouvrez un terminal dans ce dossier :

- **Windows** : ouvrez le dossier dans l'Explorateur, tapez `cmd` dans la barre d'adresse, puis Entrée.
- **macOS** : ouvrez le Terminal, tapez `cd ` (avec une espace), glissez le dossier dans la fenêtre, puis Entrée.
- **Linux** : clic droit dans le dossier › « Ouvrir dans un terminal », ou `cd` vers ce dossier.

## Utilisation

Les commandes ci-dessous utilisent `python3`. **Sous Windows, tapez `py` à la place.**

**1. Exportez votre bibliothèque Stremio** (lecture seule : rien ne change dans Stremio)

```
python3 stremio_to_nuvio.py export
```

Choisissez votre façon de vous connecter à Stremio, puis suivez les instructions. Le fichier `stremio-library.json` est créé.

**2. Préparez l'import** (aperçu hors ligne, rien n'est envoyé)

```
python3 stremio_to_nuvio.py build
```

Le dossier `out` et le rapport `out/report.md` sont créés : ce qui sera envoyé, les séries non décodées, les éléments
laissés de côté. Lisez le rapport.

**3. Simulation** : connexion à Nuvio, liste des profils et quantités, sans rien écrire

```
python3 stremio_to_nuvio.py push --profile "Votre profil" --dry-run
```

**4. Envoi** vers ce profil, puis retapez le nom du profil pour confirmer

```
python3 stremio_to_nuvio.py push --profile "Votre profil"
```

**5. Fermez puis rouvrez Nuvio** sur ce profil : bibliothèque, coches « vu » et « Continuer à regarder » apparaissent.

### Plusieurs personnes

Donnez à chaque export son propre fichier et son propre dossier, puis envoyez chacun vers son profil :

```
python3 stremio_to_nuvio.py export --out stremio-library-anna.json
python3 stremio_to_nuvio.py build stremio-library-anna.json --out out-anna
python3 stremio_to_nuvio.py push --profile "Anna" --dir out-anna --dry-run
python3 stremio_to_nuvio.py push --profile "Anna" --dir out-anna
```

### Importé avec la version 1.0.0 ou 1.0.1 ?

Avec Python 3.10 ou plus ancien, ces versions lisaient mal certaines dates de Stremio : une partie des titres, coches
« vu » et reprises ont été envoyés datés du **1ᵉʳ janvier 1970** (les coches elles-mêmes sont bonnes, mais le tri par
date et l'historique sont faussés). La version 1.0.2 corrige cela. Pour réparer un profil déjà importé, lancez ceci avec
le même fichier d'export :

```
python3 stremio_to_nuvio.py fix-dates stremio-library.json --profile "Votre profil" --dry-run
python3 stremio_to_nuvio.py fix-dates stremio-library.json --profile "Votre profil"
```

Seules les dates mal envoyées par l'outil sont modifiées : ce que vous avez changé dans Nuvio depuis n'est pas touché.
Avec Python 3.11 ou plus récent, il n'y a rien à réparer (l'outil le dit).

## Se connecter à Stremio

`export` demande la méthode à utiliser (ou passez `--login password|link|authkey`) :

| Méthode | Pour | Comment |
|---|---|---|
| **1. E-mail et mot de passe** | comptes avec un mot de passe Stremio | saisis dans le terminal (le mot de passe reste invisible) |
| **2. Lien (stremio.com)** | **Facebook, Apple** ou tout autre compte | l'outil affiche un lien qui ouvre **stremio.com**, le site de Stremio (sa connexion est distincte de celle de web.stremio.com). Si ce navigateur est déjà connecté à stremio.com, la page approuve tout de suite (« Remote login to new device succeeded ») **avec ce compte**. Pour choisir le compte, ouvrez le lien dans une fenêtre de navigation privée et connectez-vous. Aucun mot de passe à saisir dans le terminal. |
| **3. Clé de session** (avancé) | solution de secours | sur [web.stremio.com](https://web.stremio.com), connecté, ouvrez la console du navigateur (F12), lancez `JSON.parse(localStorage.getItem("profile")).auth.key`, puis collez le résultat |

## Sécurité

- **Les mots de passe et clés de session ne sont jamais écrits sur le disque.**
- Stremio : les méthodes 1 et 2 ouvrent une session temporaire, fermée à la fin. Une clé collée (méthode 3) n'est
  jamais fermée, puisqu'elle appartient à votre navigateur.
- Nuvio : l'outil se connecte avec votre compte, puis ne ferme **que sa propre session** à la fin. Vos apps restent connectées.
- Seules des fonctions **d'ajout** du serveur Nuvio sont utilisées (`sync_push_library_items`, `sync_push_watched_items`,
  `sync_push_watch_progress`). La fonction qui remplace toute une bibliothèque n'est jamais appelée.
- Les titres, coches et reprises **déjà présents dans le profil sont ignorés** : vos données existantes ne sont jamais remplacées.
- `push` n'écrit que dans le profil nommé, et demande de retaper son nom.
- Les fichiers exportés contiennent votre bibliothèque personnelle : **ne les partagez pas** et ne les publiez pas (le `.gitignore` les exclut).

## Limites connues

- **Coche « série vue » sur les affiches** : Nuvio la calcule sur chaque appareil, petit à petit après l'import (ou tout
  de suite quand vous ouvrez la fiche de la série). Les épisodes, eux, sont cochés dès la fin de l'import.
- **Quelques séries peuvent ne pas être décodées** si leur numérotation a changé depuis (listées dans `report.md`) :
  cochez-les à la main dans Nuvio.
- Un épisode à la fois vu et en cours reste « vu » dans Nuvio.
- Pour voir les titres importés, gardez **Nuvio** comme source de la bibliothèque dans les réglages de Nuvio (avec Trakt
  comme source, Nuvio affiche votre liste de suivi Trakt à la place).

## En cas de problème

| Message | Solution |
|---|---|
| `python3` introuvable (Windows) | utilisez `py` |
| Erreur de certificat SSL (macOS) | lancez « Install Certificates.command » dans Applications › Python 3.x |
| « Profil introuvable » | utilisez le nom exact affiché dans la liste (majuscules indifférentes) |
| Le lien n'a pas été ouvert à temps | relancez `export` et ouvrez le nouveau lien dans les 5 minutes |
| Ce n'est pas la bonne bibliothèque (méthode 2) | le navigateur était connecté à stremio.com avec un autre compte : ouvrez le lien dans une fenêtre de navigation privée et connectez-vous avec le bon |
| Connexion Nuvio refusée | utilisez l'e-mail et le mot de passe de votre compte Nuvio |

## Fonctionnement

1. **export** lit la collection `libraryItem` de votre compte Stremio (`api.strem.io`).
2. **build** la convertit. Stremio stocke les épisodes vus sous forme de cases compressées, rangées selon la liste des
   épisodes de la série. L'outil reconstitue cette liste depuis des métadonnées publiques (Cinemeta, Nuvio Catalog) et
   ne l'accepte que si votre dernier épisode vu tombe exactement là où Stremio l'a enregistré. Sinon, il réaligne comme
   le fait Stremio, et seulement si chaque case tombe sur un épisode. `--source-file` ajoute vos propres sources,
   essayées en premier.
3. **push** trouve le serveur Nuvio grâce à son document de découverte public (`/.well-known/nuvio`), se connecte, puis
   appelle les fonctions de synchronisation de Nuvio pour le profil choisi. `--server` vise un serveur Nuvio auto-hébergé.

Options : `python3 stremio_to_nuvio.py <commande> --help`. Les messages suivent la langue du système (français ou
anglais) ; forcez-la avec `--lang fr` ou `--lang en`.

## Licence

[MIT](LICENSE)
