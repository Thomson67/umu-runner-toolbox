#!/usr/bin/env python3

import argparse
import ast
import csv
import hashlib
import gzip
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_GAMELIST = Path("/userdata/roms/windows/gamelist.xml")
DEFAULT_DB = Path("/userdata/system/umu/toolbox/data/umu-database.csv")
DEFAULT_PROTONFIXES = Path("/userdata/system/wine/custom/GE-Proton10-25-UMU/protonfixes")
DEFAULT_OVERRIDES = Path("/userdata/system/umu/toolbox/config/gameid-overrides.csv")

def normalize_title(value: str) -> str:
    value = value or ""
    value = value.replace("™", "").replace("®", "").replace("©", "")
    for char in ("’", "‘", "‚", "‛", "`", "´"): value = value.replace(char, "'")
    for char in ('“', '”', '„', '«', '»'): value = value.replace(char, '"')
    for char in ("‐", "-", "‒", "–", "—", "―"): value = value.replace(char, "-")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.casefold().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def canonical_game_path(value: str) -> str:
    value = (value or "").strip().replace("\\", "/")
    if value.startswith("./"): value = value[2:]
    return value.rstrip("/")

def load_gamelist(path: Path):
    root = ET.parse(path).getroot()
    games = []
    for game in root.findall("game"):
        game_path, title = game.findtext("path"), game.findtext("name")
        if game_path and title:
            games.append({"path": canonical_game_path(game_path), "title": title.strip()})
    return games

def find_batocera_game(game_path: str, games):
    requested = canonical_game_path(game_path)
    requested_name = Path(requested).name
    exact = [g for g in games if g["path"] == requested]
    if len(exact) == 1: return exact[0], "PATH_EXACT"
    if len(exact) > 1: raise RuntimeError(f"Plusieurs entrées gamelist utilisent le chemin {requested!r}")
    basename_matches = [g for g in games if Path(g["path"]).name == requested_name]
    if len(basename_matches) == 1: return basename_matches[0], "BASENAME_EXACT"
    if len(basename_matches) > 1: raise RuntimeError(f"Plusieurs entrées gamelist utilisent le fichier {requested_name!r}")
    container_exts = (".wsquashfs", ".wine")
    def split_container(name):
        folded = name.casefold()
        for ext in container_exts:
            if folded.endswith(ext): return name[:-len(ext)], ext
        return None, None
    requested_stem, requested_ext = split_container(requested_name)
    if requested_ext is not None:
        matches=[]
        for g in games:
            stem, ext = split_container(Path(g["path"]).name)
            if ext is not None and stem == requested_stem: matches.append(g)
        if len(matches) == 1: return matches[0], "CONTAINER_EQUIVALENT"
        if len(matches) > 1: raise RuntimeError(f"Plusieurs entrées gamelist correspondent au même jeu .wine/.wsquashfs pour {requested_name!r}")
    raise RuntimeError(f"Aucune entrée gamelist trouvée pour {game_path!r}")

def detect_columns(fieldnames):
    lookup={n.strip().casefold():n for n in (fieldnames or [])}
    def get(*candidates):
        for c in candidates:
            if c.casefold() in lookup: return lookup[c.casefold()]
    title_col=get("TITLE","title","name"); store_col=get("STORE","store"); id_col=get("UMU_ID","umu_id","GAMEID","gameid")
    if not title_col or not store_col or not id_col: raise RuntimeError(f"Colonnes UMU introuvables. Colonnes présentes : {fieldnames}")
    return title_col,store_col,id_col

def load_umu_database(path: Path):
    rows=[]
    if not path.is_file() and path.suffix == ".csv":
        gz_path=Path(str(path)+".gz")
        if gz_path.is_file(): path=gz_path
    opener=gzip.open if path.suffix == ".gz" else path.open
    with opener("rt" if path.suffix == ".gz" else "r", encoding="utf-8-sig", newline="") as handle:
        reader=csv.DictReader(handle)
        title_col,store_col,id_col=detect_columns(reader.fieldnames)
        for row in reader:
            title=(row.get(title_col) or "").strip(); store=(row.get(store_col) or "").strip().casefold(); gameid=(row.get(id_col) or "").strip()
            if not title or not gameid: continue
            if store in ("","null","none","umu"): store="none"
            rows.append({"title":title,"normalized":normalize_title(title),"store":store,"gameid":gameid})
    return rows

def find_database_matches(title: str, rows):
    exact=[r for r in rows if r["title"].casefold() == title.casefold()]
    if exact: return exact,"EXACT"
    key=normalize_title(title); normalized=[r for r in rows if r["normalized"] == key]
    return (normalized,"NORMALIZED") if normalized else ([],"NO_MATCH")

def steam_fix_title(path: Path):
    try:
        module=ast.parse(path.read_text(encoding="utf-8"))
        title=(ast.get_docstring(module, clean=True) or "").splitlines()[0].strip()
    except (OSError, UnicodeError, SyntaxError):
        return ""
    title=re.sub(r"^game\s+fix\s+for\s+", "", title, flags=re.IGNORECASE).strip()
    return title

