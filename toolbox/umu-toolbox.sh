#!/bin/bash
set -u

TOOLBOX_VERSION="0.5.2b"
ROOT="/userdata/system/umu/toolbox"
OVERLAY="$ROOT/overlay"
CUSTOM_DIR="/userdata/system/wine/custom"
UMU_DIR="/userdata/system/umu"
UMU_RUN="$UMU_DIR/umu-run"
UMU_BACKUP="$UMU_DIR/backups"
LOG_DIR="/userdata/system/logs/umu-toolbox"
PORTS="/userdata/roms/ports"
RUNNER_STAGING_ROOT="$ROOT/staging"

GE_REPO="GloriousEggroll/proton-ge-custom"
UMU_REPO="Open-Wine-Components/umu-launcher"

mkdir -p "$CUSTOM_DIR" "$UMU_DIR" "$UMU_BACKUP" "$LOG_DIR" "$RUNNER_STAGING_ROOT"

LOG="$LOG_DIR/toolbox-$(date '+%Y%m%d-%H%M%S').log"
touch "$LOG"

log() {
    printf '%s\n' "$*" >> "$LOG"
}

pause() {
    printf '\nAppuyez sur Entree pour continuer...'
    read -r _
}

msg() {
    local title="$1"
    local text="$2"
    if command -v dialog >/dev/null 2>&1; then
        dialog --title "$title" --msgbox "$text" 22 92
    else
        clear
        echo "==== $title ===="
        echo
        printf '%b\n' "$text"
        pause
    fi
}

yesno() {
    local title="$1"
    local text="$2"
    if command -v dialog >/dev/null 2>&1; then
        dialog --title "$title" --yesno "$text" 20 92
        return $?
    fi
    clear
    echo "==== $title ===="
    echo
    printf '%b\n' "$text"
    echo
    printf "Continuer ? [y/N] "
    read -r ans
    case "$ans" in y|Y|o|O|oui|OUI|yes|YES) return 0 ;; *) return 1 ;; esac
}

menu_choice() {
    local title="$1"
    shift
    if command -v dialog >/dev/null 2>&1; then
        dialog --stdout --title "$title" --menu "Choisissez une action :" 26 96 15 "$@"
    else
        clear
        echo "==== $title ===="
        echo
        local args=("$@")
        local i=0
        while [ "$i" -lt "${#args[@]}" ]; do
            printf "%s) %s\n" "${args[$i]}" "${args[$((i+1))]}"
            i=$((i+2))
        done
        echo
        printf "Choix : "
        read -r choice
        printf '%s' "$choice"
    fi
}

input_box() {
    local title="$1"
    local prompt="$2"
    local initial="${3-}"
    if command -v dialog >/dev/null 2>&1; then
        dialog --stdout --title "$title" --inputbox "$prompt" 12 90 "$initial"
    else
        clear
        echo "==== $title ===="
        echo
        echo "$prompt"
        printf "> "
        read -r value
        printf '%s' "${value:-$initial}"
    fi
}

require_net() {
    if ! curl -fsS --connect-timeout 8 https://api.github.com/ >/dev/null 2>&1; then
        msg "Connexion requise" "Impossible de joindre GitHub.\n\nVerifiez que Batocera est connecte a Internet."
        return 1
    fi
    return 0
}

root_bridge() {
    printf '%s' "$OVERLAY/umu-batocera/umu-root-runner.py"
}

umu_version() {
    if [ ! -s "$UMU_RUN" ]; then
        printf 'non installe'
        return
    fi
    python3 "$(root_bridge)" "$UMU_RUN" --version 2>/dev/null | head -n1 | sed 's/^umu-launcher version //' || printf 'inconnue'
}

installed_runners() {
    find "$CUSTOM_DIR" -mindepth 1 -maxdepth 1 -type d -name 'GE-Proton*-UMU' -printf '%f\n' 2>/dev/null | sort -V
}


runner_info_dir() {
    printf '%s' "$1/umu-batocera"
}

runner_manifest_path() {
    printf '%s' "$(runner_info_dir "$1")/integrity.sha256"
}

runner_state_path() {
    printf '%s' "$(runner_info_dir "$1")/runner-info"
}

manifest_files() {
    local r="$1"
    local p
    for p in \
        proton \
        bin/wine \
        bin/wine64 \
        bin/wineserver \
        umu-batocera/umu-root-runner.py \
        files/bin/wine \
        files/bin/wineserver \
        files/lib/wine/x86_64-unix/ntdll.so \
        files/lib/wine/x86_64-unix/win32u.so \
        files/lib/wine/i386-unix/ntdll.so \
        files/lib/wine/i386-unix/win32u.so \
        files/lib/wine/x86_64-windows/ntdll.dll \
        files/lib/wine/x86_64-windows/win32u.dll \
        files/lib/wine/x86_64-windows/shell32.dll \
        files/lib/wine/x86_64-windows/kernel32.dll \
        files/lib/wine/x86_64-windows/advapi32.dll \
        files/lib/wine/x86_64-windows/combase.dll \
        files/lib/wine/x86_64-windows/dinput8.dll \
        files/lib/wine/i386-windows/ntdll.dll \
        files/lib/wine/i386-windows/win32u.dll \
        files/lib/wine/i386-windows/shell32.dll \
        files/lib/wine/i386-windows/kernel32.dll \
        files/lib/wine/i386-windows/advapi32.dll \
        files/lib/wine/i386-windows/combase.dll \
        files/lib/wine/i386-windows/dinput8.dll
    do
        [ -f "$r/$p" ] && printf '%s\n' "$p"
    done
}

write_manifest() {
    local r="$1"
    local m
    m="$(runner_manifest_path "$r")"
    mkdir -p "$(dirname "$m")"
    : > "$m"
    while IFS= read -r p; do
        [ -n "$p" ] || continue
        (cd "$r" && sha256sum "$p") >> "$m" || return 1
    done <<< "$(manifest_files "$r")"
    [ -s "$m" ]
}

verify_runner_manifest() {
    local r="$1"
    local m
    m="$(runner_manifest_path "$r")"
    if [ ! -s "$m" ]; then
        return 2
    fi
    (cd "$r" && sha256sum -c "$(realpath "$m" 2>/dev/null || printf '%s' "$m")" >/dev/null 2>&1)
}

runner_integrity_label() {
    local r="$1"
    if [ ! -s "$(runner_manifest_path "$r")" ]; then
        printf 'NON MANAGE'
        return
    fi
    if verify_runner_manifest "$r"; then
        printf 'PROTEGE / OK'
    else
        printf 'MODIFIE'
    fi
}

