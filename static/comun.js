// Codigo compartido entre index.html (formulario) y resultados.html
// (pagina de resultados): la animacion de carga y como se dibuja cada
// tarjeta de producto.

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
