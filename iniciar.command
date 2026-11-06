#!/bin/bash
# Mac: clique duas vezes neste arquivo para iniciar.
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 não encontrado. Instale em https://www.python.org/downloads/ e tente de novo."
  read -r -p "Pressione Enter para fechar."
  exit 1
fi
python3 iniciar.py
