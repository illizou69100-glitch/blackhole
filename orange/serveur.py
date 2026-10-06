#!/usr/bin/env python3
"""Relais local pour la télécommande du décodeur TV d'Orange.

Le décodeur expose une API HTTP sur le port 8080 de votre réseau local.
Un navigateur ne peut pas l'appeler directement (CORS, et contenu mixte
depuis une page HTTPS) : ce script sert l'application ET relaie les
commandes vers le décodeur.

Usage :
    python3 serveur.py                 # détecte le décodeur automatiquement
    python3 serveur.py --decodeur 192.168.1.20
    python3 serveur.py --port 8765

Puis ouvrez http://<ip-de-cet-ordinateur>:8765 sur votre téléphone
(même Wi-Fi). Aucune dépendance : Python 3.8+ suffit.
"""
import argparse
import ipaddress
import json
import os
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

DOSSIER = os.path.dirname(os.path.abspath(__file__))
FICHIER_CONFIG = os.path.join(DOSSIER, "config.json")
PORT_DECODEUR = 8080


def lire_config():
    try:
        with open(FICHIER_CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def ecrire_config(cfg):
    with open(FICHIER_CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def appel_decodeur(ip, params, delai=3.0):
    """Appelle /remoteControl/cmd sur le décodeur et renvoie le JSON décodé."""
    url = f"http://{ip}:{PORT_DECODEUR}/remoteControl/cmd?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=delai) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def ip_locale():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # aucun paquet n'est envoyé
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def sonder(ip):
    try:
        rep = appel_decodeur(str(ip), {"operation": "10"}, delai=1.2)
        data = rep.get("result", {}).get("data", {})
        if "activeStandbyState" in data or "osdContext" in data:
            return {"ip": str(ip), "nom": data.get("friendlyName", "Décodeur Orange")}
    except Exception:
        pass
    return None


def chercher_decodeurs():
    reseau = ipaddress.ip_network(ip_locale() + "/24", strict=False)
    with ThreadPoolExecutor(max_workers=64) as pool:
        return [r for r in pool.map(sonder, reseau.hosts()) if r]


class Gestionnaire(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DOSSIER, **kw)

    def log_message(self, fmt, *args):
        if not self.path.startswith("/api/etat"):  # l'état est interrogé en boucle
            sys.stderr.write("  " + (fmt % args) + "\n")

    def repondre(self, code, obj):
        corps = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if not url.path.startswith("/api/"):
            if url.path.endswith("config.json"):
                return self.send_error(404)
            return super().do_GET()
        q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
        route = url.path[len("/api/"):]
        cfg = lire_config()
        ip = cfg.get("ip")

        if route == "decodeur":
            if "ip" in q:
                try:
                    ip = str(ipaddress.ip_address(q["ip"]))
                except ValueError:
                    return self.repondre(400, {"erreur": "Adresse IP invalide"})
                cfg["ip"] = ip
                ecrire_config(cfg)
            return self.repondre(200, {"ip": ip})

        if route == "recherche":
            trouves = chercher_decodeurs()
            if len(trouves) == 1:
                cfg["ip"] = trouves[0]["ip"]
                ecrire_config(cfg)
            return self.repondre(200, {"decodeurs": trouves, "ip": cfg.get("ip")})

        if not ip:
            return self.repondre(409, {"erreur": "Aucun décodeur configuré"})

        if route == "touche":
            if not q.get("code", "").isdigit():
                return self.repondre(400, {"erreur": "Code de touche manquant"})
            params = {"operation": "01", "key": q["code"], "mode": q.get("mode", "0")}
        elif route == "etat":
            params = {"operation": "10"}
        else:
            return self.repondre(404, {"erreur": "Route inconnue"})

        try:
            return self.repondre(200, appel_decodeur(ip, params))
        except (urllib.error.URLError, socket.timeout, OSError) as e:
            return self.repondre(502, {"erreur": f"Décodeur injoignable ({ip}) : {e}"})
        except ValueError:
            return self.repondre(502, {"erreur": "Réponse illisible du décodeur"})


def main():
    p = argparse.ArgumentParser(description="Relais télécommande décodeur Orange")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--decodeur", help="adresse IP du décodeur (sinon détection auto)")
    args = p.parse_args()

    cfg = lire_config()
    if args.decodeur:
        cfg["ip"] = args.decodeur
        ecrire_config(cfg)
    elif not cfg.get("ip"):
        print("Recherche du décodeur sur le réseau local…")
        trouves = chercher_decodeurs()
        if trouves:
            cfg["ip"] = trouves[0]["ip"]
            ecrire_config(cfg)
            print(f"  trouvé : {trouves[0]['nom']} ({cfg['ip']})")
        else:
            print("  aucun décodeur trouvé — réglez l'IP dans l'app (⚙︎).")

    serveur = ThreadingHTTPServer(("0.0.0.0", args.port), Gestionnaire)
    print(f"\nTélécommande prête : http://{ip_locale()}:{args.port}")
    print("Ouvrez cette adresse sur votre téléphone (même Wi-Fi). Ctrl+C pour arrêter.\n")
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
