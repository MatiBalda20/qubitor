# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React + Vite + TypeScript + Tailwind CSS (fijado por el plan de desarrollo). Login con Clerk (proveedor GitHub). Deploy en Cloudflare Pages; la API FastAPI corre en Render.

## Users

Primario: el líder técnico de un equipo de desarrollo. Entra después de un escaneo para entender de un vistazo el estado de seguridad de un repositorio (Risk Score y nota A–F) y decidir qué se arregla primero.

Secundario: desarrolladores que revisan hallazgos puntuales y los marcan como resueltos o falsos positivos.

## Product Purpose

Qubitor es una plataforma SaaS de auditoría continua de seguridad. Conecta un repositorio de GitHub y corre cuatro motores (SAST, SCA, secretos y criptografía), prioriza los hallazgos con IA (Gemini) y devuelve un reporte accionable. El éxito es que el líder técnico sepa qué tan expuesto está su repo y por dónde empezar, sin leer cada hallazgo.

## Positioning

El diferencial es la criptografía: además de la criptografía clásica rota (MD5, DES, RSA < 2048), Qubitor audita la preparación post-cuántica (RSA, ECDSA, ECDH y DH frente a Shor, AES-128 frente a Grover) y arma un inventario criptográfico (CBOM).

## Operating Context

- Pipeline: clonado → motores en paralelo → normalización → triage con IA → Risk Score → persistencia.
- Escaneos asíncronos: el frontend hace polling a `GET /scans/{id}` para mostrar el progreso.
- Trabajo académico (TPI, UTN FRLP 2026): demo funcional el 09/11/2026 y defensa el 30/11/2026, escaneando en vivo el repo `qubitor-demo-vulnerable`.
- Cada módulo del equipo construye sus vistas en `frontend/src/features/<módulo>/` sobre la base compartida del Módulo B.

## Capabilities and Constraints

- Severidad unificada: critical (peso 10), high (5), medium (2), low (0.5), info (0, inventario).
- Risk Score = max(0, 100 − Σ pesos de hallazgos abiertos y no falsos positivos). Nota: A ≥ 90, B ≥ 75, C ≥ 60, D ≥ 40, F < 40.
- Motores: `sast`, `sca`, `secrets`, `crypto`.
- Estados de un hallazgo: abierto, resuelto o falso positivo.
- Los snippets llegan con los secretos enmascarados; la interfaz nunca debe mostrar un secreto en claro.
- Pendiente de definir: forma exacta de la respuesta de la API (el backend del Módulo A todavía no existe).

## Evidence on Hand

- No hay clientes, métricas ni testimonios reales. Los datos de la interfaz son mock hasta integrar la API, basados en las fallas plantadas del repo de demo.

## Product Principles

1. Primero el veredicto, después el detalle: el estado del repo se entiende en una mirada.
2. La severidad manda: el orden y el énfasis siguen el riesgo real, no el motor.
3. Precisión de herramienta profesional: datos exactos, nada decorativo que compita con los hallazgos.
4. Una sola base visual para los cinco módulos.

## Accessibility & Inclusion

La severidad nunca se comunica solo con color: siempre va con texto. Contraste WCAG AA y navegación por teclado.
