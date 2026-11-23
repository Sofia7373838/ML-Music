# `.github/workflows/` — CI/CD

| Workflow | Cuándo corre | Qué hace |
| --- | --- | --- |
| `ci.yml` | Cada push a `main` y cada pull request | Lint, formato, pruebas y build de la imagen |
| `cd.yml` | Cuando el CI termina bien en `main`, o a mano | Sube la imagen a ECR y actualiza la Lambda |

## CI (`ci.yml`)

Dos jobs en paralelo:

- **test**: instala `requirements-dev.txt` con Python 3.13 y corre `ruff check .`,
  `ruff format --check .` y `pytest`. Son los mismos comandos que se corren en local antes de
  subir cambios.
- **docker**: construye la imagen de Lambda para confirmar que el `Dockerfile` y
  `requirements-api.txt` funcionan. No la sube a ningún lado.

## CD (`cd.yml`)

```text
merge a main ─> CI ✔ ─> credenciales temporales (OIDC) ─> docker build/push a ECR (tag = SHA del commit)
                                                       ─> aws lambda update-function-code
                                                       ─> espera a que la función se actualice
                                                       ─> curl $API_URL/health
```

- **Sin llaves en el repositorio**: GitHub pide un token OIDC y AWS lo cambia por credenciales
  temporales del rol `music-recommender-github-actions`. El rol solo acepta tokens de la rama
  `main` de este repositorio y solo puede subir a este ECR y actualizar esta función.
- **Trazabilidad**: cada imagen se etiqueta con el SHA del commit, así se sabe exactamente qué
  código está desplegado y se puede regresar a una versión anterior con
  `aws lambda update-function-code --image-uri <repo>:<sha-anterior>`.
- **No corre hasta que haya infraestructura**: el job se salta mientras la variable
  `AWS_ROLE_ARN` no exista. Las variables necesarias están en
  [`infra/README.md`](../../infra/README.md#desplegar); Terraform las imprime con
  `terraform output github_variables`.
- **Despliegues en orden**: `concurrency: cd` evita que dos despliegues se pisen.
- El job no usa `environment:` a propósito: eso cambiaría el claim `sub` del token y el rol
  lo rechazaría.

El CD despliega código, no el modelo. Para publicar un modelo nuevo ver
[`models/README.md`](../../models/README.md#publicar-una-versión-del-modelo).

Para correrlo a mano: pestaña *Actions → CD → Run workflow* sobre `main`.

## Si falla `Not authorized to perform sts:AssumeRoleWithWebIdentity`

AWS rechazó el token de GitHub. Revisa en este orden:

1. **`AWS_ROLE_ARN`** debe ser exactamente el que imprime `terraform output github_variables`,
   con el número de la cuenta donde se desplegó (es fácil copiar el de otra cuenta).
2. **Las variables** deben estar en la pestaña *Variables*, no en *Secrets*.
3. **Sujetos inmutables**: si el repositorio los usa, el token trae los IDs de la cuenta y del
   repositorio y el rol debe aceptarlos (`github_oidc_subject_prefix`, ver
   [`infra/README.md`](../../infra/README.md#desplegar)).
4. **La rama**: el rol solo acepta `main`; un run sobre otra rama siempre falla.
