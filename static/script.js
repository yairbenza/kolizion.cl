// PERFIL_KEY/getPerfil/guardarPerfil ahora viven en comun.js (los necesitan
// koko.js y resultados.html tambien, y comun.js se carga antes que este).

const secciones = [
  "seccion-perfil",
  "seccion-quien",
  "seccion-busqueda-yo",
  "seccion-busqueda-regalo",
];

// Las opciones pueden ser un texto simple ("Otro") o un par
// [texto, definicion corta] cuando conviene explicarle al usuario que
// significa cada una. La definicion solo cambia lo que se VE en el select
// -- el value que manda el buscador sigue siendo el texto solo, en
// minuscula, para no arriesgar que una palabra de la definicion choque con
// otra palabra clave del buscador.
const TIPO_PRENDA_OPCIONES = {
  "prenda superior": ["Polera", "Poleron", "Chaqueta", "Camisa", "Camiseta", "Top", "Me da igual", "Otro"],
  "prenda inferior": [
    "Pantalon", "Shorts",
    ["Falda cargo", "con bolsillos grandes al costado"],
    ["Bike shorts / shorts ciclista", "ajustados, tipo ciclista"],
    "Me da igual", "Otro",
  ],
};

const CORTE_OPCIONES = {
  "prenda superior": [
    ["Slim fit", "se pega al cuerpo"],
    ["Regular fit", "calce normal, ni ajustado ni suelto"],
    ["Straight", "cae recto, sin marcar la cintura"],
    ["Boxy fit", "ancho y cuadrado, largo normal"],
    ["Oversized", "grande y holgado, hombros caídos"],
    "Me da igual", "Otro",
  ],
  "prenda inferior": [
    ["Skinny", "bien pegado a la pierna"],
    ["Slim fit", "ajustado, con un poco de espacio"],
    ["Straight fit", "calce parejo, ni ajustado ni suelto"],
    ["Baggy", "holgado y suelto en toda la pierna"],
    "Me da igual", "Otro",
  ],
};

// Solo aplica cuando el tipo de prenda elegido es "pantalon", "shorts" o "top".
const SUBTIPO_OPCIONES = {
  "pantalon": ["Pantalón de buzo", "Pantalón de jeans", "Pantalón cargo", "Cualquiera"],
  "shorts": ["Short de jeans", "Short de tela", "Short cargo", "Short de baño", "Cualquiera"],
  "top": [
    ["Crop top / crop hoodie", "corto, deja el abdomen a la vista"],
    ["Baby tee", "corto y ajustado"],
    ["Top con breteles / halter", "sin mangas, amarrado al cuello"],
    ["Corset top", "ajustado, con costuras marcadas"],
    ["Tank top", "musculosa, sin mangas"],
    ["Camisas/blusas", "con botones, más estructurada"],
    "Cualquiera",
  ],
};

// El largo es independiente del corte (una prenda puede ser oversize Y
// crop al mismo tiempo). Solo aplica a las prendas tipo "top". Las claves
// tienen que calzar con el value que arma poblarOpciones (el texto de
// TIPO_PRENDA_OPCIONES en minuscula).
const LARGO_TIPOS = ["polera", "camiseta", "top"];
const LARGO_OPCIONES_LISTA = ["Corto/crop", "Largo normal", "Extra largo (longline)", "Cualquiera"];
const LARGO_OPCIONES = Object.fromEntries(LARGO_TIPOS.map((t) => [t, LARGO_OPCIONES_LISTA]));

// Manga solo aplica a "polera"; capucha y cierre solo a "poleron". Los 3
// son independientes del corte (una polera puede ser oversize Y manga
// larga a la vez).
const MANGA_OPCIONES = {
  "polera": ["Manga larga", "Manga corta", "Cualquiera"],
};
const CAPUCHA_OPCIONES = {
  "poleron": ["Con capucha", "Sin capucha", "Cualquiera"],
};
const CIERRE_OPCIONES = {
  "poleron": ["Con cierre", "Sin cierre (crewneck)", "Cualquiera"],
};

