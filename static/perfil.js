// Pagina /perfil: solo MUESTRA el perfil guardado en localStorage (ver
// getPerfil en comun.js). Editar no duplica el formulario -- manda a "/"
// con ?editar_perfil=1, que script.js detecta para abrir el mismo
// formulario de perfil que ya existe, precargado (ver script.js).

const TEMA_KEY = "temaKolizion";

// El interruptor se arma aparte del resto (no depende de tener perfil
// guardado) -- se llama primero, sin importar si mas abajo se corta con el
// "return" de "sin perfil todavia".
function configurarInterruptorTema() {
  const toggle = document.getElementById("toggle-tema");
  // Default oscuro: solo desmarcado si se eligio "light" explicitamente
  // antes (mismo criterio que _tema_inline.html).
  toggle.checked = localStorage.getItem(TEMA_KEY) !== "light";
  toggle.addEventListener("change", () => {
    if (toggle.checked) {
      localStorage.setItem(TEMA_KEY, "dark");
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      localStorage.setItem(TEMA_KEY, "light");
      document.documentElement.removeAttribute("data-theme");
    }
  });
}

// etiqueta la escribimos nosotros siempre (texto fijo, ej. "Nombre"), pero
// valor puede venir de lo que el usuario escribio en el formulario de
// perfil -- se escapa igual, nunca confiar en un dato guardado solo
// porque lo puso el propio usuario (ver escaparHtml en comun.js).
function agregarFilaPerfil(resumen, etiqueta, valor) {
  const fila = document.createElement("div");
  fila.className = "perfil-fila";
  fila.innerHTML = `<span class="perfil-etiqueta">${escaparHtml(etiqueta)}</span><span class="perfil-valor">${escaparHtml(String(valor))}</span>`;
  resumen.appendChild(fila);
  return fila;
}

// Talla estimada -- mismo calculo que ya usa el buscador para filtrar
// resultados (estimar_tallas() en app.py), mostrada aca solo como
// referencia (no es un dato que el usuario haya escrito, no se puede
// editar). Si hay 2 tallas posibles (ej. peso y altura no coinciden
// exacto), se muestra la principal + la segunda opcion entre parentesis.
async function agregarTallaEstimada(resumen, perfil) {
  if (!perfil.altura && !perfil.peso) return;
  try {
    const params = new URLSearchParams({
      genero: perfil.genero || "",
      peso: perfil.peso || "",
      altura: perfil.altura || "",
    });
    const resp = await fetch("/api/estimar_talla?" + params.toString());
    const data = await resp.json();
    const tallas = data.tallas || [];
    if (tallas.length === 0) return;
    const texto = tallas.length > 1 ? `${tallas[0]} (o ${tallas[1]})` : tallas[0];
    agregarFilaPerfil(resumen, "Talla estimada", texto);
  } catch (e) {
    // Best-effort: si falla, simplemente no se muestra esta fila.
  }
}

// Preferencia de idioma de Koko -- solo se muestra si el usuario ya le
// pidio alguna vez hablar como chileno en alguna conversacion (ver
// preferencia_idioma_koko() en app.py); el default es neutro, y como
// nunca se "configura" explicitamente, no hay nada que mostrar en ese caso.
async function agregarPreferenciaIdiomaKoko(resumen, email) {
  if (!email) return;
  try {
    const resp = await fetch("/api/koko/historial_chat?email=" + encodeURIComponent(email));
    const data = await resp.json();
    if (data.preferencia_idioma === "chileno") {
      agregarFilaPerfil(resumen, "Koko te habla en", "Chileno");
    }
  } catch (e) {
    // Best-effort.
  }
}

// Mismas etiquetas que HOBBIES_CONOCIDOS/GENEROS_MUSICALES_CONOCIDOS en
// app.py -- solo para mostrar el valor guardado (ej. "musica") de forma
// legible ("Música"). Si aparece un valor viejo/desconocido (perfil
// guardado antes de este cambio, cuando el hobbie era texto libre), se
// muestra tal cual en vez de perderlo.
const ETIQUETAS_HOBBIE = {
  musica: "Música", deportes: "Deportes", relajo: "Relajo / lifestyle tranquilo",
  arte_cultura: "Arte y cultura", gaming: "Gaming", peliculas_series: "Películas y series",
  anime: "Anime",
};
const ETIQUETAS_GENERO_MUSICAL = {
  rock: "Rock", reggaeton: "Reguetón / urbano", pop: "Pop", hip_hop: "Hip-hop / rap",
  electronica: "Electrónica", indie: "Indie / alternativo",
};
const ETIQUETAS_DEPORTE = {
  gym: "Gym", futbol: "Fútbol", baseball: "Baseball", ski: "Ski",
};

// Hobbies con un segundo grupo de sub-opciones -- mismo listado que
// SUBGRUPOS_HOBBIE en script.js (acá solo hace falta para mostrar texto,
// no para pintar checkboxes).
const SUBGRUPOS_HOBBIE = [
  { hobby: "musica", nombreSub: "hobbie_musica_genero", etiquetas: ETIQUETAS_GENERO_MUSICAL },
  { hobby: "deportes", nombreSub: "hobbie_deportes_subtipo", etiquetas: ETIQUETAS_DEPORTE },
];