protect_runner() {
    local runners choice r state
    runners="$(installed_runners)"
    if [ -z "$runners" ]; then
        msg "Creer une reference" "Aucun runner GE-Proton-UMU installe."
        return
    fi

    local opts=()
    while IFS= read -r r; do
        [ -n "$r" ] || continue
        state="$(runner_integrity_label "$CUSTOM_DIR/$r")"
        opts+=("$r" "$state")
    done <<< "$runners"

    if command -v dialog >/dev/null 2>&1; then
        choice="$(dialog --stdout --title "Creer une reference d'integrite" \
            --menu "v0.4 : une reference existante n'est JAMAIS remplacee." \
            22 90 14 "${opts[@]}")" || return
    else
        clear; printf '%s\n' "$runners"; echo; printf "Runner : "; read -r choice
    fi
    [ -n "$choice" ] || return
    r="$CUSTOM_DIR/$choice"

    if [ -s "$(runner_manifest_path "$r")" ]; then
        msg "Reference verrouillee" \
"$choice possede deja une empreinte d'integrite.

La v0.4 refuse de la recalculer afin qu'un runner contamine ne puisse jamais devenir la nouvelle reference saine.

Si ce runner est MODIFIE, archivez-le puis reinstallez une copie propre."
        return
    fi

    if ! write_manifest "$r"; then
        msg "Erreur" "Impossible de creer le manifest d'integrite de $choice."
        return
    fi
    mkdir -p "$(runner_info_dir "$r")"
    cat > "$(runner_state_path "$r")" <<EOF
GE_PROTON=${choice%-UMU}
UMU_INTEGRATION=3.7.1
TOOLBOX_VERSION=$TOOLBOX_VERSION
STATUS=validated
VALIDATED_AT=$(date -Is 2>/dev/null || date)
EOF
    msg "Reference creee" "$choice est maintenant reference. Cette empreinte ne sera plus remplacee par la Toolbox."
}


show_status() {
    local uv runtime runners
    uv="$(umu_version)"
    if [ -d "$UMU_DIR/home/.local/share/umu/steamrt4" ]; then
        runtime="present"
    else
        runtime="absent (sera telecharge par UMU au besoin)"
    fi
    runners=""
    local rr
    while IFS= read -r rr; do
        [ -n "$rr" ] || continue
        runners="${runners}${rr}  [$(runner_integrity_label "$CUSTOM_DIR/$rr")]\n"
    done <<< "$(installed_runners)"
    [ -n "$runners" ] || runners="(aucun)"

    msg "Etat de l'installation" \
"Toolbox : v$TOOLBOX_VERSION
Couche Batocera UMU : v3.7.1

UMU : $uv
steamrt4 : $runtime

Runners UMU installes :
$runners

PROTEGE / OK : empreinte valide
MODIFIE : fichiers critiques differents
NON MANAGE : aucune reference encore creee

Logs Toolbox :
$LOG_DIR"
}

fetch_latest_umu_json() {
    curl -fsSL --max-time 20 "https://api.github.com/repos/$UMU_REPO/releases/latest"
}

update_umu() {
    require_net || return

    clear
    echo "Recherche de la derniere version UMU..."
    log "UMU update started"

    local json tag asset checksum tmp oldver
    tmp="$(mktemp -d)"
    json="$tmp/release.json"

    if ! fetch_latest_umu_json > "$json"; then
        rm -rf "$tmp"
        msg "Erreur UMU" "Impossible de recuperer les informations de release UMU."
        return
    fi

    tag="$(python3 - "$json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
print(d.get("tag_name",""))
PY
)"
    asset="$(python3 - "$json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
for a in d.get("assets",[]):
    u=a.get("browser_download_url","")
    if u.endswith("zipapp.tar"):
        print(u); break
PY
)"
    checksum="$(python3 - "$json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
for a in d.get("assets",[]):
    u=a.get("browser_download_url","")
    if u.endswith("umu-run.sha512sum"):
        print(u); break
PY
)"

    if [ -z "$tag" ] || [ -z "$asset" ]; then
        rm -rf "$tmp"
        msg "Erreur UMU" "Release UMU invalide ou asset zipapp introuvable."
        return
    fi

    oldver="$(umu_version)"
    if printf '%s' "$oldver" | grep -q "^$tag"; then
        rm -rf "$tmp"
        msg "UMU" "UMU $tag est deja installe."
        return
    fi

    if ! yesno "Mise a jour UMU" \
"Version installee : $oldver
Derniere version : $tag

L'ancien umu-run sera sauvegarde.
steamrt4, les saves et les prefixes ne seront pas supprimes.

Installer UMU $tag ?"; then
        rm -rf "$tmp"
        return
    fi

    clear
    echo "Telechargement UMU $tag..."
    if ! curl -fL --progress-bar "$asset" -o "$tmp/umu-launcher.tar"; then
        rm -rf "$tmp"
        msg "Erreur UMU" "Echec du telechargement."
        return
    fi

    mkdir -p "$tmp/extracted"
    if ! tar -xf "$tmp/umu-launcher.tar" -C "$tmp/extracted"; then
        rm -rf "$tmp"
        msg "Erreur UMU" "Impossible d'extraire l'archive."
        return
    fi

    local newrun
    newrun="$(find "$tmp/extracted" -type f -name umu-run | head -n1)"
    if [ -z "$newrun" ] || [ ! -s "$newrun" ]; then
        rm -rf "$tmp"
        msg "Erreur UMU" "umu-run est absent de l'archive."
        return
    fi

    if [ -n "$checksum" ]; then
        echo "Verification SHA512..."
        if ! curl -fsSL "$checksum" -o "$tmp/umu-run.sha512sum"; then
            rm -rf "$tmp"
            msg "Erreur UMU" "Impossible de telecharger le checksum."
            return
        fi
        # The upstream checksum is for a file named umu-run.
        cp "$newrun" "$tmp/umu-run"
        if ! (cd "$tmp" && sha512sum -c umu-run.sha512sum); then
            rm -rf "$tmp"
            msg "Erreur UMU" "Le checksum SHA512 de umu-run est invalide."
            return
        fi
    fi

    mkdir -p "$UMU_BACKUP"
    if [ -s "$UMU_RUN" ]; then
        local safeold
        safeold="$(printf '%s' "$oldver" | tr -c 'A-Za-z0-9._-' '_')"
        cp -a "$UMU_RUN" "$UMU_BACKUP/umu-run-${safeold}-$(date '+%Y%m%d-%H%M%S')"
    fi

    cp -a "$newrun" "$UMU_RUN"
    chmod +x "$UMU_RUN"
    rm -f "$UMU_DIR/umu_run.py"
    ln -s umu-run "$UMU_DIR/umu_run.py"
    echo "$tag" > "$UMU_DIR/.umu_version"

    rm -rf "$tmp"
    log "UMU updated to $tag"
    msg "UMU mis a jour" \
"UMU $tag est installe.

Les anciennes copies sont conservees dans :
$UMU_BACKUP

Le runtime steamrt4 existant est conserve."
}

rollback_umu() {
    local files count
    files="$(find "$UMU_BACKUP" -maxdepth 1 -type f -name 'umu-run-*' -printf '%f\n' 2>/dev/null | sort -r)"
    if [ -z "$files" ]; then
        msg "Rollback UMU" "Aucune sauvegarde UMU disponible."
        return
    fi

    local opts=()
    while IFS= read -r f; do
        [ -n "$f" ] && opts+=("$f" "$f")
    done <<< "$files"

    local choice
    if command -v dialog >/dev/null 2>&1; then
        choice="$(dialog --stdout --title "Rollback UMU" --menu "Choisissez la sauvegarde a restaurer :" 20 90 12 "${opts[@]}")" || return
    else
        clear
        echo "$files"
        echo
        printf "Nom exact de la sauvegarde : "
        read -r choice
    fi
    [ -n "$choice" ] || return

    if yesno "Rollback UMU" "Restaurer $choice ?"; then
        cp -a "$UMU_BACKUP/$choice" "$UMU_RUN"
        chmod +x "$UMU_RUN"
        rm -f "$UMU_DIR/umu_run.py"
        ln -s umu-run "$UMU_DIR/umu_run.py"
        msg "Rollback UMU" "Sauvegarde restauree.\n\nVersion active : $(umu_version)"
    fi
}

