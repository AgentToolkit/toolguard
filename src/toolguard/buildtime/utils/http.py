MEDIA_TYPE_APP_JSON = "application/json"
MEDIA_TYPE_MULTIPART_FORM = "multipart/form-data"
MEDIA_TYPE_APP_FORM = "application/x-www-form-urlencoded"

PARAM_API_KEY = "api_key"

AUTH_HEADER = "Authorization"

SECURITY_COMPONENT_TYPE_API_KEY = "apiKey"  # pragma: allowlist secret
SECURITY_COMPONENT_SCHEME_BEARER = "bearer"
SECURITY_COMPONENT_SCHEME_BASIC = "basic"

SECURITY_COMPONENT_BEARER = {
    "type": "http",
    "scheme": SECURITY_COMPONENT_SCHEME_BEARER,
    "bearerFormat": "JWT",
}