// Llena un select con una lista de opciones. Cada opcion puede ser texto
// simple o [texto, definicion] -- el value que manda el buscador siempre
// es el texto solo, en minuscula; la definicion solo se agrega a lo que
// se ve, entre parentesis.
function poblarOpciones(select, opciones) {
  select.innerHTML = "";
  for (const opcion of opciones) {
    const [texto, definicion] = Array.isArray(opcion) ? opcion : [opcion, null];
    const option = document.createElement("option");
    option.value = texto.toLowerCase();
    option.textContent = definicion ? `${texto} (${definicion})` : texto;
    select.appendChild(option);
  }
}

// Muestra/oculta un select dependiente (tipo de prenda o corte) segun la
// categoria elegida, y deja listo su campo de texto libre para "Otro".
function actualizarSelectDependiente(valorCategoria, opcionesPorCategoria, campo, select, otroCampo, otroInput) {
  otroCampo.classList.add("oculto");
  otroInput.required = false;
  otroInput.value = "";

  const opciones = opcionesPorCategoria[valorCategoria];
  if (opciones) {
    campo.classList.remove("oculto");
    poblarOpciones(select, opciones);
  } else {
    campo.classList.add("oculto");
    select.innerHTML = "";
  }
}

// Muestra/oculta un select dependiente que no necesita campo de texto libre
// (ej: subtipo de pantalon/shorts), segun el valor del select del que
// depende.
function actualizarSelectSimple(valorDelQueDepende, opcionesPorValor, campo, select) {
  const opciones = opcionesPorValor[valorDelQueDepende];
  if (opciones) {
    campo.classList.remove("oculto");
    poblarOpciones(select, opciones);
  } else {
    campo.classList.add("oculto");
    select.innerHTML = "";
  }
}

// El genero para "yo" sale del perfil guardado; para "regalo" sale del
// select de genero de ese mismo formulario.
function obtenerGeneroActual(prefix) {
  if (prefix === "yo") {
    const perfil = getPerfil();
    return perfil ? perfil.genero : "";
  }
  const generoSelect = document.querySelector(`#form-busqueda-${prefix} select[name="genero"]`);
  return generoSelect ? generoSelect.value : "";
}

// El largo solo se pregunta para mujer (u otro/sin especificar) -- para
// hombre se oculta aunque la prenda elegida sea de las que normalmente
// preguntan largo (polera, camiseta, top).
function actualizarLargo(prefix, valorTipoPrenda, largoCampo, largoSelect) {
  const esHombre = (obtenerGeneroActual(prefix) || "").toLowerCase() === "hombre";
  actualizarSelectSimple(valorTipoPrenda, esHombre ? {} : LARGO_OPCIONES, largoCampo, largoSelect);
}

// Para hombre, "Top" no se ofrece como opcion de prenda superior.
function opcionesTipoPrendaFiltradas(prefix) {
  const esHombre = (obtenerGeneroActual(prefix) || "").toLowerCase() === "hombre";
  if (!esHombre) return TIPO_PRENDA_OPCIONES;
  return {
    ...TIPO_PRENDA_OPCIONES,
    "prenda superior": TIPO_PRENDA_OPCIONES["prenda superior"].filter(
      (opcion) => (Array.isArray(opcion) ? opcion[0] : opcion).toLowerCase() !== "top"
    ),
  };
}

