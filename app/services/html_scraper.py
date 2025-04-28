import json
import re
import aiohttp
from bs4 import BeautifulSoup
from utils.logger import setup_logger
import os


STATE = os.getenv("STATE")
logger = setup_logger("scraper")



async def fetch_company_details(url: str) -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
                return await parse_html_details(html)
    except Exception as e:
        logger.error(f"Error fetching data for query '{url}': {e}")
        return []
async def fetch_company_data(query: str) -> list[dict]:
    url = "https://ecorp.azcc.gov/EntitySearch/Search"
    payload = f"model%5BPageID%5D=0&model%5BPageCount%5D=0&model%5BTotalResults%5D=0&model%5BTotalPages%5D=0&model%5BMessage%5D=&model%5BSearchCriteria%5D%5BSearchCriteria%5D=&model%5BSearchCriteria%5D%5BSearchType%5D=&model%5BSearchCriteria%5D%5BSearchValue%5D=&model%5BSearchCriteria%5D%5BquickSearch%5D%5BStartsWith%5D=true&model%5BSearchCriteria%5D%5BquickSearch%5D%5BContains%5D=false&model%5BSearchCriteria%5D%5BquickSearch%5D%5BExactMatch%5D=false&model%5BSearchCriteria%5D%5BquickSearch%5D%5BBusinessName%5D={query}&model%5BSearchCriteria%5D%5BquickSearch%5D%5BAgentName%5D=&model%5BSearchCriteria%5D%5BquickSearch%5D%5BPrincipalName%5D=&model%5BSearchCriteria%5D%5BquickSearch%5D%5BBusinessId%5D=&model%5BSearchCriteria%5D%5BquickSearch%5D%5BbarcodeNumber%5D=&model%5BSearchCriteria%5D%5BquickSearch%5D%5BFilingNumber%5D=&model%5BSearchCriteria%5D%5BquickSearch%5D%5BMicroFilmLocation%5D=&model%5BSearchCriteria%5D%5BquickSearch%5D%5BBusinessModal%5D=&model%5BSearchCriteria%5D%5BadvancedSearch%5D%5BBusinessTypeID%5D=All&model%5BSearchCriteria%5D%5BadvancedSearch%5D%5BBusinessStatusID%5D=All&model%5BSearchCriteria%5D%5BadvancedSearch%5D%5BNameType%5D=All&model%5BSearchCriteria%5D%5BadvancedSearch%5D%5BStreetAddress1%5D=&model%5BSearchCriteria%5D%5BadvancedSearch%5D%5BZipCode%5D=&model%5BSearchCriteria%5D%5BadvancedSearch%5D%5BCity%5D=&model%5BSearchCriteria%5D%5BadvancedSearch%5D%5BCounty%5D=All&model%5BSearchCriteria%5D%5BadvancedSearch%5D%5BZip4%5D=&model%5BSearchCriteria%5D%5BadvancedSearch%5D%5BFields%5D=businessentitytype%3D%7C%7Cbusinessstatus%3DE%7C%7CnameType%3D%7C%7CCounty%3D%7C%7CStreetAddress1%3D%7C%7Ccity%3D%7C%7Czipcode%3D%7C%7CisSimilarSoundingBusiness%3D0%7C%7CisSimilarSoundingAgent%3D0%7C%7CisSimilarSoundingAgent%3D0%7C%7CisSimilarSoundingPrincipal%3D0&model%5BSearchResults%5D=&"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    }
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url, data=payload) as response:
                response.raise_for_status()
                json_data = await response.text()
                data = json.loads(json_data)
                return await parse_html_search(data['Data'])
    except Exception as e:
        logger.error(f"Error fetching data for query '{query}': {e}")
        return []

async def parse_html_search(html: str):
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table#grid_resutList tbody tr")

    results = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue

        entity_id = cols[0].text
        name_tag = cols[1].find("a")
        entity_name = name_tag.text if name_tag else cols[1].text
        entity_id_url = name_tag["href"] if name_tag and "href" in name_tag.attrs else ""
        status = cols[6].text if len(cols) > 6 else ""

        results.append({
            "state": STATE,
            "name": entity_name,
            "status": status,
            "id": entity_id,
            "url": "https://ecorp.azcc.gov" + entity_id_url
        })

    return results


async def parse_html_details(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    async def get_documents(number):
        try:
            payload = f'businessId={number}&source=online'
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            url = "https://ecorp.azcc.gov/BusinessSearch/BusinessFilings"
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(url, data=payload) as response:
                    response.raise_for_status()
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    table = soup.find('table', id='xhtml_grid')
                    rows = table.tbody.find_all('tr')
                    documents = []
                    for row in rows:
                        a_tag = row.find('a', attrs={'name': 'lnkdownload'})
                        if a_tag:
                            name = a_tag.get_text(strip=True)
                            link = a_tag['href']
                            documents.append({
                                'name': name,
                                'url': 'https://ecorp.azcc.gov'+link
                            })
                    return documents
        except Exception as e:
            logger.error(f"Error fetching data for documents '{number}': {e}")
            return []

    name = soup.find("label", attrs={"for": "Business_BusinessName"}).find_parent('div').find_next_sibling('div').text.strip()
    registration_number = soup.find("label", attrs={"for": "Business_BusinessNumber"}).find_parent('div').find_next_sibling('div').text.strip()
    entity_type = soup.find("label", attrs={"for": "Business_EntityType"}).find_parent('div').find_next_sibling('div').text.strip()
    status = soup.find("strong", style=lambda x: x and "font-weight: bold;" in x)
    status = status.get_text() if status else ""
    date_registered = soup.find("label", attrs={"for": "Business_FormationDate"}).find_parent('div').find_next_sibling('div').text.strip()
    agent_name = soup.find("label", attrs={"for": "Agent_AgentName"}).find_parent('div').find_next_sibling('div').text.strip()
    principal_address = soup.find("label", attrs={"for": "Agent_PrincipalAddress"}).find_parent('div').find_next_sibling('div').text.strip()
    mailing_address = soup.find("label", attrs={"for": "Agent_MailingAddress_FullAddress"}).find_parent('div').find_next_sibling('div').text.strip()
    input_tag = soup.find('input', attrs={'value': 'Document History'})
    onclick_attr = input_tag.get('onclick')
    match = re.search(r'submitFilingHistory\((\d+)\)', onclick_attr)
    if match:
        number = match.group(1)
        document_images = await get_documents(number)

    return {
        "state": STATE,
        "name": name,
        "status": status,
        "registration_number": registration_number,
        "date_registered": date_registered,
        "entity_type": entity_type,
        "agent_name": agent_name,
        "principal_address": principal_address,
        "mailing_address": mailing_address,
        "document_images": document_images
    }