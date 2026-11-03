// Puente con las funciones nativas del iPhone (2026-11-03, ver
// ios-app/README.md). Solo se carga dentro de la app de iOS (_pwa_meta.html,
// cuando es_app) -- en el navegador normal este archivo ni se descarga.
//
// La app es una "ventana" (Capacitor) que abre kolizion.cl, y le suma 4
// cosas que una pagina web sola no puede hacer:
//   1. Login nativo con Google y Apple (Google bloquea su login web en apps).
//   2. Notificaciones push (Apple).
//   3. Hoja de compartir del iPhone en cada producto.
//   4. Favoritos sin conexion: se copian al telefono (con sus fotos) y la
//      pantalla offline de la app (ios-app/www/offline.html) los muestra.
// Ademas, los links a tiendas se abren dentro de la app (navegador interno)
// y los de Instagram/WhatsApp en sus propias apps.
(function () {
  "use strict";
  var C = window.Capacitor;
  if (!C || typeof C.nativePromise !== "function") return;

  // --- Llamadas a plugins nativos -------------------------------------------
  // Se llama a los plugins por nombre (sin @capacitor/core empaquetado,
  // porque la pagina viene del servidor y no de un bundle de la app).
  function disponible(plugin) {
    if (typeof C.isPluginAvailable === "function") return C.isPluginAvailable(plugin);
    return (C.PluginHeaders || []).some(function (h) { return h.name === plugin; });
  }
  function llamar(plugin, metodo, opciones) {
    return C.nativePromise(plugin, metodo, opciones || {});
  }
  function escuchar(plugin, evento, callback) {
    C.nativeCallback(plugin, "addListener", { eventName: evento }, callback);
  }

  var CLAVE_FAVORITOS = "kz_favoritos_offline";
  var CARPETA_FOTOS = "favoritos";

  // --- Links externos -------------------------------------------------------
  var HOSTS_APP_PROPIA = /(^|\.)(instagram\.com|wa\.me|whatsapp\.com|tiktok\.com)$/i;

  function abrirExterno(url) {
    var destino;
    try { destino = new URL(url, location.href); } catch (e) { return; }
    if (destino.origin === location.origin) {
      // Links propios (ej. /ir/<tienda>, que redirige a la tienda): se
      // navegan en la misma ventana para conservar la sesion; si terminan
      // en otro dominio, la app los abre en Safari.
      location.href = destino.href;
    } else if (HOSTS_APP_PROPIA.test(destino.hostname) && disponible("AppLauncher")) {
      llamar("AppLauncher", "openUrl", { url: destino.href });
    } else if (disponible("Browser")) {
      llamar("Browser", "open", { url: destino.href, presentationStyle: "fullscreen" });
    } else {
      location.href = destino.href;
    }
  }

  window.open = function (url) {
    if (url) abrirExterno(url);
    return null;
  };

  document.addEventListener("click", function (evento) {
    var link = evento.target.closest && evento.target.closest("a[href]");
    if (!link || evento.defaultPrevented) return;
    var href = link.getAttribute("href") || "";
    if (!href || href === "#" || href.indexOf("javascript:") === 0 || href.indexOf("mailto:") === 0 || href.indexOf("tel:") === 0) return;
    var destino;
    try { destino = new URL(href, location.href); } catch (e) { return; }
    var esExterno = destino.origin !== location.origin;
    if (esExterno || link.target === "_blank") {
      evento.preventDefault();
      abrirExterno(destino.href);
    }
  });
  // (Fase normal, no "captura", a proposito: si otro script ya maneja el
  // clic -- ej. la animacion "Te llevamos a la tienda" de comun.js, que
  // despues llama a window.open -- ese hace preventDefault y aca no se
  // abre dos veces.)

  // --- Compartir -------------------------------------------------------------
  function compartir(datos) {
    if (!disponible("Share")) return Promise.reject(new Error("Share no disponible"));
    return llamar("Share", "share", {
      title: datos.title || "KOLIZION",
      text: datos.text || "",
      url: datos.url || location.origin,
      dialogTitle: "Compartir",
    });
  }

  // --- Login nativo (Google y Apple) -----------------------------------------
  var loginInicializado = null;

  function inicializarLogin() {
    if (!loginInicializado) {
      var config = window.KZ_CONFIG || {};
      var opciones = { apple: {} };
      if (config.googleIosClientId) opciones.google = { iOSClientId: config.googleIosClientId, mode: "online" };
      loginInicializado = llamar("SocialLogin", "initialize", opciones);
    }
    return loginInicializado;
  }

  function perfilLocal() {
    try { return typeof getPerfil === "function" ? getPerfil() : null; } catch (e) { return null; }
  }

  function botonCargando(id, texto) {
    var boton = document.getElementById(id);
    if (!boton) return function () {};
    var original = boton.innerHTML;
    boton.disabled = true;
    boton.textContent = texto;
    return function () { boton.disabled = false; boton.innerHTML = original; };
  }

  async function login(proveedor, siguiente) {
    if (!disponible("SocialLogin")) {
      alert("Esta versión de la app no tiene ese inicio de sesión. Actualízala desde la App Store.");
      return;
    }
    var restaurar = botonCargando(proveedor === "apple" ? "btn-apple-login" : "btn-google-login", "Conectando...");
    try {
      await inicializarLogin();
      var opciones = proveedor === "apple"
        ? { provider: "apple", options: { scopes: ["email", "name"] } }
        : { provider: "google", options: { scopes: ["email", "profile"] } };
      var respuesta = await llamar("SocialLogin", "login", opciones);
      var r = (respuesta && respuesta.result) || {};
      var perfil = r.profile || {};
      var idToken = r.idToken || r.identityToken || "";
      if (!idToken) throw new Error("sin id_token");

      var resp = await fetch("/auth/nativo/" + proveedor, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id_token: idToken,
          nombre: perfil.givenName || "",
          apellido: perfil.familyName || "",
          perfil: perfilLocal(),
          siguiente: siguiente || "/",
        }),
      });
      var data = await resp.json();
      if (!resp.ok || !data.url) throw new Error(data.error || "No se pudo iniciar sesión");
      location.href = data.url;
    } catch (error) {
      restaurar();
      var mensaje = String((error && error.message) || "");
      // Cerrar la ventana de Google/Apple sin elegir cuenta no es un error.
      if (/cancel/i.test(mensaje) || /1001/.test(mensaje)) return;
      alert(mensaje && mensaje.length < 200 && !/sin id_token/.test(mensaje)
        ? mensaje
        : "No pudimos iniciar sesión. Intenta de nuevo o entra con tu correo.");
    }
  }

  // --- Notificaciones push ----------------------------------------------------
  var CLAVE_PUSH_PREGUNTADO = "kz_push_preguntado";

  function configurarPush() {
    if (!disponible("PushNotifications")) return;

    escuchar("PushNotifications", "registration", function (token) {
      if (!token || !token.value) return;
      fetch("/api/push/registrar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: token.value }),
      }).catch(function () {});
    });

    // Al tocar un aviso: si trae un link interno (ej. /vitrina), se abre.
    escuchar("PushNotifications", "pushNotificationActionPerformed", function (accion) {
      var datos = (accion && accion.notification && accion.notification.data) || {};
      var url = datos.url || "";
      if (url.charAt(0) === "/" && url.charAt(1) !== "/") location.href = url;
    });

    llamar("PushNotifications", "checkPermissions").then(function (estado) {
      if (estado.receive === "granted") {
        // Una vez por apertura de la app (no en cada pagina): asi el token
        // queda asociado a la cuenta si la persona inicio sesion.
        var yaRegistrado = false;
        try { yaRegistrado = sessionStorage.getItem("kz_push_registrado") === "1"; } catch (e) {}
        if (!yaRegistrado) {
          try { sessionStorage.setItem("kz_push_registrado", "1"); } catch (e) {}
          llamar("PushNotifications", "register");
        }
        return;
      }
      if (estado.receive !== "prompt" && estado.receive !== "prompt-with-rationale") return;
      var yaPregunto = false;
      try { yaPregunto = localStorage.getItem(CLAVE_PUSH_PREGUNTADO) === "1"; } catch (e) {}
      if (yaPregunto) return;
      // Se pide permiso una sola vez, unos segundos despues de abrir (no
      // apenas carga la primera pantalla).
      setTimeout(function () {
        try { localStorage.setItem(CLAVE_PUSH_PREGUNTADO, "1"); } catch (e) {}
        llamar("PushNotifications", "requestPermissions").then(function (r) {
          if (r.receive === "granted") llamar("PushNotifications", "register");
        });
      }, 4000);
    }).catch(function () {});
  }

  // --- Favoritos sin conexion -------------------------------------------------
  // Copia los favoritos (y una foto chica de cada uno) al telefono. Corre al
  // abrir cualquier pagina (como maximo cada 10 min) y siempre poco despues
  // de marcar o desmarcar una estrella.
  var CLAVE_ULTIMA_SYNC = "kz_favoritos_sync";
  var MAX_FAVORITOS_OFFLINE = 60;
  var sincronizando = false;

  function hashTexto(texto) {
    var h = 0;
    for (var i = 0; i < texto.length; i++) h = (h * 31 + texto.charCodeAt(i)) | 0;
    return (h >>> 0).toString(36);
  }

  function urlFotoChica(url) {
    // Las fotos de Shopify aceptan ?width= -- se baja una version liviana.
    try {
      var u = new URL(url, location.href);
      if (/cdn\.shopify\.com$|\/cdn\/shop\//.test(u.hostname + u.pathname)) u.searchParams.set("width", "400");
      return u.href;
    } catch (e) { return url; }
  }

  async function guardarFoto(url) {
    if (!url || !disponible("Filesystem")) return "";
    var absoluta = urlFotoChica(url);
    var ruta = CARPETA_FOTOS + "/" + hashTexto(absoluta) + ".img";
    try {
      await llamar("Filesystem", "stat", { path: ruta, directory: "DATA" });
      return ruta; // ya estaba guardada
    } catch (e) { /* no existe todavia */ }
    try {
      var resp = await llamar("CapacitorHttp", "request", { url: absoluta, method: "GET", responseType: "blob" });
      if (!resp || resp.status !== 200 || typeof resp.data !== "string") return "";
      await llamar("Filesystem", "writeFile", { path: ruta, data: resp.data, directory: "DATA", recursive: true });
      return ruta;
    } catch (e) {
      return "";
    }
  }

  async function sincronizarFavoritos(forzar) {
    if (sincronizando || !disponible("Preferences")) return;
    var email = typeof emailFavoritos === "function" ? emailFavoritos() : "";
    if (!email) return;
    var ahora = Date.now();
    var ultima = 0;
    try { ultima = Number(localStorage.getItem(CLAVE_ULTIMA_SYNC) || 0); } catch (e) {}
    if (!forzar && ahora - ultima < 10 * 60 * 1000) return;

    sincronizando = true;
    try {
      var resp = await fetch("/api/favoritos?email=" + encodeURIComponent(email));
      if (!resp.ok) return;
      var data = await resp.json();
      var lista = (data.favoritos || []).slice(-MAX_FAVORITOS_OFFLINE).reverse();
      var items = [];
      for (var i = 0; i < lista.length; i++) {
        var f = lista[i];
        items.push({
          nombre: f.nombre || "",
          tienda: f.tienda || "",
          precio: f.precio || "",
          link: f.link ? new URL(f.link, location.href).href : "",
          foto: await guardarFoto(f.imagen),
        });
      }
      await llamar("Preferences", "set", {
        key: CLAVE_FAVORITOS,
        value: JSON.stringify({ actualizado: new Date().toISOString(), email: email, items: items }),
      });
      try { localStorage.setItem(CLAVE_ULTIMA_SYNC, String(ahora)); } catch (e) {}
    } catch (e) {
      // Sin conexion o error del servidor: queda la copia anterior.
    } finally {
      sincronizando = false;
    }
  }

  // Detecta cuando se marca/desmarca un favorito (POST/DELETE a
  // /api/favoritos desde comun.js/favoritos.js) para actualizar la copia.
  var fetchOriginal = window.fetch;
  window.fetch = function (recurso, opciones) {
    var promesa = fetchOriginal.apply(this, arguments);
    try {
      var url = typeof recurso === "string" ? recurso : (recurso && recurso.url) || "";
      var metodo = ((opciones && opciones.method) || "GET").toUpperCase();
      if (url.indexOf("/api/favoritos") !== -1 && metodo !== "GET") {
        promesa.then(function () { setTimeout(function () { sincronizarFavoritos(true); }, 1500); });
      }
    } catch (e) {}
    return promesa;
  };

  function limpiarDatosLocales() {
    var tareas = [];
    if (disponible("Preferences")) tareas.push(llamar("Preferences", "remove", { key: CLAVE_FAVORITOS }));
    if (disponible("Filesystem")) {
      tareas.push(llamar("Filesystem", "rmdir", { path: CARPETA_FOTOS, directory: "DATA", recursive: true }).catch(function () {}));
    }
    return Promise.all(tareas).catch(function () {});
  }

  // Al cerrar sesion, se borra la copia offline de favoritos de esa cuenta.
  document.addEventListener("submit", function (evento) {
    var form = evento.target;
    if (form && form.getAttribute && form.getAttribute("action") === "/logout") limpiarDatosLocales();
  }, true);

  window.KZNativo = {
    login: login,
    compartir: compartir,
    sincronizarFavoritos: sincronizarFavoritos,
    limpiarDatosLocales: limpiarDatosLocales,
  };

  // Color de los iconos de la barra de estado (hora, bateria): oscuros en
  // modo claro, claros en modo oscuro (data-theme, ver _tema_inline.html).
  function ajustarBarraEstado() {
    if (!disponible("StatusBar")) return;
    var oscuro = document.documentElement.getAttribute("data-theme") === "dark";
    llamar("StatusBar", "setStyle", { style: oscuro ? "DARK" : "LIGHT" }).catch(function () {});
  }
  new MutationObserver(ajustarBarraEstado).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  function iniciar() {
    ajustarBarraEstado();
    configurarPush();
    sincronizarFavoritos(location.pathname === "/favoritos");
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
