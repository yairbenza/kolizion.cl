"""Construye el catalogo REAL (data/catalog.json) a partir de productos
verificados a mano en las tiendas piloto confirmadas (ver conversacion del
2026-08-19 en adelante: investigacion de 14 tiendas candidatas, de las
cuales 9 tenian sitio real -- Reserved se dejo afuera a proposito, ver nota
abajo).

IMPORTANTE -- de donde sale cada dato:
- nombre, precio_clp, link, imagen: sacados directo de la pagina real de
  cada tienda (WebFetch), NUNCA inventados.
- categoria/subtipo/genero/manga/largo: inferidos del nombre real del
  producto con reglas simples y explicitas (ver clasificar_prenda()) --
  no hay IA adivinando por fuera de lo que el nombre ya dice.
- corte: solo se asigna si (a) la palabra aparece literal en el nombre real
  del producto, o (b) se verifico a mano leyendo la ficha de un producto
  representativo de esa MISMA linea (ver diccionario VERIFICADO_A_MANO).
  Si no hay ninguna de las 2 senales, queda vacio -- no se inventa.
- material/gramaje: solo se carga donde se leyo explicito en una ficha real
  (verificado a mano), nunca por defecto.
- tallas_disponibles: rango general observado en una ficha real de esa
  tienda (aproximacion a nivel tienda, declarada como tal -- el stock real
  cambia todo el tiempo, esto es una foto del dia que se reviso).
- marca_autor: True para las 8 tiendas de esta lista -- todas son marcas
  chicas que disenan su propia ropa (no reventa de marcas grandes). Queda
  pendiente que el dueno del proyecto lo confirme (ver CLAUDE.md: esta
  decision es de KOLIZION, no de la tienda).

Reserved (reserved.cl) SE DEJO AFUERA a proposito: revisando su catalogo
real, es una tienda que revende ropa de marcas de lujo internacionales
(Balenciaga, Off-White, Palm Angels, BAPE, Supreme) a precios muy por
debajo del retail oficial -- no calza con "tiendas chicas independientes"
y hay riesgo real de que sean replicas, no producto autentico. No se cargo
ningun producto de ahi. Si el dueno del proyecto confirma que quiere
incluirla igual, se puede sumar despues.

Corre una sola vez a mano (igual que agregar_materiales.py, etc.) --
NO se re-corre solo. Hace un respaldo del catalogo mock antes de
reemplazarlo.
"""
import html
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CATALOG_PATH = BASE_DIR / "data" / "catalog.json"
BACKUP_PATH = BASE_DIR / "data" / "catalog_mock_backup.json"

OCASIONES_DEFAULT = ["carrete", "universidad", "junta social", "junta de amigos/skate park", "concierto/festival"]

