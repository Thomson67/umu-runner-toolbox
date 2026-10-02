#!/bin/bash
set -u

TOOLBOX_VERSION="0.13.0"
INTEGRATION_VERSION="3.10.0"
ROOT="/userdata/system/umu/toolbox"
OVERLAY="$ROOT/overlay"
CUSTOM_DIR="/userdata/system/wine/custom"
UMU_DIR="/userdata/system/umu"
UMU_RUN="$UMU_DIR/umu-run"
UMU_BACKUP="$UMU_DIR/backups"
LOG_DIR="/userdata/system/logs/umu-toolbox"
PORTS="/userdata/roms/ports"
PORT="$PORTS/UMU Runner Toolbox.sh"
PORT_KEYS="$PORTS/UMU Runner Toolbox.sh.keys"
OLD_ROOT="/userdata/system/umu-runner-toolbox"
RUNNER_STAGING_ROOT="$ROOT/staging"
GAMEID_OVERRIDES="$ROOT/config/gameid-overrides.csv"
WINDOWS_GAMELIST="/userdata/roms/windows/gamelist.xml"
RUNNER_LOG_DIR="/userdata/system/logs/umu-runner"
LANGUAGE_FILE="$ROOT/config/language"
TOOLBOX_LANGUAGE="fr"

load_language() {
    local saved=""
    [ -s "$LANGUAGE_FILE" ] && saved="$(tr -d '\r\n[:space:]' < "$LANGUAGE_FILE" 2>/dev/null || true)"
    case "$saved" in
        en|fr) TOOLBOX_LANGUAGE="$saved" ;;
        *) TOOLBOX_LANGUAGE="fr" ;;
    esac
}

save_language() {
    mkdir -p "$(dirname "$LANGUAGE_FILE")"
    printf '%s\n' "$TOOLBOX_LANGUAGE" > "$LANGUAGE_FILE"
}

ui() {
    i18n "$@"
}

load_language

load_i18n() {
    local catalog="$ROOT/lang/$TOOLBOX_LANGUAGE.sh"
    declare -gA I18N=()
    if [ -r "$catalog" ]; then
        # Translation catalogs contain data only: one associative array.
        # shellcheck disable=SC1090
        source "$catalog"
    fi
}

i18n() {
    local key="$1" fmt
    shift || true
    fmt="${I18N[$key]-}"
    if [ -z "$fmt" ]; then
        printf '[missing translation: %s]' "$key"
        log "i18n_missing key=$key language=$TOOLBOX_LANGUAGE"
        return 1
    fi
    printf "$fmt" "$@"
}

load_i18n

GE_REPO="GloriousEggroll/proton-ge-custom"
GDK_REPO="Weather-OS/GDK-Proton"
CACHY_REPO="CachyOS/proton-cachyos"
EM_REPO="BananaWorks07/Proton"
DW_REPO="dawn-winery/dwproton-mirror"
UMU_REPO="Open-Wine-Components/umu-launcher"
TOOLBOX_REPO="Thomson67/umu-runner-toolbox"
TOOLBOX_BRANCH="main"

# GE-Proton10-30..10-34 were previously blocked while compressed Batocera
# prefixes were passed directly to Proton as OverlayFS. Integration v3.8 keeps
# Proton's PFX on a real filesystem, so no GE 10-3x blacklist is required.
ge_tag_blocked() {
    return 1
}

mkdir -p "$CUSTOM_DIR" "$UMU_DIR" "$UMU_BACKUP" "$LOG_DIR" "$RUNNER_STAGING_ROOT"

LOG="$LOG_DIR/toolbox-$(date '+%Y%m%d-%H%M%S').log"
touch "$LOG"

log() {
    printf '%s\n' "$*" >> "$LOG"
}

rotate_log_dir() {
    local dir="$1" keep="${2:-20}" max_days="${3:-30}" current="${4:-}"
    local deleted=0 f
    mkdir -p "$dir"
    while IFS= read -r f; do
        [ -n "$f" ] || continue
        [ -n "$current" ] && [ "$f" = "$current" ] && continue
        rm -f -- "$f" 2>/dev/null && deleted=$((deleted+1))
    done < <(find "$dir" -mindepth 1 -maxdepth 1 -type f -name '*.log' -mtime "+$max_days" -print 2>/dev/null)
    local files=()
    while IFS= read -r f; do [ -n "$f" ] && files+=("$f"); done < <(find "$dir" -mindepth 1 -maxdepth 1 -type f -name '*.log' -printf '%T@ %p\n' 2>/dev/null | sort -nr | sed 's/^[^ ]* //')
    local i
    for ((i=keep; i<${#files[@]}; i++)); do
        f="${files[$i]}"
        [ -n "$current" ] && [ "$f" = "$current" ] && continue
        rm -f -- "$f" 2>/dev/null && deleted=$((deleted+1))
    done
    printf '%s' "$deleted"
}
rotate_umu_logs() {
    local tb rb
    tb="$(rotate_log_dir "$LOG_DIR" 20 30 "$LOG")"
    rb="$(rotate_log_dir "$RUNNER_LOG_DIR" 20 30)"
    log "log_rotation toolbox_deleted=$tb runner_deleted=$rb max_count=20 max_age=30d"
}
rotate_umu_logs

pause() {
    printf '\n%s' "$(ui press_enter)"
    read -r _
}

msg() {
    local title="$1"
    local text="$2"
    if command -v dialog >/dev/null 2>&1; then
        dialog --ok-label "$(i18n accept)" --title "$title" --msgbox "$text" 22 92
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
        dialog --yes-label "$(i18n yes)" --no-label "$(i18n no)" --title "$title" --yesno "$text" 20 92
        return $?
    fi
    clear
    echo "==== $title ===="
    echo
    printf '%b\n' "$text"
    echo
    printf "%s" "$(ui continue_prompt)"
    read -r ans
    case "$ans" in y|Y|o|O|oui|OUI|yes|YES) return 0 ;; *) return 1 ;; esac
}

menu_choice() {
    local title="$1"
    shift
    local raw=("$@") translated=() i=0 label_idx
    while [ "$i" -lt "${#raw[@]}" ]; do
        label_idx=$((i + 1))
        translated+=("${raw[$i]}" "${raw[$label_idx]}")
        i=$((i + 2))
    done
    if command -v dialog >/dev/null 2>&1; then
        set -- "${translated[@]}"
        dialog --stdout --ok-label "$(i18n accept)" --cancel-label "$(i18n cancel)" --title "$title" --menu "$(ui choose_action)" 26 96 15 "$@"
    else
        clear
        echo "==== $title ===="
        echo
        local args=("$@")
        local i=0
        local label_idx
        while [ "$i" -lt "${#args[@]}" ]; do
            label_idx=$((i + 1))
            printf '%s) %s\n' "${args[$i]}" "${args[$label_idx]}"
            i=$((i + 2))
        done
        echo
        printf "%s" "$(i18n choice_prompt)"
        read -r choice
        printf '%s' "$choice"
    fi
}

input_box() {
    local title="$1"
    local prompt="$2"
    local initial="${3-}"
    if command -v dialog >/dev/null 2>&1; then
        dialog --stdout --ok-label "$(i18n accept)" --cancel-label "$(i18n cancel)" --title "$title" --inputbox "$prompt" 12 90 "$initial"
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
        msg "$(ui connection_required)" "$(ui github_unreachable)"
        return 1
    fi
    return 0
}

root_bridge() {
    printf '%s' "$OVERLAY/umu-batocera/umu-root-runner.py"
}

umu_run_works() {
    [ -s "$UMU_RUN" ] || return 1
    [ -x "$UMU_RUN" ] || return 1
    python3 "$(root_bridge)" "$UMU_RUN" --version >/dev/null 2>&1
}

umu_version() {
    if [ ! -s "$UMU_RUN" ]; then
        printf 'non installe'
        return
    fi
    python3 "$(root_bridge)" "$UMU_RUN" --version 2>/dev/null | head -n1 | sed 's/^umu-launcher version //' || printf 'inconnue'
}

installed_runners() {
    find "$CUSTOM_DIR" -mindepth 1 -maxdepth 1 -type d \
        \( -name 'GE-Proton*-UMU' -o -name 'GDK-Proton*-UMU' -o -name 'Proton-CachyOS-*-UMU' -o -name 'proton-EM-*-UMU' -o -name 'dwproton-*-UMU' \) -printf '%f\n' 2>/dev/null | sort -V
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
        umu-batocera/umu-gameid-resolver.py \
        umu-batocera/data/umu-database.csv \
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

integrity_label_i18n() {
    local label
    label="$(runner_integrity_label "$1")"
    case "$label" in
        OK) i18n integrity_ok ;;
        MODIFIE|MODIFIED) i18n integrity_modified ;;
        "NON GERE"|UNMANAGED) i18n integrity_unmanaged ;;
        ABSENT|MISSING) i18n integrity_missing ;;
        *) i18n integrity_unknown ;;
    esac
}

protect_runner() {
    local runners choice r state
    runners="$(installed_runners)"
    if [ -z "$runners" ]; then
        msg "$(i18n create_reference)" "$(i18n export_none)"
        return
    fi

    local opts=()
    while IFS= read -r r; do
        [ -n "$r" ] || continue
        state="$(runner_integrity_label "$CUSTOM_DIR/$r")"
        opts+=("$r" "$state")
    done <<< "$runners"

    if command -v dialog >/dev/null 2>&1; then
        choice="$(dialog --stdout --ok-label "$(i18n accept)" --cancel-label "$(i18n cancel)" --title "$(i18n reference_dialog_title)" \
            --menu "$(i18n reference_dialog_desc)" \
            22 90 14 "${opts[@]}")" || return
    else
        clear; printf '%s\n' "$runners"; echo; printf "%s" "$(i18n runner_prompt)"; read -r choice
    fi
    [ -n "$choice" ] || return
    r="$CUSTOM_DIR/$choice"

    if [ -s "$(runner_manifest_path "$r")" ]; then
        msg "$(i18n reference_locked)" "$(i18n reference_locked_body "$choice")"
        return
    fi

    if ! write_manifest "$r"; then
        msg "$(i18n error)" "$(i18n reference_manifest_failed "$choice")"
        return
    fi
    mkdir -p "$(runner_info_dir "$r")"
    local family runner_name
    runner_name="${choice%-UMU}"
    case "$choice" in
        GE-Proton*-UMU) family="GE-Proton" ;;
        GDK-Proton*-UMU) family="GDK-Proton" ;;
        Proton-CachyOS-*-UMU) family="Proton-CachyOS" ;;
        proton-EM-*-UMU) family="Proton-EM" ;;
        dwproton-*-UMU) family="DW-Proton" ;;
        *) family="Proton" ;;
    esac
    cat > "$(runner_state_path "$r")" <<EOF
RUNNER=$runner_name
RUNNER_FAMILY=$family
UMU_INTEGRATION=$INTEGRATION_VERSION
TOOLBOX_VERSION=$TOOLBOX_VERSION
STATUS=validated
VALIDATED_AT=$(date -Is 2>/dev/null || date)
EOF
    msg "$(i18n reference_created)" "$(i18n reference_created_body "$choice")"
}


show_status() {
    local uv runtime runners rr rr_state
    uv="$(umu_version)"
    if find "$UMU_DIR/home/.local/share/umu" -maxdepth 1 -type d -name 'steamrt*' -print -quit 2>/dev/null | grep -q .; then
        runtime="$(i18n runtime_present)"
    else
        runtime="$(i18n runtime_missing_lazy)"
    fi
    runners=""
    while IFS= read -r rr; do
        [ -n "$rr" ] || continue
        rr_state="$(integrity_label_i18n "$CUSTOM_DIR/$rr")"
        runners="${runners}${rr}  [${rr_state}]\\n"
    done <<< "$(installed_runners)"
    [ -n "$runners" ] || runners="$(i18n none_parenthesized)"

    msg "$(i18n status_title)" "$(i18n status_body "$TOOLBOX_VERSION" "$INTEGRATION_VERSION" "$uv" "$runtime" "$runners" "$LOG_DIR")"
}

install_umu_if_missing() {
    if [ -s "$UMU_RUN" ] && [ -x "$UMU_RUN" ] && umu_run_works; then
        if [ ! -L "$UMU_DIR/umu_run.py" ]; then
            rm -f "$UMU_DIR/umu_run.py"
            ln -s umu-run "$UMU_DIR/umu_run.py"
        fi
        return 0
    fi

    require_net || return 1
    clear
    echo "UMU n'est pas installe correctement."
    echo "Installation automatique de la derniere release officielle..."

    local tmp json tag asset checksum newrun
    tmp="$(mktemp -d "$RUNNER_STAGING_ROOT/umu-install.XXXXXX")"
    json="$tmp/release.json"
    if ! curl -fsSL --max-time 30 "https://api.github.com/repos/$UMU_REPO/releases/latest" -o "$json"; then
        rm -rf "$tmp"
        msg "$(i18n umu_install_impossible)" "$(i18n umu_release_fetch_failed)"
        return 1
    fi

    tag="$(python3 - "$json" <<'PY2'
import json,sys
d=json.load(open(sys.argv[1]))
print(d.get('tag_name',''))
PY2
)"
    asset="$(python3 - "$json" <<'PY2'
import json,sys
d=json.load(open(sys.argv[1]))
for a in d.get('assets',[]):
    u=a.get('browser_download_url','')
    if u.endswith('zipapp.tar'):
        print(u); break
PY2
)"
    checksum="$(python3 - "$json" <<'PY2'
import json,sys
d=json.load(open(sys.argv[1]))
for a in d.get('assets',[]):
    u=a.get('browser_download_url','')
    if u.endswith('umu-run.sha512sum'):
        print(u); break
PY2
)"
    if [ -z "$tag" ] || [ -z "$asset" ]; then
        rm -rf "$tmp"
        msg "$(i18n umu_install_impossible)" "$(i18n umu_zipapp_missing)"
        return 1
    fi
    if ! curl -fL --progress-bar "$asset" -o "$tmp/umu-launcher.tar"; then
        rm -rf "$tmp"
        msg "$(i18n umu_install_failed)" "$(i18n umu_download_failed "$tag")"
        return 1
    fi
    mkdir -p "$tmp/extracted"
    if ! tar -xf "$tmp/umu-launcher.tar" -C "$tmp/extracted"; then
        rm -rf "$tmp"
        msg "$(i18n umu_install_impossible)" "$(i18n umu_extract_version_failed "$tag")"
        return 1
    fi
    newrun="$(find "$tmp/extracted" -type f -name umu-run -print -quit)"
    if [ -z "$newrun" ] || [ ! -s "$newrun" ]; then
        rm -rf "$tmp"
        msg "$(i18n umu_install_impossible)" "$(i18n umu_run_version_missing "$tag")"
        return 1
    fi
    if [ -n "$checksum" ]; then
        if ! curl -fsSL "$checksum" -o "$tmp/umu-run.sha512sum"; then
            rm -rf "$tmp"
            msg "$(i18n umu_install_failed)" "$(i18n umu_checksum_download_failed)"
            return 1
        fi
        cp "$newrun" "$tmp/umu-run"
        if ! (cd "$tmp" && sha512sum -c umu-run.sha512sum); then
            rm -rf "$tmp"
            msg "$(i18n umu_install_failed)" "$(i18n umu_checksum_invalid)"
            return 1
        fi
    fi
    if ! python3 "$(root_bridge)" "$newrun" --version >/dev/null 2>&1; then
        rm -rf "$tmp"
        msg "$(i18n umu_install_impossible)" "$(i18n umu_exec_test_failed)"
        return 1
    fi

    mkdir -p "$UMU_BACKUP"
    if [ -s "$UMU_RUN" ]; then
        cp -a "$UMU_RUN" "$UMU_BACKUP/umu-run-broken-$(date '+%Y%m%d-%H%M%S')"
    fi
    cp -a "$newrun" "$UMU_RUN"
    chmod +x "$UMU_RUN"
    rm -f "$UMU_DIR/umu_run.py"
    ln -s umu-run "$UMU_DIR/umu_run.py"
    printf '%s\n' "$tag" > "$UMU_DIR/.umu_version"
    rm -rf "$tmp"
    log "UMU installed automatically: $tag"
    return 0
}

