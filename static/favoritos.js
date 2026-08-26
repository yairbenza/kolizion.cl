// Pagina /favoritos: lista de todos los productos que el usuario marco con
// la estrella, asociados a su correo (mismo identificador que usa el
// historial de Koko -- ver emailFavoritos en comun.js). Reusa la misma
// tarjeta de /resultados (renderResultados) -- aca la estrella arranca
// siempre llena (son favoritos) y, a diferencia de resultados/vitrina,
// sacar el favorito saca la tarjeta entera de la lista (no solo apaga la
// estrella) -- ver "quitarSiNoMarcado" en conectarBotonFavorito (comun.js).

document.addEventListener("DOMContentLoaded", async () => {
  const vacio = document.getElementById("favoritos-vacio");
  const sinPerfil = document.getElementById("favoritos-sin-perfil");
  const estado = document.getElementById("estado");
  const btnBorrarTodos = document.getElementById("btn-borrar-favoritos");

  const email = emailFavoritos();
  if (!email) {
    sinPerfil.classList.remove("oculto");
    return;
  }

  btnBorrarTodos.addEventListener("click", async () => {
    if (!confirm("¿Seguro que quieres borrar todos tus favoritos?")) return;
    try {
      const resp = await fetch("/api/favoritos?email=" + encodeURIComponent(email), { method: "DELETE" });
      if (!resp.ok) throw new Error("Error del servidor: " + resp.status);
      document.getElementById("favoritos-lista").innerHTML = "";
      btnBorrarTodos.classList.add("oculto");
      vacio.classList.remove("oculto");
    } catch (err) {
      estado.textContent = "Algo salió mal borrando tus favoritos: " + err.message;
    }
  });

  try {
    const resp = await fetch("/api/favoritos?email=" + encodeURIComponent(email));
    const data = await resp.json();
    const favoritos = data.favoritos || [];
    if (favoritos.length === 0) {
      vacio.classList.remove("oculto");
      return;
    }
    const favoritosSet = new Set(favoritos.map((f) => f.nombre));
    renderResultados("favoritos-lista", favoritos, { favoritosSet, quitarSiNoMarcado: true });
    btnBorrarTodos.classList.remove("oculto");
  } catch (err) {
    estado.textContent = "Algo salió mal cargando tus favoritos: " + err.message;
  }
});
