// Codigo compartido entre index.html (formulario) y resultados.html
// (pagina de resultados): el perfil guardado, la animacion de carga y como
// se dibuja cada tarjeta de producto.

// Distingue una ilustracion mock (SVG local, generada por
// generar_imagenes_prendas.py/generar_imagenes_gorro.py) de una foto real
// de producto (URL externa al CDN de la tienda, catalogo real). Las mock
// siempre viven en /static/img/... -- cualquier otra cosa (http/https a un
// dominio externo) es una foto real, y el aviso de "imagen ilustrativa" no
// le corresponde.
function esImagenIlustrativa(imagen) {
  return typeof imagen === "string" && imagen.startsWith("/static/img/");
}

// "Confianza KOLIZION" (2026-09-02): sello con el nivel (0-5) calculado en
// construir_catalogo_real.py a partir de 5 criterios objetivos (marca de
// autor, material informado, despacho declarado, trayectoria en KOLIZION,
// fotos reales) -- ver docs/catalogo_real.md. Reusado en tarjetas mini
// (comun.js), tarjetas de vitrina (vitrina.js) y la ficha completa
// (_vista_previa.html).
const CONFIANZA_ETIQUETAS = {
  marca_autor: "Marca de autor",
  material_calidad: "Material informado/de calidad",
  despacho_declarado: "Despacho declarado",
  trayectoria_kolizion: "Trayectoria sin problemas en KOLIZION",
  fotos_reales: "Fotos reales",
};

function insigniaConfianzaTitulo(confianza) {
  // 2026-09-07 (spec "Nivel de Confianza KOLIZION"): ahora se listan los 5
  // criterios siempre -- lenguaje neutral ("no verificado todavia") para
  // los que faltan, nunca "no cumple" (ausencia de evidencia no es una
  // acusacion). Reemplaza el criterio anterior (2026-09-02) de listar solo
  // los cumplidos.
  return Object.entries(CONFIANZA_ETIQUETAS)
    .map(([clave, texto]) => (confianza[clave] ? `✓ ${texto}` : `○ ${texto} (no verificado todavía)`))
    .join("\n");
}

// data-confianza (no title): 2026-09-03, pedido del usuario -- en mobile un
// tap no muestra el title (tooltip), asi que el detalle se abre con un
// popup real al tocar/clickear el sello (ver _abrirPopupConfianza abajo).
function insigniaConfianzaHtml(rec) {
  const confianza = rec.confianza;
  if (!confianza || typeof confianza.nivel !== "number") return "";
  return `<span class="insignia-confianza" data-confianza='${JSON.stringify(confianza)}'>Nivel ${confianza.nivel}</span>`;
}

let _popupConfianzaEl = null;

function _cerrarPopupConfianza() {
  if (_popupConfianzaEl) {
    _popupConfianzaEl.remove();
    _popupConfianzaEl = null;
  }
}

function _abrirPopupConfianza(badge, confianza) {
  _cerrarPopupConfianza();
  const pop = document.createElement("div");
  pop.className = "popup-confianza";
  pop.style.visibility = "hidden";
  pop.innerHTML = `
    <strong>Confianza KOLIZION · Nivel ${confianza.nivel}/5</strong>
    <p>${insigniaConfianzaTitulo(confianza).replace(/\n/g, "<br>")}</p>
  `;
  document.body.appendChild(pop);
  const r = badge.getBoundingClientRect();
  const arriba = r.bottom + pop.offsetHeight + 8 > window.innerHeight;
  pop.style.left = Math.max(8, Math.min(r.left, window.innerWidth - pop.offsetWidth - 8)) + "px";
  pop.style.top = (arriba ? r.top - pop.offsetHeight - 8 : r.bottom + 8) + "px";
  pop.style.visibility = "visible";
  _popupConfianzaEl = pop;
}

// Captura (no burbuja): las tarjetas (resultado-card-mini, tarjeta-vitrina)
// tienen su propio listener de click que abre la ficha completa -- en fase
// de burbuja ese listener ya se disparo antes de llegar aca. En captura,
// este handler corre primero y stopPropagation() frena TODO lo demas
// (incluido abrir la ficha) cuando el click fue sobre el sello.
document.addEventListener("click", (e) => {
  const badge = e.target.closest(".insignia-confianza");
  if (badge && badge.dataset.confianza) {
    e.stopPropagation();
    const yaAbierto = _popupConfianzaEl !== null;
    _cerrarPopupConfianza();
    if (!yaAbierto) _abrirPopupConfianza(badge, JSON.parse(badge.dataset.confianza));
    return;
  }
  if (_popupConfianzaEl && !e.target.closest(".popup-confianza")) _cerrarPopupConfianza();
}, true);

// Producto "oficial" (2026-08-27): tienda con consentimiento explicito para
// vender de verdad (ver TIENDAS_OFICIALES en construir_catalogo_real.py),
// no solo foto real -- eso ya lo tienen varias tiendas mas sin ser
// "oficial". Para estos productos la compra pasa a ser real DENTRO de
// KOLIZION (carrito local, ver mas abajo) en vez de linkear afuera -- las
// demas tiendas (la gran mayoria del catalogo hoy) siguen linkeando a su
// sitio externo exactamente igual que siempre, no se les toco nada.
function productoTieneStock(rec) {
  if (rec.tallas_variantes && rec.tallas_variantes.length) {
    return rec.tallas_variantes.some((v) => v.disponible);
  }
  return Boolean(rec.tallas_disponibles && rec.tallas_disponibles.length);
}

function botonAccionProductoHtml(rec) {
  if (!rec.oficial) {
    return `<a href="${rec.link}" target="_blank" rel="noopener">${esImagenIlustrativa(rec.imagen) ? "Ver producto (ejemplo)" : "Ver producto"}</a>`;
  }
  if (!productoTieneStock(rec)) {
    return `<span class="boton-proximamente" aria-disabled="true">Próximamente</span>`;
  }
  // Elegir talla/color pasa siempre por la ficha completa (modal) -- este
  // boton de la tarjeta solo la abre, el "Agregar al carrito" real esta
  // ahi dentro (ver abrirVistaPrevia).
  return `<button type="button" class="btn-abrir-ficha-carrito">Agregar al carrito</button>`;
}

// PWA: registra el service worker (static/sw.js, servido en /sw.js para
// que su alcance cubra toda la app -- ver app.py) en todas las paginas.
// Junto con manifest.json y los iconos (ver _pwa_meta.html), esto es lo
// que deja "instalar" KOLIZION desde el navegador del celular. Si falla
// (ej. sin HTTPS -- los navegadores exigen conexion segura para service
// workers, salvo en localhost) queda en silencio: la app sigue funcionando
// normal en el navegador, solo no se puede instalar.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}

