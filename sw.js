const C="scatty-katie-v2";
const FILES=["./","index.html","manifest.json","icon-192.png","icon-512.png","apple-touch-icon.png","data/spoons.json","data/poundland.json"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(FILES).catch(()=>{})));self.skipWaiting()});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))));self.clients.claim()});
self.addEventListener("fetch",e=>{const u=new URL(e.request.url);
  if(e.request.method!=="GET"||u.origin!==location.origin)return;
  const key=new Request(u.origin+u.pathname);
  e.respondWith(fetch(e.request).then(r=>{const cp=r.clone();caches.open(C).then(c=>c.put(key,cp));return r}).catch(()=>caches.match(key)))});
