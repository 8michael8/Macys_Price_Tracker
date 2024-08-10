import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import re

#Brightdata login Informartion
username = 'brd-customer-hl_01bbc4c4-zone-macys_scrape'
password = '4i7oe41b7dpl'
auth = f'{username}:{password}'
host = 'brd.superproxy.io:9222'
browser_url = f'wss://{auth}@{host}'

async def scrape_individual_item(keyword, link):
    async with async_playwright() as pw:
        attempts = 0
        success = False
        browser = None

        while attempts < 3 and not success:
            try:
                print(f"Attempt {attempts + 1}", flush=True)
                # Wait for the main container to ensure the page is fully loaded
                print('Connecting to browser')
                # Launch new browser
                browser = await pw.chromium.connect_over_cdp(browser_url)
                print('Connected')
                page = await browser.new_page()
                # Go to Macy's URL
                if link is None:
                    print(f'Navigating to Macy\'s with keyword: {keyword}')
                    await page.goto(f"https://www.macys.com/shop/search?keyword={keyword}", timeout=60000)
                else:
                    print(f'Navigating to Macy\'s with specified link: {link}')
                    await page.goto(link, timeout=60000)
                print('Data extraction in progress')

                print("Waiting for main container", flush=True)
                # Check if the main content div is present
                await page.wait_for_selector('div.c-margin-top-3v', timeout=60000)
                print('Main container found', flush=True)

                # select the main container
                main_cont_present = await page.query_selector('div.c-margin-top-3v')
                success = True
            except Exception as e:
                print(f"Attempt {attempts + 1} failed: {e}", flush=True)
                attempts += 1
                if attempts < 3:
                    print("Retrying...", flush=True)
                else:
                    print("All attempts failed. Exiting.", flush=True)
                    if browser:
                        await browser.close()
                    return []

        if not success:
            return []

        try:
            results = []
            result = {}

            # Product Brand
            brand_element = await main_cont_present.query_selector('a[data-auto="product-brand"]')
            brand_name = (await brand_element.inner_text()).strip() if brand_element else 'N/A'

            # Product Name
            product_desc_element = await main_cont_present.query_selector('div[data-auto="product-name"]')
            product_desc = (await product_desc_element.inner_text()).strip() if product_desc_element else 'N/A'

            result['brand_name'] = brand_name
            result['product_name'] = product_desc

            # Price
            sale_price_element = await main_cont_present.query_selector('div.lowest-sale-price span.bold.c-red')
            original_price_element = await main_cont_present.query_selector('div.c-strike')
            if not original_price_element:
                original_price_element = await main_cont_present.query_selector('div.lowest-sale-price span.bold')

            sale_price = (await sale_price_element.inner_text()).strip() if sale_price_element else 'N/A'
            original_price = (await original_price_element.inner_text()).strip() if original_price_element else 'N/A'

            result['original_price'] = original_price
            result['sale_price'] = sale_price

            #product link
            result['product_link'] = f"https://www.macys.com/shop/search?keyword={keyword}"

            if result['product_name'] != 'N/A':
                results.append(result)
        finally:
            # Close browser
            if browser:
                await browser.close()

            return results

        ''' # Rating and Number of reviews
         rating_element = await main_cont_present.query_selector('div[data-el="pdp-stars"]')
         if rating_element:
             rating_text = (await rating_element.get_attribute('aria-label')).strip()
             # Extract rating and number of reviews from the aria-label attribute
             rating_match = re.search(r'([\d\.]+) out of 5 rating with ([\d,]+) reviews', rating_text)
             if rating_match:
                 result['rating'] = rating_match.group(1)
                 result['number_of_reviews'] = int(rating_match.group(2).replace(',', ''))
             else:
                 result['rating'] = 'N/A'
                 result['number_of_reviews'] = 'N/A'
         else:
             result['rating'] = 'N/A'
             result['number_of_reviews'] = 'N/A'
         print(f"Rating: {result['rating']}")
         print(f"Number of Reviews: {result['number_of_reviews']}")'''
