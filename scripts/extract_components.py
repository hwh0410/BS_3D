import argparse, hashlib, json, struct
from pathlib import Path
import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components
import trimesh

def main():
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 with a.source.open('rb') as f: sha=hashlib.file_digest(f,'sha256').hexdigest();f.seek(80);n=struct.unpack('<I',f.read(4))[0]
 if sha!='3591355fc311096333078001acec6d5bf7a99ef8e39711f54ee15771dcaf28c2':raise ValueError('Unexpected source SHA256')
 dt=np.dtype([('n','<f4',(3,)),('v','<f4',(3,3)),('a','<u2')]);raw=np.memmap(a.source,dtype=dt,offset=84,mode='r',shape=(n,));q=np.rint(np.ascontiguousarray(raw['v'].reshape(-1,3))*1e5).astype(np.int32)
 u,inv=np.unique(q,axis=0,return_inverse=True);del q;f=inv.reshape(-1,3).astype(np.int32);del inv
 i=np.concatenate([f[:,0],f[:,1]]);j=np.concatenate([f[:,1],f[:,2]]);g=sp.coo_matrix((np.ones(len(i),dtype=np.bool_),(i,j)),shape=(len(u),len(u))).tocsr();del i,j
 nc,l=connected_components(g,directed=False);del g
 lo=np.full((nc,3),np.iinfo(np.int32).max,dtype=np.int32);hi=np.full((nc,3),np.iinfo(np.int32).min,dtype=np.int32);np.minimum.at(lo,l,u);np.maximum.at(hi,l,u);lo=lo/1e5;hi=hi/1e5;d=hi-lo;fl=l[f[:,0]];cnt=np.bincount(fl,minlength=nc);del f,u,l
 names=['unclassified','reactor_candidate_1','reactor_candidate_2','reactor_candidate_3','reactor_candidate_4','excavator_candidate','worker_candidate_1','worker_candidate_2','worker_candidate_3','shared_platform_piping_candidate','ground_candidate'];steps=[.035,.015,.015,.015,.015,.005,0,0,0,.008,.035];colors=[[150,156,158,255]]+[[168,79,59,255]]*4+[[218,169,48,255]]+[[225,180,70,255]]*3+[[111,137,145,255],[185,183,169,255]]
 group=np.zeros(nc,dtype=np.int32)
 for k in range(4):
  z=24.0+2.5*k;mask=(lo[:,0]>=-9.55)&(hi[:,0]<=2.85)&(lo[:,2]>=z-.08)&(hi[:,2]<=z+2.5+.08)&(lo[:,1]>=-9.55)&(hi[:,1]<=-5.35);group[mask]=k+1
 mask=(lo[:,0]>=-16.2)&(hi[:,0]<=-8.5)&(lo[:,2]>=37.1)&(hi[:,2]<=43.6)&(lo[:,1]>=-9.65)&(hi[:,1]<=-4.3);group[mask]=5
 workers=np.flatnonzero((d[:,1]>1.5)&(d[:,1]<2.1)&(d[:,0]<1)&(d[:,2]<1)&(cnt>1000));workers=workers[np.argsort(lo[workers,0])];assert len(workers)==3
 for k,w in enumerate(workers):group[w]=6+k
 mask=(group==0)&(lo[:,0]>=-10)&(hi[:,0]<=4)&(lo[:,2]>=23)&(hi[:,2]<=38)&(lo[:,1]>=-9.6)&(hi[:,1]<=-3.5);group[mask]=9
 mask=(group==0)&(d[:,1]<.4)&(d[:,0]>10)&(d[:,2]>10)&(hi[:,1]<-8.9);group[mask]=10
 facegroup=group[fl];scene=trimesh.Scene();records=[]
 for k,name in enumerate(names):
  if not np.any(group==k):continue
  ix=np.flatnonzero(facegroup==k);part=np.asarray(raw['v'][ix]).reshape(-1,3);del ix
  step=steps[k];base=part.min(axis=0);q=np.rint((part-base)/step).astype(np.int32) if step else part
  v,idx=np.unique(q,axis=0,return_inverse=True);f=idx.reshape(-1,3);del q,part,idx
  v=v.astype(np.float32)*step+base if step else v
  ok=(f[:,0]!=f[:,1])&(f[:,1]!=f[:,2])&(f[:,0]!=f[:,2]);f=f[ok];_,idx=np.unique(np.sort(f,axis=1),axis=0,return_index=True);f=f[np.sort(idx)]
  m=trimesh.Trimesh(vertices=v,faces=f,process=False);m.remove_unreferenced_vertices();m.visual=trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(baseColorFactor=colors[k],roughnessFactor=.8));scene.add_geometry(m,node_name=name,geom_name=name);out=a.output/(name+'.glb');m.export(out);check=trimesh.load(out,force='mesh',process=False);assert len(check.faces)==len(m.faces)
  records.append(dict(name=name,components=int((group==k).sum()),source_faces=int(cnt[group==k].sum()),output_faces=len(m.faces),bytes=out.stat().st_size,bounds=m.bounds.tolist(),grid_step=step));print(name,records[-1],flush=True)
 assert sum(r['source_faces'] for r in records)==n
 scene.export(a.output/'component_scene.glb');(a.output/'component_manifest.json').write_text(json.dumps(dict(source_sha256=sha,source_faces=n,components=nc,weld_grid=.00001,classification='whole connected component candidate groups, not verified CAD assembly',units='assumed metres; Y up',groups=records),indent=2))
if __name__=='__main__':main()
