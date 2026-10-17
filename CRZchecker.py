#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SERVER CHECKER PRO v3.6
Desarrollado por: CRZ
Compatible con QPython, Termux y Pydroid 3
"""

import os
import sys
import re
import time
import threading
import concurrent.futures
from datetime import datetime
import urllib.parse
import warnings

warnings.filterwarnings("ignore")

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    print("ERROR: Se requiere el módulo 'requests'. Instálalo con: pip install requests")
    sys.exit(1)

# ============================================================
# VARIABLES GLOBALES (EDITABLES)
# ============================================================
RUTA_COMBO = "/storage/emulated/0/servidores/"
RUTA_HITS = "/storage/emulated/0/hits/server/"
TIMEOUT = 5
MAX_WORKERS = 20
DEV = "CRZ"
VERSION = "3.6"


# ============================================================
# COLORES ANSI
# ============================================================
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"
    GOLD = "\033[38;5;220m"


# ============================================================
# MANEJO DE ARCHIVOS
# ============================================================
def crear_carpetas():
    """Crea las carpetas necesarias si no existen."""
    for ruta in (RUTA_COMBO, RUTA_HITS):
        try:
            if not os.path.exists(ruta):
                os.makedirs(ruta)
        except Exception as e:
            print(f"{Colors.RED}[!] No se pudo crear la carpeta {ruta}: {e}{Colors.RESET}")


def cargar_proxies(ruta_archivo):
    """
    Lee archivos robustamente en Android (QuickEdit / Pydroid / Termux).
    Maneja BOM, UTF-16 y el bug de línea gigante.
    """
    contenido = ""
    try:
        with open(ruta_archivo, "rb") as f:
            raw = f.read()

        try:
            contenido = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                contenido = raw.decode("utf-16", errors="ignore")
            except Exception:
                contenido = raw.decode("latin-1", errors="ignore")

        # Eliminar BOM
        contenido = contenido.replace("\ufeff", "")

        # Bug Android: todo en una sola línea gigante
        if "\n" not in contenido.strip():
            contenido = contenido.replace("http", "\nhttp")
            contenido = contenido.replace(",", "\n")
        else:
            contenido = contenido.replace(",", "\n")

    except Exception as e:
        print(f"{Colors.RED}[!] Error al leer {ruta_archivo}: {e}{Colors.RESET}")
        return []

    lineas = []
    for linea in contenido.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        if linea.startswith("#"):
            continue
        lineas.append(linea)

    return lineas


def extraer_host(url):
    """Normaliza y extrae host de una URL."""
    if not url:
        return None
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        url = "http://" + url
    try:
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return None
        puerto = parsed.port
        if puerto:
            return f"{parsed.scheme}://{hostname}:{puerto}"
        return f"{parsed.scheme}://{hostname}"
    except Exception:
        return None


# ============================================================
# VERIFICACIÓN DE SERVIDORES
# ============================================================
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; SM-G975F) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    )
}


def check_server(host):
    """Verifica un servidor. Retorna (host, 'ONLINE'|'OFFLINE')."""
    try:
        r = requests.get(
            host,
            timeout=TIMEOUT,
            verify=False,
            stream=True,
            headers=HEADERS,
            allow_redirects=False,
        )
        code = r.status_code
        try:
            r.close()
        except Exception:
            pass
        if code in (200, 301, 302, 401) or (200 <= code < 400):
            return (host, "ONLINE")
        return (host, "OFFLINE")
    except Exception:
        return (host, "OFFLINE")


# ============================================================
# ESCANEO MULTITHREAD
# ============================================================
def escanear_servidores(servers):
    if not servers:
        print(f"\n{Colors.YELLOW}[!] No hay servidores para escanear.{Colors.RESET}")
        return []

    # Preguntar workers
    try:
        entrada = input(
            f"{Colors.CYAN}Hilos/Workers (Enter = {MAX_WORKERS}): {Colors.RESET}"
        ).strip()
        if entrada == "":
            workers = MAX_WORKERS
        else:
            workers = int(entrada)
            if workers <= 0:
                workers = MAX_WORKERS
    except Exception:
        workers = MAX_WORKERS

    total = len(servers)
    hits = []
    print(f"\n{Colors.CYAN}▶ Iniciando escaneo de {total} servidor(es) con {workers} hilos...{Colors.RESET}\n")

    inicio = time.time()
    lock = threading.Lock()

    def procesar(host):
        h, estado = check_server(host)
        with lock:
            if estado == "ONLINE":
                print(f"{Colors.GREEN}✅ {h} -> ONLINE{Colors.RESET}")
                hits.append(h)
            else:
                print(f"{Colors.RED}❌ {h} -> OFFLINE{Colors.RESET}")
        return (h, estado)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(procesar, s) for s in servers]
            concurrent.futures.wait(futures)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[!] Escaneo interrumpido por el usuario.{Colors.RESET}")

    fin = time.time()
    tiempo_total = fin - inicio
    online = len(hits)
    offline = total - online
    tasa = (online / total * 100) if total > 0 else 0
    promedio = (tiempo_total / total) if total > 0 else 0

    # Resumen
    linea = "═" * 50
    print(f"\n{Colors.GOLD}{linea}{Colors.RESET}")
    print(f"{Colors.GOLD}{Colors.BOLD}         RESUMEN DEL ESCANEO{Colors.RESET}")
    print(f"{Colors.GOLD}{linea}{Colors.RESET}")
    print(f"{Colors.WHITE}Total     :{Colors.RESET} {total}")
    print(f"{Colors.GREEN}Online    :{Colors.RESET} {online}")
    print(f"{Colors.RED}Offline   :{Colors.RESET} {offline}")
    print(f"{Colors.CYAN}Tasa      :{Colors.RESET} {tasa:.2f}%")
    print(f"{Colors.CYAN}Tiempo    :{Colors.RESET} {tiempo_total:.2f}s")
    print(f"{Colors.CYAN}Promedio  :{Colors.RESET} {promedio:.3f}s/servidor")
    print(f"{Colors.GOLD}{linea}{Colors.RESET}")

    return hits


# ============================================================
# GUARDAR HITS
# ============================================================
def guardar_hits(hits):
    if not hits:
        print(f"\n{Colors.YELLOW}[!] No hay servidores ONLINE para guardar.{Colors.RESET}")
        return

    try:
        crear_carpetas()
        nombre = f"online_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        ruta = os.path.join(RUTA_HITS, nombre)
        linea = "═" * 50
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(ruta, "w", encoding="utf-8") as f:
            f.write(linea + "\n")
            f.write("🔥 SERVER CHECKER PRO 🔥\n")
            f.write(linea + "\n")
            f.write(f"📅 Fecha: {fecha}\n")
            f.write(f"📊 Total obtenido: {len(hits)}\n")
            f.write(linea + "\n\n")
            for i, h in enumerate(hits, 1):
                f.write(f"{i}. {h}\n")
            f.write("\n" + linea + "\n")
            f.write("🏢 Desarrollado por: CRZ\n")
            f.write(linea + "\n")

        print(f"\n{Colors.GREEN}[✓] Resultados guardados en:{Colors.RESET}")
        print(f"{Colors.CYAN}    {ruta}{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}[!] Error al guardar hits: {e}{Colors.RESET}")


# ============================================================
# MENÚ PRINCIPAL
# ============================================================
def menu_principal():
    crear_carpetas()

    while True:
        try:
            os.system("clear" if os.name == "posix" else "cls")
        except Exception:
            pass

        linea_c = "═" * 50
        div = "─" * 50

        print(f"{Colors.CYAN}{Colors.BOLD}{linea_c}{Colors.RESET}")
        print(f"{Colors.WHITE}{Colors.BOLD}   🔥 CHECKER DE SERVIDORES 🔥 v{VERSION}{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}{linea_c}{Colors.RESET}")
        print()
        print(f"  {Colors.GREEN}[1]{Colors.RESET} 📁 Escanear desde archivo")
        print(f"  {Colors.GREEN}[2]{Colors.RESET} ✍️  Escanear servidor manual")
        print(f"  {Colors.GREEN}[3]{Colors.RESET} 🚪 Salir")
        print()
        print(f"{Colors.CYAN}{div}{Colors.RESET}")
        print(f"{Colors.GRAY}Dev: {DEV} | Timeout: {TIMEOUT}s{Colors.RESET}")
        print()
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  AVISO IMPORTANTE:{Colors.RESET}")
        print(f"{Colors.WHITE}   Los archivos .txt deben estar en:{Colors.RESET}")
        print(f"   📁 {Colors.CYAN}{RUTA_COMBO}{Colors.RESET}")
        print(f"{Colors.WHITE}   Los hits se guardarán en:{Colors.RESET}")
        print(f"   📁 {Colors.CYAN}{RUTA_HITS}{Colors.RESET}")
        print(f"{Colors.GRAY}{div}{Colors.RESET}")
        print()
        print(f"{Colors.MAGENTA}{Colors.BOLD}                       ★ FRIENDS SCHOOL ★{Colors.RESET}")

        try:
            opcion = input(f"\n{Colors.WHITE}Opción > {Colors.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if opcion == "1":
            try:
                if not os.path.exists(RUTA_COMBO):
                    crear_carpetas()
                archivos = [a for a in os.listdir(RUTA_COMBO) if a.lower().endswith(".txt")]
            except Exception as e:
                print(f"\n{Colors.RED}[!] Error al listar archivos: {e}{Colors.RESET}")
                input(f"\n{Colors.GRAY}Presiona Enter para continuar...{Colors.RESET}")
                continue

            if not archivos:
                print(f"\n{Colors.YELLOW}[!] No hay archivos .txt en {RUTA_COMBO}{Colors.RESET}")
                input(f"\n{Colors.GRAY}Presiona Enter para continuar...{Colors.RESET}")
                continue

            print(f"\n{Colors.CYAN}Archivos disponibles:{Colors.RESET}")
            for i, a in enumerate(archivos, 1):
                print(f"  {Colors.GREEN}[{i}]{Colors.RESET} {a}")

            try:
                sel = input(f"\n{Colors.WHITE}Selecciona número: {Colors.RESET}").strip()
                idx = int(sel) - 1
                if idx < 0 or idx >= len(archivos):
                    raise ValueError
            except Exception:
                print(f"\n{Colors.RED}[!] Selección inválida.{Colors.RESET}")
                input(f"\n{Colors.GRAY}Presiona Enter para continuar...{Colors.RESET}")
                continue

            ruta_sel = os.path.join(RUTA_COMBO, archivos[idx])
            lineas = cargar_proxies(ruta_sel)
            servidores = []
            for l in lineas:
                h = extraer_host(l)
                if h:
                    servidores.append(h)

            if not servidores:
                print(f"\n{Colors.YELLOW}[!] El archivo no contiene servidores válidos.{Colors.RESET}")
                input(f"\n{Colors.GRAY}Presiona Enter para continuar...{Colors.RESET}")
                continue

            hits = escanear_servidores(servidores)
            guardar_hits(hits)
            input(f"\n{Colors.GRAY}Presiona Enter para continuar...{Colors.RESET}")

        elif opcion == "2":
            try:
                entrada = input(
                    f"\n{Colors.WHITE}Ingresa hosts (separados por coma): {Colors.RESET}"
                ).strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not entrada:
                print(f"\n{Colors.YELLOW}[!] No ingresaste ningún host.{Colors.RESET}")
                input(f"\n{Colors.GRAY}Presiona Enter para continuar...{Colors.RESET}")
                continue

            servidores = []
            for parte in entrada.split(","):
                h = extraer_host(parte)
                if h:
                    servidores.append(h)

            if not servidores:
                print(f"\n{Colors.RED}[!] No hay hosts válidos.{Colors.RESET}")
                input(f"\n{Colors.GRAY}Presiona Enter para continuar...{Colors.RESET}")
                continue

            hits = escanear_servidores(servidores)
            guardar_hits(hits)
            input(f"\n{Colors.GRAY}Presiona Enter para continuar...{Colors.RESET}")

        elif opcion == "3":
            print(f"\n{Colors.MAGENTA}¡Hasta luego! 👋{Colors.RESET}")
            break
        else:
            print(f"\n{Colors.RED}[!] Opción inválida.{Colors.RESET}")
            time.sleep(1)


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================
if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}[!] Programa interrumpido por el usuario.{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}[!] Error inesperado: {e}{Colors.RESET}")
        sys.exit(1)