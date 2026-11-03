// Genera y configura el proyecto de Xcode de la app de iOS.
//
// No se sube la carpeta ios/ a git: se genera desde cero en cada build (en
// Codemagic, ver ../../codemagic.yaml) con "npx cap add ios" y despues este
// script le aplica toda la configuracion propia de KOLIZION. Asi el proyecto
// siempre sale igual y no hay que abrir Xcode a mano.
//
// Uso:  node scripts/preparar-ios.mjs
// Variables de entorno opcionales:
//   GOOGLE_IOS_CLIENT_ID  Client ID tipo iOS de Google (para "Continuar con Google")
//   BUILD_NUMBER          numero de build (Codemagic lo pone solo)
import { execSync } from "node:child_process";
import { copyFileSync, existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import plist from "plist";

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), "..");
const IOS_APP = join(RAIZ, "ios", "App");
const APP = join(IOS_APP, "App");
const paquete = JSON.parse(readFileSync(join(RAIZ, "package.json"), "utf8"));

function correr(comando) {
  console.log(`$ ${comando}`);
  execSync(comando, { cwd: RAIZ, stdio: "inherit" });
}

// 1. Crear el proyecto nativo si no existe y copiar plugins/config.
if (!existsSync(IOS_APP)) correr("npx cap add ios");
correr("npx cap sync ios");

// 2. Info.plist: nombre, permisos (textos que ve la persona al pedirlos),
//    orientacion, cifrado y esquema de URL de Google.
const rutaInfo = join(APP, "Info.plist");
const info = plist.parse(readFileSync(rutaInfo, "utf8"));
Object.assign(info, {
  CFBundleDisplayName: "KOLIZION",
  NSLocationWhenInUseUsageDescription:
    "KOLIZION usa tu ubicación solo si tocas \"Usar mi ubicación actual\", para completar tu comuna y estimar el envío.",
  NSCameraUsageDescription: "KOLIZION usa la cámara solo si quieres sacarte una foto de perfil.",
  NSPhotoLibraryUsageDescription: "KOLIZION accede a tus fotos solo para elegir tu foto de perfil.",
  ITSAppUsesNonExemptEncryption: false,
  UISupportedInterfaceOrientations: ["UIInterfaceOrientationPortrait"],
  UIRequiresFullScreen: true,
});
delete info["UISupportedInterfaceOrientations~ipad"];

const googleClientId = (process.env.GOOGLE_IOS_CLIENT_ID || "").trim();
if (googleClientId.endsWith(".apps.googleusercontent.com")) {
  const esquema = "com.googleusercontent.apps." + googleClientId.replace(".apps.googleusercontent.com", "");
  const tipos = (info.CFBundleURLTypes || []).filter((t) => !(t.CFBundleURLSchemes || []).some((s) => s.startsWith("com.googleusercontent.apps.")));
  tipos.push({ CFBundleURLName: "google", CFBundleURLSchemes: [esquema] });
  info.CFBundleURLTypes = tipos;
  info.GIDClientID = googleClientId;
} else {
  console.warn("AVISO: falta GOOGLE_IOS_CLIENT_ID -- \"Continuar con Google\" no funcionará en esta build.");
}
writeFileSync(rutaInfo, plist.build(info));

// 3. Capacidades: notificaciones push y "Iniciar sesión con Apple".
writeFileSync(
  join(APP, "App.entitlements"),
  plist.build({
    "aps-environment": "production",
    "com.apple.developer.applesignin": ["Default"],
  }),
);

// 4. Proyecto de Xcode: solo iPhone (no iPad), entitlements y versiones.
const rutaProyecto = join(IOS_APP, "App.xcodeproj", "project.pbxproj");
let proyecto = readFileSync(rutaProyecto, "utf8");
proyecto = proyecto.replace(/TARGETED_DEVICE_FAMILY = "?[0-9,]+"?;/g, "TARGETED_DEVICE_FAMILY = 1;");
proyecto = proyecto.replace(/MARKETING_VERSION = [^;]+;/g, `MARKETING_VERSION = ${paquete.version};`);
if (process.env.BUILD_NUMBER) {
  proyecto = proyecto.replace(/CURRENT_PROJECT_VERSION = [^;]+;/g, `CURRENT_PROJECT_VERSION = ${process.env.BUILD_NUMBER};`);
}
if (!proyecto.includes("CODE_SIGN_ENTITLEMENTS")) {
  proyecto = proyecto.replace(/(\s*)(INFOPLIST_FILE = App\/Info\.plist;)/g, "$1$2$1CODE_SIGN_ENTITLEMENTS = App/App.entitlements;");
}
writeFileSync(rutaProyecto, proyecto);

// 5. AppDelegate: entregar el token de push a Capacitor y devolver el
//    control a Google despues de su login.
const rutaDelegate = join(APP, "AppDelegate.swift");
let delegate = readFileSync(rutaDelegate, "utf8");
if (!delegate.includes("KOLIZION")) {
  delegate = delegate.replace(
    "import Capacitor\n",
    "import Capacitor\n#if canImport(GoogleSignIn)\nimport GoogleSignIn\n#endif\n",
  );
  delegate = delegate.replace(
    "return ApplicationDelegateProxy.shared.application(app, open: url, options: options)",
    "#if canImport(GoogleSignIn)\n        if GIDSignIn.sharedInstance.handle(url) { return true }\n        #endif\n        return ApplicationDelegateProxy.shared.application(app, open: url, options: options)",
  );
  const ultimaLlave = delegate.lastIndexOf("}");
  delegate =
    delegate.slice(0, ultimaLlave) +
    `
    // KOLIZION: notificaciones push (plugin @capacitor/push-notifications).
    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        NotificationCenter.default.post(name: .capacitorDidRegisterForRemoteNotifications, object: deviceToken)
    }

    func application(_ application: UIApplication, didFailToRegisterForRemoteNotificationsWithError error: Error) {
        NotificationCenter.default.post(name: .capacitorDidFailToRegisterForRemoteNotifications, object: error)
    }
` +
    delegate.slice(ultimaLlave);
  writeFileSync(rutaDelegate, delegate);
}

// 6. Icono (1024x1024, sin transparencia) y pantalla de carga.
const carpetaIcono = join(APP, "Assets.xcassets", "AppIcon.appiconset");
copyFileSync(join(RAIZ, "assets", "icono-1024.png"), join(carpetaIcono, "AppIcon-1024.png"));
for (const archivo of readdirSync(carpetaIcono)) {
  if (archivo.endsWith(".png") && archivo !== "AppIcon-1024.png") execSync(`rm "${join(carpetaIcono, archivo)}"`);
}
writeFileSync(
  join(carpetaIcono, "Contents.json"),
  JSON.stringify({
    images: [{ filename: "AppIcon-1024.png", idiom: "universal", platform: "ios", size: "1024x1024" }],
    info: { author: "xcode", version: 1 },
  }, null, 2),
);
const carpetaSplash = join(APP, "Assets.xcassets", "Splash.imageset");
if (existsSync(carpetaSplash)) {
  for (const archivo of readdirSync(carpetaSplash)) {
    if (archivo.endsWith(".png")) copyFileSync(join(RAIZ, "assets", "splash-2732.png"), join(carpetaSplash, archivo));
  }
}

console.log("Proyecto de iOS listo en ios-app/ios/App (abrir App.xcworkspace).");
