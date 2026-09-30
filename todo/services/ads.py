"""Offline-safe advertising boundary. Cashier-critical surfaces are never eligible."""
CASHIER_CRITICAL=frozenset({"sale","payment","change","cash_closure","receipt"})
ALLOWED_SURFACES=frozenset({"dashboard","settings","reports","about"})

class OfflineAdProvider:
    """Default provider: no network, no tracking, no interruption."""
    def placement(self, surface):
        return None

def is_allowed_surface(surface):
    return str(surface or "").strip().lower() in ALLOWED_SURFACES

def placement_for(surface, provider=None):
    """Return a future ad placement only where policy permits it; never raise."""
    if not is_allowed_surface(surface):
        return None
    try:
        return (provider or OfflineAdProvider()).placement(surface)
    except Exception:
        return None
