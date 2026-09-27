# Open Source & Third-Party Legal Notices — DOGFOOD 2026

## 1. Project License
The **DOGFOOD 2026 Hackathon Platform** is licensed under the **MIT License** ([LICENSE](file:///c:/Users/heman/Desktop/dogfood/LICENSE)).

```
MIT License
Copyright (c) 2026 DOGFOOD Hackathon Team
```

---

## 2. Open-Source Dependencies & Software Bill of Materials (SBOM)

This project has been developed with **zero proprietary cloud dependencies** and relies exclusively on permissive, OSI-approved open-source libraries:

| Component | License | Copyright / Origin | Permitted Use |
| :--- | :--- | :--- | :--- |
| **FastAPI** | MIT License | (c) 2018 Sebastián Ramírez | Commercial, modification, distribution |
| **Starlette** | BSD-3-Clause | (c) 2018 Encode OSS Ltd | Commercial, modification, distribution |
| **Uvicorn** | BSD-3-Clause | (c) 2017 Encode OSS Ltd | Commercial, modification, distribution |
| **Jinja2** | BSD-3-Clause | (c) 2007 Pallets Team | Commercial, modification, distribution |
| **Pydantic** | MIT License | (c) 2017 Samuel Colvin | Commercial, modification, distribution |
| **SQLite** | Public Domain | Dedicated to public domain (D. Richard Hipp) | Unrestricted use |
| **Python Standard Library** | PSF License | Python Software Foundation | Unrestricted open source |

---

## 3. Legal & Privacy Compliance Checklist

- [x] **OSI-Approved License (`LICENSE`)**: Standard MIT License provided at the root of the repository.
- [x] **No Proprietary Vendor Lock-In**: Platform runs completely offline on local hardware with zero external API calls or telemetry beacons.
- [x] **GDPR & Privacy Protection**: All user records, reviewer profiles, and team submissions in [`fixtures.json`](file:///c:/Users/heman/Desktop/dogfood/fixtures.json) utilize synthetic, anonymized domain names (`@example.org`, `@dogfood.local`). No real personal identifiable information (PII) is stored or processed.
- [x] **Originality of Authoring**: All application logic, database schemas, authorization guards, and normalization algorithms were created during the competition window.
- [x] **Asset Integrity**: All CSS, SVG graphics, and layout templates are original assets with zero unlicensed commercial fonts, stock imagery, or proprietary icons.
