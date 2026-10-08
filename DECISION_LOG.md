# Registro de decisiones técnicas

Este documento explica las decisiones del proyecto, las alternativas consideradas y sus
consecuencias. Distingue los requisitos del desafío de las decisiones adicionales acordadas
durante la especificación y la implementación.

El alcance inicial priorizó las funciones obligatorias de listas y tareas. La segunda etapa
incorporó autenticación, asignación de responsables e invitaciones simuladas, opcionales en
el enunciado pero requeridas para ese incremento por decisión del autor.

Las decisiones de producto se confirmaron mediante preguntas sobre casos concretos antes de
cerrar las especificaciones. Este registro explica el porqué; los contratos completos y las
instrucciones de ejecución permanecen en las especificaciones y el README.

## 1. Arquitectura y herramientas — 2026-10-07

### D01. Un monolito organizado por casos de uso

**Decisión:** construir una sola aplicación desplegable con capas Domain, Application/UseCases
e Infrastructure. El dominio no depende de FastAPI, HTTP ni del ORM. Las dependencias de
persistencia se inyectan mediante interfaces pequeñas en la capa de aplicación.

**Motivo:** demostrar separación de responsabilidades y capacidad de prueba dentro de un
reto estimado en 4–6 horas. La oferta laboral menciona microservicios y serverless, pero el
problema no requiere distribución entre servicios.

**Alternativas y costo:** los microservicios añadirían despliegues, comunicación remota y
consistencia distribuida sin una necesidad actual. Las capas y sus adaptadores añaden algo
de código, por lo que se limita la abstracción a fronteras utilizadas. UnitOfWork coordina
transacciones; no se introduce un contenedor de inyección ni un framework de repositorios.

### D02. Python 3.11, FastAPI y gestión con uv

**Decisión:** utilizar Python 3.11, FastAPI y Pydantic; gestionar dependencias y entornos con
uv, declarar herramientas en `pyproject.toml` y conservar `uv.lock`. Verificar la vigencia del
archivo de bloqueo y utilizar instalaciones congeladas en verificación local y Docker.

**Motivo:** Python y FastAPI responden al enunciado; la versión y uv son elecciones del
proyecto para mantener un entorno reproducible y comandos uniformes.

**Alternativas y costo:** gestionar manualmente versiones y entornos aumenta la posibilidad
de diferencias entre equipos. Un archivo de bloqueo exige actualizar y revisar sus cambios;
una instalación con `--frozen` por sí sola no comprueba que siga alineado con la declaración.

### D03. PostgreSQL, SQLAlchemy, psycopg y Alembic

**Decisión:** utilizar PostgreSQL tanto en ejecución como en integración, SQLAlchemy y
psycopg para persistencia, y migraciones explícitas con Alembic. Mantener el ORM en
Infrastructure y proteger relaciones, unicidad y valores mediante restricciones de base de datos.

**Motivo:** cubrir persistencia real, transacciones, concurrencia e integridad referencial
con el mismo motor que se prueba. Las migraciones permiten reproducir la evolución del esquema.

**Alternativas y costo:** SQL manual reduce dependencias, pero obliga a mantener más mapeo y
migraciones propias. SQLite simplificaría el arranque, pero no verifica el comportamiento
específico de PostgreSQL. Se acepta ejecutar un servicio de base de datos adicional.

### D04. Código orientado a objetos y nombres del dominio

**Decisión:** usar clases para entidades, casos de uso y adaptadores con responsabilidades
cohesivas; preferir composición y permitir funciones para utilidades y conexiones entre
componentes. El paquete es `src/task_manager/`, con importaciones como
`task_manager.domain.task`.

**Motivo:** el nombre identifica la aplicación, no la empresa. El nombre de distribución en
`pyproject.toml` no obliga a usar el nombre del repositorio como paquete Python.

**Alternativas y costo:** una clase por función o una jerarquía genérica añadiría navegación
sin comportamiento útil. Los módulos agrupan operaciones relacionadas; las interfaces se
justifican por aislamiento y pruebas, no por extensibilidad hipotética.

### D05. Docker desde el primer incremento y ejecución síncrona

