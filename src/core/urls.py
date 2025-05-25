"""
URL configuration for Voice AI Platform

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path
from api.main import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
