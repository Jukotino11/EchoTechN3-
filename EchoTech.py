import getpass
import hashlib
import hmac
import json
import logging
import os
import re
import secrets

# pip install requests 
import requests

ARCHIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usuarios.json")
URL_GEO = "https://geocoding-api.open-meteo.com/v1/search"
URL_CLIMA = "https://api.open-meteo.com/v1/forecast"
URL_DOLAR = "https://cl.dolarapi.com/v1/cotizaciones/{}"
MONEDAS = ("USD", "EUR")
ESTADOS = {0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado", 3: "Nublado",
           45: "Niebla", 61: "Lluvia ligera", 63: "Lluvia moderada", 65: "Lluvia intensa",
           80: "Chubascos", 95: "Temporal"}

logging.basicConfig(filename="echotech_errores.log", level=logging.ERROR)
API_KEY = os.environ.get("API_KEY")


def hashear(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000).hex()


def cargar_usuarios():
    try:
        with open(ARCHIVO, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        logging.error("No se pudo leer los usuarios: %s", e)
        return {}


def registrar():
    usuarios = cargar_usuarios()
    nombre = input("Usuario (4-20 letras, números o _): ").strip().lower()
    password = getpass.getpass("Contraseña (mín. 8, con mayúscula, minúscula y número): ")
    if not re.fullmatch(r"\w{4,20}", nombre) or \
       not re.fullmatch(r"(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{8,}", password):
        print("Usuario o contraseña no cumplen los requisitos.")
        return
    if nombre in usuarios:
        print("No se pudo registrar con ese nombre de usuario.")
        return
    salt = secrets.token_bytes(16)  
    usuarios[nombre] = {"salt": salt.hex(), "hash": hashear(password, salt)}
    try:
        with open(ARCHIVO, "w", encoding="utf-8") as f:
            json.dump(usuarios, f, indent=2)
        print("Usuario registrado correctamente.")
    except OSError as e:
        logging.error("No se pudo guardar el usuario: %s", e)
        print("No se pudo registrar el usuario.")


def login():
    usuarios = cargar_usuarios()
    if not usuarios:
        print("No hay usuarios registrados. Primero debes registrarte.")
        return False
    for _ in range(3):  
        usuario = input("Usuario: ").strip().lower()
        password = getpass.getpass("Contraseña: ") 
        if not usuario or not password:
            print("Usuario y contraseña no pueden estar vacíos.")
            continue
        datos = usuarios.get(usuario)
        if datos and hmac.compare_digest(
                hashear(password, bytes.fromhex(datos["salt"])), datos["hash"]):
            print(f"Bienvenido/a, {usuario}.")
            return True
        print("Credenciales incorrectas.")  
    print("Demasiados intentos fallidos.")
    return False


def pedir(url, params=None):
    """GET con control de errores. Devuelve el JSON o None si algo falló."""
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
        logging.error("HTTP %s en %s", r.status_code, url)
        if r.status_code == 404:
            print("No se encontró la información solicitada (404).")
        elif r.status_code >= 500:
            print("El servicio externo tiene problemas. Intenta más tarde.")
        else:
            print(f"El servicio respondió con un error ({r.status_code}).")
    except ValueError:
        logging.error("Respuesta no JSON desde %s", url)
        print("El servicio entregó una respuesta inválida.")
    except requests.exceptions.RequestException as e:
        logging.error("Fallo de conexión en %s: %s", url, e)
        print("No se pudo conectar con el servicio externo.")
    return None


def clima():
    ciudad = input("Ciudad: ").strip()
    if not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñ ]{2,50}", ciudad):
        print("Ciudad inválida (solo letras, 2 a 50 caracteres).")
        return
    geo = pedir(URL_GEO, {"name": ciudad, "count": 1, "language": "es"})
    if not geo:
        return
    if not geo.get("results"):
        print("Ciudad no encontrada.")
        return
    lugar = geo["results"][0]
    datos = pedir(URL_CLIMA, {"latitude": lugar["latitude"], "longitude": lugar["longitude"],
                              "current": "temperature_2m,relative_humidity_2m,weather_code"})
    try:
        a = datos["current"]
        estado = 
        ESTADOS.get(a["weather_code"], "Sin descripción")
        print(f"{lugar['name']}, {lugar.get('country', '')}: {estado}, {a['temperature_2m']} °C, "
      f"Humedad {a['relative_humidity_2m']}%")
    except (KeyError, TypeError):
        print("Los datos del clima no son utilizables.")


def cambio():
    moneda = input(f"Moneda ({'/'.join(MONEDAS)}): ").strip().upper()
    if moneda not in MONEDAS:
        print("Moneda inválida.")
        return
    datos = pedir(URL_DOLAR.format(moneda.lower()))
    try:
        venta = float(datos["venta"])
    except (KeyError, TypeError, ValueError):
        print("Los datos del tipo de cambio no son utilizables.")
        return
    print(f"1 {moneda} = ${venta:,.2f} CLP")
    try:
        monto = float(input(f"Monto a pagar en {moneda}: ").replace(",", "."))
        if not 0 < monto <= 1e9:
            raise ValueError
    except ValueError:
        print("Monto inválido.")
        return
    print(f"Pago equivalente: ${monto * venta:,.0f} CLP")


def sesion():
    while True:
        op = input("\n1. Clima  2. Tipo de cambio  3. Cerrar sesión: ").strip()
        if op == "1":
            clima()
        elif op == "2":
            cambio()
        elif op == "3":
            break
        else:
            print("Opción inválida.")

def main():
    while True:
        op = input("\n1. Iniciar sesión  2. Registrarse  3. Salir: ").strip()
        if op == "1":
            if login():
                sesion()
        elif op == "2":
            registrar()
        elif op == "3":
            break
        else:
            print("Opción inválida.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e: 
        logging.error("Error no controlado: %s", e)
        print("Ocurrió un error inesperado.")