ensure_umu_for_runner() {
    if install_umu_if_missing; then
        return 0
    fi
    msg "$(i18n runner_install_cancelled)" "$(i18n umu_required_runner)"
    return 1
}

prepare_runtime_for_runner() {
    local runner="$1"
    [ -s "$runner/toolmanifest.vdf" ] || { log "runtime_bootstrap=skipped runner=$runner reason=no-toolmanifest"; return 0; }
    echo "$(i18n steamrt_prepare)"
    HOME="$UMU_DIR/home" XDG_CACHE_HOME="$UMU_DIR/cache" PROTONPATH="$runner" python3 "$(root_bridge)" "$UMU_RUN" --prepare-runtime
    local rc=$?
    if [ "$rc" -ne 0 ]; then
        log "runtime_bootstrap=failed runner=$runner rc=$rc"
        msg "$(i18n steamrt_title)" "$(i18n steamrt_failed)"
        return "$rc"
    fi
    log "runtime_bootstrap=ok runner=$runner"
    return 0
}

fetch_latest_umu_json() {
    curl -fsSL --max-time 20 "https://api.github.com/repos/$UMU_REPO/releases/latest"
}

update_umu() {
    require_net || return

    clear
    echo "$(i18n checking_latest_umu)"
    log "UMU update started"

    local json tag asset checksum tmp oldver
    tmp="$(mktemp -d)"
    json="$tmp/release.json"

    if ! fetch_latest_umu_json > "$json"; then
        rm -rf "$tmp"
        msg "$(i18n umu_error)" "$(i18n umu_release_info_failed)"
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
        msg "$(i18n umu_error)" "$(i18n umu_release_asset_invalid)"
        return
    fi

    oldver="$(umu_version)"
    if printf '%s' "$oldver" | grep -q "^$tag"; then
        rm -rf "$tmp"
        msg "UMU" "$(i18n umu_already_installed "$tag")"
        return
    fi

    if ! yesno "$(i18n umu_update)" "$(i18n umu_update_prompt "$oldver" "$tag" "$tag")"; then
        rm -rf "$tmp"
        return
    fi

    clear
    echo "Telechargement UMU $tag..."
    if ! curl -fL --progress-bar "$asset" -o "$tmp/umu-launcher.tar"; then
        rm -rf "$tmp"
        msg "$(i18n umu_error)" "$(i18n download_failed_simple)"
        return
    fi

    mkdir -p "$tmp/extracted"
    if ! tar -xf "$tmp/umu-launcher.tar" -C "$tmp/extracted"; then
        rm -rf "$tmp"
        msg "$(i18n umu_error)" "$(i18n archive_extract_failed)"
        return
    fi

    local newrun
    newrun="$(find "$tmp/extracted" -type f -name umu-run | head -n1)"
    if [ -z "$newrun" ] || [ ! -s "$newrun" ]; then
        rm -rf "$tmp"
        msg "$(i18n umu_error)" "$(i18n umu_archive_missing)"
        return
    fi

    if [ -n "$checksum" ]; then
        echo "$(i18n verify_sha512)"
        if ! curl -fsSL "$checksum" -o "$tmp/umu-run.sha512sum"; then
            rm -rf "$tmp"
            msg "$(i18n umu_error)" "$(i18n checksum_download_failed)"
            return
        fi
        # The upstream checksum is for a file named umu-run.
        cp "$newrun" "$tmp/umu-run"
        if ! (cd "$tmp" && sha512sum -c umu-run.sha512sum); then
            rm -rf "$tmp"
            msg "$(i18n umu_error)" "$(i18n umu_checksum_invalid)"
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
    msg "$(i18n umu_updated_title)" "$(i18n umu_updated_body "$tag" "$UMU_BACKUP")"
}

rollback_umu() {
    local files count
    files="$(find "$UMU_BACKUP" -maxdepth 1 -type f -name 'umu-run-*' -printf '%f\n' 2>/dev/null | sort -r)"
    if [ -z "$files" ]; then
        msg "Rollback UMU" "$(i18n umu_backup_none)"
        return
    fi

    local opts=()
    while IFS= read -r f; do
        [ -n "$f" ] && opts+=("$f" "$f")
    done <<< "$files"

    local choice
    if command -v dialog >/dev/null 2>&1; then
        choice="$(dialog --stdout --ok-label "$(i18n accept)" --cancel-label "$(i18n cancel)" --title "$(i18n rollback_umu)" --menu "$(i18n rollback_choose)" 20 90 12 "${opts[@]}")" || return
    else
        clear
        echo "$files"
        echo
        printf "%s" "$(i18n rollback_name_prompt)"
        read -r choice
    fi
    [ -n "$choice" ] || return

    if yesno "$(i18n rollback_umu)" "$(i18n rollback_restore "$choice")"; then
        cp -a "$UMU_BACKUP/$choice" "$UMU_RUN"
        chmod +x "$UMU_RUN"
        rm -f "$UMU_DIR/umu_run.py"
        ln -s umu-run "$UMU_DIR/umu_run.py"
        msg "Rollback UMU" "$(i18n umu_backup_restored "$(umu_version)")"
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
fetch_gdk_releases() {
    local out="$1"
    curl -fsSL --max-time 25 \
        "https://api.github.com/repos/$GDK_REPO/releases?per_page=100" -o "$out"
}

build_gdk_menu() {
    local json="$1"
    local menu="$2"
    python3 - "$json" > "$menu" <<'PY_GDK'
import json,sys,re
rels=json.load(open(sys.argv[1],encoding="utf-8"))
rows=[]
for rel in rels if isinstance(rels,list) else []:
    if rel.get("draft") or rel.get("prerelease"):
        continue
    release_name=rel.get("name","") or ""
    tag=rel.get("tag_name","") or ""
    m=re.search(r"GDK-Proton(\d+)-(\d+)",release_name)
    if not m:
        m=re.fullmatch(r"release(\d+)-(\d+)",tag)
    if not m:
        continue
    major,minor=int(m.group(1)),int(m.group(2))
    runner=f"GDK-Proton{major}-{minor}"
    candidates=[]
    for a in rel.get("assets",[]):
        name=a.get("name","")
        if not name.endswith(".tar.gz"):
            continue
        priority=0 if name==f"{runner}.tar.gz" else 1 if name==f"GE-Proton{major}-{minor}.tar.gz" else 9
        if priority < 9:
            digest=a.get("digest") or ""
            sha=digest.split(":",1)[1] if digest.startswith("sha256:") else ""
            candidates.append((priority,a.get("browser_download_url",""),sha))
    if candidates:
        _,url,sha=sorted(candidates)[0]
        rows.append(((major,minor),runner,url,sha))
for _,name,url,sha in sorted(rows,reverse=True):
    print(f"{name}\t{url}\t{sha}")
PY_GDK
}

install_gdk() {
    require_net || return
    local tmp json menu_file
    tmp="$(mktemp -d "$RUNNER_STAGING_ROOT/gdk-list.XXXXXX")"
    json="$tmp/releases.json"
    clear
    echo "$(i18n loading_gdk)"
    if ! fetch_gdk_releases "$json"; then
        rm -rf "$tmp"
        msg "$(i18n runner_error "GDK-Proton")" "$(i18n releases_fetch_failed "GDK-Proton")"
        return
    fi
    menu_file="$tmp/menu.tsv"
    build_gdk_menu "$json" "$menu_file"
    if [ ! -s "$menu_file" ]; then
        rm -rf "$tmp"
        msg "$(i18n runner_error "GDK-Proton")" "$(i18n release_compatible_none "GDK-Proton")"
        return
    fi

    local opts=() name tarurl sha state
    while IFS=$'\t' read -r name tarurl sha; do
        [ -n "$name" ] || continue
        if [ -d "$CUSTOM_DIR/${name}-UMU" ]; then
            state="$(i18n state_installed_protected)"
        else
            state="$(i18n state_available)"
        fi
        opts+=("$name" "$state")
    done < "$menu_file"

    if command -v dialog >/dev/null 2>&1; then
        name="$(dialog --stdout --ok-label "$(i18n accept)" --cancel-label "$(i18n cancel)" --title "$(i18n install_gdk_title)" \
          --menu "$(i18n immutable_menu_desc)"  \
          22 96 14 "${opts[@]}")" || { rm -rf "$tmp"; return; }
    else
        clear
        cut -f1 "$menu_file"
        echo
        printf "%s" "$(i18n version_to_install_prompt)"
        read -r name
    fi
    [ -n "$name" ] || { rm -rf "$tmp"; return; }

    local line target
    line="$(awk -F '\t' -v t="$name" '$1==t {print; exit}' "$menu_file")"
    [ -n "$line" ] || { rm -rf "$tmp"; msg "$(i18n release_invalid)" "$(i18n archive_missing "$name")"; return; }
    tarurl="$(printf '%s' "$line" | cut -f2)"
    sha="$(printf '%s' "$line" | cut -f3)"
    target="$CUSTOM_DIR/${name}-UMU"

    if [ -e "$target" ]; then
        rm -rf "$tmp"
        msg "$(i18n runner_protected)" "$(i18n runner_exists_body "$name-UMU")"
        return
    fi

    if ! yesno "$(i18n install_named "$name-UMU")" \
"Le runner sera construit dans une zone temporaire puis controle avant installation.

Destination :
$target

Continuer ?"; then
        rm -rf "$tmp"
        return
    fi
    if ! ensure_umu_for_runner; then
        rm -rf "$tmp"
        return
    fi

    local stage tarname extracted candidate actual
    stage="$RUNNER_STAGING_ROOT/${name}-UMU.$(date '+%Y%m%d-%H%M%S').$$"
    mkdir -p "$stage/download" "$stage/extracted"
    tarname="$(basename "$tarurl")"

    clear
    echo "$(i18n downloading "$name")"
    if ! curl -fL --progress-bar "$tarurl" -o "$stage/download/$tarname"; then
        rm -rf "$tmp" "$stage"
        msg "$(i18n runner_error "GDK-Proton")" "$(i18n download_failed)"
        return
    fi

    if [ -n "$sha" ]; then
        echo "$(i18n verify_github_sha256)"
        actual="$(sha256sum "$stage/download/$tarname" | awk '{print $1}')"
        if [ "$actual" != "$sha" ]; then
            rm -rf "$tmp" "$stage"
            msg "$(i18n runner_error "GDK-Proton")" "$(i18n checksum_invalid_github)"
            return
        fi
    else
        log "WARNING GitHub asset digest absent for $name"
    fi

    echo "$(i18n extracting_staging)"
    if ! tar -xzf "$stage/download/$tarname" -C "$stage/extracted"; then
        rm -rf "$tmp" "$stage"
        msg "$(i18n runner_error "GDK-Proton")" "$(i18n extract_failed_simple)"
        return
    fi

    extracted="$(find "$stage/extracted" -mindepth 1 -maxdepth 1 -type d | head -n1)"
    if [ -z "$extracted" ] || [ ! -s "$extracted/proton" ] ||
       [ ! -s "$extracted/files/bin/wine" ] ||
       [ ! -s "$extracted/files/bin/wineserver" ]; then
        rm -rf "$tmp" "$stage"
        msg "$(i18n runner_error "GDK-Proton")" "$(i18n runner_unexpected_structure "GDK-Proton")"
        return
    fi

    candidate="$stage/candidate"
    mv "$extracted" "$candidate"
    cp -a "$OVERLAY/." "$candidate/"
    chmod +x "$candidate/proton" "$candidate/bin/wine" "$candidate/bin/wine64" \
        "$candidate/bin/wineserver" "$candidate/umu-batocera/umu-root-runner.py" 2>/dev/null || true

    mkdir -p "$candidate/umu-batocera"
    cat > "$candidate/umu-batocera/runner-info" <<EOF
RUNNER=$name
RUNNER_FAMILY=GDK-Proton
UMU_INTEGRATION=$INTEGRATION_VERSION
TOOLBOX_VERSION=$TOOLBOX_VERSION
INSTALL_SOURCE=github-release
SOURCE_REPO=$GDK_REPO
SOURCE_URL=$tarurl
SOURCE_SHA256=${sha:-unavailable}
STATUS=experimental
INSTALLED_AT=$(date -Is 2>/dev/null || date)
EOF

    if ! write_manifest "$candidate" || ! verify_runner_manifest "$candidate"; then
        rm -rf "$tmp" "$stage"
        msg "$(i18n runner_error "GDK-Proton")" "$(i18n runner_integrity_failed)"
        return
    fi

    if ! prepare_runtime_for_runner "$candidate"; then rm -rf "$tmp" "$stage"; return; fi

    if [ -e "$target" ]; then
        rm -rf "$tmp" "$stage"
        msg "$(i18n conflict)" "$(i18n runner_conflict_body "$target")"
        return
    fi

    echo "$(i18n atomic_install "$name-UMU")"
    if ! mv "$candidate" "$target"; then
        rm -rf "$tmp" "$stage"
        msg "$(i18n runner_error "GDK-Proton")" "$(i18n runner_finalize_failed)"
        return
    fi

    rm -rf "$tmp" "$stage"
    log "Installed immutable ${name}-UMU provider=GDK-Proton"
    msg "$(i18n runner_installed)" "$(i18n runner_installed_body "$name-UMU" "GDK-Proton")"
}

fetch_cachy_releases() {
    local out="$1"
    curl -fsSL --max-time 25 \
        "https://api.github.com/repos/$CACHY_REPO/releases?per_page=100" -o "$out"
}

build_cachy_menu() {
    local json="$1"
    local menu="$2"
    python3 - "$json" > "$menu" <<'PY_CACHY'
import json,sys,re
rels=json.load(open(sys.argv[1],encoding="utf-8"))
rows=[]
for rel in rels if isinstance(rels,list) else []:
    if rel.get("draft") or rel.get("prerelease"):
        continue
    tag=rel.get("tag_name","") or ""
    m=re.fullmatch(r"cachyos-(\d+\.\d+-[0-9]+)-slr",tag)
    if not m:
        continue
    version=m.group(1)
    base=f"proton-cachyos-{version}-slr-x86_64"
    assets={a.get("name",""):a for a in rel.get("assets",[])}
    tar=assets.get(base+".tar.xz")
    chk=assets.get(base+".sha512sum")
    if not tar:
        continue
    rows.append((rel.get("published_at","") or "", version,
                 tar.get("browser_download_url",""),
                 chk.get("browser_download_url","") if chk else ""))
for _,version,url,chk in sorted(rows,reverse=True):
    print(f"Proton-CachyOS-{version}\t{url}\t{chk}")
PY_CACHY
}

install_cachy() {
    require_net || return
    local tmp json menu_file
    tmp="$(mktemp -d "$RUNNER_STAGING_ROOT/cachy-list.XXXXXX")"
    json="$tmp/releases.json"
    clear
    echo "$(i18n loading_cachyos)"
    if ! fetch_cachy_releases "$json"; then
        rm -rf "$tmp"
        msg "$(i18n runner_error "Proton-CachyOS")" "$(i18n releases_fetch_failed "Proton-CachyOS")"
        return
    fi
    menu_file="$tmp/menu.tsv"
    build_cachy_menu "$json" "$menu_file"
    if [ ! -s "$menu_file" ]; then
        rm -rf "$tmp"
        msg "$(i18n runner_error "Proton-CachyOS")" "$(i18n release_slr_none)"
        return
    fi

    local opts=() name tarurl sumurl state
    while IFS=$'\t' read -r name tarurl sumurl; do
        [ -n "$name" ] || continue
        if [ -d "$CUSTOM_DIR/${name}-UMU" ]; then state="$(i18n state_installed_protected)"; else state="$(i18n state_available_slr)"; fi
        opts+=("$name" "$state")
    done < "$menu_file"

    if command -v dialog >/dev/null 2>&1; then
        name="$(dialog --stdout --ok-label "$(i18n accept)" --cancel-label "$(i18n cancel)" --title "$(i18n install_cachyos_title)" \
          --menu "$(i18n cachyos_menu_desc)"  \
          22 100 14 "${opts[@]}")" || { rm -rf "$tmp"; return; }
    else
        clear; cut -f1 "$menu_file"; echo; printf "%s" "$(i18n version_to_install_prompt)"; read -r name
    fi
    [ -n "$name" ] || { rm -rf "$tmp"; return; }

    local line target
    line="$(awk -F '\t' -v t="$name" '$1==t {print; exit}' "$menu_file")"
    [ -n "$line" ] || { rm -rf "$tmp"; msg "$(i18n release_invalid)" "$(i18n archive_missing "$name")"; return; }
    tarurl="$(printf '%s' "$line" | cut -f2)"
    sumurl="$(printf '%s' "$line" | cut -f3)"
    target="$CUSTOM_DIR/${name}-UMU"
    if [ -e "$target" ]; then rm -rf "$tmp"; msg "$(i18n runner_protected)" "$(i18n runner_exists_body "$name-UMU")"; return; fi

    if ! yesno "$(i18n install_named "$name-UMU")" \
"Source : Proton-CachyOS SLR x86_64
Verification : SHA-512 upstream lorsque disponible
Destination :
$target

Aucun runner existant ne sera modifie.

Continuer ?"; then rm -rf "$tmp"; return; fi
    if ! ensure_umu_for_runner; then rm -rf "$tmp"; return; fi

    local stage tarname sumname extracted candidate
    stage="$RUNNER_STAGING_ROOT/${name}-UMU.$(date '+%Y%m%d-%H%M%S').$$"
    mkdir -p "$stage/download" "$stage/extracted"
    tarname="$(basename "$tarurl")"
    clear; echo "$(i18n downloading_build "$name" "SLR x86_64")"
    if ! curl -fL --progress-bar "$tarurl" -o "$stage/download/$tarname"; then rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "Proton-CachyOS")" "$(i18n download_failed)"; return; fi

    if [ -n "$sumurl" ]; then
        sumname="$(basename "$sumurl")"
        echo "$(i18n verify_upstream_sha512)"
        if ! curl -fsSL "$sumurl" -o "$stage/download/$sumname" || ! (cd "$stage/download" && sha512sum -c "$sumname"); then
            rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "Proton-CachyOS")" "$(i18n checksum_invalid_sha512)"; return
        fi
    else
        log "WARNING upstream SHA512 asset absent for $name"
    fi

    echo "$(i18n extracting_staging)"
    if ! tar -xJf "$stage/download/$tarname" -C "$stage/extracted"; then rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "Proton-CachyOS")" "$(i18n extract_xz_failed)"; return; fi
    extracted="$(find "$stage/extracted" -mindepth 1 -maxdepth 1 -type d | head -n1)"
    if [ -z "$extracted" ] || [ ! -s "$extracted/proton" ] || [ ! -s "$extracted/files/bin/wine" ] || [ ! -s "$extracted/files/bin/wineserver" ]; then
        rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "Proton-CachyOS")" "$(i18n runner_unexpected_structure "Proton-CachyOS")"; return
    fi

    candidate="$stage/candidate"
    mv "$extracted" "$candidate"
    cp -a "$OVERLAY/." "$candidate/"
    chmod +x "$candidate/proton" "$candidate/bin/wine" "$candidate/bin/wine64" "$candidate/bin/wineserver" "$candidate/umu-batocera/umu-root-runner.py" 2>/dev/null || true
    mkdir -p "$candidate/umu-batocera"
    cat > "$candidate/umu-batocera/runner-info" <<EOF
