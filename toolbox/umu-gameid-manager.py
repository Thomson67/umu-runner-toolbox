#!/usr/bin/env python3
import argparse,ast,csv,difflib,re,xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_GAMELIST=Path('/userdata/roms/windows/gamelist.xml')
DEFAULT_OVERRIDES=Path('/userdata/system/umu/toolbox/config/gameid-overrides.csv')
DEFAULT_DB=Path('/userdata/system/umu/toolbox/data/umu-database.csv')
DEFAULT_RUNNERS=Path('/userdata/system/wine/custom')
FIELDS=['path','title','gameid','store']
VALID_GAME_SUFFIXES=('.wsquashfs','.wine','.pc','.wtgz')

def norm(s):
    s=(s or '').casefold().replace('™','').replace('®','')
    s=re.sub(r'[^a-z0-9]+',' ',s)
    return ' '.join(s.split())

def clean_field(s):
    # Keep command output one-record-per-line and immune to dialog/IFS parsing.
    return re.sub(r'[\t\r\n]+', ' ', (s or '').strip())

def games(path):
    root=ET.parse(path).getroot(); out=[]
    for g in root.findall('game'):
        gp=clean_field(g.findtext('path')); n=clean_field(g.findtext('name'))
        if gp and n and gp.casefold().endswith(VALID_GAME_SUFFIXES): out.append((n,gp))
    return sorted(out,key=lambda x:x[0].casefold())

def rows(path):
    if not path.is_file(): return []
    with path.open('r',encoding='utf-8-sig',newline='') as h: return list(csv.DictReader(h))

def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w',encoding='utf-8',newline='') as h:
        w=csv.DictWriter(h,fieldnames=FIELDS); w.writeheader(); w.writerows(data)
    tmp.replace(path)

def db_candidates(db):
    out={}
    if not db.is_file(): return out
    with db.open('r',encoding='utf-8-sig',newline='') as h:
        for r in csv.reader(h):
            if len(r)<4: continue
            title,store,_,gameid=(x.strip() for x in r[:4])
            if not title or not gameid: continue
            key=(gameid,title)
            out.setdefault(key,set())
            if store: out[key].add(store.casefold())
    return out

def steam_candidates(runners):
    out={}
    if not runners.is_dir(): return out
    seen=set()
    patterns=(
        'GE-Proton*-UMU/protonfixes/gamefixes-steam/*.py',
        'GDK-Proton*-UMU/protonfixes/gamefixes-steam/*.py',
    )
    for pattern in patterns:
        for p in runners.glob(pattern):
            if not p.stem.isdigit() or p.stem in seen: continue
            seen.add(p.stem)
            try:
                tree=ast.parse(p.read_text(encoding='utf-8',errors='replace'))
                title=(ast.get_docstring(tree) or '').splitlines()[0].strip()
            except Exception: continue
            title=re.sub(r'^game\s+fix\s+for\s+','',title,flags=re.I).strip()
            if title: out[(p.stem,title)]={'steam'}
    return out

def candidate_list(title,db,runners,limit=12):
    allc=db_candidates(db)
    for k,stores in steam_candidates(runners).items(): allc.setdefault(k,set()).update(stores)
    nt=norm(title); scored=[]
    for (gid,name),stores in allc.items():
        nn=norm(name)
        score=difflib.SequenceMatcher(None,nt,nn).ratio()
        if nt==nn: score=1.0
        elif nt and (nt in nn or nn in nt): score=max(score,0.90)
        scored.append((score,name,gid,','.join(sorted(stores))))
    scored.sort(key=lambda x:(-x[0],x[1].casefold(),x[2]))
    return scored[:limit]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--gamelist',type=Path,default=DEFAULT_GAMELIST); p.add_argument('--overrides',type=Path,default=DEFAULT_OVERRIDES); p.add_argument('--database',type=Path,default=DEFAULT_DB); p.add_argument('--runners',type=Path,default=DEFAULT_RUNNERS)
    sp=p.add_subparsers(dest='cmd',required=True)
    sp.add_parser('games'); sp.add_parser('list'); sp.add_parser('scan')
    c=sp.add_parser('candidates'); c.add_argument('--title',required=True); c.add_argument('--limit',type=int,default=12)
    s=sp.add_parser('set'); s.add_argument('--path',required=True); s.add_argument('--title',required=True); s.add_argument('--gameid',required=True); s.add_argument('--store',default='')
    d=sp.add_parser('delete'); d.add_argument('--index',type=int,required=True)
    a=p.parse_args()
    if a.cmd=='games':
        for i,(n,path) in enumerate(games(a.gamelist),1): print(f'{i}\t{n}\t{path}')
        return
    if a.cmd=='candidates':
        for i,(score,name,gid,stores) in enumerate(candidate_list(a.title,a.database,a.runners,a.limit),1): print(f'{i}\t{score:.3f}\t{clean_field(name)}\t{gid}\t{stores}')
        return
    if a.cmd=='scan':
        overridden={r.get('path','') for r in rows(a.overrides)}
        counts={'CLEAR':0,'AMBIGUOUS':0,'NONE':0,'OVERRIDE':0}
        results=[]
        for title,gp in games(a.gamelist):
            if gp in overridden:
                counts['OVERRIDE']+=1; continue
            cand=candidate_list(title,a.database,a.runners,3)
            top=cand[0][0] if cand else 0.0
            second=cand[1][0] if len(cand)>1 else 0.0
            # Exact normalized title is clear. Otherwise demand both a strong
            # score and a useful lead over the runner-up; do not auto-assign.
            exact=bool(cand and norm(title)==norm(cand[0][1]))
            if exact or (top>=0.92 and top-second>=0.08): status='CLEAR'
            elif top>=0.70: status='AMBIGUOUS'
            else: status='NONE'
            counts[status]+=1
            if status=='AMBIGUOUS':
                best=clean_field(cand[0][1]) if cand else ''
                gid=cand[0][2] if cand else ''
                results.append((status,title,gp,top,best,gid))
        total=sum(counts.values())
        print(f'SUMMARY\t{total}\t{counts["CLEAR"]}\t{counts["AMBIGUOUS"]}\t{counts["NONE"]}\t{counts["OVERRIDE"]}')
        for i,(status,title,gp,score,best,gid) in enumerate(results,1):
            print(f'ITEM\t{i}\t{status}\t{score:.3f}\t{clean_field(title)}\t{clean_field(gp)}\t{best}\t{gid}')
        return
    data=rows(a.overrides)
    if a.cmd=='list':
        for i,r in enumerate(data,1): print('\t'.join([str(i),r.get('title',''),r.get('gameid',''),r.get('store',''),r.get('path','')]))
    elif a.cmd=='set':
        if not (a.gameid.startswith('umu-') or a.gameid.isdigit()): raise SystemExit('GAMEID must be an umu-* ID or a numeric Steam AppID')
        data=[r for r in data if r.get('path','')!=a.path]
        data.append({'path':a.path,'title':a.title,'gameid':a.gameid,'store':a.store.strip().casefold()})
        data.sort(key=lambda r:r['title'].casefold()); write(a.overrides,data)
    elif a.cmd=='delete':
        idx=a.index-1
        if idx<0 or idx>=len(data): raise SystemExit('invalid index')
        del data[idx]; write(a.overrides,data)
if __name__=='__main__': main()
