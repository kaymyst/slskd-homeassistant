import requests
from slskd_api import SlskdClient

from .const import CONF_API_KEY_ROLE, ROLE_READONLY, ROLE_READWRITE


def get_server_state(client: SlskdClient) -> dict:
    """Return the slskd server state.

    slskd 0.26.2+ restricts GET /api/v0/server to Administrator API keys, so read
    the same ServerState from GET /api/v0/application, which any key can access.
    """
    app_state = client.application.state() or {}
    server = dict(app_state.get("server") or {})
    server.setdefault("username", (app_state.get("user") or {}).get("username"))
    return server


def get_role(entry) -> str | None:
    """Return the API key role saved on a config entry (options win over data)."""
    return entry.options.get(CONF_API_KEY_ROLE, entry.data.get(CONF_API_KEY_ROLE))


def detect_role(client: SlskdClient) -> str:
    """Probe GET /api/v0/server, which slskd 0.26.2+ restricts to readwrite keys.

    Only an authorization error means the key is readonly; any other error
    (server down, timeout) is raised so the caller can retry later.
    """
    try:
        client.server.state()
    except requests.HTTPError as err:
        if err.response is not None and err.response.status_code in (401, 403):
            return ROLE_READONLY
        raise
    return ROLE_READWRITE