fetch_ge_releases() {
    local out="$1"
    : > "$out"
    local page tmp count
    for page in 1 2 3 4 5; do
        tmp="${out}.page${page}"
        if ! curl -fsSL --max-time 25 \
            "https://api.github.com/repos/$GE_REPO/releases?per_page=100&page=$page" \
            -o "$tmp"; then
            rm -f "${out}.page"*
            return 1
        fi
        count="$(python3 - "$tmp" <<'PY'
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    print(len(d) if isinstance(d,list) else 0)
except Exception:
    print(0)
PY
)"
        cat "$tmp" >> "$out"
        printf '\n' >> "$out"
        rm -f "$tmp"
        [ "${count:-0}" -lt 100 ] && break
    done
    return 0
}

build_ge_menu() {
    local pages="$1"
    local menu="$2"
    python3 - "$pages" > "$menu" <<'PY'
import json,sys,re
path=sys.argv[1]
releases=[]
text=open(path,encoding="utf-8").read()
dec=json.JSONDecoder()
i=0
while i < len(text):
    while i < len(text) and text[i].isspace():
        i+=1
    if i>=len(text):
        break
    try:
        obj,j=dec.raw_decode(text,i)
    except Exception:
        break
    if isinstance(obj,list):
        releases.extend(obj)
    i=j

def select_assets(rel, tag):
    assets=rel.get("assets",[])
    by_name={a.get("name",""):a.get("browser_download_url","") for a in assets}

    # New GE releases (notably 11-4/11-5) publish architecture-specific x86_64
    # archives. Prefer these so Batocera x86_64 never receives aarch64.
    tar_candidates=[
        f"{tag}-x86_64.tar.gz",
        f"{tag}.tar.gz",
    ]
    sum_candidates=[
        f"{tag}-x86_64.sha512sum",
        f"{tag}.sha512sum",
    ]

    tarurl=next((by_name[n] for n in tar_candidates if by_name.get(n)), "")
    sumurl=next((by_name[n] for n in sum_candidates if by_name.get(n)), "")

    # Fallback on URLs, while explicitly excluding aarch64.
    if not tarurl:
        for a in assets:
            name=a.get("name","")
            u=a.get("browser_download_url","")
            if "aarch64" in name.lower():
                continue
            if re.search(rf"/{re.escape(tag)}(?:-x86_64)?\.tar\.gz$",u):
                tarurl=u
                break
    if not sumurl:
        for a in assets:
            name=a.get("name","")
            u=a.get("browser_download_url","")
            if "aarch64" in name.lower():
                continue
            if re.search(rf"/{re.escape(tag)}(?:-x86_64)?\.sha512sum$",u):
                sumurl=u
                break
    return tarurl,sumurl

seen=set()
rows=[]
for rel in releases:
    tag=rel.get("tag_name","")
    if tag in seen or not re.fullmatch(r"GE-Proton\d+-\d+",tag):
        continue
    seen.add(tag)
    tarurl,sumurl=select_assets(rel,tag)
    if tarurl:
        nums=list(map(int,re.findall(r"\d+",tag)))
        rows.append(((nums[0],nums[1]),tag,tarurl,sumurl))

for _,tag,tarurl,sumurl in sorted(rows,reverse=True):
    print(f"{tag}\t{tarurl}\t{sumurl}")
PY
}
fetch_ge_tag() {
    local tag="$1"
    local out="$2"
    curl -fsSL --max-time 25 \
        "https://api.github.com/repos/$GE_REPO/releases/tags/$tag" \
        -o "$out"
}