function textoHobbies(perfil) {
  const hobbies = Array.isArray(perfil.hobbie) ? perfil.hobbie : [];
  if (!hobbies.length) return typeof perfil.hobbie === "string" ? perfil.hobbie : "";
  const partes = hobbies.map((h) => ETIQUETAS_HOBBIE[h] || h);
  for (const { hobby, nombreSub, etiquetas } of SUBGRUPOS_HOBBIE) {
    const subvalores = perfil[nombreSub];
    if (hobbies.includes(hobby) && Array.isArray(subvalores) && subvalores.length) {
      const texto = subvalores.map((v) => etiquetas[v] || v).join(", ");
      const idx = partes.indexOf(ETIQUETAS_HOBBIE[hobby]);
      partes[idx] = `${ETIQUETAS_HOBBIE[hobby]} (${texto})`;
    }
  }
  return partes.join(", ");
}

// "Ver historial" (2026-08-26, pedido del usuario): busquedas hechas y
// productos vistos, guardados por email (mismos datos que ya se usaban
// para personalizar el prompt de Koko -- ver resumen_historial_para_prompt
// en servicio_koko.py -- ahora tambien visibles para la persona). Reusa
// agregarFilaPerfil()/.perfil-resumen para no inventar un estilo nuevo.
function formatearFechaHistorial(iso) {
  const fecha = new Date(iso);
  if (isNaN(fecha)) return "";
  return fecha.toLocaleDateString("es-CL", { day: "numeric", month: "short", year: "numeric" });
}

function textoBusquedaHistorial(b) {
  const partes = [b.tipo_prenda, b.corte, b.ocasion].filter(Boolean);
  return partes.length ? partes.join(", ") : (b.categoria || "Búsqueda");
}

function pintarHistorial(contenido, busquedas, productos) {
  contenido.innerHTML = "";
  if (!busquedas.length && !productos.length) {
    contenido.innerHTML = "<p class=\"ayuda\">Todavía no tienes búsquedas guardadas.</p>";
    return;
  }
  if (busquedas.length) {
    const titulo = document.createElement("h3");
    titulo.textContent = "Búsquedas recientes";
    contenido.appendChild(titulo);
    const lista = document.createElement("div");
    lista.className = "perfil-resumen";
    for (const b of busquedas.slice(0, 20)) {
      const fila = agregarFilaPerfil(lista, formatearFechaHistorial(b.fecha), textoBusquedaHistorial(b));
      // Solo las busquedas guardadas con "payload" (2026-08-28) se pueden
      // volver a correr -- entradas viejas (guardadas antes de este cambio)
      // no tienen como reconstruirse, asi que se quedan sin este boton en
      // vez de fingir que se puede volver a algo que no se guardo.
      if (b.payload) {
        fila.classList.add("perfil-fila-clickable");
        fila.title = "Ver estos resultados de nuevo";
        fila.addEventListener("click", () => {
          buscar({ ...b.payload, _historial_replay: true });
        });
      }
    }
    contenido.appendChild(lista);
  }
  if (productos.length) {
    const titulo2 = document.createElement("h3");
    titulo2.textContent = "Productos que viste";
    contenido.appendChild(titulo2);
    const lista2 = document.createElement("div");
    lista2.className = "perfil-resumen";
    for (const p of productos.slice(0, 20)) {
      agregarFilaPerfil(lista2, formatearFechaHistorial(p.fecha), `${p.nombre} (${p.tienda})`);
    }
    contenido.appendChild(lista2);
  }
}

// El boton (y el bloque entero) solo existe en el HTML si hay sesion real
// iniciada (ver {% if usuario %} en perfil.html) -- el email NO se manda
// desde aca, /api/historial lo saca de la sesion del servidor (mas
// confiable que cualquier dato de localStorage, ver app.py).
function configurarHistorial() {
  const btn = document.getElementById("btn-ver-historial");
  if (!btn) return;

  document.getElementById("btn-hablar-koko-historial").addEventListener("click", () => {
    document.getElementById("btn-abrir-koko").click();
  });

  const contenido = document.getElementById("historial-contenido");
  let cargado = false;

  btn.addEventListener("click", async () => {
    const vaAMostrar = contenido.classList.contains("oculto");
    if (vaAMostrar && !cargado) {
      btn.disabled = true;
      btn.textContent = "Cargando...";
      try {
        const resp = await fetch("/api/historial");
        const data = await resp.json();
        pintarHistorial(contenido, data.busquedas || [], data.productos_interes || []);
        cargado = true;
      } catch (e) {
        contenido.innerHTML = "<p class=\"ayuda\">No pudimos cargar tu historial -- intenta de nuevo.</p>";
      } finally {
        btn.disabled = false;
      }
    }
    contenido.classList.toggle("oculto", !vaAMostrar);
    btn.textContent = vaAMostrar ? "Ocultar historial" : "Ver historial";
  });
}

