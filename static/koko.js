// Chat de Koko (mascota-perrito, asistente de estilo) -- vive en las 4
// paginas (index, resultados, vitrina, perfil), y se abre siempre a
// PANTALLA COMPLETA (como una app de mensajeria, nunca una ventana chica).
// Habla con la API de Anthropic del lado del servidor (/api/koko/chat).
//
// La conversacion se guarda en el servidor por email (data/chats_koko.json,
// ver app.py) y se recarga cada vez que se abre el panel -- nunca se pierde
// al recargar la pagina o volver a entrar.
//
// Reusa getPerfil() y buscar() (comun.js) para no duplicar la logica de
// "activar el buscador real" cuando el usuario acepta una sugerencia de Koko.

const MENSAJE_BIENVENIDA_KOKO =
  "¡Hola! Me llamo Koko y soy experto en ropa. Puedo ayudarte a encontrar una prenda que te va a " +
  "cambiar la vida, o armarte el outfit del día completo. ¿Qué buscas hoy?";

let mensajesKoko = [];

// --- Formato de texto: negritas/cursivas reales, saltos de linea reales ---
// Antes se pintaba con textContent (texto plano) -- los **asteriscos** del
// modelo se veian literales y los saltos de linea se perdian. Ahora se
// escapa el texto primero (nunca confiar HTML crudo, aunque venga de nuestro
// propio backend) y RECIEN AHI se aplican las 2 reglas de markdown que
// soportamos. Los saltos de linea reales los resuelve el CSS
// (white-space: pre-wrap en .burbuja-koko), no hace falta convertirlos aca.
// (escaparHtml() vive en comun.js -- la reusa perfil.js tambien.)

function formatearTextoKoko(texto) {
  let seguro = escaparHtml(texto);
  seguro = seguro.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  seguro = seguro.replace(/\*(.+?)\*/g, "<em>$1</em>");
  return seguro;
}

function pintarBurbujaKoko(rol, texto) {
  const cont = document.getElementById("mensajes-koko");
  const div = document.createElement("div");
  div.className = `burbuja-koko burbuja-koko-${rol}`;
  div.innerHTML = formatearTextoKoko(texto);
  cont.appendChild(div);
  cont.scrollTop = cont.scrollHeight;
}

// --- Animacion del personaje: poses/frames, no la imagen entera moviendose ---
// KOKO_FRAMES lista las poses que DEBERIAN existir -- hoy solo la primera
// (koko.png, pose neutra) existe de verdad. Las otras 4 son emotes
// (2026-08-07: subido de 3 a 4 a pedido del usuario) que hay que generar
// aparte. precargarFramesKoko() prueba cargar cada una; las que fallan
// (404, todavia no generadas) se descartan solas, asi el codigo ya queda
// listo para cuando se agreguen sin tener que tocar nada mas. Con 1 sola
// pose disponible, se usa un pulso sutil de respaldo (clase
// "koko-pensando" en style.css) que NO mueve al personaje de lugar.
const KOKO_FRAMES = [
  "/static/img/koko/koko.png",
  "/static/img/koko/koko-emote-1.png",
  "/static/img/koko/koko-emote-2.png",
  "/static/img/koko/koko-emote-3.png",
  "/static/img/koko/koko-emote-4.png",
];

let framesDisponibles = [KOKO_FRAMES[0]];
let intervaloAnimacionKoko = null;

function precargarFramesKoko() {
  return Promise.all(
    KOKO_FRAMES.map(
      (src) =>
        new Promise((resolve) => {
          const img = new Image();
          img.onload = () => resolve(src);
          img.onerror = () => resolve(null);
          img.src = src;
        })
    )
  ).then((resultados) => {
    const validos = resultados.filter(Boolean);
    if (validos.length > 1) framesDisponibles = validos;
  });
}

