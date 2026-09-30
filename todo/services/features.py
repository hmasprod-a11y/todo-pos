"""Central, offline-safe feature entitlement policy for ToDo editions."""
from services.licensing import LocalLicenseProvider

FREE_FEATURES=frozenset({"SALE","BARCODE","BASIC_STOCK","BASIC_REPORTS","LOCAL_BACKUP"})
PRO_FEATURES=frozenset({"PROMOTIONS","LOYALTY","ADVANCED_STATISTICS","CUSTOMER_DISPLAY","SCALE","RFID","SERIAL_DEVICES","ADVANCED_IMPORT_EXPORT","MULTI_USER","PERMISSIONS","SCHEDULED_BACKUP"})
ALL_FEATURES=FREE_FEATURES|PRO_FEATURES

def normalize_plan(value):
    return "PRO" if str(value or "").strip().upper()=="PRO" else "FREE"

class FeatureService:
    """One entitlement boundary; unknown features are denied safely."""
    def __init__(self, plan=None, provider=None):
        self.provider=provider or LocalLicenseProvider()
        self.plan=normalize_plan(plan if plan is not None else self.provider.plan())
    def can(self, feature):
        feature=str(feature or "").strip().upper()
        return feature in FREE_FEATURES or (self.plan=="PRO" and feature in PRO_FEATURES)
