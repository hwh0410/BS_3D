// V0.6.3: preserve exported source materials; do not override or decimate.
const base='models/color/';
const raw='https://raw.githubusercontent.com/hwh0410/BS_3D/main/';
export async function loadColor(T,GLTFLoader,progress,active=()=>true){
 const get=async path=>{let r;try{r=await fetch(path,{cache:'no-cache'});if(!r.ok)throw Error(String(r.status));}catch{r=await fetch(raw+path);if(!r.ok)throw Error('彩色模型尚未部署：'+r.status)}return r};
 const m=await (await get(base+'manifest.json')).json();
 if(m.source_sha256!=='d52a44d389925a7ee3cb7faf517f47e26ffc515ed1bf1f512ef546e8074de34f'||m.assemblies.length!==50||m.triangles!==4621182)throw Error('彩色模型清單校驗失敗');
 const group=new T.Group();let total=0;const loader=new GLTFLoader();
 const dispose=()=>group.traverse(o=>{if(o.isMesh){o.geometry.dispose();for(const mat of [].concat(o.material)){for(const v of Object.values(mat))if(v?.isTexture)v.dispose();mat.dispose()}}});
 try{for(let i=0;i<m.assemblies.length;i++){if(!active())throw Error('已取消');const a=m.assemblies[i];if(!/^assembly-\d{2}\.glb$/.test(a.file))throw Error('檔名校驗失敗');progress('載入原始彩色模型 '+(i+1)+' / 50');const bytes=await(await get(base+a.file)).arrayBuffer();const sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');if(bytes.byteLength!==a.bytes||sha!==a.sha256)throw Error(a.file+' 完整性校驗失敗');const g=await loader.parseAsync(bytes,'');let count=0;g.scene.traverse(o=>{if(o.isMesh)count+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3});if(count!==a.triangles)throw Error(a.file+' 面數校驗失敗');g.scene.name=a.name;g.scene.userData={name:a.name,desc:'原始組合件｜'+count.toLocaleString()+' 三角面；原始材質保留。'};group.add(g.scene);total+=count}
 if(total!==4621182||!active())throw Error('完整面數校驗失敗或取消');return {scene:group};
 }catch(e){dispose();throw e}
}
