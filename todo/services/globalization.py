"""Persisted country-profile settings for the offline point of sale.

Profiles provide display defaults only. They are not a certification of fiscal
compliance, and changing them never rewrites historical sale snapshots.
"""
from country_profiles import get_country_profile, normalize_country_code
from database import connect, get_setting


def _write_setting(conn, key, value):
    conn.execute(
        "INSERT INTO settings(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )


def current_country_profile(conn=None):
    if conn is None:
        with connect() as db:
            return current_country_profile(db)
    return get_country_profile(get_setting("country_code", "MA", conn))


def select_country_profile(country_code, conn=None):
    """Apply a profile to future sales and default product configuration."""
    code = normalize_country_code(country_code)
    profile = get_country_profile(code)
    if conn is None:
        with connect() as db:
            select_country_profile(code, db)
            db.commit()
            return profile
    _write_setting(conn, "country_code", profile.code)
    _write_setting(conn, "currency", profile.currency)
    _write_setting(conn, "tax_label", profile.tax_label)
    _write_setting(conn, "tax_default_rate_basis_points", profile.default_tax_rate_basis_points)
    _write_setting(conn, "tax_default_included", 1 if profile.tax_included_by_default else 0)
    return profile


def new_product_tax_defaults(conn=None):
    """Return tax fields for a new product without touching existing products."""
    if conn is None:
        with connect() as db:
            return new_product_tax_defaults(db)
    profile=current_country_profile(conn)
    rate=get_setting("tax_default_rate_basis_points", profile.default_tax_rate_basis_points, conn)
    included=get_setting("tax_default_included", 1 if profile.tax_included_by_default else 0, conn)
    return {"tax_rate_basis_points": int(rate), "tax_included": 1 if str(included)=="1" else 0}