resolve_ge_tag() {
    local tag="$1"
    local json="$2"
    python3 - "$json" "$tag" <<'PY'
import json,sys,re
d=json.load(open(sys.argv[1]))
tag=sys.argv[2]
assets=d.get("assets",[])
by_name={a.get("name",""):a.get("browser_download_url","") for a in assets}

tarurl=""
sumurl=""
for n in (f"{tag}-x86_64.tar.gz", f"{tag}.tar.gz"):
    if by_name.get(n):
        tarurl=by_name[n]
        break
for n in (f"{tag}-x86_64.sha512sum", f"{tag}.sha512sum"):
    if by_name.get(n):
        sumurl=by_name[n]
        break

if not tarurl:
    for a in assets:
        name=a.get("name","")
        u=a.get("browser_download_url","")
        if "aarch64" in name.lower():
            continue
        if re.search(rf"/{re.escape(tag)}(?:-x86_64)?\.tar\.gz$",u):
            tarurl=u
            break

if not sumurl:
    for a in assets:
        name=a.get("name","")
        u=a.get("browser_download_url","")
        if "aarch64" in name.lower():
            continue
        if re.search(rf"/{re.escape(tag)}(?:-x86_64)?\.sha512sum$",u):
            sumurl=u
            break

if tarurl:
    print(f"{tag}\t{tarurl}\t{sumurl}")
PY
}
install_ge() {
    require_net || return

    local tmp pages menu_file
    tmp="$(mktemp -d "$RUNNER_STAGING_ROOT/ge-list.XXXXXX")"
    pages="$tmp/releases.pages"

    clear
    echo "Chargement des releases GE-Proton..."
    if ! fetch_ge_releases "$pages"; then
        rm -rf "$tmp"
        msg "Erreur GE-Proton" "Impossible de recuperer les releases GE-Proton."
        return
    fi

    menu_file="$tmp/menu.tsv"
    build_ge_menu "$pages" "$menu_file"

    if [ ! -s "$menu_file" ]; then
        rm -rf "$tmp"
        msg "Erreur GE-Proton" "Aucune release x86_64 compatible n'a ete trouvee."
        return
    fi

    local opts=()
    while IFS=$'\t' read -r tag tarurl sumurl; do
        local state
        if [ -d "$CUSTOM_DIR/${tag}-UMU" ]; then
            state="INSTALLE / PROTEGE CONTRE ECRASEMENT"
        else
            state="disponible"
        fi
        opts+=("$tag" "$state")
    done < "$menu_file"
    opts+=("MANUAL" "Saisir un tag exact (ex: GE-Proton11-4)")

    local tag
    if command -v dialog >/dev/null 2>&1; then
        tag="$(dialog --stdout --title "Installer GE-Proton + UMU" \
            --menu "Installation immutable : un runner existant ne sera jamais remplace." \
            24 96 17 "${opts[@]}")" || { rm -rf "$tmp"; return; }
    else
        clear
        cut -f1 "$menu_file"
        echo "MANUAL"
        echo
        printf "Version a installer : "
        read -r tag
    fi
    [ -n "$tag" ] || { rm -rf "$tmp"; return; }

    local line tarurl sumurl tag_json
    if [ "$tag" = "MANUAL" ]; then
        tag="$(input_box "Version GE-Proton" "Saisissez le tag exact, par exemple GE-Proton11-4 :" "GE-Proton11-4")" || {
            rm -rf "$tmp"; return;
        }
        if ! printf '%s' "$tag" | grep -Eq '^GE-Proton[0-9]+-[0-9]+$'; then
            rm -rf "$tmp"
            msg "Tag invalide" "Format attendu : GE-Proton11-4"
            return
        fi
        tag_json="$tmp/tag.json"
        if ! fetch_ge_tag "$tag" "$tag_json"; then
            rm -rf "$tmp"
            msg "Release introuvable" "$tag n'a pas ete trouve sur GitHub."
            return
        fi
        line="$(resolve_ge_tag "$tag" "$tag_json")"
    else
        line="$(awk -F '\t' -v t="$tag" '$1==t {print; exit}' "$menu_file")"
    fi

    if [ -z "$line" ]; then
        rm -rf "$tmp"
        msg "Release invalide" "Archive x86_64 introuvable pour $tag."
        return
    fi

    tarurl="$(printf '%s' "$line" | cut -f2)"
    sumurl="$(printf '%s' "$line" | cut -f3)"
    local target="$CUSTOM_DIR/${tag}-UMU"

    # IMMUTABLE POLICY: never touch an existing runner.
    if [ -e "$target" ]; then
        rm -rf "$tmp"
        msg "Runner protege" \
"$tag-UMU existe deja.

La v0.4 refuse volontairement toute reinstallation ou mise a niveau sur place.

Pour tester une nouvelle version, installez-la sous son propre numero de version.
Pour remplacer exceptionnellement ce runner, archivez-le d'abord depuis le menu de suppression."
        return
    fi

    if ! yesno "Installer $tag-UMU" \
"Le runner sera construit dans une zone temporaire puis controle avant installation.

Destination finale :
$target

Aucun runner existant ne sera modifie.

Continuer ?"; then
        rm -rf "$tmp"
        return
    fi

    local stage="$RUNNER_STAGING_ROOT/${tag}-UMU.$(date '+%Y%m%d-%H%M%S').$$"
    mkdir -p "$stage/download" "$stage/extracted"
    local tarname sumname
    tarname="$(basename "$tarurl")"
    if [ -n "$sumurl" ]; then
        sumname="$(basename "$sumurl")"
    else
        sumname="$tag.sha512sum"
    fi

    clear
    echo "Telechargement de $tag..."
    if ! curl -fL --progress-bar "$tarurl" -o "$stage/download/$tarname"; then
        rm -rf "$tmp" "$stage"
        msg "Erreur GE-Proton" "Echec du telechargement."
        return
    fi

    if [ -n "$sumurl" ]; then
        echo "Verification SHA512 upstream..."
        if ! curl -fsSL "$sumurl" -o "$stage/download/$sumname"; then
            rm -rf "$tmp" "$stage"
            msg "Erreur GE-Proton" "Impossible de telecharger le checksum."
            return
        fi
        if ! (cd "$stage/download" && sha512sum -c "$sumname"); then
            rm -rf "$tmp" "$stage"
            msg "Erreur GE-Proton" "Checksum SHA512 upstream invalide. Rien n'a ete installe."
            return
        fi
    else
        log "WARNING checksum absent for $tag"
    fi

    echo "Extraction en staging..."
    if ! tar -xzf "$stage/download/$tarname" -C "$stage/extracted"; then
        rm -rf "$tmp" "$stage"
        msg "Erreur GE-Proton" "Extraction impossible. Rien n'a ete installe."
        return
    fi

    local extracted candidate
    extracted="$(find "$stage/extracted" -mindepth 1 -maxdepth 1 -type d | head -n1)"
    if [ -z "$extracted" ] || [ ! -s "$extracted/proton" ] ||
       [ ! -s "$extracted/files/bin/wine" ] ||
       [ ! -s "$extracted/files/bin/wineserver" ]; then
        rm -rf "$tmp" "$stage"
        msg "Erreur GE-Proton" "Structure GE-Proton inattendue. Rien n'a ete installe."
        return
    fi

    candidate="$stage/candidate"
    mv "$extracted" "$candidate"

    # Overlay only adds Batocera integration files. Existing upstream files are
    # never taken from another installed runner.
    cp -a "$OVERLAY/." "$candidate/"
    chmod +x "$candidate/proton" "$candidate/bin/wine" "$candidate/bin/wine64" \
        "$candidate/bin/wineserver" "$candidate/umu-batocera/umu-root-runner.py" 2>/dev/null || true

    mkdir -p "$candidate/umu-batocera"
    cat > "$candidate/umu-batocera/runner-info" <<EOF
GE_PROTON=$tag
UMU_INTEGRATION=3.7.1
TOOLBOX_VERSION=$TOOLBOX_VERSION
INSTALL_SOURCE=github-release
SOURCE_URL=$tarurl
STATUS=experimental
INSTALLED_AT=$(date -Is 2>/dev/null || date)
EOF

    if ! write_manifest "$candidate"; then
        rm -rf "$tmp" "$stage"
        msg "Erreur GE-Proton" "Impossible de creer l'empreinte d'integrite. Rien n'a ete installe."
        return
    fi

    # Re-check the staged candidate after hashing.
    if ! verify_runner_manifest "$candidate"; then
        rm -rf "$tmp" "$stage"
        msg "Erreur GE-Proton" "Le runner a change pendant sa preparation. Installation annulee."
        return
    fi

    # Atomic same-filesystem install. Refuse if target appeared in the meantime.
    if [ -e "$target" ]; then
        rm -rf "$tmp" "$stage"
        msg "Conflit" "$target est apparu pendant l'installation. Aucun fichier n'a ete ecrase."
        return
    fi

    echo "Installation atomique de $tag-UMU..."
    if ! mv "$candidate" "$target"; then
        rm -rf "$tmp" "$stage"
        msg "Erreur GE-Proton" "Impossible de finaliser l'installation. Les runners existants sont intacts."
        return
    fi

    rm -rf "$tmp" "$stage"
    log "Installed immutable ${tag}-UMU"
    msg "Runner installe" \
"$tag-UMU est installe comme NOUVEAU runner.

Statut : EXPERIMENTAL
Integrite : PROTEGEE

Apres validation en jeu, utilisez :
Proteger / valider un runner
pour le marquer comme connu fonctionnel.

Une autre version GE-Proton-UMU ne modifiera jamais ce dossier."
}

list_runners() {
    local out="" r
    while IFS= read -r r; do
        [ -n "$r" ] || continue
        out="${out}${r}  [$(runner_integrity_label "$CUSTOM_DIR/$r")]\n"
    done <<< "$(installed_runners)"
    [ -n "$out" ] || out="(aucun runner UMU installe)"
    msg "Runners GE-Proton + UMU" "$out"
}

