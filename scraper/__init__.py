"""
Acibadem University data Scraper Module
Handles dual-source scraping:
- Static content: acibadem.edu.tr
- Dynamic content: obs.acibadem.edu.tr
"""

from .acibadem_dual_scraper import AcibademDualScraper

__all__ = ['AcibademDualScraper']