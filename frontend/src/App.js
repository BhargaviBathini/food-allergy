import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [currentView, setCurrentView] = useState('login'); // 'login', 'register', 'main', 'profile'
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [showCamera, setShowCamera] = useState(false);
  const [foodHistory, setFoodHistory] = useState([]);
  
  // Forms
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [registerForm, setRegisterForm] = useState({ 
    email: '', 
    password: '', 
    allergies: [] 
  });
  
  // Refs
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);

  const commonAllergies = [
    'Nuts', 'Dairy', 'Gluten', 'Shellfish', 'Eggs', 'Soy', 'Fish', 'Sesame'
  ];

  // Authentication functions
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${BACKEND_URL}/api/login`, loginForm);
      setUser(response.data);
      setCurrentView('main');
      setLoginForm({ email: '', password: '' });
    } catch (error) {
      alert('Login failed: ' + (error.response?.data?.detail || 'Unknown error'));
    }
    setLoading(false);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${BACKEND_URL}/api/register`, registerForm);
      // Auto login after registration
      const loginResponse = await axios.post(`${BACKEND_URL}/api/login`, {
        email: registerForm.email,
        password: registerForm.password
      });
      setUser(loginResponse.data);
      setCurrentView('main');
      setRegisterForm({ email: '', password: '', allergies: [] });
    } catch (error) {
      alert('Registration failed: ' + (error.response?.data?.detail || 'Unknown error'));
    }
    setLoading(false);
  };

  const handleLogout = () => {
    setUser(null);
    setCurrentView('login');
    setSelectedImage(null);
    setAnalysisResult(null);
    setFoodHistory([]);
  };

  // Camera functions
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: 'environment' } 
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setShowCamera(true);
    } catch (error) {
      alert('Camera access denied or not available');
      console.error('Camera error:', error);
    }
  };

  const capturePhoto = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0);
    
    canvas.toBlob((blob) => {
      setSelectedImage(blob);
      stopCamera();
    }, 'image/jpeg', 0.8);
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach(track => track.stop());
    }
    setShowCamera(false);
  };

  // File upload
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedImage(file);
    }
  };

  // Analyze food
  const analyzeFood = async () => {
    if (!selectedImage || !user) return;
    
    setLoading(true);
    setAnalysisResult(null);
    
    try {
      const formData = new FormData();
      formData.append('user_id', user.user_id);
      formData.append('image', selectedImage);
      
      const response = await axios.post(`${BACKEND_URL}/api/analyze-food`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setAnalysisResult(response.data);
    } catch (error) {
      alert('Analysis failed: ' + (error.response?.data?.detail || 'Unknown error'));
      console.error('Analysis error:', error);
    }
    setLoading(false);
  };

  // Load food history
  const loadFoodHistory = async () => {
    if (!user) return;
    try {
      const response = await axios.get(`${BACKEND_URL}/api/user/${user.user_id}/history`);
      setFoodHistory(response.data.history);
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  };

  // Toggle allergy in registration
  const toggleAllergy = (allergy) => {
    setRegisterForm(prev => ({
      ...prev,
      allergies: prev.allergies.includes(allergy) 
        ? prev.allergies.filter(a => a !== allergy)
        : [...prev.allergies, allergy]
    }));
  };

  // Reset analysis
  const resetAnalysis = () => {
    setSelectedImage(null);
    setAnalysisResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  useEffect(() => {
    if (user && currentView === 'main') {
      loadFoodHistory();
    }
  }, [user, currentView]);

  // Login View
  if (currentView === 'login') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">🍽️ Allergy Detector</h1>
            <p className="text-gray-600">Keep yourself safe from food allergies</p>
          </div>
          
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <input
                type="email"
                placeholder="Email"
                value={loginForm.email}
                onChange={(e) => setLoginForm({...loginForm, email: e.target.value})}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                required
              />
            </div>
            <div>
              <input
                type="password"
                placeholder="Password"
                value={loginForm.password}
                onChange={(e) => setLoginForm({...loginForm, password: e.target.value})}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-green-500 text-white py-3 rounded-lg font-semibold hover:bg-green-600 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Signing In...' : 'Sign In'}
            </button>
          </form>
          
          <p className="text-center mt-6 text-gray-600">
            Don't have an account?{' '}
            <button
              onClick={() => setCurrentView('register')}
              className="text-green-500 font-semibold hover:underline"
            >
              Sign Up
            </button>
          </p>
        </div>
      </div>
    );
  }

  // Register View
  if (currentView === 'register') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">🍽️ Join Us</h1>
            <p className="text-gray-600">Create your allergy profile</p>
          </div>
          
          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <input
                type="email"
                placeholder="Email"
                value={registerForm.email}
                onChange={(e) => setRegisterForm({...registerForm, email: e.target.value})}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                required
              />
            </div>
            <div>
              <input
                type="password"
                placeholder="Password"
                value={registerForm.password}
                onChange={(e) => setRegisterForm({...registerForm, password: e.target.value})}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                required
              />
            </div>
            
            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-700">
                Select your allergies:
              </label>
              <div className="grid grid-cols-2 gap-2">
                {commonAllergies.map(allergy => (
                  <label key={allergy} className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={registerForm.allergies.includes(allergy)}
                      onChange={() => toggleAllergy(allergy)}
                      className="rounded border-gray-300 text-green-500 focus:ring-green-500"
                    />
                    <span className="text-sm text-gray-700">{allergy}</span>
                  </label>
                ))}
              </div>
            </div>
            
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-green-500 text-white py-3 rounded-lg font-semibold hover:bg-green-600 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Creating Account...' : 'Create Account'}
            </button>
          </form>
          
          <p className="text-center mt-6 text-gray-600">
            Already have an account?{' '}
            <button
              onClick={() => setCurrentView('login')}
              className="text-green-500 font-semibold hover:underline"
            >
              Sign In
            </button>
          </p>
        </div>
      </div>
    );
  }

  // Main App View
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-800">🍽️ Allergy Detector</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">Hello, {user?.email}</span>
              <button
                onClick={() => setCurrentView('profile')}
                className="text-sm text-green-600 hover:text-green-700"
              >
                Profile
              </button>
              <button
                onClick={handleLogout}
                className="text-sm text-red-600 hover:text-red-700"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto p-6">
        {/* Camera Modal */}
        {showCamera && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl p-6 w-full max-w-md">
              <div className="text-center mb-4">
                <h3 className="text-lg font-semibold">Take a Photo</h3>
              </div>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                className="w-full rounded-lg mb-4"
              />
              <canvas ref={canvasRef} className="hidden" />
              <div className="flex space-x-3">
                <button
                  onClick={capturePhoto}
                  className="flex-1 bg-green-500 text-white py-2 rounded-lg font-semibold hover:bg-green-600"
                >
                  📸 Capture
                </button>
                <button
                  onClick={stopCamera}
                  className="flex-1 bg-gray-500 text-white py-2 rounded-lg font-semibold hover:bg-gray-600"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Main Content */}
        {currentView === 'main' && (
          <div className="space-y-8">
            {/* Upload Section */}
            <div className="bg-white rounded-2xl shadow-lg p-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">
                Analyze Your Food
              </h2>
              
              {!selectedImage ? (
                <div className="space-y-4">
                  <div className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center">
                    <div className="text-4xl mb-4">📸</div>
                    <p className="text-gray-600 mb-4">Upload a photo or take a picture of your food</p>
                    <div className="flex flex-col sm:flex-row gap-3 justify-center">
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className="bg-green-500 text-white px-6 py-3 rounded-lg font-semibold hover:bg-green-600 transition-colors"
                      >
                        📁 Upload Photo
                      </button>
                      <button
                        onClick={startCamera}
                        className="bg-blue-500 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-600 transition-colors"
                      >
                        📷 Take Photo
                      </button>
                    </div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      onChange={handleFileSelect}
                      className="hidden"
                    />
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="text-center">
                    <img
                      src={URL.createObjectURL(selectedImage)}
                      alt="Selected food"
                      className="max-w-full max-h-64 rounded-lg shadow-md mx-auto"
                    />
                  </div>
                  <div className="flex flex-col sm:flex-row gap-3 justify-center">
                    <button
                      onClick={analyzeFood}
                      disabled={loading}
                      className="bg-green-500 text-white px-8 py-3 rounded-lg font-semibold hover:bg-green-600 disabled:opacity-50 transition-colors"
                    >
                      {loading ? '🔍 Analyzing...' : '🔍 Analyze Food'}
                    </button>
                    <button
                      onClick={resetAnalysis}
                      className="bg-gray-500 text-white px-8 py-3 rounded-lg font-semibold hover:bg-gray-600 transition-colors"
                    >
                      🔄 Try Another
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Results Section */}
            {analysisResult && (
              <div className="bg-white rounded-2xl shadow-lg p-8">
                <h3 className="text-2xl font-bold text-gray-800 mb-6">Analysis Results</h3>
                
                {/* Safety Alert */}
                <div className={`p-6 rounded-xl mb-6 ${
                  analysisResult.safe_to_eat 
                    ? 'bg-green-50 border-2 border-green-200' 
                    : 'bg-red-50 border-2 border-red-200'
                }`}>
                  <div className="flex items-center space-x-3">
                    <div className="text-3xl">
                      {analysisResult.safe_to_eat ? '✅' : '⚠️'}
                    </div>
                    <div>
                      <h4 className={`text-xl font-bold ${
                        analysisResult.safe_to_eat ? 'text-green-800' : 'text-red-800'
                      }`}>
                        {analysisResult.safe_to_eat ? 'Safe to Eat!' : 'Warning!'}
                      </h4>
                      {analysisResult.warning_message && (
                        <p className="text-red-700 mt-1">{analysisResult.warning_message}</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Food Details */}
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <h5 className="font-semibold text-gray-800 mb-3">Detected Food:</h5>
                    <p className="text-lg text-gray-700 bg-gray-50 p-3 rounded-lg">
                      {analysisResult.food_name}
                    </p>
                  </div>
                  
                  <div>
                    <h5 className="font-semibold text-gray-800 mb-3">Confidence:</h5>
                    <div className="bg-gray-50 p-3 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-green-500 h-2 rounded-full"
                            style={{ width: `${(analysisResult.confidence * 100)}%` }}
                          ></div>
                        </div>
                        <span className="text-sm font-medium text-gray-700">
                          {Math.round(analysisResult.confidence * 100)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Ingredients */}
                <div className="mt-6">
                  <h5 className="font-semibold text-gray-800 mb-3">Detected Ingredients:</h5>
                  <div className="flex flex-wrap gap-2">
                    {analysisResult.ingredients.map((ingredient, index) => (
                      <span
                        key={index}
                        className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm"
                      >
                        {ingredient}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Allergens */}
                {analysisResult.allergens_detected.length > 0 && (
                  <div className="mt-6">
                    <h5 className="font-semibold text-red-800 mb-3">⚠️ Allergens Found:</h5>
                    <div className="flex flex-wrap gap-2">
                      {analysisResult.allergens_detected.map((allergen, index) => (
                        <span
                          key={index}
                          className="bg-red-100 text-red-800 px-3 py-1 rounded-full text-sm font-medium"
                        >
                          {allergen}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Food History */}
            {foodHistory.length > 0 && (
              <div className="bg-white rounded-2xl shadow-lg p-8">
                <h3 className="text-2xl font-bold text-gray-800 mb-6">Recent Food Analysis</h3>
                <div className="space-y-4">
                  {foodHistory.slice(0, 5).map((item, index) => (
                    <div key={index} className="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg">
                      <img 
                        src={`data:image/jpeg;base64,${item.image_base64}`}
                        alt={item.food_name}
                        className="w-16 h-16 object-cover rounded-lg"
                      />
                      <div className="flex-1">
                        <h5 className="font-semibold text-gray-800">{item.food_name}</h5>
                        <p className="text-sm text-gray-600">
                          {item.safe_to_eat ? '✅ Safe' : '⚠️ Contains allergens'}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className="text-xs text-gray-500">
                          {new Date(item.analyzed_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Profile View */}
        {currentView === 'profile' && (
          <div className="bg-white rounded-2xl shadow-lg p-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-800">Your Profile</h2>
              <button
                onClick={() => setCurrentView('main')}
                className="text-green-600 hover:text-green-700 font-semibold"
              >
                ← Back to Main
              </button>
            </div>
            
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email:</label>
                <p className="text-lg text-gray-800 bg-gray-50 p-3 rounded-lg">{user?.email}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Your Allergies:</label>
                <div className="flex flex-wrap gap-2">
                  {user?.allergies?.length > 0 ? (
                    user.allergies.map((allergy, index) => (
                      <span
                        key={index}
                        className="bg-red-100 text-red-800 px-3 py-1 rounded-full text-sm font-medium"
                      >
                        {allergy}
                      </span>
                    ))
                  ) : (
                    <p className="text-gray-500">No allergies specified</p>
                  )}
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Total Scans:</label>
                <p className="text-lg text-gray-800 bg-gray-50 p-3 rounded-lg">{foodHistory.length}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;