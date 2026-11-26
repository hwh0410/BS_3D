"""Rebuild the V0.2 preview without modifying the source STL."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import trimesh
p=argparse.ArgumentParser()
p.add_argument("source",type=Path)
p.add_argument("output",type=Path)
args=p.parse_args()
expected="3591355fc311096333078001acec6d5bf7a99ef8e39711f54ee15771dcaf28c2"
with args.source.open("rb") as f:
    actual=hashlib.file_digest(f,"sha256").hexdigest()
if actual!=expected:
    raise SystemExit("Source SHA-256 does not match the uploaded original")
dt=np.dtype([("n","<f4",(3,)),("v","<f4",(3,3)),("a","<u2")])
a=np.memmap(args.source,dtype=dt,offset=84,mode="r")
v=a["v"]
lo=v.min(axis=(0,1)); hi=v.max(axis=(0,1)); step=.035
q=np.rint((v-lo)/step).astype(np.int32)
dims=np.ceil((hi-lo)/step).astype(np.int64)+2
k=(q[:,:,0].astype(np.int64)*dims[1]+q[:,:,1])*dims[2]+q[:,:,2]
del q
ok=(k[:,0]!=k[:,1])&(k[:,1]!=k[:,2])&(k[:,0]!=k[:,2])
k=k[ok]
_,idx=np.unique(np.sort(k,axis=1),axis=0,return_index=True)
k=k[idx]
ids,inv=np.unique(k,return_inverse=True)
xyz=np.column_stack((ids//(dims[1]*dims[2]),ids//dims[2]%dims[1],ids%dims[2])).astype(np.float32)*step+lo
m=trimesh.Trimesh(vertices=xyz,faces=inv.reshape(-1,3),process=False)
args.output.parent.mkdir(parents=True,exist_ok=True)
m.export(args.output)
report=dict(source_sha256=actual,source_faces=len(a),source_bounds=[lo.tolist(),hi.tolist()],grid_step_source_units=step,preview_faces=len(m.faces),preview_vertices=len(m.vertices),preview_bounds=m.bounds.tolist(),preview_bytes=args.output.stat().st_size,method="vertex grid clustering; visual preview, not engineering verification",source_units="assumed metres; Y up provisional")
args.output.with_suffix(".json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
