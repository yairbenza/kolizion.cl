// Logica de la pagina /resultados. Lee lo que dejo guardado script.js en
// sessionStorage (la busqueda ya se hizo, esto solo la muestra) y maneja
// el boton "Mostrar mas opciones" (que si hace una llamada nueva, con su
// propia animacion, sin salir de esta pagina).

document.addEventListener("DOMContentLoaded", async () => {
  const estado = document.getElementById("estado");
  const feedback = document.getElementById("feedback-busqueda");

  // "Cambiar requisitos de busqueda": atajo directo a los filtros ya
  // llenos, sin depender del boton atras del navegador. script.js detecta
  // el parametro "volver_filtros" al cargar "/" y llama a restaurarFiltros()
  // con lo ultimo guardado en sessionStorage -- mismo mecanismo que ya usa
  // el boton atras, solo que disparado a mano.
  const btnCambiarFiltros = document.getElementById("btn-cambiar-filtros");
  if (btnCambiarFiltros) {
    btnCambiarFiltros.addEventListener("click", () => {
      window.location.href = "/?volver_filtros=1";
    });
  }

  const payloadGuardado = sessionStorage.getItem("ultimoPayload");
  const resultadosGuardados = sessionStorage.getItem("resultados");

  if (!payloadGuardado || resultadosGuardados === null) {
    // Alguien llego aca sin haber buscado nada (ej: entro directo a la URL).
    window.location.href = "/";
    return;
  }

  const ultimoPayload = JSON.parse(payloadGuardado);
  const recomendaciones = JSON.parse(resultadosGuardados);
  const sinTalla = sessionStorage.getItem("sinTalla") === "true";
  const favoritosSet = await cargarFavoritosSet();

  if (recomendaciones.length === 0) {
    estado.textContent = sinTalla
      ? "No encontramos tu talla en las opciones actuales."
      : "No encontramos nada en el catálogo todavía para esto.";
  } else {
    renderResultados("resultados", recomendaciones, { favoritosSet });
    feedback.classList.remove("oculto");
  }

  document.getElementById("btn-si-encontre").addEventListener("click", () => {
    feedback.classList.add("oculto");
  });

  document.getElementById("btn-mas-opciones").addEventListener("click", async () => {
    feedback.classList.add("oculto");
    try {
      const data = await buscarConAnimacion({ ...ultimoPayload, plan_b: true });
      const hayExactas = data.recomendaciones && data.recomendaciones.length > 0;
      // "alternativas" son productos que ya no cumplen el corte pedido (se
      // relajo ese filtro porque no quedaba nada mas exacto) -- se muestran
      // aparte, con su propio aviso, nunca mezcladas en silencio con las
      // que si cumplen todo lo pedido.
      const hayAlternativas = data.alternativas && data.alternativas.length > 0;

      if (!hayExactas && !hayAlternativas) {
        estado.textContent = data.sin_talla
          ? "No encontramos tu talla en las opciones actuales."
          : "No encontramos nada en el catálogo todavía para esto.";
        return;
      }

      const contenedor = document.getElementById("resultados-plan-b");

      if (hayExactas) {
        const titulo = document.createElement("h3");
        titulo.textContent = "Más opciones:";
        contenedor.appendChild(titulo);
        renderResultados("resultados-plan-b", data.recomendaciones, { favoritosSet });
      }

      if (hayAlternativas) {
        const aviso = document.createElement("h3");
        aviso.className = "aviso-alternativas";
        aviso.textContent = data.aviso_alternativas || "Esto también podría interesarte:";
        contenedor.appendChild(aviso);
        renderResultados("resultados-plan-b", data.alternativas, { favoritosSet });
      }

      // Los resultados nuevos se agregan al final de la pagina -- sin esto,
      // si ya se estaba viendo la parte de abajo, pueden quedar fuera de lo
      // visible (mas todavia con la barra de navegacion fija) y parecer que
      // no paso nada.
      contenedor.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      estado.textContent = "Algo salió mal: " + err.message;
    }
  });
});
