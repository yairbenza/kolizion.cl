// Pagina de navegacion libre (/vitrina): sin preguntas, catalogo agrupado
// en Tendencias/Ofertas/Destacados. Cada seccion es una fila horizontal
// (carrusel) en vez de una grilla -- Tendencias y Ofertas quedan visibles
// al mismo tiempo, sin scroll vertical.
//
// No reusa renderResultados (comun.js): las tarjetas de vitrina llevan una
// insignia (razon de la tendencia, o el % de descuento) que las de
// /resultados no tienen, asi que usan su propio armado.

function tarjetaVitrina(rec, favoritosSet) {
  const card = document.createElement("div");
  card.className = "resultado-card tarjeta-vitrina";

  const esOferta = Boolean(rec.descuento_pct);
  const claseInsignia = esOferta ? "insignia-vitrina insignia-oferta" : "insignia-vitrina insignia-tendencia";
  const textoInsignia = esOferta ? `-${rec.descuento_pct}%` : rec.razon;
  const email = emailFavoritos();

  card.innerHTML = `
    <span class="${claseInsignia}">${textoInsignia}</span>
    ${email ? marcadorFavoritoHtml(rec.nombre, favoritosSet) : ""}
    ${rec.imagen ? `<img src="${rec.imagen}" alt="${esImagenIlustrativa(rec.imagen) ? "Ilustración de referencia (no es una foto real del producto)" : rec.nombre}" class="imagen-producto">` : ""}
    ${rec.imagen && esImagenIlustrativa(rec.imagen) ? `<p class="aviso-imagen">Imagen ilustrativa de referencia, no es el producto real.</p>` : ""}
    <div class="tienda">${rec.tienda}</div>
    ${rec.marca_autor ? `<span class="insignia-marca-autor">✦ Marca de autor</span>` : ""}
    <h3>${rec.nombre}</h3>
    ${rec.marca ? `<p class="marca">${rec.marca}</p>` : ""}
    <p class="precio-vitrina">
      ${rec.precio ? `<span class="precio">${rec.precio}</span>` : ""}
      ${esOferta && rec.precio_original ? `<span class="precio-tachado">${rec.precio_original}</span>` : ""}
    </p>
    ${!esOferta ? `<p class="razon">${rec.razon}</p>` : ""}
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
    conectarBotonFavorito(card, rec);
  }
  conectarVistaPrevia(card, rec);
  return card;
}

function renderFilaVitrina(contenedorId, recomendaciones, favoritosSet, infinito) {
  const contenedor = document.getElementById(contenedorId);
  // Carrusel infinito (2026-08-25): en vez de pedir mas productos al
  // catalogo (tarea pesada, pendiente), la lista se repite 3 veces seguidas
  // -- alcanza para dar sensacion de scroll sin fin sin tocar el backend.
  const lista = infinito && recomendaciones.length ? [...recomendaciones, ...recomendaciones, ...recomendaciones] : recomendaciones;
  for (const rec of lista) {
    contenedor.appendChild(tarjetaVitrina(rec, favoritosSet));
  }
  if (infinito && recomendaciones.length) {
    activarScrollInfinito(contenedor);
  }
}

// Como las 3 copias son identicas, apenas el usuario se acerca al borde de
// una copia lo salteamos sin animacion al mismo punto de la copia vecina --
// el salto no se nota y se puede seguir deslizando en cualquier direccion
// sin toparse nunca con un final abrupto.
function activarScrollInfinito(contenedor) {
  requestAnimationFrame(() => {
    const anchoSet = contenedor.scrollWidth / 3;
    if (!anchoSet) return;
    contenedor.scrollLeft = anchoSet;
    contenedor.addEventListener("scroll", () => {
      if (contenedor.scrollLeft < anchoSet * 0.15) {
        contenedor.scrollLeft += anchoSet;
      } else if (contenedor.scrollLeft > anchoSet * 1.85) {
        contenedor.scrollLeft -= anchoSet;
      }
    });
  });
}

// "Llegan rápido a ti" (2026-08-25): a pedido del usuario, dejo de mostrarse
// como fila de tarjetas grandes (como si fuera un catalogo de productos) --
// ahora es un icono chico que abre un modal con solo la INFO de que tiendas
// llegan mas rapido (nombre, ubicacion, texto de envio), sin links a
// catalogo externo. Cada item del modal si linkea a la ficha propia de la
// tienda (/tienda/<id>), que es informacion de la tienda, no un producto.
function itemTiendaRapida(t) {
  const li = document.createElement("li");
  li.className = "item-llegan-rapido";
  const ubicacion = [t.comuna, t.region].filter(Boolean).join(", ");
  li.innerHTML = `
    <div class="item-llegan-rapido-info">
      <strong>${escaparHtml(t.nombre)}</strong>
      <span class="item-llegan-rapido-envio">${escaparHtml(t.envio_texto)}</span>
      ${ubicacion ? `<span class="item-llegan-rapido-ubicacion">${escaparHtml(ubicacion)}</span>` : ""}
    </div>
    <a href="/tienda/${t.id}">Ver tienda</a>
  `;
  return li;
}

// El icono fijo solo aparece si hay algo que mostrar (direccion guardada Y
// al menos 1 tienda piloto con datos de envio) -- si no, se queda oculto en
// vez de mostrar un aviso, porque ya no vive dentro de una seccion del
// feed con espacio propio para explicar por que esta vacio.
async function cargarTiendasRapido() {
  const btnAbrir = document.getElementById("btn-llegan-rapido");
  const perfil = getPerfil();
  const direccion = (perfil && perfil.direccion) || "";

  try {
    const resp = await fetch("/api/tiendas_rapido?direccion=" + encodeURIComponent(direccion));
    const data = await resp.json();
    if (!data.direccion_configurada || !(data.tiendas || []).length) return;
    const lista = document.getElementById("lista-llegan-rapido");
    for (const t of data.tiendas) {
      lista.appendChild(itemTiendaRapida(t));
    }
    btnAbrir.classList.remove("oculto");
  } catch (e) {
    // Sin datos de envio, el icono simplemente no aparece.
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  const estado = document.getElementById("estado");
  estado.textContent = "Cargando Descubre...";

  document.querySelectorAll(".fila-flecha").forEach((boton) => {
    boton.addEventListener("click", () => {
      const fila = document.getElementById(boton.dataset.fila);
      const direccion = boton.classList.contains("fila-flecha-izq") ? -1 : 1;
      fila.scrollBy({ left: direccion * fila.clientWidth * 0.8, behavior: "smooth" });
    });
  });

  cargarTiendasRapido();
  document.getElementById("btn-llegan-rapido").addEventListener("click", () => {
    document.getElementById("modal-llegan-rapido").classList.remove("oculto");
  });
  document.getElementById("btn-cerrar-llegan-rapido").addEventListener("click", () => {
    document.getElementById("modal-llegan-rapido").classList.add("oculto");
  });

  try {
    const [resp, favoritosSet] = await Promise.all([fetch("/api/vitrina"), cargarFavoritosSet()]);
    if (!resp.ok) throw new Error("Error del servidor: " + resp.status);
    const data = await resp.json();
    estado.textContent = "";

    renderFilaVitrina("vitrina-tendencias", data.tendencias || [], favoritosSet, true);
    renderFilaVitrina("vitrina-lanzamientos", data.lanzamientos || [], favoritosSet);
    renderFilaVitrina("vitrina-ofertas", data.ofertas || [], favoritosSet, true);
    renderFilaVitrina("vitrina-destacados", data.destacados || [], favoritosSet, true);
  } catch (err) {
    estado.textContent = "Algo salió mal cargando Descubre: " + err.message;
  }
});