# Ocasiones que se marca a mano por leer la ficha real de una linea
# concreta (nombre exacto del producto -> lo que corresponde). Ver
# docstring del modulo.
#
# 2026-08-20 -- pasada completa de retagueo: el usuario detecto que el
# buscador devolvia pocos/ningun resultado para bastantes cortes porque la
# primera version de este script solo taggeaba corte cuando la palabra
# aparecia LITERAL en el nombre (ej. "BAGGY", "OVERSIZE"), dejando 91 de
# 130 prendas sin corte -- el criterio real definido en CLAUDE.md pide
# comparar la ficha (descripcion/medidas) de cada producto contra la tabla
# de holgura, no solo el nombre. Se releyo la ficha real de al menos un
# producto representativo de CADA linea/coleccion (mismo diseño base,
# distinto color) y se generalizo el corte encontrado a toda esa linea --
# nunca entre lineas distintas. Donde la ficha no daba una senal clara de
# UN corte especifico (ej. selector de multiples cortes en el mismo
# producto, o texto ambiguo sin mencionar ninguno de los 5/4 cortes
# conocidos), se marca literal "sin corte definido" en vez de adivinar --
# pedido explicito del usuario, ver lista aparte que se imprime al final.
VERIFICADO_A_MANO = {
    # --- OVA Chile ---
    # "Basics Heavyweight": 100% algodon, 280g, regular fit (ficha propia).
    "Polera OVA Apparel Basics Heavyweight – Negra": {"material": "algodon_100", "gramaje_gsm": 280, "corte": "regular fit"},
    "Polera OVA Apparel Basics Heavyweight – Blanca": {"material": "algodon_100", "gramaje_gsm": 280, "corte": "regular fit"},
    "Polera OVA Apparel Basics Heavyweight – Arena": {"material": "algodon_100", "gramaje_gsm": 280, "corte": "regular fit"},
    # "Clasica": ficha dice "Su calce regular fit ofrece una silueta mas
    # clasica y ajustada" -- regular fit, sin selector de otros cortes.
    "POLERA OVA APPAREL CLÁSICA CELESTE": {"corte": "regular fit"},
    "POLERA OVA APPAREL CLÁSICA CAFÉ CHOCOLATE": {"corte": "regular fit"},
    "POLERA OVA APPAREL CLÁSICA VERDE": {"corte": "regular fit"},
    "POLERA OVA APPAREL CLÁSICA ROSADA": {"corte": "regular fit"},
    # "God's Plan": ficha dice "fit oversize relajado" / "Fit oversize para
    # maximo flow", sin selector de otros cortes.
    "POLERA OVA APPAREL GOD´S PLAN NEGRA (PREVENTA)": {"corte": "oversize"},
    "POLERA OVA APPAREL GOD´S PLAN BLANCA (PREVENTA)": {"corte": "oversize"},
    # "Retro": ficha dice "fit oversize relajado", sin selector.
    "POLERA OVA RETRO NEGRO": {"corte": "oversize"},
    # "The Cross", "Street Design", "OG", "United Brothers": la ficha real
    # ofrece 3 cortes SELECCIONABLES (Boxy fit / Oversize / Regular) en el
    # mismo producto -- no hay un unico corte que representar sin mentir,
    # asi que quedan "sin corte definido" (ver lista al usuario).
    "POLERA OVA APPAREL THE CROSS BLANCA": {"corte": "sin corte definido"},
    "POLERA OVA APPAREL THE CROSS CAFÉ (PREVENTA)": {"corte": "sin corte definido"},
    "POLERA OVA APPAREL STREET DESIGN NEGRO": {"corte": "sin corte definido"},
    "POLERA OVA APPAREL STREET DESIGN CREMA": {"corte": "sin corte definido"},
    "POLERA OVA APPAREL STREET DESIGN BLANCA": {"corte": "sin corte definido"},
    "POLERA OVA APPAREL OG BLANCA": {"corte": "sin corte definido"},
    "POLERA OVA APPAREL UNITED BROTHERS VERDE": {"corte": "sin corte definido"},
    # "Art Verde": ficha no menciona ninguno de los cortes conocidos.
    "POLERA OVA APPAREL ART VERDE (PREVENTA)": {"corte": "sin corte definido"},

    # --- Oversaints ---
    # "Knit": ficha dice "Standar fit" -> mapeado a regular fit (el mas
    # cercano de los conocidos).
    "Knit black": {"corte": "regular fit"},
    "Knit cream": {"corte": "regular fit"},
    "Knit mint green": {"corte": "regular fit"},
    # Poleron con cierre (zipper): ficha dice "Standar fit" tambien.
    "Poleron black zipper": {"corte": "regular fit"},
    "Poleron pink zipper": {"corte": "regular fit"},
    "Poleron Crema Anillo": {"material": "algodon_100", "corte": "regular fit"},
    # Linea "OS" (Oversaints confirma que "OS" = Oversize en la ficha real
    # de "Poleron OS Celeste"; "Gris Stone 777" comparte el mismo slug
    # "-os-" en su URL real, misma linea).
    "Poleron OS Celeste": {"corte": "oversize"},
    "Poleron Gris Stone 777": {"corte": "oversize"},
    # "Washed OVRST": verificado en ficha real -- "Standar fit" (igual que
    # Knit y el poleron con cierre), no depende de la sigla del nombre.
    "Poleron Washed OVRST": {"corte": "regular fit"},

    # --- El Pulento Style ---
    # Unicos 2 productos de la coleccion sin "oversize"/"overzise" en el
    # nombre (los otros 10 ya se detectan solos) -- la ficha tampoco
    # menciona ningun corte especifico, no se generaliza el de los otros.
    "CREAM & BROWN": {"corte": "sin corte definido"},
    "STREET AND TRIP": {"corte": "sin corte definido"},

    # --- Rapt ---
    # Linea "Common" (Hoodie + Long Sleeve): ficha real confirma "Fit:
    # Boxy fit" para ambos tipos de prenda de esta linea.
    "COMMON HOODIE MORO": {"corte": "boxy fit"},
    "COMMON HOODIE AZURE": {"corte": "boxy fit"},
    "COMMON HOODIE MOSS": {"corte": "boxy fit"},
    "COMMON LONG SLEEVE MORO": {"corte": "boxy fit"},
    "COMMON LONG SLEEVE AZURE": {"corte": "boxy fit"},
    "COMMON LONG SLEEVE MOSS": {"corte": "boxy fit"},
    # Linea "Foundation": la chaqueta si declara "Fit: Boxy fit" en su
    # ficha -- el pantalon de la misma linea NO se revisa por separado
    # (prenda inferior usa otra tabla de cortes), no se generaliza.
    "FOUNDATION JACKET": {"corte": "boxy fit"},
    "FOUNDATION TROUSER": {"corte": "sin corte definido"},
    "FOUNDATION TROUSER BLACK": {"corte": "sin corte definido"},
    # Linea "Shift"/"Grid" (zip, hoodie, tee, longsleeve): ficha real sin
    # ningun corte mencionado, en 2 productos representativos revisados.
    "GRID LAYER TEE MELANGE": {"corte": "sin corte definido"},
    "GRID LAYER TEE NAVY": {"corte": "sin corte definido"},
    "GRID SHIFT ZIP MELANGE": {"corte": "sin corte definido"},
    "GRID SHIFT ZIP NAVY": {"corte": "sin corte definido"},
    "RAW SHIFT HOODIE BLACK": {"corte": "sin corte definido"},
    "ACID SHIFT HOODIE": {"corte": "sin corte definido"},
    "DUAL SHIFT TEE SAND": {"corte": "sin corte definido"},
    "PATCH SHIFT ZIP BLACK": {"corte": "sin corte definido"},
    "SHIFT LONGSLEEVE BLACK": {"corte": "sin corte definido"},
    "RAW DENIM JACKET": {"corte": "sin corte definido"},
    "HOODIE ESSENCE CLASSIC II / PRE-ORDER": {"corte": "sin corte definido"},

    # --- Roots South ---
    # Familia "Knit Original"/"Knit Wear Conciously" (chalecos): ficha real
    # dice "estilo baggy"/"corte suelto" -- se mapea a oversize (el mas
    # cercano de los cortes de prenda superior a "suelto/holgado").
    "Black Knit Original": {"corte": "oversize"},
    "Black Knit Wear Conciously": {"corte": "oversize"},
    "Gray Knit Original": {"corte": "oversize"},
    "Gray Knit Wear Conciously": {"corte": "oversize"},
    # Familia "Layers"/"Club"/"Zipper"/"Mountain": ficha real (revisada en
    # 3 productos representativos) usa el mismo texto en los 3 -- "Combi-
    # nacion entre cortes Oversize & Boxy... caida recta que sobrepasa la
    # cintura" -- se etiqueta oversize (coincide con la definicion de la
    # tabla: "largo que pasa la cadera").
    "Black Origin Layers": {"corte": "oversize"},
    "Black Zipper Layers": {"corte": "oversize"},
    "Cream Zipper Rootsouth Est": {"corte": "oversize"},
    "Chocolate The Club": {"corte": "oversize"},
    "Cream Rootsouth Club": {"corte": "oversize"},
    "Chocolate Zipper": {"corte": "oversize"},
    "Chocolate Zipper Patch": {"corte": "oversize"},
    "Cream Mountain": {"corte": "oversize"},
    "Espresso Zip Knit": {"corte": "oversize"},
    # Unico producto sin ficha de corte disponible.
    "Hahave T-shirt Black": {"corte": "sin corte definido"},
    # Black Few Run (verificado en la primera pasada: 100% algodon
    # organico, 500g/m2, combinacion oversize/boxy -- boxy fit, el mas
    # cercano de los 2 conocidos).
    "Black Few Run": {"material": "algodon_100", "gramaje_gsm": 500, "corte": "boxy fit"},

    # --- Selvanegrawear ---
    # Linea "Polera" (12 estampados distintos sobre la misma polera base):
    # ficha real revisada ("Polera Logo Verde") confirma 100% algodon,
    # pero SIN ningun corte mencionado -- se generaliza el material (misma
    # polera base para toda la linea de estampados) pero no se inventa un
    # corte que la ficha no da.
    "Polera Logo Verde": {"material": "algodon_100", "corte": "sin corte definido"},
    "Polera Oranwutang Logo Negra": {"material": "algodon_100", "corte": "sin corte definido"},
    "Polera Oranwutang Micro Blanca": {"material": "algodon_100", "corte": "sin corte definido"},
    "Polera Pixa-Throwup Negra": {"material": "algodon_100", "corte": "sin corte definido"},
    "Polera SheoxTatto Negra": {"material": "algodon_100", "corte": "sin corte definido"},
    "Polera TagxGiro Burdeo": {"material": "algodon_100", "corte": "sin corte definido"},
    "Polera TagxGiro Negra": {"material": "algodon_100", "corte": "sin corte definido"},
    "Polera Pixa-Throwup Mora": {"material": "algodon_100", "corte": "sin corte definido"},
    "Polera Flubber": {"material": "algodon_100", "corte": "sin corte definido"},
    "Polera Mono Hiphop 50 Años Blanca": {"material": "algodon_100", "corte": "sin corte definido"},
    "Polera SheoxTatto": {"material": "algodon_100", "corte": "sin corte definido"},
    "Polera Logo Clásica": {"material": "algodon_100", "corte": "sin corte definido"},
    # "Canguro" (poleron con bolsillo canguro): ficha real revisada sin
    # ningun dato de corte ni material.
    "Canguro Calaka Letras Verdes": {"corte": "sin corte definido"},
    "Canguro Sunset Mujer": {"corte": "sin corte definido"},
    # Las 4 "Sudadera" se sacaron del catalogo (ver lista SELVANEGRA_POLERAS
    # mas abajo) -- eran musculosas de liquidacion, no polerones.

    # --- Rotten ---
    # Familia "Blur": ficha real dice "calce relajado de silueta boxy y
    # hombros caidos" -- boxy fit.
    "black blur tee": {"corte": "boxy fit"},
    "blur tee": {"corte": "boxy fit"},
    "red blur tee": {"corte": "boxy fit"},
    # Familia "Love Solitude": ficha real dice "corte regular fit con
    # mangas cortas y caida recta" -- regular fit.
    "black love solitude tee": {"corte": "regular fit"},
    "red love solitude tee": {"corte": "regular fit"},
    "white love solitude tee": {"corte": "regular fit"},
    # Familia "Longsleeve v2": ficha real dice "polera boxy fit con mangas
    # largas" -- boxy fit.
    "longsleeve black": {"corte": "boxy fit"},
    "longsleeve cherry": {"corte": "boxy fit"},
    "longsleeve dark blue": {"corte": "boxy fit"},
    "longsleeve olive green": {"corte": "boxy fit"},
    # Familia "Gia" (ya verificada en la primera pasada).
    "gia tee": {"corte": "straight"},
    "gia tee (regular fit)": {"corte": "regular fit"},
    "white gia tee": {"corte": "straight"},
    "white gia tee (regular fit)": {"corte": "regular fit"},
    "gia longsleeve": {"corte": "straight"},
    "gia longsleeve (regular fit)": {"corte": "regular fit"},
    # Productos sueltos, sin ficha revisada -- ninguna otra linea con la
    # que generalizar.
    "bedrot longsleeve": {"corte": "sin corte definido"},
    # "Baby tee" es por definicion corto y AJUSTADO (ver ES_BABY_TEE arriba)
    # -- slim fit, el mas cercano de los conocidos a "ajustado".
    "dnd baby tee": {"corte": "slim fit"},
    "rotten keychain tee": {"corte": "sin corte definido"},

    # --- Simpl. ---
    # "PANTALON CARGO WOODLAND (CAMO)": el nombre visible no dice "baggy",
    # pero la URL real del producto es "pantalon-baggy-blank-gris-melange-
    # copia" -- confirma que es la misma linea baggy que el resto del
    # catalogo de pantalones de Simpl.
    "PANTALON CARGO WOODLAND (CAMO)": {"corte": "baggy"},
    # "POLERA .TXT": la ficha real vende el MISMO producto en 3 cortes
    # seleccionables (Oversize / Boxy / Regular) -- no hay un unico corte
    # que representar sin mentir, queda sin corte definido.
    "POLERA .TXT (ACID WASH)": {"corte": "sin corte definido"},
    "POLERA .TXT (BLANCA)": {"corte": "sin corte definido"},
    "POLERA .TXT (CAFÉ)": {"corte": "sin corte definido"},

    # --- AbsolutelyWrong (2026-08-22) --- ficha real no menciona corte para
    # la linea "Basico Heavyweight" (pantalon) ni para "Short Blacksummer" --
    # verificado por FOTO real del catalogo (ver docs/catalogo_real.md):
    # pantalon ancho de pierna recta y caida suelta, short amplio en el
    # muslo -> baggy en los 2. Mismo corte generalizado a todos los colores
    # de la misma linea (preventa incluida), nunca entre lineas distintas.
    "PANTALON BASICO HEAVYWEIGHT (ROSADO)": {"material": "algodon_100", "gramaje_gsm": 400, "corte": "baggy"},
    "PANTALON BASICO HEAVYWEIGHT (CAFE)": {"material": "algodon_100", "gramaje_gsm": 400, "corte": "baggy"},
    "PANTALON MARINO (HEAVYWEIGHT)": {"material": "algodon_100", "gramaje_gsm": 400, "corte": "baggy"},
    "PANTALON BASICO HEAVYWEIGHT NEGRO (PREVENTA)": {"material": "algodon_100", "gramaje_gsm": 400, "corte": "baggy"},
    "PANTALON BASICO HEAVYWEIGHT GRIS (PREVENTA)": {"material": "algodon_100", "gramaje_gsm": 400, "corte": "baggy"},
    "PANTALON BASICO HEAVYWEIGHT AZUL MARINO (PREVENTA)": {"material": "algodon_100", "gramaje_gsm": 400, "corte": "baggy"},
    "PANTALON BASICO HEAVYWEIGHT BURDEO (PREVENTA)": {"material": "algodon_100", "gramaje_gsm": 400, "corte": "baggy"},
    "SHORT BLACKSUMMER (HEAVYWEIGHT)": {"corte": "baggy"},
    # "Polerón Básico Heavyweight": la ficha dice literal "Boxy Regular Fit"
    # -- frase ambigua (mezcla 2 cortes), asi que se reviso la foto real
    # para desempatar: silueta ancha/cuadrada con hombros caidos, calza con
    # "boxy fit" de la tabla, no con "regular fit". Corte generalizado a
    # los 5 colores preventa (misma linea).
    "POLERON BASICO HEAVYWEIGHT NEGRO (PREVENTA)": {"material": "algodon_100", "gramaje_gsm": 400, "corte": "boxy fit"},
    "POLERON BASICO HEAVYWEIGHT GRIS (PREVENTA)": {"material": "algodon_100", "gramaje_gsm": 400, "corte": "boxy fit"},
    "POLERON BASICO HEAVYWEIGHT AZUL MARINO (PREVENTA)": {"material": "algodon_100", "gramaje_gsm": 400, "corte": "boxy fit"},
    "POLERON BASICO HEAVYWEIGHT BURDEO (PREVENTA)": {"material": "algodon_100", "gramaje_gsm": 400, "corte": "boxy fit"},
    "POLERON BASICO HEAVYWEIGHT ROSADO (PREVENTA)": {"material": "algodon_100", "gramaje_gsm": 400, "corte": "boxy fit"},
    # "Polerón Gay Boxy Oversized": nombre dice "Boxy Oversized" -- se deja
    # que detectar_corte() lo tome como "oversize" (el ultimo/mas fuerte de
    # los 2 descriptores en el nombre), consistente con como se maneja en
    # otras tiendas cuando el nombre combina 2 palabras de corte.
    "POLERON GAY BOXY OVERSIZED": {"material": "mezcla_algodon_poliester"},

    # --- ForceBlack (2026-08-22/23) --- TODA la ficha real usa el mismo
    # texto de plantilla "Forceblack — Loose fit" (verificado en 2 productos
    # representativos, "Black Ripped" y "Cloud denim cargo") -- "loose fit"
    # se mapea a "baggy" (el mas cercano de la tabla de prenda inferior a
    # "holgado/suelto"), confirmado tambien por foto (pierna ancha, caida
    # suelta). Se generaliza a TODA la linea de jeans -- misma marca, mismo
    # texto de ficha, mismo corte real. "Short blackrugged" no repite el
    # texto de ficha pero la foto muestra el mismo corte ancho -> mismo
    # corte por foto. "Thunder Black" no trae "jean" en el nombre -- ficha
    # real confirma que es un pantalon/jean de la misma linea (categoria
    # override).
    "Black acid wash jeans": {"corte": "baggy"},
    "Black bur jeans": {"corte": "baggy"},
    "Black diamond flare jeans": {"corte": "baggy"},
    "Black Ripped jeans": {"corte": "baggy"},
    "Blessing VVS jeans": {"corte": "baggy"},
    "Blue Glow VVS jeans": {"corte": "baggy"},
    "Blue motion cargo flare jeans": {"corte": "baggy"},
    "Cloud denim cargo jeans": {"corte": "baggy"},
    "Denim diamond flare jeans": {"corte": "baggy"},
    "Denim Essentials jeans": {"corte": "baggy"},
    "Essentials Black jeans": {"corte": "baggy"},
    "Essentials Blue jeans": {"corte": "baggy"},
    "Iron Black jeans": {"corte": "baggy"},
    "Iron Blue Cargo jeans": {"corte": "baggy"},
    "Iron grey jeans": {"corte": "baggy"},
    "Iron Ice jeans": {"corte": "baggy"},
    "Light Ripped jeans": {"corte": "baggy"},
    "Short blackrugged": {"corte": "baggy", "subtipo": "cargo"},
    "Sky blue cargo jeans": {"corte": "baggy"},
    "Sky frost jeans": {"corte": "baggy"},
    "Thunder Black": {"corte": "baggy", "categoria": "pantalon", "subtipo": "jeans"},
    "Thunder VVS jeans": {"corte": "baggy"},

    # --- Floating (2026-08-23) --- linea "Perfect Fit" (polerones): ficha
    # dice "combinacion entre boxy y oversize" (texto ambiguo, mezcla 2
    # cortes) -- se reviso la FOTO real de "Noir Pulse" y "FLTNG Zip Hoodie"
    # (hombros caidos, mangas anchas, largo que pasa la cadera) y se
    # desempato a "oversize" por calzar mejor con esa definicion de tabla.
    # Generalizado a toda la linea "Perfect Fit" (Noir Pulse/Nuit Volt +
    # variantes de color, FLTNG Zip). "Aero pants"/"Hover Denim"/jorts:
    # ficha dice literal "calce holgado"/"loose fit" -> baggy. "Polera
    # Esencial": ficha dice "ajustado" pero la FOTO muestra silueta ancha y
    # cuadrada (boxy), no ajustada -- se prioriza la foto real por sobre el
    # texto de marketing ambiguo. "Baby tee": ficha aclara explicitamente
    # que NO es corto/crop (a pesar del nombre) y calce "ajustado" -> slim
    # fit, largo normal (no se fuerza el largo "crop" que normalmente
    # implica el subtipo baby tee -- ver aviso en docs/catalogo_real.md).
    "Aero pants": {"categoria": "pantalon", "corte": "baggy"},
    # "Baby tee" hace match con la regla automatica ES_BABY_TEE (categoria
    # "top", largo "crop"), pero LA FICHA REAL de este producto puntual dice
    # explicitamente "no es corto" y da medidas de largo normal -- se
    # respeta la ficha real por sobre la regla generica del nombre.
    "Baby tee": {"corte": "slim fit", "largo": "normal"},
    "FLTNG Zip Hoodie": {"categoria": "poleron", "corte": "oversize"},
    "FLTNG ZIP V2": {"categoria": "poleron", "corte": "oversize"},
    "Hover Denim": {"corte": "baggy"},
    # "Noir Pulse"/"Nuit Volt": el nombre no trae ninguna palabra clave de
    # categoria (ni "hoodie"/"poleron"/"zip") -- confirmado por ficha real
    # que son polerones (franela de algodon, gorro doble forrado).
    "Noir Pulse": {"categoria": "poleron", "corte": "oversize"},
    "Noir Pulse - Aureum": {"categoria": "poleron", "corte": "oversize"},
    "Noir Pulse - Emerald": {"categoria": "poleron", "corte": "oversize"},
    "Noir Pulse - Morganite": {"categoria": "poleron", "corte": "oversize"},
    "Nomad Jort": {"categoria": "shorts", "corte": "baggy", "subtipo": "jeans"},
    "Nuit Volt": {"categoria": "poleron", "corte": "oversize"},
    "Nuit Volt - Heaven": {"categoria": "poleron", "corte": "oversize"},
    "Nuit Volt - Void": {"categoria": "poleron", "corte": "oversize"},
    "Polera Esencial - Blanca": {"corte": "boxy fit"},
    "Polera Esencial - Verde botella": {"corte": "boxy fit"},
    "Shadow Jorts": {"categoria": "shorts", "corte": "baggy", "subtipo": "jeans"},
    "Stealth Jorts": {"categoria": "shorts", "corte": "baggy", "subtipo": "jeans"},

    # --- BANG GANG (2026-08-23) --- ficha real: TODAS las poleras usan
    # "fit regular unisex" (verificado en "Polera 333 Black", texto de
    # plantilla de la tabla de medidas). TODOS los polerones dicen literal
    # "Corte boxy fit" (verificado en 2 productos representativos,
    # "Poleron 333 Dollars Black" y "Poleron Bloodline Blue Black").
    # Las poleras con "Boxy" en el nombre ya se auto-detectan solas
    # (no necesitan entrada aca). "Cargo Parachute": nombre dice "Cargo"
    # pero clasificar_prenda() no lo reconoce sin la palabra "pantalon"
    # (igual que "Thunder Black" en ForceBlack) -- categoria/subtipo a
    # mano, corte "baggy" confirmado por foto (pantalon cargo ancho).
    "Polera Crystals Logo Acid Wash": {"corte": "regular fit"},
    "Poleron Crystals Logo BG": {"corte": "boxy fit"},
    "Poleron Heavy Crystals": {"corte": "boxy fit"},
    "Poleron Crystals Logo BG": {"corte": "boxy fit"},
    "Polera Crystals Logo Heavyweight Black": {"corte": "regular fit"},
    "Polera Crystals Logo Heavyweight Grey": {"corte": "regular fit"},
    "Poleron 333 White Black Chance": {"corte": "boxy fit"},
    "Poleron 333 Pink Black Chance": {"corte": "boxy fit"},
    "Cargo Parachute Grey": {"categoria": "pantalon", "subtipo": "cargo", "corte": "baggy"},
    "Cargo Parachute Black": {"categoria": "pantalon", "subtipo": "cargo", "corte": "baggy"},
    "Polera Reflex Hard Gvng": {"corte": "regular fit"},
    "Polera Ak-47 Reflectante": {"corte": "regular fit"},
    "Poleron Bloodline Blue Black": {"corte": "boxy fit"},
    "Polera Toyota Supra BG": {"corte": "regular fit"},
    "Poleron Bloodline Grey Black": {"corte": "boxy fit"},
    "Polera Scarface Red V2": {"corte": "regular fit"},
    "Polera The Godfather Corleone": {"corte": "regular fit"},
    "Polera Los Sopranos": {"corte": "regular fit"},
    "Polera Scarface Blue V3": {"corte": "regular fit"},
    "Polera BANG GANG Mafia": {"corte": "regular fit"},
    "Polera BG Except Black": {"corte": "regular fit"},
    "Polera R34 GT-R Black": {"corte": "regular fit"},
    "Polera Butterfly Effect White": {"corte": "regular fit"},
    "Polera The Final Sky": {"corte": "regular fit"},
    "Polera Jason FT13 BG": {"corte": "regular fit"},
    "Polera Travis Scott": {"corte": "regular fit"},
    "Polera Mac Miller": {"corte": "regular fit"},
    "Polera No Love Just Money": {"corte": "regular fit"},
    "Polera Fortune Black": {"corte": "regular fit"},
    "Polera Post Malone": {"corte": "regular fit"},
    "Polera Scarface": {"corte": "regular fit"},
    "Poleron 333 Red Special": {"corte": "boxy fit"},
    "Poleron Bloodline Red Black": {"corte": "boxy fit"},
    "Poleron Shooters Triple White Blue": {"corte": "boxy fit"},
    "Poleron Shooters Blue Black": {"corte": "boxy fit"},
    "Poleron Shooters Pink Black": {"corte": "boxy fit"},
    "Poleron Shooters Blue Melange": {"corte": "boxy fit"},
    "Poleron Shooters Pink Melange": {"corte": "boxy fit"},
    "Poleron Shooters Ultra Melange": {"corte": "boxy fit"},
    "Poleron Shooters Ultra Pink": {"corte": "boxy fit"},
    "Polera Shooters Pink White": {"corte": "regular fit"},
    "Polera Shooters Blue White": {"corte": "regular fit"},
    "Polera Shooters Blue Black": {"corte": "regular fit"},
    "Polera Shooters Pink Black": {"corte": "regular fit"},
    "Poleron Angels Or Visitors": {"corte": "boxy fit"},
    "Polera Angels Or Visitors": {"corte": "regular fit"},
    "Poleron Graff BG": {"corte": "boxy fit"},
    "Polera Graff BG": {"corte": "regular fit"},
    "Poleron No Love Just Money": {"corte": "boxy fit"},
    "Polera ESTHER BG": {"corte": "regular fit"},
    "Poleron ESTHER BG": {"corte": "boxy fit"},
    "Poleron The Final Sky": {"corte": "boxy fit"},
    "Polera Chuky BG": {"corte": "regular fit"},
    "Polera 50 Cent BG": {"corte": "regular fit"},
    "Polera Ice Cube BG": {"corte": "regular fit"},
    "Polera Eminem BG": {"corte": "regular fit"},
    "Polera Drake BG": {"corte": "regular fit"},
    "Polera 333 White": {"corte": "regular fit"},
    "Polera Lights At Night Orange": {"corte": "regular fit"},
    "Polera Loyalty Ultra White": {"corte": "regular fit"},
    "Polera Loyalty Purple White": {"corte": "regular fit"},
    "Polera FM Diamonds Sky Blue Black": {"corte": "regular fit"},
    "Polera Bloodline Grey Black": {"corte": "regular fit"},
    "Polera Fire Angel": {"corte": "regular fit"},
    "Polera The World Is Yours": {"corte": "regular fit"},
    "Polera Butterfly Effect Black": {"corte": "regular fit"},
    "Polera 333 Black": {"corte": "regular fit"},
    "Polera Money In Heaven Black": {"corte": "regular fit"},
    "Polera BG Except White": {"corte": "regular fit"},
    "Polera Fortune White": {"corte": "regular fit"},
    "Polera Mustang BG": {"corte": "regular fit"},
    "Polera Lights At Night Grey": {"corte": "regular fit"},
    "Polera Silence Black": {"corte": "regular fit"},
    "Polera Loyalty Yellow Black": {"corte": "regular fit"},
    "Polera FM Diamonds Sky Blue White": {"corte": "regular fit"},
    "Polera FM Diamonds Green White": {"corte": "regular fit"},
    "Polera FM Diamonds Green Black": {"corte": "regular fit"},
    "Polera Tribal Engine Black": {"corte": "regular fit"},
    "Polera Tribal Engine White": {"corte": "regular fit"},
    "Polera Porsche 911 Black": {"corte": "regular fit"},
    "Polera Porsche 911 White": {"corte": "regular fit"},
    "Polera Godzilla Blue": {"corte": "regular fit"},
    "Polera Godzilla Red": {"corte": "regular fit"},
    "Poleron 333 Dollars Black": {"corte": "boxy fit"},
    "Polera Bloodline Red Black": {"corte": "regular fit"},
    "Polera Bloodline Blue Black": {"corte": "regular fit"},
    "Polera Bloodline Blue White": {"corte": "regular fit"},
    "Polera Bloodline Red White": {"corte": "regular fit"},

    # --- UNK Chile (2026-08-23) --- "Hoodie"/"Poleron"/"Polar Hoodie":
    # foto real confirma silueta oversize (hombros caidos, mangas anchas,
    # largo pasa cadera), verificado en "Hoodie Unk. Acid Blue". "Jogger":
    # foto muestra pantalon de calce recto tipo track pant (ni ajustado ni
    # suelto), verificado en "Jogger UNK. Euro Gray" -> straight fit.
    # "Jogger Cargo...": nombre dice "Cargo" pero clasificar_prenda() no
    # lo reconoce sin "pantalon"/"jean"/"denim" -- categoria/subtipo a
    # mano. "Short Unk. Tiger...": foto muestra calce recto (ni baggy ni
    # ajustado) -> straight fit, verificado en "Short Unk. Tiger Gray".
    # "Jacket"/"Polera" (graficas/tie-dye): sin senal de corte clara ni en
    # texto ni en foto (formas de producto muy variadas) -- quedan
    # "sin corte definido", no se adivina.
    "Hoodie Unk. Acid Blue": {"corte": "oversize"},
    "Jogger Cargo UNK. Acid Yellow": {"categoria": "pantalon", "subtipo": "cargo", "corte": "straight fit"},
    "Jogger Cargo Unk. Acid Black": {"categoria": "pantalon", "subtipo": "cargo", "corte": "straight fit"},
    "Hoodie Unk. Acid Beige": {"corte": "oversize"},
    "Hoodie Unk. Acid Pink": {"corte": "oversize"},
    "Hoodie Unk. Acid Green": {"corte": "oversize"},
    "Hoodie Unk. Acid Black": {"corte": "oversize"},
    "Hoodie UNK. Smile Pink": {"corte": "oversize"},
    "Jogger Unk. Generation Black": {"categoria": "pantalon", "corte": "straight fit"},
    "Hoodie Camaleón Safary Green": {"corte": "oversize"},
    "Polerón Camaleón Skate Black": {"corte": "oversize"},
    "Polerón Camaleón Skate White": {"corte": "oversize"},
    "Polerón Unk. Black & White": {"corte": "oversize"},
    "Polerón Unk. Focus Colors": {"corte": "oversize"},
    "Polerón Unk. Focus Orange": {"corte": "oversize"},
    "Polar Hoodie UNK. Blue": {"corte": "oversize"},
    "Polar Hoodie UNK. Black": {"corte": "oversize"},
    "Hoodie UNK. Tie Dye Jade": {"corte": "oversize"},
    "Hoodie UNK. Original White": {"corte": "oversize"},
    "Hoodie UNK. Original Calypso": {"corte": "oversize"},
    "Jogger UNK. Euro Gray": {"categoria": "pantalon", "corte": "straight fit"},
    "Jogger UNK. Euro Calypso": {"categoria": "pantalon", "corte": "straight fit"},
    "Jogger Unk. Green": {"categoria": "pantalon", "corte": "straight fit"},
    "Hoodie Block White": {"corte": "oversize"},
    "Hoodie Unk. Spiral Mint": {"corte": "oversize"},
    "Jogger Unk. Dark": {"categoria": "pantalon", "corte": "straight fit"},
    "Hoodie Unk. Spiral Blue": {"corte": "oversize"},
    "Hoodie Unk. Old Brown": {"corte": "oversize"},
    "Hoodie Unk. Old Black": {"corte": "oversize"},
    "Hoodie UNK. Smile Mint": {"corte": "oversize"},
    "Hoodie Unk. Peace Steel": {"corte": "oversize"},
    "Short Unk. Tiger Gray": {"corte": "straight fit"},
    "Polera UNK. Infinity Black": {"corte": "sin corte definido"},
    "Polera UNK. Infinity Verde Amarelo": {"corte": "sin corte definido"},
    "Polera UNK. Infinity Sweet Lilac": {"corte": "sin corte definido"},
    "Polera Unk. Infinity Greensky": {"corte": "sin corte definido"},
    "Polera Unk. Infinity Shine White": {"corte": "sin corte definido"},
    "Jacket Cortaviento Carbon Color Print": {"corte": "sin corte definido"},
    "Jacket Cortaviento Blue Snow": {"corte": "sin corte definido"},
    "Jacket Cortaviento Sky Blue": {"corte": "sin corte definido"},
    "Jacket Cortaviento Crema Color Print": {"corte": "sin corte definido"},
    "Polera Unk. New Plane Steel Green": {"corte": "sin corte definido"},
    "Polera UNK. Spiral White": {"corte": "sin corte definido"},
    "Polera UNK. Pastel White": {"corte": "sin corte definido"},
    "Polera UNK. Head Pro Black": {"corte": "sin corte definido"},
    "Polera UNK. Pastel Black": {"corte": "sin corte definido"},
    "Polera UNK. Head Pro Light Blue": {"corte": "sin corte definido"},
    "Polera Camaleón Army White": {"corte": "sin corte definido"},
    "Polera UNK. Future Green": {"corte": "sin corte definido"},
    "Polera Unk. Skate Large White": {"corte": "sin corte definido"},
    "Polera Unk. Skate Large Black": {"corte": "sin corte definido"},
    "Polera Unk. Peace Black": {"corte": "sin corte definido"},
    "Polera Unk. Peace Orange": {"corte": "sin corte definido"},
    "Polera Unk. Hero Peach": {"corte": "sin corte definido"},
    "Polera Unk. Hero Lilac": {"corte": "sin corte definido"},
    "Polera Unk. Large Rainbow Pink": {"corte": "sin corte definido"},
    "Polera Unk. Large Rainbow Blue": {"corte": "sin corte definido"},
    "Jacket Unk. Peak Pink": {"corte": "sin corte definido"},
    "Jacket Unk. Peak Orange": {"corte": "sin corte definido"},
    "Jacket Unk. Mountain Blue": {"corte": "sin corte definido"},
    "Polera UNK. Premium Burgundy": {"corte": "sin corte definido"},
    "Polera UNK. Tie Dye Duo Mint": {"corte": "sin corte definido"},
    "Polera Camaleón Tie Dye Blue": {"corte": "sin corte definido"},
    "Jacket Unk. Mountain Brown": {"corte": "sin corte definido"},
    "Polera Camaleón Tie Dye Burgundy": {"corte": "sin corte definido"},
    "Polera Tie dye World Blue": {"corte": "sin corte definido"},
    "Polera Unk. Skate Light Blue": {"corte": "sin corte definido"},
    "Jacket Cortaviento UNK. 4k Colors": {"corte": "sin corte definido"},
    "Jacket Cortaviento UNK. 4K Black": {"corte": "sin corte definido"},
    "Jacket Cortaviendo unk. 4K Blue": {"corte": "sin corte definido"},
    "Jacket Cortaviento Unk. Crack Gray": {"corte": "sin corte definido"},
    "Jacket Cortaviento Unk. Rainbow Blue": {"corte": "sin corte definido"},
    "Polera Unk. Skate Pink": {"corte": "sin corte definido"},
    "Jacket Cortaviento Unk. Rainbow Pink": {"corte": "sin corte definido"},
    "Jacket Cortaviento Monster Blue": {"corte": "sin corte definido"},
    "Jacket Cortaviento Monster White": {"corte": "sin corte definido"},
    "Jacket Cortaviento UNK. Wire White": {"corte": "sin corte definido"},
    "Polera UNK. Pocket Pink": {"corte": "sin corte definido"},
    "Polera UNK. Pocket Light Blue": {"corte": "sin corte definido"},
    "Polera UNK. Summer Mint": {"corte": "sin corte definido"},
    "Polera Unk. Marley Red": {"corte": "sin corte definido"},
    "Jacket Cortaviento Camaleón Head Blue": {"corte": "sin corte definido"},
    "Jacket Cortaviento Camaleón Head Black": {"corte": "sin corte definido"},
    "Jacket Cortaviento Unk. Snowflake White": {"corte": "sin corte definido"},
    "Jacket Cortaviento Unk. Noodles Pink": {"corte": "sin corte definido"},
    "Jacket Cortaviento Unk. Noodles Tiffany": {"corte": "sin corte definido"},
    "Jacket Cortaviento Unk. Fall Calypso": {"corte": "sin corte definido"},
    "Polera Camaleón Dynamic Turquoise": {"corte": "sin corte definido"},
    "Polera Camaleón Dynamic Coral": {"corte": "sin corte definido"},
    "Polera Camaleón Crazy Black": {"corte": "sin corte definido"},
    "Polera Camaleón Crazy Oil Blue": {"corte": "sin corte definido"},
    "Polera Kmaleón Tie Dye Pink": {"corte": "sin corte definido"},
    "Polera UNK. Tie Dye Duo Steel": {"corte": "sin corte definido"},
    "Polera UNK. Plane Blue": {"corte": "sin corte definido"},
    "Polera UNK. Spiral Black": {"corte": "sin corte definido"},
    "Short Unk. Tiger Blue": {"corte": "straight fit"},
    "Polerón Unk. Cubox Fluor": {"corte": "oversize"},
    "Polerón Unk. Cubox Lilac": {"corte": "oversize"},
    "Jogger Unk. Rainbow Pink": {"categoria": "pantalon", "corte": "straight fit"},
    "Jogger Unk. Rainbow blue": {"categoria": "pantalon", "corte": "straight fit"},
    "Joggers Unk. Generation Blue": {"categoria": "pantalon", "corte": "straight fit"},
    "Hoodie Unk. Level Orange": {"corte": "oversize"},
    "Hoodie Camaleón Safary Blue": {"corte": "oversize"},
    # --- Doslobos (2026-08-23) --- "Hoodie"/"Poleron": ficha real dice
    # literal "Oversize-fit" (verificado en 2 productos representativos).
    # "Sweater"/"Cardigan": mismo texto "Oversize-fit", pero sin mencion
    # de capucha -- se tratan como chaleco (mismo criterio que "chaleco"
    # generico de la app), no poleron. "Crewneck" explicito en el nombre
    # -> sin capucha por definicion de la palabra (cuello redondo, no
    # capucha), aunque siga siendo categoria poleron. "Pantalon"/"Jort":
    # ficha real confirma "Wide-fit"/"pierna ancha" (pantalon) y
    # "Baggy-fit cargo" (jort) -- ambos a "baggy". "Poleras": el corte
    # SI varia producto a producto (verificado "Boxy-fit" en uno,
    # "Oversize-fit" en otro) -- no se generaliza, queda sin corte
    # definido para las 50 poleras de esta tienda (revisar de a poco).
    # "Chaquetas": generalizado a oversize verificado en 1 producto
    # representativo ("CAMO 10TH BOMBER-JACKET") -- menor certeza que el
    # resto, marcar para revisar si se quiere mas precision.
    "NITIDO long sleeve": {"corte": "sin corte definido"},
    "WOLVES emblem tee": {"corte": "sin corte definido"},
    "LOGO black tee": {"corte": "sin corte definido"},
    "NITIDO vibe hoodie": {"corte": "oversize"},
    "LOGO dark hoodie": {"corte": "oversize"},
    "WASHED long sleeve": {"corte": "sin corte definido"},
    "LOBO plaid shirt": {"corte": "sin corte definido"},
    "RESILIO plaid shirt": {"corte": "sin corte definido"},
    "BIG LOGO RAW SWEATER": {"categoria": "chaleco", "corte": "oversize"},
    "BIG LOGO BLACK SWEATER": {"categoria": "chaleco", "corte": "oversize"},
    "+ TIME 4 LOVE SWEATER": {"categoria": "chaleco", "corte": "oversize"},
    "SUEDE VAQUERA-JACKET": {"corte": "oversize"},
    "FEAR BLACK HOODIE": {"corte": "oversize"},
    "SAINTWOLF HOODIE": {"corte": "oversize"},
    "SAINT WOLF TEE": {"corte": "sin corte definido"},
    "+ TIME 4 LOVE TEE": {"corte": "sin corte definido"},
    "METAL GRAY HOODIE": {"corte": "oversize"},
    "METAL GRAY PANTS": {"categoria": "pantalon", "corte": "baggy"},
    "METAL BLACK PANTS": {"categoria": "pantalon", "corte": "baggy"},
    "METAL BLACK HOODIE": {"corte": "oversize"},
    "ESFINGE CATS HOODIE": {"corte": "oversize"},
    "ESFINGE CATS TEE": {"corte": "sin corte definido"},
    "3D CHROME HOODIE": {"corte": "oversize"},
    "DSLS JAPO TEE": {"corte": "sin corte definido"},
    "MANADA TOUR HOODIE": {"corte": "oversize"},
    "MANADA TOUR BLACK TEE": {"corte": "sin corte definido"},
    "MANADA TOUR WHITE TEE": {"corte": "sin corte definido"},
    "BLACK MINIMAL TEE": {"corte": "sin corte definido"},
    "BIG LOGO MINT SWEATER": {"categoria": "chaleco", "corte": "oversize"},
    "BLACK WOLF PANTS": {"categoria": "pantalon", "corte": "baggy"},
    "LIGHT BLUE JORT": {"categoria": "shorts", "corte": "baggy"},
    "METAL BLACK JORT": {"categoria": "shorts", "corte": "baggy"},
    "CAMO GRAY JORT": {"categoria": "shorts", "corte": "baggy"},
    "ICE BLUE PANTS": {"categoria": "pantalon", "corte": "baggy"},
    "CAMO GRAY PANTS": {"categoria": "pantalon", "corte": "baggy"},
    "BIG LOGO PINK SWEATER": {"categoria": "chaleco", "corte": "oversize"},
    "BIG LOGO GRAY SWEATER": {"categoria": "chaleco", "corte": "oversize"},
    "ANNIVERSARY 10 JAPO-TEE": {"corte": "sin corte definido"},
    "ESFINGE PINK CATS TEE": {"corte": "sin corte definido"},
    "BLACK LOGO 3D TEE": {"corte": "sin corte definido"},
    "METAL CROMO BLACK HOODIE": {"corte": "oversize"},
    "ACABÉ TRIUNFANDO HOODIE": {"corte": "oversize"},
    "ESFINGE PINK CATS HOODIE": {"corte": "oversize"},
    "ANNIVERSARY 10 CAMISETA": {"corte": "sin corte definido"},
    "CAMO 10TH BOMBER-JACKET": {"corte": "oversize"},
    "BLACK 10TH VARSITY-JACKET": {"corte": "oversize"},
    "DENIM SKULL JORT": {"categoria": "shorts", "corte": "baggy"},
    "DENIM RAPPORT JORT": {"categoria": "shorts", "corte": "baggy"},
    "SKULL HOODIE": {"corte": "oversize"},
    "GRITA Y EXHALE HOODIE": {"corte": "oversize"},
    "GRITA & EXHALE TEE": {"corte": "sin corte definido"},
    "BLUE SKULL TEE": {"corte": "sin corte definido"},
    "SUEDE VAQUERA-JACKET": {"corte": "oversize"},
    "TIGER PANTS MEN": {"categoria": "pantalon", "corte": "baggy"},
    "STRASS BLUE TEE": {"corte": "sin corte definido"},
    "STRASS BLACK TEE": {"corte": "sin corte definido"},
    "WOLVES CROME VARSITY-JACKET": {"corte": "oversize"},
    "SUEDE VAQUERA-JACKET": {"corte": "oversize"},
    "TOTAL BLACK VARSITY-JACKET": {"corte": "oversize"},
    "MANADA VARSITY-JACKET": {"corte": "oversize"},
    "STRASS BLUE HOODIE": {"corte": "oversize"},
    "STRASS BLACK HOODIE": {"corte": "oversize"},
    "KRYPTA TEE": {"corte": "sin corte definido"},
    "KRYPTA HOODIE": {"corte": "oversize"},
    "GRITA & EXHALE TEE": {"corte": "sin corte definido"},
    "BLVCK LOGO TEE": {"corte": "sin corte definido"},
    "SKULL DARK PANTS": {"categoria": "pantalon", "corte": "baggy"},
    "SKULL SWEATER": {"categoria": "chaleco", "corte": "oversize"},
    "DETHKID BABY-TEE": {"corte": "sin corte definido"},
    "DETHKID HOODIE": {"corte": "oversize"},
    "DETHKID TEE": {"corte": "sin corte definido"},
    "DEHTKID BOMBER-JACKET": {"corte": "oversize"},
    "EXHALE BLUE SWEATER.": {"categoria": "chaleco", "corte": "oversize"},
    "BLUE SKULL TEE": {"corte": "sin corte definido"},
    "MANADA STONE TEE": {"corte": "sin corte definido"},
    "BLACK CORE TEE": {"corte": "sin corte definido"},
    "CAPUCHA BLACK GILETTE": {"categoria": "poleron", "corte": "oversize"},
    "TIGER BOMBER-JACKET": {"corte": "oversize"},
    "TIGER PANTS": {"categoria": "pantalon", "corte": "baggy"},
    "BLACK RIVET FLARE-PANTS": {"categoria": "pantalon", "corte": "baggy"},
    "GRAY TIGER CARDIGÁN": {"categoria": "chaleco", "corte": "oversize"},
    "EXHALE BLUE SWEATER": {"categoria": "chaleco", "corte": "oversize"},
    "MANADA STONE HOODIE": {"corte": "oversize"},
    "BLACK VAQUERA-JACKET": {"corte": "oversize"},
    "CORE BLACK HOODIE": {"corte": "oversize"},
    "I LOVE DSLS TEE": {"corte": "sin corte definido"},
    "GRAY JAPO-TEE": {"corte": "sin corte definido"},
    "VARSITY JACKET 09": {"corte": "oversize"},
    "CAMO GREEN PANTS MEN": {"categoria": "pantalon", "corte": "baggy"},
    "CAMO GREEN PANTS GIRL": {"categoria": "pantalon", "corte": "baggy"},
    "CAMO GRAY PANTS GIRL": {"categoria": "pantalon", "corte": "baggy"},
    "CAMO GRAY PANTS MEN": {"categoria": "pantalon", "corte": "baggy"},
    "BOXY TEE NEGRA": {"corte": "sin corte definido"},
    "HOODIE CAMO STRASS": {"corte": "oversize"},
    "SWEATER CARDIGÁN 09": {"categoria": "chaleco", "corte": "oversize"},
    "BOXY TEE NEGRA // NocityLimits": {"corte": "sin corte definido"},
    "Faith&Love HOODIE": {"corte": "oversize"},
    "María flame TEE": {"corte": "sin corte definido"},
    "Faith&Love TEE": {"corte": "sin corte definido"},
    "Love-strong TEE": {"corte": "sin corte definido"},
    "Wolf-graffiti TEE": {"corte": "sin corte definido"},
    "Rosary TEE": {"corte": "sin corte definido"},
    "Dsls-cromo TEE": {"corte": "sin corte definido"},
    "Wolf graffiti CREWNECK": {"categoria": "poleron", "corte": "oversize"},
    "María flame HOODIE": {"corte": "oversize"},
    "HOODIE VIRGEN": {"corte": "oversize"},
    "Embroidery PANTS": {"categoria": "pantalon", "corte": "baggy"},
    "Denim-rapport JACKET": {"corte": "oversize"},
    "Denim-rapport PANTS": {"categoria": "pantalon", "corte": "baggy"},
    "Denim-tribal SHORT": {"categoria": "shorts", "corte": "baggy"},
    "Denim-rapport JORT": {"categoria": "shorts", "corte": "baggy"},
    "LA FERIA ON TOUR / Anniversary tee": {"corte": "sin corte definido"},
    "POLERA STRASS GRIS": {"corte": "sin corte definido"},
    "LOGO STRASS TEE": {"corte": "sin corte definido"},
    "LOGO STRASS HOODIE": {"corte": "oversize"},
    "JORT CARGO CAMO VERDE": {"categoria": "shorts", "corte": "baggy", "subtipo": "cargo"},
    "JORT CARGO CAMO GRIS": {"categoria": "shorts", "corte": "baggy", "subtipo": "cargo"},
    "TANK TOP MEN": {"corte": "sin corte definido"},
    "TANK TOP GIRL": {"corte": "sin corte definido"},
    "BOXY TEE GRIS": {"corte": "sin corte definido"},
    "SWEATER CAPUCHA LOGO": {"categoria": "chaleco", "corte": "oversize"},
    "VARSITY-JACKET CAMO": {"corte": "oversize"},
    "STRASS REED HOODIE": {"corte": "oversize"},
    "STRASS BLACK HOODIE": {"corte": "oversize"},
    "STRASS PINK HOODIE": {"corte": "oversize"},
    "VARSITY JACKET LUCIERNAGA": {"corte": "oversize"},
    "CATS GRAY TEE": {"corte": "sin corte definido"},
    "CAPUCHA JACKET BLACK 02": {"corte": "oversize"},
    "POLERA BLACK 02 BOXY": {"corte": "sin corte definido"},
    "VARSITY JACKET BLACK 02": {"corte": "oversize"},
    "TEE BOXY DARK PINK": {"corte": "sin corte definido"},
    "CROP-TOP DARK PINK": {"corte": "sin corte definido"},
    "CROP-TOP CROMO NEGRO": {"corte": "sin corte definido"},
    "HOODIE CROMO OVERSIZE": {"corte": "oversize"},
    "POLERA LOCK ARDE": {"corte": "sin corte definido"},
    "CARGO-PANTS WOLVES": {"categoria": "pantalon", "corte": "baggy", "subtipo": "cargo"},
    "CARPINTERO-PANTS CHEETAH": {"categoria": "pantalon", "corte": "baggy"},
    "FLARE-PANTS DARK": {"categoria": "pantalon", "corte": "baggy"},
    "CROP-TOP CROMO GRIS": {"corte": "sin corte definido"},
    "POLERA CONEXIÓN NEGRA": {"corte": "sin corte definido"},
    "POLERA UNIÓN GRIS": {"corte": "sin corte definido"},
    "POLERA OBSIDIANA CLIP": {"corte": "sin corte definido"},
    "POLERA NOCTURA DISCO": {"corte": "sin corte definido"},
    "SWEATER TRIBAL": {"categoria": "chaleco", "corte": "oversize"},
    "SWEATER SALLY ROJO": {"categoria": "chaleco", "corte": "oversize"},
    "SWEATER JACK NEGRO": {"categoria": "chaleco", "corte": "oversize"},
    "VARSITY-JACKET ARCANA CAFÉ": {"corte": "oversize"},
    "VARSITY-JACKET ARCANA NEGRA": {"corte": "oversize"},
    "HOODIE CROMO BOXY": {"corte": "oversize"},
    "HOODIE DARK OSCURIDAD": {"corte": "oversize"},
    "CREWNECK DARK ARCANA": {"categoria": "poleron", "corte": "oversize"},
    "Pants \"Black Wolf\"": {"categoria": "pantalon", "corte": "baggy"},
    "Tee gray \"Angel wings\"": {"corte": "sin corte definido"},
    "Tee Gray \"Girly\"": {"corte": "sin corte definido"},
    "Snake Blue Tee": {"corte": "sin corte definido"},
    "Pants \"Gray Wolf\"": {"categoria": "pantalon", "corte": "baggy"},
    "Zipper gray hoodie": {"corte": "oversize"},
    "CREWNECK OXIDADO MINIMAL": {"categoria": "poleron", "corte": "oversize"},
    "Tee oversize gray logo": {"corte": "sin corte definido"},
    "Tee Black \"Night Witch\"": {"corte": "sin corte definido"},
    "Tee Black \"Biker skeletons\"": {"corte": "sin corte definido"},
    "Tee Minimal \"Mint\"": {"corte": "sin corte definido"},
    "Tee Stripe \"Orange\"": {"corte": "sin corte definido"},
    "Tee Stripe \"Cross\"": {"corte": "sin corte definido"},
    "Cargo zipper pants": {"categoria": "pantalon", "corte": "baggy", "subtipo": "cargo"},
    "Two wolves hoodie": {"corte": "oversize"},
    "CREWNECK GALGOS ETERNAL VERSIÓN": {"categoria": "poleron", "corte": "oversize"},
    "Tee Oversize \"White Mask\"": {"corte": "sin corte definido"},
    "Tee oversize black \"Anniversary Nº7\"": {"corte": "sin corte definido"},
    "CAMO LOGO SHIRT": {"corte": "sin corte definido"},
    "Camisa Moon Ritual": {"corte": "oversize", "categoria": "camisa"},
    "ROMULO Y REMO TEE": {"corte": "sin corte definido"},
    "Raw eonia hoodie": {"corte": "oversize"},
    "Post vortex gray hoodie": {"corte": "oversize"},
    "WOLVES BLACK TEE": {"corte": "sin corte definido"},
    "Tee oversize gray logo": {"corte": "sin corte definido"},
    "Skull blue tee": {"corte": "sin corte definido"},
    "Monje black tee": {"corte": "sin corte definido"},
    "Monje color gray tee": {"corte": "sin corte definido"},
    "Rómulo y Remo hoodie": {"corte": "oversize"},
    "Skull gray tee": {"corte": "sin corte definido"},
    "Wolf chrome tee": {"corte": "sin corte definido"},
    "Tee oversize blue logo": {"corte": "sin corte definido"},
    "WOLVES RED HOODIE": {"corte": "oversize"},
    "Post Vortex Crewneck": {"categoria": "poleron", "corte": "oversize"},
    "Moon raw hoodie": {"corte": "oversize"},
    "Tee oversize black \"Angel\"": {"corte": "sin corte definido"},
    "WOLVES GRAY/BLACK TEE": {"corte": "sin corte definido"},
    "RED ANGEL TEE": {"corte": "sin corte definido"},
    "MOON RITUAL BLACK TEE": {"corte": "sin corte definido"},
    "MOON RITUAL GRAY/BLACK TEE": {"corte": "sin corte definido"},
    "LUCIÉRNAGA BLACK CROPPED TEE": {"corte": "sin corte definido"},
    "Tee Ninja \"Black\"": {"corte": "sin corte definido"},
    "Hoodie Mint Logo": {"corte": "oversize"},
    "LUCIÉRNAGA BLACK HOODIE": {"corte": "oversize"},
    "Varsity Jacket Mint Minimal": {"corte": "oversize"},
    "Tee Ninja \"Mint\"": {"corte": "sin corte definido"},
    "Sweater cardigán logo": {"categoria": "chaleco", "corte": "oversize"},
    "LOGO CHROME TEE": {"corte": "sin corte definido"},
    "Sweater Étnico": {"categoria": "chaleco", "corte": "oversize"},
    "Varsity Jacket \"Brown Paisley\"": {"corte": "oversize"},
    "Varsity Jacket Black Minimal": {"corte": "oversize"},
    "Crewneck Galgos": {"categoria": "poleron", "corte": "oversize"},
    "Tee Black \"orange mask\"": {"corte": "sin corte definido"},
    "CHROME SWEATER": {"categoria": "chaleco", "corte": "oversize"},
    "Sweater cardigán skeleton": {"categoria": "chaleco", "corte": "oversize"},
    "POLERA CALMA NEGRA": {"corte": "sin corte definido"},
    "POLERA ALMA BLANCA": {"corte": "sin corte definido"},
    "POLERÓN CONTIGO NEGRO": {"categoria": "poleron", "corte": "oversize"},
    "POLERÓN SIEMPRE ROJO": {"categoria": "poleron", "corte": "oversize"},
    "Varsity Jacket Black Wolf": {"corte": "oversize"},
    "STRASS LUCIÉRNAGA HOODIE": {"corte": "oversize"},
    "CATS BLACK HOODIE": {"corte": "oversize"},
    "Tee Gray Galgos": {"corte": "sin corte definido"},
    "CATS BLACK TEE": {"corte": "sin corte definido"},
    "3D CHROME LOGO HOODIE": {"corte": "oversize"},
    "POLERA DARK IGOR": {"corte": "sin corte definido"},
    "JORT CARGO CORROÍDO": {"categoria": "shorts", "corte": "baggy", "subtipo": "cargo"},
    "CHAQUETA CORROÍDO": {"corte": "oversize"},
    "PANTALÓN CARGO": {"categoria": "pantalon", "corte": "baggy", "subtipo": "cargo"},
    "PANTALÓN CARPINTERO": {"categoria": "pantalon", "corte": "baggy"},
    "POLERA DARK CARRIE": {"corte": "sin corte definido"},
    "CROP TOP LOGOGRAMA": {"corte": "sin corte definido"},
    "POLERA LOGOGRAMA": {"corte": "sin corte definido"},
    "POLERÓN INFINITO 08": {"categoria": "poleron", "corte": "oversize"},
    "CAMISETA DARK ETERNAL": {"corte": "sin corte definido"},
    "SWEATER MINIMALISTA": {"categoria": "chaleco", "corte": "oversize"},
    "SWEATER ETERNAL": {"categoria": "chaleco", "corte": "oversize"},
    "POLERA INFINITO 08": {"corte": "sin corte definido"},
    "JORT CARPINTERO ETERNO 08": {"categoria": "shorts", "corte": "baggy"},
    "CAMISA ETERNO 08": {"corte": "sin corte definido"},

    # --- Novorich (2026-08-24, ficha real via products.json) ---
    "HODDIE LUXURY SKY BLUE": {"corte": "oversize"},
    "HODDIE - ESSENCE PURPLE": {"corte": "boxy fit"},
    "HODDIE - ESSENCE BLACK": {"corte": "oversize"},
    "HODDIE - LUXURY BLVCK": {"corte": "boxy fit"},

    # --- Stuffies Concept (2026-08-24, ficha real via products.json) ---
    "DICE HOODIE \"Third Edition\" Black": {"corte": "boxy fit"},
    "DICE HOODIE \"Third Edition\" Blue Navy": {"corte": "boxy fit"},
}