RUNNER=$name
RUNNER_FAMILY=Proton-CachyOS
UMU_INTEGRATION=$INTEGRATION_VERSION
TOOLBOX_VERSION=$TOOLBOX_VERSION
INSTALL_SOURCE=github-release-slr-x86_64
SOURCE_REPO=$CACHY_REPO
SOURCE_URL=$tarurl
SOURCE_SHA512_FILE=${sumurl:-unavailable}
STATUS=experimental
INSTALLED_AT=$(date -Is 2>/dev/null || date)
EOF
    if ! write_manifest "$candidate" || ! verify_runner_manifest "$candidate"; then rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "Proton-CachyOS")" "$(i18n runner_integrity_failed)"; return; fi
    if ! prepare_runtime_for_runner "$candidate"; then rm -rf "$tmp" "$stage"; return; fi

    if [ -e "$target" ]; then rm -rf "$tmp" "$stage"; msg "$(i18n conflict)" "$(i18n runner_conflict_body "$target")"; return; fi
    echo "$(i18n atomic_install "$name-UMU")"
    if ! mv "$candidate" "$target"; then rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "Proton-CachyOS")" "$(i18n runner_finalize_failed)"; return; fi
    rm -rf "$tmp" "$stage"
    log "Installed immutable ${name}-UMU provider=Proton-CachyOS asset=SLR-x86_64"
    msg "$(i18n runner_installed)" "$(i18n runner_installed_build_body "$name-UMU" "Proton-CachyOS" "SLR x86_64")"
}

fetch_em_releases() {
    local out="$1"
    curl -fsSL --max-time 25 \
        "https://api.github.com/repos/$EM_REPO/releases?per_page=100" -o "$out"
}

build_em_menu() {
    local json="$1"
    local menu="$2"
    python3 - "$json" > "$menu" <<'PY_EM'
import json,sys,re
rels=json.load(open(sys.argv[1],encoding="utf-8"))
rows=[]
for rel in rels if isinstance(rels,list) else []:
    if rel.get("draft"):
        continue
    tag=rel.get("tag_name","") or ""
    assets={a.get("name",""):a for a in rel.get("assets",[])}
    for name,a in assets.items():
        m=re.fullmatch(r"proton-EM-(.+)\.tar\.xz",name,re.I)
        if not m:
            continue
        version=m.group(1)
        sumname=f"proton-EM-{version}.sha256sum"
        chk=assets.get(sumname)
        url=a.get("browser_download_url","") or ""
        if not url:
            continue
        rows.append((rel.get("published_at","") or "", version, tag, url,
                     chk.get("browser_download_url","") if chk else ""))
for _,version,tag,url,chk in sorted(rows,reverse=True):
    print(f"proton-EM-{version}\t{tag}\t{url}\t{chk}")
PY_EM
}

install_em() {
    local requested="${1:-}" noninteractive="${2:-0}"
    require_net || return
    local tmp json menu_file
    tmp="$(mktemp -d "$RUNNER_STAGING_ROOT/em-list.XXXXXX")"
    json="$tmp/releases.json"
    clear
    echo "$(i18n loading_em)"
    if ! fetch_em_releases "$json"; then
        rm -rf "$tmp"
        msg "$(i18n runner_error "Proton-EM")" "$(i18n releases_fetch_failed "Proton-EM")"
        return
    fi
    menu_file="$tmp/menu.tsv"
    build_em_menu "$json" "$menu_file"
    if [ ! -s "$menu_file" ]; then
        rm -rf "$tmp"
        msg "$(i18n runner_error "Proton-EM")" "$(i18n release_tar_compatible_none "Proton-EM")"
        return
    fi

    local opts=() name tag tarurl sumurl state
    while IFS=$'\t' read -r name tag tarurl sumurl; do
        [ -n "$name" ] || continue
        if [ -d "$CUSTOM_DIR/${name}-UMU" ]; then
            state="$(i18n state_installed_protected)"
        elif [ -z "$sumurl" ]; then
            state="$(i18n state_not_installable_checksum)"
        else
            state="$(i18n state_available) ($tag)"
        fi
        opts+=("$name" "$state")
    done < "$menu_file"

    if [ -n "$requested" ]; then
        name="${requested%-UMU}"
    elif command -v dialog >/dev/null 2>&1; then
        name="$(dialog --stdout --ok-label "$(i18n accept)" --cancel-label "$(i18n cancel)" --title "$(i18n install_em_title)" \
          --menu "$(i18n em_menu_desc)"  \
          24 105 16 "${opts[@]}")" || { rm -rf "$tmp"; return; }
    else
        clear; cut -f1 "$menu_file"; echo; printf "%s" "$(i18n version_to_install_prompt)"; read -r name
    fi
    [ -n "$name" ] || { rm -rf "$tmp"; return; }

    local line target
    line="$(awk -F '\t' -v t="$name" '$1==t {print; exit}' "$menu_file")"
    [ -n "$line" ] || { rm -rf "$tmp"; msg "$(i18n release_invalid)" "$(i18n archive_missing "$name")"; return; }
    tag="$(printf '%s' "$line" | cut -f2)"
    tarurl="$(printf '%s' "$line" | cut -f3)"
    sumurl="$(printf '%s' "$line" | cut -f4)"
    target="$CUSTOM_DIR/${name}-UMU"
    if [ -e "$target" ]; then
        if [ "$noninteractive" = "1" ] && verify_runner_manifest "$target"; then rm -rf "$tmp"; echo "already-installed: $name-UMU"; return 0; fi
        rm -rf "$tmp"; msg "$(i18n runner_protected)" "$(i18n runner_exists_body "$name-UMU")"; return 2
    fi

    if [ -z "$sumurl" ]; then
        rm -rf "$tmp"
        msg "$(i18n proton_not_installable "Proton-EM")" "$(i18n checksum_required_sha256 "$tag")"
        return
    fi
    if [ "$noninteractive" != "1" ] && ! yesno "$(i18n install_named "$name-UMU")" \
"Source : BananaWorks07/Proton ($tag)
Verification : SHA-256 upstream obligatoire
Destination :
$target

Aucun runner existant ne sera modifie.

Continuer ?"; then rm -rf "$tmp"; return; fi
    if ! ensure_umu_for_runner; then rm -rf "$tmp"; return; fi

    local stage tarname sumname extracted candidate
    stage="$RUNNER_STAGING_ROOT/${name}-UMU.$(date '+%Y%m%d-%H%M%S').$$"
    mkdir -p "$stage/download" "$stage/extracted"
    tarname="$(basename "$tarurl")"
    sumname="$(basename "$sumurl")"
    clear; echo "$(i18n downloading "$name")"
    if ! curl -fL --progress-bar "$tarurl" -o "$stage/download/$tarname"; then rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "Proton-EM")" "$(i18n download_failed)"; return; fi

    echo "$(i18n verify_upstream_sha256)"
    if ! curl -fsSL "$sumurl" -o "$stage/download/$sumname"; then
        rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "Proton-EM")" "$(i18n checksum_download_sha256_failed)"; return
    fi
    if ! (cd "$stage/download" && sha256sum -c "$sumname"); then
        # Some upstream checksum files may contain a path/name that differs from the downloaded basename.
        local expected actual
        expected="$(awk 'NF {print $1; exit}' "$stage/download/$sumname")"
        actual="$(sha256sum "$stage/download/$tarname" | awk '{print $1}')"
        if [ -z "$expected" ] || [ "$expected" != "$actual" ]; then
            rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "Proton-EM")" "$(i18n checksum_invalid_sha256)"; return
        fi
    fi

    echo "$(i18n extracting_staging)"
    if ! tar -xJf "$stage/download/$tarname" -C "$stage/extracted"; then rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "Proton-EM")" "$(i18n extract_xz_failed)"; return; fi
    extracted="$(find "$stage/extracted" -mindepth 1 -maxdepth 1 -type d | head -n1)"
    if [ -z "$extracted" ] || [ ! -s "$extracted/proton" ] || [ ! -s "$extracted/files/bin/wine" ] || [ ! -s "$extracted/files/bin/wineserver" ]; then
        rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "Proton-EM")" "$(i18n runner_unexpected_structure "Proton-EM")"; return
    fi

    candidate="$stage/candidate"
    mv "$extracted" "$candidate"
    cp -a "$OVERLAY/." "$candidate/"
    chmod +x "$candidate/proton" "$candidate/bin/wine" "$candidate/bin/wine64" "$candidate/bin/wineserver" "$candidate/umu-batocera/umu-root-runner.py" 2>/dev/null || true
    mkdir -p "$candidate/umu-batocera"
    cat > "$candidate/umu-batocera/runner-info" <<EOF
RUNNER=$name
RUNNER_FAMILY=Proton-EM
UMU_INTEGRATION=$INTEGRATION_VERSION
TOOLBOX_VERSION=$TOOLBOX_VERSION
INSTALL_SOURCE=github-release
SOURCE_REPO=$EM_REPO
SOURCE_TAG=$tag
SOURCE_URL=$tarurl
SOURCE_SHA256_FILE=$sumurl
STATUS=experimental
INSTALLED_AT=$(date -Is 2>/dev/null || date)
EOF
    if ! write_manifest "$candidate" || ! verify_runner_manifest "$candidate"; then rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "Proton-EM")" "$(i18n runner_integrity_failed)"; return; fi
    if ! prepare_runtime_for_runner "$candidate"; then rm -rf "$tmp" "$stage"; return; fi

    if [ -e "$target" ]; then rm -rf "$tmp" "$stage"; msg "$(i18n conflict)" "$(i18n runner_conflict_body "$target")"; return; fi
    echo "$(i18n atomic_install "$name-UMU")"
    if ! mv "$candidate" "$target"; then rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "Proton-EM")" "$(i18n runner_finalize_failed)"; return; fi
    rm -rf "$tmp" "$stage"
    log "Installed immutable ${name}-UMU provider=Proton-EM tag=$tag"
    msg "$(i18n runner_installed)" "$(i18n runner_installed_release_body "$name-UMU" "Proton-EM" "$tag")"
}
fetch_dw_releases() {
    local out="$1"
    curl -fsSL --max-time 25 \
        "https://api.github.com/repos/$DW_REPO/releases?per_page=100" -o "$out"
}

build_dw_menu() {
    local json="$1"
    local menu="$2"
    python3 - "$json" > "$menu" <<'PY_DW'
import json,sys,re
rels=json.load(open(sys.argv[1],encoding="utf-8"))
rows=[]
for rel in rels if isinstance(rels,list) else []:
    if rel.get("draft"):
        continue
    tag=rel.get("tag_name","") or ""
    assets={a.get("name",""):a for a in rel.get("assets",[])}
    for name,a in assets.items():
        m=re.fullmatch(r"dwproton-(.+)-x86_64\.tar\.xz",name,re.I)
        if not m:
            continue
        version=m.group(1)
        sumname=f"dwproton-{version}-x86_64.sha512sum"
        chk=assets.get(sumname)
        url=a.get("browser_download_url","") or ""
        if not url:
            continue
        rows.append((rel.get("published_at","") or "", version, tag, url,
                     chk.get("browser_download_url","") if chk else ""))
def version_key(row):
    version=row[1]
    return tuple(int(x) for x in re.findall(r"\d+", version))
for _,version,tag,url,chk in sorted(rows,key=version_key,reverse=True):
    print(f"dwproton-{version}\t{tag}\t{url}\t{chk}")
PY_DW
}