// Muestra/oculta los selects de tipo de prenda y corte segun la categoria
// elegida, y maneja el campo de texto libre que aparece cuando se elige
// "Otro" en cualquiera de los selects (categoria, tipo de prenda, corte,
// ocasion).
function configurarBusquedaPrenda(prefix) {
  const categoriaSelect = document.getElementById(`categoria-${prefix}`);
  const categoriaOtroCampo = document.getElementById(`campo-categoria-otro-${prefix}`);
  const categoriaOtroInput = categoriaOtroCampo.querySelector("input");

  const tipoPrendaCampo = document.getElementById(`campo-tipo-prenda-${prefix}`);
  const tipoPrendaSelect = document.getElementById(`tipo-prenda-${prefix}`);
  const tipoPrendaOtroCampo = document.getElementById(`campo-tipo-prenda-otro-${prefix}`);
  const tipoPrendaOtroInput = tipoPrendaOtroCampo.querySelector("input");

  const subtipoCampo = document.getElementById(`campo-subtipo-${prefix}`);
  const subtipoSelect = document.getElementById(`subtipo-${prefix}`);

  const largoCampo = document.getElementById(`campo-largo-${prefix}`);
  const largoSelect = document.getElementById(`largo-${prefix}`);

  const mangaCampo = document.getElementById(`campo-manga-${prefix}`);
  const mangaSelect = document.getElementById(`manga-${prefix}`);

  const capuchaCampo = document.getElementById(`campo-capucha-${prefix}`);
  const capuchaSelect = document.getElementById(`capucha-${prefix}`);

  const cierreCampo = document.getElementById(`campo-cierre-${prefix}`);
  const cierreSelect = document.getElementById(`cierre-${prefix}`);

  const corteCampo = document.getElementById(`campo-corte-${prefix}`);
  const corteSelect = document.getElementById(`corte-${prefix}`);
  const corteOtroCampo = document.getElementById(`campo-corte-otro-${prefix}`);
  const corteOtroInput = corteOtroCampo.querySelector("input");

  const ocasionSelect = document.getElementById(`ocasion-${prefix}`);
  const ocasionOtroCampo = document.getElementById(`campo-ocasion-otro-${prefix}`);
  const ocasionOtroInput = ocasionOtroCampo.querySelector("input");

  const gorroCaminoCampo = document.getElementById(`campo-gorro-camino-${prefix}`);
  const gorroCaminoSelect = document.getElementById(`gorro-camino-${prefix}`);
  const gorroColoresCampo = document.getElementById(`campo-gorro-colores-${prefix}`);
  const gorroOutfitCampo = document.getElementById(`campo-gorro-outfit-${prefix}`);
  const gorroFormaCampo = document.getElementById(`campo-gorro-forma-${prefix}`);
  const gorroFormaSelect = document.getElementById(`gorro-forma-${prefix}`);

  // Reevalua subtipo/largo/manga/capucha/cierre segun el tipo de prenda
  // elegido ahora mismo -- se llama cada vez que cambia el tipo de prenda,
  // o cada vez que se repuebla su select (cambio de categoria o de genero).
  function refrescarCamposDependientesDeTipo() {
    actualizarSelectSimple(tipoPrendaSelect.value, SUBTIPO_OPCIONES, subtipoCampo, subtipoSelect);
    actualizarLargo(prefix, tipoPrendaSelect.value, largoCampo, largoSelect);
    actualizarSelectSimple(tipoPrendaSelect.value, MANGA_OPCIONES, mangaCampo, mangaSelect);
    actualizarSelectSimple(tipoPrendaSelect.value, CAPUCHA_OPCIONES, capuchaCampo, capuchaSelect);
    actualizarSelectSimple(tipoPrendaSelect.value, CIERRE_OPCIONES, cierreCampo, cierreSelect);
  }

  // Gorro no usa corte/subtipo -- tiene su propio flujo (camino de color +
  // forma). "campo-gorro-camino" y "campo-gorro-forma" se muestran/ocultan
  // segun si la categoria elegida es "gorro"; dentro de eso, cual de los 2
  // caminos (colores especificos / combinar con outfit) se ve depende de
  // gorroCaminoSelect.
  function refrescarCamposGorro() {
    const esGorro = categoriaSelect.value === "gorro";
    gorroCaminoCampo.classList.toggle("oculto", !esGorro);
    gorroFormaCampo.classList.toggle("oculto", !esGorro);
    gorroCaminoSelect.required = esGorro;
    gorroFormaSelect.required = esGorro;

    if (!esGorro) {
      gorroColoresCampo.classList.add("oculto");
      gorroOutfitCampo.classList.add("oculto");
      return;
    }
    const camino = gorroCaminoSelect.value || "colores";
    gorroColoresCampo.classList.toggle("oculto", camino !== "colores");
    gorroOutfitCampo.classList.toggle("oculto", camino !== "outfit");
  }

  gorroCaminoSelect.addEventListener("change", refrescarCamposGorro);

  categoriaSelect.addEventListener("change", () => {
    const valor = categoriaSelect.value;
    const esOtro = valor === "otro";
    categoriaOtroCampo.classList.toggle("oculto", !esOtro);
    categoriaOtroInput.required = esOtro;

    actualizarSelectDependiente(
      valor, opcionesTipoPrendaFiltradas(prefix), tipoPrendaCampo, tipoPrendaSelect, tipoPrendaOtroCampo, tipoPrendaOtroInput
    );
    actualizarSelectDependiente(
      valor, CORTE_OPCIONES, corteCampo, corteSelect, corteOtroCampo, corteOtroInput
    );
    // El tipo de prenda se acaba de repoblar y el navegador deja
    // seleccionada su primera opcion sola, sin disparar "change" -- por eso
    // refrescarCamposDependientesDeTipo lee tipoPrendaSelect.value directo
    // en vez de asumir que quedo vacio.
    refrescarCamposDependientesDeTipo();
    refrescarCamposGorro();
  });

  tipoPrendaSelect.addEventListener("change", () => {
    const esOtro = tipoPrendaSelect.value === "otro";
    tipoPrendaOtroCampo.classList.toggle("oculto", !esOtro);
    tipoPrendaOtroInput.required = esOtro;

    refrescarCamposDependientesDeTipo();
  });

  // Si cambia el genero (solo aplica al formulario de regalo -- en "yo" el
  // genero viene fijo del perfil), hay que repoblar el tipo de prenda
  // (para sacar/agregar "Top") y re-evaluar los campos que dependen de el.
  const generoSelect = document.querySelector(`#form-busqueda-${prefix} select[name="genero"]`);
  if (generoSelect) {
    generoSelect.addEventListener("change", () => {
      actualizarSelectDependiente(
        categoriaSelect.value, opcionesTipoPrendaFiltradas(prefix),
        tipoPrendaCampo, tipoPrendaSelect, tipoPrendaOtroCampo, tipoPrendaOtroInput
      );
      refrescarCamposDependientesDeTipo();
    });
  }

  corteSelect.addEventListener("change", () => {
    const esOtro = corteSelect.value === "otro";
    corteOtroCampo.classList.toggle("oculto", !esOtro);
    corteOtroInput.required = esOtro;
  });

  ocasionSelect.addEventListener("change", () => {
    const esOtro = ocasionSelect.value === "otro";
    ocasionOtroCampo.classList.toggle("oculto", !esOtro);
    ocasionOtroInput.required = esOtro;
  });
}

