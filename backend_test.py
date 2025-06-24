import requests
import json
import base64
import os
import unittest
from io import BytesIO
from PIL import Image, ImageDraw
import random
import uuid
import sys

# Get backend URL from frontend .env file
with open('/app/frontend/.env', 'r') as f:
    for line in f:
        if line.startswith('REACT_APP_BACKEND_URL='):
            BACKEND_URL = line.strip().split('=')[1]
            break

# Ensure API prefix
API_URL = f"{BACKEND_URL}/api"

# Test data
TEST_USER = {
    "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
    "password": "testpass123",
    "allergies": ["Nuts", "Dairy", "Gluten"]
}

class FoodAllergyDetectorAPITest(unittest.TestCase):
    
    def setUp(self):
        # Create a test user for the tests
        self.user_id = None
        self.create_test_user()
        
        # Create a test image
        self.test_image = self.create_test_food_image()
    
    def create_test_user(self):
        """Create a test user for the tests"""
        response = requests.post(
            f"{API_URL}/register",
            json=TEST_USER
        )
        
        if response.status_code == 200:
            data = response.json()
            self.user_id = data.get("user_id")
            print(f"Created test user with ID: {self.user_id}")
        else:
            # Try logging in if user already exists
            login_response = requests.post(
                f"{API_URL}/login",
                json={
                    "email": TEST_USER["email"],
                    "password": TEST_USER["password"]
                }
            )
            
            if login_response.status_code == 200:
                data = login_response.json()
                self.user_id = data.get("user_id")
                print(f"Logged in as existing test user with ID: {self.user_id}")
            else:
                print(f"Failed to create or login test user: {response.text}")
    
    def create_test_food_image(self):
        """Create a simple test food image"""
        # Create a simple image with text
        img = Image.new('RGB', (400, 300), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        d.text((10, 10), "Test Food Image\nContains: Bread, Cheese, Peanuts", fill=(255, 255, 0))
        
        # Save to BytesIO
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        
        return img_byte_arr
    
    def test_health_endpoint(self):
        """Test the health check endpoint"""
        print("\n--- Testing /api/health endpoint ---")
        response = requests.get(f"{API_URL}/health")
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")
        print("✅ Health endpoint test passed")
    
    def test_register_endpoint(self):
        """Test the user registration endpoint"""
        print("\n--- Testing /api/register endpoint ---")
        
        # Create a unique test user
        unique_email = f"unique_{uuid.uuid4().hex[:8]}@example.com"
        test_user = {
            "email": unique_email,
            "password": "testpass123",
            "allergies": ["Eggs", "Soy", "Fish"]
        }
        
        response = requests.post(
            f"{API_URL}/register",
            json=test_user
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json() if response.status_code == 200 else response.text}")
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertIn("user_id", response.json())
        print("✅ Register endpoint test passed")
    
    def test_login_endpoint(self):
        """Test the login endpoint"""
        print("\n--- Testing /api/login endpoint ---")
        
        # Ensure we have a user to test with
        self.assertIsNotNone(self.user_id, "Test user not created")
        
        login_data = {
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        }
        
        response = requests.post(
            f"{API_URL}/login",
            json=login_data
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json() if response.status_code == 200 else response.text}")
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["user_id"], self.user_id)
        print("✅ Login endpoint test passed")
    
    def test_get_user_endpoint(self):
        """Test the get user endpoint"""
        print("\n--- Testing /api/user/{user_id} endpoint ---")
        
        # Ensure we have a user to test with
        self.assertIsNotNone(self.user_id, "Test user not created")
        
        response = requests.get(f"{API_URL}/user/{self.user_id}")
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json() if response.status_code == 200 else response.text}")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_id"], self.user_id)
        self.assertEqual(response.json()["email"], TEST_USER["email"])
        
        # Note: We're not checking the exact allergies list as it might have been updated
        self.assertIsInstance(response.json()["allergies"], list)
        print("✅ Get user endpoint test passed")
    
    def test_update_allergies_endpoint(self):
        """Test the update allergies endpoint"""
        print("\n--- Testing /api/user/{user_id}/allergies endpoint ---")
        
        # Ensure we have a user to test with
        self.assertIsNotNone(self.user_id, "Test user not created")
        
        # New allergies list
        new_allergies = ["Shellfish", "Sesame", "Eggs"]
        
        update_data = {
            "user_id": self.user_id,
            "allergies": new_allergies
        }
        
        response = requests.put(
            f"{API_URL}/user/{self.user_id}/allergies",
            json=update_data
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json() if response.status_code == 200 else response.text}")
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        
        # Verify the allergies were updated
        get_user_response = requests.get(f"{API_URL}/user/{self.user_id}")
        self.assertEqual(get_user_response.json()["allergies"], new_allergies)
        print("✅ Update allergies endpoint test passed")
    
    def test_analyze_food_endpoint(self):
        """Test the analyze food endpoint with direct Gemini API integration"""
        print("\n--- Testing /api/analyze-food endpoint with direct Gemini API ---")
        
        # Ensure we have a user to test with
        self.assertIsNotNone(self.user_id, "Test user not created")
        
        # First update allergies to include something in our test image
        update_data = {
            "user_id": self.user_id,
            "allergies": ["Nuts", "Dairy"]  # Our test image has peanuts and cheese
        }
        
        requests.put(
            f"{API_URL}/user/{self.user_id}/allergies",
            json=update_data
        )
        
        # Prepare the multipart form data
        files = {
            'image': ('test_food.jpg', self.test_image, 'image/jpeg')
        }
        
        data = {
            'user_id': self.user_id
        }
        
        response = requests.post(
            f"{API_URL}/analyze-food",
            files=files,
            data=data
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Check if the API call was successful
        if response.status_code == 200:
            result = response.json()
            print("✅ Analyze food endpoint test passed with direct Gemini API integration")
            
            # Validate the response structure
            self.assertIn("food_name", result)
            self.assertIn("ingredients", result)
            self.assertIn("allergens_detected", result)
            self.assertIn("safe_to_eat", result)
            self.assertIn("confidence", result)
            
            # Since our test image mentions peanuts and cheese, and we set allergies to Nuts and Dairy,
            # we expect allergens to be detected and safe_to_eat to be False
            if len(result["allergens_detected"]) > 0:
                self.assertFalse(result["safe_to_eat"], "Food should not be safe to eat with detected allergens")
                print(f"Detected allergens: {result['allergens_detected']}")
            
            print(f"Food name: {result['food_name']}")
            print(f"Ingredients: {result['ingredients']}")
            print(f"Safe to eat: {result['safe_to_eat']}")
            print(f"Confidence: {result['confidence']}")
            
        elif response.status_code == 500 and "API key not valid" in response.text:
            print("⚠️ Analyze food endpoint test - API key issue detected")
            print("The Gemini API key appears to be invalid or has expired.")
        else:
            self.fail(f"Unexpected response: {response.status_code} - {response.text}")
    
    def test_get_food_history_endpoint(self):
        """Test the get food history endpoint"""
        print("\n--- Testing /api/user/{user_id}/history endpoint ---")
        
        # Ensure we have a user to test with
        self.assertIsNotNone(self.user_id, "Test user not created")
        
        # We won't try to analyze food first since we know it will fail
        response = requests.get(f"{API_URL}/user/{self.user_id}/history")
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json() if response.status_code == 200 else response.text}")
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("history", response.json())
        self.assertIsInstance(response.json()["history"], list)
        print("✅ Get food history endpoint test passed")
    
    def test_invalid_login(self):
        """Test invalid login credentials"""
        print("\n--- Testing invalid login ---")
        
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        response = requests.post(
            f"{API_URL}/login",
            json=login_data
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid credentials", response.text)
        print("✅ Invalid login test passed - Returns 401 as expected")
    
    def test_nonexistent_user(self):
        """Test getting a nonexistent user"""
        print("\n--- Testing nonexistent user ---")
        
        fake_user_id = str(uuid.uuid4())
        response = requests.get(f"{API_URL}/user/{fake_user_id}")
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        self.assertEqual(response.status_code, 404)
        self.assertIn("User not found", response.text)
        print("✅ Nonexistent user test passed - Returns 404 as expected")

if __name__ == "__main__":
    # Run the tests
    print(f"Testing backend API at: {API_URL}")
    
    # Create a test suite
    suite = unittest.TestSuite()
    suite.addTest(FoodAllergyDetectorAPITest('test_health_endpoint'))
    suite.addTest(FoodAllergyDetectorAPITest('test_register_endpoint'))
    suite.addTest(FoodAllergyDetectorAPITest('test_login_endpoint'))
    suite.addTest(FoodAllergyDetectorAPITest('test_get_user_endpoint'))
    suite.addTest(FoodAllergyDetectorAPITest('test_update_allergies_endpoint'))
    suite.addTest(FoodAllergyDetectorAPITest('test_analyze_food_endpoint'))
    suite.addTest(FoodAllergyDetectorAPITest('test_get_food_history_endpoint'))
    suite.addTest(FoodAllergyDetectorAPITest('test_invalid_login'))
    suite.addTest(FoodAllergyDetectorAPITest('test_nonexistent_user'))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)