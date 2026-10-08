# API de gestión de tareas

Servicio síncrono con FastAPI para administrar listas y tareas, con autenticación JWT,
asignación de responsables e invitaciones simuladas. Utiliza Python 3.11, PostgreSQL para
persistencia, Alembic para migraciones y `uv` para gestionar dependencias.

El paquete `src/task_manager/` separa Domain, Application e Infrastructure. Las rutas y los
esquemas HTTP están en `infrastructure/http/`; los modelos y adaptadores de persistencia,
en `infrastructure/persistence/`. Los módulos agrupan responsabilidades relacionadas;
la cantidad de líneas es una señal de revisión, no un límite obligatorio.

Las pruebas se dividen en unitarias, integración y end-to-end, con fixtures compartidos en
`tests/fixtures/`.

## Instalación y ejecución local

Instala `uv` y Docker con Compose. Desde la raíz del repositorio, crea la configuración local
si aún no tienes un archivo `.env`:

```sh
cp .env.example .env
openssl rand -hex 32
```

Reemplaza las contraseñas de ejemplo por valores locales distintos para desarrollo y pruebas,
tanto en las variables de contraseña como en sus URL correspondientes. Usa el valor aleatorio
generado como `JWT_SIGNING_KEY`. No incluyas `.env` en el control de versiones. La API exige
la clave de firma cuando está presente la configuración de base de datos para ejecución.

Instala Python y las dependencias e inicia los servicios:

```sh
uv python install 3.11
uv lock --check
uv sync --frozen
docker compose up --build -d --wait
curl --fail-with-body http://localhost:8000/health
```

La API queda disponible en `http://localhost:8000` y PostgreSQL en el puerto `55432`.
Los datos se conservan en el volumen `postgres_data`. El servicio de migraciones debe
terminar correctamente antes de iniciar el contenedor de la API, que se ejecuta con un
usuario no root. Las dependencias se instalan desde `uv.lock` con `uv sync --frozen --no-dev`.

Si actualizas una base de datos del MVP que ya contiene listas sin propietario, sigue
primero la sección de actualización de bases existentes.

## Probar con Postman

La forma recomendada de recorrer la API es importar la
[colección de Postman](docs/task-manager.postman_collection.json), ubicada en `docs/`.

1. Inicia la API con Docker siguiendo los pasos anteriores.
2. En Postman, selecciona **Import** e importa `docs/task-manager.postman_collection.json`.
3. Abre las variables de la colección y comprueba `origin=http://localhost:8000` y
   `base_url=http://localhost:8000/api/v1`. Si cambiaste el puerto, ajusta ambas.
4. Selecciona **No environment** para facilitar la revisión. No necesitas crear un entorno
   ni introducir un token antes de comenzar.
5. Ejecuta la colección completa con **Collection Runner**, desde la primera petición,
   respetando el orden de las carpetas `00` a `09`. También puedes enviarlas manualmente
   en ese mismo orden.
6. Revisa los resultados de las comprobaciones incluidas en cada petición.

La colección genera cuentas de demostración y guarda automáticamente sus credenciales,
tokens e identificadores como variables. Recorre registro y login, CRUD de listas y tareas,
filtros, paginación, completitud, permisos, asignaciones e invitaciones. Las peticiones que
prueban errores esperan respuestas como 401, 403, 404 o 422; no todas deben responder 200.
La carpeta final elimina las listas creadas durante el recorrido.

La colección utiliza `{{owner_token}}`, `{{member_token}}` y `{{outsider_token}}` para
resolver automáticamente la autorización. Si una petición falla porque Postman no resuelve
la variable o el token está incompleto, puedes introducirlo directamente:

1. Ejecuta **Login owner** y copia el valor completo del campo `access_token` de la respuesta.
2. En la petición del propietario, abre **Authorization → Bearer Token** y reemplaza
   `{{owner_token}}` por ese valor completo, sin comillas, espacios ni el prefijo `Bearer`.
   No copies el objeto JSON completo ni una versión abreviada del token.
3. Envía nuevamente la petición. Si editas la cabecera manualmente, su formato debe ser
   `Authorization: Bearer <access_token completo>`.

Para peticiones de miembros o usuarios externos, usa el token de su propio login; sustituirlo
por el del propietario cambia los permisos y altera las pruebas. No modifiques las peticiones
que prueban deliberadamente tokens inválidos o ausentes.

Si un token caduca, ejecuta otra vez el login correspondiente y reemplaza también cualquier
valor pegado manualmente. No guardes tokens reales en archivos compartidos o versionados.
Repite **Health and fresh demo variables** solo al comenzar un recorrido nuevo: reinicia las
variables de cuentas e identificadores.

