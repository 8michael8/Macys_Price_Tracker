import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import re


username = 'brd-customer-hl_01bbc4c4-zone-macys_scrape'
password = '4i7oe41b7dpl'
auth = f'{username}:{password}'
host = 'brd.superproxy.io:9222'
browser_url = f'wss://{auth}@{host}'


async def scrape_macys_data(keyword):
    async with async_playwright() as pw:
        # Extract information
        results = []

        attempts = 0
        success = False

        while attempts < 3 and not success:
            try:
                print(f"Attempt {attempts + 1}", flush=True)
                # Wait for the main container to ensure the page is fully loaded
                print('Connecting to browser')
                # Launch new browser
                browser = await pw.chromium.connect_over_cdp(browser_url)
                print('Connected')
                page = await browser.new_page()
                print(f'Navigating to Macy\'s with keyword: {keyword}')
                # Go to Macy's URL
                await page.goto(
                    f"https://www.macys.com/shop/search?keyword={keyword}",
                    timeout=60000)
                print('Data extraction in progress')

                print("Waiting for main container", flush=True)

                await page.wait_for_selector('div#app', timeout=60000)
                print('Main container found', flush=True)

                # Select the main container
                main_container = await page.query_selector('div#app')
                success = True
            except Exception as e:
                print(f"Attempt {attempts + 1} failed: {e}", flush=True)
                attempts += 1
                if attempts < 3:
                    print("Retrying...", flush=True)
                else:
                    print("All attempts failed. Exiting.", flush=True)
                    await browser.close()
                    return []

        if not success:
            return []

        # Extract listings within the main container
        listings = await main_container.query_selector_all('div.product-description')

        print(f"Found {len(listings)} listings.")

        # Limit to first 10 listings
        for listing in listings[:10]:
            result = {}

            # Product Name
            brand_element = await listing.query_selector('div.product-brand')
            brand_name = (await brand_element.inner_text()).strip() if brand_element else 'N/A'

            # Product description
            product_desc_link = await listing.query_selector('a.brand-and-name')
            product_desc = (await product_desc_link.inner_text()).strip() if product_desc_link else 'N/A'

            result['brand_name'] = brand_name

            # Full product name
            product_element = await listing.query_selector('div.product-name')
            product_name = (await product_element.inner_text()).strip() if product_element else 'N/A'
            result['product_name'] = product_name


            # Price
            original_price_element = await listing.query_selector('span.price-reg')
            sale_price_element = await listing.query_selector('span.discount')

            if original_price_element:
                result['original_price'] = (await original_price_element.inner_text()).strip()
            else:
                result['original_price'] = 'N/A'

            if sale_price_element:
                original_price_element = await listing.query_selector('span.price-strike')
                result['original_price'] = (await original_price_element.inner_text()).strip()
                result['sale_price'] = (await sale_price_element.inner_text()).strip().replace('Sale ', '')
            else:
                result['sale_price'] = 'N/A'

            # Rating and Number of reviews
            rating_element = await listing.query_selector('div.rating fieldset')
            if rating_element:
                rating_text = (await rating_element.get_attribute('aria-label')).strip()
                # Extract rating and number of reviews from the aria-label attribute
                rating_match = re.search(r'Rated ([\d\.]+) stars with ([\d,]+) reviews', rating_text)
                if rating_match:
                    result['rating'] = rating_match.group(1)
                    result['number_of_reviews'] = int(rating_match.group(2).replace(',', ''))
                else:
                    result['rating'] = 'N/A'
                    result['number_of_reviews'] = 'N/A'
            else:
                result['rating'] = 'N/A'
                result['number_of_reviews'] = 'N/A'

            #product link
            product_href = (await product_desc_link.get_attribute('href')).strip() if product_desc_link else 'N/A'
            result['product_link'] = f"https://macys.com{product_href}"


            if result['product_name'] != 'N/A':
                results.append(result)


        # Close browser
        await browser.close()
        return results


