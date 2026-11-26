"""Lossless binary STL -> indexed GLB. No welding tolerance, face deletion,
quantization, simplification or material-based filtering. Preserve float32
position bits and triangle order; source normals are not encoded."""
import argparse, hashlib, json, struct
from pathlib import Path
import numpy as np
SHA='3591355fc311096333078001acec6d5bf7a99ef8e39711f54ee15771dcaf28c2'
def main():
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
 with a.source.open('rb') as f:
  sha=hashlib.file_digest(f,'sha256').hexdigest();f.seek(80);n=struct.unpack('<I',f.read(4))[0]
 if sha!=SHA or n!=4621182 or a.source.stat().st_size!=84+50*n:raise ValueError('Source integrity check failed')
 dt=np.dtype([('normal','<f4',(3,)),('position','<f4',(3,3)),('attribute','<u2')])
 raw=np.memmap(a.source,dtype=dt,offset=84,shape=(n,),mode='r')
 # Exact indexing of float32 position bits; retain every face, including duplicates.
 flat=np.ascontiguousarray(raw['position'].reshape(-1,3))
 if not np.isfinite(flat).all():raise ValueError('Nonfinite coordinates')
 bits=flat.view('<u4').reshape(-1,3)
 u,inv=np.unique(bits,axis=0,return_inverse=True)
 v=np.ascontiguousarray(u.view('<f4'));idx=np.ascontiguousarray(inv,dtype='<u4')
 # Verify every coordinate bit in original corner order, in bounded batches.
 for i in range(0,len(idx),300000):
  assert np.array_equal(u[idx[i:i+300000]],bits[i:i+300000])
 lo=v.min(axis=0).tolist();hi=v.max(axis=0).tolist()
 # Omit normals: browser calculates flat geometric normals from triangles.
 # No source color is available in standard STL; double-sided neutral material.
 vb=v.tobytes();ib=idx.tobytes();binary=vb+ib
 doc={'asset':{'version':'2.0','generator':'BS_3D exact-position indexing V0.6.1'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'mesh':0,'name':'complete_original_geometry'}],'meshes':[{'primitives':[{'attributes':{'POSITION':0},'indices':1,'material':0,'mode':4}]}],'materials':[{'doubleSided':True,'pbrMetallicRoughness':{'baseColorFactor':[0.52,0.62,0.65,1],'metallicFactor':0,'roughnessFactor':0.85}}],'buffers':[{'byteLength':len(binary)}],'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':len(vb),'target':34962},{'buffer':0,'byteOffset':len(vb),'byteLength':len(ib),'target':34963}],'accessors':[{'bufferView':0,'componentType':5126,'count':len(v),'type':'VEC3','min':lo,'max':hi},{'bufferView':1,'componentType':5125,'count':len(idx),'type':'SCALAR','min':[int(idx.min())],'max':[int(idx.max())]}]}
 j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*((-len(j))%4)
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('wb') as f:
  f.write(struct.pack('<4sII',b'glTF',2,12+8+len(j)+8+len(binary)));f.write(struct.pack('<I4s',len(j),b'JSON'));f.write(j);f.write(struct.pack('<I4s',len(binary),b'BIN\x00'));f.write(binary)
 # Verify serialized asset, including index order and all position bits.
 with a.output.open('rb') as f:
  magic,version,total=struct.unpack('<4sII',f.read(12));assert magic==b'glTF' and version==2 and total==a.output.stat().st_size
  jl,jt=struct.unpack('<I4s',f.read(8));assert jt==b'JSON';d=json.loads(f.read(jl));bl,bt=struct.unpack('<I4s',f.read(8));assert bt==b'BIN\x00' and bl==len(binary);offset=f.tell()
 vv=np.memmap(a.output,dtype='<u4',offset=offset,shape=u.shape,mode='r');ii=np.memmap(a.output,dtype='<u4',offset=offset+len(vb),shape=idx.shape,mode='r')
 for i in range(0,len(ii),300000):assert np.array_equal(vv[ii[i:i+300000]],bits[i:i+300000])
 assert d['accessors'][1]['count']==3*n
 report=dict(source_sha256=sha,source_faces=n,output_faces=len(idx)//3,unique_exact_vertices=len(v),bounds=[lo,hi],bytes=a.output.stat().st_size,position_bits_and_triangle_order_verified=True,geometry_loss=False,normals='derived from triangles at render time; source STL normals not encoded',materials='neutral; STL has no standard material hierarchy',units='assumed metres; Y up')
 if a.output.stat().st_size>=100*1024*1024:raise ValueError('GLB exceeds GitHub single-file limit; use chunked distribution')
 a.output.with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
