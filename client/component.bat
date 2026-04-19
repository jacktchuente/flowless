#!/bin/bash

# Vérifiez si au moins 3 arguments sont passés (nom, objet et méthode)
if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <name> <object-name> <method> [additional-args...]"
  exit 1
fi

# Affecter les arguments à des variables
NAME=$1
OBJECT_NAME=$2
METHOD=$3
shift 3 # Supprime les trois premiers arguments pour laisser uniquement les arguments restants

# Construire la commande ng
ng g @kwyxyz/ngx-request:crud-component --standalone --name "/components/${NAME}" --object-name "${OBJECT_NAME}" --method "${METHOD}" "$@"