function iniciarAnimacionKoko(personaje) {
  if (framesDisponibles.length <= 1) {
    personaje.classList.add("koko-pensando");
    return;
  }
  // Un fundido cortito antes de cambiar de emote (opacity, via CSS
  // transition en .personaje-koko) para que el cambio se sienta como una
  // transicion, no un corte seco entre fotos.
  let i = 0;
  intervaloAnimacionKoko = setInterval(() => {
    i = (i + 1) % framesDisponibles.length;
    personaje.style.opacity = "0";
    setTimeout(() => {
      personaje.src = framesDisponibles[i];
      personaje.style.opacity = "1";
    }, 90);
  }, 260);
}

function detenerAnimacionKoko(personaje) {
  if (intervaloAnimacionKoko) {
    clearInterval(intervaloAnimacionKoko);
    intervaloAnimacionKoko = null;
  }
  personaje.classList.remove("koko-pensando");
  personaje.style.opacity = "1";
  personaje.src = framesDisponibles[0];
}

const SUGERENCIA_PENDIENTE_KEY = "kokoSugerenciaPendiente";
// Se prende cuando el usuario confirma una busqueda sugerida por Koko (ver
// mostrarSugerenciaKoko) -- asi, si se va a otra pagina (ej. "Descubre") sin
// pasar por /resultados de nuevo y vuelve a abrir el chat, se le puede
// ofrecer un acceso directo de vuelta a esos resultados en vez de perderlos
// (pedido del usuario, 2026-08-26: "no perder resultados de Koko al
// navegar"). Vive toda la pestaña (sessionStorage), no hace falta borrarla
// manualmente -- solo se limpia al reiniciar la conversacion.
const RESULTADOS_KOKO_PENDIENTES_KEY = "kokoResultadosPendientes";

function ocultarSugerenciaKoko() {
  const cont = document.getElementById("sugerencia-koko");
  cont.classList.add("oculto");
  cont.innerHTML = "";
  sessionStorage.removeItem(SUGERENCIA_PENDIENTE_KEY);
}

// Trae la conversacion guardada de este email (si tiene) y la pinta tal
// cual; si no hay nada guardado (usuario nuevo, o sin perfil todavia),
// muestra el saludo de siempre. Se llama cada vez que se abre el panel.
async function cargarHistorialKoko() {
  const cont = document.getElementById("mensajes-koko");
  cont.innerHTML = "";
  mensajesKoko = [];

  const perfilCompleto = getPerfil() || {};
  const email = perfilCompleto.gmail || "";

  if (email) {
    try {
      const resp = await fetch("/api/koko/historial_chat?email=" + encodeURIComponent(email));
      const data = await resp.json();
      if (data.mensajes && data.mensajes.length) {
        mensajesKoko = data.mensajes;
        for (const m of mensajesKoko) {
          pintarBurbujaKoko(m.rol, m.texto);
        }
        if (!restaurarSugerenciaPendienteKoko()) {
          mostrarAvisoResultadosPendientesKoko();
        }
        return;
      }
    } catch (err) {
      // Si falla la carga, seguimos con el saludo de siempre en vez de
      // dejar el chat vacio.
    }
  }
  pintarBurbujaKoko("koko", MENSAJE_BIENVENIDA_KOKO);
}

// Si Koko ya habia propuesto una busqueda (tarjeta "¿Buscamos X para ti?")
// y la persona se fue a otra pagina (ej: "Descubre") sin confirmar ni
// rechazar, esa tarjeta antes se perdia -- el chat guardado en el servidor
// solo tiene el TEXTO de la respuesta, no el dato estructurado de la
// sugerencia. Se guarda aparte en sessionStorage (dura toda la pestaña,
// como "resultados"/"ultimoPayload" en comun.js) y se repinta al volver a
// abrir el panel, para no tener que volver a pedirle la busqueda a Koko.
function restaurarSugerenciaPendienteKoko() {
  const guardada = sessionStorage.getItem(SUGERENCIA_PENDIENTE_KEY);
  if (!guardada) return false;
  try {
    mostrarSugerenciaKoko(JSON.parse(guardada));
    return true;
  } catch (err) {
    sessionStorage.removeItem(SUGERENCIA_PENDIENTE_KEY);
    return false;
  }
}

