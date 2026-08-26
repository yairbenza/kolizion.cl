// JS del boton "Continuar con Google" -- vive aparte de comun.js (que
// carga en TODAS las paginas) porque solo lo necesitan /login y /registro.
// Ver docs/cuentas.md para el flujo completo.

async function iniciarLoginGoogle(siguiente, recordar) {
  const boton = document.getElementById("btn-google-login");
  if (boton) {
    boton.disabled = true;
    boton.textContent = "Conectando con Google...";
  }
  try {
    // El perfil de localStorage (si hay uno) viaja al servidor para que,
    // si la cuenta resulta ser nueva, se use para completar los datos que
    // Google no manda (altura, peso, direccion, hobbies, telefono) -- ver
    // /auth/google/iniciar en app.py. "recordar" es el checkbox "mantener
    // sesion iniciada" (ausente/false en Safari, ver login.html/registro.html)
    // -- se guarda en la sesion server-side y se usa recien en el callback.
    const perfil = getPerfil();
    const resp = await fetch("/auth/google/iniciar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ perfil, siguiente, recordar: Boolean(recordar) }),
    });
    const data = await resp.json();
    if (data.url) {
      window.location.href = data.url;
    } else {
      throw new Error(data.error || "No se pudo iniciar Google login");
    }
  } catch (e) {
    if (boton) {
      boton.disabled = false;
      boton.textContent = "Continuar con Google";
    }
    alert("No se pudo conectar con Google. Intenta con tu correo y contraseña.");
  }
}
