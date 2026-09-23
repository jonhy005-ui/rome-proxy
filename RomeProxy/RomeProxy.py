
from fastapi import FastAPI, HTTPException, Security, Depends

from fastapi.security import APIKeyHeader

from fastapi.middleware.cors import CORSMiddleware

from fastapi import Request

from fastapi.responses import JSONResponse

from bs4 import BeautifulSoup

from urllib.parse import urljoin

import requests

import re

import os

import secrets



app = FastAPI(

    title="ROME ADEM Proxy",

    version="1.0.0"

)





# Configuration CORS étendue pour Render

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],  # Ou spécifiez votre domaine frontend

    allow_credentials=True,

    allow_methods=["GET", "OPTIONS"],

    allow_headers=["X-API-Key", "Content-Type"],

)



# Gestion explicite des requêtes OPTIONS pour les routes avec paramètres

@app.options("/search")

@app.options("/search/")

@app.options("/job/{rome_code}")

@app.options("/job/{rome_code}/")

@app.options("/job/{rome_code}/appellations")

async def handle_options(request: Request):

    return JSONResponse(

        content={},

        headers={

            "Access-Control-Allow-Origin": "*",

            "Access-Control-Allow-Methods": "GET, OPTIONS",

            "Access-Control-Allow-Headers": "X-API-Key, Content-Type",

            "Access-Control-Max-Age": "86400",

        }

    )



BASE_URL = "https://rome.adem.etat.lu"

SEARCH_URL = f"{BASE_URL}/search/"



# --- Sécurité par clé API ---

#

# La clé attendue est lue depuis la variable d'environnement ROME_PROXY_API_KEY.

# Ne jamais mettre la clé en dur dans le code source.

#

# Exemple de lancement :

#   export ROME_PROXY_API_KEY="une-longue-chaine-secrete"

#   uvicorn RomeProxy:app --host 0.0.0.0 --port 8000



API_KEY_NAME = "X-API-Key"

API_KEY = os.environ.get("ROME_PROXY_API_KEY")



api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)



def clean_text(text):

    """Nettoie une chaîne en supprimant espaces/saut de ligne superflus."""

    if not text:

        return None

    # Remplace les sauts de ligne/tabulations par un espace, puis nettoie

    text = re.sub(r'[\n\t\r]+', ' ', str(text))

    # Supprime les espaces multiples et les espaces en début/fin

    text = ' '.join(text.split()).strip()

    return text if text else None



def verify_api_key(provided_key: str = Security(api_key_header)):

    if not API_KEY:

        # Si aucune clé n'est configurée côté serveur, on bloque l'accès

        # plutôt que de laisser l'API ouverte par erreur de configuration.

        raise HTTPException(

            status_code=500,

            detail="Server misconfiguration: ROME_PROXY_API_KEY is not set."

        )



    if not provided_key or not secrets.compare_digest(provided_key, API_KEY):

        raise HTTPException(

            status_code=401,

            detail="Invalid or missing API key."

        )



    return provided_key



@app.get("/")

def root():

    return {

        "service": "ROME ADEM Proxy",

        "status": "running"

    }



@app.get("/categories")

def get_categories(api_key: str = Depends(verify_api_key)):

    try:

        response = requests.get(

            f"{BASE_URL}/index_metier.html",

            timeout=20

        )



        response.raise_for_status()

        html = response.content.decode("utf-8", errors="replace")

        soup = BeautifulSoup(html, "html.parser")



        results = []



        for link in soup.find_all("a"):

            href = link.get("href")

            label = link.get_text(strip=True)



            if href and "fiches_rome" in href:

                results.append({

                    "name": clean_text(label),

                    "url": href

                })



        return {

            "count": len(results),

            "items": results

        }



    except Exception as ex:

        raise HTTPException(

            status_code=500,

            detail=str(ex)

        )



@app.get("/search")

