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

function abrirVistaPrevia(rec) {
  const imagenes = imagenesPreview(rec);
  const principal = document.getElementById("vp-imagen-principal");
  const miniaturas = document.getElementById("vp-miniaturas");

  principal.src = imagenes[0] || "";
  miniaturas.innerHTML = imagenes
    .map((src, i) => `<button type="button" class="vp-miniatura${i === 0 ? " activa" : ""}" data-src="${src}"><img src="${src}" alt=""></button>`)
    .join("");
  miniaturas.querySelectorAll(".vp-miniatura").forEach((btn) => {
    btn.addEventListener("click", () => {
      principal.src = btn.dataset.src;
      miniaturas.querySelectorAll(".vp-miniatura").forEach((b) => b.classList.remove("activa"));
      btn.classList.add("activa");
    });
  });

  document.getElementById("vp-tienda").textContent = rec.tienda || "";
  document.getElementById("vp-nombre").textContent = rec.nombre || "";
  document.getElementById("vp-precio").textContent = rec.precio || "";
  document.getElementById("vp-descripcion").textContent = rec.descripcion || rec.razon || "";
  // Material y gramaje (2026-08-19): el catalogo real todavia no siempre
  // los tiene -- estas filas directamente no se muestran si el producto no
  // las trae.
  const filaMaterial = document.getElementById("vp-material");
  if (rec.material) {
    filaMaterial.textContent = `Material: ${rec.material}`;
    filaMaterial.classList.remove("oculto");
  } else {
    filaMaterial.classList.add("oculto");
  }
  const filaGramaje = document.getElementById("vp-gramaje");
  if (rec.gramaje_texto) {
    filaGramaje.textContent = rec.gramaje_texto;
    filaGramaje.classList.remove("oculto");
  } else {
    filaGramaje.classList.add("oculto");
  }
  // Insignia "Marca de autor" (2026-08-19): identidad de diseño propia,
  // no depende de que la tienda lo declare -- lo define KOLIZION al
  // cargar cada tienda piloto (ver CLAUDE.md).
  document.getElementById("vp-marca-autor").classList.toggle("oculto", !rec.marca_autor);
  document.getElementById("vp-link").href = rec.link || "#";
  // El click de "Ir a la tienda" no navega directo -- lo intercepta el
  // listener de mas abajo (una sola vez, en DOMContentLoaded) y usa estas
  // 2 variables para saber a donde ir. Se guardan aca porque el boton es
  // un solo elemento fijo del modal, reusado para cualquier producto.
  vpLinkActual = rec.link || "#";
  vpTiendaActual = rec.tienda || "";

  document.getElementById("modal-vista-previa").classList.remove("oculto");
}

function cerrarVistaPrevia() {
  document.getElementById("modal-vista-previa").classList.add("oculto");
}

// Conecta el boton "Vista previa rapida" de una tarjeta ya armada. El modal
// (_vista_previa.html) no vive en todas las paginas (index.html/perfil.html
// no tienen tarjetas de producto) -- por eso el listener de cerrar se
// engancha con guard mas abajo, no aca arriba.
function conectarVistaPrevia(card, rec) {
  const btn = card.querySelector(".btn-vista-previa");
  if (btn) btn.addEventListener("click", () => abrirVistaPrevia(rec));
}

let vpLinkActual = "#";
let vpTiendaActual = "";

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

  const linkVP = document.getElementById("vp-link");
  if (linkVP) {
    linkVP.addEventListener("click", (e) => {
      e.preventDefault();
      abrirEnlaceConAnimacion(vpLinkActual, vpTiendaActual);
    });
  }
});

function renderResultados(contenedorId, recomendaciones, opciones = {}) {
  const contenedor = document.getElementById(contenedorId);
  const email = emailFavoritos();
  const favoritosSet = opciones.favoritosSet || new Set();
  for (const rec of recomendaciones) {
    const card = document.createElement("div");
    card.className = "resultado-card";
    card.innerHTML = `
      ${email ? marcadorFavoritoHtml(rec.nombre, favoritosSet) : ""}
      ${rec.imagen ? `<img src="${rec.imagen}" alt="${esImagenIlustrativa(rec.imagen) ? "Ilustración de referencia (no es una foto real del producto)" : rec.nombre}" class="imagen-producto">` : ""}
      ${rec.imagen && esImagenIlustrativa(rec.imagen) ? `<p class="aviso-imagen">Imagen ilustrativa de referencia, no es el producto real.</p>` : ""}
      <div class="tienda">${rec.tienda}</div>
      ${rec.marca_autor ? `<span class="insignia-marca-autor">✦ Marca de autor</span>` : ""}
      <h3>${rec.nombre}</h3>
      ${rec.marca ? `<p class="marca">${rec.marca}</p>` : ""}
      ${rec.precio ? `<p class="precio">${rec.precio}</p>` : ""}
      ${rec.descripcion ? `<p class="descripcion">${rec.descripcion}</p>` : ""}
      ${rec.tallas_coincidentes && rec.tallas_coincidentes.length ? `<p class="talla">Disponible en: ${rec.tallas_coincidentes.join(", ")}</p>` : ""}
      ${rec.razon ? `<p class="razon">${rec.razon}</p>` : ""}
      ${rec.imagen ? `<button type="button" class="btn-vista-previa">Vista previa rápida</button>` : ""}
      <a href="${rec.link}" target="_blank" rel="noopener">${esImagenIlustrativa(rec.imagen) ? "Ver producto (ejemplo)" : "Ver producto"}</a>
    `;
    const link = card.querySelector("a");
    if (link) {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        registrarInteresProducto(rec);
        abrirEnlaceConAnimacion(rec.link, rec.tienda);
      });
    }
    if (email) {
      conectarBotonFavorito(card, rec, opciones);
    }
    conectarVistaPrevia(card, rec);
    contenedor.appendChild(card);
  }
}

// Llama a /api/recommend mostrando el esqueleto + frases rotativas de
// #cargando, esperando un minimo de minMs (3 segundos por defecto) aunque
// la respuesta real llegue antes -- asi la animacion siempre se alcanza a
// ver. Devuelve el JSON ya parseado, o lanza un error si algo fallo.
async function buscarConAnimacion(payload, minMs = 3000) {
  const cargando = document.getElementById("cargando");
  const cargandoTexto = document.getElementById("cargando-texto");

  let indiceFrase = 0;
  cargandoTexto.textContent = FRASES_CARGA[0];
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
      esperar(minMs),
    ]);
    if (!resp.ok) throw new Error("Error del servidor: " + resp.status);
    return await resp.json();
  } finally {
    clearInterval(intervalo);
    cargando.classList.add("oculto");
  }
}

// --- Guia de bienvenida: tour de 3 pantallas (Buscador/Koko/Descubre) -----
// Vive aca (no en script.js) para funcionar en las 4 paginas -- se abre de
// 2 formas: automatica la primera vez que se crea el perfil (script.js
// muestra antes #modal-onboarding-pregunta y, si el usuario dice que si,
// llama a abrirTourOnboarding) y manual en cualquier momento con el icono
// fijo "#btn-abrir-guia" (_guia_bienvenida.html, en las 4 paginas).
const ONBOARDING_KEY = "kolizionOnboardingVisto";
const TOUR_SLIDES_TOTAL = 3;
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
    window.location.href = "/resultados";
  } catch (err) {
    estado.textContent = "Algo salió mal: " + err.message;
  }
}

