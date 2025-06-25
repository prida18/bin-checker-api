from fastapi import FastAPI, Query, Request, HTTPException,Header
from load_data import load_bin_data
from typing import Optional
import json
import requests

app = FastAPI() 

RAPIDAPI_KEY_HEADER = "x-rapidapi-key"
# Load CSVs into memory on startup
bin_data = load_bin_data(["bin-list-data.csv","bin-list-data2.csv"])
with open("countries.json", "r", encoding="utf-8") as f:
    countries = json.load(f) 

def enrich_country_info(country):
    name = country.get("name", {}).get("common", "")
    native_names = country.get("name", {}).get("native", {})
    native = next(iter(native_names.values()))["common"] if native_names else name
    flag = country.get("flag", "")
    numeric = country.get("ccn3", "")
    capital = country.get("capital", [""])[0]
    currencies = country.get("currencies", {})
    currency_code = next(iter(currencies), "")
    currency_info = currencies.get(currency_code, {}) if currency_code else {}
    currency_name = currency_info.get("name", "")
    currency_symbol = currency_info.get("symbol", "")
    region = country.get("region", "")
    subregion = country.get("subregion", "")
    idd_root = country.get("idd", {}).get("root", "")
    idd_suffix = country.get("idd", {}).get("suffixes", [""])[0]
    idd = idd_root + idd_suffix if idd_root else ""
    alpha2 = country.get("cca2", "")
    alpha3 = country.get("cca3", "")
    languages = country.get("languages", {})
    language_code = next(iter(languages), "")
    language = languages.get(language_code, "")

    return {
        "name": name,
        "native": native,
        "flag": flag,
        "numeric": numeric,
        "capital": capital,
        "currency": currency_code,
        "currency_name": currency_name,
        "currency_symbol": currency_symbol,
        "region": region,
        "subregion": subregion,
        "idd": idd,
        "alpha2": alpha2,
        "alpha3": alpha3,
        "language": language,
        "language_code": language_code
    }

def find_country_by_alpha2(alpha2_code):
    return next((c for c in countries if c.get("cca2") == alpha2_code), None)



def get_ip_info(ip):
    try:
        response = requests.get(f"https://ipwho.is/{ip}")
        data = response.json()
        if data.get("success", False):
            return {
                "ip": ip,
                "country": data.get("country"),
                "region": data.get("region"),
                "city": data.get("city"),
                "country_code": data.get("country_code"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "org": data.get("org"),
                "isp": data.get("connection", {}).get("isp", "")
            }
    except Exception as e:
        print(f"IP Lookup failed: {e}")
    return None


@app.get("/check")
def check_bin(request: Request, bin: str = Query(...), ip: Optional[str] = None,x_rapidapi_key: Optional[str] = Header(None)):
    if not x_rapidapi_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    bin_prefix = bin[:6]
    data = bin_data.get(bin_prefix)

    if not data: 
        return {"success": False, "code": 404, "message": "BIN not found"}

    # Sanitize fields
    brand = data.get("brand", "").upper() or "UNKNOWN"
    type_ = data.get("type", "").upper() or "UNKNOWN"
    level = data.get("category", "").upper() or "UNKNOWN"
    issuer = data.get("issuer", "") or "UNKNOWN"
    issuer_url = data.get("issuer_url", "") or "UNKNOWN"
    issuer_phone = data.get("issuer_phone", "") or "UNKNOWN"

    # Determine commercial/prepaid
    is_prepaid = "PREPAID" in level
    is_commercial = any(keyword in level for keyword in ["BUSINESS", "COMMERCIAL", "CORPORATE"]) or \
                    any(keyword in type_ for keyword in ["BUSINESS", "COMMERCIAL", "CORPORATE"])

    # Enrich country data
    country_code = data["country"].get("alpha2", "")
    full_country_obj = find_country_by_alpha2(country_code)
    enriched = enrich_country_info(full_country_obj) if full_country_obj else {
        "name": data["country"].get("name", "UNKNOWN"),
        "alpha2": country_code or "UNKNOWN"
    }

    response = {
        "success": True,
        "code": 200,
        "BIN": {
            "valid": True,
            "number": int(bin_prefix),
            "length": 6,
            "scheme": brand,
            "brand": brand,
            "type": type_,
            "level": level,
            "is_commercial": is_commercial,
            "is_prepaid": is_prepaid,
            "currency": enriched.get("currency", "UNKNOWN"),
            "issuer": {
                "name": issuer,
                "website": issuer_url,
                "phone": issuer_phone
            },
            "country": enriched
        }
    }

    if ip:
        ip_data = get_ip_info(ip)
        response["IP"] = ip_data or {"error": "Failed to get IP info"}

        # Simple fraud score
        bin_country = data["country"].get("alpha2", "").upper()
        ip_country = ip_data.get("country_code", "").upper() if ip_data else ""
        response["risk_score"] = {
            "bin_country": bin_country,
            "ip_country": ip_country,
            "match": bin_country == ip_country,
            "score": 20 if bin_country == ip_country else 75
        }

    return response