# 2026-08-20 -- capucha/cierre de los 28 polerones reales (ninguno lo tenia
# cargado, ver CLAUDE.md). Criterio explicito del usuario, en 2 pasadas:
# 1ra pasada (texto): "con capucha"/"con cierre" solo si la ficha REAL o el
#    nombre dice literalmente "con capucha"/"hoodie"/"capota"/"gorro"
#    (capucha) o "cierre"/"zipper"/"zip" (cierre) -- ej. "RAW SHIFT HOODIE"
#    -> con capucha por el nombre, aunque la descripcion no lo repita.
# 2da pasada (foto, mismo dia): para lo que quedo "no especificado" tras el
#    texto, se miro la foto real del producto -- linea visible de cierre al
#    centro = con cierre; capucha visible en la imagen = con capucha; sin
#    ninguna senal ni en texto ni en foto, se mantiene "no especificado"
#    (nunca "sin capucha"/"sin cierre" a ciegas). Cada entrada abajo indica
#    "(texto)" o "(foto)" segun de donde salio el dato, para saber donde
#    revisar primero si alguna vez hay dudas.
CAPUCHA_CIERRE_VERIFICADO = {
    # --- OVA Chile --- ni ficha ni foto dan senal (la foto disponible esta
    # recortada a la altura del pecho, no se ve capucha ni cierre).
    "BUZO BAGGY OVA APPAREL NEGRO (PREVENTA)": {},
    "BUZO BAGGY OVA APPAREL GRIS (PREVENTA)": {},

    # --- Oversaints --- capucha (texto): TODA la linea comparte la frase de
    # ficha "Goma con el logo de la marca en el gorro", confirmado en 3
    # productos representativos. Cierre (texto): solo los 2 nombrados
    # "zipper" mencionan cierre en la ficha. El resto de la linea son
    # mockups de una sola imagen (sin foto real del producto puesto) --
    # no se pudo revisar cierre por foto para Crema Anillo/Gris Stone
    # 777/OS Celeste/Washed OVRST, quedan "no especificado" en cierre.
    "Poleron black zipper": {"capucha": "con capucha", "cierre": "con cierre"},
    "Poleron pink zipper": {"capucha": "con capucha", "cierre": "con cierre"},
    "Poleron Crema Anillo": {"capucha": "con capucha"},
    "Poleron Gris Stone 777": {"capucha": "con capucha"},
    "Poleron OS Celeste": {"capucha": "con capucha"},
    "Poleron Washed OVRST": {"capucha": "con capucha"},

    # --- Rapt --- capucha/cierre (texto) confirmados primero por nombre/
    # ficha (ver comentario original), y (foto) donde la primera pasada
    # dejo un lado sin dato -- foto de catalogo real, vista frontal clara
    # en todos menos "HOODIE ESSENCE CLASSIC II" (foto es vista trasera,
    # no se ve el frente -- cierre queda "no especificado").
    "GRID SHIFT ZIP MELANGE": {"capucha": "con capucha", "cierre": "con cierre"},
    "GRID SHIFT ZIP NAVY": {"capucha": "con capucha", "cierre": "con cierre"},
    "PATCH SHIFT ZIP BLACK": {"capucha": "con capucha", "cierre": "con cierre"},
    "RAW SHIFT HOODIE BLACK": {"capucha": "con capucha", "cierre": "sin cierre"},
    "ACID SHIFT HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "HOODIE ESSENCE CLASSIC II / PRE-ORDER": {"capucha": "con capucha"},
    "COMMON HOODIE MORO": {"capucha": "con capucha", "cierre": "sin cierre"},
    "COMMON HOODIE AZURE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "COMMON HOODIE MOSS": {"capucha": "con capucha", "cierre": "sin cierre"},

    # --- Roots South --- cierre (texto) por "Zip"/"Zipper" en el nombre.
    # Capucha (foto): ninguna ficha la menciona, pero la foto real de
    # catalogo la muestra clara en los 5 (incluye "Espresso Zip Knit", que
    # a pesar del nombre "Zip" es en realidad un chaleco/cardigan tejido
    # con cuello alto, SIN capucha -- confirmado visualmente, ver aviso
    # aparte sobre su categoria).
    "Black Zipper Layers": {"capucha": "con capucha", "cierre": "con cierre"},
    "Chocolate Zipper": {"capucha": "con capucha", "cierre": "con cierre"},
    "Chocolate Zipper Patch": {"capucha": "con capucha", "cierre": "con cierre"},
    "Cream Zipper Rootsouth Est": {"capucha": "con capucha", "cierre": "con cierre"},
    "Espresso Zip Knit": {"capucha": "sin capucha", "cierre": "con cierre"},

    # --- Selvanegrawear --- "Canguro" (foto): ni la ficha ni el nombre
    # mencionan capucha/cierre, pero la foto real muestra capucha con
    # cordon y bolsillo canguro cerrado (sin cierre) en los 2 productos.
    # "Sudadera" (4 productos): NO se tagueo -- ver aviso aparte, las fotos
    # muestran musculosas sin mangas, no polerones, posible error de datos
    # de la tienda que hay que confirmar con el dueno del proyecto antes de
    # asignar cualquier corte/capucha/cierre.
    "Canguro Calaka Letras Verdes": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Canguro Sunset Mujer": {"capucha": "con capucha", "cierre": "sin cierre"},

    # --- AbsolutelyWrong (2026-08-22) --- ficha no menciona ninguna de las
    # 2 cosas (solo "Boxy Regular Fit"/material/gramaje). Foto real
    # confirma: capucha visible, bolsillo canguro cerrado sin cierre --
    # mismo criterio en los 6 productos de poleron de esta tienda.
    "POLERON BASICO HEAVYWEIGHT NEGRO (PREVENTA)": {"capucha": "con capucha", "cierre": "sin cierre"},
    "POLERON BASICO HEAVYWEIGHT GRIS (PREVENTA)": {"capucha": "con capucha", "cierre": "sin cierre"},
    "POLERON BASICO HEAVYWEIGHT AZUL MARINO (PREVENTA)": {"capucha": "con capucha", "cierre": "sin cierre"},
    "POLERON BASICO HEAVYWEIGHT BURDEO (PREVENTA)": {"capucha": "con capucha", "cierre": "sin cierre"},
    "POLERON BASICO HEAVYWEIGHT ROSADO (PREVENTA)": {"capucha": "con capucha", "cierre": "sin cierre"},
    "POLERON GAY BOXY OVERSIZED": {"capucha": "con capucha", "cierre": "sin cierre"},

    # --- Floating (2026-08-23) --- ficha real: todos dicen "Gorro doble
    # forrado" (capucha). "FLTNG Zip..." ademas dice "Cierre metalico"; los
    # "Noir Pulse"/"Nuit Volt" no mencionan cierre y son pullover.
    "FLTNG Zip Hoodie": {"capucha": "con capucha", "cierre": "con cierre"},
    "FLTNG ZIP V2": {"capucha": "con capucha", "cierre": "con cierre"},
    "Noir Pulse": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Noir Pulse - Aureum": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Noir Pulse - Emerald": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Noir Pulse - Morganite": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Nuit Volt": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Nuit Volt - Heaven": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Nuit Volt - Void": {"capucha": "con capucha", "cierre": "sin cierre"},

    # --- BANG GANG (2026-08-23) --- ficha real dice literal "Hoodie" +
    # "Bolsillo tipo canguro en la parte frontal", sin mencion de cierre
    # -- con capucha, sin cierre, en TODOS los polerones (verificado en 2
    # productos representativos).
    "Poleron Crystals Logo BG": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron Heavy Crystals": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron Crystals Logo BG": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron 333 White Black Chance": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron 333 Pink Black Chance": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron Bloodline Blue Black": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron Bloodline Grey Black": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron 333 Red Special": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron Bloodline Red Black": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron Shooters Triple White Blue": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron Shooters Blue Black": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron Shooters Pink Black": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron Shooters Blue Melange": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron Shooters Pink Melange": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron Shooters Ultra Melange": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron Shooters Ultra Pink": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron Angels Or Visitors": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron Graff BG": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron No Love Just Money": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron ESTHER BG": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron The Final Sky": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Poleron 333 Dollars Black": {"capucha": "con capucha", "cierre": "sin cierre"},

    # --- UNK Chile (2026-08-23) --- ficha real confirma "Poleron con
    # capucha" (texto), y la foto confirma pullover sin cierre (bolsillo
    # canguro, sin zipper visible) en todos los "Hoodie"/"Poleron".
    "Hoodie Unk. Acid Blue": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie Unk. Acid Beige": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie Unk. Acid Pink": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie Unk. Acid Green": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie Unk. Acid Black": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie UNK. Smile Pink": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie Camaleón Safary Green": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Polerón Camaleón Skate Black": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Polerón Camaleón Skate White": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Polerón Unk. Black & White": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Polerón Unk. Focus Colors": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Polerón Unk. Focus Orange": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Polar Hoodie UNK. Blue": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Polar Hoodie UNK. Black": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie UNK. Tie Dye Jade": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie UNK. Original White": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie UNK. Original Calypso": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie Block White": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie Unk. Spiral Mint": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie Unk. Spiral Blue": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie Unk. Old Brown": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie Unk. Old Black": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie UNK. Smile Mint": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie Unk. Peace Steel": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Polerón Unk. Cubox Fluor": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Polerón Unk. Cubox Lilac": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie Unk. Level Orange": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie Camaleón Safary Blue": {"capucha": "con capucha", "cierre": "sin cierre"},

    "NITIDO vibe hoodie": {"capucha": "con capucha", "cierre": "sin cierre"},
    "LOGO dark hoodie": {"capucha": "con capucha", "cierre": "sin cierre"},
    "FEAR BLACK HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "SAINTWOLF HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "METAL GRAY HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "METAL BLACK HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "ESFINGE CATS HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "3D CHROME HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "MANADA TOUR HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "METAL CROMO BLACK HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "ACABÉ TRIUNFANDO HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "ESFINGE PINK CATS HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "SKULL HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "GRITA Y EXHALE HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "STRASS BLUE HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "STRASS BLACK HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "KRYPTA HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "DETHKID HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "CAPUCHA BLACK GILETTE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "MANADA STONE HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "CORE BLACK HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "HOODIE CAMO STRASS": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Faith&Love HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Wolf graffiti CREWNECK": {"capucha": "sin capucha", "cierre": "sin cierre"},
    "María flame HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "HOODIE VIRGEN": {"capucha": "con capucha", "cierre": "sin cierre"},
    "LOGO STRASS HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "STRASS REED HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "STRASS BLACK HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "STRASS PINK HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "HOODIE CROMO OVERSIZE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "HOODIE CROMO BOXY": {"capucha": "con capucha", "cierre": "sin cierre"},
    "HOODIE DARK OSCURIDAD": {"capucha": "con capucha", "cierre": "sin cierre"},
    "CREWNECK DARK ARCANA": {"capucha": "sin capucha", "cierre": "sin cierre"},
    "Zipper gray hoodie": {"capucha": "con capucha", "cierre": "sin cierre"},
    "CREWNECK OXIDADO MINIMAL": {"capucha": "sin capucha", "cierre": "sin cierre"},
    "Two wolves hoodie": {"capucha": "con capucha", "cierre": "sin cierre"},
    "CREWNECK GALGOS ETERNAL VERSIÓN": {"capucha": "sin capucha", "cierre": "sin cierre"},
    "Raw eonia hoodie": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Post vortex gray hoodie": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Rómulo y Remo hoodie": {"capucha": "con capucha", "cierre": "sin cierre"},
    "WOLVES RED HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Post Vortex Crewneck": {"capucha": "sin capucha", "cierre": "sin cierre"},
    "Moon raw hoodie": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Hoodie Mint Logo": {"capucha": "con capucha", "cierre": "sin cierre"},
    "LUCIÉRNAGA BLACK HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "Crewneck Galgos": {"capucha": "sin capucha", "cierre": "sin cierre"},
    "POLERÓN CONTIGO NEGRO": {"capucha": "con capucha", "cierre": "sin cierre"},
    "POLERÓN SIEMPRE ROJO": {"capucha": "con capucha", "cierre": "sin cierre"},
    "STRASS LUCIÉRNAGA HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "CATS BLACK HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "3D CHROME LOGO HOODIE": {"capucha": "con capucha", "cierre": "sin cierre"},
    "POLERÓN INFINITO 08": {"capucha": "con capucha", "cierre": "sin cierre"},

    # --- Novorich, Shatters, Stuffies Concept (2026-08-24) --- capucha
    # confirmada por la palabra "hoodie" literal en el nombre real (regla
    # de siempre, ver docstring arriba). Cierre no se pudo confirmar ni en
    # texto ni revisando foto -- queda "no especificado" (default de
    # cc.get(), no hace falta declararlo aca).
    "HODDIE - LUXURY WHITE": {"capucha": "con capucha"},
    "HODDIE LUXURY SKY BLUE": {"capucha": "con capucha"},
    "HODDIE LUXURY BLACK TURCOISE": {"capucha": "con capucha"},
    "HODDIE - LUXURY PURPLE": {"capucha": "con capucha"},
    "HODDIE - ESSENCE PURPLE": {"capucha": "con capucha"},
    "HODDIE - ESSENCE BLACK": {"capucha": "con capucha"},
    "HODDIE - LUXURY BLVCK": {"capucha": "con capucha"},
    "Shatters Cloud Hoodie": {"capucha": "con capucha"},
    "Smoke Hoodie": {"capucha": "con capucha"},
    "Newland Hoodie": {"capucha": "con capucha"},
    "SS Black Hoodie": {"capucha": "con capucha"},
    "Star Wash Hoodie": {"capucha": "con capucha"},
    "Newland Black Hoodie": {"capucha": "con capucha"},
    "Winter Sky Hoodie": {"capucha": "con capucha"},
    "Pink Motion Hoodie": {"capucha": "con capucha"},
    "DICE HOODIE \"Third Edition\" Black": {"capucha": "con capucha"},
    "DICE HOODIE \"Third Edition\" Blue Navy": {"capucha": "con capucha"},
}

# Fuente de cada dato de capucha/cierre de arriba (texto de la ficha o foto
# real del producto) -- separado del dict de arriba a proposito, porque el
# VALOR que usa el buscador tiene que ser el string limpio exacto
# ("con capucha"/"sin capucha"/"con cierre"/"sin cierre", ver
# CAPUCHA_CONOCIDA/CIERRE_CONOCIDO en app.py) y no puede llevar sufijos. Este
# dict es solo para trazabilidad -- si alguna vez hay dudas sobre un dato,
# revisar aca primero antes de volver a la ficha real.
FUENTE_CAPUCHA_CIERRE = {
    "Poleron black zipper": {"capucha": "texto", "cierre": "texto"},
    "Poleron pink zipper": {"capucha": "texto", "cierre": "texto"},
    "Poleron Crema Anillo": {"capucha": "texto"},
    "Poleron Gris Stone 777": {"capucha": "texto"},
    "Poleron OS Celeste": {"capucha": "texto"},
    "Poleron Washed OVRST": {"capucha": "texto"},
    "GRID SHIFT ZIP MELANGE": {"capucha": "foto", "cierre": "texto"},
    "GRID SHIFT ZIP NAVY": {"capucha": "foto", "cierre": "texto"},
    "PATCH SHIFT ZIP BLACK": {"capucha": "foto", "cierre": "texto"},
    "RAW SHIFT HOODIE BLACK": {"capucha": "texto", "cierre": "foto"},
    "ACID SHIFT HOODIE": {"capucha": "texto", "cierre": "foto"},
    "HOODIE ESSENCE CLASSIC II / PRE-ORDER": {"capucha": "texto"},
    "COMMON HOODIE MORO": {"capucha": "texto", "cierre": "foto"},
    "COMMON HOODIE AZURE": {"capucha": "texto", "cierre": "foto"},
    "COMMON HOODIE MOSS": {"capucha": "texto", "cierre": "foto"},
    "Black Zipper Layers": {"capucha": "foto", "cierre": "texto"},
    "Chocolate Zipper": {"capucha": "foto", "cierre": "texto"},
    "Chocolate Zipper Patch": {"capucha": "foto", "cierre": "texto"},
    "Cream Zipper Rootsouth Est": {"capucha": "foto", "cierre": "texto"},
    "Espresso Zip Knit": {"capucha": "foto", "cierre": "texto"},
    "Canguro Calaka Letras Verdes": {"capucha": "foto", "cierre": "foto"},
    "Canguro Sunset Mujer": {"capucha": "foto", "cierre": "foto"},
    "POLERON BASICO HEAVYWEIGHT NEGRO (PREVENTA)": {"capucha": "foto", "cierre": "foto"},
    "POLERON BASICO HEAVYWEIGHT GRIS (PREVENTA)": {"capucha": "foto", "cierre": "foto"},
    "POLERON BASICO HEAVYWEIGHT AZUL MARINO (PREVENTA)": {"capucha": "foto", "cierre": "foto"},
    "POLERON BASICO HEAVYWEIGHT BURDEO (PREVENTA)": {"capucha": "foto", "cierre": "foto"},
    "POLERON BASICO HEAVYWEIGHT ROSADO (PREVENTA)": {"capucha": "foto", "cierre": "foto"},
    "POLERON GAY BOXY OVERSIZED": {"capucha": "foto", "cierre": "foto"},
    "FLTNG Zip Hoodie": {"capucha": "texto", "cierre": "texto"},
    "FLTNG ZIP V2": {"capucha": "texto", "cierre": "texto"},
    "Noir Pulse": {"capucha": "texto", "cierre": "texto"},
    "Noir Pulse - Aureum": {"capucha": "texto", "cierre": "texto"},
    "Noir Pulse - Emerald": {"capucha": "texto", "cierre": "texto"},
    "Noir Pulse - Morganite": {"capucha": "texto", "cierre": "texto"},
    "Nuit Volt": {"capucha": "texto", "cierre": "texto"},
    "Nuit Volt - Heaven": {"capucha": "texto", "cierre": "texto"},
    "Nuit Volt - Void": {"capucha": "texto", "cierre": "texto"},

    "Poleron Crystals Logo BG": {"capucha": "texto", "cierre": "texto"},
    "Poleron Heavy Crystals": {"capucha": "texto", "cierre": "texto"},
    "Poleron Crystals Logo BG": {"capucha": "texto", "cierre": "texto"},
    "Poleron 333 White Black Chance": {"capucha": "texto", "cierre": "texto"},
    "Poleron 333 Pink Black Chance": {"capucha": "texto", "cierre": "texto"},
    "Poleron Bloodline Blue Black": {"capucha": "texto", "cierre": "texto"},
    "Poleron Bloodline Grey Black": {"capucha": "texto", "cierre": "texto"},
    "Poleron 333 Red Special": {"capucha": "texto", "cierre": "texto"},
    "Poleron Bloodline Red Black": {"capucha": "texto", "cierre": "texto"},
    "Poleron Shooters Triple White Blue": {"capucha": "texto", "cierre": "texto"},
    "Poleron Shooters Blue Black": {"capucha": "texto", "cierre": "texto"},
    "Poleron Shooters Pink Black": {"capucha": "texto", "cierre": "texto"},
    "Poleron Shooters Blue Melange": {"capucha": "texto", "cierre": "texto"},
    "Poleron Shooters Pink Melange": {"capucha": "texto", "cierre": "texto"},
    "Poleron Shooters Ultra Melange": {"capucha": "texto", "cierre": "texto"},
    "Poleron Shooters Ultra Pink": {"capucha": "texto", "cierre": "texto"},
    "Poleron Angels Or Visitors": {"capucha": "texto", "cierre": "texto"},
    "Poleron Graff BG": {"capucha": "texto", "cierre": "texto"},
    "Poleron No Love Just Money": {"capucha": "texto", "cierre": "texto"},
    "Poleron ESTHER BG": {"capucha": "texto", "cierre": "texto"},
    "Poleron The Final Sky": {"capucha": "texto", "cierre": "texto"},
    "Poleron 333 Dollars Black": {"capucha": "texto", "cierre": "texto"},

    "Hoodie Unk. Acid Blue": {"capucha": "texto", "cierre": "foto"},
    "Hoodie Unk. Acid Beige": {"capucha": "texto", "cierre": "foto"},
    "Hoodie Unk. Acid Pink": {"capucha": "texto", "cierre": "foto"},
    "Hoodie Unk. Acid Green": {"capucha": "texto", "cierre": "foto"},
    "Hoodie Unk. Acid Black": {"capucha": "texto", "cierre": "foto"},
    "Hoodie UNK. Smile Pink": {"capucha": "texto", "cierre": "foto"},
    "Hoodie Camaleón Safary Green": {"capucha": "texto", "cierre": "foto"},
    "Polerón Camaleón Skate Black": {"capucha": "texto", "cierre": "foto"},
    "Polerón Camaleón Skate White": {"capucha": "texto", "cierre": "foto"},
    "Polerón Unk. Black & White": {"capucha": "texto", "cierre": "foto"},
    "Polerón Unk. Focus Colors": {"capucha": "texto", "cierre": "foto"},
    "Polerón Unk. Focus Orange": {"capucha": "texto", "cierre": "foto"},
    "Polar Hoodie UNK. Blue": {"capucha": "texto", "cierre": "foto"},
    "Polar Hoodie UNK. Black": {"capucha": "texto", "cierre": "foto"},
    "Hoodie UNK. Tie Dye Jade": {"capucha": "texto", "cierre": "foto"},
    "Hoodie UNK. Original White": {"capucha": "texto", "cierre": "foto"},
    "Hoodie UNK. Original Calypso": {"capucha": "texto", "cierre": "foto"},
    "Hoodie Block White": {"capucha": "texto", "cierre": "foto"},
    "Hoodie Unk. Spiral Mint": {"capucha": "texto", "cierre": "foto"},
    "Hoodie Unk. Spiral Blue": {"capucha": "texto", "cierre": "foto"},
    "Hoodie Unk. Old Brown": {"capucha": "texto", "cierre": "foto"},
    "Hoodie Unk. Old Black": {"capucha": "texto", "cierre": "foto"},
    "Hoodie UNK. Smile Mint": {"capucha": "texto", "cierre": "foto"},
    "Hoodie Unk. Peace Steel": {"capucha": "texto", "cierre": "foto"},
    "Polerón Unk. Cubox Fluor": {"capucha": "texto", "cierre": "foto"},
    "Polerón Unk. Cubox Lilac": {"capucha": "texto", "cierre": "foto"},
    "Hoodie Unk. Level Orange": {"capucha": "texto", "cierre": "foto"},
    "Hoodie Camaleón Safary Blue": {"capucha": "texto", "cierre": "foto"},

    "NITIDO vibe hoodie": {"capucha": "texto", "cierre": "texto"},
    "LOGO dark hoodie": {"capucha": "texto", "cierre": "texto"},
    "FEAR BLACK HOODIE": {"capucha": "texto", "cierre": "texto"},
    "SAINTWOLF HOODIE": {"capucha": "texto", "cierre": "texto"},
    "METAL GRAY HOODIE": {"capucha": "texto", "cierre": "texto"},
    "METAL BLACK HOODIE": {"capucha": "texto", "cierre": "texto"},
    "ESFINGE CATS HOODIE": {"capucha": "texto", "cierre": "texto"},
    "3D CHROME HOODIE": {"capucha": "texto", "cierre": "texto"},
    "MANADA TOUR HOODIE": {"capucha": "texto", "cierre": "texto"},
    "METAL CROMO BLACK HOODIE": {"capucha": "texto", "cierre": "texto"},
    "ACABÉ TRIUNFANDO HOODIE": {"capucha": "texto", "cierre": "texto"},
    "ESFINGE PINK CATS HOODIE": {"capucha": "texto", "cierre": "texto"},
    "SKULL HOODIE": {"capucha": "texto", "cierre": "texto"},
    "GRITA Y EXHALE HOODIE": {"capucha": "texto", "cierre": "texto"},
    "STRASS BLUE HOODIE": {"capucha": "texto", "cierre": "texto"},
    "STRASS BLACK HOODIE": {"capucha": "texto", "cierre": "texto"},
    "KRYPTA HOODIE": {"capucha": "texto", "cierre": "texto"},
    "DETHKID HOODIE": {"capucha": "texto", "cierre": "texto"},
    "CAPUCHA BLACK GILETTE": {"capucha": "texto", "cierre": "texto"},
    "MANADA STONE HOODIE": {"capucha": "texto", "cierre": "texto"},
    "CORE BLACK HOODIE": {"capucha": "texto", "cierre": "texto"},
    "HOODIE CAMO STRASS": {"capucha": "texto", "cierre": "texto"},
    "Faith&Love HOODIE": {"capucha": "texto", "cierre": "texto"},
    "Wolf graffiti CREWNECK": {"capucha": "texto", "cierre": "texto"},
    "María flame HOODIE": {"capucha": "texto", "cierre": "texto"},
    "HOODIE VIRGEN": {"capucha": "texto", "cierre": "texto"},
    "LOGO STRASS HOODIE": {"capucha": "texto", "cierre": "texto"},
    "STRASS REED HOODIE": {"capucha": "texto", "cierre": "texto"},
    "STRASS BLACK HOODIE": {"capucha": "texto", "cierre": "texto"},
    "STRASS PINK HOODIE": {"capucha": "texto", "cierre": "texto"},
    "HOODIE CROMO OVERSIZE": {"capucha": "texto", "cierre": "texto"},
    "HOODIE CROMO BOXY": {"capucha": "texto", "cierre": "texto"},
    "HOODIE DARK OSCURIDAD": {"capucha": "texto", "cierre": "texto"},
    "CREWNECK DARK ARCANA": {"capucha": "texto", "cierre": "texto"},
    "Zipper gray hoodie": {"capucha": "texto", "cierre": "texto"},
    "CREWNECK OXIDADO MINIMAL": {"capucha": "texto", "cierre": "texto"},
    "Two wolves hoodie": {"capucha": "texto", "cierre": "texto"},
    "CREWNECK GALGOS ETERNAL VERSIÓN": {"capucha": "texto", "cierre": "texto"},
    "Raw eonia hoodie": {"capucha": "texto", "cierre": "texto"},
    "Post vortex gray hoodie": {"capucha": "texto", "cierre": "texto"},
    "Rómulo y Remo hoodie": {"capucha": "texto", "cierre": "texto"},
    "WOLVES RED HOODIE": {"capucha": "texto", "cierre": "texto"},
    "Post Vortex Crewneck": {"capucha": "texto", "cierre": "texto"},
    "Moon raw hoodie": {"capucha": "texto", "cierre": "texto"},
    "Hoodie Mint Logo": {"capucha": "texto", "cierre": "texto"},
    "LUCIÉRNAGA BLACK HOODIE": {"capucha": "texto", "cierre": "texto"},
    "Crewneck Galgos": {"capucha": "texto", "cierre": "texto"},
    "POLERÓN CONTIGO NEGRO": {"capucha": "texto", "cierre": "texto"},
    "POLERÓN SIEMPRE ROJO": {"capucha": "texto", "cierre": "texto"},
    "STRASS LUCIÉRNAGA HOODIE": {"capucha": "texto", "cierre": "texto"},
    "CATS BLACK HOODIE": {"capucha": "texto", "cierre": "texto"},
    "3D CHROME LOGO HOODIE": {"capucha": "texto", "cierre": "texto"},
    "POLERÓN INFINITO 08": {"capucha": "texto", "cierre": "texto"},
}

