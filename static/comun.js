// Codigo compartido entre index.html (formulario) y resultados.html
// (pagina de resultados): el perfil guardado, la animacion de carga y como
// se dibuja cada tarjeta de producto.

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

function renderResultados(contenedorId, recomendaciones) {
  const contenedor = document.getElementById(contenedorId);
  for (const rec of recomendaciones) {
    const card = document.createElement("div");
    card.className = "resultado-card";
    card.innerHTML = `
      ${rec.imagen ? `<img src="${rec.imagen}" alt="Ilustración de referencia (no es una foto real del producto)" class="imagen-producto">` : ""}
      ${rec.imagen ? `<p class="aviso-imagen">Imagen ilustrativa de referencia, no es el producto real.</p>` : ""}
      <div class="tienda">${rec.tienda}</div>
      <h3>${rec.nombre}</h3>
      ${rec.marca ? `<p class="marca">${rec.marca}</p>` : ""}
      ${rec.precio ? `<p class="precio">${rec.precio}</p>` : ""}
      ${rec.descripcion ? `<p class="descripcion">${rec.descripcion}</p>` : ""}
      ${rec.tallas_coincidentes && rec.tallas_coincidentes.length ? `<p class="talla">Disponible en: ${rec.tallas_coincidentes.join(", ")}</p>` : ""}
      <p class="razon">${rec.razon}</p>
      <a href="${rec.link}" target="_blank" rel="noopener">Ver producto (ejemplo)</a>
    `;
    const link = card.querySelector("a");
    if (link) {
      link.addEventListener("click", () => registrarInteresProducto(rec));
    }
    contenedor.appendChild(card);
  }
}

// Llama a /api/recommend mostrando el spinner + frases rotativas de
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