// Perfil guardado en localStorage (una sola vez, no se vuelve a preguntar).
// Vive aca (no en script.js) porque koko.js y el tracking de clics de
// renderResultados tambien lo necesitan, y ambos corren en paginas donde
// script.js no esta cargado (resultados.html).
const PERFIL_KEY = "miPerfil";

function getPerfil() {
  const raw = localStorage.getItem(PERFIL_KEY);
  return raw ? JSON.parse(raw) : null;
}

function guardarPerfil(perfil) {
  localStorage.setItem(PERFIL_KEY, JSON.stringify(perfil));
}

// Preferencias negativas (2026-08-28): que excluir por completo de "yo"
// buscando -- aparte del perfil (no es un dato de la persona, es un filtro),
// se manda tal cual al servidor en cada busqueda "yo" (ver form-busqueda-yo
// en script.js y btn-koko-si en koko.js). Los checkboxes viven en /perfil
// (ver configurarPreferenciasNegativas en perfil.js).
const PREFERENCIAS_NEGATIVAS_KEY = "preferenciasNegativas";

function getPreferenciasNegativas() {
  try {
    return JSON.parse(localStorage.getItem(PREFERENCIAS_NEGATIVAS_KEY)) || {};
  } catch (e) {
    return {};
  }
}

function guardarPreferenciasNegativas(prefs) {
  localStorage.setItem(PREFERENCIAS_NEGATIVAS_KEY, JSON.stringify(prefs));
}

// Preferencia de calce/ajuste (2026-09-07, pedido del usuario): "Como
// prefieres que te quede la ropa" -- Ajustado/Normal/Holgado. Mismo patron
// que preferencias negativas (se guarda aparte del perfil, se manda tal cual
// al servidor en cada busqueda "yo", se edita en /perfil -- ver
// configurarAjusteTalla en perfil.js). "normal" es el default: no cambia el
// calculo de talla de siempre.
const AJUSTE_TALLA_KEY = "ajusteTallaKolizion";

function getAjusteTalla() {
  return localStorage.getItem(AJUSTE_TALLA_KEY) || "normal";
}

function guardarAjusteTalla(ajuste) {
  localStorage.setItem(AJUSTE_TALLA_KEY, ajuste);
}

// Texto humano de cada clave de preferencia negativa (usado por
// resultados.js para armar la pregunta "tienes marcado que no te gustan
// X -- ¿buscamos igual incluyendo esas opciones, solo por esta vez?").
const ETIQUETAS_PREFERENCIAS_NEGATIVAS = {
  excluir_rotos: "pantalones rotos/desgastados",
  excluir_grafico_grande: "gráficos/dibujos muy grandes",
  excluir_texto_grande: "frases/texto muy grande",
  excluir_cara_logo_grande: "caras/logos gigantes",
};

// Escapa HTML (< > & " ' etc.) para poder insertar texto por innerHTML sin
// riesgo de XSS -- crea un elemento, le pone el texto como textContent
// (nunca se interpreta como HTML) y lee de vuelta el innerHTML ya escapado.
// Usado por koko.js (respuestas de Koko) y perfil.js (datos que el usuario
// escribio el mismo en el formulario de perfil, guardados tal cual en
// localStorage -- nunca confiar en que un dato ya guardado sea "seguro"
// solo porque lo escribio el propio usuario).
function escaparHtml(texto) {
  const div = document.createElement("div");
  div.textContent = texto;
  return div.innerHTML;
}

// Frases de relleno para la animacion de carga -- el usuario las va a
// reemplazar por las suyas propias despues.
const FRASES_CARGA = [
  "Buscando tu prenda ideal...",
  "Revisando tiendas chicas...",
  "Comparando cortes y tallas...",
  "Ya casi...",
];

function esperar(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Avisa al backend que el usuario hizo clic en "Ver producto" -- una de las
// 2 senales de "interes" que usa el historial de Koko (la otra es lo que ya
// busca). Solo se registra en busquedas "yo" con email conocido; una
// busqueda "regalo" es sobre el estilo de otra persona, no del usuario.
// Best-effort: si falla, no debe afectar que el link igual abra el producto.
function registrarInteresProducto(rec) {
  try {
    const payloadRaw = sessionStorage.getItem("ultimoPayload");
    if (!payloadRaw) return;
    const payload = JSON.parse(payloadRaw);
    if (payload.modo !== "yo" || !payload.email) return;
    fetch("/api/koko/interes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: payload.email,
        producto: { nombre: rec.nombre, tienda: rec.tienda, categoria: rec.categoria, corte: rec.corte },
      }),
    });
  } catch (e) {
    // Silencioso a proposito -- ver comentario de arriba.
  }
}

// --- Favoritos: estrella reutilizable en resultados/vitrina/perfil --------
// El identificador es el email del perfil guardado (mismo que usa el
// historial de Koko) -- sin perfil/gmail no hay donde guardar el favorito,
// asi que la estrella directamente no se dibuja.
function emailFavoritos() {
  const perfil = getPerfil();
  return perfil ? perfil.gmail || "" : "";
}

// Trae el set de nombres ya marcados como favoritos para pintar la
// estrella llena desde el primer render (no despues de un parpadeo).
// Best-effort: si falla, se sigue mostrando todo con la estrella vacia.
async function cargarFavoritosSet() {
  const email = emailFavoritos();
  if (!email) return new Set();
  try {
    const resp = await fetch("/api/favoritos?email=" + encodeURIComponent(email));
    const data = await resp.json();
    return new Set((data.favoritos || []).map((p) => p.nombre));
  } catch (e) {
    return new Set();
  }
}

function marcadorFavoritoHtml(nombreProducto, favoritosSet) {
  const activo = Boolean(favoritosSet && favoritosSet.has(nombreProducto));
  return `
    <button type="button" class="btn-favorito${activo ? " activo" : ""}" aria-label="Marcar como favorito" aria-pressed="${activo}">
      <svg viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 21 12 17.77 5.82 21 7 14.14l-5-4.87 6.91-1.01L12 2z"/></svg>
    </button>
  `;
}

