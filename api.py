import json
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from selenium_driverless import webdriver
from selenium_driverless.types.by import By
import dateutil.parser
import asyncio
import uuid
import time
import threading
import re

app = Flask("NameMC Droptime API")
app.config['TIMEOUT'] = 30

limiter = Limiter(app)

apiKeysFile = 'apikeys.json'

try:
    with open(apiKeysFile, 'r') as file:
        apiKeys = json.load(file)
except FileNotFoundError:
    apiKeys = {}

cachedData = {}

def save_api_keys_to_file():
    active_keys = {k: v for k, v in apiKeys.items() if v["privileged"]}
    with open(apiKeysFile, 'w') as file:
        json.dump(active_keys, file, indent=4)
    
def generate_api_key(discord_id, discord_username):
    new_api_key = str(uuid.uuid4())
    apiKeys[new_api_key] = {
        "privileged": True,
        "discordId": discord_id,
        "discordUsername": discord_username
    }
    save_api_keys_to_file()
    return new_api_key

def validate_api_key(api_key):
    return api_key in apiKeys and apiKeys[api_key]["privileged"]

def validate_secret(secret):
    return secret == "PR69wU2FAmCu5BhxZyaYqXTk8zVc3t7EDjSs4pMnfdQKbLHegv"

async def getDroptime(name: str):
    options = webdriver.ChromeOptions()
    options.headless = False
    async with webdriver.Chrome(options=options) as driver:
        await driver.get(f"https://namemc.com/search?q={name}")
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

        # Cache the data
        cachedData[name] = {"data": data, "endUnix": endUnix}
        return data

async def getSearches(name : str):
    options = webdriver.ChromeOptions()
    options.headless = False
    async with webdriver.Chrome(options=options) as driver:
        await driver.get(f"https://namemc.com/search?q={name}")
        await driver.sleep(0.5)
        await driver.wait_for_cdp("Page.domContentEventFired", timeout=15)

        searchesElement = await driver.find_element(By.XPATH, '//*[@id="status-bar"]/div/div[2]/div[2]')
        searchesText = await searchesElement.text
        searches = int(re.search(r'\d+', searchesText).group())

        data = {
            "searches": searches
        }
        return data

@app.route('/generateKey', methods=['POST'])
def generate_api_key_endpoint():
    secret = request.headers.get('X-Secret')

    if not validate_secret(secret):
        return jsonify({"error": "Invalid generation secret"}), 403
    
    try:
        json_data = request.json
        discord_id = json_data.get('discordId')
        discord_username = json_data.get('discord')
    except ValueError:
        return jsonify({"error": "Invalid JSON format"}), 400

    new_api_key = generate_api_key(discord_id, discord_username)
    save_api_keys_to_file()
    return jsonify({"api_key": new_api_key})


@app.route('/disableKey', methods=['POST'])
def disable_api_key():
    secret = request.headers.get('X-Secret')

    if not validate_secret(secret):
        return jsonify({"error": "Invalid secret"}), 403

    try:
        json_data = request.json
        apiKey = json_data.get('apiKey')

        if apiKey not in apiKeys:
            return jsonify({"error": "API key not found"}), 404

        # Disable the API key
        apiKeys[apiKey]["privileged"] = False
        save_api_keys_to_file()

        return jsonify({"message": "API key disabled successfully"})
    except ValueError:
        return jsonify({"error": "Invalid JSON format"}), 400


@app.route('/getDroptime', methods=['GET'])
@limiter.limit("5 per minute")
async def get_droptime():
    name = request.args.get('name')
    api_key = request.headers.get('X-API-Key')

    if not validate_api_key(api_key):
        return jsonify({"error": "Invalid API key or insufficient privileges"}), 401

    try:
        # Check if data is in the cache before fetching
        if name in cachedData:
            return jsonify(cachedData[name]["data"])

        data = await getDroptime(name)
        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/getSearches', methods=['GET'])
@limiter.limit("5 per minute")
async def get_searches():
    name = request.args.get('name')
    api_key = request.headers.get('X-API-Key')

    if not validate_api_key(api_key):
        return jsonify({"error": "Invalid API key or insufficient privileges"}), 401

    try:
        data = await getSearches(name)
        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def periodic_cleanup():
    while True:
        now_unix = int(time.time())

        to_remove = [name for name, data in cachedData.items() if data["endUnix"] <= now_unix]
        for name in to_remove:
            del cachedData[name]

        time.sleep(60)

async def main():
    cleanup_thread = threading.Thread(target=periodic_cleanup)
    cleanup_thread.start()
    app.run(debug=False)

if __name__ == '__main__':
    asyncio.run(main())
