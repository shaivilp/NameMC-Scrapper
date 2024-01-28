from selenium_driverless import webdriver
from selenium_driverless.types.by import By
import asyncio
import dateutil.parser

async def getDroptime(name: str):
    async with webdriver.Chrome() as driver:
        print("trying to get droptime")
        await driver.get(f"https://namemc.com/search?q={name}")
        print("trying to get droptime 2")
        await driver.sleep(0.5)
        await driver.wait_for_cdp("Page.domContentEventFired", timeout=15)

        startElement = await driver.find_element(By.ID, "availability-time")
        endElement = await driver.find_element(By.ID, "availability-time2")

        start = await startElement.get_dom_attribute("datetime")
        end = await endElement.get_dom_attribute("datetime")

        startUnix = int(dateutil.parser.isoparse(start).timestamp())
        endUnix = int(dateutil.parser.isoparse(end).timestamp())

        data = {
            "startUnix": startUnix,
            "endUnix": endUnix
        }

        return data

name = input("What name do you want to scrape? ")
print(asyncio.run(getDroptime(name)))