// Conecta el click de la estrella de una tarjeta ya armada: guarda/saca el
// favorito en el servidor y actualiza el dibujo. "opciones.quitarSiNoMarcado"
// se usa en /favoritos (favoritos.js) -- ahi sacar el favorito tiene que
// sacar la tarjeta entera, no solo apagar la estrella.
function conectarBotonFavorito(card, rec, opciones) {
  const btn = card.querySelector(".btn-favorito");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    const email = emailFavoritos();
    if (!email) return;

    // Rebote + brillo al toque, independiente de la respuesta del servidor
    // (se siente al instante, no despues del fetch) -- se saca sola al
    // terminar la animacion CSS (favorito-pulso, style.css).
    const svg = btn.querySelector("svg");
    if (svg) {
      svg.classList.remove("pulso");
      void svg.offsetWidth;
      svg.classList.add("pulso");
      svg.addEventListener("animationend", () => svg.classList.remove("pulso"), { once: true });
    }

    btn.disabled = true;
    try {
      const resp = await fetch("/api/favoritos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, producto: rec }),
      });
      const data = await resp.json();
      const marcado = Boolean(data.marcado);
      btn.classList.toggle("activo", marcado);
      btn.setAttribute("aria-pressed", String(marcado));
      if (!marcado && opciones && opciones.quitarSiNoMarcado) {
        card.remove();
      }
    } catch (e) {
      // Silencioso a proposito -- best-effort, igual que registrarInteresProducto.
    } finally {
      btn.disabled = false;
    }
  });
}

// --- Vista previa rapida: fotos + descripcion + "Ir a la tienda" ----------
// Si el producto ya tiene catalogo real (rec.fotos, set completo sacado
// directo de la ficha de la tienda -- ver construir_catalogo_real.py),
// se muestran esas tal cual. Si no, es un producto todavia con imagen
// ilustrativa (SVG mock): 3 "fotos" son el mismo dibujo (rec.imagen) mas
// 2 variantes generadas (sufijos "-trasera"/"-detalle", ver
// generar_imagenes_prendas.py), derivadas del nombre de archivo.
function imagenesPreview(rec) {
  if (rec.fotos && rec.fotos.length > 0) return rec.fotos;
  if (!rec.imagen) return [];
  if (!rec.imagen.endsWith(".svg")) return [rec.imagen];
  const base = rec.imagen.slice(0, -4);
  return [rec.imagen, `${base}-trasera.svg`, `${base}-detalle.svg`];
}

// --- Carrito local (2026-08-27) -------------------------------------------
// Arquitectura minima para que "Agregar al carrito" sea una accion real, no
// cosmetica -- guarda en localStorage (por dispositivo, igual que el resto
// de las conveniencias de este tipo en la app). El checkout real (pago,
// confirmacion de pedido) es un trabajo aparte; esto solo deja la prenda
// elegida (con su talla/color) guardada y lista para cuando ese flujo
// exista, sin inventar un pago que todavia no se puede procesar.
const CARRITO_KEY = "kolizionCarrito";

function leerCarrito() {
  try {
    return JSON.parse(localStorage.getItem(CARRITO_KEY)) || [];
  } catch (e) {
    return [];
  }
}

function agregarAlCarrito(item) {
  try {
    const carrito = leerCarrito();
    carrito.push(item);
    localStorage.setItem(CARRITO_KEY, JSON.stringify(carrito));
  } catch (e) {
    // Silencioso a proposito -- best-effort, igual que favoritos.
  }
}

// --- Resenas de producto (2026-08-27) --------------------------------------
// Nunca inventadas -- si /api/resenas devuelve total=0 (ningun comprador
// dejo una todavia), se muestra el empty state en vez de datos de relleno.
function _estrellasHtml(promedio) {
  const llenas = Math.round(promedio || 0);
  let html = "";
  for (let i = 1; i <= 5; i++) html += i <= llenas ? "★" : "☆";
  return html;
}

function _renderResenas(resumen) {
  const resumenEl = document.getElementById("vp-resenas-resumen");
  const listaEl = document.getElementById("vp-resenas-lista");
  const estrellasResumen = document.getElementById("vp-estrellas-resumen");
  if (!resumenEl || !listaEl) return;

  if (!resumen || !resumen.total) {
    resumenEl.innerHTML = "";
    listaEl.innerHTML = `<p class="vp-resenas-vacio">Este producto todavía no tiene reseñas.</p>`;
    if (estrellasResumen) estrellasResumen.classList.add("oculto");
    return;
  }

  if (estrellasResumen) {
    estrellasResumen.classList.remove("oculto");
    const plural = resumen.total === 1 ? "reseña" : "reseñas";
    estrellasResumen.innerHTML = `<span class="vp-estrellas">${_estrellasHtml(resumen.promedio)}</span> ${resumen.promedio} (${resumen.total} ${plural})`;
  }

  const barras = [5, 4, 3, 2, 1]
    .map((n) => {
      const cantidad = (resumen.distribucion || {})[String(n)] || 0;
      const pct = resumen.total ? Math.round((cantidad / resumen.total) * 100) : 0;
      return `<div class="vp-barra-estrella"><span>${n}★</span><div class="vp-barra-fondo"><div class="vp-barra-relleno" style="width:${pct}%"></div></div><span>${cantidad}</span></div>`;
    })
    .join("");
  resumenEl.innerHTML = `
    <div class="vp-estrellas-grande">${_estrellasHtml(resumen.promedio)}</div>
    <div class="vp-resumen-numero">${resumen.promedio} de 5 · ${resumen.total} ${resumen.total === 1 ? "reseña" : "reseñas"}</div>
    <div class="vp-barras">${barras}</div>
  `;

  listaEl.innerHTML = (resumen.items || [])
    .map(
      (r) => `
    <div class="vp-resena">
      <div class="vp-resena-cabecera">
        <span class="vp-resena-usuario">${r.usuario || "Usuario KOLIZION"}</span>
        <span class="vp-estrellas">${_estrellasHtml(r.estrellas)}</span>
        ${r.compra_verificada ? `<span class="vp-compra-verificada">Compra verificada</span>` : ""}
      </div>
      <p class="vp-resena-comentario">${r.comentario || ""}</p>
      <span class="vp-resena-fecha">${r.fecha || ""}</span>
    </div>
  `
    )
    .join("");
}

function _cargarResenas(nombre) {
  fetch(`/api/resenas?nombre=${encodeURIComponent(nombre || "")}`)
    .then((r) => r.json())
    .then(_renderResenas)
    .catch(() => _renderResenas(null));
}

function _cargarEnvioTienda(tienda) {
  const det = document.getElementById("vp-det-envio");
  const texto = document.getElementById("vp-envio-texto");
  if (!det || !texto) return;
  fetch(`/api/envio_tienda?tienda=${encodeURIComponent(tienda || "")}`)
    .then((r) => r.json())
    .then((data) => {
      if (data.texto) {
        texto.textContent = data.texto;
        det.classList.remove("oculto");
      } else {
        det.classList.add("oculto");
      }
    })
    .catch(() => det.classList.add("oculto"));
}

