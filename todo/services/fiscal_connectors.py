"""Fiscal connector registry: no country is claimed compliant until verified."""
from country_profiles import normalize_country_code

_CONNECTORS={}

def connector_for_country(country_code):
    """Return a verified connector, or None when no verified integration exists."""
    return _CONNECTORS.get(normalize_country_code(country_code))

def availability(country_code):
    code=normalize_country_code(country_code)
    connector=connector_for_country(code)
    if connector is None:
        return {"country_code":code,"available":False,"reason":"Fiscal connector not configured or verified."}
    return {"country_code":code,"available":True,"reason":"Verified connector available.","connector":connector}
