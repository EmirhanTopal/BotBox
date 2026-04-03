from django.db import models
from django.utils import timezone

class UniversityInfo(models.Model):
    """General university information"""
    title = models.CharField(max_length=500)
    description = models.TextField()
    mission = models.TextField(blank=True)
    vision = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "University Information"
        verbose_name_plural = "University Information"
    
    def __str__(self):
        return self.title


class Department(models.Model):
    """University departments"""
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    link = models.URLField(blank=True)
    source = models.CharField(max_length=50, default='acibadem.edu.tr')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Program(models.Model):
    """Academic programs"""
    LEVEL_CHOICES = [
        ('Bachelor', 'Bachelor'),
        ('Master', 'Master'),
        ('PhD', 'PhD'),
        ('Certificate', 'Certificate'),
    ]
    
    name = models.CharField(max_length=255, unique=True)
    level = models.CharField(max_length=50, choices=LEVEL_CHOICES)
    duration = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    sources = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['level', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.level})"


class Course(models.Model):
    """Courses offered"""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    credits = models.CharField(max_length=10, blank=True)
    type = models.CharField(max_length=100, blank=True)
    source = models.CharField(max_length=50, default='obs.acibadem.edu.tr')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class ChatMessage(models.Model):
    """Chat history"""
    question = models.TextField()
    answer = models.TextField()
    sources = models.JSONField(default=list)  # Which data sources were used
    confidence = models.FloatField(default=0.0)  # Confidence score
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Q: {self.question[:50]}..."


class ScrapingLog(models.Model):
    """Track scraping operations"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    items_scraped = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-start_time']
    
    def __str__(self):
        return f"Scrape {self.status} at {self.start_time}"


class ChatSession(models.Model):
    title = models.CharField(max_length=200, default='Yeni Sohbet')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-updated_at']


class Message(models.Model):
    ROLE_CHOICES = [('user', 'Kullanıcı'), ('bot', 'Bot')]
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"

    class Meta:
        ordering = ['created_at']