# Nombres de producto que en realidad son "baby tee" (categoria "top",
# subtipo "babytee") -- clasificar_prenda() los mandaria por defecto a
# "polera" porque no tiene una regla especial para esta frase.
ES_BABY_TEE = {"dnd baby tee"}

# Rango de tallas observado en una ficha real de cada tienda (aproximacion
# a nivel tienda -- ver docstring).
TALLAS_POR_TIENDA = {
    "OVA Chile": ["S", "M", "L", "XL"],
    "Oversaints": ["S", "M", "L", "XL"],
    "El Pulento Style": ["S", "M", "L", "XL"],
    "Rapt": ["S", "M", "L", "XL"],
    "Roots South": ["S", "M", "L", "XL"],
    "Rotten": ["S", "M", "L", "XL"],
    "Selvanegrawear": ["S", "M", "L", "XL"],
    "Simpl.": ["S", "M", "L", "XL"],
    # AbsolutelyWrong (2026-08-22): la ficha real ofrece M/L/XL/XXL (sin S)
    # -- la app solo modela hasta XL (ver ORDEN_TALLAS en app.py), asi que
    # XXL no se puede representar (limitacion conocida, no es un error de
    # carga). No se agrega "S" porque la tienda genuinamente no la vende.
    "AbsolutelyWrong": ["M", "L", "XL"],
    # ForceBlack (2026-08-23): vende por talla numerica (40/42/44/46/48),
    # pero la propia ficha trae una tabla de equivalencia a S/M/L/XL por
    # medidas -- se usa esa tabla, no una traduccion inventada.
    "ForceBlack": ["S", "M", "L", "XL"],
    "Floating": ["S", "M", "L", "XL"],
    "BANG GANG": ["S", "M", "L", "XL"],
    "UNK Chile": ["S", "M", "L", "XL"],
    "Doslobos": ["S", "M", "L", "XL"],
}


def _tiene_palabra(nombre, palabra):
    return palabra.lower() in nombre.lower()


def detectar_corte(nombre):
    n = nombre.lower()
    if "baggy" in n:
        return "baggy"
    if "oversize" in n or "overzise" in n or "oversized" in n:
        return "oversize"
    if "boxy" in n:
        return "boxy fit"
    if "slim" in n:
        return "slim fit"
    if "regular" in n:
        return "regular fit"
    if "straight" in n:
        return "straight"
    if "skinny" in n:
        return "skinny"
    return ""


def clasificar_prenda(nombre):
    """Devuelve (categoria, subtipo, manga, largo) a partir de palabras
    clave reales del nombre del producto. Reglas explicitas, en orden --
    ver docstring del modulo para el criterio general."""
    n = nombre.lower()

    if nombre in ES_BABY_TEE or "baby tee" in n or "babytee" in n:
        # "Baby tee" es, por definicion propia del formulario de KOLIZION
        # ("Baby tee: corto y ajustado", ver CLAUDE.md), un largo crop --
        # no es un dato inventado para ESTE producto puntual, es lo que
        # significa el subtipo en si.
        return "top", "babytee", None, "crop"

    if "gorro" in n or "beanie" in n:
        return "gorro", None, None, None

    if "tracksuit" in n or "conjunto" in n:
        # Set de 2 piezas (poleron/buzo + pantalon) vendido como una sola
        # ficha -- categoria nueva (2026-08-24, aprobada por el dueno).
        # Sin subtipo/manga/largo: son conceptos de 1 sola prenda, no
        # aplican a un conjunto de 2 piezas, no inventar un valor.
        return "conjunto", None, None, None

    if "chaleco" in n or (n.startswith("knit") or " knit" in n) and "zip" not in n and "hoodie" not in n:
        return "chaleco", None, None, None

    if "jacket" in n or "chaqueta" in n:
        subtipo = None
        if "denim" in n:
            subtipo = "mezclilla"
        elif "leather" in n or "cuero" in n:
            subtipo = "cuero"
        elif "bomber" in n:
            subtipo = "bomber"
        return "chaqueta", subtipo, None, None

    # 2026-08-23 -- "jean"/"denim" agregados como disparador de categoria
    # (antes solo contaban para el SUBTIPO dentro de este mismo bloque, asi
    # que "Black Ripped jeans" -- sin la palabra "pantalon"/"trouser" -- caia
    # al default "polera", categoria equivocada). Bug real encontrado
    # cargando ForceBlack (22 productos, todos "... jeans"), corregido antes
    # de seguir con mas tiendas. El chequeo de "chaqueta"/"jacket" arriba ya
    # se encarga de "denim jacket" antes de llegar aca, asi que agregar
    # "denim" no genera falsos positivos con chaquetas.
    if "trouser" in n or "pantalon" in n or "jean" in n or "denim" in n:
        subtipo = None
        if "cargo" in n:
            subtipo = "cargo"
        elif "jean" in n or "denim" in n:
            subtipo = "jeans"
        return "pantalon", subtipo, None, None

    # 2026-08-22 -- "short" nunca habia aparecido en las 8 tiendas piloto
    # originales, asi que clasificar_prenda() no lo manejaba (caia al
    # default "polera", categoria equivocada). Mismo criterio que pantalon.
    if "short" in n:
        subtipo = None
        if "cargo" in n:
            subtipo = "cargo"
        elif "jean" in n or "denim" in n:
            subtipo = "jeans"
        elif "bano" in n or "baño" in n or "swim" in n:
            subtipo = "bano"
        elif "tela" in n:
            subtipo = "tela"
        return "shorts", subtipo, None, None

    if any(p in n for p in ("hoodie", "poleron", "zip", "canguro", "sudadera")):
        return "poleron", None, None, None

    if "longsleeve" in n or "long sleeve" in n:
        return "polera", None, "larga", "normal"

    # Poleras/tees genericas (incluye "buzo" sueltos de Selvanegrawear, que
    # por contexto de catalogo -- junto a canguro/sudadera -- son la parte
    # de arriba tipo hoodie, no pantalon).
    if "buzo" in n and "pantalon" not in n:
        return "poleron", None, None, None

    return "polera", None, "corta", "normal"


def genero_de(nombre):
    n = nombre.lower()
    if "mujer" in n or "women" in n:
        return "mujer"
    if "hombre" in n or "men" in n:
        return "hombre"
    return "unisex"


def limpiar_precio(precio_clp):
    return f"${precio_clp:,}".replace(",", ".")


def img_absoluta(url):
    if url.startswith("//"):
        return "https:" + url
    return url