Para revisar también el contrato OpenAPI, configura `ENABLE_API_DOCS=true` en `.env` y
recrea la API:

```sh
docker compose up -d --force-recreate api
```

Así estarán disponibles [Swagger](http://localhost:8000/docs),
[ReDoc](http://localhost:8000/redoc) y [OpenAPI](http://localhost:8000/openapi.json).
Con la documentación deshabilitada, la petición de OpenAPI de la colección espera 404.

Consulta la [guía de pruebas manuales](docs/MANUAL_TESTING.md) para el recorrido detallado
con Docker y `curl`, y para usar una instancia aislada. Las comprobaciones de migraciones,
concurrencia, tipado y cobertura se ejecutan desde la terminal; Postman no las sustituye.

## Configuración

| Variable | Propósito |
|----------|-----------|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Credenciales de PostgreSQL de desarrollo en Compose |
| `DATABASE_URL` | URL PostgreSQL con psycopg para ejecutar Alembic o la API desde el equipo local |
| `TEST_POSTGRES_USER`, `TEST_POSTGRES_PASSWORD`, `TEST_POSTGRES_DB` | Credenciales de la base separada de pruebas |
| `TEST_DATABASE_URL` | URL de la base exclusiva para las pruebas de integración |
| `DATABASE_SCHEMA` | Esquema opcional validado para pruebas o ejecución aislada |
| `JWT_SIGNING_KEY` | Clave secreta HS256 obligatoria, de al menos 256 bits |
| `JWT_ISSUER`, `JWT_AUDIENCE` | Emisor y audiencia esperados del token; Compose proporciona valores locales por defecto |
| `ENABLE_API_DOCS` | Habilita Swagger, ReDoc y OpenAPI únicamente cuando vale `true` |

`DATABASE_URL` debe comenzar con `postgresql+psycopg://`. Mantén las credenciales fuera del
repositorio, las imágenes y los logs. Compose proporciona el hostname interno de PostgreSQL
a los contenedores de migración y API.

## Endpoints

Las rutas de la tabla tienen el prefijo `/api/v1`:

| Método | Ruta | Resultado |
|--------|------|-----------|
| `POST` | `/auth/register` | Registrar una cuenta |
| `POST` | `/auth/login` | Obtener un token Bearer |
| `GET` | `/auth/me` | Consultar el perfil autenticado |
| `POST` | `/task-lists` | Crear lista; 201 y cabecera `Location` |
| `GET` | `/task-lists` | Consultar listas accesibles con `limit` y `offset` |
| `GET` | `/task-lists/{list_id}` | Consultar una lista |
| `PATCH` | `/task-lists/{list_id}` | Actualizar parcialmente una lista |
| `DELETE` | `/task-lists/{list_id}` | Eliminar lista y tareas; 204 |
| `GET` | `/task-lists/{list_id}/participants` | Consultar propietario y miembros con paginación |
| `DELETE` | `/task-lists/{list_id}/participants/{user_id}` | Retirar un miembro y limpiar sus asignaciones; 204 |
| `POST` | `/task-lists/{list_id}/tasks` | Crear tarea; 201 y `Location` |
| `GET` | `/task-lists/{list_id}/tasks` | Filtrar y paginar tareas con resumen de completitud |
| `GET` | `/task-lists/{list_id}/tasks/{task_id}` | Consultar una tarea dentro de su lista |
| `PATCH` | `/task-lists/{list_id}/tasks/{task_id}` | Actualizar tarea, estado o responsable |
| `DELETE` | `/task-lists/{list_id}/tasks/{task_id}` | Eliminar tarea; 204 |
| `POST` | `/task-lists/{list_id}/invitations` | Simular invitación y mostrar el token una sola vez |
| `GET` | `/task-lists/{list_id}/invitations` | Consultar invitaciones paginadas sin tokens |
| `GET` | `/task-lists/{list_id}/invitations/{invitation_id}` | Consultar metadatos de una invitación |
| `POST` | `/task-lists/{list_id}/invitations/{invitation_id}/revoke` | Revocar una invitación pendiente |
| `POST` | `/task-lists/{list_id}/invitations/{invitation_id}/resend` | Rotar el token y simular reenvío con vigencia de siete días |
| `POST` | `/invitations/accept` | Aceptar una invitación con la cuenta destinataria y su token |

### Autenticación y permisos

El registro es público y recibe JSON con `display_name`, `email` y `password`.
El login recibe `application/x-www-form-urlencoded`, con `username` igual al correo y
`password` como contraseña. Devuelve un token Bearer válido durante 30 minutos.
Las rutas de negocio requieren `Authorization: Bearer <token>`.

No hay refresh token ni revocación de sesión en el servidor: descartar el token en el
cliente no lo invalida antes de su vencimiento. La documentación está oculta por defecto.

El creador es propietario de la lista. Solo el propietario administra sus metadatos,
eliminación, invitaciones y membresías; tanto propietarios como miembros pueden consultar
listas y gestionar tareas. Un usuario ajeno recibe 404; un miembro recibe 403 si intenta
una operación reservada al propietario.

Las invitaciones son simuladas: no se envía correo. Crear o reenviar muestra el token de
aceptación una vez al propietario; las consultas posteriores solo contienen metadatos.
Los responsables elegibles se descubren mediante los participantes de cada lista; no existe
un directorio global de cuentas.

### Reglas de tareas

Los textos se recortan antes de validar su longitud; las descripciones vacías se convierten
en null. Los estados son `pending`, `in_progress` y `completed`; las prioridades,
`low`, `medium` y `high`. Las colecciones se ordenan por fecha de creación y UUID.
Los filtros de tareas se combinan con AND y el resumen representa la lista completa,
independientemente de los filtros y de la paginación.

## Desarrollo y migraciones

Para ejecutar comandos locales que necesitan las variables de `.env`:

```sh
set -a
. ./.env
set +a
uv run --frozen alembic upgrade head
uv run --frozen uvicorn task_manager.infrastructure.http.api:create_app --factory
```

Si la API de Compose ya ocupa el puerto 8000, detenla antes de iniciar Uvicorn localmente.
Las revisiones de Alembic están en `migrations/versions/`. No se utiliza
`Base.metadata.create_all()` para reemplazar migraciones. La clave foránea de tareas apunta
a `task_lists.id` y elimina las tareas en cascada al borrar su lista.

### Actualizar una base con datos del MVP

Una base vacía aplica todas las revisiones automáticamente. Para una base compartida
anterior que contiene listas sin propietario, detén la API y conserva el volumen de
PostgreSQL. Aplica el esquema adicional, selecciona el propietario histórico de forma
interactiva y exige después la propiedad obligatoria:

```sh
docker compose stop api
docker compose up -d --wait db
docker compose run --rm migrate uv run --frozen --no-dev alembic upgrade 0004_access_schema
docker compose run --rm migrate uv run --frozen --no-dev python -m task_manager.infrastructure.bootstrap_owner
docker compose run --rm migrate uv run --frozen --no-dev alembic upgrade head
docker compose up --build -d --wait api
```

La herramienta requiere una terminal interactiva. Permite seleccionar una cuenta existente
por correo canónico o crear una; solicita y confirma la contraseña nueva sin mostrarla en
pantalla. Asigna únicamente listas sin propietario en una transacción y nunca cambia la
contraseña de una cuenta existente.

Si la revisión 0005 detecta listas sin propietario, ejecuta la selección explícita y reintenta
`alembic upgrade head`. No reinicies la base desde cero ni elimines su volumen. La API
permanece bloqueada hasta que se aplique la restricción final de propiedad.

## Verificación local

Inicia la base aislada de pruebas y ejecuta las comprobaciones:

```sh
docker compose --profile test up -d --wait db-test
set -a
. ./.env
set +a
uv run --frozen flake8 src tests migrations
uv run --frozen black --check src tests migrations
uv run --frozen mypy --strict src tests migrations
uv run --frozen pytest
docker build -t task-manager:local .
```

La ejecución completa exige al menos 75 % de cobertura sobre `src/task_manager`.
Los fixtures crean un esquema PostgreSQL por prueba, aplican las migraciones y eliminan
solo su propio esquema al terminar. Los end-to-end ejecutan un proceso Uvicorn real con
configuración de firma exclusiva de pruebas. Nunca apuntes `TEST_DATABASE_URL` a la base
de desarrollo.

Para ejecutar solo un nivel sin exigir el umbral de cobertura de toda la suite:

```sh
uv run --frozen pytest -m unit --no-cov
```

Sustituye `unit` por `integration` o `e2e` cuando corresponda. Antes de entregar, ejecuta
la suite completa y los controles de dependencias, tipado, lint, formato, Docker y persistencia.

## Documentación adicional

- [Colección de Postman](docs/task-manager.postman_collection.json): recorrido de la API con tokens, identificadores y comprobaciones automáticas.
- [Guía de pruebas manuales](docs/MANUAL_TESTING.md): pasos con Docker, Postman y `curl`.
- [Guía de colaboración segura](specs/002-secure-task-collaboration/quickstart.md): migraciones, invitaciones y pruebas aisladas.
- [Registro de decisiones](DECISION_LOG.md): motivos, alternativas y limitaciones del diseño.