**Decisión:** empezar con una aplicación mínima, un endpoint de salud y un contenedor
verificable. Usar Docker Compose, almacenamiento persistente, un proceso de migración previo
a la API, configuración por entorno y ejecución de la aplicación con usuario no root.
Los controladores HTTP y las operaciones de base de datos son síncronos.

**Motivo:** comprobar temprano que un evaluador puede ejecutar el proyecto. Un modelo
síncrono es suficiente para estas operaciones CRUD y reduce la complejidad de ejecución.

## 2. Reglas del MVP y consistencia — 2026-10-07

### D06. Identidad estable y ciclo de vida sencillo

**Decisión:** identificar listas y tareas con UUID, permitir nombres y títulos duplicados(se permitio esto teniendo en cuenta los feature adicionales ya que cada lista de tareas era posible que tuviera su propio owner) y
mantener inmutable la lista de una tarea. Una eliminación de lista elimina también sus tareas
atómicamente. No se incluye borrado lógico ni recuperación.

**Motivo:** el identificador resuelve la identidad; los nombres son descriptivos. Obligar a
nombres únicos restringiría usos válidos sin aportar una necesidad del desafío.

**Alternativas y costo:** mover tareas o conservar eliminaciones requeriría reglas adicionales.
El borrado definitivo simplifica el modelo, con la limitación explícita de que no hay deshacer.

### D07. Estados, prioridades y porcentaje calculado

**Decisión:** estados `pending`, `in_progress` y `completed`; prioridades `low`, `medium` y
`high`. Los valores iniciales son `pending` y `medium`. Se permiten todas las transiciones,
incluida completar directamente o reabrir una tarea. El cambio de estado usa el PATCH existente.

El porcentaje es `tareas completadas / tareas totales × 100`, calculado al consultar y no
almacenado. Una lista vacía muestra cero. Se usa Decimal y redondeo de mitades hacia arriba
a dos decimales. Todas las tareas pesan igual; filtros, paginación y prioridad no cambian
el denominador. Por ejemplo, una completada entre 32 produce 3,13 %.

**Motivo:** tener una única fuente de verdad y evitar desajustes al crear, borrar o reabrir tareas.

**Alternativas y costo:** almacenar el porcentaje exigiría mantenerlo en cada escritura.
Ponderar por prioridad o introducir progreso parcial cambia el significado del indicador.
Calcular conteos exactos tiene un costo creciente con el volumen, aceptado para este alcance.

### D08. Contratos explícitos y actualizaciones parciales

**Decisión:** validar peticiones y respuestas con Pydantic y conservar invariantes en el
dominio. Recortar espacios exteriores antes de validar longitudes, convertir descripciones
vacías en null y mantener los tokens de enumeración sensibles a mayúsculas. Rechazar campos
desconocidos, campos inmutables y parámetros de consulta desconocidos o repetidos.

PATCH distingue omisión de null: lo omitido se conserva; null limpia una descripción, pero
no vacía atributos obligatorios. Un cambio sin diferencias normalizadas conserva `updated_at`.
Los cambios de tareas no modifican la fecha de actualización de la lista.

**Motivo:** evitar pérdida de información y errores silenciosos del cliente. Los errores de
negocio se traducen a respuestas HTTP consistentes, sin trazas ni datos sensibles.

**Alternativas y costo:** ignorar entradas desconocidas es más permisivo, pero oculta errores.
Un marcador de omisión en los comandos añade una pequeña complejidad necesaria para expresar
actualizaciones parciales sin confundir ausencia y eliminación de un valor.

### D09. Paginación acotada por página y lectura coherente

**Decisión:** utilizar limit/offset, con 20 resultados por defecto y máximo 100 por página.
Ordenar por fecha de creación y UUID. Combinar estado y prioridad con AND; devolver elementos,
conteos y resumen desde una misma instantánea de lectura REPEATABLE READ de solo lectura.

**Motivo:** ofrecer navegación simple y evitar que un cambio concurrente produzca una página
cuyos elementos contradigan sus conteos o porcentaje.

