from fastapi import FastAPI, HTTPException
from web3 import Web3
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import requests
import os
from datetime import datetime
import json
from fastapi.responses import JSONResponse
import logging

logging.basicConfig(
    level=logging.INFO,  
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI()

ETHEREUM_RPC_URL ="https://eth-mainnet.g.alchemy.com/v2/gC02g8A97UzBWyoXi5WEX1MS3inp2uw9"
CONTRACT_ABI = json.load((open('./SOTO.abi.json', 'r')))
CONTRACT_ADDRESS="0xD533a949740bb3306d119CC777fa900bA034cd52"
TOKEN_ID="curve-dao-token"

# CoinGecko API URL
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/"

# MongoDB Configuration
MONGO_URI = os.environ.get('MONGO_URI')
MONGO_DB = "token_balance"
MONGO_COLLECTION = "balances"

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
collection = db[MONGO_COLLECTION]


def get_token_balance(wallet: str):
    try:
        # Connect to the Ethereum Node
        web3 = Web3(Web3.HTTPProvider(ETHEREUM_RPC_URL))
        # Get token balance using web3py
        # Token contract address ABI are needed here

        token_contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
        return (token_contract.functions.balanceOf(wallet).call(), int(token_contract.functions.decimals().call()))
    except Exception as e:
        logging.error(f"Error getting token balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_token_price (currency: str):
    try:
        # Here we get token price in USD using CoinGecko
        token_price_response = requests.get(f"{COINGECKO_API_URL}simple/price",params={"ids": TOKEN_ID, "vs_currencies": currency})
        return token_price_response.json()[TOKEN_ID]["usd"] 
    except Exception as e:
        logging.error(f"Error getting token price: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_balance")
def get_balance(wallet: str):
    try: 
        token_balance, decimals = get_token_balance(wallet)
        token_price_usd = get_token_price("usd")

        # Here we calculate token balance in USD
        token_balance_usd = round((token_balance * token_price_usd) // decimals, 2)

        # Here we save the data to MongoDB
        current_time = datetime.now().isoformat()

        collection.insert_one({
            "wallet": wallet, 
            "last_update_time": current_time, 
            "current_balance": token_balance,
            "current_balance_usd": token_balance_usd
        })

        logging.info(f"Balance retrieved for wallet: {wallet}")
        return JSONResponse(content={"wallet": wallet, "token_balance": token_balance, "token_balance_usd": token_balance_usd})
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get_history")
def get_history(wallet: str):
    try: 
        history = collection.find({"wallet": wallet})

        hist_data = list(history)
        for i in range(len(hist_data)):
            hist_data[i]['_id'] = str(hist_data[i]['_id'])

        return JSONResponse(content=hist_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))