// Casilleros de "Que no quieres ver" (2026-08-28): mapa id -> clave del
// objeto guardado, auto-guarda al tocar cada uno (sin boton "Guardar").
// El texto corto es solo para el chip -- la etiqueta completa vive en el
// <label> del HTML.
const MAPA_PREFERENCIAS_NEGATIVAS = {
  "pref-rotos": { clave: "excluir_rotos", texto: "Rotos/desgastados" },
  "pref-grafico": { clave: "excluir_grafico_grande", texto: "Gráficos grandes" },
  "pref-texto": { clave: "excluir_texto_grande", texto: "Texto grande" },
  "pref-cara-logo": { clave: "excluir_cara_logo_grande", texto: "Caras/logos gigantes" },
};

// Dropdown compacto (2026-08-29): mismos checkboxes/claves de siempre, solo
// cambia como se muestran -- ocultos dentro de un panel que se abre al
// tocar el boton, y las opciones marcadas se resumen como chips con "x".
function configurarPreferenciasNegativas() {
  const boton = document.getElementById("btn-selector-exclusiones");
  const panel = document.getElementById("selector-exclusiones-panel");
  const texto = document.getElementById("selector-exclusiones-texto");
  const chips = document.getElementById("selector-exclusiones-chips");
  if (!boton || !panel || !texto || !chips) return;

  function refrescarResumen() {
    const marcados = Object.entries(MAPA_PREFERENCIAS_NEGATIVAS)
      .filter(([id]) => document.getElementById(id).checked);
    texto.textContent = marcados.length
      ? `${marcados.length} preferencia${marcados.length > 1 ? "s" : ""} seleccionada${marcados.length > 1 ? "s" : ""}`
      : "Seleccionar preferencias";
    chips.innerHTML = "";
    for (const [id, { texto: textoChip }] of marcados) {
      const chip = document.createElement("span");
      chip.className = "selector-exclusiones-chip";
      chip.textContent = textoChip + " ";
      const btnX = document.createElement("button");
      btnX.type = "button";
      btnX.setAttribute("aria-label", `Quitar ${textoChip}`);
      btnX.textContent = "×";
      btnX.addEventListener("click", () => {
        document.getElementById(id).checked = false;
        document.getElementById(id).dispatchEvent(new Event("change"));
      });
      chip.appendChild(btnX);
      chips.appendChild(chip);
    }
  }

  const prefs = getPreferenciasNegativas();
  for (const [id, { clave }] of Object.entries(MAPA_PREFERENCIAS_NEGATIVAS)) {
    const input = document.getElementById(id);
    if (!input) continue;
    input.checked = Boolean(prefs[clave]);
    input.addEventListener("change", () => {
      const actuales = getPreferenciasNegativas();
      actuales[clave] = input.checked;
      guardarPreferenciasNegativas(actuales);
      refrescarResumen();
    });
  }
  refrescarResumen();

  boton.addEventListener("click", () => {
    const abierto = !panel.classList.contains("oculto");
    panel.classList.toggle("oculto", abierto);
    boton.setAttribute("aria-expanded", String(!abierto));
  });
  document.addEventListener("click", (ev) => {
    if (!document.getElementById("selector-exclusiones").contains(ev.target)) {
      panel.classList.add("oculto");
      boton.setAttribute("aria-expanded", "false");
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  configurarInterruptorTema();
  configurarPreferenciasNegativas();
  // Independiente del perfil de busqueda (localStorage) de mas abajo -- el
  // historial depende solo de la sesion real (ver {% if usuario %} en
  // perfil.html), asi que alguien logueado sin perfil local igual tiene
  // que poder verlo.
  configurarHistorial();

  const perfil = getPerfil();
  const resumen = document.getElementById("perfil-resumen");
  const linkEditar = document.getElementById("link-editar");
  const sinPerfil = document.getElementById("sin-perfil");

  if (!perfil) {
    sinPerfil.classList.remove("oculto");
    return;
  }

  // Solo caracteristicas de busqueda (2026-08-30, pedido del usuario):
  // nombre/correo/telefono se separaron al icono "Mi cuenta" fijo arriba
  // (ver _barra_cuenta.html) para no mostrar el mismo dato 2 veces en la
  // pantalla. Genero se sigue usando internamente (ver agregarTallaEstimada
  // mas abajo), solo que ya no se muestra como fila aparte.
  const campos = [
    ["Altura", perfil.altura],
    ["Peso", perfil.peso],
    ["Hobbies", textoHobbies(perfil)],
    ["Dirección", perfil.direccion],
  ];

  for (const [etiqueta, valor] of campos) {
    if (!valor) continue;
    agregarFilaPerfil(resumen, etiqueta, valor);
  }

  agregarTallaEstimada(resumen, perfil);
  agregarPreferenciaIdiomaKoko(resumen, perfil.gmail || "");

  linkEditar.classList.remove("oculto");
});