// Si Koko encontro resultados y el usuario se fue a otra pagina sin
// verlos/seguir ahi, muestra un aviso chico para volver a esa pantalla de
// resultados -- reusa el mismo contenedor que la tarjeta "¿Buscamos X?"
// (nunca se muestran los dos a la vez: si hay una sugerencia pendiente, esa
// tiene prioridad). No aplica si ya estamos en /resultados (no tiene
// sentido ofrecer "ver resultados" ahi mismo).
function mostrarAvisoResultadosPendientesKoko() {
  if (window.location.pathname === "/resultados") return;
  if (sessionStorage.getItem(RESULTADOS_KOKO_PENDIENTES_KEY) !== "1") return;
  // Mismo limite de 15 minutos que el aviso del buscador (ver
  // hayResultadosRecientes en comun.js) -- pasado ese tiempo, mejor no
  // seguir insistiendo con resultados viejos.
  if (!hayResultadosRecientes()) return;

  const cont = document.getElementById("sugerencia-koko");
  cont.innerHTML = `
    <p>Encontramos productos para ti hace un momento.</p>
    <div class="botones-quien">
      <button id="btn-koko-ver-resultados" type="button">Ver resultados</button>
    </div>
  `;
  cont.classList.remove("oculto");
  document.getElementById("btn-koko-ver-resultados").addEventListener("click", () => {
    window.location.href = "/resultados";
  });
}

