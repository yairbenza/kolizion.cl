// Chat de Koko (mascota-perrito, asistente de estilo) -- solo vive en
// index.html, en un panel aparte del formulario de busqueda. Habla con la
// API de Anthropic del lado del servidor (/api/koko/chat). La conversacion
// en si vive solo en memoria del navegador (se pierde al cerrar/recargar) --
// lo que persiste es el historial estructurado (busquedas + clics en
// productos) que ya maneja app.py, nunca el texto crudo de la charla.
//
// Reusa getPerfil() (comun.js) y buscar() (script.js) para no duplicar la
// logica de "activar el buscador real" cuando el usuario acepta una
// sugerencia de Koko.

let mensajesKoko = [];

function pintarBurbujaKoko(rol, texto) {
  const cont = document.getElementById("mensajes-koko");
  const div = document.createElement("div");
  div.className = `burbuja-koko burbuja-koko-${rol}`;
  div.textContent = texto;
  cont.appendChild(div);
  cont.scrollTop = cont.scrollHeight;
}

function ocultarSugerenciaKoko() {
  const cont = document.getElementById("sugerencia-koko");
  cont.classList.add("oculto");
  cont.innerHTML = "";
}

// Pinta la mini-tarjeta "¿Buscamos X para ti?" cuando Koko llama la tool
// sugerir_busqueda. Si el usuario confirma, se arma el mismo payload que ya
// usa el formulario normal (modo "yo") y se llama a buscar() -- eso activa
// la animacion de carga y termina en /resultados, igual que una busqueda
// hecha a mano.
function mostrarSugerenciaKoko(sugerencia) {
  const cont = document.getElementById("sugerencia-koko");
  const detalle = [sugerencia.tipo_prenda, sugerencia.corte].filter(Boolean).join(" ");
  cont.innerHTML = `
    <p>¿Buscamos ${detalle || "esto"} para ti?</p>
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
    };
    buscar({
      modo: "yo",
      email: perfilCompleto.gmail || "",
      perfil: perfilParaBuscar,
      categoria: sugerencia.categoria || "",
      tipo_prenda: sugerencia.tipo_prenda || "",
      subtipo: "",
      largo: "",
      manga: "",
      capucha: "",
      cierre: "",
      corte: sugerencia.corte || "",
      ocasion: "",
      precio: "",
      gorro_camino: "",
      gorro_colores: [],
      gorro_outfit: "",
      gorro_forma: "",
    });
  });

  document.getElementById("btn-koko-no").addEventListener("click", ocultarSugerenciaKoko);
}

async function enviarMensajeKoko(texto) {
  mensajesKoko.push({ rol: "usuario", texto });
  pintarBurbujaKoko("usuario", texto);
  ocultarSugerenciaKoko();

  // Animacion de rebote mientras espera la respuesta -- se apaga apenas
  // llega (o si algo falla), nunca queda pegada.
  const avatar = document.getElementById("avatar-koko-chat");
  avatar.classList.add("koko-pensando");

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
  } catch (err) {
    pintarBurbujaKoko("koko", "Guau, algo salió mal. ¿Intentamos de nuevo?");
  } finally {
    avatar.classList.remove("koko-pensando");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const panel = document.getElementById("panel-koko");
  const input = document.getElementById("input-koko");

  document.getElementById("btn-abrir-koko").addEventListener("click", () => {
    panel.classList.remove("oculto");
    input.focus();
  });

  document.getElementById("btn-cerrar-koko").addEventListener("click", () => {
    panel.classList.add("oculto");
  });

  document.getElementById("form-koko").addEventListener("submit", (e) => {
    e.preventDefault();
    const texto = input.value.trim();
    if (!texto) return;
    input.value = "";
    enviarMensajeKoko(texto);
  });
});