install_dw() {
    require_net || return
    local tmp json menu_file
    tmp="$(mktemp -d "$RUNNER_STAGING_ROOT/dw-list.XXXXXX")"
    json="$tmp/releases.json"
    clear
    echo "$(i18n loading_dw)"
    if ! fetch_dw_releases "$json"; then
        rm -rf "$tmp"
        msg "$(i18n runner_error "DW-Proton")" "$(i18n releases_fetch_failed "DW-Proton")"
        return
    fi
    menu_file="$tmp/menu.tsv"
    build_dw_menu "$json" "$menu_file"
    if [ ! -s "$menu_file" ]; then
        rm -rf "$tmp"
        msg "$(i18n runner_error "DW-Proton")" "$(i18n release_tar_compatible_none "DW-Proton")"
        return
    fi

    local opts=() name tag tarurl sumurl state
    while IFS=$'\t' read -r name tag tarurl sumurl; do
        [ -n "$name" ] || continue
        if [ -d "$CUSTOM_DIR/${name}-UMU" ]; then
            state="$(i18n state_installed_protected)"
        elif [ -z "$sumurl" ]; then
            state="$(i18n state_not_installable_checksum)"
        else
            state="$(i18n state_available) ($tag)"
        fi
        opts+=("$name" "$state")
    done < "$menu_file"

    if command -v dialog >/dev/null 2>&1; then
        name="$(dialog --stdout --ok-label "$(i18n accept)" --cancel-label "$(i18n cancel)" --title "$(i18n install_dw_title)" \
          --menu "$(i18n dw_menu_desc)" \
          24 105 16 "${opts[@]}")" || { rm -rf "$tmp"; return; }
    else
        clear; cut -f1 "$menu_file"; echo; printf "%s" "$(i18n version_to_install_prompt)"; read -r name
    fi
    [ -n "$name" ] || { rm -rf "$tmp"; return; }

    local line target
    line="$(awk -F '\t' -v t="$name" '$1==t {print; exit}' "$menu_file")"
    [ -n "$line" ] || { rm -rf "$tmp"; msg "$(i18n release_invalid)" "$(i18n archive_missing "$name")"; return; }
    tag="$(printf '%s' "$line" | cut -f2)"
    tarurl="$(printf '%s' "$line" | cut -f3)"
    sumurl="$(printf '%s' "$line" | cut -f4)"
    target="$CUSTOM_DIR/${name}-UMU"
    if [ -e "$target" ]; then rm -rf "$tmp"; msg "$(i18n runner_protected)" "$(i18n runner_exists_body "$name-UMU")"; return; fi

    if [ -z "$sumurl" ]; then
        rm -rf "$tmp"
        msg "$(i18n proton_not_installable "DW-Proton")" "$(i18n checksum_required_sha512 "$tag")"
        return
    fi
    if ! yesno "$(i18n install_named "$name-UMU")" \
"Source : dawn-winery/dwproton-mirror ($tag)
Verification : SHA-512 upstream obligatoire
Destination :
$target

Aucun runner existant ne sera modifie.

Continuer ?"; then rm -rf "$tmp"; return; fi
    if ! ensure_umu_for_runner; then rm -rf "$tmp"; return; fi

    local stage tarname sumname extracted candidate
    stage="$RUNNER_STAGING_ROOT/${name}-UMU.$(date '+%Y%m%d-%H%M%S').$$"
    mkdir -p "$stage/download" "$stage/extracted"
    tarname="$(basename "$tarurl")"
    sumname="$(basename "$sumurl")"
    clear; echo "$(i18n downloading "$name")"
    if ! curl -fL --progress-bar "$tarurl" -o "$stage/download/$tarname"; then rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "DW-Proton")" "$(i18n download_failed)"; return; fi

    echo "$(i18n verify_upstream_sha512)"
    if ! curl -fsSL "$sumurl" -o "$stage/download/$sumname"; then
        rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "DW-Proton")" "$(i18n checksum_download_sha512_failed)"; return
    fi
    if ! (cd "$stage/download" && sha512sum -c "$sumname"); then
        # Some upstream checksum files may contain a path/name that differs from the downloaded basename.
        local expected actual
        expected="$(awk 'NF {print $1; exit}' "$stage/download/$sumname")"
        actual="$(sha512sum "$stage/download/$tarname" | awk '{print $1}')"
        if [ -z "$expected" ] || [ "$expected" != "$actual" ]; then
            rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "DW-Proton")" "$(i18n checksum_invalid_sha512)"; return
        fi
    fi

    echo "$(i18n extracting_staging)"
    if ! tar -xJf "$stage/download/$tarname" -C "$stage/extracted"; then rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "DW-Proton")" "$(i18n extract_xz_failed)"; return; fi
    extracted="$(find "$stage/extracted" -mindepth 1 -maxdepth 1 -type d | head -n1)"
    if [ -z "$extracted" ] || [ ! -s "$extracted/proton" ] || [ ! -s "$extracted/files/bin/wine" ] || [ ! -s "$extracted/files/bin/wineserver" ]; then
        rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "DW-Proton")" "$(i18n runner_unexpected_structure "DW-Proton")"; return
    fi

    candidate="$stage/candidate"
    mv "$extracted" "$candidate"
    cp -a "$OVERLAY/." "$candidate/"
    chmod +x "$candidate/proton" "$candidate/bin/wine" "$candidate/bin/wine64" "$candidate/bin/wineserver" "$candidate/umu-batocera/umu-root-runner.py" 2>/dev/null || true
    mkdir -p "$candidate/umu-batocera"
    cat > "$candidate/umu-batocera/runner-info" <<EOF
RUNNER=$name
RUNNER_FAMILY=DW-Proton
UMU_INTEGRATION=$INTEGRATION_VERSION
TOOLBOX_VERSION=$TOOLBOX_VERSION
INSTALL_SOURCE=github-release
SOURCE_REPO=$DW_REPO
SOURCE_TAG=$tag
SOURCE_URL=$tarurl
SOURCE_SHA512_FILE=$sumurl
STATUS=experimental
INSTALLED_AT=$(date -Is 2>/dev/null || date)
EOF
    if ! write_manifest "$candidate" || ! verify_runner_manifest "$candidate"; then rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "DW-Proton")" "$(i18n runner_integrity_failed)"; return; fi
    if ! prepare_runtime_for_runner "$candidate"; then rm -rf "$tmp" "$stage"; return; fi

    if [ -e "$target" ]; then rm -rf "$tmp" "$stage"; msg "$(i18n conflict)" "$(i18n runner_conflict_body "$target")"; return; fi
    echo "$(i18n atomic_install "$name-UMU")"
    if ! mv "$candidate" "$target"; then rm -rf "$tmp" "$stage"; msg "$(i18n runner_error "DW-Proton")" "$(i18n runner_finalize_failed)"; return; fi
    rm -rf "$tmp" "$stage"
    log "Installed immutable ${name}-UMU provider=DW-Proton tag=$tag"
    msg "$(i18n runner_installed)" "$(i18n runner_installed_release_body "$name-UMU" "DW-Proton" "$tag")"
}

install_runner_menu() {
    while true; do
        local choice
        choice="$(menu_choice "$(i18n install_runner_menu)" \
            "1" "GE-Proton" \
            "2" "GDK-Proton" \
            "3" "Proton-CachyOS (SLR x86_64)" \
            "4" "Proton-EM" \
            "5" "DW-Proton" \
            "0" "$(i18n back)")" || return
        case "$choice" in
            1) install_ge ;;
            2) install_gdk ;;
            3) install_cachy ;;
            4) install_em ;;
            5) install_dw ;;
            0|"") return ;;
        esac
    done
}

install_ge() {
    local requested="${1:-}" noninteractive="${2:-0}"
    require_net || return

    local tmp pages menu_file
    tmp="$(mktemp -d "$RUNNER_STAGING_ROOT/ge-list.XXXXXX")"
    pages="$tmp/releases.pages"

    clear
    echo "$(i18n loading_ge)"
    if ! fetch_ge_releases "$pages"; then
        rm -rf "$tmp"
        msg "$(i18n runner_error "GE-Proton")" "$(i18n releases_fetch_failed "GE-Proton")"
        return
    fi

    menu_file="$tmp/menu.tsv"
    build_ge_menu "$pages" "$menu_file"


    if [ ! -s "$menu_file" ]; then
        rm -rf "$tmp"
        msg "$(i18n runner_error "GE-Proton")" "$(i18n release_compatible_none "x86_64")"
        return
    fi

    local opts=()
    while IFS=$'\t' read -r tag tarurl sumurl; do
        local state
        if [ -d "$CUSTOM_DIR/${tag}-UMU" ]; then
            state="$(i18n state_installed_protected)"
        else
            state="$(i18n state_available)"
        fi
        opts+=("$tag" "$state")
    done < "$menu_file"
    opts+=("MANUAL" "Saisir un tag exact (ex: GE-Proton11-4)")

    local tag
    if [ -n "$requested" ]; then
        tag="${requested%-UMU}"
    elif command -v dialog >/dev/null 2>&1; then
        tag="$(dialog --stdout --ok-label "$(i18n accept)" --cancel-label "$(i18n cancel)" --title "$(i18n install_ge_title)" \
            --menu "$(i18n immutable_menu_desc)"  \
            24 96 17 "${opts[@]}")" || { rm -rf "$tmp"; return; }
    else
        clear
        cut -f1 "$menu_file"
        echo "MANUAL"
        echo
        printf "%s" "$(i18n version_to_install_prompt)"
        read -r tag
    fi
    [ -n "$tag" ] || { rm -rf "$tmp"; return; }

    local line tarurl sumurl tag_json
    if [ -n "$requested" ]; then
        if ! printf '%s' "$tag" | grep -Eq '^GE-Proton[0-9]+-[0-9]+$'; then rm -rf "$tmp"; msg "$(i18n tag_invalid)" "$(i18n ge_tag_expected)"; return 2; fi
        tag_json="$tmp/tag.json"
        if ! fetch_ge_tag "$tag" "$tag_json"; then rm -rf "$tmp"; msg "$(i18n release_not_found)" "$(i18n release_not_found_body "$tag")"; return 3; fi
        line="$(resolve_ge_tag "$tag" "$tag_json")"
    elif [ "$tag" = "MANUAL" ]; then
        tag="$(input_box "Version GE-Proton" "Saisissez le tag exact, par exemple GE-Proton11-4 :" "GE-Proton11-4")" || {
            rm -rf "$tmp"; return;
        }
        if ! printf '%s' "$tag" | grep -Eq '^GE-Proton[0-9]+-[0-9]+$'; then
            rm -rf "$tmp"
            msg "$(i18n tag_invalid)" "$(i18n ge_tag_expected)"
            return
        fi
        tag_json="$tmp/tag.json"
        if ! fetch_ge_tag "$tag" "$tag_json"; then
            rm -rf "$tmp"
            msg "$(i18n release_not_found)" "$(i18n release_not_found_body "$tag")"
            return
        fi
        line="$(resolve_ge_tag "$tag" "$tag_json")"
    else
        line="$(awk -F '\t' -v t="$tag" '$1==t {print; exit}' "$menu_file")"
    fi

    if ge_tag_blocked "$tag"; then
        rm -rf "$tmp"
        msg "$(i18n runner_unsupported)" "$(i18n ge_blocked "$tag")"
        return
    fi

    if [ -z "$line" ]; then
        rm -rf "$tmp"
        msg "$(i18n release_invalid)" "$(i18n archive_x64_missing "$tag")"
        return
    fi

    tarurl="$(printf '%s' "$line" | cut -f2)"
    sumurl="$(printf '%s' "$line" | cut -f3)"
    local target="$CUSTOM_DIR/${tag}-UMU"

    # IMMUTABLE POLICY: never touch an existing runner.
    if [ -e "$target" ]; then
        rm -rf "$tmp"
        if [ "$noninteractive" = "1" ] && verify_runner_manifest "$target"; then rm -rf "$tmp"; echo "already-installed: $tag-UMU"; return 0; fi
        msg "Runner protege" \
"$tag-UMU existe deja.

La Toolbox refuse volontairement toute reinstallation ou mise a niveau sur place.

Pour tester une nouvelle version, installez-la sous son propre numero de version.
Pour remplacer exceptionnellement ce runner, archivez-le d'abord depuis le menu de suppression."
        return
    fi

    if [ "$noninteractive" != "1" ] && ! yesno "$(i18n install_named "$tag-UMU")" \
"Le runner sera construit dans une zone temporaire puis controle avant installation.

Destination finale :
$target

Aucun runner existant ne sera modifie.

Continuer ?"; then
        rm -rf "$tmp"
        return
    fi

    if ! ensure_umu_for_runner; then
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
    echo "$(i18n downloading "$tag")"
    if ! curl -fL --progress-bar "$tarurl" -o "$stage/download/$tarname"; then
        rm -rf "$tmp" "$stage"
        msg "$(i18n runner_error "GE-Proton")" "$(i18n download_failed)"
        return
    fi

    if [ -n "$sumurl" ]; then
        echo "$(i18n verify_upstream_sha512)"
        if ! curl -fsSL "$sumurl" -o "$stage/download/$sumname"; then
            rm -rf "$tmp" "$stage"
            msg "$(i18n runner_error "GE-Proton")" "$(i18n checksum_download_failed)"
            return
        fi
        if ! (cd "$stage/download" && sha512sum -c "$sumname"); then
            rm -rf "$tmp" "$stage"
            msg "$(i18n runner_error "GE-Proton")" "$(i18n checksum_invalid_sha512)"
            return
        fi
    else
        log "WARNING checksum absent for $tag"
    fi

    echo "$(i18n extracting_staging)"
    if ! tar -xzf "$stage/download/$tarname" -C "$stage/extracted"; then
        rm -rf "$tmp" "$stage"
        msg "$(i18n runner_error "GE-Proton")" "$(i18n extraction_failed)"
        return
    fi

    local extracted candidate
    extracted="$(find "$stage/extracted" -mindepth 1 -maxdepth 1 -type d | head -n1)"
    if [ -z "$extracted" ] || [ ! -s "$extracted/proton" ] ||
       [ ! -s "$extracted/files/bin/wine" ] ||
       [ ! -s "$extracted/files/bin/wineserver" ]; then
        rm -rf "$tmp" "$stage"
        msg "$(i18n runner_error "GE-Proton")" "$(i18n runner_unexpected_structure "GE-Proton")"
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
RUNNER=$tag
RUNNER_FAMILY=GE-Proton
GE_PROTON=$tag
UMU_INTEGRATION=$INTEGRATION_VERSION
TOOLBOX_VERSION=$TOOLBOX_VERSION
INSTALL_SOURCE=github-release
SOURCE_URL=$tarurl
STATUS=experimental
INSTALLED_AT=$(date -Is 2>/dev/null || date)
EOF

    if ! write_manifest "$candidate"; then
        rm -rf "$tmp" "$stage"
        msg "$(i18n runner_error "GE-Proton")" "$(i18n integrity_manifest_install_failed)"
        return
    fi

    # Re-check the staged candidate after hashing.
    if ! verify_runner_manifest "$candidate"; then
        rm -rf "$tmp" "$stage"
        msg "$(i18n runner_error "GE-Proton")" "$(i18n runner_changed_staging)"
        return
    fi

    # Atomic same-filesystem install. Refuse if target appeared in the meantime.
    if ! prepare_runtime_for_runner "$candidate"; then rm -rf "$tmp" "$stage"; return; fi

    if [ -e "$target" ]; then
        rm -rf "$tmp" "$stage"
        msg "$(i18n runner_conflict)" "$(i18n install_target_conflict "$target")"
        return
    fi

    echo "$(i18n atomic_install "$tag-UMU")"
    if ! mv "$candidate" "$target"; then
        rm -rf "$tmp" "$stage"
        msg "$(i18n runner_error "GE-Proton")" "$(i18n install_finalize_safe_failed)"
        return
    fi

    rm -rf "$tmp" "$stage"
    log "Installed immutable ${tag}-UMU"
    msg "$(i18n runner_installed_title)" "$(i18n ge_runner_installed_body "$tag-UMU")"
}

