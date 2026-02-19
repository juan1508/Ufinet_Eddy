# 🔴 Ufinet | Monitor de Incidencias

Dashboard de análisis de incidencias con alertas de reincidencias, MTBF y disponibilidad SLA.

## 🚀 Despliegue en Streamlit Cloud (recomendado)

### 1. Sube el proyecto a GitHub

```bash
git init
git add .
git commit -m "Initial commit - Ufinet Dashboard"
git remote add origin https://github.com/TU_USUARIO/ufinet-dashboard.git
git push -u origin main
```

### 2. Despliega en Streamlit Cloud

1. Ve a [share.streamlit.io](https://share.streamlit.io)
2. Conecta tu cuenta de GitHub
3. Selecciona el repositorio `ufinet-dashboard`
4. Main file: `app.py`
5. Haz clic en **Deploy**

### 3. Configura las credenciales de Google Sheets

En Streamlit Cloud:
1. Ve a tu app → **Settings** → **Secrets**
2. Pega el contenido de `.streamlit/secrets.toml.template` con tus datos reales

---

## 🔧 Ejecución local

```bash
pip install -r requirements.txt
# Crea .streamlit/secrets.toml basado en el template
streamlit run app.py
```

---

## 📋 Funcionalidades

| # | Módulo | Descripción |
|---|--------|-------------|
| 1 | Alertas Diarias | Servicios con >2 incidentes en el mes actual |
| 2 | **Reincidencias** ⭐ | Detección automática por criterio mensual y trimestral |
| 3 | MTBF | Promedio de días entre fallas con semáforo de estabilidad |
| 4-5 | Disponibilidad | Consumo de SLA 99.8% y Top 20 servicios críticos |

## 📊 Estructura del Excel esperada

Columnas clave que la app reconoce automáticamente:

| Columna en Excel | Uso |
|-----------------|-----|
| `Id de Ticket` | Identificador único |
| `Fecha y Hora de creación` | Fecha del incidente |
| `Fecha estado resuelto` | Cierre del ticket |
| `Cliente Customer` | Cliente |
| `Servicio afectado` | Servicio (clave para agrupaciones) |
| `País Origen` | Para filtros geográficos |
| `Tiempo imputable a Ufinet` | Para cálculo de downtime/SLA |

## 🌐 Conexión a Google Sheets

La app acepta cualquier Google Sheet que tenga las mismas columnas que el Excel.  
Compartir el Sheet con el email de la cuenta de servicio (rol "Lector").

---

*Desarrollado para Ufinet — Cono Sur Operations*
