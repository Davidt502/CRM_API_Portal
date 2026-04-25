"""
routes/reports_routes.py - Módulo de reportes de actividad
Filtros: fecha, usuario, endpoint
Exportar: CSV
"""
import csv
import io
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify, Response

from middleware.auth_middleware import token_required, admin_required
from models.database import db_connection

logger = logging.getLogger(__name__)
reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


# ── Reporte de actividad ─────────────────────────────────────────
@reports_bp.route("/activity", methods=["GET"])
@token_required
def get_activity():
    """
    Retorna logs de actividad con filtros opcionales.
    Query params: fecha_inicio, fecha_fin, email, endpoint, page, per_page
    Solo admins ven todos los logs; usuarios ven solo los suyos.
    """
    user = getattr(request, "current_user", {})
    is_admin = user.get("rol") == "admin"

    fecha_inicio = _parse_date(request.args.get("fecha_inicio"))
    fecha_fin    = _parse_date(request.args.get("fecha_fin"))
    email_filter = request.args.get("email", "").strip() or None
    ep_filter    = request.args.get("endpoint", "").strip() or None

    # Usuarios normales solo pueden ver su propio historial
    if not is_admin:
        email_filter = user.get("email")

    try:
        page     = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 50))))
    except (ValueError, TypeError):
        page, per_page = 1, 50

    try:
        with db_connection() as (conn, cursor):
            cursor.execute(
                """
                EXEC sp_reporte_actividad
                    @fecha_inicio  = %s,
                    @fecha_fin     = %s,
                    @email_usuario = %s,
                    @endpoint      = %s,
                    @page          = %s,
                    @per_page      = %s
                """,
                (fecha_inicio, fecha_fin, email_filter, ep_filter, page, per_page)
            )

            # Primer resultado: total
            total_row = cursor.fetchone()
            total = total_row.get("total", 0) if total_row else 0

            # Segundo resultado: datos
            cursor.nextset()
            rows = cursor.fetchall()

        # Serializar fechas
        logs = []
        for row in (rows or []):
            entry = dict(row)
            if isinstance(entry.get("fecha_acceso"), datetime):
                entry["fecha_acceso"] = entry["fecha_acceso"].isoformat()
            logs.append(entry)

        return jsonify({
            "total":    total,
            "page":     page,
            "per_page": per_page,
            "pages":    (total + per_page - 1) // per_page if per_page else 1,
            "data":     logs,
        })

    except Exception as exc:
        logger.error("Error en reporte de actividad: %s", exc, exc_info=True)
        return jsonify({"error": "Error al obtener reportes."}), 500


# ── Exportar CSV ─────────────────────────────────────────────────
@reports_bp.route("/activity/export", methods=["GET"])
@token_required
def export_activity_csv():
    """
    Exporta el reporte de actividad como archivo CSV.
    Acepta los mismos filtros que GET /api/reports/activity.
    """
    user = getattr(request, "current_user", {})
    is_admin = user.get("rol") == "admin"

    fecha_inicio = _parse_date(request.args.get("fecha_inicio"))
    fecha_fin    = _parse_date(request.args.get("fecha_fin"))
    email_filter = request.args.get("email", "").strip() or None
    ep_filter    = request.args.get("endpoint", "").strip() or None

    if not is_admin:
        email_filter = user.get("email")

    try:
        with db_connection() as (conn, cursor):
            cursor.execute(
                """
                EXEC sp_reporte_actividad
                    @fecha_inicio  = %s,
                    @fecha_fin     = %s,
                    @email_usuario = %s,
                    @endpoint      = %s,
                    @page          = 1,
                    @per_page      = 10000
                """,
                (fecha_inicio, fecha_fin, email_filter, ep_filter, )
            )
            cursor.nextset()
            rows = cursor.fetchall() or []

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        headers = [
            "ID", "Nombre", "Email", "IP", "User Agent",
            "Método", "Endpoint", "Query Params",
            "Status Code", "Duración (ms)", "Fecha Acceso"
        ]
        writer.writerow(headers)

        for row in rows:
            fecha = row.get("fecha_acceso", "")
            if isinstance(fecha, datetime):
                fecha = fecha.isoformat()
            writer.writerow([
                row.get("id_log", ""),
                row.get("nombre_usuario", ""),
                row.get("email_usuario", ""),
                row.get("ip_address", ""),
                row.get("user_agent", ""),
                row.get("metodo_http", ""),
                row.get("endpoint", ""),
                row.get("query_params", ""),
                row.get("status_code", ""),
                row.get("duracion_ms", ""),
                fecha,
            ])

        output.seek(0)
        filename = f"reporte_actividad_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return Response(
            output.getvalue(),
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    except Exception as exc:
        logger.error("Error exportando CSV: %s", exc, exc_info=True)
        return jsonify({"error": "Error al exportar reporte."}), 500


# ── Estadísticas ─────────────────────────────────────────────────
@reports_bp.route("/stats", methods=["GET"])
@admin_required
def get_stats():
    """Estadísticas del dashboard de reportes. Solo para admins."""
    try:
        with db_connection() as (conn, cursor):
            cursor.execute("EXEC sp_reporte_estadisticas")

            total_usuarios = (cursor.fetchone() or {}).get("total_usuarios", 0)
            cursor.nextset()
            requests_hoy   = (cursor.fetchone() or {}).get("requests_hoy", 0)
            cursor.nextset()
            top_endpoints  = cursor.fetchall() or []
            cursor.nextset()
            por_dia        = cursor.fetchall() or []

        return jsonify({
            "total_usuarios": total_usuarios,
            "requests_hoy":   requests_hoy,
            "top_endpoints":  [dict(r) for r in top_endpoints],
            "requests_por_dia": [
                {
                    "fecha": r["fecha"].isoformat() if isinstance(r.get("fecha"), datetime) else r.get("fecha", ""),
                    "total": r.get("total", 0)
                }
                for r in por_dia
            ],
        })

    except Exception as exc:
        logger.error("Error en stats: %s", exc, exc_info=True)
        return jsonify({"error": "Error al obtener estadísticas."}), 500
