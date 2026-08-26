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

// Sube la foto de perfil de la cuenta real (ver docs/cuentas.md) --
// aparte del resto porque solo aparece si hay una cuenta logueada
// (usuario != None, ver perfil.html). Best-effort: si algo falla, se
// avisa con texto simple, nunca rompe la pagina.
function configurarSubidaFoto() {
  const input = document.getElementById("input-foto-perfil");
  if (!input) return;
  input.addEventListener("change", async () => {
    const archivo = input.files[0];
    if (!archivo) return;
    const estado = document.getElementById("estado-foto-perfil");
    estado.textContent = "Subiendo...";
    try {
      const formData = new FormData();
      formData.append("foto", archivo);
      const resp = await fetch("/perfil/foto", { method: "POST", body: formData });
      const data = await resp.json();
      if (data.foto_perfil) {
        document.getElementById("foto-perfil-actual").src = data.foto_perfil;
        estado.textContent = "¡Listo!";
      } else {
        estado.textContent = data.error || "No se pudo subir la foto.";
      }
    } catch (e) {
      estado.textContent = "No se pudo subir la foto -- intenta de nuevo.";
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  configurarInterruptorTema();
  configurarSubidaFoto();

  const perfil = getPerfil();
  const resumen = document.getElementById("perfil-resumen");
  const linkEditar = document.getElementById("link-editar");
  const sinPerfil = document.getElementById("sin-perfil");

  if (!perfil) {
    sinPerfil.classList.remove("oculto");
    return;
  }

  const campos = [
    ["Nombre", `${perfil.nombre || ""} ${perfil.apellido || ""}`.trim()],
    ["Correo", perfil.gmail],
    ["Teléfono", perfil.telefono],
    ["Género", perfil.genero],
    ["Edad", perfil.edad],
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