**Alternativas y costo:** los cursores aportan ventajas a grandes volúmenes, pero añaden un
contrato innecesario aquí. La instantánea permite consultas SQL sencillas a costa de varios
viajes a la base. No se promete una instantánea compartida entre distintas peticiones.

### D10. Escrituras atómicas y concurrencia mediante bloqueos

**Decisión:** utilizar transacciones READ COMMITTED y bloqueos de filas. Comparar PATCH con
el valor persistido después de adquirir el bloqueo, modificar solo atributos enviados que
cambien y confirmar antes de responder éxito. La última escritura serializada prevalece
para campos coincidentes; cambios sobre campos distintos se conservan.

**Motivo:** impedir actualizaciones perdidas y detectar correctamente operaciones sin cambios.
Se mantiene un orden de bloqueo que comienza por la lista y continúa por la tarea.

**Alternativas y costo:** el control optimista requeriría versiones y conflictos visibles para
el cliente. Los bloqueos pueden esperar y exigen transacciones cortas. Una pérdida de conexión
durante el commit puede dejar un resultado incierto; no se promete idempotencia de creación.

## 3. Calidad y decisiones reconsideradas — 2026-10-07

### D11. Pruebas de comportamiento y verificación local

**Decisión:** exigir pytest con pruebas unitarias, integración en PostgreSQL y recorridos
end-to-end sobre un proceso Uvicorn real. Usar una base de pruebas separada y esquemas aislados,
aplicar migraciones y recoger cobertura del proceso HTTP. Mantener el mínimo de 75 % de
cobertura, Flake8, Black y mypy estricto. Las pruebas acompañan los cambios; TDD no es obligatorio.

**Motivo:** comprobar reglas, persistencia y contratos externos. Los mocks por sí solos no
verifican restricciones, transacciones ni comportamiento HTTP real.

**Alternativas y costo:** estas pruebas requieren PostgreSQL y más tiempo de ejecución que
las unitarias. La cobertura es un umbral, no una demostración automática de todos los casos.
La constitución conserva anotaciones locales explícitas: mypy estricto no impone por sí solo
esa regla, por lo que también requiere revisión del código.

### D12. Retirar CI/CD del alcance

**Decisión:** eliminar el workflow de GitHub Actions y sustituir los requisitos de pipeline
por controles locales previos a la entrega. El cambio se registró en la constitución v3.0.0.

**Motivo:** CI/CD aparece en la oferta laboral, pero no es un requisito del documento de la
prueba. Se había incorporado como decisión adicional y se retiró para ajustar el alcance.

**Consecuencia:** se mantienen pruebas, cobertura, tipado, formato, lint y comprobaciones de
Docker. Retirar la automatización remota no corrige errores de mypy ni elimina esos controles;
su ejecución queda a cargo de quien entrega el proyecto.

### D13. Retirar el límite de 100 líneas por archivo

**Decisión:** sustituir el límite y su prueba automática por revisión de cohesión, según la
constitución v4.0.0. Dividir módulos cuando mezclan responsabilidades o dificultan comprender,
probar o modificar el comportamiento. No fragmentar solo para reducir líneas.

**Motivo:** el tamaño no demuestra calidad. Un módulo cohesivo de más de 100 líneas puede
resultar más legible que varios archivos pequeños y estrechamente acoplados.

**Consecuencia:** se conserva la organización existente, pero desaparece un umbral artificial.
La revisión de diseño requiere criterio; los controles objetivos de comportamiento, tipos,
formato y lint continúan vigentes.

## 4. Colaboración y seguridad — decisiones confirmadas al 2026-10-08

### D14. Corregir el MVP antes de ampliar funcionalidad

**Decisión:** resolver primero los cinco hallazgos reproducidos: desbordamiento de offset,
texto NUL que llegaba a PostgreSQL, parámetros ausentes en OpenAPI, errores sin localización
útil y fallos de tipado.

**Motivo:** las funciones adicionales no deben ocultar defectos del alcance obligatorio.
Se registraron reproducciones y regresiones en la [evidencia de defectos](specs/002-secure-task-collaboration/defect-evidence.md).

**Consecuencia:** para offsets mayores que el conteo se devuelve una página vacía sin enviar
el valor a SQL, conservando totales y resumen. Se valida texto antes de escribir y se amplía
la comparación del contrato a parámetros y esquemas, no solo rutas y códigos HTTP.

