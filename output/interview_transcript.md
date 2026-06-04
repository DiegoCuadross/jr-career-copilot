# Transcripción de Entrevista Mock

**Candidato:** Alejandro Silva Torres  
**Job Description:** job_description_1.txt — Junior Backend Engineer @ PayFlow Technologies  
**Fecha:** 2025-06-03 17:30  

---

### Pregunta 1

**🎙️ Reclutador:**

¡Bienvenido, Alejandro! Soy el Engineering Lead de PayFlow Technologies. Gracias por tomarte el tiempo hoy.
Para comenzar, cuéntame sobre tu proyecto de microservicio de análisis predictivo de tráfico que desarrollaste como proyecto de fin de carrera en la UFPS. ¿Cómo lo diseñaste y qué desafíos técnicos enfrentaste?

**👤 Candidato:**

Gracias por recibirme. El proyecto consistió en construir un microservicio en Python con FastAPI que consumía datos en tiempo real de sensores de tráfico urbano y exponía predicciones a través de endpoints REST. El mayor desafío fue el diseño del pipeline de datos: los sensores enviaban lecturas cada 5 segundos y necesitaba procesar sin bloquear los endpoints. Resolví esto con colas asyncio y tareas en segundo plano con BackgroundTasks de FastAPI. Para la persistencia usé PostgreSQL con particionamiento por timestamp. También implementé un modelo de regresión lineal simple con scikit-learn para las predicciones, que retrenaba automáticamente cada hora con los últimos datos.

**💬 Feedback:**

Excelente respuesta, Alejandro. Demostraste comprensión profunda del stack técnico — mencionas asyncio, BackgroundTasks, particionamiento en PostgreSQL y reentrenamiento automático, todos conceptos avanzados para un perfil junior. Para mejorar: en entrevistas reales, menciona métricas concretas (latencia promedio del endpoint, precisión del modelo, volumen de datos manejado). Los reclutadores técnicos valoran mucho los números.

---

### Pregunta 2

**🎙️ Reclutador:**

Muy sólido. Ahora, en PayFlow manejamos millones de transacciones diarias y la latencia de nuestra base de datos es crítica. Durante tu pasantía en SoftTech Solutions mencionas que optimizaste consultas SQL y redujiste tiempos de respuesta en un 15%. ¿Cuál fue el proceso exacto que seguiste para identificar y resolver ese problema?

**👤 Candidato:**

El problema lo detecté revisando los logs de PostgreSQL con `pg_stat_statements` — identifiqué tres consultas que representaban el 70% del tiempo total de ejecución. Con `EXPLAIN ANALYZE` descubrí que dos de ellas hacían sequential scans en tablas de más de 500k registros porque faltaban índices en columnas usadas frecuentemente en los WHERE. Agregué índices compuestos estratégicos y en la tercera consulta, que era un JOIN entre cuatro tablas, la reescribí usando una CTE materializada para evitar que el planner recalculara el resultado intermedio múltiples veces. El resultado fue pasar de ~800ms promedio a ~680ms, un 15% de mejora. También documenté el proceso para el equipo.

**💬 Feedback:**

Respuesta técnicamente muy madura. Usaste las herramientas correctas (`pg_stat_statements`, `EXPLAIN ANALYZE`), identificaste correctamente los sequential scans como el problema raíz, y aplicaste soluciones apropiadas (índices compuestos + CTEs materializadas). El 15% de mejora es creíble y bien sustentado. Un punto a desarrollar: mencionar el contexto del problema — ¿qué impacto tenía esa latencia en los usuarios finales? Esto conecta la solución técnica con el negocio, algo muy valorado en FinTech.

---

### Pregunta 3

**🎙️ Reclutador:**

Perfecto. En PayFlow integramos con Stripe y MercadoPago. Imagina que te piden diseñar un webhook handler para procesar notificaciones de pagos exitosos de Stripe. El handler debe ser idempotente — si Stripe envía el mismo evento dos veces, no debe procesarse dos veces. ¿Cómo lo diseñarías?

**👤 Candidato:**

