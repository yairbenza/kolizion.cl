// Logica de la pagina /resultados. Lee lo que dejo guardado script.js en
// sessionStorage (la busqueda ya se hizo, esto solo la muestra) y maneja
// el boton "Mostrar mas opciones" (que si hace una llamada nueva, con su
// propia animacion, sin salir de esta pagina).

// Caja "tienes marcado que no te gustan X -- buscamos igual solo por esta
// vez?" -- compartida entre la busqueda inicial (0 resultados) y "Mostrar
// mas opciones" (2026-08-30, pedido del usuario: el mismo aviso debe
// aparecer tambien la primera vez que se aprieta ese boton y no hay mas
// resultados por una preferencia negativa activa, no solo en la busqueda
// inicial). alConfirmar() se llama ya con la caja sacada del DOM.
function crearCajaRelajarPrefs(bloqueantes, alConfirmar) {
  const etiquetas = bloqueantes
    .map((clave) => ETIQUETAS_PREFERENCIAS_NEGATIVAS[clave] || clave)
    .join(", ");
  const caja = document.createElement("div");
  caja.className = "pregunta-relajar-prefs";
  const texto = document.createElement("p");
  texto.textContent =
    `Tienes marcado que no te gustan: ${etiquetas} — ¿quieres que busquemos igual ` +
    "incluyendo esas opciones, solo por esta vez?";
  const botones = document.createElement("div");
  botones.className = "botones-quien";
  const btnSi = document.createElement("button");
  btnSi.type = "button";
  btnSi.textContent = "Sí, buscar igual";
  const btnNo = document.createElement("button");
  btnNo.type = "button";
  btnNo.textContent = "No, gracias";
  botones.append(btnSi, btnNo);
  caja.append(texto, botones);

  btnNo.addEventListener("click", () => caja.remove());
  btnSi.addEventListener("click", () => {
    caja.remove();
    alConfirmar();
  });
  return caja;
}

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

  // Reusa el mismo boton que abre el panel de Koko a pantalla completa
  // (koko.js escucha #btn-abrir-koko) -- asi no hay que duplicar la logica
  // de abrir el panel/cargar el historial, solo dar un acceso directo mas
  // claro que el icono flotante para "seguir hablando de esta busqueda".
  // Solo se muestra si ESTOS resultados vinieron de una sugerencia de Koko
  // (bandera que koko.js prende al confirmar "Si, buscar") -- si la
  // busqueda se hizo con el formulario normal, no tiene sentido ofrecer
  // "volver a Koko" (nunca se hablo con el para esto), asi que el boton
  // queda oculto (pedido del usuario, 2026-08-26).
  const btnSeguirKoko = document.getElementById("btn-seguir-koko");
  if (btnSeguirKoko) {
    if (sessionStorage.getItem("kokoResultadosPendientes") === "1") {
      btnSeguirKoko.classList.remove("oculto");
      btnSeguirKoko.addEventListener("click", () => {
        document.getElementById("btn-abrir-koko").click();
      });
    } else {
      btnSeguirKoko.remove();
    }
  }

  const payloadGuardado = sessionStorage.getItem("ultimoPayload");
  const resultadosGuardados = sessionStorage.getItem("resultados");

  if (!payloadGuardado || resultadosGuardados === null) {
    // Alguien llego aca sin haber buscado nada (ej: entro directo a la URL).
    window.location.href = "/";
    return;
  }

  let ultimoPayload = JSON.parse(payloadGuardado);
  const recomendaciones = JSON.parse(resultadosGuardados);
  const sinTalla = sessionStorage.getItem("sinTalla") === "true";
  const avisoGorroForma = sessionStorage.getItem("avisoGorroForma") || "";
  const favoritosSet = await cargarFavoritosSet();

  if (recomendaciones.length === 0) {
    estado.textContent = sinTalla
      ? "No encontramos tu talla en las opciones actuales."
      : "No encontramos nada en el catálogo todavía para esto.";
  } else {
    // Pedido por el usuario y una forma de gorro (plano/curvo/lana) no
    // tenia nada -- en vez de dejar la busqueda vacia se muestran las
    // otras formas, avisando primero que la pedida no se encontro
    // (2026-08-30, pedido del usuario).
    if (avisoGorroForma) {
      estado.textContent = avisoGorroForma;
    }
    renderResultados("resultados", recomendaciones, { favoritosSet });
    feedback.classList.remove("oculto");
  }

  document.getElementById("btn-si-encontre").addEventListener("click", () => {
    feedback.classList.add("oculto");
  });

  const btnMasOpciones = document.getElementById("btn-mas-opciones");
  // Ids ya mostrados (resultado inicial + cada tanda anterior) para que el
  // backend no repita los mismos productos en cada tanda de "mas opciones"
  // (antes la busqueda era determinista y tanda tras tanda devolvia lo mismo).
  const idsYaMostrados = new Set(recomendaciones.map((r) => r.id).filter(Boolean));
  const contenedor = document.getElementById("resultados-plan-b");
  let tanda = 0;

  async function buscarTanda(prefsRelajadas) {
    tanda += 1;
    try {
      const data = await buscarConAnimacion({
        ...ultimoPayload,
        plan_b: true,
        ids_excluir: Array.from(idsYaMostrados),
        ...(prefsRelajadas ? { relajar_preferencias_negativas: prefsRelajadas } : {}),
      });
      const hayExactas = data.recomendaciones && data.recomendaciones.length > 0;
      // "alternativas" son productos que ya no cumplen el corte pedido (se
      // relajo ese filtro porque no quedaba nada mas exacto) -- se muestran
      // aparte, con su propio aviso, nunca mezcladas en silencio con las
      // que si cumplen todo lo pedido.
      const hayAlternativas = data.alternativas && data.alternativas.length > 0;

      if (!hayExactas && !hayAlternativas) {
        // Si lo que esta bloqueando son preferencias negativas activas del
        // perfil, se ofrece relajarlas solo por esta busqueda (mismo aviso
        // que en la busqueda inicial con 0 resultados) ANTES de dar por
        // agotadas las opciones -- pedido del usuario, 2026-08-30. No se
        // repite si ya se pregunto (prefsRelajadas viene seteado en el
        // reintento), para no quedar preguntando en loop.
        const bloqueantes = data.preferencias_bloqueantes || [];
        if (!prefsRelajadas && bloqueantes.length > 0) {
          tanda -= 1;
          const caja = crearCajaRelajarPrefs(bloqueantes, () => buscarTanda(bloqueantes));
          contenedor.appendChild(caja);
          caja.scrollIntoView({ behavior: "smooth", block: "start" });
          return;
        }
        // Ya no queda nada nuevo por mostrar (todo lo que el catalogo tiene
        // para esto ya se mostro antes) -- se corta aca, mostrando el aviso
        // justo despues de la ultima prenda ya listada (pedido del usuario,
        // 2026-08-28: que siempre se vea un cierre claro, no un boton que
        // deja de hacer algo en silencio).
        const fin = document.createElement("p");
        fin.className = "aviso-alternativas";
        fin.textContent = "No encontramos nada más.";
        contenedor.appendChild(fin);
        fin.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }

      if (hayExactas) {
        const titulo = document.createElement("h3");
        titulo.textContent = `Tanda de más opciones ${tanda}:`;
        contenedor.appendChild(titulo);
        renderResultados("resultados-plan-b", data.recomendaciones, { favoritosSet });
        data.recomendaciones.forEach((r) => r.id && idsYaMostrados.add(r.id));
      }

      if (hayAlternativas) {
        const aviso = document.createElement("h3");
        aviso.className = "aviso-alternativas";
        aviso.textContent = data.aviso_alternativas || "Esto también podría interesarte:";
        contenedor.appendChild(aviso);
        renderResultados("resultados-plan-b", data.alternativas, { favoritosSet });
        data.alternativas.forEach((r) => r.id && idsYaMostrados.add(r.id));
      }

      // Despues de cada tanda se pregunta si seguir, en vez de dejar un
      // boton fijo arriba de la pagina (pedido del usuario, 2026-08-28) --
      // asi la pregunta siempre aparece pegada a la ultima prenda mostrada.
      const pregunta = document.createElement("div");
      pregunta.className = "pregunta-mas-opciones";
      const texto = document.createElement("p");
      texto.textContent = "¿Quieres ver aún más opciones?";
      const botones = document.createElement("div");
      botones.className = "botones-quien";
      const btnSi = document.createElement("button");
      btnSi.type = "button";
      btnSi.textContent = "Sí, mostrar más";
      const btnNo = document.createElement("button");
      btnNo.type = "button";
      btnNo.textContent = "No, gracias";
      botones.append(btnSi, btnNo);
      pregunta.append(texto, botones);
      contenedor.appendChild(pregunta);
      pregunta.scrollIntoView({ behavior: "smooth", block: "start" });

      btnSi.addEventListener("click", () => {
        pregunta.remove();
        buscarTanda();
      });
      btnNo.addEventListener("click", () => {
        pregunta.remove();
      });
    } catch (err) {
      estado.textContent = "Algo salió mal: " + err.message;
    }
  }

  btnMasOpciones.addEventListener("click", () => {
    feedback.classList.add("oculto");
    buscarTanda();
  });

  // "Relajar por esta vez" (2026-08-30, pedido del usuario): si la busqueda
  // dio 0 resultados y el backend detecto que alguna preferencia negativa
  // activa era justo la que estaba bloqueando, se ofrece buscar igual
  // incluyendo esas opciones -- solo para esta busqueda puntual, sin tocar
  // lo guardado en el perfil (se manda aparte en "relajar_preferencias_negativas",
  // el checkbox del perfil no se toca).
  const prefsBloqueantes = JSON.parse(sessionStorage.getItem("prefsBloqueantes") || "[]");
  if (recomendaciones.length === 0 && prefsBloqueantes.length > 0) {
    const caja = crearCajaRelajarPrefs(prefsBloqueantes, async () => {
      const payloadRelajado = { ...ultimoPayload, relajar_preferencias_negativas: prefsBloqueantes };
      try {
        const data = await buscarConAnimacion(payloadRelajado);
        ultimoPayload = payloadRelajado;
        sessionStorage.setItem("ultimoPayload", JSON.stringify(payloadRelajado));
        sessionStorage.setItem("resultados", JSON.stringify(data.recomendaciones || []));
        sessionStorage.setItem("sinTalla", String(Boolean(data.sin_talla)));
        sessionStorage.setItem("prefsBloqueantes", JSON.stringify(data.preferencias_bloqueantes || []));
        sessionStorage.setItem("avisoGorroForma", data.aviso_gorro_forma || "");
        if (data.recomendaciones && data.recomendaciones.length > 0) {
          estado.textContent = data.aviso_gorro_forma || "";
          renderResultados("resultados", data.recomendaciones, { favoritosSet });
          data.recomendaciones.forEach((r) => r.id && idsYaMostrados.add(r.id));
          feedback.classList.remove("oculto");
        } else {
          estado.textContent = "Aun asi no encontramos nada.";
        }
      } catch (err) {
        estado.textContent = "Algo salió mal: " + err.message;
      }
    });
    estado.insertAdjacentElement("afterend", caja);
  }
});