// Boton "Reiniciar conversacion" del header (icono, junto al de cerrar):
// pide confirmacion (no se puede deshacer), borra el historial guardado en
// el servidor para este email y deja el chat como recien abierto, con el
// saludo de siempre.
async function reiniciarConversacionKoko() {
  if (!window.confirm("¿Seguro que quieres reiniciar la conversación? Se va a borrar todo el historial.")) {
    return;
  }

  const perfilCompleto = getPerfil() || {};
  const email = perfilCompleto.gmail || "";
  if (email) {
    try {
      await fetch("/api/koko/reiniciar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
    } catch (err) {
      // Best-effort: si falla el borrado en el servidor, igual limpiamos
      // la vista -- la proxima vez que se abra el panel se vuelve a
      // cargar el historial viejo desde el servidor, pero no rompe nada
      // ahora mismo.
    }
  }

  mensajesKoko = [];
  document.getElementById("mensajes-koko").innerHTML = "";
  ocultarSugerenciaKoko();
  sessionStorage.removeItem(RESULTADOS_KOKO_PENDIENTES_KEY);
  pintarBurbujaKoko("koko", MENSAJE_BIENVENIDA_KOKO);
}

// Pinta la mini-tarjeta "¿Buscamos X para ti?" cuando Koko llama la tool
// sugerir_busqueda. Si el usuario confirma, se arma el mismo payload que ya
// usa el formulario normal (modo "yo") y se llama a buscar() -- eso activa
// la animacion de carga y termina en /resultados, igual que una busqueda
// hecha a mano.
function mostrarSugerenciaKoko(sugerencia) {
  const cont = document.getElementById("sugerencia-koko");
  const detalle = [sugerencia.tipo_prenda, sugerencia.subtipo, sugerencia.forma_gorro, sugerencia.color, sugerencia.corte]
    .filter(Boolean)
    .join(" ");
  const conPresupuesto = sugerencia.presupuesto_max
    ? `${detalle || "esto"} hasta $${Number(sugerencia.presupuesto_max).toLocaleString("es-CL")}`
    : detalle || "esto";
  const excluidos = Array.isArray(sugerencia.excluir) ? sugerencia.excluir.filter(Boolean) : [];
  const conExclusion = excluidos.length ? `${conPresupuesto} (sin ${excluidos.join(", ")})` : conPresupuesto;
  cont.innerHTML = `
    <p>¿Buscamos ${conExclusion} para ti?</p>
    <div class="botones-quien">
      <button id="btn-koko-si" type="button">Sí, buscar</button>
      <button id="btn-koko-no" type="button">Seguir hablando</button>
    </div>
  `;
  cont.classList.remove("oculto");

  document.getElementById("btn-koko-si").addEventListener("click", () => {
    // El panel de Koko es un overlay a pantalla completa (position: fixed,
    // z-index: 100) -- si se queda abierto, tapa por completo el esqueleto
    // de carga de buscarConAnimacion() (comun.js), que vive en el flujo
    // normal de la pagina sin z-index propio. Por eso antes "no pasaba
    // nada" mientras se buscaba: la animacion SI corria, pero quedaba
    // escondida detras del panel. Cerrarlo antes de buscar la deja visible.
    document.getElementById("panel-koko").classList.add("oculto");
    sessionStorage.removeItem(SUGERENCIA_PENDIENTE_KEY);
    sessionStorage.setItem(RESULTADOS_KOKO_PENDIENTES_KEY, "1");

    const perfilCompleto = getPerfil() || {};
    const perfilParaBuscar = {
      genero: perfilCompleto.genero,
      edad: perfilCompleto.edad,
      altura: perfilCompleto.altura,
      peso: perfilCompleto.peso,
      hobbie: perfilCompleto.hobbie,
      hobbie_musica_genero: perfilCompleto.hobbie_musica_genero,
      hobbie_deportes_subtipo: perfilCompleto.hobbie_deportes_subtipo,
    };
    buscar({
      modo: "yo",
      email: perfilCompleto.gmail || "",
      perfil: perfilParaBuscar,
      categoria: sugerencia.categoria || "",
      tipo_prenda: sugerencia.tipo_prenda || "",
      subtipo: sugerencia.subtipo || "",
      largo: "",
      manga: "",
      capucha: "",
      cierre: "",
      corte: sugerencia.corte || "",
      color: sugerencia.color || "",
      ocasion: "",
      precio: sugerencia.presupuesto_max ? String(sugerencia.presupuesto_max) : "",
      gorro_forma: sugerencia.forma_gorro || "",
      ignorar_talla: Boolean(sugerencia.ignorar_talla),
      excluir: excluidos,
      preferencias_negativas: getPreferenciasNegativas(),
    });
  });

  document.getElementById("btn-koko-no").addEventListener("click", ocultarSugerenciaKoko);
}

function deshabilitarInputKoko() {
  const input = document.getElementById("input-koko");
  const boton = document.querySelector("#form-koko button[type='submit']");
  input.disabled = true;
  input.placeholder = "Volvé mañana para seguir la charla";
  if (boton) boton.disabled = true;
}

async function enviarMensajeKoko(texto) {
  mensajesKoko.push({ rol: "usuario", texto });
  pintarBurbujaKoko("usuario", texto);
  ocultarSugerenciaKoko();

  // Animacion del PERSONAJE (poses/frames si estan disponibles, o el pulso
  // de respaldo) mientras espera la respuesta -- se apaga apenas llega (o
  // si algo falla), nunca queda pegada.
  const personaje = document.getElementById("personaje-koko");
  iniciarAnimacionKoko(personaje);

  try {
    const perfilCompleto = getPerfil() || {};
    const resp = await fetch("/api/koko/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: perfilCompleto.gmail || "",
        perfil: {
          genero: perfilCompleto.genero,
          edad: perfilCompleto.edad,
          altura: perfilCompleto.altura,
          peso: perfilCompleto.peso,
          hobbie: perfilCompleto.hobbie,
          hobbie_musica_genero: perfilCompleto.hobbie_musica_genero,
          hobbie_deportes_subtipo: perfilCompleto.hobbie_deportes_subtipo,
        },
        mensajes: mensajesKoko,
      }),
    });
    // Antes se asumia que la respuesta siempre era JSON valido -- si el
    // servidor devolvia un error real (500, o un 429 del limitador de
    // "10 por minuto" en /api/koko/chat), el cuerpo puede no ser JSON y
    // resp.json() lanza una excepcion DENTRO del try, que el catch de abajo
    // si atrapa. Pero si la respuesta SI era JSON valido con un status de
    // error (ej: algun proxy/error handler que devuelva JSON), antes se
    // seguia de largo como si nada -- ahora se corta antes, mismo patron
    // que buscarConAnimacion() en comun.js.
    if (!resp.ok) throw new Error("Error del servidor: " + resp.status);
    const data = await resp.json();
    const textoRespuesta = data.respuesta_texto || "¿Me cuentas un poco más?";
    mensajesKoko.push({ rol: "koko", texto: textoRespuesta });
    pintarBurbujaKoko("koko", textoRespuesta);
    if (data.sugerencia) {
      sessionStorage.setItem(SUGERENCIA_PENDIENTE_KEY, JSON.stringify(data.sugerencia));
      mostrarSugerenciaKoko(data.sugerencia);
    }
    // Limite diario de mensajes (app.py, LIMITE_MENSAJES_KOKO_DIA) -- deja
    // el mensaje bien visible en la burbuja Y ademas deshabilita el input,
    // para que no siga insistiendo sin que pase nada. Se re-habilita solo
    // recargando la pagina (al otro dia, el chequeo del servidor ya deja
    // pasar de nuevo).
    if (data.limite_alcanzado) {
      deshabilitarInputKoko();
    }
  } catch (err) {
    // Mismo texto que usa el backend cuando la llamada a la IA falla del
    // lado del servidor (servicio_koko.py) -- Koko esta entrenado para
    // reconocer ese prefijo como "quedo una busqueda pendiente" y retomarla
    // sola si la persona responde con un reintento corto ("ahora si", "dale",
    // etc). Se agrega tambien a mensajesKoko (no solo se pinta) para que la
    // proxima llamada a /api/koko/chat en esta pestaña incluya la señal de
    // falla en el historial que se manda -- si aqui no falla nunca llega al
    // servidor, asi que es la unica forma de que quede registrada.
    const textoError = "Guau, tuve un problema para responder. Intenta de nuevo.";
    mensajesKoko.push({ rol: "koko", texto: textoError });
    pintarBurbujaKoko("koko", textoError);
  } finally {
    detenerAnimacionKoko(personaje);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const panel = document.getElementById("panel-koko");
  const input = document.getElementById("input-koko");

  precargarFramesKoko();

  // Dos formas de abrir el mismo panel: desde la barra de navegacion (item
  // "Koko") entra a pantalla completa; desde el icono flotante chico entra
  // en ventana chica (ver .panel-koko-overlay.pantalla-completa en style.css).
  function abrirPanelKoko(pantallaCompleta) {
    panel.classList.toggle("pantalla-completa", pantallaCompleta);
    panel.classList.remove("oculto");
    input.focus();
    cargarHistorialKoko();
  }

  document.getElementById("btn-abrir-koko").addEventListener("click", () => {
    abrirPanelKoko(true);
  });

  document.getElementById("btn-abrir-koko-chico").addEventListener("click", () => {
    abrirPanelKoko(false);
  });

  document.getElementById("btn-cerrar-koko").addEventListener("click", () => {
    panel.classList.add("oculto");
  });

  document.getElementById("btn-reiniciar-koko").addEventListener("click", reiniciarConversacionKoko);

  // Guia "que le puedo preguntar a Koko" -- overlay aparte (#guia-koko, ver
  // _panel_koko.html), no reinicia ni toca mensajesKoko al abrir/cerrar.
  const guiaKoko = document.getElementById("guia-koko");
  document.getElementById("btn-guia-koko").addEventListener("click", () => {
    guiaKoko.classList.remove("oculto");
  });
  document.getElementById("btn-cerrar-guia-koko").addEventListener("click", () => {
    guiaKoko.classList.add("oculto");
  });
  document.querySelectorAll(".pregunta-guia-koko").forEach((boton) => {
    boton.addEventListener("click", () => {
      guiaKoko.classList.add("oculto");
      enviarMensajeKoko(boton.textContent.trim());
    });
  });

  document.getElementById("form-koko").addEventListener("submit", (e) => {
    e.preventDefault();
    const texto = input.value.trim();
    if (!texto) return;
    input.value = "";
    enviarMensajeKoko(texto);
  });
});
