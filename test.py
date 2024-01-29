from selenium_driverless import webdriver
from selenium_driverless.types.by import By
from pyvirtualdisplay import Display
import asyncio
import dateutil.parser

async def getDroptime(name: str):
    disp = Display()
    disp.start()

    print("trying to create driver")
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--headless")
    async with webdriver.Chrome(debug=True, options=options) as driver:
        print("driver created")
        await driver.get(f"https://namemc.com/search?q={name}")
        await driver.sleep(0.5)
        await driver.wait_for_cdp("Page.domContentEventFired", timeout=30)
        print("wait done")
        startElement = await driver.find_element(By.ID, "availability-time")
        print(startElement)  # Add this line

        endElement = await driver.find_element(By.ID, "availability-time2")
        print(endElement)  # Add this line

        start = await startElement.get_dom_attribute("datetime")
        end = await endElement.get_dom_attribute("datetime")

        startUnix = int(dateutil.parser.isoparse(start).timestamp())
        endUnix = int(dateutil.parser.isoparse(end).timestamp())

        data = {
            "startUnix": startUnix,
            "endUnix": endUnix
        }
        disp.stop()
        return data

name = input("What name do you want to scrape? ")
print(asyncio.run(getDroptime(name)))