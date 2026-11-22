<img width="330" height="230" alt="image" src="https://github.com/user-attachments/assets/1d1d8f52-cb5d-429e-bb72-e43ee86b1a44" />


**Dragon City Legacy** — Un proyecto de preservación histórica del juego original en Adobe Flash (2012–2020), mantenido vivo por la comunidad.

[![Estado](https://img.shields.io/badge/Estado-En_Desarrollo-orange)]()
[![Versión del juego](https://img.shields.io/badge/Juego-2.1.2c-green)]()
[![Plataforma](https://img.shields.io/badge/Windows-10%20%7C%2011%20(64--bit)-blue)]()
[![Electron](https://img.shields.io/badge/Launcher-Electron-47848F)]()
[![Comandos](https://img.shields.io/badge/Comandos_Implementados-92%2F104-yellow)]()

---

## ⚠️ Aviso Legal / Legal Notice

**Este proyecto es un esfuerzo comunitario, sin fines de lucro, de uso educativo y de preservación histórica.**
*Dragon City* y todos sus activos visuales, de audio y de marca son propiedad intelectual
de **SocialPoint / Take-Two Interactive**. Este proyecto **no está afiliado, patrocinado ni respaldado** por ellos.

Este servidor local:
- **NO** tiene fines de lucro, no acepta pagos ni donaciones a cambio del juego, y no lo distribuye comercialmente.
- **NO** compite con las versiones actuales del juego (móvil / Windows).
- Utiliza protocolos y activos de la versión de **Adobe Flash**, plataforma oficialmente descontinuada desde diciembre de 2020, cuyos servidores originales ya no funcionan.

Si eres representante legal de SocialPoint o Take-Two Interactive y tienes alguna consulta,
puedes contactarme antes de tomar cualquier acción formal.

---

## 🛠️ Estado del Desarrollo

El servidor local es funcional y permite jugar.

| Módulo | Estado |
|---|---|
| Motor de Cría | ✅ Funcional |
| Mundo Ancestral | ✅ Todos sus comandos implementados |
| Comandos (`packet.php`) | ⚠️ 92 / 104 implementados |
| Minijuego: Reflejo del Dragón | ✅ Funcional |
| Minijuego: Memoria | ❌ En desarrollo |
| Minijuego: Tesoro | ❌ En desarrollo |

### 🎮 Sobre los Minijuegos

Los minijuegos incluidos en este proyecto **no forman parte del Dragon City original**.
Son creaciones propias desarrolladas para suplir una limitación técnica del entorno local:
dado que el sistema de compra de gemas no puede funcionar sin los servidores oficiales,
estos minijuegos ofrecen al jugador una forma alternativa de obtenerlas y disfrutar
del juego de manera completa.

---

## 🚀 Instalación

### Requisitos

- Windows 10 u 11 de **64 bits**.
- El **puerto 80** libre (no debe estar en uso por otro programa, como IIS o Apache).

> Ya **no** necesitas un navegador con Flash: el launcher incluye todo lo necesario.

### 1. Descargar

- Descarga la última versión desde la sección [Releases](../../releases/latest).
- Extrae el archivo `.zip` en la carpeta que prefieras.

### 2. Jugar

- Ejecuta `Dragon City Legacy.exe`.
- Se abrirá una ventana con el menú de selección de perfil. Crea uno y disfruta.

> ⚠️ **Windows pedirá permisos de administrador.** El juego modifica temporalmente el archivo `hosts` de Windows para
> redirigir los dominios originales del juego a tu propio equipo, y lo restaura al cerrar el juego.

> ⚠️ **SmartScreen / antivirus:** Windows puede mostrar una advertencia al ejecutar el archivo.
> Haz clic en **"Más información" → "Ejecutar de todas formas"**. Esto es normal en ejecutables
> que no están firmados digitalmente. Algunos antivirus pueden marcarlo por error (falso positivo).

---

## 💾 Guardado

El progreso se guarda localmente en archivos `.json` dentro de la carpeta `web/srv/`
Cuando crees un usuario, usá los botones Exportar / Importar que están en login.html para hacer copias de seguridad de tus usuarios (esto respalda los usuarios creados, no las partidas).

---

## ❓ Problemas frecuentes

<details>
<summary><b>Sale "No se ha podido cargar el complemento"</b></summary>

Falta el plugin de Flash o no coincide con el launcher. Comprueba que `plugins/pepflashplayer.dll` existe y que es la versión de **64 bits**.
</details>

<details>
<summary><b>Aparece el aviso "Puerto 80 ocupado"</b></summary>

Otro programa está usando el puerto 80. Abre CMD como administrador y ejecuta:

```
netstat -ano | findstr :80
tasklist /svc /fi "PID eq NUMERO"
```

Reemplaza `NUMERO` por el PID de la última columna. Cierra ese programa y vuelve a abrir el juego.
</details>

<details>
<summary><b>No puedo mover o borrar la carpeta del juego</b></summary>

El servidor todavía está en ejecución. Cierra la ventana del juego y, si sigue ocurriendo, termina el proceso `Dragon City.exe` desde el Administrador de tareas.
</details>

<details>
<summary><b>Algo falla y no sé por qué</b></summary>

Pulsa el botón **"📋 Registro"** de la barra superior del juego (o `Ctrl+L`) para ver el registro del servidor en vivo.
Los archivos se guardan en la carpeta `logs/`. Si abres un *issue*, adjunta el archivo más reciente.
Antes de compartirlo, revísalo ya que puede contener nombres o identificadores de tus perfiles.
</details>

---

## 🐞 Reportar errores

Abre un [issue](../../issues) indicando: la versión del juego/servidor, qué estabas haciendo y, si puedes, el archivo de registro.

---

## 📚 Sobre la Preservación del Patrimonio Digital

- [Exemption to PCCPSACT](https://www.federalregister.gov/documents/2018/10/26/2018-23241/exemption-to-prohibition-on-circumvention-of-copyright-protection-systems-for-access-control) — Exenciones a la Sección 1201 de la DMCA.
- [EFGAMP](https://efgamp.eu/) — Federación Europea de Archivos y Museos de Videojuegos.
- [BlueMaxima's Flashpoint](https://bluemaxima.org/flashpoint/) — Proyecto definitivo de preservación de juegos web.
- [The Internet Archive](https://archive.org/) — Biblioteca digital de artefactos culturales.
- [UNESCO PERSIST Programme](https://unescopersist.org/) — Acceso continuo a la información digital.
- [Adobe Flash Player Archive](https://archive.org/download/flashplayerarchive/) — Archivo histórico de Flash Player.

---

## 📄 Licencia

```
Dragon City Legacy.
Reconstrucción de servidor local — Proyecto personal de preservación.
El código fuente del servidor y del launcher (.py, .js, .html adaptados) está bajo la Licencia MIT.
Los activos originales del juego (.swf, imágenes, audio) pertenecen a SocialPoint / Take-Two Interactive.
Adobe Flash Player pertenece a Adobe / Harman. Electron, Flask y pypresence pertenecen a sus respectivos autores.
```
