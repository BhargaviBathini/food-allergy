import requests
import json
import base64
import os
import unittest
from io import BytesIO
from PIL import Image, ImageDraw
import random
import uuid

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
        print(f"Response: {response.json()}")
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertIn("user_id", response.json())
    
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
        print(f"Response: {response.json()}")
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["user_id"], self.user_id)
    
    def test_get_user_endpoint(self):
        """Test the get user endpoint"""
        print("\n--- Testing /api/user/{user_id} endpoint ---")
        
        # Ensure we have a user to test with
        self.assertIsNotNone(self.user_id, "Test user not created")
        
        response = requests.get(f"{API_URL}/user/{self.user_id}")
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_id"], self.user_id)
        self.assertEqual(response.json()["email"], TEST_USER["email"])
        self.assertEqual(response.json()["allergies"], TEST_USER["allergies"])
    
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
        print(f"Response: {response.json()}")
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        
        # Verify the allergies were updated
        get_user_response = requests.get(f"{API_URL}/user/{self.user_id}")
        self.assertEqual(get_user_response.json()["allergies"], new_allergies)
    
    def test_analyze_food_endpoint(self):
        """Test the analyze food endpoint"""
        print("\n--- Testing /api/analyze-food endpoint ---")
        
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
        print(f"Response: {response.json()}")
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("food_name", response.json())
        self.assertIn("ingredients", response.json())
        self.assertIn("allergens_detected", response.json())
        self.assertIn("safe_to_eat", response.json())
        self.assertIn("confidence", response.json())
    
    def test_get_food_history_endpoint(self):
        """Test the get food history endpoint"""
        print("\n--- Testing /api/user/{user_id}/history endpoint ---")
        
        # Ensure we have a user to test with
        self.assertIsNotNone(self.user_id, "Test user not created")
        
        # First analyze a food to create history
        self.test_analyze_food_endpoint()
        
        response = requests.get(f"{API_URL}/user/{self.user_id}/history")
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("history", response.json())
        self.assertIsInstance(response.json()["history"], list)
        
        # Check if we have at least one history entry
        if response.json()["history"]:
            history_item = response.json()["history"][0]
            self.assertIn("user_id", history_item)
            self.assertIn("food_name", history_item)
            self.assertIn("ingredients", history_item)
            self.assertIn("allergens_detected", history_item)
            self.assertIn("safe_to_eat", history_item)
    
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
    
    def test_nonexistent_user(self):
        """Test getting a nonexistent user"""
        print("\n--- Testing nonexistent user ---")
        
        fake_user_id = str(uuid.uuid4())
        response = requests.get(f"{API_URL}/user/{fake_user_id}")
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        self.assertEqual(response.status_code, 404)

if __name__ == "__main__":
    # Run the tests
    print(f"Testing backend API at: {API_URL}")
    unittest.main(argv=['first-arg-is-ignored'], exit=False)