def find_steam_gamefix_match(title: str, protonfixes: Path):
    root=protonfixes / "gamefixes-steam"
    if not root.is_dir(): return None, "STEAM_FIX_DIR_MISSING"
    key=normalize_title(title); matches=[]
    for path in root.glob("*.py"):
        if not path.stem.isdigit(): continue
        fix_title=steam_fix_title(path)
        if fix_title and normalize_title(fix_title) == key:
            matches.append((path.stem,fix_title))
    unique={appid:fix_title for appid,fix_title in matches}
    if len(unique)==1:
        appid,fix_title=next(iter(unique.items()))
        return {"gameid":appid,"title":fix_title}, "AUTO_STEAM_MATCH"
    if len(unique)>1: return None, "AMBIGUOUS_STEAM_MATCH"
    return None, "NO_STEAM_MATCH"

def gamefix_path(root: Path, gameid: str, store: str):
    return root / ("gamefixes-umu" if store == "none" else f"gamefixes-{store}") / f"{gameid}.py"

def choose_store(gameid: str, stores, protonfixes: Path):
    stores=sorted(set(stores))
    if len(stores)==1: return stores[0],"SINGLE_STORE"
    with_fix=[store for store in stores if (lambda p:p.exists() or p.is_symlink())(gamefix_path(protonfixes,gameid,store))]
    if len(with_fix)==1: return with_fix[0],"MULTI_STORE_GAMEFIX_PREFERRED"
    if len(with_fix)>1:
        hashes={}
        for store in with_fix:
            try:
                real=gamefix_path(protonfixes,gameid,store).resolve(strict=True)
                digest=hashlib.sha256(real.read_bytes()).hexdigest()
            except Exception:
                return "","MULTI_STORE_FIX_UNRESOLVED"
            hashes.setdefault(digest,[]).append(store)
        if len(hashes)==1: return sorted(with_fix)[0],"MULTI_STORE_FIX_IDENTICAL"
        return "","MULTI_STORE_FIX_DIFFERENT"
    return stores[0],"MULTI_STORE_NO_GAMEFIX"

def load_overrides(path: Path):
    if not path.is_file(): return []
    rows=[]
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            game_path=canonical_game_path(row.get("path","")); title=(row.get("title") or "").strip()
            gameid=(row.get("gameid") or "").strip(); store=(row.get("store") or "").strip().casefold()
            if gameid: rows.append({"path":game_path,"title":title,"gameid":gameid,"store":store})
    return rows

def find_override(game, overrides):
    by_path=[r for r in overrides if r["path"] and r["path"] == game["path"]]
    if len(by_path)==1: return by_path[0]
    by_title=[r for r in overrides if r["title"] and normalize_title(r["title"]) == normalize_title(game["title"])]
    return by_title[0] if len(by_title)==1 else None

def resolve(game_path,gamelist,database,protonfixes,overrides):
    game,path_match=find_batocera_game(game_path,load_gamelist(gamelist))
    override=find_override(game,load_overrides(overrides))
    if override:
        return {"GAMEID":override["gameid"],"STORE":override["store"],"MATCH":"MANUAL_OVERRIDE","PATH_MATCH":path_match,"TITLE":game["title"],"DB_TITLE":"","STORE_POLICY":"MANUAL"}

    matches,match_type=find_database_matches(game["title"],load_umu_database(database))
    result={"GAMEID":"umu-default","STORE":"","MATCH":match_type,"PATH_MATCH":path_match,"TITLE":game["title"],"DB_TITLE":"","STORE_POLICY":"NONE"}
    if not matches:
        steam_match,steam_policy=find_steam_gamefix_match(game["title"],protonfixes)
        if steam_match:
            result.update({"GAMEID":steam_match["gameid"],"STORE":"steam","MATCH":"AUTO_STEAM_MATCH","DB_TITLE":steam_match["title"],"STORE_POLICY":"STEAM_GAMEFIX_EXACT_NORMALIZED"})
        elif steam_policy == "AMBIGUOUS_STEAM_MATCH":
            result["MATCH"]="AMBIGUOUS_STEAM_MATCH"; result["STORE_POLICY"]="AMBIGUOUS_STEAM_GAMEFIX"
        return result
    gameids=sorted({r["gameid"] for r in matches})
    if len(gameids)!=1:
        result["MATCH"]=result["STORE_POLICY"]="AMBIGUOUS_ID"; return result
    gameid=gameids[0]; relevant=[r for r in matches if r["gameid"]==gameid]
    store,policy=choose_store(gameid,[r["store"] for r in relevant],protonfixes)
    result.update({"GAMEID":gameid,"STORE":"" if store=="none" else store,"DB_TITLE":" | ".join(sorted({r["title"] for r in relevant})),"STORE_POLICY":policy})
    return result

def shell_escape(value):
    return "'" + str(value).replace("'", "'\"'\"'") + "'"

def main():
    p=argparse.ArgumentParser(description="Résolveur GAMEID/STORE UMU pour Batocera")
    p.add_argument("game"); p.add_argument("--gamelist",type=Path,default=DEFAULT_GAMELIST); p.add_argument("--database",type=Path,default=DEFAULT_DB); p.add_argument("--protonfixes",type=Path,default=DEFAULT_PROTONFIXES); p.add_argument("--overrides",type=Path,default=DEFAULT_OVERRIDES)
    a=p.parse_args()
    try: result=resolve(a.game,a.gamelist,a.database,a.protonfixes,a.overrides)
    except Exception as exc:
        print(f"ERROR={shell_escape(str(exc))}",file=sys.stderr); return 2
    for key in ("GAMEID","STORE","MATCH","PATH_MATCH","TITLE","DB_TITLE","STORE_POLICY"):
        print(f"{key}={shell_escape(result.get(key,''))}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
