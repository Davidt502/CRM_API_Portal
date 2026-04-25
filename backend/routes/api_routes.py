"""
routes/api_routes.py - APIs del CRM expuestas con documentación OpenAPI/Swagger
"""
import json
import logging
from flask import Blueprint, jsonify, request

from middleware.auth_middleware import token_required

logger = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__)


# ── OpenAPI / Swagger Spec ────────────────────────────────────────
OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "CRM API Portal",
        "description": (
            "## Portal de APIs CRM - Ing Software\n\n"
            "**Aviso de Privacidad:** Toda actividad en esta API es registrada con fines de "
            "seguridad y auditoría, incluyendo dirección IP, dispositivo y endpoints consultados.\n\n"
            "### Autenticación\n"
            "Todas las rutas requieren un token JWT en el header:\n"
            "```\nAuthorization: Bearer <token>\n```\n"
            "Obtén tu token en `POST /api/auth/login`."
        ),
        "version": "3.0.0",
        "contact": {
            "name": "Soporte CRM",
            "email": "soporte@crm-ingsoftware.com"
        },
        "license": {"name": "Privado"}
    },
    "servers": [
        {"url": "http://localhost:5000", "description": "Desarrollo local"},
        {"url": "https://api.crm-ingsoftware.com", "description": "Producción"}
    ],
    "components": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Ingresa tu JWT obtenido del endpoint de login"
            }
        },
        "schemas": {
            "Error": {
                "type": "object",
                "properties": {
                    "error": {"type": "string", "example": "Mensaje de error"}
                }
            },
            "LoginRequest": {
                "type": "object",
                "required": ["email", "password"],
                "properties": {
                    "email":    {"type": "string", "format": "email", "example": "usuario@empresa.com"},
                    "password": {"type": "string", "format": "password", "example": "MiPassword123"}
                }
            },
            "RegisterRequest": {
                "type": "object",
                "required": ["nombre_completo", "email", "password", "acepto_terminos"],
                "properties": {
                    "nombre_completo": {"type": "string", "example": "Juan García López"},
                    "email":           {"type": "string", "format": "email"},
                    "password":        {"type": "string", "minLength": 8},
                    "acepto_terminos": {"type": "boolean", "example": True}
                }
            },
            "Cliente": {
                "type": "object",
                "properties": {
                    "id_cliente":      {"type": "integer"},
                    "nombre":          {"type": "string"},
                    "email":           {"type": "string"},
                    "telefono":        {"type": "string"},
                    "fecha_registro":  {"type": "string", "format": "date-time"}
                }
            },
            "Empleado": {
                "type": "object",
                "properties": {
                    "id_empleado":   {"type": "integer"},
                    "nombre":        {"type": "string"},
                    "dependencia":   {"type": "string"},
                    "estado":        {"type": "string", "enum": ["Activo", "Inactivo"]}
                }
            },
            "Proveedor": {
                "type": "object",
                "properties": {
                    "id_proveedor": {"type": "integer"},
                    "nombre":       {"type": "string"},
                    "contacto":     {"type": "string"},
                    "email":        {"type": "string"}
                }
            },
            "ActivityLog": {
                "type": "object",
                "properties": {
                    "id_log":          {"type": "integer"},
                    "nombre_usuario":  {"type": "string"},
                    "email_usuario":   {"type": "string"},
                    "ip_address":      {"type": "string"},
                    "user_agent":      {"type": "string"},
                    "metodo_http":     {"type": "string"},
                    "endpoint":        {"type": "string"},
                    "status_code":     {"type": "integer"},
                    "duracion_ms":     {"type": "integer"},
                    "fecha_acceso":    {"type": "string", "format": "date-time"}
                }
            }
        }
    },
    "security": [{"BearerAuth": []}],
    "paths": {
        "/api/auth/register": {
            "post": {
                "tags": ["Autenticación"],
                "summary": "Registro de nuevo usuario",
                "security": [],
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RegisterRequest"}}}
                },
                "responses": {
                    "201": {"description": "Usuario registrado exitosamente"},
                    "400": {"description": "Datos inválidos", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    "409": {"description": "Email ya registrado"}
                }
            }
        },
        "/api/auth/login": {
            "post": {
                "tags": ["Autenticación"],
                "summary": "Iniciar sesión",
                "security": [],
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/LoginRequest"}}}
                },
                "responses": {
                    "200": {
                        "description": "Login exitoso, retorna JWT",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "success": {"type": "boolean"},
                                        "token":   {"type": "string"},
                                        "user":    {"type": "object"}
                                    }
                                }
                            }
                        }
                    },
                    "401": {"description": "Credenciales incorrectas"},
                    "429": {"description": "Demasiados intentos de login"}
                }
            }
        },
        "/api/clientes": {
            "get": {
                "tags": ["Clientes"],
                "summary": "Listar clientes",
                "parameters": [
                    {"name": "nombre", "in": "query", "schema": {"type": "string"}},
                    {"name": "page",   "in": "query", "schema": {"type": "integer", "default": 1}}
                ],
                "responses": {
                    "200": {"description": "Lista de clientes"},
                    "401": {"description": "No autorizado"}
                }
            },
            "post": {
                "tags": ["Clientes"],
                "summary": "Crear cliente",
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Cliente"}}}
                },
                "responses": {
                    "201": {"description": "Cliente creado"},
                    "400": {"description": "Datos inválidos"}
                }
            }
        },
        "/api/clientes/{id}": {
            "get": {
                "tags": ["Clientes"],
                "summary": "Obtener cliente por ID",
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                "responses": {
                    "200": {"description": "Cliente encontrado"},
                    "404": {"description": "No encontrado"}
                }
            }
        },
        "/api/empleados": {
            "get": {
                "tags": ["Empleados"],
                "summary": "Listar empleados",
                "parameters": [
                    {"name": "nombre",      "in": "query", "schema": {"type": "string"}},
                    {"name": "dependencia", "in": "query", "schema": {"type": "string"}},
                    {"name": "estado",      "in": "query", "schema": {"type": "string", "enum": ["Activo", "Inactivo"]}},
                    {"name": "page",        "in": "query", "schema": {"type": "integer", "default": 1}}
                ],
                "responses": {"200": {"description": "Lista de empleados"}}
            },
            "post": {
                "tags": ["Empleados"],
                "summary": "Crear empleado",
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Empleado"}}}
                },
                "responses": {"201": {"description": "Empleado creado"}}
            }
        },
        "/api/proveedores": {
            "get": {
                "tags": ["Proveedores"],
                "summary": "Listar proveedores",
                "responses": {"200": {"description": "Lista de proveedores"}}
            }
        },
        "/api/compras": {
            "get": {
                "tags": ["Compras"],
                "summary": "Listar compras",
                "parameters": [
                    {"name": "proveedor",   "in": "query", "schema": {"type": "string"}},
                    {"name": "estado_pago", "in": "query", "schema": {"type": "string"}},
                    {"name": "page",        "in": "query", "schema": {"type": "integer", "default": 1}}
                ],
                "responses": {"200": {"description": "Lista de compras"}}
            }
        },
        "/api/reports/activity": {
            "get": {
                "tags": ["Reportes"],
                "summary": "Ver logs de actividad",
                "description": "Retorna el historial de accesos a la API. Admins ven todos; usuarios ven solo los suyos.",
                "parameters": [
                    {"name": "fecha_inicio", "in": "query", "schema": {"type": "string", "format": "date"}},
                    {"name": "fecha_fin",    "in": "query", "schema": {"type": "string", "format": "date"}},
                    {"name": "email",        "in": "query", "schema": {"type": "string"}},
                    {"name": "endpoint",     "in": "query", "schema": {"type": "string"}},
                    {"name": "page",         "in": "query", "schema": {"type": "integer", "default": 1}},
                    {"name": "per_page",     "in": "query", "schema": {"type": "integer", "default": 50}}
                ],
                "responses": {
                    "200": {
                        "description": "Logs de actividad paginados",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "total":    {"type": "integer"},
                                        "page":     {"type": "integer"},
                                        "per_page": {"type": "integer"},
                                        "data":     {"type": "array", "items": {"$ref": "#/components/schemas/ActivityLog"}}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/api/reports/activity/export": {
            "get": {
                "tags": ["Reportes"],
                "summary": "Exportar logs como CSV",
                "parameters": [
                    {"name": "fecha_inicio", "in": "query", "schema": {"type": "string", "format": "date"}},
                    {"name": "fecha_fin",    "in": "query", "schema": {"type": "string", "format": "date"}},
                    {"name": "email",        "in": "query", "schema": {"type": "string"}}
                ],
                "responses": {
                    "200": {
                        "description": "Archivo CSV",
                        "content": {"text/csv": {}}
                    }
                }
            }
        },
        "/api/reports/stats": {
            "get": {
                "tags": ["Reportes"],
                "summary": "Estadísticas generales (solo admin)",
                "responses": {"200": {"description": "Estadísticas del portal"}}
            }
        },
        "/api/health": {
            "get": {
                "tags": ["Sistema"],
                "summary": "Health check",
                "security": [],
                "responses": {"200": {"description": "API funcionando correctamente"}}
            }
        }
    }
}


@api_bp.route("/api/openapi.json", methods=["GET"])
def openapi_spec():
    """Retorna el spec OpenAPI en JSON."""
    return jsonify(OPENAPI_SPEC)