function _textoDetallesProducto(rec) {
  const partes = [];
  if (rec.corte) partes.push(`Corte: ${rec.corte}`);
  if (rec.subtipo) partes.push(`Subtipo: ${rec.subtipo}`);
  if (rec.manga) partes.push(`Manga: ${rec.manga}`);
  if (rec.largo) partes.push(`Largo: ${rec.largo}`);
  if (rec.capucha) partes.push(`Capucha: ${rec.capucha}`);
  if (rec.cierre) partes.push(`Cierre: ${rec.cierre}`);
  return partes.join(" · ");
}

// --- Selector de talla/color ------------------------------------------------
// Usa tallas_variantes (disponible Y agotada, real de Shopify -- ver
// _variantes_talla_shopify en construir_catalogo_real.py) cuando existe;
// si el producto no la tiene, cae a tallas_disponibles como antes (rango
// de la tienda, sin distinguir agotado -- es lo unico que hay para esas).
function _opcionesTalla(rec) {
  if (rec.tallas_variantes && rec.tallas_variantes.length) return rec.tallas_variantes;
  if (rec.tallas_disponibles && rec.tallas_disponibles.length) {
    return rec.tallas_disponibles.map((t) => ({ talla: t, disponible: true }));
  }
  return [];
}

function _renderChipsTalla(rec) {
  const bloque = document.getElementById("vp-selector-talla");
  const cont = document.getElementById("vp-chips-talla");
  const opciones = _opcionesTalla(rec);

  // Talla unica (ej. gorros de lana, ver construir_producto en
  // construir_catalogo_real.py) -- con 1 sola opcion no hay nada que
  // "elegir", mostrar el selector solo confundia (2026-08-30, bug
  // reportado: decia "Elige una talla" pero no se podia tocar nada).
  if (!rec.oficial || !opciones.length || (opciones.length === 1 && opciones[0].disponible)) {
    bloque.classList.add("oculto");
    if (opciones.length === 1 && opciones[0].disponible) vpTallaElegida = opciones[0].talla;
    return;
  }

  bloque.classList.remove("oculto");
  // Talla destacada (2026-09-07, pedido del usuario): la que estimar_tallas()
  // calcula como "principal" segun tu cuerpo, ya desplazada por tu
  // preferencia de ajuste/calce si la configuraste en /perfil (Ajustado/
  // Holgado). Solo se resalta y se preselecciona si esa talla existe Y esta
  // disponible en ESTE producto real -- nunca se inventa ni se oculta
  // ninguna otra opcion, el usuario igual puede elegir cualquier chip.
  const destacada = opciones.find((o) => o.disponible && o.talla === rec.talla_destacada);
  cont.innerHTML = opciones
    .map((o) => {
      const esDestacada = destacada && o.talla === destacada.talla;
      const clases = ["vp-chip", o.disponible ? "" : "agotada", esDestacada ? "activa sugerida" : ""]
        .filter(Boolean)
        .join(" ");
      const etiqueta = esDestacada ? `${o.talla} · recomendada` : o.talla;
      return `<button type="button" class="${clases}" data-talla="${o.talla}" ${o.disponible ? "" : "disabled"}>${etiqueta}</button>`;
    })
    .join("");
  if (destacada) vpTallaElegida = destacada.talla;
  cont.querySelectorAll(".vp-chip:not(.agotada)").forEach((btn) => {
    btn.addEventListener("click", () => {
      cont.querySelectorAll(".vp-chip").forEach((b) => b.classList.remove("activa"));
      btn.classList.add("activa");
      vpTallaElegida = btn.dataset.talla;
      _actualizarCta();
    });
  });
}

// Colores: casi ningun producto del catalogo tiene hoy este dato separado
// del nombre (ver docs/catalogo_real.md) -- el bloque queda oculto para
// esos, "si corresponde" tal como se pidio, sin inventar un color.
function _renderChipsColor(rec) {
  const bloque = document.getElementById("vp-selector-color");
  const cont = document.getElementById("vp-chips-color");

  if (!rec.colores_disponibles || !rec.colores_disponibles.length) {
    bloque.classList.add("oculto");
    return;
  }

  bloque.classList.remove("oculto");
  cont.innerHTML = rec.colores_disponibles.map((c) => `<button type="button" class="vp-chip" data-color="${c}">${c}</button>`).join("");
  cont.querySelectorAll(".vp-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      cont.querySelectorAll(".vp-chip").forEach((b) => b.classList.remove("activa"));
      btn.classList.add("activa");
      vpColorElegido = btn.dataset.color;
    });
  });
}

function _actualizarCta() {
  const rec = vpRecActual;
  const link = document.getElementById("vp-link");
  const nota = document.getElementById("vp-cta-nota");
  if (!rec || !link) return;

  if (!rec.oficial) {
    link.textContent = "Ir a la tienda";
    link.classList.remove("boton-proximamente");
    link.removeAttribute("aria-disabled");
    nota.classList.add("oculto");
    return;
  }

  if (!productoTieneStock(rec)) {
    link.textContent = "Próximamente";
    link.classList.add("boton-proximamente");
    link.setAttribute("aria-disabled", "true");
    nota.textContent = "Sin stock por ahora.";
    nota.classList.remove("oculto");
    return;
  }

  link.classList.remove("boton-proximamente");
  link.removeAttribute("aria-disabled");
  const necesitaTalla = !document.getElementById("vp-selector-talla").classList.contains("oculto");
  link.textContent = necesitaTalla && !vpTallaElegida ? "Elige una talla" : "Agregar al carrito";
  nota.classList.add("oculto");
}

let vpRecActual = null;
let vpTallaElegida = null;
let vpColorElegido = null;
let vpImagenes = [];
let vpIndice = 0;

// Pinta la foto en el indice dado en TODOS lados que la muestran (principal,
// miniatura activa, y el zoom si esta abierto) -- un solo punto de verdad
// para que las flechitas de la galeria y las del zoom naveguen lo mismo.
function _pintarImagenVp(indice) {
  if (!vpImagenes.length) return;
  vpIndice = (indice + vpImagenes.length) % vpImagenes.length;
  const src = vpImagenes[vpIndice];
  document.getElementById("vp-imagen-principal").src = src;
  document.querySelectorAll("#vp-miniaturas .vp-miniatura").forEach((b, i) => {
    b.classList.toggle("activa", i === vpIndice);
  });
  const zoomImg = document.getElementById("zoom-imagen");
  if (zoomImg) zoomImg.src = src;
}

