<img width="330" height="230" alt="image" src="https://github.com/user-attachments/assets/1d1d8f52-cb5d-429e-bb72-e43ee86b1a44" />


**Dragon City Flash Restoration Project** — Un proyecto de preservación histórica del juego
original en Adobe Flash (2012–2020), mantenido vivo por la comunidad.

[![Estado](https://img.shields.io/badge/Estado-En_Desarrollo-orange)]()
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)]()
[![Flask](https://img.shields.io/badge/Flask-Servidor_Local-lightgrey)]()
[![Comandos](https://img.shields.io/badge/Comandos_Implementados-39%2F104-yellow)]()

---

## ⚠️ Aviso Legal / Legal Notice

**Este proyecto es de uso estrictamente educativo y de preservación histórica.**
*Dragon City* y todos sus activos visuales, de audio y de marca son propiedad intelectual
de **SocialPoint / Take-Two Interactive**.

Este servidor local:
- **NO** tiene fines de lucro ni distribuye el juego comercialmente.
- **NO** compite con las versiones actuales del juego (móvil / Windows).
- Opera bajo el amparo de las exenciones a la **Sección 1201 de la DMCA**, relativas a la
  preservación de videojuegos cuyos servidores de autenticación originales han sido
  apagados de forma permanente.
- Utiliza protocolos y activos de la versión de **Adobe Flash**, plataforma
  oficialmente descontinuada desde diciembre de 2020.

Si eres representante legal de SocialPoint o Take-Two Interactive y tienes alguna consulta,
puedes contactarme antes de tomar cualquier acción formal.

---

## 🛠️ Estado del Desarrollo

El servidor local es funcional y permite cargar el juego.

| Módulo | Estado |
|---|---|
| Motor de Cría | ✅ Funcional |
| Comandos (`packets.php`) | ⚠️ 30 / 104 implementados |
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

- Un navegador compatible con Flash Player
  - ⚡ **Recomendado:** [FlashBrowser](https://github.com/radubirsan/FlashBrowser/releases/latest)
  - 🌕 Alternativa: [Pale Moon](https://www.palemoon.org/)

### 1. Descargar el servidor

- Descarga la última versión desde la sección [Releases](../../releases/latest).
- Extrae el archivo `.zip` en la carpeta que prefieras.

### 2. Iniciar el servidor

- Ejecuta `Dragon City.exe`.
- Abrí el navegador con Flash y navegá hasta `http://127.0.0.1:80`.

> ⚠️ **Nota:** Windows puede mostrar una advertencia de SmartScreen al ejecutar el archivo.
> Haz clic en **"Más información" → "Ejecutar de todas formas"**. Esto es normal en ejecutables
> que no están firmados digitalmente.

---

## 🎮 Cómo Jugar

- Abre el navegador y navega a `http://127.0.0.1:80`.
- Crea un perfil en la pantalla de inicio y disfruta.

---

## 💾 Guardado

El progreso se guarda localmente en archivos `.json` dentro de la carpeta `web/srv/`
y en el caché del navegador. Usa los botones **Exportar / Importar** en `login.html`
para hacer copias de seguridad de tus usuarios.

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
Dragon City Flash Restoration Project.
Reconstrucción de servidor local — Proyecto personal de preservación.
El código fuente del servidor (.py, .html adaptados) está bajo la Licencia MIT.
Los activos originales del juego (.swf, imágenes, audio) pertenecen a SocialPoint / Take-Two Interactive.
```