// Si el select vale "otro", usa lo que el usuario escribio en el campo
// libre. Si vale "me da igual", no manda nada -- asi esa pregunta no
// filtra la busqueda.
function valorFinal(select, otroCampo) {
  if (select.value === "otro") {
    return otroCampo.querySelector("input").value;
  }
  if (select.value === "me da igual") {
    return "";
  }
  return select.value;
}

function leerBusquedaPrenda(prefix) {
  return {
    categoria: valorFinal(
      document.getElementById(`categoria-${prefix}`),
      document.getElementById(`campo-categoria-otro-${prefix}`)
    ),
    tipo_prenda: valorFinal(
      document.getElementById(`tipo-prenda-${prefix}`),
      document.getElementById(`campo-tipo-prenda-otro-${prefix}`)
    ),
    subtipo: document.getElementById(`subtipo-${prefix}`).value,
    largo: document.getElementById(`largo-${prefix}`).value,
    manga: document.getElementById(`manga-${prefix}`).value,
    capucha: document.getElementById(`capucha-${prefix}`).value,
    cierre: document.getElementById(`cierre-${prefix}`).value,
    corte: valorFinal(
      document.getElementById(`corte-${prefix}`),
      document.getElementById(`campo-corte-otro-${prefix}`)
    ),
    ocasion: valorFinal(
      document.getElementById(`ocasion-${prefix}`),
      document.getElementById(`campo-ocasion-otro-${prefix}`)
    ),
    precio: document.getElementById(`precio-${prefix}`).value,
    gorro_camino: document.getElementById(`gorro-camino-${prefix}`).value,
    gorro_colores: Array.from(
      document.querySelectorAll(`#campo-gorro-colores-${prefix} input[type="checkbox"]:checked`)
    ).map((el) => el.value),
    gorro_outfit: document.getElementById(`gorro-outfit-${prefix}`).value,
    gorro_forma: document.getElementById(`gorro-forma-${prefix}`).value,
  };
}

