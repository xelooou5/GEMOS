#!/usr/bin/env python3
"""
🔧 API INTEGRATION FRAMEWORK - READY FOR YOUR APIS
Built by AI team while you acquire APIs - just insert keys and go!
"""

import asyncio
import aiohttp
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime

class APIIntegrationFramework:
    """Ready-to-use API integration framework - just add your API keys!"""
    
    def __init__(self):
        self.api_keys = {
            # INSERT YOUR API KEYS HERE
            'openai_api_key': os.getenv('OPENAI_API_KEY', 'YOUR_OPENAI_KEY_HERE'),
            'weather_api_key': os.getenv('WEATHER_API_KEY', 'YOUR_WEATHER_KEY_HERE'),
            'gmail_credentials': os.getenv('GMAIL_CREDENTIALS', 'YOUR_GMAIL_CREDS_HERE'),
            'fda_api_key': os.getenv('FDA_API_KEY', 'YOUR_FDA_KEY_HERE'),
            'news_api_key': os.getenv('NEWS_API_KEY', 'YOUR_NEWS_KEY_HERE'),
            'spotify_client_id': '1868e3732f8f4fc7950ec7741b4aece9',  # Already have this!
        }
        
        self.session = None
        print("🔧 API Integration Framework ready - just insert your API keys!")
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def openai_request(self, prompt: str) -> str:
        """OpenAI API integration - ready for your key"""
        if self.api_keys['openai_api_key'] == 'YOUR_OPENAI_KEY_HERE':
            return "🔑 Insert your OpenAI API key to enable AI responses"
            
        headers = {
            'Authorization': f"Bearer {self.api_keys['openai_api_key']}",
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'gpt-4o-mini',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 500
        }
        
        try:
            async with self.session.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data
            ) as response:
                result = await response.json()
                return result['choices'][0]['message']['content']
        except Exception as e:
            return f"OpenAI API error: {e}"
            
    async def weather_request(self, city: str = "London") -> Dict[str, Any]:
        """Weather API integration - ready for your key"""
        if self.api_keys['weather_api_key'] == 'YOUR_WEATHER_KEY_HERE':
            return {"error": "🔑 Insert your Weather API key"}
            
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            'q': city,
            'appid': self.api_keys['weather_api_key'],
            'units': 'metric'
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                return await response.json()
        except Exception as e:
            return {"error": f"Weather API error: {e}"}
            
    async def fda_drug_lookup(self, drug_name: str) -> Dict[str, Any]:
        """FDA Drug API integration - ready to use"""
        url = f"https://api.fda.gov/drug/label.json"
        params = {
            'search': f'openfda.brand_name:"{drug_name}"',
            'limit': 1
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                return await response.json()
        except Exception as e:
            return {"error": f"FDA API error: {e}"}
            
    async def news_request(self, query: str = "accessibility") -> Dict[str, Any]:
        """News API integration - ready for your key"""
        if self.api_keys['news_api_key'] == 'YOUR_NEWS_KEY_HERE':
            return {"error": "🔑 Insert your News API key"}
            
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': query,
            'apiKey': self.api_keys['news_api_key'],
            'pageSize': 5,
            'sortBy': 'relevancy'
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                return await response.json()
        except Exception as e:
            return {"error": f"News API error: {e}"}
            
    async def test_all_apis(self):
        """Test all API integrations"""
        print("\n🧪 TESTING ALL API INTEGRATIONS...")
        
        # Test OpenAI
        print("\n🤖 Testing OpenAI API...")
        ai_response = await self.openai_request("Hello, this is a test for GEM OS accessibility")
        print(f"   Response: {ai_response[:100]}...")
        
        # Test Weather
        print("\n🌤️ Testing Weather API...")
        weather_data = await self.weather_request("London")
        if 'error' not in weather_data:
            temp = weather_data.get('main', {}).get('temp', 'N/A')
            print(f"   London temperature: {temp}°C")
        else:
            print(f"   {weather_data['error']}")
            
        # Test FDA
        print("\n💊 Testing FDA Drug API...")
        drug_data = await self.fda_drug_lookup("aspirin")
        if 'error' not in drug_data:
            print("   ✅ FDA drug database accessible")
        else:
            print(f"   {drug_data['error']}")
            
        # Test News
        print("\n📰 Testing News API...")
        news_data = await self.news_request("accessibility technology")
        if 'error' not in news_data:
            articles = news_data.get('articles', [])
            print(f"   Found {len(articles)} accessibility news articles")
        else:
            print(f"   {news_data['error']}")
            
        print("\n✅ API TESTING COMPLETE!")

async def main():
    """Test the API integration framework"""
    print("🔧 API INTEGRATION FRAMEWORK - READY FOR YOUR KEYS!")
    
    async with APIIntegrationFramework() as api_framework:
        await api_framework.test_all_apis()
        
    print("\n🚀 FRAMEWORK READY - INSERT YOUR API KEYS AND RESTART!")

if __name__ == "__main__":
    asyncio.run(main())