function abrirVistaPrevia(rec) {
  vpRecActual = rec;
  vpTallaElegida = null;
  vpColorElegido = null;
  vpImagenes = imagenesPreview(rec);
  vpIndice = 0;

  const miniaturas = document.getElementById("vp-miniaturas");
  const hayVarias = vpImagenes.length > 1;
  document.getElementById("vp-flecha-izq").classList.toggle("oculto", !hayVarias);
  document.getElementById("vp-flecha-der").classList.toggle("oculto", !hayVarias);

  miniaturas.innerHTML = vpImagenes
    .map((src, i) => `<button type="button" class="vp-miniatura${i === 0 ? " activa" : ""}" data-src="${src}"><img src="${src}" alt=""></button>`)
    .join("");
  miniaturas.querySelectorAll(".vp-miniatura").forEach((btn, i) => {
    btn.addEventListener("click", () => _pintarImagenVp(i));
  });
  _pintarImagenVp(0);

  document.getElementById("vp-tienda").textContent = rec.tienda || "";
  document.getElementById("vp-nombre").textContent = rec.nombre || "";
  document.getElementById("vp-precio").textContent = rec.precio || "";
  document.getElementById("vp-descripcion").textContent = rec.descripcion || rec.razon || "";
  // Insignia "Marca de autor" (2026-08-19): identidad de diseño propia,
  // no depende de que la tienda lo declare -- lo define KOLIZION al
  // cargar cada tienda piloto (ver CLAUDE.md).
  document.getElementById("vp-marca-autor").classList.toggle("oculto", !rec.marca_autor);
  document.getElementById("vp-unisex").classList.toggle("oculto", rec.genero !== "unisex");
  const confianza = rec.confianza;
  const tieneConfianza = confianza && typeof confianza.nivel === "number";
  const badgeConfianza = document.getElementById("vp-confianza");
  badgeConfianza.textContent = tieneConfianza ? `Nivel ${confianza.nivel}` : "";
  badgeConfianza.title = tieneConfianza ? `Confianza KOLIZION\n${insigniaConfianzaTitulo(confianza)}` : "";
  badgeConfianza.classList.toggle("oculto", !tieneConfianza);
  document.getElementById("vp-det-confianza").classList.toggle("oculto", !tieneConfianza);
  if (tieneConfianza) {
    // 2026-09-07: se listan los 5 criterios siempre, cumplidos y no
    // verificados (mismo criterio que insigniaConfianzaTitulo -- ver
    // comentario ahi).
    document.getElementById("vp-confianza-lista").innerHTML = Object.entries(CONFIANZA_ETIQUETAS)
      .map(([clave, texto]) => (
        confianza[clave]
          ? `<li class="vp-confianza-si">✓ ${texto}</li>`
          : `<li class="vp-confianza-no">○ ${texto} (no verificado todavía)</li>`
      ))
      .join("");
  }
  // Sello "por que es tendencia" (2026-08-29): solo para productos que
  // vienen de la fila Tendencias (rec.esTendencia, ver vitrina.js) -- no se
  // confunde con la "razon" de match de una busqueda normal, que sigue
  // yendo solo a la Descripcion (linea de abajo).
  const badgeTendencia = document.getElementById("vp-tendencia");
  badgeTendencia.textContent = rec.esTendencia && rec.razon ? `🔥 ${rec.razon}` : "";
  badgeTendencia.classList.toggle("oculto", !(rec.esTendencia && rec.razon));

  const detalles = _textoDetallesProducto(rec);
  document.getElementById("vp-det-detalles").classList.toggle("oculto", !detalles);
  document.getElementById("vp-detalles").textContent = detalles;

  const materialTexto = [rec.material ? `Material: ${rec.material}` : "", rec.gramaje_texto || ""].filter(Boolean).join(" · ");
  document.getElementById("vp-det-materiales").classList.toggle("oculto", !materialTexto);
  document.getElementById("vp-materiales").textContent = materialTexto;

  _renderChipsTalla(rec);
  _renderChipsColor(rec);
  _actualizarCta();
  _cargarResenas(rec.nombre);
  _cargarEnvioTienda(rec.tienda);

  document.getElementById("modal-vista-previa").classList.remove("oculto");
}

function cerrarVistaPrevia() {
  document.getElementById("modal-vista-previa").classList.add("oculto");
}

// Zoom de foto (2026-08-28): las fotos suelen ser de un modelo con la
// prenda puesta, asi que hace falta acercarse a la prenda misma. Tocar la
// foto principal abre esto a pantalla completa; adentro, tocar la foto de
// nuevo agranda/achica (transform: scale, ver style.css) -- si esta
// agrandada, el contenedor tiene scroll propio para desplazarse (funciona
// con el dedo en celular y con el mouse/trackpad en compu).
function zoomImagenAbrir() {
  if (!vpImagenes.length) return;
  const zoomImg = document.getElementById("zoom-imagen");
  zoomImg.src = vpImagenes[vpIndice];
  zoomImg.classList.remove("zoom-agrandada");
  const hayVarias = vpImagenes.length > 1;
  document.getElementById("vp-zoom-flecha-izq").classList.toggle("oculto", !hayVarias);
  document.getElementById("vp-zoom-flecha-der").classList.toggle("oculto", !hayVarias);
  document.getElementById("modal-zoom-imagen").classList.remove("oculto");
}

function zoomImagenCerrar() {
  document.getElementById("modal-zoom-imagen").classList.add("oculto");
  document.getElementById("zoom-imagen").classList.remove("zoom-agrandada");
}

// Conecta el boton "Vista previa rapida" Y el "Agregar al carrito" de la
// tarjeta (cuando el producto es oficial con stock -- ver
// botonAccionProductoHtml) de una tarjeta ya armada: ambos abren la misma
// ficha completa, elegir talla/color siempre pasa por ahi. El modal
// (_vista_previa.html) no vive en todas las paginas (index.html/perfil.html
// no tienen tarjetas de producto) -- por eso el listener de cerrar se
// engancha con guard mas abajo, no aca arriba.
function conectarVistaPrevia(card, rec) {
  const btn = card.querySelector(".btn-vista-previa");
  if (btn) btn.addEventListener("click", () => abrirVistaPrevia(rec));
  const btnCarrito = card.querySelector(".btn-abrir-ficha-carrito");
  if (btnCarrito) btnCarrito.addEventListener("click", () => abrirVistaPrevia(rec));
}