def link_absoluto(dominio, path):
    if path.startswith("http"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return f"https://{dominio}{path}"


def _handle_de_path(path):
    return path.split("?")[0].rstrip("/").split("/")[-1]


def _limpiar_html(html_crudo):
    """Descripcion real de la tienda (body_html de Shopify) pasada a texto
    plano -- se saca la etiqueta HTML pero NUNCA se resume ni se reescribe
    el contenido (pedido explicito: descripcion completa tal como la tiene
    la tienda, no resumida)."""
    texto = re.sub(r"<[^>]+>", " ", html_crudo or "")
    texto = html.unescape(texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _tallas_disponibles_shopify(producto_shopify):
    """Tallas con stock real (available=true) segun products.json publico
    de Shopify. Shopify publico solo expone disponible/agotado por talla,
    NUNCA una cantidad exacta -- confirmado a mano el 2026-08-24 (ver
    docs/catalogo_real.md), asi que esto es lo mas real que se puede cargar
    sin que la tienda de acceso a su inventario (API/integracion aparte)."""
    opciones = producto_shopify.get("options", [])
    idx_talla = None
    for i, opt in enumerate(opciones):
        if opt.get("name", "").strip().lower() in ("talla", "size", "tamano", "tamaño"):
            idx_talla = i
    tallas = []
    for variante in producto_shopify["variants"]:
        if not variante.get("available"):
            continue
        if idx_talla is not None:
            talla = variante.get(f"option{idx_talla + 1}")
        else:
            talla = variante.get("option1") or variante.get("title")
        if talla and talla not in tallas:
            tallas.append(talla)
    return tallas


def cargar_shopify_cache(ruta_json, excluir_handles=()):
    """Lee un products.json de Shopify ya cacheado en disco (ver
    data/shopify_cache/, bajado con curl real -- nunca inventado) y arma
    una lista de dicts con nombre/precio/path/fotos/descripcion_real/
    tallas_reales, todo dato real de la ficha de la tienda. NO clasifica
    categoria/corte -- eso lo sigue haciendo construir_producto() con
    clasificar_prenda()/detectar_corte()/VERIFICADO_A_MANO, igual que
    siempre."""
    datos = json.loads(Path(ruta_json).read_text(encoding="utf-8"))
    productos = []
    for p in datos["products"]:
        if p["handle"] in excluir_handles:
            continue
        variantes = p["variants"]
        productos.append({
            "nombre": p["title"],
            "precio": int(float(variantes[0]["price"])),
            "path": f"/products/{p['handle']}",
            "handle": p["handle"],
            "fotos": [img["src"] for img in p.get("images", [])],
            "descripcion_real": _limpiar_html(p.get("body_html")),
            "tallas_reales": _tallas_disponibles_shopify(p),
        })
    return productos


def datos_shopify_por_handle(ruta_json):
    """Mismo cache que cargar_shopify_cache(), pero indexado por handle --
    para cruzar productos YA cargados a mano (tuplas nombre/precio/path/
    imagen) contra el products.json real y pisarles imagen/descripcion/
    tallas con el dato real, sin tocar el corte/categoria ya verificados."""
    return {p["handle"]: p for p in cargar_shopify_cache(ruta_json)}


def construir_producto(idx, tienda, dominio, marca, nombre, precio_clp, path, imagen_rel,
                        marca_autor=True, es_gorro=False, color_dominante=None, forma_gorro=None,
                        fotos=None, descripcion_real=None, tallas_reales=None):
    categoria, subtipo, manga, largo = ("gorro", None, None, None) if es_gorro else clasificar_prenda(nombre)
    corte = detectar_corte(nombre)

    extra = VERIFICADO_A_MANO.get(nombre, {})
    if extra.get("corte"):
        corte = extra["corte"]
    if extra.get("subtipo"):
        # Override manual (2026-08-22): para cuando el nombre no trae la
        # palabra clave pero la FICHA o la FOTO real confirman el subtipo
        # (ej. bolsillos cargo visibles en la foto aunque el nombre no diga
        # "cargo") -- mismo criterio explicito del usuario que para
        # capucha/cierre por foto.
        subtipo = extra["subtipo"]
    if extra.get("categoria"):
        # Override manual (2026-08-22): para nombres de producto que no
        # traen NINGUNA palabra clave de categoria (ej. "Thunder Black" es
        # un pantalon, pero el nombre no dice "jean"/"pantalon"/etc.) --
        # confirmado leyendo la ficha real, nunca adivinado.
        categoria = extra["categoria"]
    if "largo" in extra:
        # Override manual (2026-08-23): para cuando el nombre matchea una
        # regla de largo automatica (ej. "baby tee" -> crop, ver
        # ES_BABY_TEE) pero la ficha REAL de ese producto puntual dice
        # explicitamente lo contrario -- no se asume el largo por el
        # nombre solo si la ficha lo contradice.
        largo = extra["largo"]

    corte_real = corte if corte and corte != "sin corte definido" else None

    producto = {
        "id": f"real_{tienda.lower().replace(' ', '').replace('.', '')}_{idx:04d}",
        "nombre": nombre,
        "marca": marca,
        "tienda": tienda,
        "link": link_absoluto(dominio, path),
        "precio": limpiar_precio(precio_clp),
        "precio_clp": precio_clp,
        "precio_original": "",
        "descuento_pct": None,
        "en_oferta": False,
        "descripcion": descripcion_real if descripcion_real else f"{marca} -- producto real de {tienda}, tienda chica chilena de streetwear. Precio y stock sujetos a cambios en el sitio de la tienda.",
        "imagen": fotos[0] if fotos else img_absoluta(imagen_rel),
        "genero": genero_de(nombre),
        "categoria": categoria,
        "ocasiones": OCASIONES_DEFAULT,
        "tags": ["streetwear", "urbano", marca.lower()] + ([corte_real] if corte_real else []),
        "marca_autor": marca_autor,
    }
    if fotos:
        # Fotos reales completas de la ficha de la tienda (todas, no solo
        # 3 de referencia) -- reemplaza el truco de espejar/recortar el
        # SVG ilustrativo que usa imagenesPreview() en comun.js cuando el
        # producto todavia no tiene fotos reales cargadas.
        producto["fotos"] = fotos

    if es_gorro:
        producto["forma"] = forma_gorro or "lana"
        if color_dominante:
            producto["color_dominante"] = color_dominante
        if (forma_gorro or "lana") == "lana":
            # Dato real, literal en el nombre ("Gorro Lana ...") -- nunca
            # inventado, ver MATERIALES_CONOCIDOS en app.py.
            producto["material"] = "lana"
    else:
        # tallas_reales=None (no vino de Shopify) -> rango tipico de la
        # tienda, como siempre. tallas_reales=[] es un dato REAL (Shopify
        # confirmo que hoy no hay ninguna talla disponible) -- no se
        # reemplaza por el rango generico, seria mentir stock que no hay.
        if tallas_reales is not None:
            producto["tallas_disponibles"] = tallas_reales
        else:
            producto["tallas_disponibles"] = TALLAS_POR_TIENDA.get(tienda, ["S", "M", "L", "XL"])
        if corte:
            producto["corte"] = corte
        if subtipo:
            producto["subtipo"] = subtipo
        if manga:
            producto["manga"] = manga
        if largo:
            producto["largo"] = largo
        if categoria == "poleron":
            cc = CAPUCHA_CIERRE_VERIFICADO.get(nombre, {})
            producto["capucha"] = cc.get("capucha", "no especificado")
            producto["cierre"] = cc.get("cierre", "no especificado")

    if extra.get("material"):
        producto["material"] = extra["material"]
    if extra.get("gramaje_gsm"):
        producto["gramaje_gsm"] = extra["gramaje_gsm"]

    return producto


# ---------------------------------------------------------------------
# Datos reales por tienda: (nombre, precio_clp, path_producto, imagen)
# ---------------------------------------------------------------------

OVA = [
    ("POLERA OVA APPAREL GOD´S PLAN NEGRA (PREVENTA)", 24990, "/products/polera-ova-apparel-god-s-plan-negra", "//ovachile.cl/cdn/shop/files/POLERA-OVA-GOD_S-PLAN-NEGRA.png?width=533"),
    ("BUZO BAGGY OVA APPAREL NEGRO (PREVENTA)", 34990, "/products/buzo-baggy-ova-apparel-negro-preventa", "//ovachile.cl/cdn/shop/files/CopiadeChatGPTImage17may2026_02_22_29p.m..png?width=533"),
    ("POLERA OVA APPAREL GOD´S PLAN BLANCA (PREVENTA)", 24990, "/products/polera-ova-apparel-god-s-plan-blanca", "//ovachile.cl/cdn/shop/files/POLERA-OVA-GOD_S-PLAN-ESPALDA.png?width=533"),
    ("POLERA OVA RETRO NEGRO", 24990, "/products/polera-ova-retro-negro", "//ovachile.cl/cdn/shop/files/CapturadePantalla2025-01-14ala_s_21.58.25.png?width=533"),
    ("POLERA OVA APPAREL OG BLANCA", 24990, "/products/polera-ova-apparel-og-blanca-1", "//ovachile.cl/cdn/shop/files/POLERA-OVA-APPAREL-OG-G-FRENTE.png?width=533"),
    ("BUZO BAGGY OVA APPAREL GRIS (PREVENTA)", 34990, "/products/buzo-baggy-ova-apparel-gris-preventa", "//ovachile.cl/cdn/shop/files/2_b4800935-095f-4e1f-b69a-539ea4aaf9f6.png?width=533"),
    ("Polera OVA Apparel Basics Heavyweight – Negra", 19990, "/products/polera-ova-apparel-basics-heavyweight-negra", "//ovachile.cl/cdn/shop/files/POLERA_NEGRA_LISA.png?width=533"),
    ("POLERA OVA APPAREL STREET DESIGN NEGRO", 24990, "/products/polera-ova-apparel-street-design-negro-preventa-copia", "//ovachile.cl/cdn/shop/files/11_b0b1fc3d-2e2a-46dd-8ba9-df6710bca0fb.png?width=533"),
    ("POLERA OVA APPAREL CLÁSICA CELESTE", 24990, "/products/polera-ova-apparel-clasica-celeste", "//ovachile.cl/cdn/shop/files/16_73270569-ef3d-418f-aea3-d59b545d2f52.png?width=533"),
    ("POLERA OVA APPAREL CLÁSICA CAFÉ CHOCOLATE", 24990, "/products/polera-ova-apparel-clasica-cafe-chocolate", "//ovachile.cl/cdn/shop/files/14.png?width=533"),
    ("POLERA OVA APPAREL THE CROSS BLANCA", 24990, "/products/polera-ova-apparel-the-cross-blanca-preventa", "//ovachile.cl/cdn/shop/files/5_20ff2d13-b64a-4daa-b38b-609aba9dfa98.png?width=533"),
    ("Polera OVA Apparel Basics Heavyweight – Blanca", 19990, "/products/polera-ova-apparel-basics-heavyweight-blanca", "//ovachile.cl/cdn/shop/files/POLERA_BLANCA_LISA_ecb036f1-581b-4b70-b6a8-7612eb8e03ce.png?width=533"),
    ("POLERA OVA APPAREL CLÁSICA VERDE", 24990, "/products/polera-ova-apparel-clasica-verde", "//ovachile.cl/cdn/shop/files/12.png?width=533"),
    ("POLERA OVA APPAREL STREET DESIGN CREMA", 24990, "/products/polera-ova-apparel-street-design-negro-preventa-copia-1", "//ovachile.cl/cdn/shop/files/13_f9808074-8a2e-4e13-b45e-6f8ddb0920a6.png?width=533"),
    ("POLERA OVA APPAREL CLÁSICA ROSADA", 24990, "/products/polera-ova-apparel-clasica-rosada", "//ovachile.cl/cdn/shop/files/10.png?width=533"),
    ("Polera OVA Apparel Basics Heavyweight – Arena", 19990, "/products/polera-ova-apparel-basics-heavyweight-arena", "//ovachile.cl/cdn/shop/files/POLERABEIGE_CREMA.png?width=533"),
    ("POLERA OVA APPAREL ART VERDE (PREVENTA)", 24990, "/products/polera-ova-apparel-art-verde", "//ovachile.cl/cdn/shop/files/shopify_87_2_1771988524_31a5af1b.png?width=533"),
    ("POLERA OVA APPAREL UNITED BROTHERS VERDE", 24990, "/products/polera-ova-apparel-street-design-celeste-preventa-copia", "//ovachile.cl/cdn/shop/files/20.png?width=533"),
    ("POLERA OVA APPAREL STREET DESIGN BLANCA", 24990, "/products/polera-ova-apparel-the-cross-cafe-preventa-copia", "//ovachile.cl/cdn/shop/files/7_1c009fe0-63ce-40e1-8520-ea6859933c58.png?width=533"),
    ("POLERA OVA APPAREL THE CROSS CAFÉ (PREVENTA)", 24990, "/products/polera-ova-apparel-the-cross-cafe-preventa", "//ovachile.cl/cdn/shop/files/thecrosscafe.png?width=533"),
]

OVERSAINTS = [
    ("Knit black", 50150, "/products/knits-black", "//studioversaints.com/cdn/shop/files/WhatsAppImage2025-11-28at13.01.12_769c2c67-7393-4bba-bf73-3a6941056c5b.jpg?width=1946"),
    ("Knit cream", 50150, "/products/knit-cream", "//studioversaints.com/cdn/shop/files/ChatGPTImage17dic2025_08_33_49p.m..png?width=1946"),
    ("Knit mint green", 50150, "/products/knite-sky-blue", "//studioversaints.com/cdn/shop/files/ChatGPTImage17dic2025_08_18_44p.m..png?width=1946"),
    ("Poleron black zipper", 66207, "/products/poleron-con-cierre", "//studioversaints.com/cdn/shop/files/8_749d0b6c-68ab-49cd-9a5e-25f41d16b274.png?width=1946"),
    ("Poleron Crema Anillo", 69790, "/products/poleron-crema-anillo", "//studioversaints.com/cdn/shop/files/mockupfeed_2_5ada1f7f-48fa-4df7-b8fd-09d447641ed4.svg?width=1946"),
    ("Poleron Gris Stone 777", 69790, "/products/hoodie-os-grey-copia", "//studioversaints.com/cdn/shop/files/mockupfeed_1.svg?width=1946"),
    ("Poleron OS Celeste", 35000, "/products/hoodie-os-skyblue", "//studioversaints.com/cdn/shop/files/mockupfeed_6.svg?width=1946"),
    ("Poleron pink zipper", 66207, "/products/poleron-pink-zipper", "//studioversaints.com/cdn/shop/files/6_9db49cce-46bd-4cfa-a664-bfd8df5e54a0.png?width=1946"),
    ("Poleron Washed OVRST", 69790, "/products/poleron-washed-ovrst", "//studioversaints.com/cdn/shop/files/mockupfeed_18.svg?width=1946"),
]

PULENTO = [
    ("BLACK & CENTER OVERZISE", 12490, "/producto/black-center-overzise/", "https://www.elpulentostyle.cl/wp-content/uploads/2025/11/IMG_9677-300x300.jpg"),
    ("BLACK & DIAMON STYLE OVERSIZE", 12990, "/producto/black-diamon-style-oversize/", "https://www.elpulentostyle.cl/wp-content/uploads/2026/02/Photoroom_20260206_210353-300x300.png"),
    ("RED LINES OVERSIZE STYLE", 14490, "/producto/red-lines-oversize-style/", "https://www.elpulentostyle.cl/wp-content/uploads/2026/01/IMG_0571-300x300.jpg"),
    ("BLACK & MONEY OVERZISE", 12990, "/producto/black-money-overzise/", "https://www.elpulentostyle.cl/wp-content/uploads/2025/11/69FE52BB-909D-471B-871E-7FBD52BFA5F1-300x300.jpg"),
    ("BLACK & STREET OVERZISE", 12490, "/producto/black-street-overzise/", "https://www.elpulentostyle.cl/wp-content/uploads/2025/11/IMG_0456-1-300x300.jpg"),
    ("STREET ON FIRE STYLE OVERSIZE", 12990, "/producto/street-on-fire-style/", "https://www.elpulentostyle.cl/wp-content/uploads/2026/02/IMG_1471-300x300.jpeg"),
    ("STREET YORK STYLE OVERSIZE", 12990, "/producto/street-york-style/", "https://www.elpulentostyle.cl/wp-content/uploads/2026/02/IMG_1444-1-300x300.jpg"),
    ("BLACK & THORNS OVERZISE", 13490, "/producto/black-thorns-overzise/", "https://www.elpulentostyle.cl/wp-content/uploads/2025/11/7584FA37-4898-45D2-A40B-F9E86681BCCE-300x300.jpg"),
    ("BROWN & OVERZISE", 11990, "/producto/brown-overzise/", "https://www.elpulentostyle.cl/wp-content/uploads/2025/11/IMG_9670-300x300.jpg"),
    ("COFFE & THORNS OVERZISE", 13390, "/producto/coffe-thorns-overzise/", "https://www.elpulentostyle.cl/wp-content/uploads/2025/11/IMG_9666-1-300x300.jpg"),
    ("CREAM & BROWN", 11990, "/producto/cream-brown/", "https://www.elpulentostyle.cl/wp-content/uploads/2026/01/IMG_0424-300x300.jpg"),
    ("STREET AND TRIP", 11990, "/producto/street-and-trip/", "https://www.elpulentostyle.cl/wp-content/uploads/2026/01/IMG_0864-300x300.jpg"),
]

RAPT = [
    ("GRID LAYER TEE MELANGE", 27990, "/grid-layer-tee-melange", "https://cdnx.jumpseller.com/rapt/image/75814900/resize/480/600"),
    ("GRID LAYER TEE NAVY", 27990, "/grid-layer-tee-navy", "https://cdnx.jumpseller.com/rapt/image/75815328/resize/480/600"),
    ("GRID SHIFT ZIP MELANGE", 39990, "/grid-shift-zip-melange", "https://cdnx.jumpseller.com/rapt/image/75816556/resize/480/600"),
    ("GRID SHIFT ZIP NAVY", 39990, "/grid-shift-zip-navy", "https://cdnx.jumpseller.com/rapt/image/75816371/resize/480/600"),
    ("RAW SHIFT HOODIE BLACK", 31990, "/raw-shift-hoodie-black", "https://cdnx.jumpseller.com/rapt/image/75819668/resize/480/600"),
    ("ACID SHIFT HOODIE", 34990, "/acid-shift-hoodie", "https://cdnx.jumpseller.com/rapt/image/75815640/resize/480/600"),
    ("DUAL SHIFT TEE SAND", 28990, "/dual-shift-tee-sand", "https://cdnx.jumpseller.com/rapt/image/75842970/resize/480/600"),
    ("PATCH SHIFT ZIP BLACK", 46990, "/patch-shift-zip-black", "https://cdnx.jumpseller.com/rapt/image/75834611/resize/480/600"),
    ("SHIFT LONGSLEEVE BLACK", 23990, "/shift-longsleeve-black", "https://cdnx.jumpseller.com/rapt/image/76168998/resize/480/600"),
    ("FOUNDATION JACKET", 74990, "/foundation-jacket", "https://cdnx.jumpseller.com/rapt/image/78942775/resize/480/600"),
    ("FOUNDATION TROUSER", 54990, "/foundation-trouser", "https://cdnx.jumpseller.com/rapt/image/78941214/resize/480/600"),
    ("RAW DENIM JACKET", 64990, "/raw-denim-jacket", "https://cdnx.jumpseller.com/rapt/image/79261184/resize/480/600"),
    ("COMMON HOODIE MORO", 39990, "/common-hoodie-moro", "https://cdnx.jumpseller.com/rapt/image/77844170/resize/480/600"),
    ("COMMON HOODIE AZURE", 39990, "/common-hoodie-azure", "https://cdnx.jumpseller.com/rapt/image/77844186/resize/480/600"),
    ("COMMON HOODIE MOSS", 39990, "/common-hoodie-moss", "https://cdnx.jumpseller.com/rapt/image/78874781/resize/480/600"),
    ("COMMON LONG SLEEVE MORO", 26990, "/common-tee-moro", "https://cdnx.jumpseller.com/rapt/image/78934163/resize/480/600"),
    ("COMMON LONG SLEEVE AZURE", 26990, "/common-tee-azure", "https://cdnx.jumpseller.com/rapt/image/78239087/resize/480/600"),
    ("COMMON LONG SLEEVE MOSS", 26990, "/common-tee-moss", "https://cdnx.jumpseller.com/rapt/image/78239091/resize/480/600"),
    ("FOUNDATION TROUSER BLACK", 54990, "/foundation-trouser-black", "https://cdnx.jumpseller.com/rapt/image/79535787/resize/480/600"),
    ("HOODIE ESSENCE CLASSIC II / PRE-ORDER", 38990, "/hoodie-essence-classic-ii", "https://cdnx.jumpseller.com/rapt/image/60258641/resize/480/600"),
]

ROOTSOUTH = [
    ("Black Few Run", 44990, "/products/black-few-run", "//rootsouth.cl/cdn/shop/files/HoodiesEcommerce-16.png?width=533"),
    ("Black Knit Original", 67990, "/products/chaleco-original-negro", "//rootsouth.cl/cdn/shop/files/Mesadetrabajo1_11_f43b9ecd-53a5-4aae-b908-c00d6328c4ab.png?width=533"),
    ("Black Knit Wear Conciously", 67990, "/products/chaleco-wear-conciously-negro", "//rootsouth.cl/cdn/shop/files/Mesadetrabajo1_12_1a1e418e-bf4a-42d0-9a37-e511908bb23f.png?width=533"),
    ("Black Origin Layers", 54990, "/products/black-origin-layers", "//rootsouth.cl/cdn/shop/files/BLACK_ORIGIN_BACK.png?width=533"),
    ("Black Zipper Layers", 67990, "/products/black-zipper-layers", "//rootsouth.cl/cdn/shop/files/BLACK_ZIP_FRONT.png?width=533"),
    ("Chocolate The Club", 44990, "/products/chocolate-the-club", "//rootsouth.cl/cdn/shop/files/HoodiesEcommerce-09.png?width=533"),
    ("Chocolate Zipper", 59990, "/products/zipper-chocolatte", "//rootsouth.cl/cdn/shop/files/Rootsouth_Winter_Games_Mesa_de_trabajo_1-19.jpg?width=533"),
    ("Chocolate Zipper Patch", 54990, "/products/chocolate-zipper-patch", "//rootsouth.cl/cdn/shop/files/CHOCOLATE_ZIP_PATCH_FRONT.png?width=533"),
    ("Cream Mountain", 59990, "/products/cream-mountain", "//rootsouth.cl/cdn/shop/files/CAPPU_MOUNT_BACJK.png?width=533"),
    ("Cream Rootsouth Club", 39990, "/products/cream-rootsouth-club", "//rootsouth.cl/cdn/shop/files/HoodiesEcommerce-19.png?width=533"),
    ("Cream Zipper Rootsouth Est", 59990, "/products/cream-zipper-rootsouth-est", "//rootsouth.cl/cdn/shop/files/CAPPU_ZIP_BACK.png?width=533"),
    ("Espresso Zip Knit", 69990, "/products/knit-zipper-brown", "//rootsouth.cl/cdn/shop/files/1_8878f0a0-52f5-422d-9f77-8e998b5191d0.png?width=533"),
    ("Gray Knit Original", 67990, "/products/chaleco-original-gris", "//rootsouth.cl/cdn/shop/files/Mesadetrabajo1_4_5eae2ed1-d262-4da9-b441-84d56dba68bb.png?width=533"),
    ("Gray Knit Wear Conciously", 67990, "/products/chaleco-wear-conciously-gris", "//rootsouth.cl/cdn/shop/files/Mesadetrabajo1_10_4489af8e-4d49-41c3-b41b-db23c34629f7.png?width=533"),
    ("Hahave T-shirt Black", 25990, "/products/polera-1", "//rootsouth.cl/cdn/shop/files/Mesadetrabajo21_4.png?width=533"),
]

ROTTEN = [
    ("bedrot longsleeve", 31990, "/products/bedrot-longsleeve", "//rottenbrand.cl/cdn/shop/files/bedrot-longsleeve-pagina-v1.png?width=3840"),
    ("black blur tee", 26990, "/products/black-blur-tee", "//rottenbrand.cl/cdn/shop/files/blur-tee-negra-pagina-fondo.jpg?width=3840"),
    ("black love solitude tee", 26990, "/products/black-love-solitude-tee", "//rottenbrand.cl/cdn/shop/files/solitude-negra-pagina-fondo_872a3e3d-9484-40da-86a5-a697b6d76dd3.png?width=3840"),
    ("blur tee", 26990, "/products/blur-white-tee", "//rottenbrand.cl/cdn/shop/files/blur-tee-blanca-pagina-fondo.jpg?width=3840"),
    ("dnd baby tee", 21990, "/products/dnd-babe-tee", "//rottenbrand.cl/cdn/shop/files/baby-tee-pagina-v2.png?width=3840"),
    ("gia longsleeve", 29990, "/products/gia-black-longsleeve", "//rottenbrand.cl/cdn/shop/files/longsleeves-pagina-fondo.jpg?width=3840"),
    ("gia longsleeve (regular fit)", 29990, "/products/gia-longsleeve-regular-fit", "//rottenbrand.cl/cdn/shop/files/gia-ls-negra-pagina-fondo_617a13f9-21b8-4d7c-92a6-b2ddb6458a03.png?width=3840"),
    ("gia tee", 26990, "/products/gia-tee", "//rottenbrand.cl/cdn/shop/files/gia-tee-pagina-fondo.jpg?width=3840"),
    ("gia tee (regular fit)", 26990, "/products/gia-tee-regular-fit", "//rottenbrand.cl/cdn/shop/files/gia-negra-pagina-fondo_cd1757b2-6821-451d-8832-9849bfad4de1.png?width=3840"),
    ("longsleeve black", 28990, "/products/longsleeve-v2-black", "//rottenbrand.cl/cdn/shop/files/longsleeve-negra-web.png?width=3840"),
    ("longsleeve cherry", 28990, "/products/longsleeve-v2-burgundy", "//rottenbrand.cl/cdn/shop/files/longsleeve-cherry-web.png?width=3840"),
    ("longsleeve dark blue", 28990, "/products/longsleeve-v2-dark-blue", "//rottenbrand.cl/cdn/shop/files/longsleeve-azul-web.png?width=3840"),
    ("longsleeve olive green", 28990, "/products/longsleeve-olive-green", "//rottenbrand.cl/cdn/shop/files/longsleeve-verde-web.png?width=3840"),
    ("red blur tee", 26990, "/products/red-blur-tee", "//rottenbrand.cl/cdn/shop/files/blur-tee-rojo-pagina-fondo.jpg?width=3840"),
    ("red love solitude tee", 26990, "/products/red-love-solitude-shirt", "//rottenbrand.cl/cdn/shop/files/solitude-roja-pagina-fondo_2a379325-4de9-4385-9f0c-fffc9f3d4d96.png?width=3840"),
    ("rotten keychain tee", 26990, "/products/rotten-keychain-tee", "//rottenbrand.cl/cdn/shop/files/rotten-keychain-pagina.png?width=3840"),
    ("white gia tee", 26990, "/products/white-gia-tee", "//rottenbrand.cl/cdn/shop/files/gia-tee-blanca-pagina-fondo.jpg?width=3840"),
    ("white gia tee (regular fit)", 26990, "/products/white-gia-tee-regular-fit", "//rottenbrand.cl/cdn/shop/files/gia-regular-blanca-pagina-fondo_b8135b29-e832-4e71-84f4-04077d5faf6f.png?width=3840"),
    ("white love solitude tee", 26990, "/products/white-love-solitude-shirt", "//rottenbrand.cl/cdn/shop/files/solitude-blanca-pagina-fondo_b36c7d18-4668-4460-9edb-d03935091087.png?width=3840"),
]

SELVANEGRA_POLERAS = [
    ("Polera Logo Verde", 12593, "/producto/polera-logo-verde/", "https://selvanegrawear.cl/wp-content/uploads/2023/12/polera-logo-verde.jpg"),
    ("Polera Oranwutang Logo Negra", 12593, "/producto/polera-oranwutang-logo-negra/", "https://selvanegrawear.cl/wp-content/uploads/2024/11/polera-logo-wu-negra-2.jpg"),
    ("Polera Oranwutang Micro Blanca", 12593, "/producto/polera-oranwutang-micro-blanca/", "https://selvanegrawear.cl/wp-content/uploads/2023/10/POLERA-ORANWU-MICRO-BLANCO-1-683x1024.jpg"),
    ("Polera Pixa-Throwup Negra", 12593, "/producto/polera-pixa-throwup-negra/", "https://selvanegrawear.cl/wp-content/uploads/2024/11/polera-pixa-throuw-negro.jpg"),
    ("Polera SheoxTatto Negra", 12593, "/producto/polera-sheotatto-negra/", "https://selvanegrawear.cl/wp-content/uploads/2025/01/polera-sheo-gris.jpg"),
    ("Polera TagxGiro Burdeo", 12593, "/producto/polera-tagxgiro/", "https://selvanegrawear.cl/wp-content/uploads/2023/10/polera-tag-x-giro-burdeo-x-desco.jpg"),
    ("Polera TagxGiro Negra", 12593, "/producto/polera-tagxgiro-negra/", "https://selvanegrawear.cl/wp-content/uploads/2023/10/polera-tag-giro-negra-2.png"),
    ("Polera Pixa-Throwup Mora", 12593, "/producto/polera-pixa-throwup-mora/", "https://selvanegrawear.cl/wp-content/uploads/2024/11/polera-pixa-throuw-mora.jpg"),
    ("Polera Flubber", 12593, "/producto/polera-flubber/", "https://selvanegrawear.cl/wp-content/uploads/2024/11/polera-flubber-1.jpg"),
    ("Polera Mono Hiphop 50 Años Blanca", 12593, "/producto/polera-mono-hiphop-50-anos-blanca/", "https://selvanegrawear.cl/wp-content/uploads/2023/11/mono-h2-blanca-1.jpg"),
    ("Polera SheoxTatto", 12593, "/producto/polera-sxcheo-tatto/", "https://selvanegrawear.cl/wp-content/uploads/2024/11/polera-sheo-roja-2.jpg"),
    ("Polera Logo Clásica", 12593, "/producto/polera-logo/", "https://selvanegrawear.cl/wp-content/uploads/2023/10/polera-logo-negro-2-1.jpg"),
    ("Canguro Calaka Letras Verdes", 18990, "/producto/canguro-sn-calaka-letras-verdes/", "https://selvanegrawear.cl/wp-content/uploads/2024/01/CANGURO-CALAKA-SN-LETRAS-VERDES-1-576x1024.jpeg"),
    ("Canguro Sunset Mujer", 15990, "/producto/canguro-sunset-mujer/", "https://selvanegrawear.cl/wp-content/uploads/2023/11/WhatsApp-Image-2023-11-15-at-23.27.48-1-683x1024.jpeg"),
    # Las 4 "Sudadera" (Gris Perla/Marengo/Oranwutang/Sudamérica) se sacaron
    # el 2026-08-20 -- confirmado en el sitio real (selvanegrawear.cl) que
    # son musculosas sin mangas de liquidación ("Remate"/"Stock Total", 1
    # sola talla cada una), no polerones, a pesar del nombre. No hay
    # categoria "musculosa"/tank top en la app todavia -- si el dueño del
    # proyecto la quiere agregar mas adelante, volver a sumarlas ahi.
]

# (nombre, precio_clp, path, imagen, color_dominante o None)
SELVANEGRA_GORROS = [
    ("Gorro Lana Liso Lila", 6993, "/producto/gorro-lana-liso-lila/", "https://selvanegrawear.cl/wp-content/uploads/2023/11/Gemini_Generated_Image_wgyvbvwgyvbvwgyv-820x1024.png", "morado"),
    ("Gorro Lana Liso Negro", 6993, "/producto/gorro-lana-liso-negro/", "https://selvanegrawear.cl/wp-content/uploads/2026/05/Gemini_Generated_Image_bloqmnbloqmnbloq.png", "negro"),
    ("Gorro Lana Liso Rosa", 6993, "/producto/gorro-lana-liso-rosa/", "https://selvanegrawear.cl/wp-content/uploads/2023/11/Gemini_Generated_Image_z5hcvfz5hcvfz5hc-1-768x1024.png", None),
    ("Gorro Lana Liso Verde", 6993, "/producto/gorro-lana-liso-verde/", "https://selvanegrawear.cl/wp-content/uploads/2023/11/Gemini_Generated_Image_gd4p69gd4p69gd4p-768x1024.png", "verde"),
    ("Gorro Lana Tie Dye Amarillo", 6993, "/producto/gorro-lana-tie-dye-amarillo/", "https://selvanegrawear.cl/wp-content/uploads/2026/05/Gemini_Generated_Image_ppe7e0ppe7e0ppe7.png", "amarillo"),
    ("Gorro Lana Tie Dye Celeste", 6993, "/producto/gorro-lana-tie-dye-celeste/", "https://selvanegrawear.cl/wp-content/uploads/2026/05/Gemini_Generated_Image_964r1x964r1x964r.png", "azul"),
    ("Gorro Lana Tie Dye Naranja", 6993, "/producto/gorro-lana-tie-dye-naranja/", "https://selvanegrawear.cl/wp-content/uploads/2026/05/Gemini_Generated_Image_4wg16k4wg16k4wg1.png", None),
    ("Gorro Lana Tie Dye Verde", 6993, "/producto/gorro-lana-tie-dye-verde/", "https://selvanegrawear.cl/wp-content/uploads/2026/05/Gemini_Generated_Image_1uc0s31uc0s31uc0.png", "verde"),
]

SIMPL = [
    ("PANTALON BAGGY BLANK (NEGRO)", 29990, "/products/pantalon-baggy-blank-negro", "//simpl.cl/cdn/shop/files/7_693666fd-b282-43e6-883b-952441dda6fd.png?width=1920"),
    ("PANTALON BAGGY BLANK (CREMA)", 29990, "/products/pantalon-baggy-blank-crema", "//simpl.cl/cdn/shop/files/32_ef1068b8-be38-484d-acc2-c71337855951.png?width=1920"),
    ("PANTALON BAGGY BLANK (GRIS MELANGE)", 29990, "/products/pantalon-baggy-blank-gris-melange", "//simpl.cl/cdn/shop/files/15_1d5f9981-6116-4866-b89b-ada57d89115f.png?width=1920"),
    ("PANTALON BAGGY ESENCIAL (NEGRO)", 29990, "/products/pantalon-esencial-negro", "//simpl.cl/cdn/shop/files/7_7fa94e2b-96f8-44a1-b21d-5b23d45016c3.png?width=1920"),
    ("PANTALON BAGGY ESENCIAL (MARINO)", 29990, "/products/pantalon-baggy-esencial-marino", "//simpl.cl/cdn/shop/files/88_0f58018b-882a-4b4c-8549-ea5ada8cc49e.png?width=1920"),
    ("PANTALON BAGGY ESENCIAL (ROJO)", 29990, "/products/pantalon-baggy-esencial-rojo", "//simpl.cl/cdn/shop/files/64_d0cd98fa-f29d-4b68-86dd-dd3e8b6a3e45.png?width=1920"),
    ("PANTALON BAGGY LIVE YOUR DREAM (NEGRO)", 29990, "/products/pantalon-baggy-live-your-dream-negro", "//simpl.cl/cdn/shop/files/13_f36cb99a-7a3d-4a11-915e-f8e2fb73219c.png?width=1920"),
    ("PANTALON BAGGY MAKE IT SIMPLE (NEGRO)", 29990, "/products/pantalon-baggy-make-it-simple-negro", "//simpl.cl/cdn/shop/files/5_a07aa4a4-1ed8-46ed-bd99-a93fdd18f2d3.png?width=1920"),
    ("PANTALON BAGGY MAKE IT SIMPLE (MARINO)", 29990, "/products/pantalon-baggy-make-it-simple-marinp", "//simpl.cl/cdn/shop/files/3_c05a5e04-86bb-4b7a-8a69-ede0dc6a9c46.png?width=1920"),
    ("PANTALON BAGGY STARS (NEGRO)", 29990, "/products/pantalon-baggy-stars-negro", "//simpl.cl/cdn/shop/files/29_7c95b144-c9b1-4af0-adb3-b0870f2b887b.png?width=1920"),
    ("PANTALON BAGGY STARS (MARINO)", 29990, "/products/pantalon-baggy-stars-marino", "//simpl.cl/cdn/shop/files/23_1ca6eeb0-59d0-4e83-bce9-2c96f59737d1.png?width=1920"),
    ("PANTALON BAGGY THANK GOD (NEGRO)", 29990, "/products/pantalon-baggy-thank-god-negro", "//simpl.cl/cdn/shop/files/29_d0067a0a-4f33-40b6-a0ae-3e9a776f0b97.png?width=1920"),
    ("PANTALON BAGGY THANK GOD (ROJO)", 29990, "/products/pantalon-baggy-thank-god-rojo", "//simpl.cl/cdn/shop/files/5_9b5d3435-6323-4a7a-9808-cda40734b66a.png?width=1920"),
    ("PANTALON CARGO WOODLAND (CAMO)", 34990, "/products/pantalon-baggy-blank-gris-melange-copia", "//simpl.cl/cdn/shop/files/25_6584194f-f1c2-476e-a018-aa0df49a9872.png?width=1920"),
    ("POLERA .TXT (ACID WASH)", 24990, "/products/polera-txt-acid-wash", "//simpl.cl/cdn/shop/files/22_36a54cbd-59ff-4f66-a3da-4e10b2553707.png?width=1920"),
    ("POLERA .TXT (BLANCA)", 19990, "/products/polera-txt-blanca", "//simpl.cl/cdn/shop/files/70.png?width=1920"),
    ("POLERA .TXT (CAFÉ)", 19990, "/products/polera-txt-cafe-claro", "//simpl.cl/cdn/shop/files/76_efe2e9ac-f197-4f30-ae87-c53497f0d74f.png?width=1920"),
]

# 2026-08-22 -- tienda nueva, investigada desde el Excel de candidatas
# (C:\Users\56982\Downloads\tiendas_ropa_urbana_lista_final.xlsx, fila
# "absolutely Wrong"). Sitio real confirmado (Shopify), diseno propio (no
# reventa). Se excluyeron 2 productos digitales que aparecian en el
# catalogo ("Lista de proveedores" PDF, "Paquete de mockups") -- no son
# ropa.
ABSOLUTELYWRONG = [
    ("PANTALON BASICO HEAVYWEIGHT (ROSADO)", 29990, "/products/pantalon-basico-heavyweight-1?variant=48834117304545", "https://absolutelywrong.cl/cdn/shop/files/FullSizeRender_b41bc295-9d74-440f-b680-62f571e118ca_jpg.png?v=1775839258&width=1946"),
    ("PANTALON BASICO HEAVYWEIGHT (CAFE)", 29990, "/products/pantalon-basico-heavyweight-1?variant=48834117468385", "https://absolutelywrong.cl/cdn/shop/files/FullSizeRender_b41bc295-9d74-440f-b680-62f571e118ca_jpg.png?v=1775839258&width=1946"),
    ("PANTALON MARINO (HEAVYWEIGHT)", 27990, "/products/pantalon-marino-heavyweight", "https://absolutelywrong.cl/cdn/shop/files/FullSizeRender_e8168aff-4fde-421c-bc9e-c3a60be1aa78.jpg?v=1756867665&width=1946"),
    ("POLERA BOXY BLACKSUMMER (HEAVYWEIGHT)", 21990, "/products/polera-boxy-blacksummer-heavyweight", "https://absolutelywrong.cl/cdn/shop/files/A5FD3AA6-E11F-418B-8E4E-873DB5406F62.jpg?v=1762216062&width=1946"),
    ("POLERA HANNAH MONTANA OVERSIZED (HEAVYWEIGHT) NEGRO", 21990, "/products/polera-hannah-montana-oversized-heavyweight?variant=48107390337249", "https://absolutelywrong.cl/cdn/shop/files/HANNAH_BOXY_BLACK_BACK_1853b181-b611-4ba7-96eb-b1de65202669.png?v=1776273062&width=1946"),
    ("POLERA HANNAH MONTANA OVERSIZED (HEAVYWEIGHT) CREMA", 21990, "/products/polera-hannah-montana-oversized-heavyweight?variant=48107390468321", "https://absolutelywrong.cl/cdn/shop/files/HANNAH_BOXY_BLACK_BACK_1853b181-b611-4ba7-96eb-b1de65202669.png?v=1776273062&width=1946"),
    ("POLERA OVERSIZED (HEAVYWEIGHT) NEGRO", 21990, "/products/polera-boxy-oversized-basica?variant=47670768074977", "https://absolutelywrong.cl/cdn/shop/files/boxy_negra_front_b850f059-378f-4c00-8908-13593f3875a1.png?v=1765404868&width=1946"),
    ("POLERA OVERSIZED (HEAVYWEIGHT) BLANCO", 21990, "/products/polera-boxy-oversized-basica?variant=48228691083489", "https://absolutelywrong.cl/cdn/shop/files/boxy_negra_front_b850f059-378f-4c00-8908-13593f3875a1.png?v=1765404868&width=1946"),
    ("POLERA OVERSIZED (HEAVYWEIGHT) CREMA", 21990, "/products/polera-boxy-oversized-basica?variant=46792596259041", "https://absolutelywrong.cl/cdn/shop/files/boxy_negra_front_b850f059-378f-4c00-8908-13593f3875a1.png?v=1765404868&width=1946"),
    ("POLERA OVERSIZED (HEAVYWEIGHT) CAFE", 21990, "/products/polera-boxy-oversized-basica?variant=46792596160737", "https://absolutelywrong.cl/cdn/shop/files/boxy_negra_front_b850f059-378f-4c00-8908-13593f3875a1.png?v=1765404868&width=1946"),
    ("POLERA REGULAR FIT (HEAVYWEIGHT) ROSADO", 21990, "/products/polera-regular-fit-heavyweight-1?variant=48091991572705", "https://absolutelywrong.cl/cdn/shop/files/DSC08167.jpg?v=1773678546&width=1946"),
    ("POLERA REGULAR FIT (HEAVYWEIGHT) CAFE", 21990, "/products/polera-regular-fit-heavyweight-1?variant=48091991310561", "https://absolutelywrong.cl/cdn/shop/files/DSC08167.jpg?v=1773678546&width=1946"),
    ("POLERON GAY BOXY OVERSIZED", 26990, "/products/poleron-gay-pride-2026", "https://absolutelywrong.cl/cdn/shop/files/GAY_-_POLERON_BOXY_gris.png?v=1781737881&width=1946"),
    ("SHORT BLACKSUMMER (HEAVYWEIGHT)", 21490, "/products/short-blacksummer-heavyweight", "https://absolutelywrong.cl/cdn/shop/files/7C4C96AC-C23B-4CF6-86AF-DB70A45BF8C5.jpg?v=1762275773&width=1946"),
    ("PANTALON BASICO HEAVYWEIGHT NEGRO (PREVENTA)", 55990, "/products/pantalon-basico-heavyweight?variant=48092252176609", "https://absolutelywrong.cl/cdn/shop/files/FullSizeRender_b41bc295-9d74-440f-b680-62f571e118ca_jpg.png?v=1775839258&width=1946"),
    ("PANTALON BASICO HEAVYWEIGHT GRIS (PREVENTA)", 55990, "/products/pantalon-basico-heavyweight?variant=48812636668129", "https://absolutelywrong.cl/cdn/shop/files/FullSizeRender_b41bc295-9d74-440f-b680-62f571e118ca_jpg.png?v=1775839258&width=1946"),
    ("PANTALON BASICO HEAVYWEIGHT AZUL MARINO (PREVENTA)", 55990, "/products/pantalon-basico-heavyweight?variant=48812636831969", "https://absolutelywrong.cl/cdn/shop/files/FullSizeRender_b41bc295-9d74-440f-b680-62f571e118ca_jpg.png?v=1775839258&width=1946"),
    ("PANTALON BASICO HEAVYWEIGHT BURDEO (PREVENTA)", 55990, "/products/pantalon-basico-heavyweight?variant=48812636995809", "https://absolutelywrong.cl/cdn/shop/files/FullSizeRender_b41bc295-9d74-440f-b680-62f571e118ca_jpg.png?v=1775839258&width=1946"),
    ("POLERON BASICO HEAVYWEIGHT NEGRO (PREVENTA)", 59990, "/products/poleron-absolutely-negro?variant=48079354953953", "https://absolutelywrong.cl/cdn/shop/files/NEGRO_FRONT.png?v=1775832659&width=1946"),
    ("POLERON BASICO HEAVYWEIGHT GRIS (PREVENTA)", 59990, "/products/poleron-absolutely-negro?variant=48812623855841", "https://absolutelywrong.cl/cdn/shop/files/NEGRO_FRONT.png?v=1775832659&width=1946"),
    ("POLERON BASICO HEAVYWEIGHT AZUL MARINO (PREVENTA)", 59990, "/products/poleron-absolutely-negro?variant=48812624085217", "https://absolutelywrong.cl/cdn/shop/files/NEGRO_FRONT.png?v=1775832659&width=1946"),
    ("POLERON BASICO HEAVYWEIGHT BURDEO (PREVENTA)", 59990, "/products/poleron-absolutely-negro?variant=48812624314593", "https://absolutelywrong.cl/cdn/shop/files/NEGRO_FRONT.png?v=1775832659&width=1946"),
    ("POLERON BASICO HEAVYWEIGHT ROSADO (PREVENTA)", 59990, "/products/poleron-absolutely-negro?variant=48079355019489", "https://absolutelywrong.cl/cdn/shop/files/NEGRO_FRONT.png?v=1775832659&width=1946"),
]

# 2026-08-22/23 -- tienda nueva desde el Excel (fila "forceblack.cl").
# Sitio real confirmado (Shopify), marca propia de jeans/denim urbano
# (no reventa). Todo el catalogo son jeans + 1 short.
FORCEBLACK = [
    ("Black acid wash jeans", 21990, "/products/black-acid-wash", "//forceblack.cl/cdn/shop/files/794F5ECC-C179-40E3-A3DA-E62637D6987F.png?v=1785624236&width=1000"),
    ("Black bur jeans", 21990, "/products/black-bur", "//forceblack.cl/cdn/shop/files/9981A24F-BE59-497F-B82D-991B044F9273.png?v=1785624322&width=1000"),
    ("Black diamond flare jeans", 21990, "/products/black-diamond-flare", "//forceblack.cl/cdn/shop/files/A32346E5-64BD-4654-956F-9B0FAD63E27B.png?v=1785624296&width=1000"),
    ("Black Ripped jeans", 21990, "/products/black-ripped", "//forceblack.cl/cdn/shop/files/B37E3560-325A-4307-9E16-89C49CB69703.png?v=1785624553&width=1000"),
    ("Blessing VVS jeans", 21990, "/products/blessing-vvs", "//forceblack.cl/cdn/shop/files/6D6ECA76-45B9-4575-A73B-CFA843FDD898.png?v=1785624628&width=1000"),
    ("Blue Glow VVS jeans", 21990, "/products/blue-glow-vvs", "//forceblack.cl/cdn/shop/files/672B2D0A-B96E-4D08-A93F-BC11DCE59D8C.png?v=1785624661&width=1000"),
    ("Blue motion cargo flare jeans", 21990, "/products/blue-motion-cargo-flare", "//forceblack.cl/cdn/shop/files/4B42F27E-133A-4567-99BE-8404AD5114E8.png?v=1785624262&width=1000"),
    ("Cloud denim cargo jeans", 21990, "/products/cloud-denim-cargo", "//forceblack.cl/cdn/shop/files/4793595A-E93D-460C-B73A-11F2512E123E.png?v=1785624057&width=1000"),
    ("Denim diamond flare jeans", 21990, "/products/denim-diamond-flare", "//forceblack.cl/cdn/shop/files/D18B9A46-D956-4001-A38E-E7CD0EA9BD1A.png?v=1785624136&width=1000"),
    ("Denim Essentials jeans", 21990, "/products/denim-essentials", "//forceblack.cl/cdn/shop/files/2878542B-A091-462C-9800-049896FFA6DC.png?v=1785624373&width=1000"),
    ("Essentials Black jeans", 21990, "/products/essentials-black", "//forceblack.cl/cdn/shop/files/4BB9D2EE-9D48-4827-835D-4707A7ECE387.png?v=1785624477&width=1000"),
    ("Essentials Blue jeans", 21990, "/products/essentials-blue", "//forceblack.cl/cdn/shop/files/2E49CF38-B2DA-4A97-8077-D8EE084E7E54.png?v=1785624204&width=1000"),
    ("Iron Black jeans", 21990, "/products/iron-black", "//forceblack.cl/cdn/shop/files/6E7B6F76-1D9E-436E-9339-6A094A62BB84.png?v=1785624522&width=1000"),
    ("Iron Blue Cargo jeans", 21990, "/products/iron-blue-cargo", "//forceblack.cl/cdn/shop/files/04BE9258-B616-4FC5-B288-5CF5E044DA47.png?v=1785624350&width=1000"),
    ("Iron grey jeans", 21990, "/products/iron-grey", "//forceblack.cl/cdn/shop/files/FE0E35E8-864F-45CB-8B83-8D92F46D677A.png?v=1785624177&width=1000"),
    ("Iron Ice jeans", 21990, "/products/iron-ice", "//forceblack.cl/cdn/shop/files/FFC959FA-B6C0-41A2-BF33-FAAC4EA8F118.png?v=1785624504&width=1000"),
    ("Light Ripped jeans", 21990, "/products/light-ripped", "//forceblack.cl/cdn/shop/files/8C8C64D8-917C-4529-B2EC-F5C989915666.png?v=1785624405&width=1000"),
    ("Short blackrugged", 14990, "/products/short-blackrugged", "//forceblack.cl/cdn/shop/files/0E937590-73A5-46BA-8777-2F438515CF92.png?v=1785624605&width=1000"),
    ("Sky blue cargo jeans", 21990, "/products/sky-blue-cargo-jeans", "//forceblack.cl/cdn/shop/files/AD6C5ECC-0530-4930-95AE-723B96AC569A.png?v=1785624678&width=1000"),
    ("Sky frost jeans", 21990, "/products/sky-frost", "//forceblack.cl/cdn/shop/files/E1013452-3AD5-4AE0-B19C-34AFF758C209.png?v=1785624572&width=1000"),
    ("Thunder Black", 21990, "/products/thunder-black", "//forceblack.cl/cdn/shop/files/B4931AAD-9A45-49D2-A4EC-65355CD3E3E3.png?v=1785624433&width=1000"),
    ("Thunder VVS jeans", 21990, "/products/thunder-vvs", "//forceblack.cl/cdn/shop/files/CED70BFB-9437-4B8E-A635-11B09DCF079F.png?v=1785624701&width=1000"),
]

# 2026-08-23 -- tienda nueva desde el Excel (fila "Floating"). Sitio real
# confirmado (Shopify), diseno propio. Se excluyo "Tag Camo Cap" (gorro
# tipo cap/snapback -- el flujo de gorro de la app es solo curvo/plano/
# lana, no tiene equivalente "cap" con visera, se deja fuera hasta definir
# ese caso con el dueno del proyecto).
FLOATING = [
    ("Aero pants", 42990, "/products/aero-pants", "https://floating.cl/cdn/shop/files/Floating-2.jpg?v=1747189945&width=1946"),
    ("Baby tee", 15192, "/products/baby-tee", "//floating.cl/cdn/shop/files/BBYTEEIA.jpg?v=1765146594&width=1946"),
    ("FLTNG Zip Hoodie", 43990, "/products/fltng-zip-hoodie", "//floating.cl/cdn/shop/files/IMG_1023.jpg?v=1772821942&width=1946"),
    ("FLTNG ZIP V2", 44990, "/products/fltng-zip-v2", "//floating.cl/cdn/shop/files/IMG_1023.jpg?v=1772821942&width=1946"),
    ("Hover Denim", 44990, "/products/hover-denim", "https://floating.cl/cdn/shop/files/IMG_0539.jpg?v=1765838531&width=1946"),
    ("Noir Pulse", 47990, "/products/noir-pulse", "https://floating.cl/cdn/shop/files/Floating-10.jpg?v=1747098931&width=1946"),
    ("Noir Pulse - Aureum", 42990, "/products/noir-pulse-aureum", "https://floating.cl/cdn/shop/files/Floating-10.jpg?v=1747098931&width=1946"),
    ("Noir Pulse - Emerald", 42990, "/products/noir-pulse-emerald", "https://floating.cl/cdn/shop/files/Floating-10.jpg?v=1747098931&width=1946"),
    ("Noir Pulse - Morganite", 42990, "/products/noir-pulse-morganite", "https://floating.cl/cdn/shop/files/Floating-10.jpg?v=1747098931&width=1946"),
    ("Nomad Jort", 28792, "/products/nomad-jort", "https://floating.cl/cdn/shop/files/DSC04532.jpg?v=1759191740&width=1946"),
    ("Nuit Volt", 42990, "/products/nuit-volt", "https://floating.cl/cdn/shop/files/IMG_0986_1_-5.jpg?v=1756604129&width=1946"),
    ("Nuit Volt - Heaven", 42990, "/products/nuit-volt-heaven", "https://floating.cl/cdn/shop/files/IMG_0986_1_-5.jpg?v=1756604129&width=1946"),
    ("Nuit Volt - Void", 42990, "/products/nuit-volt-void", "https://floating.cl/cdn/shop/files/IMG_0986_1_-5.jpg?v=1756604129&width=1946"),
    ("Polera Esencial - Blanca", 17592, "/products/t-shirt-blanca", "https://floating.cl/cdn/shop/files/POLERABLANCAIA.jpg?v=1765145612&width=1946"),
    ("Polera Esencial - Verde botella", 17592, "/products/polera-floating-verde-botella", "https://floating.cl/cdn/shop/files/POLERABLANCAIA.jpg?v=1765145612&width=1946"),
    ("Shadow Jorts", 39000, "/products/shadow-jorts", "https://floating.cl/cdn/shop/files/763A2A36-5891-4685-BA3F-AF837865313B.jpg?v=1770590544&width=1946"),
    ("Stealth Jorts", 30591, "/products/stealth-jorts", "https://floating.cl/cdn/shop/files/763A2A36-5891-4685-BA3F-AF837865313B.jpg?v=1770590544&width=1946"),
]

# 2026-08-23 -- tienda nueva desde el Excel (fila "BANG GANG (BVNG GVNG)").
# Sitio real confirmado (Shopify), catalogo grande (92 productos de ropa),
# extraido via products.json (mas confiable que WebFetch para catalogos
# grandes -- ver docs/catalogo_real.md). Excluidos: "Proteccion de Envio"
# (no es ropa), "Rockstar Mask" y los 3 "Trucker Hat..." (accesorios sin
# categoria soportada en la app), los "Pack...Mystery" (sorpresa, no se
# puede verificar que producto especifico trae cada uno).
BANGGANG = [
    ("Polera Crystals Logo Acid Wash", 44990, "/products/polera-crystals-logo-acid-wash", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-crystals-logo-acid-wash-1967787.png?v=1785882667"),
    ("Poleron Crystals Logo BG", 39990, "/products/polera-crystals-logo-bg", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-crystals-logo-bg-7349817.png?v=1784142307"),
    ("Poleron Heavy Crystals", 84990, "/products/poleron-heavy-crystals", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-heavy-crystals-4385766.png?v=1784142307"),
    ("Poleron Crystals Logo BG", 69990, "/products/poleron-crystals-logo-bg", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-crystals-logo-bg-9975398.png?v=1784142307"),
    ("Polera Crystals Logo Heavyweight Black", 53990, "/products/polera-crystals-logo-heavyweight-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-crystals-logo-heavyweight-black-7584838.png?v=1784142307"),
    ("Polera Crystals Logo Heavyweight Grey", 53990, "/products/polera-crystals-logo-heavyweight-grey", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-crystals-logo-heavyweight-grey-4773133.png?v=1784142307"),
    ("Poleron 333 White Black Chance", 54990, "/products/poleron-333-white-black-chance", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-333-white-black-chance-6941360.png?v=1780165027"),
    ("Poleron 333 Pink Black Chance", 54990, "/products/polera-333-pink-black-chance", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-333-pink-black-chance-8881108.png?v=1780165027"),
    ("Polera 333 Boxy Black Heavyweight White", 37990, "/products/polera-333-boxy-black-heavyweight-white", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-333-boxy-black-heavyweight-white-7004340.png?v=1780165027"),
    ("Polera 333 Boxy White Heavyweight Black", 37990, "/products/polera-333-boxy-white-heavyweight-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-333-boxy-white-heavyweight-black-1542888.png?v=1780165027"),
    ("Polera 333 Boxy Pink Heavyweight White", 37990, "/products/polera-333-boxy-pink-heavyweight-white", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-333-boxy-pink-heavyweight-white-9393633.png?v=1780165027"),
    ("Polera 333 Boxy Pink Heavyweight Black", 37990, "/products/polera-333-boxy-pink-heavyweight-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-333-boxy-pink-heavyweight-black-5741227.png?v=1780165027"),
    ("Cargo Parachute Grey", 45990, "/products/cargo-parachute-grey", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/cargo-parachute-grey-6596099.jpg?v=1751074387"),
    ("Cargo Parachute Black", 54990, "/products/cargo-parachute-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/cargo-parachute-black-3836249.jpg?v=1751074387"),
    ("Polera Reflex Hard Gvng", 25990, "/products/polera-reflex-hard-gvng", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-reflex-hard-gvng-6436150.jpg?v=1751074265"),
    ("Polera Ak-47 Reflectante", 25990, "/products/polera-ak-47-reflectante", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-ak-47-reflectante-6006899.jpg?v=1751074271"),
    ("Poleron Bloodline Blue Black", 54990, "/products/poleron-bloodline-blue-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-bloodline-blue-black-9104262.jpg?v=1751074385"),
    ("Polera Toyota Supra BG", 25990, "/products/polera-toyota-supra-bg", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-toyota-supra-bg-9361890.jpg?v=1751074333"),
    ("Poleron Bloodline Grey Black", 54990, "/products/poleron-bloodline-grey-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-bloodline-grey-black-2085781.jpg?v=1751074385"),
    ("Polera Scarface Red V2", 25990, "/products/polera-scarface-red-v2", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-scarface-red-v2-9177338.png?v=1770978667"),
    ("Polera The Godfather Corleone", 25990, "/products/polera-the-godfather-corleone", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-the-godfather-corleone-8040608.png?v=1770978668"),
    ("Polera Los Sopranos", 25990, "/products/polera-los-sopranos", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-los-sopranos-1279260.png?v=1770978667"),
    ("Polera Scarface Blue V3", 25990, "/products/polera-scarface-blue-v3", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-scarface-blue-v3-4286586.png?v=1770978668"),
    ("Polera BANG GANG Mafia", 25990, "/products/polera-bang-gang-mafia", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-bang-gang-mafia-5218157.png?v=1770730107"),
    ("Polera BG Except Black", 25990, "/products/polera-bg-except-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-bg-except-black-1707554.jpg?v=1751074335"),
    ("Polera R34 GT-R Black", 25990, "/products/polera-r34-gt-r-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-r34-gt-r-black-3872913.jpg?v=1751074337"),
    ("Polera Butterfly Effect White", 25990, "/products/polera-butterfly-effect-white", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-butterfly-effect-white-3303635.jpg?v=1751074269"),
    ("Polera The Final Sky", 25990, "/products/polera-the-final-sky", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-the-final-sky-6446449.png?v=1759604938"),
    ("Polera Jason FT13 BG", 25990, "/products/polera-jason-ft13-bg", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-jason-ft13-bg-9462975.jpg?v=1751074383"),
    ("Polera Travis Scott", 25990, "/products/polera-travis-scott", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-travis-scott-8950604.jpg?v=1751074334"),
    ("Polera Mac Miller", 25990, "/products/polera-mac-miller", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-mac-miller-4298484.jpg?v=1751074339"),
    ("Polera No Love Just Money", 25990, "/products/polera-no-love-just-money", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-no-love-just-money-8439408.png?v=1759604938"),
    ("Polera Fortune Black", 25990, "/products/polera-fortune-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-fortune-black-5541176.jpg?v=1751074339"),
    ("Polera Post Malone", 25990, "/products/polera-post-malone", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-post-malone-7170256.jpg?v=1751074332"),
    ("Polera Scarface", 25990, "/products/polera-scarface", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-scarface-7946200.jpg?v=1751074337"),
    ("Poleron 333 Red Special", 54990, "/products/poleron-333-red-special", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-333-red-special-6401767.png?v=1751074267"),
    ("Poleron Bloodline Red Black", 54990, "/products/poleron-bloodline-red-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-bloodline-red-black-4339473.jpg?v=1751074270"),
    ("Poleron Shooters Triple White Blue", 54990, "/products/poleron-shooters-triple-white-blue", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-shooters-triple-white-blue-5689749.png?v=1764237486"),
    ("Poleron Shooters Blue Black", 54990, "/products/poleron-shooters-blue-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-shooters-blue-black-7261852.png?v=1764237485"),
    ("Poleron Shooters Pink Black", 54990, "/products/poleron-shooters-pink-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-shooters-pink-black-5392778.png?v=1764237485"),
    ("Poleron Shooters Blue Melange", 54990, "/products/poleron-shooters-blue-melange", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-shooters-blue-melange-4342762.png?v=1764237485"),
    ("Poleron Shooters Pink Melange", 54990, "/products/poleron-shooters-pink-melange", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-shooters-pink-melange-4617303.png?v=1764237485"),
    ("Poleron Shooters Ultra Melange", 54990, "/products/poleron-shooters-ultra-melange", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-shooters-ultra-melange-8850734.png?v=1764237486"),
    ("Poleron Shooters Ultra Pink", 54990, "/products/poleron-shooters-ultra-pink", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-shooters-ultra-pink-5110559.png?v=1764237486"),
    ("Polera Shooters Pink White", 25990, "/products/polera-shooters-pink-white", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-shooters-pink-white-1085399.png?v=1764237486"),
    ("Polera Shooters Blue White", 25990, "/products/polera-shooters-blue-white", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-shooters-blue-white-1300561.png?v=1764237486"),
    ("Polera Shooters Blue Black", 25990, "/products/polera-shooters-blue-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-shooters-blue-black-2627857.png?v=1764237486"),
    ("Polera Shooters Pink Black", 25990, "/products/polera-shooters-pink-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-shooters-pink-black-5389621.png?v=1764237485"),
    ("Poleron Angels Or Visitors", 54990, "/products/poleron-angels-or-visitors", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-angels-or-visitors-2362391.png?v=1759604938"),
    ("Polera Angels Or Visitors", 25990, "/products/polera-angels-or-visitors", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-angels-or-visitors-3506724.png?v=1759604938"),
    ("Poleron Graff BG", 54990, "/products/poleron-no-love-just-money-copia", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-graff-bg-4294303.png?v=1759604938"),
    ("Polera Graff BG", 25990, "/products/polera-graff-bg", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-graff-bg-8799620.png?v=1759604938"),
    ("Poleron No Love Just Money", 54990, "/products/poleron-no-love-just-money", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-no-love-just-money-5147313.png?v=1759604939"),
    ("Polera ESTHER BG", 25990, "/products/polera-esther-bg", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-esther-bg-5288463.png?v=1759604938"),
    ("Poleron ESTHER BG", 54990, "/products/poleron-esther-bg", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-esther-bg-6994508.png?v=1759604938"),
    ("Poleron The Final Sky", 54990, "/products/poleron-the-final-sky", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-the-final-sky-3549067.png?v=1759604938"),
    ("Polera Chuky BG", 25990, "/products/polera-chuky-bg", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-chuky-bg-9557088.jpg?v=1751074336"),
    ("Polera 50 Cent BG", 25990, "/products/polera-50-cent", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-50-cent-bg-28155442.png?v=1751168483"),
    ("Polera Ice Cube BG", 25990, "/products/polera-ice-cube-bg", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-ice-cube-bg-50274641.png?v=1751168484"),
    ("Polera Eminem BG", 25990, "/products/polera-eminem-bg", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-eminem-bg-71552354.png?v=1751168485"),
    ("Polera Drake BG", 25990, "/products/polera-drake-bg", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-drake-bg-88128788.png?v=1751168484"),
    ("Polera 333 White", 25990, "/products/polera-333-white", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-333-white-1819309.jpg?v=1751074272"),
    ("Polera Lights At Night Orange", 25990, "/products/polera-lights-at-night-orange", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-lights-at-night-orange-3757485.png?v=1751074270"),
    ("Polera Loyalty Ultra White", 25990, "/products/polera-loyalty-ultra-white", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-loyalty-ultra-white-8696290.jpg?v=1751074270"),
    ("Polera Loyalty Purple White", 25990, "/products/polera-loyalty-purple-white", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-loyalty-purple-white-7395926.jpg?v=1751074265"),
    ("Polera FM Diamonds Sky Blue Black", 25990, "/products/polera-fm-diamonds-sky-blue-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-fm-diamonds-sky-blue-black-3461030.jpg?v=1751074272"),
    ("Polera Bloodline Grey Black", 25990, "/products/polera-bloodline-grey-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-bloodline-grey-black-4362562.jpg?v=1751074267"),
    ("Polera Fire Angel", 25990, "/products/polera-fire-angel", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-fire-angel-9812332.jpg?v=1751074266"),
    ("Polera The World Is Yours", 25990, "/products/polera-the-world-is-yours", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-the-world-is-yours-7832109.jpg?v=1751074269"),
    ("Polera Butterfly Effect Black", 25990, "/products/polera-butterfly-effect-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-butterfly-effect-black-5171585.jpg?v=1751074269"),
    ("Polera 333 Black", 25990, "/products/polera-333-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-333-black-2493154.jpg?v=1751074268"),
    ("Polera Money In Heaven Black", 25990, "/products/polera-money-in-heaven-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-money-in-heaven-black-1143384.jpg?v=1751074267"),
    ("Polera BG Except White", 25990, "/products/polera-bg-except-white", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-bg-except-white-2488665.jpg?v=1751074332"),
    ("Polera Fortune White", 25990, "/products/polera-fortune-white", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-fortune-white-5161523.jpg?v=1751074334"),
    ("Polera Mustang BG", 25990, "/products/polera-mustang-bg", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-mustang-bg-6603671.jpg?v=1751074334"),
    ("Polera Lights At Night Grey", 25990, "/products/polera-lights-at-night-grey", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-lights-at-night-grey-6220536.jpg?v=1751074336"),
    ("Polera Silence Black", 25990, "/products/polera-silence-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-silence-black-3017420.jpg?v=1751074334"),
    ("Polera Loyalty Yellow Black", 25990, "/products/polera-loyalty-yellow-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-loyalty-yellow-black-4902958.jpg?v=1751074339"),
    ("Polera FM Diamonds Sky Blue White", 25990, "/products/polera-fm-diamonds-sky-blue-white", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-fm-diamonds-sky-blue-white-7067028.jpg?v=1751074333"),
    ("Polera FM Diamonds Green White", 25990, "/products/polera-fm-diamonds-green-white", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-fm-diamonds-green-white-6650053.jpg?v=1751074338"),
    ("Polera FM Diamonds Green Black", 25990, "/products/polera-fm-diamonds-green-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-fm-diamonds-green-black-4632170.jpg?v=1751074340"),
    ("Polera Tribal Engine Black", 25990, "/products/polera-tribal-engine-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-tribal-engine-black-7099128.jpg?v=1751074337"),
    ("Polera Tribal Engine White", 25990, "/products/polera-tribal-engine-white", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-tribal-engine-white-6615905.jpg?v=1751074333"),
    ("Polera Porsche 911 Black", 25990, "/products/polera-porsche-911-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-porsche-911-black-3117846.jpg?v=1751074333"),
    ("Polera Porsche 911 White", 25990, "/products/polera-porsche-911-white", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-porsche-911-white-4016539.jpg?v=1751074340"),
    ("Polera Godzilla Blue", 25990, "/products/polera-godzilla-blue", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-godzilla-blue-7987738.jpg?v=1751074383"),
    ("Polera Godzilla Red", 25990, "/products/polera-godzilla-red", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-godzilla-red-7397873.jpg?v=1751074384"),
    ("Poleron 333 Dollars Black", 54990, "/products/poleron-333-dollars-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/poleron-333-dollars-black-4213344.jpg?v=1751074384"),
    ("Polera Bloodline Red Black", 25990, "/products/polera-bloodline-red-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-bloodline-red-black-9171398.jpg?v=1751074385"),
    ("Polera Bloodline Blue Black", 25990, "/products/polera-bloodline-blue-black", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-bloodline-blue-black-7381650.jpg?v=1751074384"),
    ("Polera Bloodline Blue White", 25990, "/products/polera-bloodline-blue-white", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-bloodline-blue-white-9953960.jpg?v=1751074383"),
    ("Polera Bloodline Red White", 25990, "/products/polera-bloodline-red-white", "https://cdn.shopify.com/s/files/1/0936/9105/2327/files/polera-bloodline-red-white-2881589.jpg?v=1751074383"),
]

# 2026-08-23 -- tienda nueva desde el Excel (fila "UNK Chile"). Sitio real
# confirmado (Shopify), extraido via products.json. Excluidos: "Test"
# (producto de prueba, $400), items con precio $0, gorros/beanies/snapback/
# dadhats (sin categoria de gorro con visera soportada), bolsos/mochilas,
# y los "...Kids..." (ropa de nino, la app no maneja tallas infantiles).
UNKCHILE = [
    ("Hoodie Unk. Acid Blue", 40550, "/products/hoodie-unk-acid-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/HoodieUnk.AcidBlue.webp?v=1734013637"),
    ("Jogger Cargo UNK. Acid Yellow", 40090, "/products/jogger-cargo-unk-acid-yellow", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/JoggerCargoUnk.AcidYellow.webp?v=1734013176"),
    ("Jogger Cargo Unk. Acid Black", 40090, "/products/pantalon-unk-cargo-pro-black", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/JoggerCargoUnk.AcidBlack.webp?v=1734012916"),
    ("Polera UNK. Infinity Black", 18550, "/products/polera-unk-clean-black", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/PoleraUNK.CleanBlack.webp?v=1733836169"),
    ("Polera UNK. Infinity Verde Amarelo", 20550, "/products/polera-unk-verde-amarelo", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/PoleraUNK.VerdeAmarelo.webp?v=1733835147"),
    ("Polera UNK. Infinity Sweet Lilac", 20550, "/products/polera-unk-sweet-lilac", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/PoleraUNK.SweetLilac.webp?v=1733853473"),
    ("Polera Unk. Infinity Greensky", 20550, "/products/polera-unk-greensky", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/PoleraUnk.Greensky.webp?v=1733833958"),
    ("Polera Unk. Infinity Shine White", 18550, "/products/polera-unk-shine-white", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/PoleraUnk.ShineWhite.webp?v=1733777855"),
    ("Hoodie Unk. Acid Beige", 40550, "/products/hoodie-unk-strong-beige", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/HoodieUnk.StrongBeige.webp?v=1733776560"),
    ("Hoodie Unk. Acid Pink", 40550, "/products/hoodie-unk-true-pink", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/HoodieUnk.TruePink.webp?v=1733776034"),
    ("Hoodie Unk. Acid Green", 40090, "/products/hoodie-unk-green-forest", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/HoodieUnk.AcidGreen.webp?v=1734013772"),
    ("Hoodie Unk. Acid Black", 40090, "/products/hoodie-unk-black-undermined", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/HoodieUnk.BlackUndermined.webp?v=1733775152"),
    ("Jacket Cortaviento Carbon Color Print", 46550, "/products/jacket-carbon-color-print", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/JacketCarbonColorPrint.webp?v=1733774263"),
    ("Jacket Cortaviento Blue Snow", 46550, "/products/jacket-unk-blue-snow", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/JacketUnk.BlueSnow.webp?v=1733773552"),
    ("Jacket Cortaviento Sky Blue", 50550, "/products/jacket-unk-sky-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/JacketUnk.SkyBlue.webp?v=1733773206"),
    ("Jacket Cortaviento Crema Color Print", 50550, "/products/jacket-unk-crema-color-print", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/JacketUnk.CremaColorPrintback.webp?v=1733772326"),
    ("Hoodie UNK. Smile Pink", 36990, "/products/hoodie-unk-smile-pink", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Hoodie_UNK._Smile_Pink.webp?v=1733756332"),
    ("Polera Unk. New Plane Steel Green", 7990, "/products/polera-unk-new-plane-steel-green", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/IMG_7384.webp?v=1724130368"),
    ("Jogger Unk. Generation Black", 24990, "/products/jogger-unk-generation-black", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/IMG_7369-1.jpg?v=1724130310"),
    ("Hoodie Camaleón Safary Green", 36990, "/products/hoodie-camaleon-safary-green", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Hoodie_Camaleon_Safary_Green.webp?v=1733746999"),
    ("Polera UNK. Spiral White", 18990, "/products/polera-unk-spiral-white", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera_UNK._Spiral_White_9d8a4519-6ed0-42b3-b7b4-b6c4d2cfe76d.webp?v=1734448599"),
    ("Polera UNK. Pastel White", 18990, "/products/polera-unk-pastel-white", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera_UNK._Pastel_White_372c9c40-0303-4dd8-873f-778b8d2931a2.webp?v=1734449136"),
    ("Polera UNK. Head Pro Black", 17990, "/products/polera-unk-head-pro-black", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera-UNK.-Head-Pro-Black.webp?v=1724130261"),
    ("Polera UNK. Pastel Black", 18990, "/products/polera-unk-pastel-black", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera-UNK.-Pastel-Black.webp?v=1724130251"),
    ("Polera UNK. Head Pro Light Blue", 17990, "/products/polera-unk-head-pro-light-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera_UNK._Head_Pro_Light_Blue_e8fd4294-ad36-4e86-bf4d-4f1f742aeaaa.webp?v=1734957809"),
    ("Polera Camaleón Army White", 17990, "/products/polera-camaleon-army-white", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera-Camaleon-Army-White2.webp?v=1724130175"),
    ("Polera UNK. Future Green", 7990, "/products/polera-unk-future-green", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/IMG_1427.webp?v=1724129971"),
    ("Polera Unk. Skate Large White", 18990, "/products/polera-unk-skate-large-white", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera_Unk._Skate_Large_White_7419696b-ace5-46fd-818a-63bfbb65dd4c.webp?v=1734449614"),
    ("Polera Unk. Skate Large Black", 18990, "/products/polera-unk-skate-large-black", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera-Unk.-Skate-Large-Black.webp?v=1724129925"),
    ("Polera Unk. Peace Black", 17990, "/products/polera-unk-peace-black", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera_Unk._Peace_Black_63eb33c7-81c7-48de-b6e6-535db50a5818.webp?v=1734449917"),
    ("Polera Unk. Peace Orange", 17990, "/products/polera-unk-peace-orange", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera_Unk._Peace_Orange_1a6db7c6-f4af-49a7-bf45-b36809e1fffa.webp?v=1734448989"),
    ("Polera Unk. Hero Peach", 17990, "/products/polera-unk-hero-peach", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera-Unk.-Hero-Peach_0ff387f9-8f9f-4295-9be2-fc95e0eeb3f0.webp?v=1738849644"),
    ("Polera Unk. Hero Lilac", 17990, "/products/polera-unk-hero-lilac", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera_Unk._Hero_Lilac.webp?v=1734957893"),
    ("Polera Unk. Large Rainbow Pink", 18990, "/products/polera-unk-large-rainbow-pink", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera-Unk.-Large-Rainbow-Pink.webp?v=1724129865"),
    ("Polera Unk. Large Rainbow Blue", 18990, "/products/polera-unk-large-rainbow-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera_Unk._Large_Rainbow_Blue_59ba3801-0a69-4db5-b295-4ea20c435f80.webp?v=1734449794"),
    ("Polerón Camaleón Skate Black", 36990, "/products/poleron-camaleon-skate-black", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Poleron_Camaleon_Skate_Black.webp?v=1733508521"),
    ("Polerón Camaleón Skate White", 36990, "/products/poleron-camaleon-skate-white", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Poleron_Camaleon_Skate_White.webp?v=1733501240"),
    ("Polerón Unk. Black & White", 38990, "/products/poleron-unk-black-white", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Poleron_Unk._Black_White.webp?v=1733498015"),
    ("Polerón Unk. Focus Colors", 37990, "/products/poleron-unk-focus-colors", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Poleron-Unk.-Focus-Colors.webp?v=1724129818"),
    ("Polerón Unk. Focus Orange", 37990, "/products/poleron-unk-focus-orange", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Poleron_Unk._Focus_Orange_back.webp?v=1733512554"),
    ("Jacket Unk. Peak Pink", 47990, "/products/jacket-unk-peak-pink", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Cortaviento-Peak-Pink.webp?v=1724129741"),
    ("Jacket Unk. Peak Orange", 47990, "/products/jacket-unk-peak-orange", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Jacket_Unk._Peak_Orange.webp?v=1733501476"),
    ("Polar Hoodie UNK. Blue", 34990, "/products/polar-hoodie-unk-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_2889.webp?v=1724129675"),
    ("Polar Hoodie UNK. Black", 34990, "/products/polar-hoodie-unk-black", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polar_Hoodie_UNK._Black.webp?v=1733512343"),
    ("Jacket Unk. Mountain Blue", 52990, "/products/jacket-unk-mountain-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Jacket_Unk._Mountain_Blue.webp?v=1733507745"),
    ("Polera UNK. Premium Burgundy", 17990, "/products/polera-unk-premium-burgundy", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_2653.webp?v=1724129575"),
    ("Polera UNK. Tie Dye Duo Mint", 7990, "/products/polera-unk-tie-dye-duo-mint", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC08125.jpg?v=1724129565"),
    ("Polera Camaleón Tie Dye Blue", 16990, "/products/polera-camaleon-tie-dye-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_2629.webp?v=1724129554"),
    ("Jacket Unk. Mountain Brown", 52990, "/products/jacket-unk-mountain-brown", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Jacket_Unk._Mountain_Brown.webp?v=1733508776"),
    ("Polera Camaleón Tie Dye Burgundy", 17990, "/products/polera-camaleon-tie-dye-burgundy", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_2624.webp?v=1724129521"),
    ("Polera Tie dye World Blue", 6990, "/products/polera-tie-dye-world-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/foto-1-100.jpg?v=1724129491"),
    ("Polera Unk. Skate Light Blue", 6990, "/products/polera-unk-skate-light-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/foto-1-40.webp?v=1724129481"),
    ("Hoodie UNK. Tie Dye Jade", 35990, "/products/hoodie-unk-tie-dye-jade", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_2923.webp?v=1724129468"),
    ("Hoodie UNK. Original White", 32990, "/products/hoodie-unk-original-white", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Hoodie_UNK._Original_White.webp?v=1733747366"),
    ("Hoodie UNK. Original Calypso", 32990, "/products/hoodie-unk-original-calypso", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Hoodie_UNK._Original_Calypso.webp?v=1733747525"),
    ("Jacket Cortaviento UNK. 4k Colors", 47990, "/products/jacket-cortaviento-unk-4k-colors", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/IMG_7522.webp?v=1724129417"),
    ("Jacket Cortaviento UNK. 4K Black", 45990, "/products/jacket-cortaviento-unk-4k-black", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_3016.webp?v=1724129397"),
    ("Jogger UNK. Euro Gray", 25990, "/products/jogger-unk-euro-gray", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Jogger_UNK._Euro_Gray_9f9f9142-ba42-4a81-afc9-bd8816ee8038.webp?v=1734450983"),
    ("Jogger UNK. Euro Calypso", 25990, "/products/jogger-unk-euro-calypso", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_3091.webp?v=1724129368"),
    ("Jacket Cortaviendo unk. 4K Blue", 47990, "/products/jacket-cortaviendo-unk-4k-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/IMG_7516.jpg?v=1724129355"),
    ("Jacket Cortaviento Unk. Crack Gray", 46990, "/products/jacket-cortaviento-unk-crack-gray", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/IMG_7487.webp?v=1724129330"),
    ("Jacket Cortaviento Unk. Rainbow Blue", 49990, "/products/jacket-cortaviento-unk-rainbow-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Jacket_Cortaviento_Unk._Rainbow_Blue.webp?v=1733509227"),
    ("Polera Unk. Skate Pink", 6990, "/products/polera-unk-skate-pink", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/foto-1-37.webp?v=1724129294"),
    ("Jogger Unk. Green", 19990, "/products/jogger-unk-green", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/IMG_7443.jpg?v=1724129264"),
    ("Hoodie Block White", 19990, "/products/hoodie-block-white", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/foto-1-1551.jpg?v=1724129253"),
    ("Jacket Cortaviento Unk. Rainbow Pink", 49990, "/products/jacket-cortaviento-unk-rainbow-pink", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/IMG_7500.webp?v=1724129208"),
    ("Jacket Cortaviento Monster Blue", 46990, "/products/jacket-cortaviento-monster-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Jacket_Cortaviento_Monster_Blue.webp?v=1733748727"),
    ("Jacket Cortaviento Monster White", 46990, "/products/jacket-cortaviento-monster-white", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Jacket_Cortaviento_Monster_White.webp?v=1733509750"),
    ("Hoodie Unk. Spiral Mint", 36990, "/products/hoodie-unk-spiral-mint", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/IMG_7821.jpg?v=1724129168"),
    ("Jacket Cortaviento UNK. Wire White", 46990, "/products/jacket-cortaviento-unk-wire-white", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_3079.webp?v=1724129155"),
    ("Jogger Unk. Dark", 17990, "/products/jogger-unk-dark", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Jogger-UNK.-Dark-1.jpg?v=1724129145"),
    ("Hoodie Unk. Spiral Blue", 36990, "/products/hoodie-unk-spiral-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/IMG_7431.webp?v=1724129106"),
    ("Hoodie Unk. Old Brown", 35990, "/products/hoodie-unk-old-brown", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/IMG_7462.jpg?v=1724129096"),
    ("Hoodie Unk. Old Black", 35990, "/products/hoodie-unk-old-black", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Hoodie_Unk._Old_Black.webp?v=1733511311"),
    ("Polera UNK. Pocket Pink", 6990, "/products/polera-unk-pocket-pink", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera_UNK._Pocket_Pink.webp?v=1733764342"),
    ("Polera UNK. Pocket Light Blue", 6990, "/products/polera-unk-pocket-light-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera_UNK._Pocket_Light_Blue.webp?v=1733747845"),
    ("Polera UNK. Summer Mint", 6990, "/products/polera-unk-summer-mint", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera_UNK._Summer_Mint.webp?v=1733749386"),
    ("Hoodie UNK. Smile Mint", 36990, "/products/hoodie-unk-smile-mint", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Hoodie_UNK._Smile_Mint.webp?v=1733500551"),
    ("Polera Unk. Marley Red", 16990, "/products/polera-unk-marley-red", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_6671-scaled-1.webp?v=1724128587"),
    ("Jacket Cortaviento Camaleón Head Blue", 29990, "/products/jacket-cortaviento-camaleon-head-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_6925-scaled-1.webp?v=1724128566"),
    ("Jacket Cortaviento Camaleón Head Black", 46990, "/products/jacket-cortaviento-camaleon-head-black", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_6909-1-scaled-1.webp?v=1724128554"),
    ("Jacket Cortaviento Unk. Snowflake White", 46990, "/products/jacket-cortaviento-unk-snowflake-white", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_69463.jpg?v=1724128530"),
    ("Jacket Cortaviento Unk. Noodles Pink", 46990, "/products/jacket-cortaviento-unk-noodles-pink", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_6998-scaled-1.webp?v=1724128520"),
    ("Jacket Cortaviento Unk. Noodles Tiffany", 46990, "/products/jacket-cortaviento-unk-noodles-tiffany", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_6971-scaled-1.webp?v=1724128509"),
    ("Jacket Cortaviento Unk. Fall Calypso", 46990, "/products/jacket-cortaviento-unk-fall-calypso", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_6887-scaled-1.webp?v=1724128487"),
    ("Hoodie Unk. Peace Steel", 32990, "/products/hoodie-unk-peace-steel", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_6784-scaled-1.webp?v=1724128476"),
    ("Short Unk. Tiger Gray", 14990, "/products/short-unk-tiger-gray", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Short-unk.-tiger-gray2-scaled-1.webp?v=1724128454"),
    ("Short Unk. Tiger Blue", 14990, "/products/short-unk-tiger-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Short_Unk._Tiger_Blue.webp?v=1733517588"),
    ("Polera Camaleón Dynamic Turquoise", 17990, "/products/polera-camaleon-dynamic-turquoise", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Dynamic-Turquoise.webp?v=1724128419"),
    ("Polera Camaleón Dynamic Coral", 17990, "/products/polera-camaleon-dynamic-coral", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera_Camaleon_Dynamic_Coral_4febc7ec-9274-4951-91f9-82af54efc123.webp?v=1734449360"),
    ("Polera Camaleón Crazy Black", 16990, "/products/polera-camaleon-crazy-black", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Camaleon-Crazy-Black.webp?v=1724128395"),
    ("Polera Camaleón Crazy Oil Blue", 16990, "/products/polera-camaleon-crazy-oil-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Camaleon-Crazy-Oil-Blue.webp?v=1724128384"),
    ("Polerón Unk. Cubox Fluor", 32990, "/products/poleron-unk-cubox-fluor", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Poleron_Unk._Cubox_Fluor.webp?v=1733505881"),
    ("Polerón Unk. Cubox Lilac", 32990, "/products/poleron-unk-cubox-lilac", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Poleron_Unk._Cubox_Lilac_e9b5b649-4ab1-434c-875a-fa0fd891c96c.webp?v=1734450326"),
    ("Jogger Unk. Rainbow Pink", 26990, "/products/jogger-unk-rainbow-pink", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Jogger_Unk._Rainbow_Pink_36721de0-1c75-4ae2-9f26-b4a15fef2ed1.webp?v=1734451105"),
    ("Jogger Unk. Rainbow blue", 26990, "/products/jogger-unk-rainbow-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Jogger-Rainbow-Blue.webp?v=1724128341"),
    ("Polera Kmaleón Tie Dye Pink", 6990, "/products/polera-kmaleon-tie-dye-pink", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/image00057-scaled-1.jpg?v=1724128325"),
    ("Joggers Unk. Generation Blue", 24990, "/products/joggers-unk-generation-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Joggers-Unk.-Generation-Blue.webp?v=1724128146"),
    ("Hoodie Unk. Level Orange", 19990, "/products/hoodie-unk-level-orange", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/foto-1-145.webp?v=1724127495"),
    ("Polera UNK. Tie Dye Duo Steel", 7990, "/products/polera-unk-tie-dye-duo-steel", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC07973-2.jpg?v=1724127471"),
    ("Polera UNK. Plane Blue", 6990, "/products/polera-unk-plane-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_2523.webp?v=1724127460"),
    ("Polera UNK. Spiral Black", 18990, "/products/polera-unk-spiral-black", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/Polera_UNK._Spiral_Black_0d23d7fc-9c6d-4618-98b1-619d1c263a77.webp?v=1734450119"),
    ("Hoodie Camaleón Safary Blue", 36990, "/products/hoodie-camaleon-safary-blue", "https://cdn.shopify.com/s/files/1/0642/2590/2731/files/DSC_6808.jpg?v=1724127388"),
]

# 2026-08-23 -- tienda nueva desde el Excel (fila "Doslobos", 133k
# seguidores). Sitio real confirmado (Shopify), catalogo muy grande (373
# productos totales via products.json en 2 paginas) -- solo se cargaron
# las categorias de ropa (Hoodie/Poleras/Pantalon/Chaquetas/Sweater),
# excluidos Bolsos (77), bufandas (8), Gorro (22, mismo motivo que otras
# tiendas -- sin categoria de gorro con visera/forma soportada) y falda (1,
# muy poca info para tagear sola). "METAL GRAY/BLACK PANTS" estaban mal
# etiquetados como tipo "Hoodie" en la tienda -- corregido a pantalon aca.
DOSLOBOS = [
    ("NITIDO long sleeve", 39990, "/products/nitido-long-sleeve", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG_7667_36355636-8b4f-4070-b2e1-c670b60cd104.jpg?v=1785540115"),
    ("WOLVES emblem tee", 39990, "/products/wolves-washed-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG_7873.jpg?v=1785540409"),
    ("LOGO black tee", 39990, "/products/wolves-emblem-tee-copia", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG_7724.jpg?v=1785540314"),
    ("NITIDO vibe hoodie", 64990, "/products/nitido-vibe-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG_7792_1225e4f7-a63e-409c-be62-5c8c611865c2.jpg?v=1785552880"),
    ("LOGO dark hoodie", 64990, "/products/logo-dark-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG_7760.jpg?v=1785554117"),
    ("WASHED long sleeve", 39990, "/products/washed-long-sleeve", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG_7835_copia.jpg?v=1785539275"),
    ("LOBO plaid shirt", 49990, "/products/nitido-long-sleeve-1", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG_7631.jpg?v=1785557261"),
    ("RESILIO plaid shirt", 49990, "/products/resilio-plaid-shirt", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG_7655_84f94033-24b2-487a-af62-978988acc880.jpg?v=1785559125"),
    ("BIG LOGO RAW SWEATER", 55000, "/products/big-logo-raw-sweater", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/F5FED20B-1DB4-4553-9B16-79BFD4C2DB0A.jpg?v=1784082715"),
    ("BIG LOGO BLACK SWEATER", 55000, "/products/big-logo-black-sweater", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/680300F0-FF38-43B1-AD97-18D9DA5BA66B.jpg?v=1784082638"),
    ("+ TIME 4 LOVE SWEATER", 55000, "/products/more-4-love-sweater", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/DOSLOBOSCATALOGO45.jpg?v=1780440169"),
    ("SUEDE VAQUERA-JACKET", 75000, "/products/suede-vaquera-jacket-2", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/DOSLOBOSCATALOGO53_9abfe2ee-1154-438d-8e6b-50912efe083e.jpg?v=1780466579"),
    ("FEAR BLACK HOODIE", 65000, "/products/sin-miedo-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/DOSLOBOSCATALOGO57_53098d4e-ba23-4b27-9775-8a551ad5e168.jpg?v=1780439944"),
    ("SAINTWOLF HOODIE", 55000, "/products/metal-black-hoodie-copia", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/DOSLOBOSCATALOGO61.jpg?v=1780457632"),
    ("SAINT WOLF TEE", 35000, "/products/saintwolf-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/DOSLOBOSCATALOGO28.jpg?v=1780439076"),
    ("+ TIME 4 LOVE TEE", 35000, "/products/more-4-love-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/DOSLOBOSCATALOGO21.jpg?v=1780439013"),
    ("METAL GRAY HOODIE", 60000, "/products/metal-gray-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/DOSLOBOSCATALOGO13.jpg?v=1780438600"),
    ("METAL GRAY PANTS", 45000, "/products/metal-gray-pants", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/DOSLOBOSCATALOGO137.jpg?v=1780457500"),
    ("METAL BLACK PANTS", 45000, "/products/metal-black-pants", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/DOSLOBOSCATALOGO100_85da161f-178b-4725-9da8-d22174884e66.jpg?v=1780457376"),
    ("METAL BLACK HOODIE", 75000, "/products/metal-black-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/DOSLOBOSCATALOGO8.jpg?v=1780438384"),
    ("ESFINGE CATS HOODIE", 60000, "/products/cats-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/DOSLOBOSCATALOGO66.jpg?v=1780457749"),
    ("ESFINGE CATS TEE", 35000, "/products/esfinge-pink-cats-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/DOSLOBOSCATALOGO23_b1fd31e8-2b40-4a4c-b5f9-41b4be782e5c.jpg?v=1780458041"),
    ("3D CHROME HOODIE", 60000, "/products/3d-chrome-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/BA30B05B-05B9-409B-8A72-9967EBCC65CE.jpg?v=1775323090"),
    ("DSLS JAPO TEE", 25000, "/products/dsls-japo-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/3BA84A16-8B1F-4E00-B7B1-548628DD090E.jpg?v=1775322346"),
    ("MANADA TOUR HOODIE", 50000, "/products/manada-tour-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/E3126EAB-86AA-4A6E-A922-D85FBBD5BE67.jpg?v=1773111644"),
    ("MANADA TOUR BLACK TEE", 35000, "/products/manada-tour-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/4969.jpg?v=1768534136"),
    ("MANADA TOUR WHITE TEE", 35000, "/products/manada-tour-white-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/499_a682e8db-9437-4c7e-99f9-3ffe5286b1ab.jpg?v=1768533813"),
    ("BLACK MINIMAL TEE", 30000, "/products/black-minimal-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/827504F4-2AC6-48D5-A996-EAFCB4B0F788.jpg?v=1766704348"),
    ("BIG LOGO MINT SWEATER", 55000, "/products/big-logo-mint-sweater", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG-7013.png?v=1766703936"),
    ("BLACK WOLF PANTS", 42000, "/products/black-pants", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/510_c61b504c-2922-4797-bf08-cf5a0f3bcd29.jpg?v=1764483086"),
    ("LIGHT BLUE JORT", 40000, "/products/light-blue-jort", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/491.jpg?v=1764482481"),
    ("METAL BLACK JORT", 45000, "/products/metal-black-jort-copia", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/500.jpg?v=1764486549"),
    ("CAMO GRAY JORT", 40000, "/products/camo-gray-jort", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/497_55bcc0e5-dedf-4828-a8dd-d0e9f568d9a7.jpg?v=1764482607"),
    ("ICE BLUE PANTS", 48000, "/products/light-blue-pants", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/561.jpg?v=1764486024"),
    ("CAMO GRAY PANTS", 48000, "/products/camo-gray-pants", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/505.jpg?v=1764482993"),
    ("BIG LOGO PINK SWEATER", 55000, "/products/big-logo-pink-sweater-1", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/520_d1fd74ed-55fb-4894-8644-71834f146ddb.jpg?v=1764483495"),
    ("BIG LOGO GRAY SWEATER", 55000, "/products/big-logo-gray-sweater-copia-1", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/519.jpg?v=1764483422"),
    ("ANNIVERSARY 10 JAPO-TEE", 30000, "/products/gray-japo-tee-copia", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/523.jpg?v=1764483556"),
    ("ESFINGE PINK CATS TEE", 30000, "/products/pink-cats-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/539.jpg?v=1764484403"),
    ("BLACK LOGO 3D TEE", 40000, "/products/black-logo-3d-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/502.jpg?v=1764488743"),
    ("METAL CROMO BLACK HOODIE", 70000, "/products/black-ojetillo-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/553.jpg?v=1764485375"),
    ("ACABÉ TRIUNFANDO HOODIE", 60000, "/products/3d-chrome-logo-hoodie-copia-1", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/550.jpg?v=1764485353"),
    ("ESFINGE PINK CATS HOODIE", 65000, "/products/cats-black-hoodie-copia", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/558.jpg?v=1764485515"),
    ("ANNIVERSARY 10 CAMISETA", 30000, "/products/camiseta-10", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/514.jpg?v=1764483329"),
    ("CAMO 10TH BOMBER-JACKET", 80000, "/products/camo-bomber-jacket", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/488.jpg?v=1764482446"),
    ("BLACK 10TH VARSITY-JACKET", 120000, "/products/black-varsity-jacket", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/485.jpg?v=1764482408"),
    ("DENIM SKULL JORT", 36990, "/products/denim-skull-jort", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/10529AF6-C9C8-48C0-923C-E60F08669C40.jpg?v=1760206020"),
    ("DENIM RAPPORT JORT", 38000, "/products/denim-rapport-jort", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/63.jpg?v=1760206051"),
    ("SKULL HOODIE", 30000, "/products/skull-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/166_571c7294-eff3-4229-b561-fbe514522244.jpg?v=1759556900"),
    ("GRITA Y EXHALE HOODIE", 55000, "/products/strass-black-hoodie-2", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/377_3b9c5775-8d16-4d2d-98b5-f55c088719ac.jpg?v=1760216973"),
    ("GRITA & EXHALE TEE", 25000, "/products/grita-exhale-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/339_32c9d862-d87b-494f-a08a-28e4fea43ee0.jpg?v=1761449152"),
    ("BLUE SKULL TEE", 25000, "/products/blue-skull-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/71_42559ad5-d4f6-49c8-81ef-24c104d5a26a.jpg?v=1759551115"),
    ("SUEDE VAQUERA-JACKET", 75000, "/products/suede-vaquera-jacket-1", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/370_b4b3f514-9840-4b25-8935-def98413f713.jpg?v=1759668837"),
    ("TIGER PANTS MEN", 47000, "/products/tiger-pants-men", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/4870C5C3-4EC6-4A43-B3F2-A4CB293B1DE6.jpg?v=1748276651"),
    ("STRASS BLUE TEE", 30000, "/products/stras-blue-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/358_0353c5d3-c863-4a1c-9fc4-91a268b210fb.jpg?v=1752466323"),
    ("STRASS BLACK TEE", 30000, "/products/stras-black-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/361_5a71518d-793e-44b9-ac26-0ef1e8373cbd.jpg?v=1752466331"),
    ("WOLVES CROME VARSITY-JACKET", 95000, "/products/remaches-varsity-jacket", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/345_2a80b429-12bb-4a9c-94a3-852abbd6fd42.jpg?v=1752465693"),
    ("SUEDE VAQUERA-JACKET", 85000, "/products/suede-vaquera-jacket", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/370_b4b3f514-9840-4b25-8935-def98413f713.jpg?v=1759668837"),
    ("TOTAL BLACK VARSITY-JACKET", 85000, "/products/total-black-varsity-jacket", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Facetune_14-07-2025-00-39-23.jpg?v=1752469053"),
    ("MANADA VARSITY-JACKET", 85000, "/products/white-logo-varsity-jacket", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/344_ad5deea6-0e16-4a90-8483-d4cd6105e5eb.jpg?v=1752465858"),
    ("STRASS BLUE HOODIE", 55000, "/products/strass-blue-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/381.jpg?v=1755831951"),
    ("STRASS BLACK HOODIE", 55000, "/products/strass-blue-hoodie-copia", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/376.jpg?v=1755831942"),
    ("KRYPTA TEE", 20000, "/products/krypta-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/353_7d3d8ef2-c1da-4a12-b846-8301cf8d46db.jpg?v=1756508784"),
    ("KRYPTA HOODIE", 30000, "/products/krypta-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/383.jpg?v=1756506631"),
    ("GRITA & EXHALE TEE", 30000, "/products/grita-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/339_32c9d862-d87b-494f-a08a-28e4fea43ee0.jpg?v=1761449152"),
    ("BLVCK LOGO TEE", 25000, "/products/maria-flame-tee-copia", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/334_1b58b028-c6fd-41c1-a298-85acc9cccc4f.jpg?v=1752466383"),
    ("SKULL DARK PANTS", 35000, "/products/tiger-pants-copia", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/329.jpg?v=1752471704"),
    ("SKULL SWEATER", 30000, "/products/exhale-blue-sweater-copia", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/337_d7654dbd-7af6-4fcb-ab02-10442fc09430.jpg?v=1752469418"),
    ("DETHKID BABY-TEE", 25000, "/products/dethkid-baby-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/351_5806a8eb-421b-4788-8b3a-f598a6f875c6.jpg?v=1752466443"),
    ("DETHKID HOODIE", 55000, "/products/dethkid-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/378_ec8e8b70-17a2-42ee-a657-e09700a88e25.jpg?v=1752469274"),
    ("DETHKID TEE", 30000, "/products/dethkid-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/332_f057d9a9-62e1-4000-9a2a-ba31b4c0b044.jpg?v=1752466102"),
    ("DEHTKID BOMBER-JACKET", 80000, "/products/dehtkid-bomber-jacket", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/362_fe71736a-705d-419a-a5f8-62381282f7fe.jpg?v=1752465929"),
    ("EXHALE BLUE SWEATER.", 55000, "/products/exhale-blue-sweater", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/99.jpg?v=1746307133"),
    ("BLUE SKULL TEE", 27000, "/products/blie-skull-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/71_42559ad5-d4f6-49c8-81ef-24c104d5a26a.jpg?v=1759551115"),
    ("MANADA STONE TEE", 30000, "/products/manada-stone-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/12_c91fc4b8-da85-4063-8696-b19ab0fdfcac.jpg?v=1746263410"),
    ("BLACK CORE TEE", 27000, "/products/black-core-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/62.jpg?v=1746262466"),
    ("CAPUCHA BLACK GILETTE", 48000, "/products/capucha-black-gillette", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/85_6dd9508a-c1ba-4dfb-a624-11aeeae85174.jpg?v=1746262023"),
    ("TIGER BOMBER-JACKET", 44000, "/products/tiger-bomber-jacket", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/80_81e15bb4-7fe2-49df-b266-d071ab923e40.jpg?v=1746261790"),
    ("TIGER PANTS", 47000, "/products/tiger-woman-pants", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/104.jpg?v=1747457257"),
    ("BLACK RIVET FLARE-PANTS", 45000, "/products/gray-rivet-flare-pants", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/BC799E17-FE11-42DD-9DC4-82460907E182.jpg?v=1756507762"),
    ("GRAY TIGER CARDIGÁN", 55000, "/products/gray-tiger-cardigan", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/108.jpg?v=1746307151"),
    ("EXHALE BLUE SWEATER", 55000, "/products/exhlae-blue-sweater", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/99.jpg?v=1746307133"),
    ("MANADA STONE HOODIE", 60000, "/products/manada-stone-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/96_b2e0e3dd-c39f-41aa-bb1f-c05e2d9733c2.jpg?v=1746307650"),
    ("BLACK VAQUERA-JACKET", 80000, "/products/black-vaquera-jacket", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/72_f52a96bc-8447-47dd-a635-4a68ff7db861.jpg?v=1746253149"),
    ("CORE BLACK HOODIE", 55000, "/products/faith-love-hoodie-copia", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/93_0e120eef-79be-49c5-abe1-2d8d35a6a215.jpg?v=1746307360"),
    ("I LOVE DSLS TEE", 30000, "/products/i-love-dsls-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/68_f2d92dfe-8641-49c0-9466-6f55c6293864.jpg?v=1746262998"),
    ("GRAY JAPO-TEE", 27000, "/products/gray-logo-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/10_d0c26f9a-c1af-4d62-bc21-457b0e4eb7b4.jpg?v=1746261002"),
    ("VARSITY JACKET 09", 70000, "/products/varsity-jacket-09", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG-0607.jpg?v=1744910027"),
    ("CAMO GREEN PANTS MEN", 42000, "/products/camo-carpintero-pants", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/356.jpg?v=1728860458"),
    ("CAMO GREEN PANTS GIRL", 45000, "/products/camo-cargo-pants-copia", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/366.jpg?v=1728860317"),
    ("CAMO GRAY PANTS GIRL", 42000, "/products/camo-cargo-gray-pants", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/343.jpg?v=1728860244"),
    ("CAMO GRAY PANTS MEN", 28000, "/products/camo-carpintero-gray-pants", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/336.jpg?v=1728860531"),
    ("BOXY TEE NEGRA", 25000, "/products/boxy-tee-negra", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/307.jpg?v=1728860758"),
    ("HOODIE CAMO STRASS", 55000, "/products/hoodie-camo-strass", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/354.jpg?v=1728861167"),
    ("SWEATER CARDIGÁN 09", 50000, "/products/sweater-cardigan-99", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/330.jpg?v=1728878509"),
    ("BOXY TEE NEGRA // NocityLimits", 25000, "/products/boxy-tee-negra-nocitylimits", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/14copia.jpg?v=1738273351"),
    ("Faith&Love HOODIE", 50000, "/products/poleron-fe-y-amor", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/03_2fc39ece-ecb2-46d0-8296-39c4c53d2c61.jpg?v=1734591520"),
    ("María flame TEE", 25000, "/products/polera-virgen", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/14_085dade8-2c76-4b4a-b680-52cd302b4763.jpg?v=1734998571"),
    ("Faith&Love TEE", 25000, "/products/polera-fe-y-amor", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/28_f0a1b8e3-6fe9-437a-bd75-111867e4b107.jpg?v=1734590345"),
    ("Love-strong TEE", 25000, "/products/polera-moto", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/12.jpg?v=1734591734"),
    ("Wolf-graffiti TEE", 25000, "/products/polera-lobo", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/23.jpg?v=1734591627"),
    ("Rosary TEE", 25000, "/products/polera-rosario", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/04_b56961c5-78ff-4683-9bff-6618d3f437fa.jpg?v=1734591818"),
    ("Dsls-cromo TEE", 25000, "/products/polera-dsls-cromo", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/31_a31321c4-35a4-4485-bf30-f71f96786b1c.jpg?v=1734591876"),
    ("Wolf graffiti CREWNECK", 45000, "/products/crewneck-lobo", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/24_1155ec0f-c3ea-4af3-8128-f179cb81777a.jpg?v=1734591924"),
    ("María flame HOODIE", 55000, "/products/hoodie-virgen-1", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/26_e80b7684-deb4-4755-96af-dc91d0b523e6.jpg?v=1734592025"),
    ("HOODIE VIRGEN", 55000, "/products/hoodie-virgen", ""),
    ("Embroidery PANTS", 42000, "/products/pantalon-logo-bolsillo-1", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/06.jpg?v=1734592232"),
    ("Denim-rapport JACKET", 60000, "/products/chaqueta-rapport", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/18_b8119dc9-70a8-443f-927f-aa121d16c7ed.jpg?v=1734592764"),
    ("Denim-rapport PANTS", 45000, "/products/pantalon-rapport", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/18_540da216-a952-4ec7-92d0-72727987ac5c.jpg?v=1734592845"),
    ("Denim-tribal SHORT", 25000, "/products/jort-tribal", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/11.jpg?v=1734593413"),
    ("Denim-rapport JORT", 38000, "/products/jort-rapport", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/00.jpg?v=1760206051"),
    ("LA FERIA ON TOUR / Anniversary tee", 45000, "/products/camiseta-dark-eternal-copia", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG_9779.jpg?v=1730175020"),
    ("POLERA STRASS GRIS", 32000, "/products/polera-strass-gris", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/362.jpg?v=1728879220"),
    ("LOGO STRASS TEE", 30000, "/products/polera-strass-negra", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/301.jpg?v=1728879141"),
    ("LOGO STRASS HOODIE", 55000, "/products/hoodie-cromo-boxy-copia", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/270.jpg?v=1728878684"),
    ("JORT CARGO CAMO VERDE", 35000, "/products/jort-cargo-camo-verde", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/316.jpg?v=1728878387"),
    ("JORT CARGO CAMO GRIS", 35000, "/products/jort-cargo-camo-gris", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/291.jpg?v=1728878280"),
    ("TANK TOP MEN", 25000, "/products/polera-musculosa-hombre", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/285.jpg?v=1728877768"),
    ("TANK TOP GIRL", 25000, "/products/polera-musculosa-mujer", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/343_f493846b-b91d-48fc-8537-3d5f6150bd26.jpg?v=1728877723"),
    ("BOXY TEE GRIS", 25000, "/products/boxy-tee-gris", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/265.jpg?v=1728860898"),
    ("SWEATER CAPUCHA LOGO", 40000, "/products/sweater-logo", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/337.jpg?v=1728860070"),
    ("VARSITY-JACKET CAMO", 60000, "/products/varsity-jacket-camo", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/281.jpg?v=1728851709"),
    ("STRASS REED HOODIE", 50000, "/products/strass-black-hoodie-copy", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Facetune_11-09-2024-00-11-06.heic?v=1726377196"),
    ("STRASS BLACK HOODIE", 50000, "/products/strass-black-hoodie-1", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Facetune_11-09-2024-00-12-27.jpg?v=1726393167"),
    ("STRASS PINK HOODIE", 50000, "/products/strass-pink-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo15587ok.jpg?v=1687989606"),
    ("VARSITY JACKET LUCIERNAGA", 75000, "/products/varsity-jacket-black-02", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo16042ok.jpg?v=1687807311"),
    ("CATS GRAY TEE", 25000, "/products/cats-gray-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/14E.jpg?v=1741904708"),
    ("CAPUCHA JACKET BLACK 02", 35000, "/products/chaqueta-capucha-black-02", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG_0208.jpgK.jpg?v=1723847778"),
    ("POLERA BLACK 02 BOXY", 25000, "/products/luciernaga-black-cropped-tee-copy", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG_0209.jpgK.jpg?v=1723850904"),
    ("VARSITY JACKET BLACK 02", 75000, "/products/varsity-jacket-black-2", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG_0213.jpgS.jpg?v=1723850744"),
    ("TEE BOXY DARK PINK", 20000, "/products/tee-boxy-dark-pink", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo15569ok_copia.jpg?v=1721708058"),
    ("CROP-TOP DARK PINK", 20000, "/products/crop-top-dark-pink", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo18573ok_copia.jpg?v=1721706266"),
    ("CROP-TOP CROMO NEGRO", 25000, "/products/crop-top-negra-cromo", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo18573ok.jpg?v=1718418142"),
    ("HOODIE CROMO OVERSIZE", 50000, "/products/gray-hoodie-oversize", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo18419ok.jpg?v=1722727086"),
    ("POLERA LOCK ARDE", 33000, "/products/polera-manga-larga", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Captura_sin_titulo18491ok.jpg?v=1718417639"),
    ("CARGO-PANTS WOLVES", 45000, "/products/cargo-black-pants", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Captura_sin_titulo18316ok.jpg?v=1718551056"),
    ("CARPINTERO-PANTS CHEETAH", 40000, "/products/carpintero-black-pants", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Captura_sin_titulo18411ok.jpg?v=1718541705"),
    ("FLARE-PANTS DARK", 42000, "/products/flare-pants-negro", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Captura_sin_titulo18526ok.jpg?v=1718540870"),
    ("CROP-TOP CROMO GRIS", 25000, "/products/crop-top-logo-cromado", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo18622ok.jpg?v=1718417951"),
    ("POLERA CONEXIÓN NEGRA", 25000, "/products/union-black-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Captura_sin_titulo18514ok.jpg?v=1718418332"),
    ("POLERA UNIÓN GRIS", 27000, "/products/conexion-chrome-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Captura_sin_titulo18560ok.jpg?v=1718418726"),
    ("POLERA OBSIDIANA CLIP", 28000, "/products/japo-gray-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo18547ok.jpg?v=1718419381"),
    ("POLERA NOCTURA DISCO", 25000, "/products/japo-black-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Captura_sin_titulo18555ok.jpg?v=1718419369"),
    ("SWEATER TRIBAL", 60000, "/products/sweater-black-canguro", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Captura_sin_titulo18322ok.jpg?v=1718419580"),
    ("SWEATER SALLY ROJO", 30000, "/products/sweater-lineas-boxy-rojo", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo18296ok.jpg?v=1718419766"),
    ("SWEATER JACK NEGRO", 45000, "/products/sweater-lineas-roxy", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo18320ok.jpg?v=1718426993"),
    ("VARSITY-JACKET ARCANA CAFÉ", 75000, "/products/varsity-jacket-brown", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Captura_sin_titulo18449ok.jpg?v=1718420900"),
    ("VARSITY-JACKET ARCANA NEGRA", 90000, "/products/varsity-jacket-black", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo18446ok.jpg?v=1718421166"),
    ("HOODIE CROMO BOXY", 49000, "/products/3d-chrome-logo-hoodie-copia", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo18363ok.jpg?v=1722726954"),
    ("HOODIE DARK OSCURIDAD", 52000, "/products/hoodie-dark-oscuridad", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Captura_sin_titulo18435ok.jpg?v=1718420102"),
    ("CREWNECK DARK ARCANA", 50000, "/products/cromado-crewneck", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo18350ok.jpg?v=1724962482"),
    ("Pants \"Black Wolf\"", 20000, "/products/pants-black", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/Capturasintitulo7894ok.jpg?v=1653982118"),
    ("Tee gray \"Angel wings\"", 25000, "/products/tee-gray-angel-wings", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/Capturasintitulo7248ok.jpg?v=1660446255"),
    ("Tee Gray \"Girly\"", 15000, "/products/copia-de-tee-gray-wolf", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/capturasintitulo10908ok.jpg?v=1673984240"),
    ("Snake Blue Tee", 20000, "/products/copia-snake-blue-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/FDA7B39A-2004-4AB0-8C02-CE1C8EC4B633.jpg?v=1717539930"),
    ("Pants \"Gray Wolf\"", 35000, "/products/pants-gray-wolf", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/Capturasintitulo7914ok.jpg?v=1653982135"),
    ("Zipper gray hoodie", 25000, "/products/zipper-gray-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/9F9459FE-2A72-4BBE-AA9C-F9557E5E6B91.jpg?v=1717435761"),
    ("CREWNECK OXIDADO MINIMAL", 25000, "/products/crewneck-oxidado-minimal", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo17492okcopia_8037eca6-e554-4d40-b662-7938b7f778a8.jpg?v=1717428231"),
    ("Tee oversize gray logo", 20000, "/products/tee-oversize-gray-logo-1", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/57100A1D-C6C2-49D8-995C-BE4A7541C171.jpg?v=1717375861"),
    ("Tee Black \"Night Witch\"", 15000, "/products/tee-black-night-witch", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/doslobosmayo20210642ok.jpg?v=1622152294"),
    ("Tee Black \"Biker skeletons\"", 15000, "/products/tee-black-biker-skeletons", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/doslobosmayo20210664ok.jpg?v=1622152385"),
    ("Tee Minimal \"Mint\"", 12000, "/products/copia-de-tee-black-night-witch", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/Capturasintitulo10855ok.jpg?v=1671167643"),
    ("Tee Stripe \"Orange\"", 8000, "/products/copia-de-tee-stripe-mint", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/capturasintitulo10825ok.jpg?v=1671163980"),
    ("Tee Stripe \"Cross\"", 8000, "/products/tee-gray-wolf-1", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/Capturasintitulo7256ok.jpg?v=1653968308"),
    ("Cargo zipper pants", 35000, "/products/cargo-zipper-pants", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/867C124D-00EE-4ED7-A5B7-499F3BD33CAB.jpg?v=1717358165"),
    ("Two wolves hoodie", 30000, "/products/two-wolves-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/06AB5D6C-F4FF-48A5-87E8-D590CF4E3216.jpg?v=1717353586"),
    ("CREWNECK GALGOS ETERNAL VERSIÓN", 45000, "/products/crewneck-galgos-eternal-version", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo17492ok.jpg?v=1717349236"),
    ("Tee Oversize \"White Mask\"", 20000, "/products/copia-de-tee-oversize-skeleton", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/capturasintitulo10959ok.jpg?v=1671211623"),
    ("Tee oversize black \"Anniversary Nº7\"", 20000, "/products/tee-oversize-black-eagle", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/Capturasintitulo10447ok.jpg?v=1668893686"),
    ("CAMO LOGO SHIRT", 25000, "/products/camo-logo-shirt", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/O6B9301ok.jpg?v=1693863997"),
    ("Camisa Moon Ritual", 30000, "/products/camisa-moon-ritual", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/FD78A2FF-E35C-43C4-AECB-86E7B86D2582.jpg?v=1717346128"),
    ("ROMULO Y REMO TEE", 20000, "/products/romulo-y-remo-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/69485F84-887E-4862-81A8-236070021A43.jpg?v=1717344587"),
    ("Raw eonia hoodie", 30000, "/products/raw-eolia-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/00A0EDC7-C620-41D8-9BB5-4A52165B9A8E.jpg?v=1717290276"),
    ("Post vortex gray hoodie", 30000, "/products/post-vortex-gray-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/E9BEF0E4-45B1-44D0-989B-184EEDDA4D38.jpg?v=1717289641"),
    ("WOLVES BLACK TEE", 20000, "/products/wolves-black-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/C043C2FA-91A6-4EF4-A0EF-86E8B819E448.jpg?v=1717286573"),
    ("Tee oversize gray logo", 20000, "/products/tee-oversize-gray-logo", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/AB010140-AE3F-48FE-AF7E-C31C0F89042B.jpg?v=1717285997"),
    ("Skull blue tee", 20000, "/products/skull-blue-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/1_copia.jpg?v=1615320028"),
    ("Monje black tee", 15000, "/products/monje-black-ter", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/doslobosmayo20210642ok.jpg?v=1622152294"),
    ("Monje color gray tee", 20000, "/products/monje-color-gray-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/BCDE1FBB-47F7-456D-8E9F-C3FDE0246C5D.jpg?v=1717279380"),
    ("Rómulo y Remo hoodie", 30000, "/products/romulo-y-remo-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/A85ED32B-303B-4FB7-A71B-59F70A39E682.jpg?v=1717278701"),
    ("Skull gray tee", 20000, "/products/skull-gray-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/9B3F61C0-E80F-4EDB-A283-1CEB5FB02C60.jpg?v=1717278210"),
    ("Wolf chrome tee", 20000, "/products/wolf-chrome-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/8ACD5352-F070-4248-80C1-45C9C7483F64.jpg?v=1717279757"),
    ("Tee oversize blue logo", 20000, "/products/tee-oversize-blue-logo", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/61DD6DAC-CB48-48C8-8100-DB0B8781CC4E.jpg?v=1717277973"),
    ("WOLVES RED HOODIE", 30000, "/products/wolves-red-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/7FEFDB0F-AD8A-4CBE-8891-855F67253AF6.jpg?v=1717277077"),
    ("Post Vortex Crewneck", 30000, "/products/post-vortex-crewneck", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/1763B424-1676-4D68-B3CA-EEF901890D9E.jpg?v=1717275817"),
    ("Moon raw hoodie", 30000, "/products/moon-raw-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/A8FDE71B-F729-4D41-8341-DB376BFB9497.jpg?v=1717275060"),
    ("Tee oversize black \"Angel\"", 25000, "/products/tee-oversize-black-angel", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/C9F8D237-2BA6-41E8-877A-6F8BE6429358.jpg?v=1717274669"),
    ("WOLVES GRAY/BLACK TEE", 20000, "/products/wolves-gray-black-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/CBEC855C-359D-4AC3-8143-FA6BD502A090.jpg?v=1717274359"),
    ("RED ANGEL TEE", 20000, "/products/wolves-leyend-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/01CE9785-64B8-4D96-8C77-A8419A4C0909.jpg?v=1717274493"),
    ("MOON RITUAL BLACK TEE", 20000, "/products/moon-ritual-black-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/2761AF93-DB3E-4312-B588-9230918C19AD.jpg?v=1717273588"),
    ("MOON RITUAL GRAY/BLACK TEE", 20000, "/products/angel-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/21CF5B5C-306F-4340-862F-F0A6ED680869.jpg?v=1717273506"),
    ("LUCIÉRNAGA BLACK CROPPED TEE", 15000, "/products/luciernaga-black-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo15577ok.jpg?v=1687939151"),
    ("Tee Ninja \"Black\"", 15000, "/products/tee-oversize-skeleton-1", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/capturasintitulo11007ok.jpg?v=1671167782"),
    ("Hoodie Mint Logo", 20000, "/products/copia-de-hoodie-black-anniversary-nº7", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/capturasintitulo11203ok.jpg?v=1671164215"),
    ("LUCIÉRNAGA BLACK HOODIE", 30000, "/products/luciernaga-black-hoodie-1", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo16479ok.jpg?v=1687913924"),
    ("Varsity Jacket Mint Minimal", 30000, "/products/copia-de-versatility-jacket-black-minimal", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/capturasintitulo11720ok.jpg?v=1674432122"),
    ("Tee Ninja \"Mint\"", 30000, "/products/copia-de-tee-ninja-black", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/capturasintitulo11064ok.jpg?v=1671165933"),
    ("Sweater cardigán logo", 50000, "/products/letter-cardigan", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG_4040.jpg?v=1714423697"),
    ("LOGO CHROME TEE", 25000, "/products/logo-chrome-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/12s.jpg?v=1741904970"),
    ("Sweater Étnico", 45000, "/products/sweater-etnico-wolves", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/Capturasintitulo7699ok.jpg?v=1659673210"),
    ("Varsity Jacket \"Brown Paisley\"", 90000, "/products/versatility-jacket-brown-bandana", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/Capturasintitulo7667ok.jpg?v=1653979558"),
    ("Varsity Jacket Black Minimal", 75000, "/products/copia-de-versatility-jacket-black-wolf", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/capturasintitulo11729ok.jpg?v=1671168253"),
    ("Crewneck Galgos", 45000, "/products/crewneck-galgos", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo2852okcopia.jpg?v=1741904826"),
    ("Tee Black \"orange mask\"", 20000, "/products/tee-black-orange-mask", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/capturasintitulo10932ok.jpg?v=1671173741"),
    ("CHROME SWEATER", 50000, "/products/chrome-sweater", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo15866ok.jpg?v=1714424130"),
    ("Sweater cardigán skeleton", 50000, "/products/cardigan-black-logo-1", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/Capturasintitulo7597ok.jpg?v=1717706520"),
    ("POLERA CALMA NEGRA", 20000, "/products/polera-negra-siempre-contigo", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG_7598_1f29452e-d02f-4e10-af5b-b5e0efb4a675.jpg?v=1707883885"),
    ("POLERA ALMA BLANCA", 25000, "/products/polera-alma-blanca", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG_7755.jpg?v=1707884215"),
    ("POLERÓN CONTIGO NEGRO", 45000, "/products/poleron-contigo-negro", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG_7680.jpg?v=1708447386"),
    ("POLERÓN SIEMPRE ROJO", 45000, "/products/poleron-rojo-siempre-contigo", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/IMG_7745.jpg?v=1707884545"),
    ("Varsity Jacket Black Wolf", 95000, "/products/bomber-jacket-black-bandana", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/Capturasintitulo7395ok.jpg?v=1653973173"),
    ("STRASS LUCIÉRNAGA HOODIE", 50000, "/products/strass-black-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo15825ok.jpg?v=1687984690"),
    ("CATS BLACK HOODIE", 45000, "/products/luciernaga-black-hoodie", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo16452ok.jpg?v=1687994530"),
    ("Tee Gray Galgos", 20000, "/products/tee-gray-galgos", "https://cdn.shopify.com/s/files/1/0396/9584/3481/products/Capturasintitulo2742ok.jpg?v=1639454566"),
    ("CATS BLACK TEE", 25000, "/products/cats-black-tee", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo15552ok.jpg?v=1697411128"),
    ("3D CHROME LOGO HOODIE", 60000, "/products/copia-de-hoodie-gray-wolf", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/capturasintitulo11681ok.jpg?v=1696178487"),
    ("POLERA DARK IGOR", 15000, "/products/polera-dark-igor", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo17693ok.jpg?v=1702670418"),
    ("JORT CARGO CORROÍDO", 35000, "/products/jort-oxidado", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo17673ok.jpg?v=1702671315"),
    ("CHAQUETA CORROÍDO", 25000, "/products/chaqueta-de-jeans-eternal", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo17761ok.jpg?v=1702670805"),
    ("PANTALÓN CARGO", 40000, "/products/pantalon-cargo", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo17654ok.jpg?v=1702713042"),
    ("PANTALÓN CARPINTERO", 40000, "/products/pantalones-carpinteros", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo17634ok_14cc2b3c-dab0-4aa4-93ff-0849fe9dfbec.jpg?v=1702676755"),
    ("POLERA DARK CARRIE", 25000, "/products/polera-julia-negra", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo17624ok.jpg?v=1702671571"),
    ("CROP TOP LOGOGRAMA", 10000, "/products/top-grabillado-logo", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo17589ok.jpg?v=1702671766"),
    ("POLERA LOGOGRAMA", 25000, "/products/polera-grabillada-logo", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo17462ok.jpg?v=1702671893"),
    ("POLERÓN INFINITO 08", 45000, "/products/poleron-infinito-08", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo17492okcopia.jpg?v=1702678500"),
    ("CAMISETA DARK ETERNAL", 35000, "/products/polera-futbol-americano-infinito-08", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo17379ok.jpg?v=1702712900"),
    ("SWEATER MINIMALISTA", 25000, "/products/chaleco-minimalista", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo17634ok.jpg?v=1706731908"),
    ("SWEATER ETERNAL", 50000, "/products/chaleco-infinito-08", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo17417ok.jpg?v=1702673549"),
    ("POLERA INFINITO 08", 15000, "/products/polera-infinito", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo17610ok.jpg?v=1702673911"),
    ("JORT CARPINTERO ETERNO 08", 35000, "/products/jort-infito", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo17530ok.jpg?v=1702674011"),
    ("CAMISA ETERNO 08", 20000, "/products/camisa-boxy-fit", "https://cdn.shopify.com/s/files/1/0396/9584/3481/files/Capturasintitulo17489ok_39907269-1711-4029-adeb-83f86bcb985d.jpg?v=1702674223"),
]


# ---------------------------------------------------------------------
# Tiendas nuevas (2026-08-24) -- consentimiento del dueno de la tienda para
# usar un crawler ya confirmado por el dueno del proyecto. Cargadas 100%
# desde el products.json real de cada una (cacheado en
# data/shopify_cache/, bajado con curl real el 2026-08-24), no desde
# tuplas a mano: con fotos completas + descripcion completa + stock real
# por talla ya es demasiado dato por producto para transcribir a mano sin
# error. Ver docs/catalogo_real.md para el detalle de exclusiones.
# ---------------------------------------------------------------------

NOVORICH = cargar_shopify_cache(
    BASE_DIR / "data" / "shopify_cache" / "novorich.json",
    excluir_handles={
        # 3 duplicados reales del mismo hoodie "HODDIE - LUXURY WHITE" --
        # el handle "hoddie-novvm-luxury" (mas antiguo, con las 6 fotos
        # combinadas de los 3) se deja como el producto real, unico.
        "hoddie-luxury-white", "hoddie-luxury-white-copia-1", "hoddie-luxury-white-copia",
        # Skullcap: gorro sin visera, pero la ficha real no confirma el
        # material ("tejido suave", sin especificar lana) -- no se carga
        # para no inventar el dato (ver casos dudosos en catalogo_real.md).
        "skullcap-novorich",
    },
)
# Los 5 "TRACKSUIT" (categoria "conjunto", agregada 2026-08-24 -- ver
# clasificar_prenda()) ya NO estan excluidos: el dueno aprobo la categoria
# nueva, asi que quedan incluidos arriba en NOVORICH mismo, con fotos +
# descripcion + stock real igual que el resto.

SHATTERS = cargar_shopify_cache(BASE_DIR / "data" / "shopify_cache" / "shatters.json")

STUFFIESCONCEPT = cargar_shopify_cache(
    BASE_DIR / "data" / "shopify_cache" / "stuffiesconcept.json",
    excluir_handles={
        # Trucker Hat: gorro CON visera -- mismo motivo que "Tag Camo Cap"
        # de Floating (ver casos dudosos, 2026-08-22): el flujo de gorro de
        # la app solo maneja curvo/plano/lana, no cap con visera.
        "three-stars-trucker-hat", "three-stars-trucker-hat-copia",
    },
)

# ---------------------------------------------------------------------
# Piloto de upgrade a fotos/descripcion/stock reales (2026-08-24) para 2
# tiendas YA cargadas a mano (las 2 mas chicas de las 14 que ademas
# resultaron ser Shopify) -- se cruza por handle (ultimo segmento del path
# ya cargado) contra el products.json real, sin tocar corte/categoria ya
# verificados de esas tiendas.
# ---------------------------------------------------------------------
DATOS_SHOPIFY_UPGRADE = {
    "Oversaints": datos_shopify_por_handle(BASE_DIR / "data" / "shopify_cache" / "oversaints.json"),
    "Roots South": datos_shopify_por_handle(BASE_DIR / "data" / "shopify_cache" / "rootsouth.json"),
    # Tanda 2 (2026-08-25): 6 tiendas mas, confirmadas Shopify, mismo
    # metodo -- cruce por handle contra el products.json real cacheado,
    # sin tocar corte/subtipo/categoria ya verificados de cada una.
    "OVA Chile": datos_shopify_por_handle(BASE_DIR / "data" / "shopify_cache" / "ova.json"),
    "Rotten": datos_shopify_por_handle(BASE_DIR / "data" / "shopify_cache" / "rotten.json"),
    "Simpl.": datos_shopify_por_handle(BASE_DIR / "data" / "shopify_cache" / "simpl.json"),
    "AbsolutelyWrong": datos_shopify_por_handle(BASE_DIR / "data" / "shopify_cache" / "absolutelywrong.json"),
    "ForceBlack": datos_shopify_por_handle(BASE_DIR / "data" / "shopify_cache" / "forceblack.json"),
    "Floating": datos_shopify_por_handle(BASE_DIR / "data" / "shopify_cache" / "floating.json"),
    # Tanda 3 (2026-08-25): las 3 tiendas mas grandes del catalogo, mismo
    # metodo -- cache paginado (products.json tiene mas de 250 productos en
    # estas 3) cruzado por handle contra las tuplas ya cargadas y
    # verificadas a mano.
    "BANG GANG": datos_shopify_por_handle(BASE_DIR / "data" / "shopify_cache" / "banggang.json"),
    "UNK Chile": datos_shopify_por_handle(BASE_DIR / "data" / "shopify_cache" / "unkchile.json"),
    "Doslobos": datos_shopify_por_handle(BASE_DIR / "data" / "shopify_cache" / "doslobos.json"),
}


def main():
    catalog_actual = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(json.dumps(catalog_actual, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Respaldo del catalogo mock guardado en {BACKUP_PATH}")
    else:
        print(f"Respaldo ya existia en {BACKUP_PATH}, no se sobreescribe")

    nuevo_catalogo = []

    fuentes = [
        ("OVA Chile", "ovachile.cl", "OVA Apparel", OVA),
        ("Oversaints", "studioversaints.com", "Oversaints", OVERSAINTS),
        ("El Pulento Style", "www.elpulentostyle.cl", "El Pulento Style", PULENTO),
        ("Rapt", "rapt.cl", "Rapt", RAPT),
        ("Roots South", "rootsouth.cl", "Roots South", ROOTSOUTH),
        ("Rotten", "rottenbrand.cl", "Rotten", ROTTEN),
        ("Selvanegrawear", "selvanegrawear.cl", "Selvanegrawear", SELVANEGRA_POLERAS),
        ("Simpl.", "simpl.cl", "Simpl.", SIMPL),
        ("AbsolutelyWrong", "absolutelywrong.cl", "AbsolutelyWrong", ABSOLUTELYWRONG),
        ("ForceBlack", "forceblack.cl", "ForceBlack", FORCEBLACK),
        ("Floating", "floating.cl", "Floating", FLOATING),
        ("BANG GANG", "bvnggvng.cl", "BANG GANG", BANGGANG),
        ("UNK Chile", "unkchile.cl", "UNK Chile", UNKCHILE),
        ("Doslobos", "dosloboschile.cl", "Doslobos", DOSLOBOS),
    ]

    for tienda, dominio, marca, productos in fuentes:
        upgrade = DATOS_SHOPIFY_UPGRADE.get(tienda, {})
        for i, (nombre, precio, path, imagen) in enumerate(productos, start=1):
            datos_reales = upgrade.get(_handle_de_path(path))
            if datos_reales:
                nuevo_catalogo.append(
                    construir_producto(
                        i, tienda, dominio, marca, nombre, precio, path, imagen,
                        fotos=datos_reales["fotos"],
                        descripcion_real=datos_reales["descripcion_real"],
                        tallas_reales=datos_reales["tallas_reales"],
                    )
                )
            else:
                nuevo_catalogo.append(
                    construir_producto(i, tienda, dominio, marca, nombre, precio, path, imagen)
                )

    # Tiendas nuevas (2026-08-24), cargadas 100% desde products.json real
    # -- ver bloque NOVORICH/SHATTERS/STUFFIESCONCEPT mas arriba.
    nuevas_tiendas_shopify = [
        ("Novorich", "www.novorich.cl", "NovoRich", NOVORICH),
        ("Shatters", "shatters.cl", "Shatters", SHATTERS),
        ("Stuffies Concept", "stuffiesconcept.com", "Stuffies Concept", STUFFIESCONCEPT),
    ]
    for tienda, dominio, marca, productos in nuevas_tiendas_shopify:
        for i, p in enumerate(productos, start=1):
            nuevo_catalogo.append(
                construir_producto(
                    i, tienda, dominio, marca, p["nombre"], p["precio"], p["path"], None,
                    fotos=p["fotos"], descripcion_real=p["descripcion_real"], tallas_reales=p["tallas_reales"],
                )
            )

    # Gorros de Selvanegrawear (forma lana, sin tallas_disponibles).
    for i, (nombre, precio, path, imagen, color) in enumerate(SELVANEGRA_GORROS, start=1):
        nuevo_catalogo.append(
            construir_producto(
                1000 + i, "Selvanegrawear", "selvanegrawear.cl", "Selvanegrawear",
                nombre, precio, path, imagen,
                es_gorro=True, color_dominante=color, forma_gorro="lana",
            )
        )

    CATALOG_PATH.write_text(json.dumps(nuevo_catalogo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Catalogo real escrito: {len(nuevo_catalogo)} productos en {CATALOG_PATH}")

    por_tienda = {}
    for p in nuevo_catalogo:
        por_tienda[p["tienda"]] = por_tienda.get(p["tienda"], 0) + 1
    for tienda, cantidad in por_tienda.items():
        print(f"  - {tienda}: {cantidad} productos")

    prendas = [p for p in nuevo_catalogo if p["categoria"] != "gorro"]
    con_corte_real = [p for p in prendas if p.get("corte") and p["corte"] != "sin corte definido"]
    sin_definir = [p for p in prendas if p.get("corte") == "sin corte definido"]
    print()
    print(f"Corte: {len(con_corte_real)}/{len(prendas)} prendas con corte real asignado.")
    print(f"'sin corte definido' (revisar a mano): {len(sin_definir)}")
    for p in sin_definir:
        print(f"  - {p['nombre']} | {p['tienda']} | {p['link']}")


if __name__ == "__main__":
    main()
