# Prode Mundial Flask Supabase v3

Web app Flask para jugar al prode del Mundial con Supabase Auth y Supabase/PostgREST.

## Stack

- Flask
- Supabase Python client
- Supabase Auth
- Bootstrap via CDN
- Gunicorn

## Instalacion local

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

Completar `.env` con las credenciales reales de Supabase.

## Variables de entorno

- `FLASK_SECRET_KEY`: secreto de sesion Flask.
- `SUPABASE_URL`: URL del proyecto Supabase.
- `SUPABASE_ANON_KEY`: anon key para Auth.
- `SUPABASE_SERVICE_ROLE_KEY`: service role key para operaciones server-side.
- `APP_BASE_URL`: URL publica de la app, usada por reset password.
- `ALLOW_EARLY_RESULT_ADMIN`: `false` por defecto. Si es `true`, permite al admin cargar resultados antes del inicio.

## Ejecucion

```powershell
python app.py
```

Produccion:

```powershell
gunicorn app:app
```

El `Procfile` incluido usa `web: gunicorn app:app`.

## Reglas de negocio

- Un usuario puede cargar o modificar pronosticos solo si `now < match_date`.
- Si `now >= match_date`, el pronostico queda cerrado.
- Si `is_finished=true`, el pronostico queda bloqueado aunque la fecha no haya pasado.
- Los goles deben ser enteros no negativos.
- Los pronosticos de otros usuarios se muestran solo cuando el partido empezo o finalizo.
- El ranking ordena por puntos, exactos, aciertos de resultado y menor cantidad de fallos.

## Admin

- Solo usuarios con `profiles.is_admin=true` acceden al panel admin.
- El admin puede cargar resultados solo cuando el partido ya empezo.
- La carga anticipada requiere `ALLOW_EARLY_RESULT_ADMIN=true`.
- Al cargar resultado se marca `is_finished=true` y se recalculan puntos.
- Al limpiar resultado se borran scores, se marca `is_finished=false` y se resetean puntos.

## Supabase

El esquema esperado esta documentado en `schema.sql`. Supabase Auth maneja usuarios, sesiones y reset password; no se duplican tablas de Auth en el schema de la app.

## Tests

```powershell
python -m unittest discover
```