### D15. Un propietario por lista y miembros explícitos

**Decisión:** añadir usuarios, `owner_id` en listas, membresías e invitaciones. El creador
es el propietario y no hay transferencia; no se duplica ese dato en `created_by_id` ni en
una membresía del propietario. La colección visible incluye listas propias y compartidas.

**Motivo:** separar identidad, acceso y responsabilidad con un modelo pequeño. Un propietario
administra metadatos, eliminación, invitaciones y membresías; propietarios y miembros trabajan
sobre las tareas. Conocer un UUID nunca concede acceso.

**Alternativas y costo:** roles configurables y auditoría de creador serían útiles si hubiera
transferencias o permisos más complejos. El modelo actual obliga a revisar acceso en cada
caso de uso. Se responde 404 a recursos inaccesibles y 403 cuando un miembro intenta una
operación reservada al propietario dentro de una lista que sí puede consultar.

### D16. JWT con dependencias de FastAPI

**Decisión:** integrar autenticación mediante Depends y el esquema OAuth2 de FastAPI, sin
un decorador personalizado. Usar PyJWT, HS256 fijo, claves por entorno y claims obligatorios
`sub`, `iat`, `exp`, `iss` y `aud`. El login recibe formulario con username=email y password.
El adaptador verifica el token; los casos de uso deciden autorización sobre recursos.

**Motivo:** reutilizar la integración de seguridad y OpenAPI del framework y mantener separadas
la identidad del solicitante y sus permisos. Los errores 401 incluyen `WWW-Authenticate: Bearer`.

**Alternativas y costo:** un decorador propio duplicaría integración. Se aceptaron tokens de
30 minutos sin refresh ni revocación por logout: cerrar sesión descarta el token en el cliente,
pero un token obtenido por otro actor sigue siendo válido hasta expirar. Los endpoints de
autenticación y salud son públicos; la documentación se habilita explícitamente por entorno.

### D17. Identidad y contraseñas con bibliotecas específicas

**Decisión:** usar pwdlib/Argon2id para contraseñas, email-validator para correo y
python-multipart para login por formulario. El correo se almacena en una representación
canónica única, con comparación sin distinción de mayúsculas; se conservan puntos y etiquetas
con signo más. Registro duplicado devuelve 409.

Las contraseñas admiten 15–128 puntos de código Unicode, sin recortar espacios, normalizar,
truncar ni exigir combinaciones arbitrarias. Se guarda únicamente su hash. Login con usuario
inexistente o contraseña incorrecta devuelve el mismo error genérico.

**Motivo:** evitar criptografía y validación de correo propias. Son dependencias acotadas a
responsabilidades concretas que se revisan y bloquean con uv.

**Consecuencia:** la comparación elegida fusiona direcciones cuya parte local difiere solo
en mayúsculas. No se incluye verificación de buzón, recuperación de contraseña, bloqueo de
contraseñas comprometidas ni limitación de intentos como parte de esta política.

### D18. Un responsable elegible por tarea

**Decisión:** añadir `assignee_id` opcional en creación y PATCH; la respuesta expone su UUID.
Solo se permite asignar al propietario o a un miembro de la misma lista, sin aceptación
adicional. Los participantes de la lista se pueden consultar sin un directorio global de usuarios.

**Motivo:** mantener un responsable inequívoco sin convertir la asignación en otro flujo de
trabajo. Cambiarlo actualiza la tarea; repetir el mismo valor es una operación sin cambios y
la asignación no modifica el porcentaje de completitud.

**Consecuencia:** retirar un miembro es una operación del propietario que limpia sus
asignaciones y elimina su membresía en una transacción. No hay salida voluntaria ni eliminación
del propietario. Bloqueos sobre la lista y comprobaciones en casos de uso coordinan asignación,
retirada y aceptación. Se descartaron triggers duplicados: SQL privilegiado que omita los casos
de uso puede saltarse esta regla de elegibilidad, aunque sigan vigentes claves y unicidad.

### D19. Invitaciones con entrega simulada y credencial de un solo acceso visual