def search(q: str, page: int = 1, api_key: str = Depends(verify_api_key)):



    try:



        offset = (page - 1) * 20



        response = requests.get(

            SEARCH_URL,

            params={

                "q": q,

                "b": offset

            },

            timeout=30

        )





        response.raise_for_status()

        html = response.content.decode("utf-8", errors="replace")

        soup = BeautifulSoup(

            html,

            "html.parser"

        )



        results = []



        for hit in soup.select("li.hit"):



            hit_id = hit.get("id")



            code = None

            title = None

            url = None



            first_link = hit.find("a", href=True)



            if first_link:



                href = first_link.get("href")



                if href:

                    url = urljoin(

                        BASE_URL,

                        href

                    )



                title_text = first_link.get_text(

                    " ",

                    strip=True

                )



                match = re.match(

                    r"([A-Z]\d{4})\s*-\s*(.*)",

                    title_text

                )



                if match:



                    code = match.group(1).strip()



                    title = match.group(2).strip()



                else:



                    title = title_text



            types = []



            type_node = hit.select_one(

                "p.Type"

            )



            if type_node:



                types = [

                    clean_text(x) for x in type_node.get_text(

                        " ",

                        strip=True

                    ).split(",")

                    if x.strip()

                ]



            category = None



            category_node = hit.select_one(

                "p.Category"

            )



            if category_node:



                strong = category_node.find(

                    "strong"

                )



                if strong:

                    strong.extract()



                category = clean_text(category_node.get_text(

                    " ",

                    strip=True

                ))



            description = None



            description_node = hit.select_one(

                "p.description"

            )



            if description_node:



                description = clean_text(description_node.get_text(

                    " ",

                    strip=True

                ))



            examples = []



            themes_node = hit.select_one(

                "p.Themes"

            )



            if themes_node:



                strong = themes_node.find(

                    "strong"

                )



                if strong:

                    strong.extract()



                examples_text = themes_node.get_text(

                    " ",

                    strip=True

                )



                examples = [

                    clean_text(x) for x in examples_text.split(",")

                    if x.strip()

                ]



            results.append(

                {

                    "id": hit_id,

                    "rome_code": clean_text(code),

                    "title": clean_text(title),

                    "url": url,

                    "types": types,

                    "main_type": (

                        types[0]

                        if len(types) > 0

                        else None

                    ),

                    "category": category,

                    "description": description,

                    "examples": examples,

                    "examples_count": len(examples),

                    "details_url": f"/job/{code}",

                    "html_fragment": str(hit)

                }

            )



        return {

            "query": clean_text(q),

            "page": page,

            "count": len(results),

            "results": results

        }



    except Exception as ex:



        raise HTTPException(

            status_code=500,

            detail=str(ex)

        )



@app.get("/job/{rome_code}")

def get_job(rome_code: str, api_key: str = Depends(verify_api_key)):



    try:



        url = f"{BASE_URL}/fiches_rome/{rome_code}.html"



        response = requests.get(

            url,

            timeout=30

        )



        response.raise_for_status()

        html = response.content.decode("utf-8", errors="replace")

        soup = BeautifulSoup(

            html,

            "html.parser"

        )



        title = None



        header = soup.find(["h1", "h2"])



        if header:

            title = clean_text(header.get_text(

                " ",

                strip=True

            ))



        sections = {}



        current_section = None



        for node in soup.find_all(

            ["h1", "h2", "h3", "h4", "p", "ul"]

        ):



            if node.name in [

                "h1",

                "h2",

                "h3",

                "h4"

            ]:



                current_section = clean_text(node.get_text(

                    " ",

                    strip=True

                ))



                sections[current_section] = []



                continue



            if not current_section:

                continue



            if node.name == "p":



                text = clean_text(node.get_text(

                    " ",

                    strip=True

                ))



                if text:



                    sections[current_section].append(

                        text

                    )



            elif node.name == "ul":



                for li in node.find_all("li"):



                    text = clean_text(li.get_text(

                        " ",

                        strip=True

                    ))



                    if text:



                        sections[current_section].append(

                            text

                        )



        return {

            "rome_code": clean_text(rome_code),

            "title": title,

            "source_url": url,

            "sections": sections

        }



    except Exception as ex:



        raise HTTPException(

            status_code=500,

            detail=str(ex)

        )