upgrade_integration() {
    local runners r base changed=0 skipped="" upgraded=""
    runners="$(installed_runners)"
    [ -n "$runners" ] || { msg "Integration v3.7.1" "Aucun runner UMU installe."; return; }

    if ! yesno "Installer l'integration v3.7.1" \
"Cette operation remplace UNIQUEMENT les fichiers d'integration Batocera (bin/wine, bin/wine64, bin/wineserver et pont UMU) des runners dont le manifest est actuellement sain.

Les fichiers Wine/Proton upstream ne sont pas remplaces.
Les runners deja MODIFIES sont refuses.

Continuer ?"; then return; fi

    while IFS= read -r r; do
        [ -n "$r" ] || continue
        base="$CUSTOM_DIR/$r"
        if [ ! -s "$(runner_manifest_path "$base")" ]; then
            skipped="$skipped$r : NON MANAGE\n"
            continue
        fi
        if ! verify_runner_manifest "$base"; then
            skipped="$skipped$r : MODIFIE (refuse)\n"
            continue
        fi
        mkdir -p "$base/umu-batocera"
        cp -a "$OVERLAY/bin/wine" "$base/bin/wine" || continue
        cp -a "$OVERLAY/bin/wine64" "$base/bin/wine64" || continue
        cp -a "$OVERLAY/bin/wineserver" "$base/bin/wineserver" || continue
        cp -a "$OVERLAY/umu-batocera/umu-root-runner.py" "$base/umu-batocera/umu-root-runner.py" || continue
        chmod +x "$base/bin/wine" "$base/bin/wine64" "$base/bin/wineserver" "$base/umu-batocera/umu-root-runner.py" 2>/dev/null || true
        # Trusted migration: old manifest was verified immediately before replacing
        # only Toolbox-owned integration files. Re-hash the complete monitored set.
        if ! write_manifest "$base"; then
            skipped="$skipped$r : erreur manifest apres migration\n"
            continue
        fi
        if [ -f "$(runner_state_path "$base")" ]; then
            sed -i 's/^UMU_INTEGRATION=.*/UMU_INTEGRATION=3.7.1/' "$(runner_state_path "$base")" 2>/dev/null || true
            sed -i "s/^TOOLBOX_VERSION=.*/TOOLBOX_VERSION=$TOOLBOX_VERSION/" "$(runner_state_path "$base")" 2>/dev/null || true
        fi
        upgraded="$upgraded$r : v3.7.1 OK\n"
        changed=$((changed+1))
    done <<< "$runners"

    msg "Integration v3.7.1" "Runners mis a niveau : $changed\n\n${upgraded:-Aucun}\nRefuses / ignores :\n${skipped:-Aucun}\nLa v3.7.1 protege automatiquement TOUS les runners *-UMU en lecture seule pendant chaque lancement UMU."
}

