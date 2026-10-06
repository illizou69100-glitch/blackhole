# Télécommande — décodeur TV d'Orange

Télécommande sur téléphone pour le décodeur TV d'Orange (UHD / TV 4 / TV 5), via le Wi-Fi de la maison.

## Pourquoi un petit serveur ?

Le décodeur reçoit ses commandes en HTTP simple sur `http://<ip-du-décodeur>:8080`.
Un navigateur refuse d'appeler cette adresse depuis une page web (CORS, et contenu mixte
si la page est en HTTPS). `serveur.py` sert donc l'app **et** relaie les commandes.
Il n'a aucune dépendance : Python 3.8 ou plus suffit.

## Démarrage

Sur un ordinateur (ou un Raspberry Pi) relié au même réseau que le décodeur :

```sh
cd orange
python3 serveur.py              # trouve le décodeur tout seul
# ou : python3 serveur.py --decodeur 192.168.1.20
```

Il affiche une adresse comme `http://192.168.1.50:8765` : ouvrez-la sur le téléphone,
puis « Ajouter à l'écran d'accueil ».

Le décodeur doit être allumé ou en veille légère pour répondre (en veille profonde, il ne répond pas sur le réseau).

## Fonctions

- Marche/veille, Menu, VOD, croix directionnelle + OK, Retour
- Volume et chaînes (maintenir appuyé pour répéter), Muet
- Retour rapide, lecture/pause, avance rapide, enregistrement
- Chaînes favorites modifiables (⚙︎) et pavé numérique
- État en direct (allumé / veille / hors ligne)
- Sur ordinateur : flèches, Entrée, Échap, `+`/`-`, `m`, PageUp/PageDown, chiffres

## Codes de l'API du décodeur

`GET /remoteControl/cmd?operation=01&key=<code>&mode=0` (`mode` : 0 appui, 1 appui long, 2 relâché)

| Touche | Code | Touche | Code |
|---|---|---|---|
| Marche | 116 | OK | 352 |
| Haut / Bas | 103 / 108 | Gauche / Droite | 105 / 106 |
| Vol + / − | 115 / 114 | Muet | 113 |
| Ch + / − | 402 / 403 | Retour | 158 |
| Menu | 139 | VOD | 393 |
| Lecture/pause | 164 | Enregistrer | 167 |
| Retour rapide | 168 | Avance rapide | 159 |
| 0 … 9 | 512 … 521 | | |

`operation=10` renvoie l'état (`activeStandbyState` : `0` allumé, `1` veille).
