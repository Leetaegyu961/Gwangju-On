import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

    async def connect_to_storage(self):
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        db_name = os.getenv("DATABASE_NAME", "gwangju_on")
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client[db_name]
        print(f"✅ Connected to MongoDB: {db_name}")

    async def close_storage(self):
        if self.client:
            self.client.close()
            print("❌ Closed MongoDB connection")

db = MongoDB()

async def get_database():
    return db.db
