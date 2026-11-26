// V0.6.4: exact original assets, bounded parallel loading, content-addressed cache.
const base='models/color/',raw='https://raw.githubusercontent.com/hwh0410/BS_3D/main/';
const dbName='BS3D-color-v1';
function openDB(){return new Promise(resolve=>{try{const q=indexedDB.open(dbName,1);q.onupgradeneeded=()=>q.result.createObjectStore('assets');q.onsuccess=()=>resolve(q.result);q.onerror=q.onblocked=()=>resolve(null)}catch{resolve(null)}})}
function read(db,k){return new Promise(resolve=>{if(!db)return resolve(null);try{const q=db.transaction('assets').objectStore('assets').get(k);q.onsuccess=()=>resolve(q.result||null);q.onerror=()=>resolve(null)}catch{resolve(null)}})}
function write(db,k,v){return new Promise(resolve=>{if(!db)return resolve(false);try{const t=db.transaction('assets','readwrite');t.objectStore('assets').put(v,k);t.oncomplete=()=>resolve(true);t.onerror=t.onabort=()=>resolve(false)}catch{resolve(false)}})}
async function get(path,signal){for(const url of [path,raw+path]){try{const r=await fetch(url,{signal});if(r.ok)return r}catch(e){if(signal.aborted)throw e}}throw Error('資產無法下載：'+path)}
async function networkBytes(a,signal){if(typeof DecompressionStream==='function'){try{const r=await get('models/color-gzip/'+a.file+'.gz',signal);const b=await new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();if(await verify(b,a))return b}catch(e){if(signal.aborted)throw e}}return (await get(base+a.file,signal)).arrayBuffer()}
async function verify(b,a){if(!(b instanceof ArrayBuffer)||b.byteLength!==a.bytes)return false;const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b)),x=>x.toString(16).padStart(2,'0')).join('');return hash===a.sha256}
export function disposeColor(group){const gs=new Set(),ms=new Set(),ts=new Set();group.traverse(o=>{if(o.isMesh){gs.add(o.geometry);for(const m of [].concat(o.material)){ms.add(m);for(const v of Object.values(m))if(v?.isTexture)ts.add(v)}}});gs.forEach(g=>g.dispose());ms.forEach(m=>m.dispose());ts.forEach(t=>t.dispose())}
export async function loadColor(T,GLTFLoader,progress,active=()=>true,partial=()=>{}){
 const start=performance.now(),controller=new AbortController(),signal=controller.signal;
 const manifest=await(await get(base+'manifest.json',signal)).json();
 if(manifest.source_sha256!=='d52a44d389925a7ee3cb7faf517f47e26ffc515ed1bf1f512ef546e8074de34f'||manifest.assemblies.length!==50||manifest.triangles!==4621182)throw Error('彩色模型清單校驗失敗');
 const items=manifest.assemblies.slice();if(new Set(items.map(a=>a.file)).size!==50||items.some(a=>!/^assembly-\d{2}\.glb$/.test(a.file)||!/^\w{64}$/.test(a.sha256)))throw Error('清單檔名校驗失敗');
 const priority=a=>/發酵貨櫃|驗氧發酵貨櫃/.test(a.name)?0:/地基圖/.test(a.name)?1:/鋼構維修|螺運機/.test(a.name)?2:3;
 items.sort((a,b)=>priority(a)-priority(b)||a.bytes-b.bytes);
 let gzipReady=false;if(typeof DecompressionStream==='function'){try{const meta=await(await get('models/color-gzip/manifest.json',signal)).json();gzipReady=meta.source_sha256===manifest.source_sha256&&(meta.assemblies===50||meta.assets?.length===50)}catch{}}const db=await openDB(),group=new T.Group();let next=0,done=0,total=0,loadedBytes=0,cacheHits=0,cacheBytes=0,cacheWrites=0,failed=null;const totalBytes=items.reduce((s,a)=>s+a.bytes,0);
 const report=()=>({done,total:50,triangles:total,loadedBytes,totalBytes,cacheHits,cacheBytes,cacheWrites,elapsed:(performance.now()-start)/1000});
 const ensure=()=>{if(failed||!active()||signal.aborted)throw Error('載入已取消')};
 partial(group,null,report());
 async function worker(){while(next<items.length){ensure();const a=items[next++];let bytes=await read(db,a.sha256);ensure();if(await verify(bytes,a)){cacheHits++;cacheBytes+=a.bytes}else{bytes=gzipReady?await networkBytes(a,signal):await(await get(base+a.file,signal)).arrayBuffer();ensure();if(!await verify(bytes,a))throw Error(a.file+' SHA-256 校驗失敗');if(await write(db,a.sha256,bytes))cacheWrites++}
 ensure();const g=await new GLTFLoader().parseAsync(bytes,'');if(failed||!active()){disposeColor(g.scene);ensure()}let count=0;g.scene.traverse(o=>{if(o.isMesh)count+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3});if(count!==a.triangles){disposeColor(g.scene);throw Error(a.file+' 面數校驗失敗')}
 g.scene.name=a.name;g.scene.userData={name:a.name,desc:'原始組合件｜'+count.toLocaleString()+' 三角面；原始材質保留。'};group.add(g.scene);total+=count;done++;loadedBytes+=a.bytes;const stats=report();partial(group,g.scene,stats);progress('載入 '+done+'/50 組｜'+(loadedBytes/1e6).toFixed(1)+' / '+(totalBytes/1e6).toFixed(1)+' MB｜快取 '+cacheHits+' 組｜'+stats.elapsed.toFixed(1)+' 秒',stats);
 }}
 try{const limit=(navigator.deviceMemory&&navigator.deviceMemory<=4)?2:4;const jobs=Array.from({length:limit},()=>worker().catch(e=>{if(!failed)failed=e;controller.abort()}));await Promise.allSettled(jobs);if(failed)throw failed;ensure();if(total!==4621182||done!==50)throw Error('完整面數校驗失敗');return {scene:group,stats:report()}}catch(e){group.removeFromParent();disposeColor(group);throw e}finally{db?.close()}
}