@app.get("/job/{rome_code}/appellations")

def get_job_appellations(rome_code: str, api_key: str = Depends(verify_api_key)):



    try:



        url = f"{BASE_URL}/fiches_rome/{rome_code}.html"



        response = requests.get(

            url,

            timeout=30

        )



        response.raise_for_status()

        html = response.content.decode("utf-8", errors="replace")

        soup = BeautifulSoup(

            html,

            "html.parser"

        )



        title = None



        title_tag = soup.find(["h1", "h2"])



        if title_tag:

            title = clean_text(title_tag.get_text(

                " ",

                strip=True

            ))



        appellations = []



        appellations_div = soup.find(

            "div",

            id="Appellations"

        )



        if appellations_div:



            # Chaque appellation est un <div id="..."> enfant direct de

            # <div id="Appellations">. Il contient, dans l'ordre :

            #   - un <span class="no-information"> (vide, pas d'info-bulle)

            #     OU un <span class="information-icon"> suivi d'un

            #     <span class="popup" id="i..."> (l'info-bulle, avec un

            #     <div class="popup-title"> + le texte de la remarque)

            #   - un dernier <span> sans classe : le libellé de l'appellation

            items = appellations_div.find_all("div", recursive=False)



            if items:



                for item in items:



                    appellation_id = item.get("id")



                    spans = item.find_all("span", recursive=False)



                    if not spans:

                        continue



                    # Le libellé est toujours le dernier <span> direct

                    label_span = spans[-1]



                    label = clean_text(label_span.get_text(

                        " ",

                        strip=True

                    ))



                    if not label:

                        continue



                    # S'il y a 3 spans (icône + popup + libellé), le popup

                    # (2e span) porte l'info-bulle à extraire séparément.

                    tooltip = None



                    if len(spans) >= 3:



                        popup_span = spans[1]



                        popup_title_node = popup_span.find("div", class_="popup-title")



                        title_text = clean_text(

                            popup_title_node.get_text(" ", strip=True)

                        ) if popup_title_node else None



                        content_parts = []



                        for div_node in popup_span.find_all("div"):



                            if div_node is popup_title_node:

                                continue



                            part_text = clean_text(div_node.get_text(

                                " ",

                                strip=True

                            ))



                            if part_text:

                                content_parts.append(part_text)



                        content_text = " ".join(content_parts) if content_parts else None



                        if title_text and content_text:

                            tooltip = f"{title_text} : {content_text}"

                        else:

                            tooltip = title_text or content_text



                    appellations.append({

                        "id": clean_text(appellation_id),

                        "label": label,

                        "tooltip": tooltip

                    })



            else:



                # Repli si la structure attendue n'est pas trouvée : on tente

                # de découper le texte brut. Dans ce cas, ni id ni info-bulle

                # ne sont disponibles distinctement.

                raw_text = appellations_div.get_text(

                    "\n",

                    strip=True

                )



                for chunk in re.split(r"[\n,]+", raw_text):

                    chunk = clean_text(chunk)

                    if chunk:

                        appellations.append({

                            "id": None,

                            "label": chunk,

                            "tooltip": None

                        })



        # Suppression des doublons (même id + même libellé) tout en conservant l'ordre d'apparition

        seen = set()

        unique_appellations = []



        for item in appellations:



            key = (item["id"], item["label"], item["tooltip"])



            if key not in seen:

                seen.add(key)

                unique_appellations.append(item)



        return {

            "rome_code": clean_text(rome_code),

            "title": title,

            "url": url,

            "appellations_count": len(unique_appellations),

            "appellations": unique_appellations

        }



    except Exception as ex:



        raise HTTPException(

            status_code=500,

            detail=str(ex)

        )
