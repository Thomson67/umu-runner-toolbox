#!/usr/bin/env python3
import argparse,csv,xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_GAMELIST=Path("/userdata/roms/windows/gamelist.xml")
DEFAULT_OVERRIDES=Path("/userdata/system/umu/toolbox/config/gameid-overrides.csv")
FIELDS=["path","title","gameid","store"]

def games(path):
    root=ET.parse(path).getroot(); out=[]
    for g in root.findall("game"):
        p=(g.findtext("path") or "").strip(); n=(g.findtext("name") or "").strip()
        if p and n: out.append((n,p))
    return sorted(out,key=lambda x:x[0].casefold())

def rows(path):
    if not path.is_file(): return []
    with path.open("r",encoding="utf-8-sig",newline="") as h: return list(csv.DictReader(h))

def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8",newline="") as h:
        w=csv.DictWriter(h,fieldnames=FIELDS); w.writeheader(); w.writerows(data)
    tmp.replace(path)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--gamelist",type=Path,default=DEFAULT_GAMELIST); p.add_argument("--overrides",type=Path,default=DEFAULT_OVERRIDES)
    sp=p.add_subparsers(dest="cmd",required=True)
    sp.add_parser("games"); sp.add_parser("list")
    s=sp.add_parser("set"); s.add_argument("--path",required=True); s.add_argument("--title",required=True); s.add_argument("--gameid",required=True); s.add_argument("--store",default="")
    d=sp.add_parser("delete"); d.add_argument("--index",type=int,required=True)
    a=p.parse_args()
    if a.cmd=="games":
        for i,(n,path) in enumerate(games(a.gamelist),1): print(f"{i}\t{n}\t{path}")
        return
    data=rows(a.overrides)
    if a.cmd=="list":
        for i,r in enumerate(data,1): print("\t".join([str(i),r.get("title",""),r.get("gameid",""),r.get("store",""),r.get("path","")]))
    elif a.cmd=="set":
        if not a.gameid.startswith("umu-"): raise SystemExit("GAMEID must start with umu-")
        data=[r for r in data if r.get("path","")!=a.path]
        data.append({"path":a.path,"title":a.title,"gameid":a.gameid,"store":a.store.strip().casefold()})
        data.sort(key=lambda r:r["title"].casefold()); write(a.overrides,data)
    elif a.cmd=="delete":
        idx=a.index-1
        if idx<0 or idx>=len(data): raise SystemExit("invalid index")
        del data[idx]; write(a.overrides,data)
if __name__=="__main__": main()