list_runners() {
    local out="" r
    while IFS= read -r r; do
        [ -n "$r" ] || continue
        local r_state="$(runner_integrity_label "$CUSTOM_DIR/$r")"
        out="${out}${r}  [$r_state]\n"
    done <<< "$(installed_runners)"
    [ -n "$out" ] || out="(aucun runner UMU installe)"
    msg "$(i18n runner_list_title)" "$out"
}

upgrade_integration() {
    local auto="${1:-0}"
    local runners r base changed=0 skipped="" upgraded="" failed="" tmpstage
    runners="$(installed_runners)"
    [ -n "$runners" ] || { msg "$(i18n integration_title "$INTEGRATION_VERSION")" "$(i18n no_runner_installed)"; return; }

    if umu_process_active; then
        log "integration_upgrade=deferred reason=umu_process_activity"
        msg "$(i18n integration_title "$INTEGRATION_VERSION")" "$(i18n integration_upgrade_deferred)"
        return 2
    fi

    if [ "$auto" != "1" ]; then
        yesno "$(i18n integration_install_title "$INTEGRATION_VERSION")" "$(i18n integration_upgrade_prompt)" || return
    fi

    while IFS= read -r r; do
        [ -n "$r" ] || continue
        base="$CUSTOM_DIR/$r"
        if [ ! -s "$(runner_manifest_path "$base")" ]; then skipped="$skipped$r : NON MANAGE\n"; continue; fi
        if ! verify_runner_manifest "$base"; then skipped="$skipped$r : MODIFIE (refuse)\n"; continue; fi
        if runner_has_runtime_mount "$base"; then skipped="$skipped$r : PROTECTION RUNTIME ACTIVE/ORPHELINE (migration reportee)\n"; continue; fi

        tmpstage="$(mktemp -d "$RUNNER_STAGING_ROOT/integration.XXXXXX")" || { failed="$failed$r : impossible de creer le staging\n"; continue; }
        mkdir -p "$tmpstage/bin" "$tmpstage/umu-batocera/data"
        if ! cp -a "$OVERLAY/bin/wine" "$tmpstage/bin/wine" ||
           ! cp -a "$OVERLAY/bin/wine64" "$tmpstage/bin/wine64" ||
           ! cp -a "$OVERLAY/bin/wineserver" "$tmpstage/bin/wineserver" ||
           ! cp -a "$OVERLAY/umu-batocera/umu-root-runner.py" "$tmpstage/umu-batocera/umu-root-runner.py" ||
           ! cp -a "$OVERLAY/umu-batocera/umu-gameid-resolver.py" "$tmpstage/umu-batocera/umu-gameid-resolver.py" ||
           ! cp -a "$OVERLAY/umu-batocera/data/umu-database.csv" "$tmpstage/umu-batocera/data/umu-database.csv"; then
            failed="$failed$r : preparation des fichiers d'integration impossible\n"; rm -rf "$tmpstage"; continue
        fi
        mkdir -p "$base/umu-batocera/data"
        if ! cp -a "$tmpstage/bin/wine" "$base/bin/wine" ||
           ! cp -a "$tmpstage/bin/wine64" "$base/bin/wine64" ||
           ! cp -a "$tmpstage/bin/wineserver" "$base/bin/wineserver" ||
           ! cp -a "$tmpstage/umu-batocera/umu-root-runner.py" "$base/umu-batocera/umu-root-runner.py" ||
           ! cp -a "$tmpstage/umu-batocera/umu-gameid-resolver.py" "$base/umu-batocera/umu-gameid-resolver.py" ||
           ! cp -a "$tmpstage/umu-batocera/data/umu-database.csv" "$base/umu-batocera/data/umu-database.csv"; then
            failed="$failed$r : ecriture des fichiers d'integration impossible\n"; rm -rf "$tmpstage"; continue
        fi
        rm -rf "$tmpstage"
        chmod +x "$base/bin/wine" "$base/bin/wine64" "$base/bin/wineserver" "$base/umu-batocera/umu-root-runner.py" 2>/dev/null || true
        if ! write_manifest "$base"; then failed="$failed$r : erreur manifest apres migration\n"; continue; fi
        if [ -f "$(runner_state_path "$base")" ]; then
            sed -i "s/^UMU_INTEGRATION=.*/UMU_INTEGRATION=$INTEGRATION_VERSION/" "$(runner_state_path "$base")" 2>/dev/null || true
            sed -i "s/^TOOLBOX_VERSION=.*/TOOLBOX_VERSION=$TOOLBOX_VERSION/" "$(runner_state_path "$base")" 2>/dev/null || true
        fi
        upgraded="$upgraded$r : v$INTEGRATION_VERSION OK\n"; changed=$((changed+1))
    done <<< "$runners"
    log "integration_upgrade=done changed=$changed"
    msg "$(i18n integration_title "$INTEGRATION_VERSION")" "$(i18n integration_upgrade_result "$changed" "${upgraded:-$(i18n none)}" "${skipped:-$(i18n none)}" "${failed:-$(i18n none)}" "$INTEGRATION_VERSION")"
}

scan_prefix_refs() {
    local p out total
    p="$(input_box "Scanner un prefixe" "Chemin du prefixe .wine / wine-bottle / prefixe monte :" "/userdata/roms/windows/")" || return
    [ -n "$p" ] || return
    if [ ! -d "$p" ]; then msg "$(i18n prefix_missing)" "$(i18n prefix_not_dir "$p")"; return; fi
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
        rm -f "$out"; msg "$(i18n prefix_analysis)" "$(i18n prefix_no_symlink)"
        return
    fi
    local report="Prefixe : $p\nLiens absolus vers des runners : $total\n\n"
    while read -r n target; do report="$report$n lien(s) -> $(basename "$target")\n"; done < "$out"
    rm -f "$out"
    msg "$(i18n cross_runner_refs)" "$(i18n cross_runner_report "$report" "$INTEGRATION_VERSION")"
}

umu_process_active() {
    # Process-only check for operations that modify runner files.
    # Stale runtime mounts without a live process are handled separately.
    if pgrep -f '/userdata/system/umu/umu-run|umu-root-runner\.py|/userdata/system/wine/custom/(GE-Proton|GDK-Proton|Proton-CachyOS-|proton-EM-|dwproton-)[^ ]*-UMU/(bin/wine|proton|files/bin/wineserver)' >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

runner_has_runtime_mount() {
    local target="$1"
    findmnt -rn -o TARGET 2>/dev/null | grep -Fxq "$target"
}

orphan_runner_protections() {
    local r target opts report="" found=0
    if umu_process_active; then
        msg "$(i18n runtime_protections)" "$(i18n runtime_active_protected)"
        return 2
    fi
    while IFS= read -r r; do
        [ -n "$r" ] || continue; target="$CUSTOM_DIR/$r"
        if runner_has_runtime_mount "$target"; then
            opts="$(findmnt -rn -o OPTIONS -M "$target" 2>/dev/null || true)"
            case ",$opts," in *,ro,*) report="$report$r [RO]\n"; found=$((found+1)) ;; esac
        fi
    done <<< "$(installed_runners)"
    if [ "$found" -eq 0 ]; then msg "$(i18n runtime_protections)" "$(i18n runtime_no_orphan)"; return 0; fi
    if ! yesno "$(i18n runtime_orphans)" "$(i18n orphan_prompt "$found" "$report")"; then return 0; fi
    if umu_process_active; then msg "$(i18n cleanup_cancelled)" "$(i18n cleanup_cancelled_active)"; return 2; fi
    local cleaned=0 failed=""
    while IFS= read -r r; do
        [ -n "$r" ] || continue; target="$CUSTOM_DIR/$r"
        if runner_has_runtime_mount "$target"; then
            opts="$(findmnt -rn -o OPTIONS -M "$target" 2>/dev/null || true)"
            case ",$opts," in *,ro,*) if umount "$target" 2>>"$LOG"; then cleaned=$((cleaned+1)); log "orphan_runner_protection_unmounted=$target"; else failed="$failed$r\n"; fi ;; esac
        fi
    done <<< "$(installed_runners)"
    msg "$(i18n runtime_protections)" "$(i18n orphan_result "$cleaned" "${failed:-$(i18n none)}")"
}

runtime_protection_status() {
    local report="" r opts active=0
    umu_process_active && active=1 || true
    while IFS= read -r r; do
        [ -n "$r" ] || continue
        if runner_has_runtime_mount "$CUSTOM_DIR/$r"; then
            opts="$(findmnt -rn -o OPTIONS -M "$CUSTOM_DIR/$r" 2>/dev/null || true)"
            case ",$opts," in
                *,ro,*) if [ "$active" -eq 1 ]; then report="$report[RO ACTIF] $r\n"; else report="$report[RO ORPHELIN] $r\n"; fi ;;
                *) report="$report[MONTAGE RW] $r\n" ;;
            esac
        else report="$report[normal] $r (sera protege RO au lancement UMU)\n"; fi
    done <<< "$(installed_runners)"
    if [ "$active" -eq 1 ]; then report="$report\nActivite UMU detectee : les protections RO sont attendues."; else report="$report\nAucune activite UMU detectee. Une ligne [RO ORPHELIN] peut etre nettoyee avec l'option Maintenance dediee."; fi
    msg "$(i18n runtime_protection)" "${report:-$(i18n no_umu_runner)}"
}

verify_install() {
    local report="" r base integ appid runtime codename rdir opts active=0
    umu_process_active && active=1 || true
    if [ -s "$UMU_RUN" ] && umu_run_works; then report="$report[OK] umu-run : $(umu_version)\n"; elif [ -s "$UMU_RUN" ]; then report="$report[KO] umu-run present mais non fonctionnel\n"; else report="$report[KO] umu-run absent\n"; fi
    report="$report\nSteam Runtime :\n"
    local runtime_seen=""
    while IFS= read -r r; do
        [ -n "$r" ] || continue
        base="$CUSTOM_DIR/$r"
        appid="$(sed -n 's/.*"require_tool_appid"[[:space:]]*"*\([0-9][0-9]*\)"*.*/\1/p' "$base/toolmanifest.vdf" 2>/dev/null | head -n1)"
        case "$appid" in
            1391110) codename="soldier"; runtime="steamrt2" ;;
            1628350) codename="sniper"; runtime="steamrt3" ;;
            4183110) codename="steamrt4"; runtime="steamrt4" ;;
            4185400) codename="steamrt4-arm64"; runtime="steamrt4-arm64" ;;
            "") report="$report[INFO] $r : aucun Steam Runtime declare\n"; continue ;;
            *) report="$report[ALERTE] $r : runtime appid $appid non reconnu\n"; continue ;;
        esac
        case " $runtime_seen " in *" $runtime "*) continue ;; esac
        runtime_seen="$runtime_seen $runtime"; rdir="$UMU_DIR/home/.local/share/umu/$runtime"
        if [ -d "$rdir" ] && [ -s "$rdir/mtree.txt.gz" ] && [ -s "$rdir/VERSIONS.txt" ] && [ -d "$rdir/pressure-vessel" ] && [ -e "$rdir/_v2-entry-point" ]; then report="$report[OK] $runtime / $codename present\n"; else report="$report[KO] $runtime / $codename absent ou incomplet\n"; fi
    done <<< "$(installed_runners)"
    [ -n "$runtime_seen" ] || report="$report[INFO] Aucun Steam Runtime requis par les runners installes\n"
    report="$report\nRunners / integrite / protection :\n"
    while IFS= read -r r; do
        [ -n "$r" ] || continue; base="$CUSTOM_DIR/$r"
        if [ ! -s "$base/proton" ] || [ ! -x "$base/bin/wine" ] || [ ! -s "$base/files/bin/wine" ]; then report="$report[KO] $r : incomplet\n"; continue; fi
        integ="$(runner_integrity_label "$base")"
        if runner_has_runtime_mount "$base"; then
            opts="$(findmnt -rn -o OPTIONS -M "$base" 2>/dev/null || true)"
            case ",$opts," in *,ro,*) [ "$active" -eq 1 ] && opts="RO actif" || opts="RO ORPHELIN" ;; *) opts="MONTAGE RW" ;; esac
        else opts="normal"; fi
        case "$integ" in
            "PROTEGE / OK") report="$report[OK] $r : integrite valide | protection $opts\n" ;;
            "MODIFIE") report="$report[ALERTE] $r : FICHIERS CRITIQUES MODIFIES | protection $opts\n" ;;
            *) report="$report[INFO] $r : non manage | protection $opts\n" ;;
        esac
    done <<< "$(installed_runners)"
    report="$report\nPolitique immutable : protection RO automatique pendant les jeux UMU.\nLogs : 20 fichiers max / 30 jours max par categorie.\n$LOG_DIR\n$RUNNER_LOG_DIR"
    msg "$(i18n diagnostic_full)" "$report"
}

