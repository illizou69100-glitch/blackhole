// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: deep-gray; icon-glyph: tv;

/* Télécommande du décodeur TV d'Orange — version iPhone (app Scriptable).
   Scriptable peut appeler le décodeur sur le Wi-Fi, ce que Safari refuse :
   ce script affiche la télécommande et transmet les touches au décodeur.
   Fichier généré par construire_scriptable.py à partir de index.html. */

const PORT = 8080;
const CLE = 'telecommande-orange';

/* ---------- Mémoire (trousseau iOS) ---------- */
function charger() {
  try { return Keychain.contains(CLE) ? JSON.parse(Keychain.get(CLE)) : {}; } catch (e) { return {}; }
}
const memoire = charger();
memoire.stock = memoire.stock || {};
function sauver() { Keychain.set(CLE, JSON.stringify(memoire)); }

/* ---------- Décodeur ---------- */
async function appel(ip, params, delai) {
  const qs = Object.entries(params).map(([k, v]) => k + '=' + encodeURIComponent(v)).join('&');
  const r = new Request(`http://${ip}:${PORT}/remoteControl/cmd?${qs}`);
  r.timeoutInterval = delai || 3;
  const texte = await r.loadString();
  try { return JSON.parse(texte); } catch (e) { return { brut: texte }; }
}

async function sonder(ip) {
  try {
    const rep = await appel(ip, { operation: '10' }, 1.5);
    const d = (rep.result && rep.result.data) || {};
    if ('activeStandbyState' in d || 'osdContext' in d) return { ip, nom: d.friendlyName || 'Décodeur Orange' };
  } catch (e) {}
  return null;
}

/* La Livebox distribue des adresses en 192.168.1.x : on sonde ce réseau. */
async function chercher() {
  const trouves = [];
  for (let debut = 1; debut < 255; debut += 64) {
    const lot = [];
    for (let i = debut; i < Math.min(debut + 64, 255); i++) lot.push(sonder('192.168.1.' + i));
    (await Promise.all(lot)).forEach(r => r && trouves.push(r));
  }
  if (trouves.length === 1) { memoire.ip = trouves[0].ip; sauver(); }
  return trouves;
}

let rechercheFaite = false;
async function ipDecodeur() {
  if (!memoire.ip && !rechercheFaite) { rechercheFaite = true; await chercher(); }
  if (!memoire.ip) throw new Error('Aucun décodeur configuré — réglez son IP (⚙︎)');
  return memoire.ip;
}

async function traiter(route, p) {
  switch (route) {
    case 'touche':
      return appel(await ipDecodeur(), { operation: '01', key: p.code, mode: p.mode || 0 });
    case 'etat':
      return appel(await ipDecodeur(), { operation: '10' });
    case 'decodeur':
      if (p.ip !== undefined) {
        if (!/^\d{1,3}(\.\d{1,3}){3}$/.test(p.ip)) throw new Error('Adresse IP invalide');
        memoire.ip = p.ip; sauver();
      }
      return { ip: memoire.ip || null };
    case 'recherche': {
      const decodeurs = await chercher();
      return { decodeurs, ip: memoire.ip || null };
    }
    case 'memoriser':
      memoire.stock[p.k] = p.v; sauver();
      return {};
  }
  throw new Error('Route inconnue : ' + route);
}

/* ---------- Pont avec la page ---------- */
const PONT = `<script>
window.__pont = {
  stock: ${JSON.stringify(memoire.stock)},
  file: [], promesses: {}, n: 0, reveil: null,
  appel(route, params) {
    return new Promise((res, rej) => {
      const id = ++this.n;
      this.promesses[id] = { res, rej };
      const p = {};
      for (const k in params) p[k] = String(params[k]);
      this.file.push({ id, route, params: p });
      if (this.reveil) this.reveil();
    });
  },
  lire(completion) {
    let t;
    const vider = () => { clearTimeout(t); this.reveil = null; const f = this.file; this.file = []; completion(f); };
    if (this.file.length) return vider();
    t = setTimeout(vider, 4000);
    this.reveil = vider;
  },
  repondre(id, ok, data) {
    const p = this.promesses[id];
    if (!p) return;
    delete this.promesses[id];
    ok ? p.res(data) : p.rej(new Error(data));
  },
};
</script>`;

const HTML = __HTML__;

const vue = new WebView();
await vue.loadHTML(HTML.replace('<head>', '<head>' + PONT));
let ouverte = true;
vue.present(true).then(() => { ouverte = false; });

while (ouverte) {
  let demandes;
  try { demandes = await vue.evaluateJavaScript('window.__pont.lire(completion)', true); }
  catch (e) { break; }
  for (const d of demandes || []) {
    let ok = true, data;
    try { data = await traiter(d.route, d.params || {}); }
    catch (e) { ok = false; data = String((e && e.message) || e); }
    await vue.evaluateJavaScript(`window.__pont.repondre(${d.id}, ${ok}, ${JSON.stringify(data)})`);
  }
}
Script.complete();
