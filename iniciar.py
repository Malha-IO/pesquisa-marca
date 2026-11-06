#!/usr/bin/env python3
"""Sobe a página e os dois processos de pesquisa, e abre o navegador.

    python3 iniciar.py        (Mac e Linux)
    py -3 iniciar.py          (Windows)

Ctrl+C encerra tudo. O que já foi pesquisado fica salvo; rodar de novo continua de onde parou.
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser

DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "8765"))


def port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def main():
    if sys.version_info < (3, 8):
        sys.exit("Este projeto precisa do Python 3.8 ou mais novo.")
    port = PORT
    while not port_free(port) and port < PORT + 20:
        port += 1
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PORT": str(port),
           "INPI_DELAY": os.environ.get("INPI_DELAY", "90"),
           "INPI_IDLE_EXIT": os.environ.get("INPI_IDLE_EXIT", "21600"),
           "PRES_DELAY": os.environ.get("PRES_DELAY", "8")}
    py = sys.executable
    procs = []
    for script, logname in (("app.py", "log_pagina.txt"),
                            ("verificar_inpi.py", None),
                            ("verificar_presenca.py", None)):
        out = open(os.path.join(DIR, logname), "a", encoding="utf-8") if logname else subprocess.DEVNULL
        procs.append(subprocess.Popen([py, os.path.join(DIR, script)], cwd=DIR, env=env,
                                      stdout=out, stderr=subprocess.STDOUT))
    url = f"http://localhost:{port}"
    for _ in range(40):
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:  # noqa: BLE001
            time.sleep(0.25)
    print(f"\nPágina no ar: {url}")
    print("Pesquisa do INPI e de domínios e redes rodando em segundo plano.")
    print("Deixe esta janela aberta. Ctrl+C encerra tudo.\n")
    webbrowser.open(url)
    try:
        while True:
            time.sleep(5)
            for p, name in zip(procs, ("página", "INPI", "domínios e redes")):
                if p.poll() is not None and not getattr(p, "_avisado", False):
                    p._avisado = True
                    print(f"O processo de {name} terminou (código {p.returncode}). Veja os arquivos log*.txt.")
    except KeyboardInterrupt:
        print("\nEncerrando…")
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    main()