export_runner() {
    local runners choice base label export_dir archive tmp_size hash
    runners="$(installed_runners)"
    if [ -z "$runners" ]; then
        msg "$(i18n export_runner_title)" "$(i18n export_none)"
        return
    fi

    local opts=() r
    while IFS= read -r r; do
        [ -n "$r" ] || continue
        opts+=("$r" "$(integrity_label_i18n "$CUSTOM_DIR/$r")")
    done <<< "$runners"

    if command -v dialog >/dev/null 2>&1; then
        choice="$(dialog --stdout --ok-label "$(i18n accept)" --cancel-label "$(i18n cancel)" --title "$(i18n export_runner_title)" \
            --menu "$(i18n export_select_desc)" \
            22 100 14 "${opts[@]}")" || return
    else
        clear
        echo "==== $(i18n export_runner_title) ===="
        echo
        while IFS= read -r r; do
            [ -n "$r" ] && printf '%s  [%s]\n' "$r" "$(runner_integrity_label "$CUSTOM_DIR/$r")"
        done <<< "$runners"
        echo
        printf "%s" "$(i18n runner_to_export_prompt)"
        read -r choice
    fi
    [ -n "$choice" ] || return

    base="$CUSTOM_DIR/$choice"
    [ -d "$base" ] || { msg "$(i18n error)" "$(i18n runner_not_found "$choice")"; return; }
    label="$(runner_integrity_label "$base")"

    if [ "$label" = "MODIFIE" ]; then
        msg "$(i18n export_refused)" "$(i18n export_modified_body "$choice")"
        return
    fi

    if [ "$label" = "NON MANAGE" ]; then
        msg "$(i18n export_refused)" "$(i18n export_unmanaged_body "$choice")"
        return
    fi

    if ! verify_runner_manifest "$base"; then
        msg "$(i18n export_refused)" "$(i18n export_integrity_failed "$choice")"
        return
    fi

    if ! command -v xz >/dev/null 2>&1; then
        msg "$(i18n export_unavailable)" "$(i18n xz_missing)"
        return
    fi

    export_dir="/userdata/system/umu/exports"
    mkdir -p "$export_dir"
    archive="$export_dir/${choice}-$(date '+%Y%m%d-%H%M%S').tar.xz"

    if ! yesno "$(i18n confirm_export)" "$(i18n export_confirm_body "$choice" "$label" "$archive")"; then
        return
    fi

    log "Export start: $choice -> $archive"
    if tar -C "$CUSTOM_DIR" -cJf "$archive" -- "$choice" >>"$LOG" 2>&1; then
        if ! xz -t "$archive" >>"$LOG" 2>&1; then
            rm -f "$archive"
            msg "$(i18n export_failed)" "$(i18n export_xz_test_failed)"
            return
        fi
        tmp_size="$(du -h "$archive" 2>/dev/null | awk '{print $1}')"
        hash="$(sha256sum "$archive" | awk '{print $1}')"
        printf '%s  %s\n' "$hash" "$(basename "$archive")" > "${archive}.sha256"
        log "Export OK: $archive sha256=$hash"
        msg "$(i18n export_complete)" "$(i18n export_complete_body "$archive" "${tmp_size:-?}" "$hash" "$(basename "$archive")")"
    else
        rm -f "$archive" "${archive}.sha256"
        msg "$(i18n export_failed)" "$(i18n export_tar_failed "$LOG")"
    fi
}
export_shareable_package() {
    local runners choice base label export_dir pkgroot pkgname work runner_archive archive hash size manifest appid runtime_variant runtime_src runtime_archive runtime_size
    runners="$(installed_runners)"
    if [ -z "$runners" ]; then
        msg "$(i18n package_title)" "$(i18n package_none)"
        return
    fi

    local opts=() r
    while IFS= read -r r; do
        [ -n "$r" ] || continue
        opts+=("$r" "$(integrity_label_i18n "$CUSTOM_DIR/$r")")
    done <<< "$runners"

    if command -v dialog >/dev/null 2>&1; then
        choice="$(dialog --stdout --ok-label "$(i18n accept)" --cancel-label "$(i18n cancel)" --title "$(i18n package_create_title)" \
            --menu "$(i18n package_select_desc)" \
            22 105 14 "${opts[@]}")" || return
    else
        clear
        echo "==== $(i18n package_create_title) ===="
        echo
        while IFS= read -r r; do
            [ -n "$r" ] && printf '%s  [%s]\n' "$r" "$(runner_integrity_label "$CUSTOM_DIR/$r")"
        done <<< "$runners"
        echo
        printf "%s" "$(i18n runner_to_share_prompt)"
        read -r choice
    fi
    [ -n "$choice" ] || return

    base="$CUSTOM_DIR/$choice"
    [ -d "$base" ] || { msg "$(i18n error)" "$(i18n runner_not_found "$choice")"; return; }
    label="$(runner_integrity_label "$base")"
    if [ "$label" != "PROTEGE / OK" ] || ! verify_runner_manifest "$base"; then
        msg "$(i18n export_refused)" "$(i18n package_unhealthy "$choice")"
        return
    fi
    manifest="$base/toolmanifest.vdf"
    [ -s "$manifest" ] || { msg "$(i18n export_refused)" "$(i18n package_manifest_missing)"; return; }
    appid="$(grep -Eo '"require_tool_appid"[[:space:]]*"?[0-9]+"?' "$manifest" 2>/dev/null | head -n1 | grep -Eo '[0-9]+' || true)"
    case "$appid" in
        1391110) runtime_variant="steamrt2" ;;
        1628350) runtime_variant="steamrt3" ;;
        4183110) runtime_variant="steamrt4" ;;
        4185400) runtime_variant="steamrt4-arm64" ;;
        *) msg "$(i18n export_refused)" "$(i18n package_runtime_appid_bad "${appid:-$(i18n none)}")"; return ;;
    esac
    runtime_src="$UMU_DIR/home/.local/share/umu/$runtime_variant"
    if [ ! -d "$runtime_src" ] || [ ! -s "$runtime_src/_v2-entry-point" ] || [ ! -s "$runtime_src/VERSIONS.txt" ] || [ ! -s "$runtime_src/mtree.txt.gz" ] || [ ! -d "$runtime_src/pressure-vessel" ]; then
        msg "$(i18n export_refused)" "$(i18n package_runtime_missing "$runtime_variant")"
        return
    fi
    runtime_size="$(du -sh "$runtime_src" 2>/dev/null | awk 'NR==1{print $1}')"
    command -v xz >/dev/null 2>&1 || { msg "$(i18n export_unavailable)" "$(i18n xz_missing)"; return; }

    export_dir="/userdata/system/umu/exports"
    mkdir -p "$export_dir"
    pkgname="${choice}-Batocera-UMU-Package-$(date '+%Y%m%d-%H%M%S')"
    work="$(mktemp -d)"
    pkgroot="$work/$pkgname"
    mkdir -p "$pkgroot/payload"
    runner_archive="$pkgroot/payload/${choice}.tar.xz"
    runtime_archive="$pkgroot/payload/${runtime_variant}.tar.xz"

    yesno "$(i18n confirm_package)" "$(i18n package_confirm_body "$choice" "$label" "$runtime_variant" "$appid" "$runtime_size")" || { rm -rf "$work"; return; }

    clear
    echo "$(i18n compressing_runner)"
    if ! tar -C "$CUSTOM_DIR" -cJf "$runner_archive" -- "$choice"; then
        rm -rf "$work"; msg "$(i18n error)" "$(i18n runner_compress_failed)"; return
    fi
    xz -t "$runner_archive" || { rm -rf "$work"; msg "$(i18n error)" "$(i18n runner_xz_failed)"; return; }
    echo "$(i18n compressing_runtime)"
    if ! tar -C "$(dirname "$runtime_src")" -cJf "$runtime_archive" -- "$runtime_variant"; then rm -rf "$work"; msg "$(i18n error)" "$(i18n runtime_compress_failed)"; return; fi
    xz -t "$runtime_archive" || { rm -rf "$work"; msg "$(i18n error)" "$(i18n runtime_xz_failed)"; return; }
    if [ ! -s "$UMU_RUN" ]; then
        rm -rf "$work"
        msg "$(i18n export_refused)" "$(i18n package_umu_missing)"
        return
    fi
    cp -a "$UMU_RUN" "$pkgroot/payload/umu-run"
    (cd "$pkgroot/payload" && sha256sum * > SHA256SUMS)

    cat > "$pkgroot/install.sh" <<'EOS'
#!/bin/bash
set -e
BASE="$(cd "$(dirname "$0")" && pwd)"
PAYLOAD="$BASE/payload"
CUSTOM="/userdata/system/wine/custom"
UMU="/userdata/system/umu"
[ "$(id -u)" -eq 0 ] || { echo "ERREUR: lancez cet installateur en root."; exit 1; }
RUNARCH="$(find "$PAYLOAD" -maxdepth 1 -type f \( -name 'GE-Proton*-UMU.tar.xz' -o -name 'GDK-Proton*-UMU.tar.xz' -o -name 'Proton-CachyOS-*-UMU.tar.xz' -o -name 'proton-EM-*-UMU.tar.xz' -o -name 'dwproton-*-UMU.tar.xz' \) | head -n1)"
[ -n "$RUNARCH" ] || { echo "ERREUR: payload runner absent."; exit 1; }
RUNNER="$(basename "$RUNARCH" .tar.xz)"
RTARCH="$(find "$PAYLOAD" -maxdepth 1 -type f \( -name 'steamrt2.tar.xz' -o -name 'steamrt3.tar.xz' -o -name 'steamrt4.tar.xz' -o -name 'steamrt4-arm64.tar.xz' \) | head -n1)"
[ -n "$RTARCH" ] || { echo "ERREUR: Steam Runtime absent du package."; exit 1; }
RUNTIME="$(basename "$RTARCH" .tar.xz)"
(cd "$PAYLOAD" && sha256sum -c SHA256SUMS)
mkdir -p "$CUSTOM" "$UMU/backups" "$UMU/home/.local/share/umu"

[ -s "$PAYLOAD/umu-run" ] || { echo "ERREUR: umu-run absent du package."; exit 1; }
if [ ! -s "$UMU/umu-run" ]; then
  cp -a "$PAYLOAD/umu-run" "$UMU/umu-run"
  chmod +x "$UMU/umu-run"
  rm -f "$UMU/umu_run.py"
  ln -s umu-run "$UMU/umu_run.py"
else
  echo "UMU deja present : conservation de l'installation existante."
fi
STAGE="$(mktemp -d /userdata/system/umu/package-staging.XXXXXX)"
trap 'rm -rf "$STAGE"' EXIT
echo "Preparation et verification de $RUNNER..."
tar -xJf "$RUNARCH" -C "$STAGE"
mkdir -p "$STAGE/runtime"
tar -xJf "$RTARCH" -C "$STAGE/runtime"
RT="$STAGE/runtime/$RUNTIME"
[ -s "$RT/_v2-entry-point" ] && [ -s "$RT/VERSIONS.txt" ] && [ -s "$RT/mtree.txt.gz" ] && [ -d "$RT/pressure-vessel" ] || { echo "ERREUR: Steam Runtime invalide."; exit 1; }
MAN="$STAGE/$RUNNER/umu-batocera/integrity.sha256"
[ -f "$MAN" ] || { echo "ERREUR: manifest absent apres extraction."; exit 1; }
(cd "$STAGE/$RUNNER" && sha256sum -c "$MAN")
echo "Installation de $RUNNER..."
rm -rf --one-file-system "$CUSTOM/$RUNNER"
mv "$STAGE/$RUNNER" "$CUSTOM/$RUNNER"
rm -rf "$UMU/home/.local/share/umu/$RUNTIME"
mv "$RT" "$UMU/home/.local/share/umu/$RUNTIME"
rm -f "$UMU/home/.local/share/umu/$RUNTIME/umu"
ln -s _v2-entry-point "$UMU/home/.local/share/umu/$RUNTIME/umu"
printf 'ok\n' > "$UMU/home/.local/share/umu/$RUNTIME/.installed.ok"
rm -rf "$STAGE"; trap - EXIT
echo
echo "Installation terminee. Le Steam Runtime $RUNTIME fourni dans le package est installe."
echo "Le runner est disponible dans /userdata/system/wine/custom/$RUNNER"
EOS
    chmod +x "$pkgroot/install.sh"

    cat > "$pkgroot/README.txt" <<EOF
BATOCERA - PACKAGE PARTAGEABLE $choice
========================================

Ce package installe le runner $choice et son Steam Runtime requis ($runtime_variant).
Il est destine a une Batocera qui possede ou non deja UMU.

INSTALLATION
------------
1. Copier ce dossier/package dans /userdata/system/ (via \\\\BATOCERA\\share\\system par exemple).
2. Ouvrir un terminal ou SSH en root.
3. Entrer dans le dossier extrait puis lancer :
     chmod +x install.sh
     ./install.sh
4. Une connexion Internet est necessaire uniquement si umu-run n'est pas deja installe.
5. Le Steam Runtime exact requis par ce runner ($runtime_variant) est inclus dans le package et installe hors ligne.
6. Le runner apparait ensuite dans les choix Wine/Windows de Batocera sous le nom : $choice

COMPATIBILITE
-------------
- jeux .pc
- prefixes .wine
- jeux .wsquashfs
- wine-bottles / sauvegardes externes

IMPORTANT
---------
Le runner contient l'integration Batocera/UMU v$INTEGRATION_VERSION et son manifest d'integrite.
Les runners UMU sont proteges en lecture seule pendant les lancements UMU afin qu'un prefixe reutilise avec plusieurs versions de Proton ne puisse pas modifier un autre runner.
Les runners standards Batocera (Proton, Wine-TKG, Kron4ek...) ne sont pas remplaces par ce package.