function mostrarSeccion(id) {
  for (const s of secciones) {
    document.getElementById(s).classList.toggle("oculto", s !== id);
  }
  document.getElementById("estado").textContent = "";
}

// Pone en un select el valor guardado de una busqueda anterior. Como
// valorFinal() ya convirtio "otro" en el texto libre y "me da igual" en ""
// al guardar, aca hacemos el camino inverso: si el valor calza con alguna
// opcion del select, se selecciona directo; si no calza con ninguna (era
// "otro"), se selecciona "otro" y se rellena su campo de texto libre; si
// viene vacio, se deja en "me da igual" (si existe esa opcion).
function restaurarSelectConOtro(select, otroCampo, otroInput, valor) {
  if (!valor) {
    const tieneMeDaIgual = Array.from(select.options).some((o) => o.value === "me da igual");
    if (tieneMeDaIgual) select.value = "me da igual";
    otroCampo.classList.add("oculto");
    otroInput.required = false;
    otroInput.value = "";
    return;
  }
  const coincide = Array.from(select.options).some((o) => o.value === valor.toLowerCase());
  if (coincide) {
    select.value = valor.toLowerCase();
    otroCampo.classList.add("oculto");
    otroInput.required = false;
  } else if (Array.from(select.options).some((o) => o.value === "otro")) {
    select.value = "otro";
    otroCampo.classList.remove("oculto");
    otroInput.required = true;
    otroInput.value = valor;
  }
}

