from fastapi import FastAPI, HTTPException
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests
import re

app = FastAPI(
    title="ROME ADEM Proxy",
    version="1.0.0"
)

BASE_URL = "https://rome.adem.etat.lu"
SEARCH_URL = f"{BASE_URL}/search/"

@app.get("/")
def root():
    return {
        "service": "ROME ADEM Proxy",
        "status": "running"
    }


@app.get("/categories")
def get_categories():
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
                    "name": label,
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
def search(q: str, page: int = 1):

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
                    x.strip()
                    for x in type_node.get_text(
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

                category = category_node.get_text(
                    " ",
                    strip=True
                )

            description = None

            description_node = hit.select_one(
                "p.description"
            )

            if description_node:

                description = description_node.get_text(
                    " ",
                    strip=True
                )

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
                    x.strip()
                    for x in examples_text.split(",")
                    if x.strip()
                ]

            results.append(
                {
                    "id": hit_id,
                    "rome_code": code,
                    "title": title,
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
            "query": q,
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
def get_job(rome_code: str):

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
            title = header.get_text(
                " ",
                strip=True
            )

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

                current_section = node.get_text(
                    " ",
                    strip=True
                )

                sections[current_section] = []

                continue

            if not current_section:
                continue

            if node.name == "p":

                text = node.get_text(
                    " ",
                    strip=True
                )

                if text:

                    sections[current_section].append(
                        text
                    )

            elif node.name == "ul":

                for li in node.find_all("li"):

                    text = li.get_text(
                        " ",
                        strip=True
                    )

                    if text:

                        sections[current_section].append(
                            text
                        )

        return {
            "rome_code": rome_code,
            "title": title,
            "source_url": url,
            "sections": sections
        }

    except Exception as ex:

        raise HTTPException(
            status_code=500,
            detail=str(ex)
        )
        
        
@app.get("/job/{rome_code}/skills")
def get_job_skills(rome_code: str):

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
            title = title_tag.get_text(
                " ",
                strip=True
            )

        skills = set()
        job_titles = set()

        # Extraction de toutes les listes de la fiche
        for li in soup.find_all("li"):

            text = li.get_text(
                " ",
                strip=True
            )

            if text and len(text) > 3:
                skills.add(text)

        # Extraction des exemples d'appellations
        themes = soup.find_all(
            string=lambda t: t and "Exemples d'appellations" in t
        )

        for theme in themes:

            parent = theme.parent

            if parent:

                text = parent.get_text(
                    " ",
                    strip=True
                )

                text = text.replace(
                    "Exemples d'appellations :",
                    ""
                )

                for item in text.split(","):

                    item = item.strip()

                    if item:
                        job_titles.add(item)

        return {
            "rome_code": rome_code,
            "title": title,
            "url": url,
            "skills_count": len(skills),
            "skills": sorted(list(skills)),
            "job_titles_count": len(job_titles),
            "job_titles": sorted(list(job_titles))
        }

    except Exception as ex:

        raise HTTPException(
            status_code=500,
            detail=str(ex)
        )