scan_prefix_refs() {
    local p out total
    p="$(input_box "Scanner un prefixe" "Chemin du prefixe .wine / wine-bottle / prefixe monte :" "/userdata/roms/windows/")" || return
    [ -n "$p" ] || return
    if [ ! -d "$p" ]; then msg "Prefixe introuvable" "$p n'est pas un dossier accessible."; return; fi
    out="$(mktemp "$RUNNER_STAGING_ROOT/prefix-scan.XXXXXX")"
    find "$p" -type l -print0 2>/dev/null | while IFS= read -r -d '' f; do
        t="$(readlink "$f" 2>/dev/null || true)"
        case "$t" in
            /userdata/system/wine/custom/*)
                printf '%s\n' "$t" | sed -n 's#^\(/userdata/system/wine/custom/[^/]*\)/.*#\1#p'
                ;;
        esac
    done | sort | uniq -c > "$out"
    total="$(awk '{s+=$1} END{print s+0}' "$out")"
    if [ "$total" -eq 0 ]; then
        rm -f "$out"; msg "Analyse du prefixe" "Aucun symlink absolu vers /userdata/system/wine/custom n'a ete trouve."
        return
    fi
    local report="Prefixe : $p\nLiens absolus vers des runners : $total\n\n"
    while read -r n target; do report="$report$n lien(s) -> $(basename "$target")\n"; done < "$out"
    rm -f "$out"
    msg "References inter-runners" "$report\nUn prefixe multi-runner reste autorise. La v3.7.1 empeche ces liens d'ecrire dans les distributions UMU."
}

runtime_protection_status() {
    local report="" r opts
    while IFS= read -r r; do
        [ -n "$r" ] || continue
        opts="$(findmnt -n -o OPTIONS -T "$CUSTOM_DIR/$r" 2>/dev/null || true)"
        if mountpoint -q "$CUSTOM_DIR/$r" 2>/dev/null; then
            case ",$opts," in *,ro,*) report="$report[RO] $r\n" ;; *) report="$report[RW MOUNT] $r\n" ;; esac
        else
            report="$report[normal] $r (sera protege RO au lancement UMU)\n"
        fi
    done <<< "$(installed_runners)"
    msg "Protection runtime" "${report:-Aucun runner UMU.}\n\nNormal hors jeu = attendu. La v3.7.1 cree les bind-mounts RO au lancement et les retire a la fin."
}

verify_install() {
    local report=""
    if [ -s "$UMU_RUN" ]; then
        report="$report[OK] umu-run : $(umu_version)\n"
    else
        report="$report[KO] umu-run absent\n"
    fi

    if [ -d "$UMU_DIR/home/.local/share/umu/steamrt4" ]; then
        report="$report[OK] steamrt4 present\n"
    else
        report="$report[INFO] steamrt4 absent (UMU peut le telecharger)\n"
    fi

    local r base integ
    while IFS= read -r r; do
        [ -n "$r" ] || continue
        base="$CUSTOM_DIR/$r"
        if [ ! -s "$base/proton" ] ||
           [ ! -x "$base/bin/wine" ] ||
           [ ! -s "$base/files/bin/wine" ]; then
            report="$report[KO] $r : incomplet\n"
            continue
        fi

        integ="$(runner_integrity_label "$base")"
        case "$integ" in
            "PROTEGE / OK") report="$report[OK] $r : integrite valide\n" ;;
            "MODIFIE") report="$report[ALERTE] $r : FICHIERS CRITIQUES MODIFIES\n" ;;
            *) report="$report[INFO] $r : non manage, creez une reference si valide\n" ;;
        esac
    done <<< "$(installed_runners)"

    report="$report\nPolitique v0.4 : runners isoles en lecture seule pendant les jeux UMU.\nLogs : $LOG_DIR"
    msg "Diagnostic / integrite" "$report"
}

export_runner() {
    local runners choice base label export_dir archive tmp_size hash
    runners="$(installed_runners)"
    if [ -z "$runners" ]; then
        msg "Exporter un runner" "Aucun runner GE-Proton-UMU installe."
        return
    fi

    local opts=() r
    while IFS= read -r r; do
        [ -n "$r" ] || continue
        opts+=("$r" "$(runner_integrity_label "$CUSTOM_DIR/$r")")
    done <<< "$runners"

    if command -v dialog >/dev/null 2>&1; then
        choice="$(dialog --stdout --title "Exporter un runner" \
            --menu "Choisissez le runner a empaqueter en .tar.xz. Un runner MODIFIE ne peut pas etre exporte." \
            22 100 14 "${opts[@]}")" || return
    else
        clear
        echo "==== Exporter un runner ===="
        echo
        while IFS= read -r r; do
            [ -n "$r" ] && printf '%s  [%s]\n' "$r" "$(runner_integrity_label "$CUSTOM_DIR/$r")"
        done <<< "$runners"
        echo
        printf "Runner a exporter : "
        read -r choice
    fi
    [ -n "$choice" ] || return

    base="$CUSTOM_DIR/$choice"
    [ -d "$base" ] || { msg "Erreur" "Runner introuvable : $choice"; return; }
    label="$(runner_integrity_label "$base")"

    if [ "$label" = "MODIFIE" ]; then
        msg "Export refuse" \
"$choice est signale MODIFIE.

L'export est bloque afin d'eviter de partager un runner contamine.
Reinstallez/reparez d'abord une copie saine."
        return
    fi

    if [ "$label" = "NON MANAGE" ]; then
        msg "Export refuse" \
"$choice ne possede pas encore de manifest de reference.

Utilisez d'abord l'option de creation de reference, puis relancez l'export."
        return
    fi

    if ! verify_runner_manifest "$base"; then
        msg "Export refuse" "Le controle d'integrite de $choice a echoue. Aucun fichier n'a ete exporte."
        return
    fi

    if ! command -v xz >/dev/null 2>&1; then
        msg "Export impossible" "La commande xz n'est pas disponible sur ce systeme."
        return
    fi

    export_dir="/userdata/system/umu/exports"
    mkdir -p "$export_dir"
    archive="$export_dir/${choice}-$(date '+%Y%m%d-%H%M%S').tar.xz"

    if ! yesno "Confirmer l'export" \
"Runner : $choice
Integrite : $label

Archive :
$archive

Le dossier du runner sera archive tel quel : permissions, executables et symlinks seront conserves.
Le runner actif ne sera pas modifie.

Creer l'archive ?"; then
        return
    fi

    log "Export start: $choice -> $archive"
    if tar -C "$CUSTOM_DIR" -cJf "$archive" -- "$choice" >>"$LOG" 2>&1; then
        if ! xz -t "$archive" >>"$LOG" 2>&1; then
            rm -f "$archive"
            msg "Export echoue" "L'archive a ete creee mais son test XZ a echoue. Elle a ete supprimee."
            return
        fi
        tmp_size="$(du -h "$archive" 2>/dev/null | awk '{print $1}')"
        hash="$(sha256sum "$archive" | awk '{print $1}')"
        printf '%s  %s\n' "$hash" "$(basename "$archive")" > "${archive}.sha256"
        log "Export OK: $archive sha256=$hash"
        msg "Export termine" \
"Runner exporte avec succes.

Archive :
$archive

Taille : ${tmp_size:-inconnue}
SHA-256 :
$hash

Un fichier .sha256 a egalement ete cree a cote de l'archive.

Pour restaurer manuellement sur une autre Batocera :
tar -xJf \"$(basename "$archive")\" -C /userdata/system/wine/custom/"
    else
        rm -f "$archive" "${archive}.sha256"
        msg "Export echoue" "tar/xz a retourne une erreur. Consultez :\n$LOG"
    fi
}
export_shareable_package() {
    local runners choice base label export_dir pkgroot pkgname work runner_archive archive hash size
    runners="$(installed_runners)"
    if [ -z "$runners" ]; then
        msg "Package partageable" "Aucun runner GE-Proton-UMU installe."
        return
    fi

    local opts=() r
    while IFS= read -r r; do
        [ -n "$r" ] || continue
        opts+=("$r" "$(runner_integrity_label "$CUSTOM_DIR/$r")")
    done <<< "$runners"

    if command -v dialog >/dev/null 2>&1; then
        choice="$(dialog --stdout --title "Creer un package partageable" \\
            --menu "Le package contient le runner, un installateur autonome et la documentation. UMU sera installe/mis a jour depuis sa release officielle sur la machine cible." \\
            22 105 14 "${opts[@]}")" || return
    else
        clear
        echo "==== Creer un package partageable ===="
        echo
        while IFS= read -r r; do
            [ -n "$r" ] && printf '%s  [%s]\n' "$r" "$(runner_integrity_label "$CUSTOM_DIR/$r")"
        done <<< "$runners"
        echo
        printf "Runner a partager : "
        read -r choice
    fi
    [ -n "$choice" ] || return

    base="$CUSTOM_DIR/$choice"
    [ -d "$base" ] || { msg "Erreur" "Runner introuvable : $choice"; return; }
    label="$(runner_integrity_label "$base")"
    if [ "$label" != "PROTEGE / OK" ] || ! verify_runner_manifest "$base"; then
        msg "Export refuse" "$choice n'est pas dans un etat sain et gere. Le package partageable n'a pas ete cree."
        return
    fi
    command -v xz >/dev/null 2>&1 || { msg "Export impossible" "La commande xz est absente."; return; }

    export_dir="/userdata/system/umu/exports"
    mkdir -p "$export_dir"
    pkgname="${choice}-Batocera-UMU-Package-$(date '+%Y%m%d-%H%M%S')"
    work="$(mktemp -d)"
    pkgroot="$work/$pkgname"
    mkdir -p "$pkgroot/payload"
    runner_archive="$pkgroot/payload/${choice}.tar.xz"

    if ! yesno "Confirmer le package" "Runner : $choice\nIntegrite : $label\n\nLe package autonome :\n- contient le runner complet ;\n- installe umu-run officiel si necessaire ;\n- laisse UMU telecharger steamrt4 au premier lancement si absent ;\n- remplace un runner homonyme apres verification ;\n- ne contient pas steamrt4 afin d'eviter une archive enorme.\n\nCreer le package ?"; then
        rm -rf "$work"; return
    fi

    clear
    echo "Compression du runner..."
    if ! tar -C "$CUSTOM_DIR" -cJf "$runner_archive" -- "$choice"; then
        rm -rf "$work"; msg "Erreur" "Echec de compression du runner."; return
    fi
    xz -t "$runner_archive" || { rm -rf "$work"; msg "Erreur" "Test XZ du runner echoue."; return; }
    (cd "$pkgroot/payload" && sha256sum "${choice}.tar.xz" > "${choice}.tar.xz.sha256")

    cat > "$pkgroot/install.sh" <<'EOS'
#!/bin/bash
set -e
BASE="$(cd "$(dirname "$0")" && pwd)"
PAYLOAD="$BASE/payload"
CUSTOM="/userdata/system/wine/custom"
UMU="/userdata/system/umu"
[ "$(id -u)" -eq 0 ] || { echo "ERREUR: lancez cet installateur en root."; exit 1; }
RUNARCH="$(find "$PAYLOAD" -maxdepth 1 -type f -name 'GE-Proton*-UMU.tar.xz' | head -n1)"
[ -n "$RUNARCH" ] || { echo "ERREUR: payload runner absent."; exit 1; }
(cd "$PAYLOAD" && sha256sum -c "$(basename "$RUNARCH").sha256")
RUNNER="$(basename "$RUNARCH" .tar.xz)"
mkdir -p "$CUSTOM" "$UMU/backups"

install_umu() {
  command -v curl >/dev/null 2>&1 || { echo "ERREUR: curl est requis."; exit 1; }
  command -v python3 >/dev/null 2>&1 || { echo "ERREUR: python3 est requis."; exit 1; }
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' RETURN
  echo "Recuperation de la derniere release officielle UMU..."
  curl -fsSL --max-time 30 https://api.github.com/repos/Open-Wine-Components/umu-launcher/releases/latest -o "$tmp/release.json"
  python3 - "$tmp/release.json" > "$tmp/urls" <<'PY2'
import json,sys
d=json.load(open(sys.argv[1])); tag=d.get('tag_name',''); asset=sum(([a.get('browser_download_url','')] for a in d.get('assets',[]) if a.get('browser_download_url','').endswith('zipapp.tar')),[]); chk=sum(([a.get('browser_download_url','')] for a in d.get('assets',[]) if a.get('browser_download_url','').endswith('umu-run.sha512sum')),[]); print(tag); print(asset[0] if asset else ''); print(chk[0] if chk else '')
PY2
  tag="$(sed -n '1p' "$tmp/urls")"; asset="$(sed -n '2p' "$tmp/urls")"; chk="$(sed -n '3p' "$tmp/urls")"
  [ -n "$asset" ] || { echo "ERREUR: asset UMU zipapp introuvable."; exit 1; }
  curl -fL --progress-bar "$asset" -o "$tmp/umu.tar"
  mkdir "$tmp/x"; tar -xf "$tmp/umu.tar" -C "$tmp/x"
  newrun="$(find "$tmp/x" -type f -name umu-run | head -n1)"; [ -s "$newrun" ] || { echo "ERREUR: umu-run absent."; exit 1; }
  if [ -n "$chk" ]; then curl -fsSL "$chk" -o "$tmp/umu-run.sha512sum"; cp "$newrun" "$tmp/umu-run"; (cd "$tmp" && sha512sum -c umu-run.sha512sum); fi
  if [ -s "$UMU/umu-run" ]; then cp -a "$UMU/umu-run" "$UMU/backups/umu-run-before-package-$(date '+%Y%m%d-%H%M%S')"; fi
  cp -a "$newrun" "$UMU/umu-run"; chmod +x "$UMU/umu-run"; rm -f "$UMU/umu_run.py"; ln -s umu-run "$UMU/umu_run.py"; printf '%s\n' "$tag" > "$UMU/.umu_version"
  rm -rf "$tmp"; trap - RETURN
}

if [ ! -s "$UMU/umu-run" ]; then install_umu; else echo "UMU deja present : conservation de l'installation existante."; fi
STAGE="$(mktemp -d /userdata/system/umu/package-staging.XXXXXX)"
trap 'rm -rf "$STAGE"' EXIT
echo "Preparation et verification de $RUNNER..."
tar -xJf "$RUNARCH" -C "$STAGE"
MAN="$STAGE/$RUNNER/umu-batocera/integrity.sha256"
[ -f "$MAN" ] || { echo "ERREUR: manifest absent apres extraction."; exit 1; }
(cd "$STAGE/$RUNNER" && sha256sum -c "$MAN")
echo "Installation de $RUNNER..."
rm -rf --one-file-system "$CUSTOM/$RUNNER"
mv "$STAGE/$RUNNER" "$CUSTOM/$RUNNER"
rm -rf "$STAGE"; trap - EXIT
echo
echo "Installation terminee. Le runtime steamrt4 sera telecharge automatiquement par UMU au premier lancement s'il n'est pas deja present."
echo "Le runner est disponible dans /userdata/system/wine/custom/$RUNNER"
EOS
    chmod +x "$pkgroot/install.sh"

    cat > "$pkgroot/README.txt" <<EOF
BATOCERA - PACKAGE PARTAGEABLE $choice
========================================

Ce package installe le runner $choice et prepare l'infrastructure UMU minimale.
Il est destine a une Batocera qui possede ou non deja UMU.

INSTALLATION
------------
1. Copier ce dossier/package dans /userdata/system/ (via \\\\BATOCERA\\share\\system par exemple).
2. Ouvrir un terminal ou SSH en root.
3. Entrer dans le dossier extrait puis lancer :
     chmod +x install.sh
     ./install.sh
4. Une connexion Internet est necessaire uniquement si umu-run n'est pas deja installe.
5. Au premier lancement d'un jeu UMU, steamrt4 peut etre telecharge automatiquement par UMU.
6. Le runner apparait ensuite dans les choix Wine/Windows de Batocera sous le nom : $choice

COMPATIBILITE
-------------
- jeux .pc
- prefixes .wine
- jeux .wsquashfs
- wine-bottles / sauvegardes externes

IMPORTANT
---------
Le runner contient l'integration Batocera/UMU v3.7.1 et son manifest d'integrite.
Les runners UMU sont proteges en lecture seule pendant les lancements UMU afin qu'un prefixe reutilise avec plusieurs versions de Proton ne puisse pas modifier un autre runner.
Les runners standards Batocera (Proton, Wine-TKG, Kron4ek...) ne sont pas remplaces par ce package.

Pour gerer, mettre a jour, diagnostiquer et exporter des runners, utilisez la UMU Runner Toolbox v0.4.2 ou ulterieure.
EOF

    (cd "$pkgroot" && sha256sum install.sh README.txt payload/* > SHA256SUMS)
    archive="$export_dir/${pkgname}.tar.xz"
    echo "Creation du package final..."
    if tar -C "$work" -cJf "$archive" -- "$pkgname" && xz -t "$archive"; then
        hash="$(sha256sum "$archive" | awk '{print $1}')"; printf '%s  %s\n' "$hash" "$(basename "$archive")" > "${archive}.sha256"; size="$(du -h "$archive" | awk '{print $1}')"
        rm -rf "$work"
        msg "Package termine" "Package partageable cree :\n$archive\n\nTaille : $size\nSHA-256 :\n$hash\n\nCe package peut etre installe sur une Batocera sans installation UMU prealable."
    else
        rm -rf "$work" "$archive" "${archive}.sha256"; msg "Export echoue" "Impossible de creer/tester le package final."
    fi
}


delete_installed_runner() {
    local runners choice r
    runners="$(installed_runners)"
    if [ -z "$runners" ]; then
        msg "Supprimer un runner" "Aucun runner GE-Proton-UMU installe."
        return
    fi
    local opts=()
    while IFS= read -r r; do
        [ -n "$r" ] && opts+=("$r" "$(runner_integrity_label "$CUSTOM_DIR/$r")")
    done <<< "$runners"
    if command -v dialog >/dev/null 2>&1; then
        choice="$(dialog --stdout --title "Supprimer un runner UMU" --menu \
            "Choisissez le runner a supprimer. Les jeux, prefixes et sauvegardes ne seront pas supprimes." \
            26 100 15 "${opts[@]}")" || return
    else
        clear; printf '%s\n' "$runners"; echo; printf "Runner a supprimer : "; read -r choice
    fi
    [ -n "$choice" ] || return
    [ -d "$CUSTOM_DIR/$choice" ] || { msg "Erreur" "Runner introuvable : $choice"; return; }
    if ! yesno "Confirmer la suppression" "Supprimer definitivement :\n\n$CUSTOM_DIR/$choice\n\nLes jeux, prefixes .wine/.pc/.wsquashfs, wine-bottles et sauvegardes ne seront pas supprimes.\n\nContinuer ?"; then return; fi
    if rm -rf --one-file-system "$CUSTOM_DIR/$choice"; then
        log "Runner deleted by user: $choice"
        msg "Runner supprime" "$choice a ete supprime.\n\nVos jeux, prefixes et sauvegardes n'ont pas ete touches."
    else
        msg "Erreur" "Impossible de supprimer $choice. Consultez :\n$LOG"
    fi
}

export_menu() {
    while true; do
        local choice
        choice="$(menu_choice "Exporter / partager un runner" \
            "1" "Creer un package partageable/autonome (recommande)" \
            "2" "Exporter le runner seul (.tar.xz)" \
            "0" "Retour")" || return
        case "$choice" in
            1) export_shareable_package ;;
            2) export_runner ;;
            0|"") return ;;
        esac
    done
}


human_bytes() {
    local bytes="${1:-0}"
    awk -v b="$bytes" 'BEGIN {
        split("o Ko Mo Go To", u, " "); i=1;
        while (b >= 1024 && i < 5) { b/=1024; i++ }
        if (i == 1) printf "%.0f %s", b, u[i]; else printf "%.1f %s", b, u[i]
    }'
}

dir_bytes() {
    local d="$1" n
    [ -d "$d" ] || { echo 0; return; }
    n="$(du -sb "$d" 2>/dev/null | awk 'NR==1{print $1}')"
    case "$n" in ''|*[!0-9]*) n=0 ;; esac
    echo "$n"
}

clear_dir_contents() {
    local d="$1"
    [ -d "$d" ] || { mkdir -p "$d"; return; }
    find "$d" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
}

umu_game_active() {
    # Never clean while UMU itself, our bridge, or an alias under merged-prefixes
    # is in use. The cleaner intentionally prefers a false positive to deleting
    # data belonging to a running game.
    if pgrep -f '/userdata/system/umu/umu-run|umu-root-runner\.py' >/dev/null 2>&1; then
        return 0
    fi
    if command -v findmnt >/dev/null 2>&1 && findmnt -rn 2>/dev/null | grep -Fq '/userdata/system/umu/merged-prefixes/'; then
        return 0
    fi
    return 1
}

clean_umu_test_data() {
    local compat="$UMU_DIR/compatdata"
    local merged="$UMU_DIR/merged-prefixes"
    local mesa="$UMU_DIR/cache/mesa_shader_cache"
    local radv="$UMU_DIR/cache/radv_builtin_shaders"
    local cb mb gb mesa_b radv_b total_game total_gpu report

    if umu_game_active; then
        msg "Nettoyage UMU refuse" "Un processus/lancement UMU ou un merged-prefix actif a ete detecte.\n\nFermez le jeu UMU en cours puis relancez le nettoyage."
        return
    fi

    mkdir -p "$compat" "$merged"
    cb="$(dir_bytes "$compat")"
    mb="$(dir_bytes "$merged")"
    total_game=$((cb + mb))
    mesa_b="$(dir_bytes "$mesa")"
    radv_b="$(dir_bytes "$radv")"
    total_gpu=$((mesa_b + radv_b))

    report="Donnees de jeux / tests UMU :\n- compatdata : $(human_bytes "$cb")\n- merged-prefixes : $(human_bytes "$mb")\n- total : $(human_bytes "$total_game")\n\nCaches graphiques facultatifs :\n- Mesa shader cache : $(human_bytes "$mesa_b")\n- RADV builtin shaders : $(human_bytes "$radv_b")\n- total : $(human_bytes "$total_gpu")\n\nSont toujours conserves : umu-run, steamrt4, home/.local/share/umu, protonfixes/umu-protonfixes, sauvegardes UMU et runners."
    msg "Analyse du nettoyage UMU" "$report"

    if [ "$total_game" -gt 0 ]; then
        if yesno "Nettoyer les donnees de tests" "Supprimer le contenu de :\n\n$compat\n$merged\n\nEspace actuellement occupe : $(human_bytes "$total_game")\n\nLes repertoires eux-memes seront conserves. Continuer ?"; then
            if umu_game_active; then
                msg "Nettoyage annule" "Un lancement UMU a demarre depuis l'analyse. Aucune donnee n'a ete supprimee."
                return
            fi
            clear_dir_contents "$compat"
            clear_dir_contents "$merged"
            log "umu_cleanup_game_data=done bytes_before=$total_game"
            msg "Nettoyage UMU" "Donnees de jeux/tests nettoyees.\n\nEspace precedemment occupe : $(human_bytes "$total_game")"
        fi
    else
        msg "Nettoyage UMU" "compatdata et merged-prefixes sont deja vides.\n\nAucune donnee de jeu/test a supprimer."
    fi

    # Shader caches are reconstructible but deliberately opt-in: deleting them
    # can cause shader recompilation/stutter on subsequent launches.
    if [ "$total_gpu" -gt 0 ] && yesno "Caches graphiques (facultatif)" "Les caches graphiques occupent $(human_bytes "$total_gpu").\n\nIls peuvent etre reconstruits automatiquement, mais leur suppression peut provoquer de la recompilation de shaders et des saccades temporaires aux prochains lancements.\n\nLes supprimer aussi ?"; then
        if umu_game_active; then
            msg "Caches non supprimes" "Un lancement UMU est maintenant actif. Les caches graphiques ont ete conserves."
            return
        fi
        clear_dir_contents "$mesa"
        clear_dir_contents "$radv"
        log "umu_cleanup_gpu_cache=done bytes_before=$total_gpu"
        msg "Caches graphiques" "Caches Mesa/RADV nettoyes.\n\nEspace precedemment occupe : $(human_bytes "$total_gpu")"
    fi
}

maintenance_menu() {
    while true; do
        local choice
        choice="$(menu_choice "Maintenance et diagnostic" \
            "1" "Verifier l'integrite des runners" \
            "2" "Verifier la protection des runners" \
            "3" "Reparer / mettre a niveau l'integration UMU" \
            "4" "Nettoyer les donnees de tests UMU" \
            "5" "Diagnostic UMU complet" \
            "0" "Retour")" || return
        case "$choice" in
            1) list_runners ;;
            2) runtime_protection_status ;;
            3) upgrade_integration ;;
            4) clean_umu_test_data ;;
            5) verify_install ;;
            0|"") return ;;
        esac
    done
}

documentation_about() {
    msg "Documentation / A propos" "UMU Runner Toolbox v$TOOLBOX_VERSION\n\nGestion simplifiee de runners GE-Proton + UMU pour Batocera.\n\nFonctions principales :\n- installation de GE-Proton-UMU ;\n- suppression d'un runner ;\n- export et creation de packages partageables ;\n- protection automatique des runners UMU en lecture seule pendant les jeux ;\n- controle automatique d'integrite avant lancement ;\n- nettoyage securise des donnees de tests UMU et caches graphiques facultatifs.\n\nLes runners Batocera standards, Wine-TKG et Kron4ek ne sont pas modifies.\n\nDocumentation :\n$ROOT/GUIDE_PARTAGE_ET_INSTALLATION.txt\n\nLogs :\n$LOG_DIR"
}

main_menu() {
    while true; do
        local choice
        choice="$(menu_choice "UMU Runner Toolbox v$TOOLBOX_VERSION" \
            "1" "Installer un runner GE-Proton UMU" \
            "2" "Supprimer un runner UMU" \
            "3" "Exporter / partager un runner" \
            "4" "Maintenance et diagnostic" \
            "5" "Documentation / A propos" \
            "0" "Quitter")" || exit 0
        case "$choice" in
            1) install_ge ;;
            2) delete_installed_runner ;;
            3) export_menu ;;
            4) maintenance_menu ;;
            5) documentation_about ;;
            0|"") clear; exit 0 ;;
        esac
    done
}
main_menu