// Vuelve a dejar la seccion de busqueda (yo o regalo) tal como estaba antes
// de mandar la ultima busqueda, usando el payload que se guardo en
// sessionStorage justo antes de ir a /resultados. Se usa cuando el usuario
// vuelve con el boton "atras" del navegador, para que no tenga que llenar
// todo el formulario de nuevo.
function restaurarFiltros(prefix, payload) {
  if (prefix === "regalo") {
    const form = document.getElementById("form-busqueda-regalo");
    if (payload.altura) form.elements["altura"].value = payload.altura;
    if (payload.peso) form.elements["peso"].value = payload.peso;
    if (payload.genero) form.elements["genero"].value = payload.genero;
  }

  const categoriaSelect = document.getElementById(`categoria-${prefix}`);
  const categoriaOtroCampo = document.getElementById(`campo-categoria-otro-${prefix}`);
  const categoriaOtroInput = categoriaOtroCampo.querySelector("input");
  restaurarSelectConOtro(categoriaSelect, categoriaOtroCampo, categoriaOtroInput, payload.categoria);
  // Dispara el listener de categoria: repuebla tipo de prenda y corte segun
  // esta categoria, y muestra/oculta los campos de gorro.
  categoriaSelect.dispatchEvent(new Event("change"));

  const tipoPrendaSelect = document.getElementById(`tipo-prenda-${prefix}`);
  const tipoPrendaOtroCampo = document.getElementById(`campo-tipo-prenda-otro-${prefix}`);
  const tipoPrendaOtroInput = tipoPrendaOtroCampo.querySelector("input");
  restaurarSelectConOtro(tipoPrendaSelect, tipoPrendaOtroCampo, tipoPrendaOtroInput, payload.tipo_prenda);
  // Dispara el listener de tipo de prenda: repuebla subtipo/largo/manga/capucha/cierre.
  tipoPrendaSelect.dispatchEvent(new Event("change"));

  const subtipoSelect = document.getElementById(`subtipo-${prefix}`);
  if (payload.subtipo) subtipoSelect.value = payload.subtipo;
  const largoSelect = document.getElementById(`largo-${prefix}`);
  if (payload.largo) largoSelect.value = payload.largo;
  const mangaSelect = document.getElementById(`manga-${prefix}`);
  if (payload.manga) mangaSelect.value = payload.manga;
  const capuchaSelect = document.getElementById(`capucha-${prefix}`);
  if (payload.capucha) capuchaSelect.value = payload.capucha;
  const cierreSelect = document.getElementById(`cierre-${prefix}`);
  if (payload.cierre) cierreSelect.value = payload.cierre;

  const corteSelect = document.getElementById(`corte-${prefix}`);
  const corteOtroCampo = document.getElementById(`campo-corte-otro-${prefix}`);
  const corteOtroInput = corteOtroCampo.querySelector("input");
  restaurarSelectConOtro(corteSelect, corteOtroCampo, corteOtroInput, payload.corte);

  const ocasionSelect = document.getElementById(`ocasion-${prefix}`);
  const ocasionOtroCampo = document.getElementById(`campo-ocasion-otro-${prefix}`);
  const ocasionOtroInput = ocasionOtroCampo.querySelector("input");
  restaurarSelectConOtro(ocasionSelect, ocasionOtroCampo, ocasionOtroInput, payload.ocasion);

  const precioSelect = document.getElementById(`precio-${prefix}`);
  if (payload.precio !== undefined) precioSelect.value = payload.precio;

  const gorroCaminoSelect = document.getElementById(`gorro-camino-${prefix}`);
  if (payload.gorro_camino) gorroCaminoSelect.value = payload.gorro_camino;
  const gorroOutfitSelect = document.getElementById(`gorro-outfit-${prefix}`);
  if (payload.gorro_outfit) gorroOutfitSelect.value = payload.gorro_outfit;
  const gorroFormaSelect = document.getElementById(`gorro-forma-${prefix}`);
  if (payload.gorro_forma) gorroFormaSelect.value = payload.gorro_forma;
  if (Array.isArray(payload.gorro_colores)) {
    document.querySelectorAll(`#campo-gorro-colores-${prefix} input[type="checkbox"]`).forEach((cb) => {
      cb.checked = payload.gorro_colores.includes(cb.value);
    });
  }
  // Dispara el listener de gorro-camino: muestra colores u outfit segun corresponda.
  gorroCaminoSelect.dispatchEvent(new Event("change"));

  mostrarSeccion(`seccion-busqueda-${prefix}`);
}

function mostrarPasoInicial() {
  const perfil = getPerfil();
  if (perfil) {
    document.getElementById("resumen-perfil").textContent =
      `Hola ${perfil.nombre}, tu perfil: ${perfil.genero}, ${perfil.edad} años.`;
    mostrarSeccion("seccion-quien");
  } else {
    mostrarSeccion("seccion-perfil");
  }
}

// Llena el formulario de perfil con los datos ya guardados, para poder
// editarlos en vez de tener que volver a escribir todo desde cero.
function precargarPerfil(perfil) {
  const form = document.getElementById("form-perfil");
  for (const campo of form.elements) {
    if (campo.name && perfil[campo.name] !== undefined) {
      campo.value = perfil[campo.name];
    }
  }
}

