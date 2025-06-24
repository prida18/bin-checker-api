import csv

def load_bin_data(csv_paths):
    bin_lookup = {}

    for path in csv_paths:
        with open(path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                bin_id = row["BIN"].strip()
                bin_lookup[bin_id] = {
                    "brand": row.get("Brand", "").upper(),
                    "type": row.get("Type", "").upper(),
                    "category": row.get("Category", "").upper(),
                    "issuer": row.get("Issuer", ""),
                    "issuer_phone": row.get("IssuerPhone", ""),
                    "issuer_url": row.get("IssuerUrl", ""),
                    "country": {
                        "name": row.get("CountryName", ""),
                        "alpha2": row.get("isoCode2", "").upper(),
                        "alpha3": row.get("isoCode3", "").upper()
                    }
                }
    return bin_lookup
