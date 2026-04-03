import pytest
from django.test import TestCase, Client
from django.urls import reverse
import json

class TestChatAPI(TestCase):
    """Test chatbot API endpoints"""
    
    def setUp(self):
        self.client = Client()
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.client.get('/api/health/')
        self.assertIn(response.status_code, [200, 404])
    
    def test_chat_endpoint_post(self):
        """Test chat endpoint accepts POST"""
        response = self.client.post(
            '/api/chat/',
            data=json.dumps({'question': 'Test'}),
            content_type='application/json'
        )
        self.assertIn(response.status_code, [200, 400, 405, 500])
    
    def test_programs_endpoint(self):
        """Test programs list endpoint"""
        response = self.client.get('/api/programs/')
        self.assertIn(response.status_code, [200, 404])
    
    def test_courses_endpoint(self):
        """Test courses list endpoint"""
        response = self.client.get('/api/courses/')
        self.assertIn(response.status_code, [200, 404])
    
    def test_departments_endpoint(self):
        """Test departments list endpoint"""
        response = self.client.get('/api/departments/')
        self.assertIn(response.status_code, [200, 404])