// Corre la busqueda (con la animacion de carga de comun.js) y, cuando
// termina, guarda el resultado y manda al usuario a /resultados -- ahi se
// ve solo el resultado, en una pagina aparte, no mezclado con el formulario.
async function buscar(payload) {
  const estado = document.getElementById("estado");
  estado.textContent = "";

  try {
    const data = await buscarConAnimacion(payload);
    sessionStorage.setItem("ultimoPayload", JSON.stringify(payload));
    sessionStorage.setItem("resultados", JSON.stringify(data.recomendaciones || []));
    sessionStorage.setItem("sinTalla", String(Boolean(data.sin_talla)));
    window.location.href = "/resultados";
  } catch (err) {
    estado.textContent = "Algo salió mal: " + err.message;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  configurarBusquedaPrenda("yo");
  configurarBusquedaPrenda("regalo");

  // Si el usuario llego a esta pagina con el boton "atras" del navegador
  // (viene de /resultados) y hay una busqueda guardada de esta sesion,
  // volvemos directo a los filtros ya llenos en vez del primer paso del
  // formulario -- asi no pierde lo que ya habia elegido. Si entro de
  // cualquier otra forma (primera visita, recargar, o el link "Hacer una
  // nueva busqueda"), el flujo normal parte desde el principio.
  const navegacion = performance.getEntriesByType("navigation")[0];
  const vieneDeAtras = navegacion && navegacion.type === "back_forward";
  const ultimoPayloadGuardado = sessionStorage.getItem("ultimoPayload");

  if (vieneDeAtras && ultimoPayloadGuardado) {
    try {
      const payload = JSON.parse(ultimoPayloadGuardado);
      restaurarFiltros(payload.modo === "regalo" ? "regalo" : "yo", payload);
    } catch (e) {
      mostrarPasoInicial();
    }
  } else {
    mostrarPasoInicial();
  }

  document.getElementById("form-perfil").addEventListener("submit", (e) => {
    e.preventDefault();
    const datos = Object.fromEntries(new FormData(e.target).entries());
    guardarPerfil(datos);
    mostrarPasoInicial();
  });

  document.getElementById("btn-para-mi").addEventListener("click", () => {
    mostrarSeccion("seccion-busqueda-yo");
  });

  document.getElementById("btn-para-otro").addEventListener("click", () => {
    mostrarSeccion("seccion-busqueda-regalo");
  });

  document.getElementById("link-editar-perfil").addEventListener("click", (e) => {
    e.preventDefault();
    const perfil = getPerfil();
    if (perfil) {
      precargarPerfil(perfil);
    }
    mostrarSeccion("seccion-perfil");
  });

  document.querySelectorAll(".volver").forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      mostrarSeccion(link.dataset.volver);
    });
  });

  document.getElementById("form-busqueda-yo").addEventListener("submit", (e) => {
    e.preventDefault();
    const perfilCompleto = getPerfil() || {};
    // Solo mandamos al servidor lo necesario para buscar, nunca datos
    // personales sensibles (nombre, orientacion sexual). El gmail SI se
    // manda ahora (como "email", aparte de "perfil") -- es el identificador
    // que usa Koko para guardar el historial de este usuario y
    // personalizar sus consejos. Ver seccion "Koko" en CLAUDE.md.
    const perfilParaBuscar = {
      genero: perfilCompleto.genero,
      edad: perfilCompleto.edad,
      altura: perfilCompleto.altura,
      peso: perfilCompleto.peso,
      hobbie: perfilCompleto.hobbie,
    };
    buscar({
      modo: "yo", email: perfilCompleto.gmail || "", perfil: perfilParaBuscar,
      ...leerBusquedaPrenda("yo"),
    });
  });

  document.getElementById("form-busqueda-regalo").addEventListener("submit", (e) => {
    e.preventDefault();
    const datos = Object.fromEntries(new FormData(e.target).entries());
    buscar({ modo: "regalo", ...datos, ...leerBusquedaPrenda("regalo") });
  });
});
