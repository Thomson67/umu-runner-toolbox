#!/bin/bash
set -eu

REPO="Thomson67/umu-runner-toolbox"
BASE_URL="https://github.com/${REPO}"
TMPDIR=""

cleanup() {
    [ -n "${TMPDIR:-}" ] && rm -rf "$TMPDIR"
}
trap cleanup EXIT INT TERM

fail() {
    echo "ERREUR: $*" >&2
    exit 1
}

for cmd in curl unzip sha256sum sed basename; do
    command -v "$cmd" >/dev/null 2>&1 || fail "commande requise absente: $cmd"
done

[ "$(id -u)" -eq 0 ] || fail "l'installation doit etre lancee en root (Batocera)."

CHANNEL="${UMU_INSTALL_CHANNEL:-stable}"

if [ "$CHANNEL" = "test" ]; then
    echo "== UMU Runner Toolbox - installation branche test =="
    TMPDIR="$(mktemp -d /tmp/umu-runner-toolbox-test.XXXXXX)" || fail "creation du dossier temporaire impossible."
    ARCHIVE="$TMPDIR/test.zip"

    echo "Telechargement de la branche test..."
    curl -fL --retry 3 --connect-timeout 15         -o "$ARCHIVE"         "https://github.com/${REPO}/archive/refs/heads/test.zip" ||         fail "telechargement de la branche test impossible."

    unzip -q "$ARCHIVE" -d "$TMPDIR" || fail "extraction de la branche test impossible."
    TEST_INSTALLER="$(find "$TMPDIR" -mindepth 2 -maxdepth 3 -type f -path '*/packaging/install.sh' | head -n 1)"
    [ -n "$TEST_INSTALLER" ] || fail "packaging/install.sh introuvable dans la branche test."
    chmod +x "$TEST_INSTALLER"
    "$TEST_INSTALLER"
    echo "Installation de la branche test terminee."
    exit 0
fi

echo "== UMU Runner Toolbox - installation depuis GitHub =="
echo "Recherche de la derniere version stable..."

LATEST_URL="$(curl -fsSL -o /dev/null -w '%{url_effective}' "${BASE_URL}/releases/latest")" || \
    fail "impossible de determiner la derniere release GitHub."
TAG="$(basename "$LATEST_URL")"

case "$TAG" in
    v*) ;;
    *) fail "tag de release inattendu: $TAG" ;;
esac

ASSET="UMU-Runner-Toolbox-${TAG}.zip"
CHECKSUM="${ASSET}.sha256"
DOWNLOAD_BASE="${BASE_URL}/releases/download/${TAG}"

TMPDIR="$(mktemp -d /tmp/umu-runner-toolbox.XXXXXX)" || fail "creation du dossier temporaire impossible."
cd "$TMPDIR"

echo "Version detectee : $TAG"
echo "Telechargement de $ASSET..."
curl -fL --retry 3 --connect-timeout 15 -o "$ASSET" "${DOWNLOAD_BASE}/${ASSET}" || \
    fail "telechargement du package impossible."

echo "Telechargement de la somme SHA-256..."
curl -fL --retry 3 --connect-timeout 15 -o "$CHECKSUM" "${DOWNLOAD_BASE}/${CHECKSUM}" || \
    fail "checksum absent pour $TAG. Installation annulee."

echo "Verification SHA-256..."
sha256sum -c "$CHECKSUM" || fail "verification SHA-256 echouee. Installation annulee."

echo "Extraction..."
unzip -q "$ASSET" || fail "extraction du package impossible."

INSTALLER="$(find "$TMPDIR" -mindepth 2 -maxdepth 2 -type f -name install.sh | head -n 1)"
[ -n "$INSTALLER" ] || fail "install.sh introuvable dans le package."
chmod +x "$INSTALLER"

echo "Lancement de l'installateur $TAG..."
"$INSTALLER"

echo "Installation GitHub terminee."
