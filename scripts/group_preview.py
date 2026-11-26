import argparse,json
from pathlib import Path
import numpy as np
import trimesh
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
m=trimesh.load(a.source,force='mesh',process=False)
t=m.triangles;c=t.mean(axis=1);x,y,z=c.T;d=np.ptp(t,axis=1)
g=np.full(len(t),8,dtype=int)
r=(x>=-9.5)&(x<=3)&(z>=23.8)&(z<34.1)
g[r]=np.clip(np.floor((z[r]-23.8)/2.575).astype(int),0,3)
g[(x>=-10)&(x<=3.2)&(z>=34.1)&(z<=38)]=4
g[(x>=-16)&(x<=-9)&(z>=37.5)&(z<=44)]=5
g[(x>=-16.5)&(x<-9.5)&(z>=22.5)&(z<37.5)]=6
g[((d[:,1]<.09)&(y<-9.05)&((d[:,0]>2)|(d[:,2]>2)))|(y<-9.8)]=7
names=['reactor_zone_1','reactor_zone_2','reactor_zone_3','reactor_zone_4','service_zone','excavator_candidate','west_equipment_zone','ground_candidate','unclassified']
colors=[[168,79,59,255]]*4+[[111,137,145,255],[218,169,48,255],[102,142,132,255],[185,183,169,255],[150,156,158,255]]
s=trimesh.Scene();report=[]
for i,n in enumerate(names):
 ix=np.flatnonzero(g==i)
 if not len(ix):continue
 f=m.faces[ix];ids,inv=np.unique(f,return_inverse=True);part=trimesh.Trimesh(vertices=m.vertices[ids],faces=inv.reshape(-1,3),process=False);part.visual=trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(baseColorFactor=colors[i],roughnessFactor=.8,metallicFactor=0));s.add_geometry(part,node_name=n,geom_name=n);report.append(dict(name=n,faces=len(ix),bounds=part.bounds.tolist()))
a.output.parent.mkdir(parents=True,exist_ok=True);s.export(a.output);assert sum(r['faces'] for r in report)==len(m.faces)
check=trimesh.load(a.output,force='scene',process=False);assert sum(len(v.faces) for v in check.geometry.values())==len(m.faces);assert np.allclose(check.bounds,m.bounds,atol=1e-5)
a.output.with_suffix('.json').write_text(json.dumps(dict(method='spatial candidate regions, not validated assembly separation',faces=len(m.faces),groups=report,bytes=a.output.stat().st_size),indent=2))
