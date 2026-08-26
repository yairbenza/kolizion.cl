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

function ocultarSugerenciaKoko() {
  const cont = document.getElementById("sugerencia-koko");
  cont.classList.add("oculto");
  cont.innerHTML = "";
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
        return;
      }
    } catch (err) {
      // Si falla la carga, seguimos con el saludo de siempre en vez de
      // dejar el chat vacio.
    }
  }
  pintarBurbujaKoko("koko", MENSAJE_BIENVENIDA_KOKO);
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
  pintarBurbujaKoko("koko", MENSAJE_BIENVENIDA_KOKO);
}

// Pinta la mini-tarjeta "¿Buscamos X para ti?" cuando Koko llama la tool
// sugerir_busqueda. Si el usuario confirma, se arma el mismo payload que ya
// usa el formulario normal (modo "yo") y se llama a buscar() -- eso activa
// la animacion de carga y termina en /resultados, igual que una busqueda
// hecha a mano.
function mostrarSugerenciaKoko(sugerencia) {
  const cont = document.getElementById("sugerencia-koko");
  const detalle = [sugerencia.tipo_prenda, sugerencia.subtipo, sugerencia.forma_gorro, sugerencia.corte]
    .filter(Boolean)
    .join(" ");
  const conPresupuesto = sugerencia.presupuesto_max
    ? `${detalle || "esto"} hasta $${Number(sugerencia.presupuesto_max).toLocaleString("es-CL")}`
    : detalle || "esto";
  cont.innerHTML = `
    <p>¿Buscamos ${conPresupuesto} para ti?</p>
    <div class="botones-quien">
      <button id="btn-koko-si" type="button">Sí, buscar</button>
      <button id="btn-koko-no" type="button">Seguir hablando</button>
    </div>
  `;
  cont.classList.remove("oculto");

  document.getElementById("btn-koko-si").addEventListener("click", () => {
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
      ocasion: "",
      precio: sugerencia.presupuesto_max ? String(sugerencia.presupuesto_max) : "",
      gorro_camino: "",
      gorro_colores: [],
      gorro_outfit: "",
      gorro_forma: sugerencia.forma_gorro || "",
      ignorar_talla: Boolean(sugerencia.ignorar_talla),
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
    const data = await resp.json();
    const textoRespuesta = data.respuesta_texto || "¿Me cuentas un poco más?";
    mensajesKoko.push({ rol: "koko", texto: textoRespuesta });
    pintarBurbujaKoko("koko", textoRespuesta);
    if (data.sugerencia) {
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
    pintarBurbujaKoko("koko", "Guau, algo salió mal. ¿Intentamos de nuevo?");
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

  document.getElementById("form-koko").addEventListener("submit", (e) => {
    e.preventDefault();
    const texto = input.value.trim();
    if (!texto) return;
    input.value = "";
    enviarMensajeKoko(texto);
  });
});
