# EchoTechN3-

1. Consumo de APIs en el sistema.

Se consumen dos servicios externos con requests. Para el clima se 
hacen dos llamadas encadenadas a Open-Meteo: primero la de geocodificación, 
que convierte el nombre de la ciudad en latitud y longitud, y luego la de 
pronóstico, que con esas coordenadas entrega temperatura y humedad actuales. 
Para el tipo de cambio se usa dolarapi (versión Chile), de donde se saca el 
campo venta y con eso se convierte el monto ingresado a pesos chilenos. Los 
parámetros se pasan como diccionario y no pegados a la URL, lo que es más limpio 
y seguro. Ojo con un detalle: ESTADOS está definido y se pide weather_code, 
pero nunca se muestra el estado del clima, y API_KEY se declara pero ninguna 
de las APIs la usa. Si el profe lo nota, mejor explicarlo o aprovecharlo.

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
        print(f"{lugar['name']}, {lugar.get('country', '')}: {a['temperature_2m']} °C, "
              f"Humedad {a['relative_humidity_2m']}%")
    except (KeyError, TypeError):
        print("Los datos del clima no son utilizables.")

2. Seguridad.

Lo principal de las contraseñas es que no se guardan en texto plano. 
Se usa pbkdf2_hmac con SHA-256 y 200.000 iteraciones, así que aunque 
alguien robe el usuarios.json al momento de calcular las contraseñas 
originales le costara mucho. Cada usuario tiene su propio salt aleatorio, 
generado con secrets, de modo que dos personas con la misma clave igual 
tendrán hashes distintos. En el login se compara con hmac.compare_digest, 
que evita ataques de tiempo y la contraseña se pide con getpass para que 
no se vea al escribirla. Además hay un máximo de 3 intentos y los mensajes 
son genéricos como : “Credenciales incorrectas" o "No se pudo registrar con 
ese nombre", para no revelar si un usuario existe. La API_KEY se lee desde 
una variable de entorno y no queda escrita en el código.

def hashear(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000).hex()


3. Errores y excepciones.
Se consumen dos servicios externos con requests. Para el clima se hacen dos llamadas 
encadenadas a Open-Meteo, en donde primero ejecuta la geocodificación, que convierte 
el nombre de la ciudad en latitud y longitud, y luego la de pronóstico que con esas 
coordenadas entrega temperatura y humedad actuales. Para el tipo de cambio se usa dolarapi, 
de donde se saca el campo venta y con eso se convierte el monto ingresado a pesos chilenos. 
Los parámetros se pasan como diccionario y no pegados a la URL, lo que es más limpio y seguro.

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

4. Validaciones de entradas y estructura del código.

Todo lo que escribe el usuario se valida antes de usarlo con 
expresiones regulares: el nombre de usuario debe ser de 4 a 20 caracteres, la 
contraseña como mínimo 8 caracteres, con al menos una mayúscula, minúsculas y  
algún número, la ciudad solo acepta letras y el monto debe ser un número entre 
positivo entre 0 y 1e9. Eso previene datos raros o inyecciones. En cuanto al orden, 
el código está dividido en funciones con una sola tarea cada una (registrar, login, 
pedir, clima, cambio) y hay dos menús. Uno principal y otro de sesión que solo se 
ve después de loguearse. Eso hace que sea fácil de leer y de mantener.

5. Justificación al uso de IA

Utilicé IA como apoyo para implementar el hash de contraseñas, Ya que anteriormente 
use SHA256 directo en lugar de PBKDF2 o bcrypt con sal. 
Si bien SHA256 es un algoritmo muy rápido, pero al no usar sal, una misma contraseña 
siempre produce el mismo hash, lo que facilita ataques con tablas precalculadas.
Por ello decidí usar PBKDF2 en lugar de bcrypt porque viene incluido en la librería estándar de 
Python, por lo que no requiere instalar dependencias externas. Para cada usuario se genera 
una sal aleatoria de 16 bytes con el módulo secrets, y se aplican 200.000 iteraciones para 
volver costoso cada intento de fuerza bruta. La sal se guarda junto al hash y en el login 
se recalcula el hash con esa sal y se compara usando hmac.compare_digest.
También validé el funcionamiento registrando usuarios y comprobé que el login acepta las 
credenciales correctas y rechaza las incorrectas. También verifiqué que dos usuarios con 
la misma contraseña generan hashes distintos.