// --- Animacion antes de ir a una tienda externa (estilo apps grandes de
// e-commerce): "Te llevamos a {tienda}..." + cuenta regresiva corta, y
// recien ahi se abre el link real en una pestaña nueva -- mismo
// comportamiento de siempre (target="_blank"), solo que ahora el clic no
// navega al toque. Rapida a proposito (4 pasos x 280ms = ~1.1s) para no
// alargar la espera mas de lo necesario.
const REDIRECCION_PASOS = ["3", "2", "1", "¡Vamos! 🐶"];
const REDIRECCION_PASO_MS = 280;

function abrirEnlaceConAnimacion(url, nombreTienda) {
  // Cuenta obligatoria para "comprar" (2026-08-24, ver docs/cuentas.md) --
  // este es el punto unico por donde pasan las 3 tarjetas de producto del
  // catalogo mock (resultados, vitrina, vista previa rapida). El otro
  // punto (tiendas piloto reales, /ir/<tienda_id>) se bloquea del lado del
  // servidor porque ese link no pasa por aca. window.KOLIZION_LOGUEADO lo
  // define _barra_nav.html en cada pagina.
  if (!window.KOLIZION_LOGUEADO) {
    const destino = window.location.pathname + window.location.search;
    window.location.href = `/login?siguiente=${encodeURIComponent(destino)}`;
    return;
  }

  const modal = document.getElementById("modal-redireccion");
  if (!modal || !url || url === "#") {
    // Defensivo: si la pagina no incluye el modal, o no hay link real, se
    // sigue abriendo directo en vez de dejar el clic sin efecto.
    if (url && url !== "#") window.open(url, "_blank", "noopener");
    return;
  }

  document.getElementById("redireccion-texto").textContent =
    nombreTienda ? `Te llevamos a ${nombreTienda}...` : "Te llevamos a la tienda...";
  const cuenta = document.getElementById("redireccion-cuenta");
  let paso = 0;

  // Reinicia "a mano" la animacion CSS del numero (forzando un reflow con
  // offsetWidth) para que cada paso vuelva a hacer el "pop" -- si solo se
  // cambiara el texto, la animacion (que ya corrio al mostrar el modal) no
  // se repetiria sola.
  function pintarPaso() {
    cuenta.textContent = REDIRECCION_PASOS[paso];
    cuenta.style.animation = "none";
    void cuenta.offsetWidth;
    cuenta.style.animation = "";
  }

  pintarPaso();
  modal.classList.remove("oculto");

  const intervalo = setInterval(() => {
    paso++;
    if (paso < REDIRECCION_PASOS.length) {
      pintarPaso();
      return;
    }
    clearInterval(intervalo);
    window.open(url, "_blank", "noopener");
    modal.classList.add("oculto");
  }, REDIRECCION_PASO_MS);
}

document.addEventListener("DOMContentLoaded", () => {
  const btnCerrarVP = document.getElementById("btn-cerrar-vista-previa");
  if (btnCerrarVP) btnCerrarVP.addEventListener("click", cerrarVistaPrevia);

  const flechaIzq = document.getElementById("vp-flecha-izq");
  const flechaDer = document.getElementById("vp-flecha-der");
  if (flechaIzq) flechaIzq.addEventListener("click", () => _pintarImagenVp(vpIndice - 1));
  if (flechaDer) flechaDer.addEventListener("click", () => _pintarImagenVp(vpIndice + 1));

  const imagenPrincipal = document.getElementById("vp-imagen-principal");
  if (imagenPrincipal) imagenPrincipal.addEventListener("click", zoomImagenAbrir);

  const zoomImg = document.getElementById("zoom-imagen");
  const btnCerrarZoom = document.getElementById("btn-cerrar-zoom");
  const modalZoom = document.getElementById("modal-zoom-imagen");
  if (zoomImg) zoomImg.addEventListener("click", () => zoomImg.classList.toggle("zoom-agrandada"));
  if (btnCerrarZoom) btnCerrarZoom.addEventListener("click", zoomImagenCerrar);
  if (modalZoom) modalZoom.addEventListener("click", (e) => { if (e.target === modalZoom) zoomImagenCerrar(); });
  const zoomFlechaIzq = document.getElementById("vp-zoom-flecha-izq");
  const zoomFlechaDer = document.getElementById("vp-zoom-flecha-der");
  if (zoomFlechaIzq) zoomFlechaIzq.addEventListener("click", () => { _pintarImagenVp(vpIndice - 1); zoomImagenAbrir(); });
  if (zoomFlechaDer) zoomFlechaDer.addEventListener("click", () => { _pintarImagenVp(vpIndice + 1); zoomImagenAbrir(); });

  const linkVP = document.getElementById("vp-link");
  if (linkVP) {
    linkVP.addEventListener("click", async (e) => {
      e.preventDefault();
      const rec = vpRecActual;
      if (!rec) return;

      if (!rec.oficial) {
        registrarInteresProducto(rec);
        abrirEnlaceConAnimacion(rec.link, rec.tienda);
        return;
      }
      if (linkVP.classList.contains("boton-proximamente")) return; // sin stock
      const necesitaTalla = !document.getElementById("vp-selector-talla").classList.contains("oculto");
      if (necesitaTalla && !vpTallaElegida) return; // boton dice "Elige una talla"

      // Cuenta obligatoria para "comprar" (mismo criterio que
      // abrirEnlaceConAnimacion, ver docs/cuentas.md) -- agregar al
      // carrito es intencion real de compra, no una accion anonima.
      if (!window.KOLIZION_LOGUEADO) {
        const destino = window.location.pathname + window.location.search;
        window.location.href = `/login?siguiente=${encodeURIComponent(destino)}`;
        return;
      }

      const tallaAlMomento = vpTallaElegida;
      const puedeSeguir = await _revalidarStockAntesDeAgregar(rec, tallaAlMomento, linkVP);
      if (!puedeSeguir || vpRecActual !== rec) return;

      agregarAlCarrito({
        nombre: rec.nombre,
        tienda: rec.tienda,
        precio: rec.precio,
        talla: vpTallaElegida,
        color: vpColorElegido,
        link: rec.link,
        imagen: rec.imagen,
        fecha: new Date().toISOString(),
      });
      const textoOriginal = "Agregar al carrito";
      linkVP.textContent = "✓ Agregado al carrito";
      setTimeout(() => {
        if (vpRecActual === rec) linkVP.textContent = textoOriginal;
      }, 1500);
    });
  }
});

