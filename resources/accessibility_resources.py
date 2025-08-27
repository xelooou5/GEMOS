#!/usr/bin/env python3
"""
♿ ACCESSIBILITY RESOURCES
WCAG 2.1 guidelines and NVDA documentation for accessibility implementation
"""

class AccessibilityResources:
    def __init__(self):
        self.wcag_guidelines = "https://www.w3.org/TR/WCAG21/"
        self.nvda_dev_guide = "https://download.nvaccess.org/documentation/developerGuide.html"
        
        self.wcag_principles = {
            'perceivable': 'Information must be presentable in ways users can perceive',
            'operable': 'Interface components must be operable',
            'understandable': 'Information and UI operation must be understandable',
            'robust': 'Content must be robust enough for various assistive technologies'
        }
        
        self.nvda_apis = {
            'speech': 'NVDA speech synthesis API',
            'braille': 'NVDA braille display API',
            'review': 'NVDA review cursor API',
            'objects': 'NVDA object navigation API'
        }
        
    def get_wcag_guidelines(self):
        """Get WCAG 2.1 guidelines reference"""
        return {
            'url': self.wcag_guidelines,
            'principles': self.wcag_principles
        }
        
    def get_nvda_resources(self):
        """Get NVDA development resources"""
        return {
            'developer_guide': self.nvda_dev_guide,
            'apis': self.nvda_apis
        }