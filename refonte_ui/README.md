# Refonte UI — Flowless TV Control

Proposition de nouvelle interface pour `./client`, en HTML/CSS/JS statique avec données factices. **Aucun code Angular n'est repris** : l'objectif est de montrer une direction visuelle et des parcours, pas une implémentation.

## Comment regarder

Ouvrir `index.html` dans un navigateur (double-clic, ou `python3 -m http.server` depuis ce dossier). Toutes les pages sont reliées entre elles par la navigation réelle du prototype.

- `index.html` — Vue d'ensemble (nouveau)
- `sources.html` — Sources média
- `collections.html` — Collections
- `medias.html` — Médias
- `channels.html` — Catalogues et chaînes
- `channel-detail.html` — Détail d'une chaîne (page la plus riche : logo, ligne éditoriale, grille de blocs, calendriers, tous les dialogs)
- `editorial-planning.html` — Planification flexible (flux de segmentation bottom-up)

`assets/styles.css` et `assets/app.js` sont partagés par toutes les pages.

## Ce qui a changé, et pourquoi

Le code actuel (`./client`) empile 6 librairies UI différentes (Material, Nebular, PrimeNG, Bootstrap, ng-select, Tailwind), ce qui produit des incohérences visuelles fines (boutons, espacements, `<select>` natif non stylé sur l'écran Chaînes). Cette proposition part d'un seul système de composants.

**Identité visuelle** — le produit est une régie de diffusion (pseudo-TV) : le vocabulaire vient de là plutôt que d'un habillage SaaS générique.
- Neutres à dominante bleu-vert (« console de régie »), accent teal (`--signal`) pour les actions, et un orange distinct (`--cue`) réservé exclusivement au marqueur « à l'antenne / live » — comme une lumière de tally.
- Typographie IBM Plex (Condensed pour les titres, Sans pour le texte, Mono pour tout ce qui est horaire/durée/identifiant — cohérent avec un outil où les timecodes sont lus comme des données, pas du texte).
- **Couleur de catégorie fixe et non aléatoire** : dans l'app actuelle, chaque bloc de calendrier reçoit une teinte par hash de son id, donc deux blocs « Fiction » de deux chaînes différentes n'ont pas la même couleur. Ici, la couleur encode la nature du contenu (fiction, documentaire, live…) partout dans l'app, avec une légende visible sur l'écran Chaînes.

**Problèmes UX ciblés** (identifiés en lisant `channel-detail`, `grid-block-edit-dialog`, `channel-management`, `editorial-run-dialog`) :

1. **Aucune vue de synthèse** → `index.html` ajoute une page d'accueil : ce qui est en erreur, ce qui vient de se passer, ce qui est à l'antenne.
2. **Formulaires de règles à 9 sélecteurs multi-valeurs à plat** (`grid-block-edit-dialog`) → regroupés en 3 blocs lisibles *Autorisé / Préféré / Interdit*, saisie par tags plutôt que multi-select (voir le modal « bloc horaire » dans `channel-detail.html`).
3. **Suggestion IA en boîte noire** (le texte remplace directement les champs) → le panneau montre désormais un aperçu des changements proposés, à cocher un par un avant application.
4. **Sélecteur de catalogue en `<select>` HTML natif**, rupture de style → remplacé par un composant cohérent avec le reste des formulaires.
5. **Mode « Flexible » jargonneux** (candidates, segments, runs, sans explication) → `editorial-planning.html` en fait une page dédiée en 5 étapes, avec le vocabulaire expliqué en une phrase à chaque étape plutôt que des boutons secs.
6. **Génération longue avec seul un spinner bloquant** → les modals de génération (plan, planning, run de segmentation) affichent une séquence d'étapes avec progression, pour que l'utilisateur sache ce qui se passe.
7. **Filtres médias sans retour visuel** → chips de filtres actifs, retirables individuellement, recherche en direct plutôt qu'un bouton « Filtrer ».
8. **Logo dispersé entre deux boutons** (upload + menu « générer ») → une seule entrée « Modifier le logo » avec les trois options dedans.

## Ce qui n'a volontairement pas été détaillé

Certains dialogs secondaires du produit actuel (edition de catalogue, dialogs de détail en lecture seule) suivent les mêmes patterns que ceux construits ici (carte, `.field`, `.tag`, `.pill`) et n'ont pas été redessinés un par un — le système de composants dans `assets/styles.css` suffit à les étendre.
