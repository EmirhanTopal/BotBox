from django.db import models
from django.utils import timezone


class UniversityInfo(models.Model):
    title = models.CharField(max_length=500)
    description = models.TextField()
    mission = models.TextField(blank=True)
    vision = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True, default='https://www.acibadem.edu.tr')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "University Information"
        verbose_name_plural = "University Information"

    def __str__(self):
        return self.title


class Department(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    link = models.URLField(blank=True)
    source = models.CharField(max_length=100, default='acibadem.edu.tr')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Program(models.Model):
    name = models.CharField(max_length=300, unique=True)
    level = models.CharField(max_length=50, blank=True)   # Bachelor/Master/PhD/Associate
    duration = models.CharField(max_length=50, blank=True) # "4 yıl" vb.
    department = models.CharField(max_length=300, blank=True)  # Fakülte adı
    language = models.CharField(max_length=50, blank=True)     # Türkçe / İngilizce
    description = models.TextField(blank=True)
    link = models.URLField(blank=True)
    sources = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['level', 'name']

    def __str__(self):
        return f"{self.name} ({self.level})"


class Course(models.Model):
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=300)
    credits = models.CharField(max_length=10, blank=True)   # AKTS kredisi
    type = models.CharField(max_length=50, blank=True)      # Zorunlu / Seçmeli
    tul = models.CharField(max_length=20, blank=True)       # T+U+L (teorik+uygulama+lab)

    # İlişki alanları — hangi programa ait, kaçıncı yarıyıl
    program_name = models.CharField(max_length=300, blank=True)   # Program adı
    program_level = models.CharField(max_length=50, blank=True)   # Bachelor/Master vb.
    semester = models.IntegerField(null=True, blank=True)         # 1-8 vb.

    source = models.CharField(max_length=100, default='obs.acibadem.edu.tr')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        sem = f" | {self.semester}.Yarıyıl" if self.semester else ""
        prog = f" | {self.program_name}" if self.program_name else ""
        return f"{self.code} - {self.name}{sem}{prog}"


class Instructor(models.Model):
    name = models.CharField(max_length=200)
    title = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    department = models.CharField(max_length=300, blank=True)
    faculty = models.CharField(max_length=300, blank=True)
    expertise = models.TextField(blank=True)
    profile_url = models.URLField(blank=True)
    level = models.CharField(max_length=50, blank=True)  # Lisans/Önlisans/Lisansüstü
    source = models.CharField(max_length=100, default='acibadem.edu.tr')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['faculty', 'department', 'name']
        unique_together = [['name', 'department']]

    def __str__(self):
        return f"{self.title} {self.name} — {self.department}"


class ChatMessage(models.Model):
    question = models.TextField()
    answer = models.TextField()
    sources = models.JSONField(default=list)
    confidence = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Q: {self.question[:50]}..."


class ScrapingLog(models.Model):
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