// Revalidacion en vivo al momento de comprar (2026-09-07, pedido del
// usuario): antes de guardar en el carrito, se le pregunta a la tienda real
// si esa talla puntual sigue disponible -- "estamos verificando..." mientras
// dura la consulta real (no un timer inventado). Si la plataforma de esa
// tienda no tiene forma de verificar en vivo hoy (ver servicio_stock_live.py
// -- ej. RAPT, que esta con la tienda desactivada), la respuesta llega con
// verificado:false y se sigue igual que antes (fail-open: nunca bloquea una
// compra solo porque no se pudo reconfirmar).
async function _revalidarStockAntesDeAgregar(rec, tallaPedida, linkVP) {
  const necesitaTalla = !document.getElementById("vp-selector-talla").classList.contains("oculto");
  if (!necesitaTalla) return true; // talla unica -- nada que revalidar por talla

  const textoOriginal = linkVP.textContent;
  linkVP.textContent = "Verificando disponibilidad...";
  linkVP.setAttribute("aria-disabled", "true");

  const controlador = new AbortController();
  const timeoutId = setTimeout(() => controlador.abort(), 12000);
  let resultado = null;
  try {
    const resp = await fetch("/api/verificar_stock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ producto_id: rec.id, talla: tallaPedida || "" }),
      signal: controlador.signal,
    });
    resultado = await resp.json();
  } catch (err) {
    // Timeout o falla de red al verificar: no bloquea la compra, sigue con
    // el dato que ya se tenia (mismo criterio best-effort que resenas/envio).
  } finally {
    clearTimeout(timeoutId);
  }

  if (vpRecActual !== rec) return false; // el usuario cerro/cambio de ficha mientras se verificaba

  if (!resultado || !resultado.verificado) {
    linkVP.removeAttribute("aria-disabled");
    linkVP.textContent = textoOriginal;
    return true; // no se pudo confirmar nada nuevo -- se sigue como antes
  }

  if (resultado.tallas_variantes) {
    rec.tallas_variantes = resultado.tallas_variantes;
    rec.tallas_disponibles = resultado.tallas_disponibles;
  } else if (resultado.talla_confirmada === false && resultado.disponible === false) {
    // Solo se supo que el producto ENTERO se agoto (ej. IPREX, sin stock
    // separado por talla) -- se refleja en todas las tallas reales.
    rec.tallas_disponibles = [];
    if (rec.tallas_variantes) {
      rec.tallas_variantes = rec.tallas_variantes.map((v) => ({ ...v, disponible: false }));
    }
  }

  linkVP.removeAttribute("aria-disabled");
  if (!resultado.disponible) {
    vpTallaElegida = null;
    _renderChipsTalla(rec);
    _actualizarCta();
    alert(`La talla "${tallaPedida}" se agotó recién en la tienda -- elige otra opción disponible.`);
    return false;
  }
  linkVP.textContent = textoOriginal;
  return true;
}

// Grilla estilo Pinterest/Mercado Libre (2026-08-28, reemplaza las tarjetas
// grandes apiladas): cada cuadradito solo muestra foto + nombre + precio --
// tocarlo abre la ficha completa (abrirVistaPrevia, mismo modal de siempre
// con todas las fotos, descripcion y el boton real de compra/"ir a la
// tienda"). Ya no hay boton de accion a nivel tarjeta.
function renderResultados(contenedorId, recomendaciones, opciones = {}) {
  const contenedor = document.getElementById(contenedorId);
  const email = emailFavoritos();
  const favoritosSet = opciones.favoritosSet || new Set();
  for (const rec of recomendaciones) {
    const card = document.createElement("div");
    card.className = "resultado-card resultado-card-mini";
    card.innerHTML = `
      ${email ? marcadorFavoritoHtml(rec.nombre, favoritosSet) : ""}
      ${rec.imagen ? `<img src="${rec.imagen}" alt="${esImagenIlustrativa(rec.imagen) ? "Ilustración de referencia (no es una foto real del producto)" : rec.nombre}" class="imagen-producto">` : ""}
      ${rec.imagen && esImagenIlustrativa(rec.imagen) ? `<span class="badge-ilustrativa">Ilustrativa</span>` : ""}
      ${rec.genero === "unisex" ? `<span class="badge-unisex">Unisex</span>` : ""}
      <div class="resultado-card-mini-info">
        <h3>${rec.nombre}</h3>
        ${rec.precio ? `<p class="precio">${rec.precio}</p>` : ""}
        ${insigniaConfianzaHtml(rec)}
      </div>
    `;
    card.addEventListener("click", () => abrirVistaPrevia(rec));
    if (email) {
      conectarBotonFavorito(card, rec, opciones);
      const btnFavorito = card.querySelector(".btn-favorito");
      if (btnFavorito) btnFavorito.addEventListener("click", (e) => e.stopPropagation());
    }
    contenedor.appendChild(card);
  }
}

// Cuanto dura el flash de "encontramos algo" antes de revelar resultados.
// Sale del mismo minMs de siempre (no se suma aparte) -- si la busqueda real
// tarda menos que minMs, el tiempo total que ve el usuario no cambia.
const CARGANDO_FLASH_MS = 500;

