from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import json
import base64
import uuid
from typing import List, Optional
import asyncio
import requests
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

# Load environment variables
load_dotenv()

# Environment variables
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

print(f"🔑 Loaded API Key: {GEMINI_API_KEY[:10]}..." if GEMINI_API_KEY else "❌ No API Key found")

# FastAPI app
app = FastAPI(title="Food Allergy Detector API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
try:
    client = MongoClient(MONGO_URL)
    db = client.food_allergy_detector
    users_collection = db.users
    food_history_collection = db.food_history
    print("Connected to MongoDB successfully")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")

# Pydantic models
class UserRegistration(BaseModel):
    email: str
    password: str
    allergies: List[str]

class UserLogin(BaseModel):
    email: str
    password: str

class UpdateAllergies(BaseModel):
    user_id: str
    allergies: List[str]

class FoodAnalysisResult(BaseModel):
    food_name: str
    ingredients: List[str]
    allergens_detected: List[str]
    safe_to_eat: bool
    confidence: float
    warning_message: Optional[str] = None

# Initialize Gemini chat - using direct API
def analyze_image_with_gemini(image_base64, user_allergies):
    """Analyze food image using Gemini API directly"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    
    prompt = f"""Analyze this food image and identify ingredients and allergens. 
Pay special attention to these allergens the user is allergic to: {', '.join(user_allergies)}.

Focus on detecting these common allergens:
- Nuts (peanuts, tree nuts)
- Dairy (milk, cheese, butter) 
- Gluten (wheat, barley, rye)
- Shellfish (shrimp, crab, lobster)
- Eggs
- Soy
- Fish
- Sesame

Return your response as a JSON object with this exact structure:
{{
    "food_name": "name of the dish",
    "ingredients": ["ingredient1", "ingredient2", "ingredient3"],
    "allergens_detected": ["allergen1", "allergen2"],
    "confidence": 0.95
}}

Be thorough and conservative - if you're unsure about an ingredient, include it for safety."""

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_base64
                    }
                }
            ]
        }]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        if 'candidates' in result and len(result['candidates']) > 0:
            content = result['candidates'][0]['content']['parts'][0]['text']
            return content
        else:
            raise Exception("No response from Gemini API")
    else:
        raise Exception(f"Gemini API error: {response.status_code} - {response.text}")

def create_gemini_chat():
    return None  # Not needed anymore

# API Routes
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "Food Allergy Detector API is running"}

@app.post("/api/register")
async def register_user(user: UserRegistration):
    try:
        # Check if user already exists
        existing_user = users_collection.find_one({"email": user.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Create new user
        user_id = str(uuid.uuid4())
        user_doc = {
            "user_id": user_id,
            "email": user.email,
            "password": user.password,  # In production, hash this!
            "allergies": user.allergies,
            "created_at": "2025-01-01T00:00:00Z"
        }
        
        users_collection.insert_one(user_doc)
        
        return {
            "success": True,
            "user_id": user_id,
            "message": "User registered successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/login")
async def login_user(user: UserLogin):
    try:
        # Find user
        user_doc = users_collection.find_one({"email": user.email, "password": user.password})
        if not user_doc:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        return {
            "success": True,
            "user_id": user_doc["user_id"],
            "email": user_doc["email"],
            "allergies": user_doc["allergies"]
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/{user_id}")
async def get_user(user_id: str):
    try:
        user_doc = users_collection.find_one({"user_id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "user_id": user_doc["user_id"],
            "email": user_doc["email"],
            "allergies": user_doc["allergies"]
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/user/{user_id}/allergies")
async def update_allergies(user_id: str, update: UpdateAllergies):
    try:
        result = users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"allergies": update.allergies}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"success": True, "message": "Allergies updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze-food")
async def analyze_food_image(
    user_id: str = Form(...),
    image: UploadFile = File(...)
):
    try:
        # Read and encode image
        image_data = await image.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Get user allergies
        user_doc = users_collection.find_one({"user_id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_allergies = user_doc["allergies"]
        
        # Analyze image with Gemini
        ai_response = analyze_image_with_gemini(image_base64, user_allergies)
        
        # Parse JSON response
        try:
            # Clean up response if needed
            response_text = ai_response.strip()
            if response_text.startswith('```json'):
                response_text = response_text.split('```json')[1].split('```')[0]
            elif response_text.startswith('```'):
                response_text = response_text.split('```')[1].split('```')[0]
            
            analysis_data = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            analysis_data = {
                "food_name": "Unknown Food",
                "ingredients": ["Unable to parse ingredients"],
                "allergens_detected": [],
                "confidence": 0.5
            }
        
        # Check for user's specific allergies
        detected_user_allergies = []
        for allergen in analysis_data.get("allergens_detected", []):
            for user_allergen in user_allergies:
                if user_allergen.lower() in allergen.lower() or allergen.lower() in user_allergen.lower():
                    detected_user_allergies.append(allergen)
        
        # Determine safety
        safe_to_eat = len(detected_user_allergies) == 0
        warning_message = None
        
        if not safe_to_eat:
            warning_message = f"⚠️ WARNING: This food contains {', '.join(detected_user_allergies)} which you are allergic to!"
        
        # Create result
        result = FoodAnalysisResult(
            food_name=analysis_data.get("food_name", "Unknown Food"),
            ingredients=analysis_data.get("ingredients", []),
            allergens_detected=detected_user_allergies,
            safe_to_eat=safe_to_eat,
            confidence=analysis_data.get("confidence", 0.8),
            warning_message=warning_message
        )
        
        # Save to history
        history_entry = {
            "user_id": user_id,
            "analysis_id": str(uuid.uuid4()),
            "food_name": result.food_name,
            "ingredients": result.ingredients,
            "allergens_detected": result.allergens_detected,
            "safe_to_eat": result.safe_to_eat,
            "image_base64": image_base64,
            "analyzed_at": "2025-01-01T00:00:00Z"
        }
        
        food_history_collection.insert_one(history_entry)
        
        return result.dict()
        
    except Exception as e:
        print(f"Error analyzing food: {e}")
        raise HTTPException(status_code=500, detail=f"Error analyzing food: {str(e)}")

@app.get("/api/user/{user_id}/history")
async def get_food_history(user_id: str):
    try:
        history = list(food_history_collection.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("analyzed_at", -1).limit(50))
        
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)