Para garantizar idempotencia, lo primero sería usar el `stripe-signature` del header para verificar la autenticidad del webhook con el secret de Stripe — descartaría cualquier request sin firma válida. Luego, para la deduplicación, persistiría el `event.id` de Stripe en una tabla `processed_webhook_events` en PostgreSQL con un índice único. Antes de procesar cualquier evento, haría un `INSERT ... ON CONFLICT DO NOTHING` con el event_id — si ya existe, retorno 200 inmediatamente sin procesar. Si no existe, proceso el evento y lo marco como procesado dentro de la misma transacción de base de datos para atomicidad. También agregaría un campo `processed_at` con TTL para poder hacer limpieza periódica de eventos viejos.

**💬 Feedback:**

Diseño correcto y completo. Cubriste los tres pilares del webhook handling seguro: autenticación de firma, deduplicación por event_id e idempotencia mediante transacciones atómicas. El `INSERT ... ON CONFLICT DO NOTHING` dentro de la transacción es exactamente la solución idiomática para PostgreSQL. Excelente que pensaste en el TTL para limpieza — muestra visión de producción. Esta pregunta la responden mal muchos candidatos mid-level, así que muy bien.

---

### Pregunta 4

**🎙️ Reclutador:**

Muy bien. Cuéntame de alguna situación durante tu rol como Ayudante de Profesor donde tuviste que explicar un concepto técnico complejo a alguien que no lo entendía. ¿Cómo lo abordaste y cuál fue el resultado?

**👤 Candidato:**

Durante el semestre, varios estudiantes tenían dificultades con el concepto de herencia múltiple en C++ y los problemas del diamante. Notaba en los laboratorios que seguían copiando código sin entender qué pasaba. En lugar de repetir la teoría del libro, diseñé un ejercicio práctico: un sistema de vehículos donde `Auto` y `Barco` heredaban de `Vehiculo`, y `HoverCraft` heredaba de ambos. Les pedí que lo compilaran sin `virtual` y vieran el error del compilador, luego lo corregimos juntos con herencia virtual. Ver el error primero y luego la solución hizo que el concepto "hiciera clic". Ese semestre, la tasa de reprobación del módulo bajó un 10% y varios estudiantes me buscaron después para hablar de otros patrones de diseño — señal de que el enfoque funcionó.

**💬 Feedback:**

Respuesta STAR perfecta. Situación clara, tarea definida, acción concreta (aprendizaje basado en errores deliberados) y resultado medible (10% menos de reprobación). Además, demuestra una habilidad muy valorada en equipos de ingeniería: la capacidad de hacer pair programming y mentoring. Esta experiencia es transferible directamente a code reviews y onboarding de nuevos integrantes del equipo.

---

## Evaluación Final

**Candidato:** Alejandro Silva Torres  
**Posición:** Junior Backend Engineer — PayFlow Technologies  
**Evaluador:** Mock Interview — jr-career-copilot (Gemini 2.5 Flash)

### Resumen

Alejandro demostró un nivel técnico sólido, por encima del promedio para un perfil junior. Sus respuestas revelan comprensión real de los conceptos (no memorización superficial): diseño de sistemas asincrónicos, optimización de bases de datos con herramientas de profiling reales, y patrones de diseño para sistemas distribuidos como idempotencia en webhooks.

### Puntuación por área

| Área | Puntuación | Comentario |
|---|---|---|
| Conocimiento técnico | 8.5/10 | Dominio real de Python, PostgreSQL y diseño de APIs |
| Resolución de problemas | 8.0/10 | Proceso metodológico correcto con herramientas reales |
| Comunicación | 8.5/10 | Respuestas claras, estructuradas y con contexto |
| Potencial de crecimiento | 9.0/10 | Pensamiento de producción notable para el nivel de experiencia |

### Puntuación global: **8.5 / 10** — ✅ Recomendado para siguiente etapa

### Áreas de mejora para entrevistas reales
1. Incluir métricas concretas en todas las respuestas técnicas (latencia, throughput, % mejora)
2. Conectar soluciones técnicas con impacto de negocio (especialmente en FinTech)
3. Preparar 2-3 preguntas inteligentes para hacerle al entrevistador al final

---
*Generado por jr-career-copilot — Mock Interview (google-genai SDK + Gemini 2.5 Flash)*