// Llama a /api/recommend mostrando el logo pulsando + frases rotativas de
// #cargando, esperando un minimo de minMs (3 segundos por defecto) aunque
// la respuesta real llegue antes -- asi la animacion siempre se alcanza a
// ver. Si la respuesta trae resultados, el logo se ilumina con "Encontramos
// algo" un instante (CARGANDO_FLASH_MS) antes de ocultar todo. Devuelve el
// JSON ya parseado, o lanza un error si algo fallo.
async function buscarConAnimacion(payload, minMs = 3000) {
  const cargando = document.getElementById("cargando");
  const cargandoTexto = document.getElementById("cargando-texto");

  let indiceFrase = 0;
  cargandoTexto.textContent = FRASES_CARGA[0];
  cargando.classList.remove("cargando-exito");
  cargando.classList.remove("oculto");
  const intervalo = setInterval(() => {
    indiceFrase = (indiceFrase + 1) % FRASES_CARGA.length;
    cargandoTexto.textContent = FRASES_CARGA[indiceFrase];
  }, 900);

  try {
    // Promise.all espera lo mas lento de los dos: la busqueda real, o el
    // minimo de animacion (si la busqueda es mas rapida, igual se espera
    // para que la animacion se alcance a ver).
    const [resp] = await Promise.all([
      fetch("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
      esperar(Math.max(minMs - CARGANDO_FLASH_MS, 0)),
    ]);
    if (!resp.ok) throw new Error("Error del servidor: " + resp.status);
    const data = await resp.json();

    clearInterval(intervalo);
    const hayResultados =
      (data.recomendaciones && data.recomendaciones.length > 0) ||
      (data.alternativas && data.alternativas.length > 0);
    if (hayResultados) {
      cargando.classList.add("cargando-exito");
      await esperar(CARGANDO_FLASH_MS);
    }
    return data;
  } finally {
    clearInterval(intervalo);
    cargando.classList.add("oculto");
    cargando.classList.remove("cargando-exito");
  }
}

// --- Guia de bienvenida: tour de 8 pantallas (2026-09-02, actualizado con
// las funciones nuevas -- se saco la pantalla de Koko a pedido del
// usuario). Vive aca (no en script.js) para funcionar en las 4 paginas --
// se abre de 2 formas: automatica la primera vez que se crea el perfil
// (script.js muestra antes #modal-onboarding-pregunta y, si el usuario
// dice que si, llama a abrirTourOnboarding) y manual en cualquier momento
// con el icono fijo "#btn-abrir-guia" (_guia_bienvenida.html, en las 4
// paginas).
const ONBOARDING_KEY = "kolizionOnboardingVisto";
const TOUR_SLIDES_TOTAL = 8;
let indiceTour = 0;
// Solo queda true si el tour se abrio desde la pregunta de bienvenida (no
// desde una reapertura manual con el icono fijo) -- controla si al cerrar
// hay que seguir con el flujo de perfil nuevo (evento "onboarding:completado",
// ver script.js) o simplemente cerrar sin tocar nada mas de la pagina.
let huboPreguntaPrevia = false;

function mostrarSlideTour(indice) {
  document.querySelectorAll(".tour-slide").forEach((el) => {
    el.classList.toggle("oculto", Number(el.dataset.slide) !== indice);
  });
  document.querySelectorAll(".tour-punto").forEach((el) => {
    el.classList.toggle("activo", Number(el.dataset.punto) === indice);
  });
  // Al cambiar de pantalla se pausa y esconde cualquier ejemplo en video
  // que haya quedado abierto (boton "No entendi", ver mas abajo).
  document.querySelectorAll(".video-ejemplo-tour").forEach((video) => {
    video.pause();
    video.classList.add("oculto");
  });
  document.getElementById("btn-tour-anterior").classList.toggle("oculto", indice === 0);
  document.getElementById("btn-tour-siguiente").textContent =
    indice === TOUR_SLIDES_TOTAL - 1 ? "Entendido, ¡vamos!" : "Siguiente";
}

function abrirTourOnboarding() {
  const pregunta = document.getElementById("modal-onboarding-pregunta");
  huboPreguntaPrevia = Boolean(pregunta && !pregunta.classList.contains("oculto"));
  if (pregunta) pregunta.classList.add("oculto");
  indiceTour = 0;
  mostrarSlideTour(0);
  document.getElementById("modal-onboarding-tour").classList.remove("oculto");
}

function cerrarTourOnboarding() {
  localStorage.setItem(ONBOARDING_KEY, "1");
  document.getElementById("modal-onboarding-tour").classList.add("oculto");
  if (huboPreguntaPrevia) {
    huboPreguntaPrevia = false;
    document.dispatchEvent(new CustomEvent("onboarding:completado"));
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("btn-tour-anterior").addEventListener("click", () => {
    if (indiceTour > 0) {
      indiceTour--;
      mostrarSlideTour(indiceTour);
    }
  });

  document.getElementById("btn-tour-siguiente").addEventListener("click", () => {
    if (indiceTour < TOUR_SLIDES_TOTAL - 1) {
      indiceTour++;
      mostrarSlideTour(indiceTour);
    } else {
      cerrarTourOnboarding();
    }
  });

  document.getElementById("btn-cerrar-tour").addEventListener("click", cerrarTourOnboarding);
  document.getElementById("btn-abrir-guia").addEventListener("click", abrirTourOnboarding);

  // Boton "No entendi" de cada pantalla del tour: carga el video de
  // ejemplo (grabacion real de la app, no animacion inventada) recien al
  // tocarlo, para no descargarlo si nadie lo pide.
  document.querySelectorAll(".btn-no-entendi").forEach((boton) => {
    boton.addEventListener("click", () => {
      const video = boton.nextElementSibling;
      if (!video || !video.classList.contains("video-ejemplo-tour")) return;
      if (!video.src) video.src = boton.dataset.video;
      video.classList.remove("oculto");
      video.play();
    });
  });
});

// Corre la busqueda (con la animacion de carga de arriba) y, cuando
// termina, guarda el resultado y manda al usuario a /resultados -- ahi se
// ve solo el resultado, en una pagina aparte, no mezclado con el formulario.
// Vive aca (no en script.js) porque koko.js tambien la llama, y koko.js
// corre tanto en index.html como en resultados.html.
async function buscar(payload) {
  const estado = document.getElementById("estado");
  estado.textContent = "";

  try {
    const data = await buscarConAnimacion(payload);
    sessionStorage.setItem("ultimoPayload", JSON.stringify(payload));
    sessionStorage.setItem("resultados", JSON.stringify(data.recomendaciones || []));
    sessionStorage.setItem("sinTalla", String(Boolean(data.sin_talla)));
    sessionStorage.setItem("prefsBloqueantes", JSON.stringify(data.preferencias_bloqueantes || []));
    sessionStorage.setItem("avisoGorroForma", data.aviso_gorro_forma || "");
    // Marca de tiempo para los avisos "Encontramos productos para ti hace
    // un momento" (buscador y chat de Koko) -- pedido del usuario
    // (2026-08-26): que ese aviso no quede molestando indefinidamente,
    // solo mientras la busqueda sigue siendo reciente. Ver
    // hayResultadosRecientes() mas abajo.
    sessionStorage.setItem("resultadosGuardadosEn", String(Date.now()));
    window.location.href = "/resultados";
  } catch (err) {
    estado.textContent = "Algo salió mal: " + err.message;
  }
}

const VIGENCIA_AVISO_RESULTADOS_MS = 15 * 60 * 1000;

// Si hay resultados guardados en esta sesion Y siguen siendo recientes
// (menos de 15 minutos desde que se buscaron) -- usado por los avisos
// "Encontramos productos para ti hace un momento" en script.js/koko.js.
// Pasado ese tiempo, el aviso deja de mostrarse solo (no hace falta
// borrar nada a mano; "resultados"/"ultimoPayload" siguen ahi por si el
// usuario entra a /resultados directo).
function hayResultadosRecientes() {
  const guardadoEn = Number(sessionStorage.getItem("resultadosGuardadosEn") || 0);
  if (!guardadoEn || Date.now() - guardadoEn > VIGENCIA_AVISO_RESULTADOS_MS) return false;
  try {
    const guardados = JSON.parse(sessionStorage.getItem("resultados") || "[]");
    return Array.isArray(guardados) && guardados.length > 0;
  } catch (e) {
    return false;
  }
}