**Decisión:** invitar a un correo a una lista, incluso antes de que exista su cuenta. La
aceptación requiere autenticación con el mismo correo canónico. Las invitaciones caducan en
siete días; el propietario puede revocar o reenviar según su estado. Reenviar rota la credencial.

Se generan tokens aleatorios de 256 bits y se almacena su verificador SHA-256. El token se
muestra solo en la respuesta de creación o reenvío al propietario autenticado. La invitación
conserva los metadatos de la última simulación, sin tabla adicional ni historial de notificaciones.
No se envía correo real ni se usa SMTP, proveedor externo o proceso de entrega en segundo plano.

**Motivo:** demostrar el caso de uso solicitado sin infraestructura innecesaria. La expiración
se evalúa al consultar; crear o reenviar actualiza estados pendientes caducados para preservar
la unicidad de invitaciones activas.

**Alternativas y costo:** mostrar la credencial al propietario facilita la evaluación, pero no
prueba control de un buzón real. La aceptación crea membresía y actualiza la invitación
atómicamente. Reintentar una aceptación solo devuelve éxito mientras la membresía exista;
una invitación ya aceptada no permite recuperar un acceso retirado. No se registran tokens
en logs ni se devuelven en consultas posteriores.

### D20. Migración de datos con propietario seleccionado explícitamente

**Decisión:** conservar las migraciones iniciales y añadir dos etapas: esquema de acceso con
propiedad temporalmente nullable (`0004`), y propiedad obligatoria (`0005`). Entre ambas, una
herramienta offline permite al operador seleccionar o crear la cuenta que recibe las listas
históricas. No se modifica una contraseña existente ni se reasignan listas con propietario.

**Motivo:** las migraciones se ejecutan antes de la API, por lo que no pueden depender de
registro HTTP. Otorgar datos al primer usuario registrado sería una asignación implícita de
acceso. Las listas y tareas conservan IDs, atributos y fechas; las tareas previas quedan sin
responsable.

**Alternativas y costo:** una orden única con valores predeterminados sería más cómoda, pero
ocultaría una decisión de propiedad. Una instalación vacía migra automáticamente; una base
poblada sin selección válida se detiene y requiere intervención. Se detiene la API compartida
anterior durante la transición y se documenta cómo reintentar sin borrar datos.

## 5. Evidencia registrada y límites

La documentación de verificación del 2026-10-08 registra **98 pruebas aprobadas y 92,27 % de
cobertura total reportada**, además de comprobaciones locales satisfactorias de dependencias,
Flake8, Black, mypy, construcción Docker y ejecución no root. También registra ensayos aislados
de instalación vacía, actualización con datos y persistencia tras reiniciar.

Estos resultados proceden de la [evidencia de la segunda etapa](specs/002-secure-task-collaboration/defect-evidence.md)
y su [guía de verificación](specs/002-secure-task-collaboration/quickstart.md); no constituyen
una nueva ejecución de pruebas realizada al redactar este documento. La primera revisión
había encontrado errores de mypy aun con 52 pruebas aprobadas: ambos resultados se mantuvieron
separados hasta documentar las correcciones.

No se declaran objetivos medidos de rendimiento ni preparación completa para producción.
Permanecen fuera de alcance las transferencias de propiedad, recuperación de eliminaciones,
movimiento de tareas, revocación inmediata de sesiones, correo real, idempotencia de creación,
CI/CD y despliegue cloud. La paginación por offset, los conteos exactos y los bloqueos pueden
requerir revisión si aumentan el volumen o la contención.

## Referencias del proyecto

- [Enunciado del desafío](docs/prueba.pdf).
- [Constitución vigente](.specify/memory/constitution.md).
- [Especificación del MVP](specs/001-manage-task-lists/spec.md) y [plan](specs/001-manage-task-lists/plan.md).
- [Especificación de colaboración](specs/002-secure-task-collaboration/spec.md) y [plan](specs/002-secure-task-collaboration/plan.md).
- [Investigación del MVP](specs/001-manage-task-lists/research.md) y [de colaboración](specs/002-secure-task-collaboration/research.md).
- [Instrucciones de ejecución](README.md).