Pour gerer, mettre a jour, diagnostiquer et exporter des runners, utilisez UMU Runner Toolbox v0.9.0 ou ulterieure.
EOF

    (cd "$pkgroot" && sha256sum install.sh README.txt payload/* > SHA256SUMS)
    archive="$export_dir/${pkgname}.tar.xz"
    echo "$(i18n creating_final_package)"
    if tar -C "$work" -cJf "$archive" -- "$pkgname" && xz -t "$archive"; then
        hash="$(sha256sum "$archive" | awk '{print $1}')"; printf '%s  %s\n' "$hash" "$(basename "$archive")" > "${archive}.sha256"; size="$(du -h "$archive" | awk '{print $1}')"
        rm -rf "$work"
        msg "$(i18n package_complete)" "$(i18n package_created "$archive" "$size" "$hash")"
    else
        rm -rf "$work" "$archive" "${archive}.sha256"; msg "$(i18n export_failed)" "$(i18n package_final_failed)"
    fi
}


delete_installed_runner() {
    local runners choice r
    if umu_uninstall_active; then
        msg "$(i18n deletion_refused)" "$(i18n delete_active)"
        return
    fi
    runners="$(installed_runners)"
    if [ -z "$runners" ]; then
        msg "$(i18n delete_runner_title)" "$(i18n delete_none)"
        return
    fi
    local opts=()
    while IFS= read -r r; do
        [ -n "$r" ] && opts+=("$r" "$(integrity_label_i18n "$CUSTOM_DIR/$r")")
    done <<< "$runners"
    if command -v dialog >/dev/null 2>&1; then
        choice="$(dialog --stdout --ok-label "$(i18n accept)" --cancel-label "$(i18n cancel)" --title "$(i18n delete_runner_title)" --menu \
            "$(i18n delete_select_desc)" \
            26 100 15 "${opts[@]}")" || return
    else
        clear
        printf '%s\n' "$runners"
        echo
        printf "%s" "$(i18n runner_to_delete_prompt)"
        read -r choice
    fi
    [ -n "$choice" ] || return
    if [ ! -d "$CUSTOM_DIR/$choice" ]; then
        msg "$(i18n error)" "$(i18n runner_not_found "$choice")"
        return
    fi
    yesno "$(i18n confirm_delete)" "$(i18n delete_confirm_body "$CUSTOM_DIR/$choice")" || return
    if rm -rf --one-file-system "$CUSTOM_DIR/$choice"; then
        log "Runner deleted by user: $choice"
        msg "$(i18n runner_deleted)" "$(i18n runner_deleted_body "$choice")"
    else
        msg "$(i18n error)" "$(i18n delete_failed "$choice" "$LOG")"
    fi
}

export_menu() {
    while true; do
        local choice
        choice="$(menu_choice "$(i18n export_menu_title)" \
            "1" "$(i18n export_menu_package)" \
            "2" "$(i18n export_menu_runner)" \
            "0" "$(i18n back)")" || return
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
    if command -v findmnt >/dev/null 2>&1 && findmnt -rn 2>/dev/null | grep -Eq '/userdata/system/umu/(merged-prefixes|materialized-prefixes|gameviews|test7-prefixes|test7-gameviews)/'; then
        return 0
    fi
    return 1
}

clean_umu_runtime_data() {
    local compat="$UMU_DIR/compatdata"
    local merged="$UMU_DIR/merged-prefixes"
    local materialized="$UMU_DIR/materialized-prefixes"
    local gameviews="$UMU_DIR/gameviews"
    local legacy_prefixes="$UMU_DIR/test7-prefixes"
    local legacy_gameviews="$UMU_DIR/test7-gameviews"
    local mesa="$UMU_DIR/cache/mesa_shader_cache"
    local radv="$UMU_DIR/cache/radv_builtin_shaders"
    local cb mb mat_b gv_b legacy_p_b legacy_g_b mesa_b radv_b total_game total_gpu total_game_h total_gpu_h report

    if umu_game_active; then
        msg "$(i18n cleanup_refused)" "$(i18n cleanup_active)"
        return
    fi

    mkdir -p "$compat" "$merged" "$materialized" "$gameviews"
    cb="$(dir_bytes "$compat")"
    mb="$(dir_bytes "$merged")"
    mat_b="$(dir_bytes "$materialized")"
    gv_b="$(dir_bytes "$gameviews")"
    legacy_p_b="$(dir_bytes "$legacy_prefixes")"
    legacy_g_b="$(dir_bytes "$legacy_gameviews")"
    total_game=$((cb + mb + mat_b + gv_b + legacy_p_b + legacy_g_b))
    total_game_h="${total_game_h}"
    mesa_b="$(dir_bytes "$mesa")"
    radv_b="$(dir_bytes "$radv")"
    total_gpu=$((mesa_b + radv_b))
    total_gpu_h="${total_gpu_h}"

    report="Donnees runtime UMU :\n- compatdata : $(human_bytes "$cb")\n- merged-prefixes : $(human_bytes "$mb")\n- materialized-prefixes : $(human_bytes "$mat_b")\n- gameviews : $(human_bytes "$gv_b")\n- anciens TEST7 : $(human_bytes "$((legacy_p_b + legacy_g_b))")\n- total : ${total_game_h}\n\nCaches graphiques facultatifs :\n- Mesa shader cache : $(human_bytes "$mesa_b")\n- RADV builtin shaders : $(human_bytes "$radv_b")\n- total : ${total_gpu_h}\n\nSont toujours conserves : umu-run, steamrt4, home/.local/share/umu, protonfixes/umu-protonfixes, sauvegardes UMU et runners."
    msg "$(i18n cleanup_analysis)" "$report"

    if [ "$total_game" -gt 0 ]; then
        if yesno "$(i18n cleanup_runtime_title)" "$(i18n cleanup_runtime_prompt "$compat" "$merged" "$materialized" "$gameviews" "${total_game_h}")"; then
            if umu_game_active; then
                msg "$(i18n cleanup_cancelled)" "$(i18n cleanup_race)"
                return
            fi
            clear_dir_contents "$compat"
            clear_dir_contents "$merged"
            clear_dir_contents "$materialized"
            clear_dir_contents "$gameviews"
            clear_dir_contents "$legacy_prefixes"
            clear_dir_contents "$legacy_gameviews"
            log "umu_cleanup_game_data=done bytes_before=$total_game"
            msg "$(i18n cleanup_done)" "$(i18n cleanup_done_body "${total_game_h}")"
        fi
    else
        msg "$(i18n cleanup_done)" "$(i18n cleanup_empty)"
    fi

    # Shader caches are reconstructible but deliberately opt-in: deleting them
    # can cause shader recompilation/stutter on subsequent launches.
    if [ "$total_gpu" -gt 0 ] && yesno "$(i18n gpu_cache_title)" "$(i18n gpu_cache_prompt "${total_gpu_h}")"; then
        if umu_game_active; then
            msg "$(i18n gpu_cache_kept)" "$(i18n gpu_cache_active)"
            return
        fi
        clear_dir_contents "$mesa"
        clear_dir_contents "$radv"
        log "umu_cleanup_gpu_cache=done bytes_before=$total_gpu"
        msg "$(i18n gpu_cache_done)" "$(i18n gpu_cache_done_body "${total_gpu_h}")"
    fi
}

toolbox_files_cleanup() {
    rm -rf -- "$ROOT" "$OLD_ROOT"
    rm -f -- "$PORT" "$PORT_KEYS"
}

umu_uninstall_active() {
    if pgrep -f '/userdata/system/umu/umu-run|umu-root-runner\.py' >/dev/null 2>&1; then
        return 0
    fi
    if pgrep -f "$CUSTOM_DIR/\(GE-Proton\|GDK-Proton\|Proton-CachyOS-\|proton-EM-\|dwproton-\).*[-]UMU" >/dev/null 2>&1; then
        return 0
    fi
    if command -v findmnt >/dev/null 2>&1 && findmnt -rn 2>/dev/null | grep -Eq '/userdata/system/umu/(merged-prefixes|materialized-prefixes|gameviews|test7-prefixes|test7-gameviews|compatdata)|/userdata/system/wine/custom/(GE-Proton|GDK-Proton|Proton-CachyOS-|proton-EM-|dwproton-)[^ ]*-UMU'; then
        return 0
    fi
    return 1
}

uninstall_toolbox_only() {
    if umu_game_active; then
        msg "$(i18n uninstall_refused)" "$(i18n uninstall_active)"
        return
    fi
    yesno "$(i18n uninstall_toolbox_title)" "$(i18n uninstall_toolbox_prompt)" || return
    if false; then
        return
    fi
    toolbox_files_cleanup
    log "toolbox_uninstall=toolbox_only"
    msg "$(i18n uninstall_toolbox_done)" "$(i18n uninstall_toolbox_done_body)"
}

uninstall_umu_and_runners() {
    local runners
    runners="$(installed_runners)"
    if umu_uninstall_active; then
        msg "$(i18n uninstall_refused)" "$(i18n uninstall_active_runner)"
        return
    fi
    if [ -n "$runners" ]; then
        runners="$(printf '%s\n' "$runners" | sed 's/^/- /')"
    else
        runners="$(i18n no_umu_runner_detected)"
    fi
    yesno "$(i18n uninstall_umu_title)" "$(i18n uninstall_umu_prompt "$runners")" || return
    if false; then
        return
    fi
    if umu_uninstall_active; then
        msg "$(i18n uninstall_cancelled)" "$(i18n uninstall_race)"
        return
    fi
    while IFS= read -r r; do
        [ -n "$r" ] || continue
        rm -rf --one-file-system "$CUSTOM_DIR/$r"
    done <<< "$(installed_runners)"
    if [ -d "$UMU_DIR" ]; then
        find "$UMU_DIR" -mindepth 1 -maxdepth 1 ! -name "$(basename "$ROOT")" -exec rm -rf -- {} +
    fi
    mkdir -p "$UMU_DIR"
    log "umu_uninstall=umu_and_runners"
    msg "$(i18n uninstall_umu_done)" "$(i18n uninstall_umu_done_body)"
}

uninstall_everything() {
    if umu_uninstall_active; then
        msg "$(i18n uninstall_refused)" "$(i18n delete_active)"
        return
    fi
    yesno "$(i18n uninstall_complete_title)" "$(i18n uninstall_complete_prompt)" || return
    if false; then
        return
    fi
    if umu_uninstall_active; then
        msg "$(i18n uninstall_cancelled)" "$(i18n uninstall_race)"
        return
    fi
    while IFS= read -r r; do
        [ -n "$r" ] || continue
        rm -rf --one-file-system "$CUSTOM_DIR/$r"
    done <<< "$(installed_runners)"
    toolbox_files_cleanup
    if [ -d "$UMU_DIR" ]; then
        rm -rf -- "$UMU_DIR"
    fi
    log "uninstall=complete"
    msg "$(i18n uninstall_complete_title)" "$(i18n uninstall_complete_done)"
}

uninstall_menu() {
    while true; do
        local choice
        choice="$(menu_choice "$(i18n uninstall_menu)" \
            "1" "$(i18n uninstall_toolbox_only)" \
            "2" "$(i18n uninstall_umu_all)" \
            "3" "$(i18n uninstall_all)" \
            "0" "$(i18n back)")" || return
        case "$choice" in
            1) uninstall_toolbox_only ;;
            2) uninstall_umu_and_runners ;;
            3) uninstall_everything ;;
            0|"") return ;;
        esac
    done
}


clean_umu_logs() {
    local tb rb total f tb_h rb_h total_h
    if umu_game_active; then
        msg "$(i18n log_cleanup_refused)" "$(i18n log_cleanup_active)"
        return
    fi
    mkdir -p "$LOG_DIR" "$RUNNER_LOG_DIR"
    tb="$(dir_bytes "$LOG_DIR")"
    rb="$(dir_bytes "$RUNNER_LOG_DIR")"
    total=$((tb + rb))
    if [ "$total" -le 0 ]; then
        msg "$(i18n log_cleanup)" "$(i18n log_cleanup_empty)"
        return
    fi
    tb_h="$(human_bytes "$tb")"
    rb_h="$(human_bytes "$rb")"
    total_h="$(human_bytes "$total")"
    yesno "$(i18n clean_logs_title)" "$(i18n clean_logs_prompt "$tb_h" "$rb_h" "$total_h")" || return
    find "$RUNNER_LOG_DIR" -mindepth 1 -maxdepth 1 -type f -name "*.log" -delete 2>/dev/null || true
    while IFS= read -r f; do
        [ -n "$f" ] || continue
        [ "$f" = "$LOG" ] && continue
        rm -f -- "$f" 2>/dev/null || true
    done < <(find "$LOG_DIR" -mindepth 1 -maxdepth 1 -type f -name "*.log" -print 2>/dev/null)
    log "umu_logs_cleanup=done bytes_before=$total"
    msg "$(i18n log_cleanup)" "$(i18n log_cleanup_done "$total_h")"
}

associate_game() {
    local helper="$ROOT/umu-gameid-manager.py" title="$1" path="$2" tab candidates choice selected idx cscore ctitle gameid cstores store storeopts
    tab="$(printf '\t')"
    candidates="$(mktemp "$RUNNER_STAGING_ROOT/gameid-candidates.XXXXXX")" || return
    python3 "$helper" candidates --title "$title" --limit 12 > "$candidates" || { rm -f "$candidates"; msg "$(i18n error)" "$(i18n gameid_search_failed)"; return; }
    [ -s "$candidates" ] || { rm -f "$candidates"; msg "$(i18n gameid_no_match)" "$(i18n gameid_no_candidate "$title")"; return; }
    if command -v dialog >/dev/null 2>&1; then
        local copts=() ci
        while IFS="$tab" read -r ci cscore ctitle gameid cstores; do
            [ -n "$ci" ] && [ -n "$ctitle" ] || continue
            copts+=("$ci" "$ctitle  [$gameid]  score=$cscore")
        done < "$candidates"
        choice="$(dialog --stdout --ok-label "$(i18n accept)" --cancel-label "$(i18n cancel)" --title "$(i18n matches_title)" --menu "$(i18n matches_prompt "$title")" 32 110 18 "${copts[@]}")" || { rm -f "$candidates"; return; }
    else
        cat "$candidates"; printf "\n%s" "$(i18n number_prompt)"; read -r choice
    fi
    selected="$(awk -F "$tab" -v n="$choice" '$1==n {print; exit}' "$candidates")"; rm -f "$candidates"
    [ -n "$selected" ] || return
    IFS="$tab" read -r idx cscore ctitle gameid cstores <<< "$selected"
    store=""
    if [ -n "$cstores" ]; then
        IFS=',' read -r -a storeopts <<< "$cstores"
        if [ "${#storeopts[@]}" -eq 1 ]; then store="${storeopts[0]}"
        elif command -v dialog >/dev/null 2>&1; then
            local sopts=() st
            for st in "${storeopts[@]}"; do [ -n "$st" ] && sopts+=("$st" "$st"); done
            store="$(dialog --stdout --ok-label "$(i18n accept)" --cancel-label "$(i18n cancel)" --title "$(i18n choose_store)" --menu "$(i18n choose_store_prompt "$ctitle" "$gameid")" 24 100 14 "${sopts[@]}")" || return
        else printf "%b" "$(i18n stores_console_prompt "$cstores")"; read -r store; fi
    fi
    if python3 "$helper" set --path "$path" --title "$title" --gameid "$gameid" --store "$store"; then
        log "gameid_override=set title=$title matched_title=$ctitle score=$cscore gameid=$gameid store=$store"
        msg "$(i18n association_saved)" "$(i18n gameid_saved_body "$title" "$ctitle" "$cscore" "$gameid" "$store")"
    else msg "$(i18n error)" "$(i18n association_save_failed)"; fi
}

global_game_scan() {
    local helper="$ROOT/umu-gameid-manager.py" scan tab kind total clear ambiguous none overrides list choice selected idx status score title path best gid remaining
    tab="$(printf '\t')"; scan="$(mktemp "$RUNNER_STAGING_ROOT/gameid-scan.XXXXXX")" || return
    clear; echo "$(i18n scanning_windows_games)"
    python3 "$helper" scan > "$scan" || { rm -f "$scan"; msg "$(i18n scan_failed)" "$(i18n scan_failed_body)"; return; }
    IFS="$tab" read -r kind total clear ambiguous none overrides < "$scan"
    list="$(mktemp "$RUNNER_STAGING_ROOT/gameid-review.XXXXXX")" || { rm -f "$scan"; return; }
    tail -n +2 "$scan" > "$list"; rm -f "$scan"
    if [ "$ambiguous" -eq 0 ]; then
        rm -f "$list"; msg "$(i18n global_scan)" "$(i18n gameid_scan_summary "$total" "$clear" "$none" "$overrides")"; return
    fi

    # Keep the scan results for this review session. After a manual association,
    # remove only the processed item and return directly to the remaining list.
    while true; do
        remaining="$(awk -F "$tab" '$1=="ITEM" && $3=="AMBIGUOUS" {n++} END{print n+0}' "$list")"
        if [ "$remaining" -eq 0 ]; then
            rm -f "$list"
            msg "$(i18n global_scan)" "$(i18n gameid_scan_done)"
            return
        fi

        if command -v dialog >/dev/null 2>&1; then
            local opts=() rec ri rs rscore rt rp rb rg label
            while IFS="$tab" read -r rec ri rs rscore rt rp rb rg; do
                [ "$rec" = "ITEM" ] || continue
                [ "$rs" = "AMBIGUOUS" ] || continue
                label="$(i18n ambiguous_label "$rt" "$rb" "$rg" "$rscore")"
                opts+=("$ri" "$label")
            done < "$list"
            choice="$(dialog --stdout --ok-label "$(i18n accept)" --cancel-label "$(i18n cancel)" --title "$(i18n global_scan_title)" --menu "$(i18n global_scan_review_prompt "$total" "$clear" "$remaining" "$ambiguous" "$none" "$overrides")" 34 120 20 "${opts[@]}")" || { rm -f "$list"; return; }
        else
            awk -F "$tab" '$1=="ITEM" && $3=="AMBIGUOUS"' "$list"
            printf "\n%s" "$(i18n number_prompt)"; read -r choice
            [ -n "$choice" ] || { rm -f "$list"; return; }
        fi

        selected="$(awk -F "$tab" -v n="$choice" '$1=="ITEM" && $2==n && $3=="AMBIGUOUS" {print; exit}' "$list")"
        [ -n "$selected" ] || continue
        IFS="$tab" read -r kind idx status score title path best gid <<< "$selected"

        associate_game "$title" "$path"

        # Only remove the item when an override for this exact game path now exists.
        # This also handles a cancelled candidate/store dialog safely: the item stays.
        if python3 "$helper" list 2>/dev/null | awk -F "$tab" -v p="$path" '$5==p {found=1} END{exit(found?0:1)}'; then
            tmp_review="$(mktemp "$RUNNER_STAGING_ROOT/gameid-review-next.XXXXXX")" || { rm -f "$list"; return; }
            awk -F "$tab" -v n="$idx" '!( $1=="ITEM" && $2==n )' "$list" > "$tmp_review"
            mv "$tmp_review" "$list"
            overrides=$((overrides + 1))
        fi
    done
}

gameid_override_menu() {
    local helper="$ROOT/umu-gameid-manager.py" action selected idx title path list choice tab
    tab="$(printf '\t')"
    [ -s "$helper" ] || { msg "$(i18n game_compat_title)" "$(i18n gameid_manager_missing "$helper")"; return; }
    while true; do
        action="$(menu_choice "$(i18n game_compat_title)" "1" "$(i18n gameid_menu_scan)" "2" "$(i18n gameid_menu_associate)" "3" "$(i18n gameid_menu_show)" "4" "$(i18n gameid_menu_delete)" "0" "$(i18n back)")" || return
        case "$action" in
          1) global_game_scan ;;
          2)
            [ -s "$WINDOWS_GAMELIST" ] || { msg "$(i18n error)" "$(i18n gamelist_missing "$WINDOWS_GAMELIST")"; continue; }
            list="$(mktemp "$RUNNER_STAGING_ROOT/gameids.XXXXXX")" || continue
            python3 "$helper" games > "$list" || { rm -f "$list"; msg "$(i18n error)" "$(i18n gamelist_read_failed)"; continue; }
            if command -v dialog >/dev/null 2>&1; then
                local opts=() i n gp
                while IFS="$tab" read -r i n gp; do [ -n "$i" ] && [ -n "$n" ] && opts+=("$i" "$n"); done < "$list"
                choice="$(dialog --stdout --ok-label "$(i18n accept)" --cancel-label "$(i18n cancel)" --title "$(i18n choose_windows_game)" --menu "$(i18n choose_windows_game_prompt)" 30 100 20 "${opts[@]}")" || { rm -f "$list"; continue; }
            else cat "$list"; printf "\n%s" "$(i18n number_prompt)"; read -r choice; fi
            selected="$(awk -F "$tab" -v n="$choice" '$1==n {print; exit}' "$list")"; rm -f "$list"
            [ -n "$selected" ] || continue
            IFS="$tab" read -r idx title path <<< "$selected"
            associate_game "$title" "$path" ;;
          3)
            list="$(python3 "$helper" list 2>/dev/null)"; [ -n "$list" ] || list="$(i18n manual_none)"; msg "$(i18n manual_associations)" "$list" ;;
          4)
            list="$(python3 "$helper" list 2>/dev/null)"; [ -n "$list" ] || { msg "$(i18n manual_associations)" "$(i18n manual_none)"; continue; }
            if command -v dialog >/dev/null 2>&1; then
                local dopts=() di dt dg ds dp label
                while IFS="$tab" read -r di dt dg ds dp; do [ -n "$di" ] || continue; label="$dt [$dg / $ds]"; dopts+=("$di" "$label"); done <<< "$list"
                choice="$(dialog --stdout --ok-label "$(i18n accept)" --cancel-label "$(i18n cancel)" --title "$(i18n delete_association)" --menu "$(i18n delete_association_prompt)" 28 105 18 "${dopts[@]}")" || continue
            else printf "%s\n" "$list"; printf "\n%s" "$(i18n number_prompt)"; read -r choice; fi
            if python3 "$helper" delete --index "$choice"; then log "gameid_override=deleted index=$choice"; msg "$(i18n association_deleted)" "$(i18n association_deleted_body)"; else msg "$(i18n error)" "$(i18n delete_impossible)"; fi ;;
          0|"") return ;;
        esac
    done
}

maintenance_menu() {
    while true; do
        local choice
        choice="$(menu_choice "$(i18n maintenance_title)" \
            "1" "$(i18n diagnostic_full)" \
            "2" "$(i18n repair_integration)" \
            "3" "$(i18n clean_runtime)" \
            "4" "$(i18n clean_logs)" \
            "5" "$(i18n clean_ro)" \
            "6" "$(i18n uninstall)" \
            "0" "Retour")" || return
        case "$choice" in
            1) verify_install ;;
            2) upgrade_integration ;;
            3) clean_umu_runtime_data ;;
            4) clean_umu_logs ;;
            5) orphan_runner_protections ;;
            6) uninstall_menu ;;
            0|"") return ;;
        esac
    done
}

update_toolbox() {
    local startup_confirmed="${1:-0}"
    require_net || return
    local base latest_url tag latest asset checksum download_base tmp pkg root newroot backup ts

    base="https://github.com/$TOOLBOX_REPO"
    latest_url="$(curl -fsSL -o /dev/null -w '%{url_effective}' "$base/releases/latest")" || {
        msg "$(i18n toolbox_update_title)" "$(i18n update_latest_failed)"
        return
    }
    tag="$(basename "$latest_url")"
    case "$tag" in
        v*) latest="${tag#v}" ;;
        *) msg "$(i18n toolbox_update_title)" "$(i18n update_bad_tag "$tag")"; return ;;
    esac

    if [ "$latest" = "$TOOLBOX_VERSION" ]; then
        msg "$(i18n toolbox_update_title)" "$(i18n update_current "$TOOLBOX_VERSION")"
        return
    fi
    if ! python3 - "$TOOLBOX_VERSION" "$latest" <<'PYVER'
import sys
def v(s): return tuple(int(x) for x in s.split('.'))
sys.exit(0 if v(sys.argv[2]) > v(sys.argv[1]) else 1)
PYVER
    then
        msg "$(i18n toolbox_update_title)" "$(i18n update_not_newer "$tag" "$TOOLBOX_VERSION")"
        return
    fi

    asset="UMU-Runner-Toolbox-$tag.zip"
    checksum="$asset.sha256"
    download_base="$base/releases/download/$tag"

    if [ "$startup_confirmed" != "1" ]; then
        if ! yesno "$(i18n toolbox_update_title)" "$(i18n update_confirm "$TOOLBOX_VERSION" "$latest" "$UMU_BACKUP")"; then return; fi
    fi

    tmp="$(mktemp -d "$RUNNER_STAGING_ROOT/toolbox-update.XXXXXX")" || { msg "$(i18n toolbox_update_title)" "$(i18n update_tmp_failed)"; return; }
    if ! curl -fL --retry 3 --connect-timeout 15 -o "$tmp/$asset" "$download_base/$asset"; then rm -rf "$tmp"; msg "$(i18n toolbox_update_title)" "$(i18n update_download_failed)"; return; fi
    if ! curl -fL --retry 3 --connect-timeout 15 -o "$tmp/$checksum" "$download_base/$checksum"; then rm -rf "$tmp"; msg "$(i18n toolbox_update_title)" "$(i18n update_checksum_missing "$tag")"; return; fi
    if ! (cd "$tmp" && sha256sum -c "$checksum"); then rm -rf "$tmp"; msg "$(i18n toolbox_update_title)" "$(i18n update_checksum_failed)"; return; fi
    if ! unzip -q "$tmp/$asset" -d "$tmp/extracted"; then rm -rf "$tmp"; msg "$(i18n toolbox_update_title)" "$(i18n update_extract_failed)"; return; fi

    pkg="$(find "$tmp/extracted" -mindepth 1 -maxdepth 1 -type d | head -n1)"
    root="$pkg/toolbox"
    if [ -z "$pkg" ] || [ ! -s "$root/umu-toolbox.sh" ] || [ ! -s "$root/VERSION" ]; then rm -rf "$tmp"; msg "$(i18n toolbox_update_title)" "$(i18n update_structure_invalid)"; return; fi
    if [ "$(tr -d '\r\n[:space:]' < "$root/VERSION")" != "$latest" ]; then rm -rf "$tmp"; msg "$(i18n toolbox_update_title)" "$(i18n update_version_mismatch)"; return; fi
    if ! bash -n "$root/umu-toolbox.sh"; then rm -rf "$tmp"; msg "$(i18n toolbox_update_title)" "$(i18n update_script_invalid)"; return; fi
    if [ -s "$root/umu-gameid-resolver.py" ] && ! python3 -m py_compile "$root/umu-gameid-resolver.py" 2>/dev/null; then rm -rf "$tmp"; msg "$(i18n toolbox_update_title)" "$(i18n update_resolver_invalid)"; return; fi
    if [ -s "$root/umu-gameid-manager.py" ] && ! python3 -m py_compile "$root/umu-gameid-manager.py" 2>/dev/null; then rm -rf "$tmp"; msg "$(i18n toolbox_update_title)" "$(i18n update_manager_invalid)"; return; fi

    newroot="$UMU_DIR/.toolbox-update.$$"; rm -rf "$newroot"
    cp -a "$root" "$newroot" || { rm -rf "$tmp" "$newroot"; msg "$(i18n toolbox_update_title)" "$(i18n update_prepare_failed)"; return; }
    if [ -d "$ROOT/config" ]; then rm -rf "$newroot/config"; cp -a "$ROOT/config" "$newroot/config" || { rm -rf "$tmp" "$newroot"; msg "$(i18n toolbox_update_title)" "$(i18n update_config_failed)"; return; }; fi

    ts="$(date '+%Y%m%d-%H%M%S')"; backup="$UMU_BACKUP/toolbox-v$TOOLBOX_VERSION-$ts"; mkdir -p "$UMU_BACKUP"
    if ! mv "$ROOT" "$backup"; then rm -rf "$tmp" "$newroot"; msg "$(i18n toolbox_update_title)" "$(i18n update_backup_failed)"; return; fi
    if ! mv "$newroot" "$ROOT"; then mv "$backup" "$ROOT" 2>/dev/null || true; rm -rf "$tmp" "$newroot"; msg "$(i18n toolbox_update_title)" "$(i18n update_replace_failed)"; return; fi

    chmod +x "$ROOT/umu-toolbox.sh" 2>/dev/null || true
    rm -rf "$tmp"
    if command -v dialog >/dev/null 2>&1; then
        dialog --ok-label "$(i18n accept)" --title "$(i18n toolbox_update_title)" --msgbox "$(i18n update_restart_complete "$TOOLBOX_VERSION" "$latest" "$backup")" 18 90
    fi
    exec env UMU_TOOLBOX_POST_UPDATE=1 UMU_TOOLBOX_PREVIOUS_VERSION="$TOOLBOX_VERSION" "$ROOT/umu-toolbox.sh"
}

sync_pad2key_mapping() {
    local src="$ROOT/ports/UMU Runner Toolbox.sh.keys"
    [ -s "$src" ] || return 0
    mkdir -p "$PORTS"
    if [ ! -s "$PORT_KEYS" ] || ! cmp -s "$src" "$PORT_KEYS"; then
        cp -f "$src" "$PORT_KEYS" 2>/dev/null || return 1
        log "pad2key_mapping=synchronized target=$PORT_KEYS"
    fi
    return 0
}

post_update_integration() {
    [ "${UMU_TOOLBOX_POST_UPDATE:-0}" = "1" ] || return 0
    local previous="${UMU_TOOLBOX_PREVIOUS_VERSION:-inconnue}"
    unset UMU_TOOLBOX_POST_UPDATE UMU_TOOLBOX_PREVIOUS_VERSION
    msg "$(i18n toolbox_update_title)" "$(i18n update_done "$previous" "$TOOLBOX_VERSION")"
    upgrade_integration 1
}

language_menu() {
    local choice
    choice="$(menu_choice "$(ui language_title)" \
        "fr" "Francais" \
        "en" "English" \
        "0" "$(ui back)")" || return
    case "$choice" in
        fr)
            TOOLBOX_LANGUAGE="fr"
            save_language
            load_i18n
            msg "$(ui language_changed)" "$(ui language_changed_text)"
            ;;
        en)
            TOOLBOX_LANGUAGE="en"
            save_language
            load_i18n
            msg "$(ui language_changed)" "$(ui language_changed_text)"
            ;;
        0|"") return ;;
    esac
}

latest_stable_toolbox_version() {
    local latest_url tag
    latest_url="$(curl -fsSL --connect-timeout 5 --max-time 10 -o /dev/null -w '%{url_effective}' "https://github.com/$TOOLBOX_REPO/releases/latest" 2>/dev/null)" || return 1
    tag="$(basename "$latest_url")"
    case "$tag" in v*) printf '%s' "${tag#v}" ;; *) return 1 ;; esac
}

version_is_newer() {
    python3 - "$1" "$2" <<'PYVER'
import sys
def v(s):
    try:
        return tuple(int(x) for x in s.split('.'))
    except ValueError:
        return ()
cur, new = v(sys.argv[1]), v(sys.argv[2])
sys.exit(0 if cur and new and new > cur else 1)
PYVER
}

startup_update_check() {
    [ "${UMU_TOOLBOX_SKIP_UPDATE_CHECK:-0}" = "1" ] && return 0
    local latest=""
    latest="$(latest_stable_toolbox_version)" || {
        log "startup_update_check=offline_or_unavailable"
        return 0
    }
    [ -n "$latest" ] || return 0
    if ! version_is_newer "$TOOLBOX_VERSION" "$latest"; then
        log "startup_update_check=no_update installed=$TOOLBOX_VERSION latest=$latest"
        return 0
    fi
    log "startup_update_check=available installed=$TOOLBOX_VERSION latest=$latest"
    if yesno "$(ui update_available)" "$(ui installed_version) : $TOOLBOX_VERSION\n$(ui new_version) : $latest\n\n$(ui update_question)"; then
        update_toolbox 1
    fi
}

documentation_about() {
    msg "$(i18n documentation_title)" "$(i18n documentation_body "$TOOLBOX_VERSION" "$ROOT" "$LOG_DIR")"
}

main_menu() {
    while true; do
        local choice
        choice="$(menu_choice "UMU Runner Toolbox v$TOOLBOX_VERSION" \
            "1" "$(ui install_runner)" \
            "2" "$(ui delete_runner)" \
            "3" "$(ui export_runner)" \
            "4" "$(ui game_compat)" \
            "5" "$(ui maintenance)" \
            "6" "$(ui update_toolbox)" \
            "7" "$(ui documentation)" \
            "8" "$(ui language)" \
            "0" "$(ui quit)")" || exit 0
        case "$choice" in
            1) install_runner_menu ;;
            2) delete_installed_runner ;;
            3) export_menu ;;
            4) gameid_override_menu ;;
            5) maintenance_menu ;;
            6) update_toolbox ;;
            7) documentation_about ;;
            8) language_menu ;;
            0|"") clear; exit 0 ;;
        esac
    done
}
install_runner_cli() {
    local requested="${1:-}" base target
    [ -n "$requested" ] || { echo "Usage: $0 --install-runner <runner>" >&2; return 64; }
    base="${requested%-UMU}"
    target="$CUSTOM_DIR/${base}-UMU"
    if [ -e "$target" ]; then
        if verify_runner_manifest "$target"; then echo "already-installed: ${base}-UMU"; return 0; fi
        echo "existing-runner-invalid: ${base}-UMU" >&2
        return 66
    fi
    case "$base" in
        GE-Proton[0-9]*-[0-9]*) install_ge "$base" 1 ;;
        proton-EM-*) install_em "$base" 1 ;;
        *) i18n cli_runner_unsupported "$requested" >&2; echo >&2; return 65 ;;
    esac
}
if [ "${1:-}" = "--install-runner" ]; then
    install_runner_cli "${2:-}"
    exit $?
fi

sync_pad2key_mapping || log "pad2key_mapping=sync_failed"
if [ "${UMU_TOOLBOX_INSTALL_SYNC:-0}" = "1" ]; then
    unset UMU_TOOLBOX_INSTALL_SYNC
    if [ -n "$(installed_runners)" ]; then
        upgrade_integration 1
    else
        msg "$(i18n first_install_title)" "$(i18n first_install_body)"
    fi
    exit 0
fi
post_update_integration
startup_update_check
main_menu
