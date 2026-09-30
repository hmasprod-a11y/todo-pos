"""Offline-safe licensing providers; Store integration can refresh the cached plan later."""
from database import get_setting

class LocalLicenseProvider:
    def plan(self):
        return "PRO" if get_setting("commercial_plan","FREE").strip().upper()=="PRO" else "FREE"

class MicrosoftStoreLicenseProvider:
    """Uses the last verified Store entitlement; never blocks POS on network access."""
    def plan(self):
        cached=get_setting("store_cached_plan","").strip().upper()
        if cached in ("FREE","PRO"):
            return cached
        return LocalLicenseProvider().plan()
